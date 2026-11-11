#!/usr/bin/env python3
"""Turn one clean post.json into the exact text each platform accepts.

Usage:  build_post.py post.json [--platforms youtube,facebook,tiktok,linkedin] [--out post.ready.json]

post.json (written by Claude from whatever the user gave):
{
  "title": "...",                 # required
  "description": "...",           # required, plain text, \n for new lines
  "tags": ["ai agent", "..."],    # plain words, no '#'
  "language": "vi",               # caption language, e.g. vi, en
  "overrides": {                  # optional, per platform: youtube, youtube_short,
    "tiktok": {"description": "shorter text", "tags": ["..."]}   # facebook, facebook_reel, tiktok, linkedin
  },
  "written_by_claude": ["title", "tags"],   # optional: parts the user did not give
  "notes": ["..."]                          # optional: things the user should check
}

Prints the result as JSON: per platform the fields to type in, plus warnings.
Exit code 1 when a required field is missing.
"""
import argparse
import json
import re
import sys
import unicodedata

PLATFORMS = ["youtube", "facebook", "tiktok", "linkedin"]

LIMITS = {
    "youtube": {"title": 100, "text": 5000, "tags_chars": 500, "hashtags": 3},
    "facebook": {"text": 5000, "hashtags": 8},
    "tiktok": {"text": 2200, "hashtags": 5},
    "linkedin": {"text": 3000, "hashtags": 5},
}


def clean_text(s):
    s = unicodedata.normalize("NFC", s or "")
    s = s.replace("\r\n", "\n").replace("\r", "\n")
    s = "\n".join(line.rstrip() for line in s.split("\n"))
    s = re.sub(r"\n{3,}", "\n\n", s)
    return s.strip()


def clean_tags(tags):
    out, seen = [], set()
    for t in tags or []:
        t = unicodedata.normalize("NFC", str(t)).strip().lstrip("#").strip()
        t = re.sub(r"\s+", " ", t)
        if t and t.lower() not in seen:
            seen.add(t.lower())
            out.append(t)
    return out


def hashtag(tag):
    # Letters (with accents), digits and underscore only; spaces removed.
    return "#" + "".join(ch for ch in tag if ch.isalnum() or ch == "_")


def hashtags(tags, n):
    out = []
    for t in tags:
        h = hashtag(t)
        if len(h) > 1 and h.lower() not in [x.lower() for x in out]:
            out.append(h)
    return out[:n]


def cut(text, limit, warnings, what):
    if len(text) <= limit:
        return text
    warnings.append(f"{what} was {len(text)} characters, cut to {limit}")
    short = text[: limit - 1]
    if " " in short[-40:]:
        short = short[: short.rstrip().rfind(" ")]
    return short.rstrip() + "…"


def with_hashtags(body, tags, limit, warnings, what):
    tail = " ".join(tags)
    room = limit - (len(tail) + 2 if tail else 0)
    body = cut(body, room, warnings, what)
    return f"{body}\n\n{tail}" if tail else body


def youtube_tags(tags, limit, warnings):
    kept, used = [], 0
    for t in tags:
        t = t.replace("<", "").replace(">", "").replace(",", " ")
        cost = len(t) + (2 if " " in t else 0) + (1 if kept else 0)
        if used + cost > limit:
            warnings.append(f"YouTube tags over {limit} characters, dropped from '{t}' on")
            break
        kept.append(t)
        used += cost
    return kept


def build(post, platform, variant=None):
    """Text for one upload. `variant` (youtube_short, facebook_reel) may have its own overrides."""
    w = []
    ov = post.get("overrides") or {}
    o = dict(ov.get(platform, {}), **ov.get(variant or "", {}))
    title = clean_text(o.get("title", post.get("title", "")))
    desc = clean_text(o.get("description", post.get("description", "")))
    tags = clean_tags(o.get("tags", post.get("tags", [])))
    lim = LIMITS[platform]
    tags_h = hashtags(tags, lim["hashtags"])
    if len(tags_h) < min(3, len(tags)) and platform != "youtube":
        w.append("fewer than 3 usable hashtags")

    if platform == "youtube":
        t = cut(title.replace("<", "").replace(">", ""), lim["title"], w, "YouTube title")
        d = desc.replace("<", "‹").replace(">", "›")
        return {
            "title": t,
            "description": with_hashtags(d, tags_h, lim["text"], w, "YouTube description"),
            "tags": youtube_tags(tags, lim["tags_chars"], w),
            "warnings": w,
        }
    if platform == "tiktok":
        # No title field: the first line is the hook.
        body = title if desc.startswith(title) or not desc else f"{title}\n\n{desc}"
        return {"caption": with_hashtags(body, tags_h, lim["text"], w, "TikTok caption"), "warnings": w}
    # facebook, linkedin: one text box
    body = f"{title}\n\n{desc}" if desc and not desc.startswith(title) else (desc or title)
    out = {"text": with_hashtags(body, tags_h, lim["text"], w, f"{platform} text"), "warnings": w}
    if platform == "facebook":
        out["title"] = cut(title, 255, w, "Facebook title")
    if platform == "linkedin":
        out["video_title"] = cut(title, 150, w, "LinkedIn video title")
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("post")
    ap.add_argument("--platforms", default=",".join(PLATFORMS))
    ap.add_argument("--out")
    a = ap.parse_args()

    with open(a.post, encoding="utf-8-sig") as f:
        post = json.load(f)
    missing = [k for k in ("title", "description") if not str(post.get(k, "")).strip()]
    if missing:
        print(json.dumps({"error": f"post.json is missing: {', '.join(missing)}"}))
        sys.exit(1)
    wanted = [p.strip().lower() for p in a.platforms.split(",") if p.strip()]
    bad = [p for p in wanted if p not in PLATFORMS]
    if bad:
        print(json.dumps({"error": f"unknown platform: {', '.join(bad)}"}))
        sys.exit(1)

    result = {"language": post.get("language", ""), "platforms": {p: build(post, p) for p in wanted}}
    text = json.dumps(result, ensure_ascii=False, indent=2)
    if a.out:
        with open(a.out, "w", encoding="utf-8") as f:
            f.write(text + "\n")
    print(text)


if __name__ == "__main__":
    main()
