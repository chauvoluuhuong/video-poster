"""End-to-end test of the form: the real server and CLI, driven over HTTP the way the page does."""
import json
import os
import subprocess
import sys
import tempfile
import unittest
import urllib.error
import urllib.request

S = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "skills", "post-video", "scripts"))
SRT = "1\n00:00:01,000 --> 00:00:02,000\nXin chào\n"


class FormFlow(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.state = os.path.join(self.tmp, "state")
        self.env = dict(os.environ, HOME=self.tmp, VIDEO_POSTER_PICK="echo /picked/file.mp4")
        self.files = {}
        for name, body in (("wide.mp4", "x"), ("tall.mp4", "x"), ("wide.srt", SRT), ("desc.md", "# Title\ntext #tag")):
            self.files[name] = os.path.join(self.tmp, name)
            with open(self.files[name], "w", encoding="utf-8") as f:
                f.write(body)
        self.srv = self.cli("start", "--no-open")
        self.addCleanup(lambda: self.cli("stop"))

    def cli(self, *args, ok=True):
        out = subprocess.run([sys.executable, os.path.join(S, "form.py"), "--state", self.state, *args],
                             capture_output=True, text=True, env=self.env, timeout=30)
        if ok:
            self.assertEqual(out.returncode, 0, out.stderr + out.stdout)
        return json.loads(out.stdout) if out.stdout.strip().startswith("{") else out

    def http(self, route, body=None, token=None, host=None):
        base = self.srv["url"].split("/?t=")[0]
        tok = self.srv["url"].split("?t=")[1] if token is None else token
        headers = {"X-Token": tok, "Content-Type": "application/json"}
        if host:
            headers["Host"] = host
        req = urllib.request.Request(base + route, data=None if body is None else json.dumps(body).encode(), headers=headers)
        try:
            with urllib.request.urlopen(req, timeout=10) as r:
                raw = r.read()
                return r.status, (json.loads(raw) if route.startswith("/api") else raw.decode())
        except urllib.error.HTTPError as e:
            with e:
                return e.code, json.loads(e.read() or b"{}")

    def form(self, **over):
        f = {"videos": {"wide": {"video": self.files["wide.mp4"], "srt": self.files["wide.srt"]},
                        "tall": {"video": self.files["tall.mp4"], "srt": ""}},
             "description_file": self.files["desc.md"], "description_text": "",
             "platforms": {"youtube": "both", "facebook": "wide", "tiktok": "tall", "linkedin": "wide"},
             "visibility": "public", "language": "vi"}
        f.update(over)
        return f

    def test_security(self):
        self.assertEqual(self.http("/api/state", token="wrong")[0], 403)
        self.assertEqual(self.http("/api/state", host="evil.example")[0], 403)
        code, page = self.http("/?t=" + self.srv["url"].split("?t=")[1])
        self.assertEqual(code, 200)
        self.assertIn("<title>Post video</title>", page)

    def test_validation(self):
        code, data = self.http("/api/submit", self.form(videos={"wide": {"video": "/nope.mp4"}, "tall": {}}, platforms={}))
        self.assertEqual(code, 400)
        self.assertEqual(len(data["errors"]), 2)  # file not found, no platform ticked
        self.assertEqual(self.http("/api/state")[1]["phase"], "form")

    def test_pick(self):
        self.assertEqual(self.http("/api/pick", {"kind": "video"})[1], {"path": "/picked/file.mp4"})
        self.assertEqual(self.http("/api/pick", {"kind": "exe"})[0], 400)

    def test_full_flow(self):
        self.assertEqual(self.cli("wait", "submit", "--timeout", "0.2"), {"waiting": True})
        self.assertEqual(self.http("/api/submit", self.form())[0], 200)
        submit = self.cli("wait", "submit")
        self.assertEqual(submit["platforms"]["youtube"], "both")
        self.assertEqual(self.http("/api/state")[1]["phase"], "preparing")

        post = os.path.join(self.state, "post.json")
        with open(post, "w", encoding="utf-8") as f:
            json.dump({"title": "Tiêu đề", "description": "Mô tả", "tags": ["một", "hai", "ba"],
                       "written_by_claude": ["tags"], "notes": ["Check me"]}, f)
        preview = os.path.join(self.state, "preview.json")
        out = subprocess.run([sys.executable, os.path.join(S, "prepare.py"), os.path.join(self.state, "submit.json"),
                              post, "--out", preview], capture_output=True, text=True, env=self.env)
        self.assertEqual(out.returncode, 0, out.stderr)
        with open(preview, encoding="utf-8") as f:
            pv = json.load(f)
        self.assertEqual([p["id"] for p in pv["posts"]],
                         ["youtube-wide", "youtube-tall", "facebook-wide", "tiktok-tall", "linkedin-wide"])
        by = {p["id"]: p for p in pv["posts"]}
        self.assertTrue(by["youtube-wide"]["captions"]["ok"])
        self.assertFalse(by["youtube-tall"]["captions"]["ok"])  # no SRT for 9:16
        self.assertTrue(by["facebook-wide"]["srt_file"].endswith("wide.vi_VN.srt"))
        self.assertIsNone(by["tiktok-tall"]["srt_file"])
        self.assertIn("Check me", pv["warnings"])
        self.assertTrue(next(f for f in by["youtube-wide"]["fields"] if f["key"] == "tags")["by_claude"])

        self.cli("preview", preview)
        self.assertEqual(self.http("/api/state")[1]["phase"], "preview")

        # over the limit is refused, nothing is approved
        code, data = self.http("/api/decision", {"action": "post", "posts": [{"id": "youtube-wide", "fields": {"title": "x" * 101}}]})
        self.assertEqual(code, 400)
        self.assertEqual(self.cli("wait", "decision", "--timeout", "0.2"), {"waiting": True})

        code, _ = self.http("/api/decision", {"action": "post", "posts": [{"id": "youtube-wide", "fields": {"title": "Edited title"}}]})
        self.assertEqual(code, 200)
        decision = self.cli("wait", "decision")
        self.assertEqual(decision["action"], "post")
        self.assertEqual(len(decision["posts"]), 5)
        self.assertEqual(decision["posts"][0]["fields"][0]["value"], "Edited title")
        self.assertEqual(decision["posts"][1]["fields"][0]["value"], "Tiêu đề")  # untouched

        self.cli("progress", "youtube-wide", "posted", "--link", "https://youtu.be/x")
        state = self.http("/api/state")[1]
        self.assertEqual(state["phase"], "posting")
        self.assertEqual(state["progress"]["youtube-wide"], {"status": "posted", "link": "https://youtu.be/x"})
        self.cli("done")
        self.assertEqual(self.http("/api/state")[1]["phase"], "done")

    def test_back_and_cancel(self):
        self.http("/api/submit", self.form())
        self.cli("wait", "submit")
        self.http("/api/preview", {"warnings": [], "posts": []})
        self.http("/api/decision", {"action": "back"})
        self.assertEqual(self.cli("wait", "decision"), {"action": "back"})
        state = self.http("/api/state")[1]
        self.assertEqual(state["phase"], "form")
        self.assertEqual(state["form"]["videos"]["wide"]["video"], self.files["wide.mp4"])  # form is refilled
        self.assertEqual(self.cli("wait", "submit", "--timeout", "0.2"), {"waiting": True})
        self.http("/api/decision", {"action": "cancel"})
        self.assertEqual(self.cli("wait", "submit"), {"action": "cancel"})

    def test_fallback_shape(self):
        form = self.form(videos={"wide": {"video": self.files["wide.mp4"], "srt": ""}, "tall": {"video": "", "srt": ""}},
                         platforms={"youtube": "both", "tiktok": "tall"})
        self.http("/api/submit", form)
        sys.path.insert(0, S)
        import prepare
        pv = prepare.prepare(self.cli("wait", "submit"), {"title": "t", "description": "d", "tags": []}, self.state)
        self.assertEqual([p["id"] for p in pv["posts"]], ["youtube-wide", "tiktok-wide"])
        self.assertEqual(len([w for w in pv["warnings"] if "TikTok" in w or "YouTube" in w]), 3)


if __name__ == "__main__":
    unittest.main()
