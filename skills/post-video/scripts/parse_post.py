#!/usr/bin/env python3
"""Read a description file written in the video-poster structure into post.json.

Usage:  parse_post.py FILE [--out post.json]

The structure is described in skills/description-file/SKILL.md, in two forms with the same
content: Markdown, marked by the line  <!-- video-poster: v1 -->  , and JSON, an object with
"video_poster": 1 (written by tools such as the make-video skill). Anything else prints
{"structured": false} and Claude turns the text into post.json by hand instead.

Prints {"structured": true, "post": {...}, "files": {...}, "settings": {...}, "problems": [...]}.
"""
import argparse
import json
import os
import re
import sys

MARKER = re.compile(r"<!--\s*video-poster:\s*v1\s*-->", re.I)
PLATFORM_KEYS = {
    "youtube": "youtube", "youtube short": "youtube_short", "youtube shorts": "youtube_short",
    "facebook": "facebook", "facebook reel": "facebook_reel", "facebook reels": "facebook_reel",
    "tiktok": "tiktok", "linkedin": "linkedin",
}
FIELD_KEYS = {"title": "title", "description": "description", "caption": "description", "text": "description",
              "tags": "tags", "hashtags": "tags", "first comment": "first_comment"}
FILE_KEYS = {
    "wide video": ("wide", "video"), "wide srt": ("wide", "srt"), "wide thumbnail": ("wide", "thumbnail"),
    "tall video": ("tall", "video"), "tall srt": ("tall", "srt"), "tall thumbnail": ("tall", "thumbnail"),
}


def norm(s):
    return re.sub(r"\s+", " ", s.strip().lower())


def tags_of(text):
    parts = re.split(r"[,\n]", text)
    out = []
    for p in parts:
        p = p.strip().lstrip("-•*").strip()
        for t in (p.split() if p.count("#") > 1 else [p]):
            t = t.strip().lstrip("#").strip()
            if t:
                out.append(t)
    return out


def pairs_of(text):
    """'- Key: value' lines → {key: value}."""
    out = {}
    for line in text.splitlines():
        m = re.match(r"\s*[-•*]?\s*([^:]+):\s*(.*)$", line)
        if m and m.group(2).strip():
            out[norm(m.group(1))] = m.group(2).strip().strip("`")
    return out


PLATFORMS = ("youtube", "facebook", "tiktok", "linkedin")
OVERRIDE_KEYS = sorted(set(PLATFORM_KEYS.values()))
TEXT_FIELDS = ("title", "description", "first_comment")
JSON_KEYS = ("video_poster", "title", "description", "tags", "first_comment", "overrides", "files", "settings")


def resolve(value, base_dir):
    path = os.path.expanduser(value)
    return os.path.abspath(path if os.path.isabs(path) else os.path.join(base_dir, path))


def parse_json(data, base_dir="."):
    """The JSON form: the same content as the Markdown form, as one object."""
    problems, post = [], {"title": "", "description": "", "tags": [], "overrides": {}}
    files, settings = {"wide": {}, "tall": {}}, {}

    def fields(src, target, where):
        for key, value in src.items():
            if key in TEXT_FIELDS:
                if isinstance(value, str):
                    target[key] = value.replace("\r\n", "\n").strip()
                else:
                    problems.append(f"{where}{key} must be text")
            elif key == "tags":
                if isinstance(value, str):
                    target[key] = tags_of(value)
                elif isinstance(value, list) and all(isinstance(t, str) for t in value):
                    target[key] = tags_of("\n".join(value))
                else:
                    problems.append(f"{where}tags must be a list of words")
            elif where:
                problems.append(f"{where}unknown key '{key}'")

    fields({k: v for k, v in data.items() if k in TEXT_FIELDS + ("tags",)}, post, "")
    for key in data:
        if key not in JSON_KEYS:
            problems.append(f"Unknown key '{key}' was ignored")

    overrides = data.get("overrides") or {}
    if not isinstance(overrides, dict):
        problems.append("overrides must be an object")
        overrides = {}
    for name, body in overrides.items():
        key = PLATFORM_KEYS.get(norm(str(name)).replace("_", " "))
        if not key or not isinstance(body, dict):
            problems.append(f"overrides: unknown platform '{name}' (use {', '.join(OVERRIDE_KEYS)})")
            continue
        post["overrides"][key] = {}
        fields(body, post["overrides"][key], f"overrides.{key}: ")

    given = data.get("files") or {}
    if not isinstance(given, dict):
        problems.append("files must be an object")
        given = {}
    for shape, slot in given.items():
        if shape not in files or not isinstance(slot, dict):
            problems.append(f"files: unknown shape '{shape}' (use wide, tall)")
            continue
        for kind, value in slot.items():
            if kind not in ("video", "srt", "thumbnail"):
                problems.append(f"files.{shape}: unknown key '{kind}'")
            elif isinstance(value, str) and value.strip():
                files[shape][kind] = resolve(value.strip(), base_dir)
                if not os.path.isfile(files[shape][kind]):
                    problems.append(f"Files: {shape} {kind} not found: {value}")

    given = data.get("settings") or {}
    if not isinstance(given, dict):
        problems.append("settings must be an object")
        given = {}
    for key, value in given.items():
        if key == "platforms":
            names = re.split(r"[,\s]+", value) if isinstance(value, str) else value
            settings["platforms"] = [norm(str(p)) for p in names or [] if str(p).strip()]
            bad = [p for p in settings["platforms"] if p not in PLATFORMS]
            if bad:
                problems.append(f"Settings: unknown platform {', '.join(bad)}")
        elif key in ("language", "visibility"):
            if value:
                settings[key] = norm(str(value))
        else:
            problems.append(f"Settings: unknown key '{key}'")

    return finish(post, files, settings, problems)


