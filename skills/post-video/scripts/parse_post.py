#!/usr/bin/env python3
"""Read a description file written in the video-poster structure into post.json.

Usage:  parse_post.py FILE [--out post.json]

The structure is described in skills/description-file/SKILL.md. A file counts as structured
only when it carries the marker line  <!-- video-poster: v1 -->  ; anything else prints
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


def parse(text, base_dir="."):
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
                        path = value if os.path.isabs(os.path.expanduser(value)) else os.path.join(base_dir, value)
                        files[shape][kind] = os.path.abspath(os.path.expanduser(path))
                        if not os.path.isfile(files[shape][kind]):
                            problems.append(f"Files: {key} not found: {value}")
                    else:
                        problems.append(f"Files: unknown line '{key}'")
            elif h == "settings":
                section = "skip"
                for key, value in pairs_of(body).items():
                    if key == "platforms":
                        settings["platforms"] = [norm(p) for p in re.split(r"[,\s]+", value) if p]
                        bad = [p for p in settings["platforms"] if p not in ("youtube", "facebook", "tiktok", "linkedin")]
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

    if settings.get("language"):
        post["language"] = settings["language"]
    post["overrides"] = {k: v for k, v in post["overrides"].items() if v}
    if not post["title"]:
        problems.append("No '# Title' line")
    if not post["description"]:
        problems.append("No description text under the title")
    files = {s: f for s, f in files.items() if f}
    return {"structured": True, "post": post, "files": files, "settings": settings, "problems": problems}


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
