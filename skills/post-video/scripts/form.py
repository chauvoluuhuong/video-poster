#!/usr/bin/env python3
"""The post-video form: a local page where the user picks files, checks the posts and presses Post.

Claude drives it with these commands (all take --state DIR, default ~/.video-poster/current):

  form.py start [--no-open]        start the server, open the page, print {"url": ...}
  form.py wait submit              block until the user submits the form; prints the form as JSON
  form.py preview preview.json     show the prepared posts on the page (phase: preview)
  form.py wait decision            block until Post / Back / Cancel; Post prints the final posts
  form.py progress ID STATUS [--link URL] [--note TEXT]   update one upload on the posting screen
  form.py done                     mark the run finished
  form.py stop                     stop the server

`wait` exits 0 with {"waiting": true} when --timeout (default 540 s) passes: run it again.

Files in the state dir: server.json, submit.json, preview.json, final.json.
The server listens on 127.0.0.1 only and every request needs the one-time token from the URL.
"""
import argparse
import json
import os
import secrets
import shutil
import subprocess
import sys
import time
import urllib.error
import urllib.request
import webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

HERE = os.path.dirname(os.path.abspath(__file__))
HOME_DIR = os.path.expanduser("~/.video-poster")
PLATFORMS = ("youtube", "facebook", "tiktok", "linkedin")
CHOICES = {
    "youtube": ("both", "wide", "tall"),
    "facebook": ("wide", "tall", "both"),
    "tiktok": ("tall", "wide"),
    "linkedin": ("wide", "tall"),
}
STATUSES = ("waiting", "uploading", "posted", "failed", "skipped")


def read_json(path, default=None):
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except (OSError, ValueError):
        return default


def write_json(path, data):
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    os.replace(tmp, path)


def expand(p):
    return os.path.abspath(os.path.expanduser(p.strip())) if p and p.strip() else ""


# ---------------------------------------------------------------- server

def pick_file(kind):
    """Open the native file picker. Returns {"path": ...}, {"cancelled": true} or {"unsupported": true}."""
    cmd = os.environ.get("VIDEO_POSTER_PICK")  # tests: a command that prints a path
    if cmd:
        out = subprocess.run(cmd, shell=True, capture_output=True, text=True)
        path = out.stdout.strip()
        return {"path": path} if path else {"cancelled": True}
    if sys.platform != "darwin":
        return {"unsupported": True}
    prompt = {"video": "Choose the video", "srt": "Choose the SRT caption file", "text": "Choose the description file"}[kind]
    of_type = ' of type {"public.movie"}' if kind == "video" else ""
    script = (
        "tell application (path to frontmost application as text) to "
        f'POSIX path of (choose file with prompt "{prompt}"{of_type})'
    )
    out = subprocess.run(["osascript", "-e", script], capture_output=True, text=True)
    path = out.stdout.strip()
    return {"path": path} if out.returncode == 0 and path else {"cancelled": True}


def validate_form(form):
    """Normalise the submitted form. Returns (clean_form, errors)."""
    errors, clean = [], {"videos": {}, "platforms": {}}
    for shape in ("wide", "tall"):
        slot = (form.get("videos") or {}).get(shape) or {}
        video, srt = expand(slot.get("video", "")), expand(slot.get("srt", ""))
        name = "16:9" if shape == "wide" else "9:16"
        if video and not os.path.isfile(video):
            errors.append(f"{name} video not found: {video}")
        if srt and not os.path.isfile(srt):
            errors.append(f"{name} SRT not found: {srt}")
        if srt and not video:
            errors.append(f"{name} has an SRT but no video")
        clean["videos"][shape] = {"video": video, "srt": srt}
    if not any(v["video"] for v in clean["videos"].values()):
        errors.append("Choose at least one video")

    clean["description_file"] = expand(form.get("description_file", ""))
    clean["description_text"] = (form.get("description_text") or "").strip()
    if clean["description_file"] and not os.path.isfile(clean["description_file"]):
        errors.append(f"Description file not found: {clean['description_file']}")
    if not clean["description_file"] and not clean["description_text"]:
        errors.append("Choose a description file or paste the text")

    for p in PLATFORMS:
        choice = (form.get("platforms") or {}).get(p)
        if choice:
            if choice not in CHOICES[p]:
                errors.append(f"Unknown choice for {p}: {choice}")
            else:
                clean["platforms"][p] = choice
    if not clean["platforms"]:
        errors.append("Tick at least one platform")

    clean["visibility"] = form.get("visibility") if form.get("visibility") in ("public", "private", "unlisted") else "public"
    clean["language"] = (form.get("language") or "vi").strip()[:10]
    return clean, errors


class State:
    def __init__(self, state_dir, token):
        self.dir, self.token = state_dir, token
        self.phase = "form"  # form | preparing | preview | posting | done | cancelled
        self.form = read_json(os.path.join(HOME_DIR, "last_form.json"), {})
        self.preview = None
        self.progress = {}
        self.rev = 0

    def path(self, name):
        return os.path.join(self.dir, name)

    def public(self):
        return {"phase": self.phase, "form": self.form, "preview": self.preview, "progress": self.progress, "rev": self.rev}

    def drop(self, *names):
        for n in names:
            try:
                os.remove(self.path(n))
            except OSError:
                pass