def finish(post, files, settings, problems):
    if settings.get("language"):
        post["language"] = settings["language"]
    post["overrides"] = {k: v for k, v in post["overrides"].items() if v}
    if not post["title"]:
        problems.append("No title")
    if not post["description"]:
        problems.append("No description text")
    files = {s: f for s, f in files.items() if f}
    return {"structured": True, "post": post, "files": files, "settings": settings, "problems": problems}


def parse(text, base_dir="."):
    if text.lstrip().startswith("{"):
        try:
            data = json.loads(text)
        except ValueError:
            data = None
        if isinstance(data, dict) and data.get("video_poster") == 1:
            return parse_json(data, base_dir)
        return {"structured": False}
    if not MARKER.search(text):
        return {"structured": False}
    text = MARKER.sub("", text.replace("\r\n", "\n"))
    problems, post = [], {"title": "", "description": "", "tags": [], "overrides": {}}
    files, settings = {"wide": {}, "tall": {}}, {}

    # split into (level, heading, body)
    blocks, cur = [], [0, "", []]
    for line in text.split("\n"):
        m = re.match(r"(#{1,3})\s+(.*?)\s*#*\s*$", line)
        if m:
            blocks.append(cur)
            cur = [len(m.group(1)), m.group(2), []]
        else:
            cur[2].append(line)
    blocks.append(cur)

    def setfield(target, key, body):
        target[key] = tags_of(body) if key == "tags" else body

    section = None  # current ## section key: None (main), a platform key, or "skip"
    for level, heading, lines in blocks:
        body = "\n".join(lines).strip()
        h = norm(heading)
        if level == 1:
            post["title"], post["description"], section = heading.strip(), body, None
        elif level == 2:
            if h in PLATFORM_KEYS:
                section = PLATFORM_KEYS[h]
                post["overrides"].setdefault(section, {})
                if body:
                    post["overrides"][section]["description"] = body
            elif h in FIELD_KEYS:
                section = None
                setfield(post, FIELD_KEYS[h], body)
            elif h == "files":
                section = "skip"
                for key, value in pairs_of(body).items():
                    if key in FILE_KEYS:
                        shape, kind = FILE_KEYS[key]
                        files[shape][kind] = resolve(value, base_dir)
                        if not os.path.isfile(files[shape][kind]):
                            problems.append(f"Files: {key} not found: {value}")
                    else:
                        problems.append(f"Files: unknown line '{key}'")
            elif h == "settings":
                section = "skip"
                for key, value in pairs_of(body).items():
                    if key == "platforms":
                        settings["platforms"] = [norm(p) for p in re.split(r"[,\s]+", value) if p]
                        bad = [p for p in settings["platforms"] if p not in PLATFORMS]
                        if bad:
                            problems.append(f"Settings: unknown platform {', '.join(bad)}")
                    elif key in ("language", "visibility"):
                        settings[key] = norm(value)
                    else:
                        problems.append(f"Settings: unknown line '{key}'")
            else:
                section = "skip"
                problems.append(f"Unknown section '## {heading}' was ignored")
        elif level == 3:
            if section in (None, "skip") or h not in FIELD_KEYS:
                problems.append(f"'### {heading}' is not inside a platform section, or is not Title / Description / Tags / First comment")
            else:
                setfield(post["overrides"][section], FIELD_KEYS[h], body)

    return finish(post, files, settings, problems)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("file")
    ap.add_argument("--out")
    a = ap.parse_args()
    with open(a.file, encoding="utf-8-sig") as f:
        res = parse(f.read(), os.path.dirname(os.path.abspath(a.file)))
    if res["structured"] and a.out:
        with open(a.out, "w", encoding="utf-8") as f:
            json.dump(res["post"], f, ensure_ascii=False, indent=2)
    print(json.dumps(res, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