def merge_decision(preview, edits):
    """Apply the user's edits to the previewed posts. Returns (posts, errors)."""
    posts, errors = [], []
    by_id = {e.get("id"): e.get("fields") or {} for e in edits or []}
    for post in preview.get("posts", []):
        post = json.loads(json.dumps(post))
        for field in post.get("fields", []):
            if field["key"] in by_id.get(post["id"], {}):
                field["value"] = str(by_id[post["id"]][field["key"]]).replace("\r\n", "\n").strip()
            limit = field.get("limit")
            if limit and len(field["value"]) > limit:
                errors.append(f"{post['platform']} {field['label']}: {len(field['value'])} characters, limit {limit}")
            if field.get("required") and not field["value"]:
                errors.append(f"{post['platform']} {field['label']} is empty")
        posts.append(post)
    return posts, errors


def make_handler(st):
    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *a):
            pass

        def send(self, code, body, ctype="application/json"):
            data = body if isinstance(body, bytes) else json.dumps(body, ensure_ascii=False).encode()
            self.send_response(code)
            self.send_header("Content-Type", ctype + "; charset=utf-8")
            self.send_header("Content-Length", str(len(data)))
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            self.wfile.write(data)

        def allowed(self):
            host = (self.headers.get("Host") or "").split(":")[0]
            if host not in ("127.0.0.1", "localhost"):
                return False
            token = self.headers.get("X-Token") or ""
            if "?t=" in self.path:
                token = token or self.path.split("?t=", 1)[1].split("&")[0]
            return secrets.compare_digest(token, st.token)

        def do_GET(self):
            if not self.allowed():
                return self.send(403, {"error": "bad token"})
            route = self.path.split("?")[0]
            if route == "/":
                with open(os.path.join(HERE, "form.html"), "rb") as f:
                    return self.send(200, f.read(), "text/html")
            if route == "/api/state":
                return self.send(200, st.public())
            self.send(404, {"error": "not found"})

        def do_POST(self):
            if not self.allowed():
                return self.send(403, {"error": "bad token"})
            try:
                body = json.loads(self.rfile.read(int(self.headers.get("Content-Length") or 0)) or b"{}")
            except ValueError:
                return self.send(400, {"error": "bad json"})
            route = self.path.split("?")[0]
            st.rev += 1

            if route == "/api/pick":
                kind = body.get("kind")
                if kind not in ("video", "srt", "text"):
                    return self.send(400, {"error": "bad kind"})
                return self.send(200, pick_file(kind))

            if route == "/api/submit":
                form, errors = validate_form(body)
                if errors:
                    return self.send(400, {"errors": errors})
                st.form, st.phase, st.preview, st.progress = form, "preparing", None, {}
                st.drop("preview.json", "final.json", "decision.json")
                write_json(st.path("submit.json"), form)
                os.makedirs(HOME_DIR, exist_ok=True)
                keep = {"choices": form["platforms"], "visibility": form["visibility"], "language": form["language"]}
                write_json(os.path.join(HOME_DIR, "last_form.json"), keep)
                return self.send(200, {"ok": True})

            if route == "/api/preview":  # from Claude
                st.preview, st.phase = body, "preview"
                write_json(st.path("preview.json"), body)
                return self.send(200, {"ok": True})

            if route == "/api/decision":
                action = body.get("action")
                if action == "cancel":
                    st.phase = "cancelled"
                    write_json(st.path("decision.json"), {"action": "cancel"})
                    return self.send(200, {"ok": True})
                if action == "back":
                    st.phase = "form"
                    st.drop("submit.json", "preview.json")
                    write_json(st.path("decision.json"), {"action": "back"})
                    return self.send(200, {"ok": True})
                if action == "post" and st.phase == "preview" and st.preview:
                    posts, errors = merge_decision(st.preview, body.get("posts"))
                    if errors:
                        return self.send(400, {"errors": errors})
                    st.preview = dict(st.preview, posts=posts)
                    st.progress = {p["id"]: {"status": "waiting"} for p in posts}
                    st.phase = "posting"
                    write_json(st.path("final.json"), {"posts": posts})
                    write_json(st.path("decision.json"), {"action": "post"})
                    return self.send(200, {"ok": True})
                return self.send(400, {"errors": ["Nothing to post yet"]})

            if route == "/api/progress":  # from Claude
                if body.get("done"):
                    st.phase = "done"
                elif body.get("id") in st.progress and body.get("status") in STATUSES:
                    st.progress[body["id"]] = {k: body[k] for k in ("status", "link", "note") if body.get(k)}
                else:
                    return self.send(400, {"error": "unknown id or status"})
                return self.send(200, {"ok": True})

            if route == "/api/stop":
                self.send(200, {"ok": True})
                os._exit(0)
            self.send(404, {"error": "not found"})

    return Handler


def serve(state_dir):
    token = secrets.token_urlsafe(24)
    st = State(state_dir, token)
    httpd = ThreadingHTTPServer(("127.0.0.1", 0), make_handler(st))
    port = httpd.server_address[1]
    write_json(st.path("server.json"), {"port": port, "token": token, "pid": os.getpid(),
                                        "url": f"http://127.0.0.1:{port}/?t={token}"})
    httpd.timeout = 60
    deadline = time.time() + 12 * 3600
    while time.time() < deadline:
        httpd.handle_request()


# ---------------------------------------------------------------- commands

def call(state_dir, route, body):
    srv = read_json(os.path.join(state_dir, "server.json"))
    if not srv:
        sys.exit(json.dumps({"error": "form server is not running; run: form.py start"}))
    req = urllib.request.Request(
        f"http://127.0.0.1:{srv['port']}{route}", data=json.dumps(body).encode(),
        headers={"Content-Type": "application/json", "X-Token": srv["token"]})
    try:
        with urllib.request.urlopen(req, timeout=10) as r:
            return json.load(r)
    except urllib.error.HTTPError as e:
        sys.exit(json.dumps({"error": e.read().decode(errors="replace")}))
    except OSError as e:
        sys.exit(json.dumps({"error": f"form server not reachable ({e}); run: form.py start"}))


def cmd_start(a):
    old = read_json(os.path.join(a.state, "server.json"))
    if old:
        try:
            os.kill(old["pid"], 15)
        except (OSError, KeyError):
            pass
    shutil.rmtree(a.state, ignore_errors=True)
    os.makedirs(a.state, exist_ok=True)
    subprocess.Popen([sys.executable, os.path.abspath(__file__), "serve", "--state", a.state],
                     stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                     start_new_session=True)
    for _ in range(100):
        srv = read_json(os.path.join(a.state, "server.json"))
        if srv:
            break
        time.sleep(0.05)
    else:
        sys.exit(json.dumps({"error": "form server did not start"}))
    if not a.no_open:
        webbrowser.open(srv["url"])
    print(json.dumps({"url": srv["url"], "state": a.state, "opened": not a.no_open}))


def cmd_wait(a):
    name = "submit.json" if a.what == "submit" else "decision.json"
    path = os.path.join(a.state, name)
    end = time.time() + a.timeout
    while time.time() < end:
        data = read_json(path)
        if data is not None:
            if a.what == "decision":
                os.remove(path)
                if data.get("action") == "post":
                    data["posts"] = read_json(os.path.join(a.state, "final.json"), {}).get("posts", [])
            else:
                cancel = read_json(os.path.join(a.state, "decision.json"))
                if cancel and cancel.get("action") == "cancel":
                    data = cancel
            print(json.dumps(data, ensure_ascii=False, indent=2))
            return
        cancel = read_json(os.path.join(a.state, "decision.json"))
        if a.what == "submit" and cancel and cancel.get("action") == "cancel":
            print(json.dumps(cancel))
            return
        if a.what == "submit" and cancel:  # a stale "back"
            os.remove(os.path.join(a.state, "decision.json"))
        time.sleep(0.5)
    print(json.dumps({"waiting": True}))


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--state", default=os.path.join(HOME_DIR, "current"))
    sub = ap.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("start"); s.add_argument("--no-open", action="store_true")
    sub.add_parser("serve")
    s = sub.add_parser("wait"); s.add_argument("what", choices=("submit", "decision")); s.add_argument("--timeout", type=float, default=540)
    s = sub.add_parser("preview"); s.add_argument("file")
    s = sub.add_parser("progress"); s.add_argument("id"); s.add_argument("status", choices=STATUSES)
    s.add_argument("--link"); s.add_argument("--note")
    sub.add_parser("done")
    sub.add_parser("stop")
    for p in sub.choices.values():
        p.add_argument("--state", default=argparse.SUPPRESS)
    a = ap.parse_args()
    a.state = os.path.abspath(os.path.expanduser(a.state))

    if a.cmd == "start":
        cmd_start(a)
    elif a.cmd == "serve":
        serve(a.state)
    elif a.cmd == "wait":
        cmd_wait(a)
    elif a.cmd == "preview":
        data = read_json(a.file)
        if not data or "posts" not in data:
            sys.exit(json.dumps({"error": f"{a.file} is not a preview file"}))
        print(json.dumps(call(a.state, "/api/preview", data)))
    elif a.cmd == "progress":
        print(json.dumps(call(a.state, "/api/progress", {"id": a.id, "status": a.status, "link": a.link, "note": a.note})))
    elif a.cmd == "done":
        print(json.dumps(call(a.state, "/api/progress", {"done": True})))
    elif a.cmd == "stop":
        srv = read_json(os.path.join(a.state, "server.json"))
        if srv:
            try:
                call(a.state, "/api/stop", {})
            except SystemExit:
                pass
            try:
                os.remove(os.path.join(a.state, "server.json"))
            except OSError:
                pass
        print(json.dumps({"stopped": True}))


if __name__ == "__main__":
    main()
