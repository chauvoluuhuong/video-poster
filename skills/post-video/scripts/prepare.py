#!/usr/bin/env python3
"""Turn the submitted form + post.json into the list of uploads the preview page shows.

Usage:  prepare.py submit.json post.json --out preview.json [--work DIR]

For every upload it: picks the video (16:9 or 9:16), builds the text with build_post,
cleans the SRT with check_srt into --work (default: the folder of --out), reads the video's
length and size with ffprobe when it is installed, and collects things the user should check.
Translations in post.json ("subtitles": extra SRT per shape and language, "translations": a title and
description per language) go to the uploads whose platform takes them (SUPPORTS); the others get
a line saying they were skipped.
Prints {"posts": N, "warnings": N}; the full result is in --out.
"""
import argparse
import json
import os
import shutil
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import build_post  # noqa: E402
import check_srt  # noqa: E402

NAMES = {"youtube": "YouTube", "facebook": "Facebook", "tiktok": "TikTok", "linkedin": "LinkedIn"}
SHAPE = {"wide": "16:9", "tall": "9:16"}
KIND = {
    ("youtube", "wide"): "Video 16:9", ("youtube", "tall"): "Short 9:16",
    ("facebook", "wide"): "Video 16:9", ("facebook", "tall"): "Reel 9:16",
    ("tiktok", "wide"): "16:9", ("tiktok", "tall"): "9:16",
    ("linkedin", "wide"): "16:9", ("linkedin", "tall"): "9:16",
}
VARIANT = {("youtube", "tall"): "youtube_short", ("facebook", "tall"): "facebook_reel"}
VISIBILITY = {
    "youtube": {"public": "Public", "private": "Private", "unlisted": "Unlisted"},
    "facebook": {"public": "Public", "private": "Only me", "unlisted": "Only me"},
    "tiktok": {"public": "Everyone", "private": "Only you", "unlisted": "Only you"},
    "linkedin": {"public": "Anyone", "private": "Connections only", "unlisted": "Connections only"},
}
AI_INFO = {  # what the AI label sets on each site, when on / off
    "youtube": {"on": "“Altered or synthetic content” → Yes", "off": "“Altered or synthetic content” → No"},
    "tiktok": {"on": "“AI-generated content” switch on", "off": "“AI-generated content” switch off"},
    "facebook": {"on": "AI label (“AI info”) where the composer offers it", "off": "no AI label"},
    "linkedin": {"on": "LinkedIn has no AI label on the web: posted without one", "off": "no AI label"},
}
LOCALES = {"vi": "vi_VN", "en": "en_US", "ja": "ja_JP", "ko": "ko_KR", "zh": "zh_CN", "fr": "fr_FR",
           "de": "de_DE", "es": "es_ES", "pt": "pt_BR", "id": "id_ID", "th": "th_TH"}
LIM = build_post.LIMITS
# What each upload can take besides its main SRT: extra subtitle languages, a translated title/description.
SUPPORTS = {
    ("youtube", "wide"): (True, True), ("youtube", "tall"): (True, True),
    ("facebook", "wide"): (True, False), ("facebook", "tall"): (False, False),
    ("linkedin", "wide"): (False, False), ("linkedin", "tall"): (False, False),
    ("tiktok", "wide"): (False, False), ("tiktok", "tall"): (False, False),
}
NO_EXTRA = {"facebook": "Reels take no extra caption files", "linkedin": "LinkedIn takes one caption file",
            "tiktok": "TikTok takes no caption files"}


def locale_of(lang):
    return LOCALES.get(lang.split("-")[0].split("_")[0].lower())


def translated(body, warnings, lang):
    """A translated title/description, cleaned and kept within YouTube's limits."""
    out = {}
    if body.get("title"):
        out["title"] = build_post.cut(build_post.clean_text(body["title"]).replace("<", "").replace(">", ""),
                                      LIM["youtube"]["title"], warnings, f"YouTube title ({lang})")
    if body.get("description"):
        out["description"] = build_post.cut(build_post.clean_text(body["description"]).replace("<", "‹").replace(">", "›"),
                                            LIM["youtube"]["text"], warnings, f"YouTube description ({lang})")
    return out


def probe(path):
    """Length and size of a video, or {} when ffprobe is missing or fails."""
    if not shutil.which("ffprobe"):
        return {}
    try:
        out = subprocess.run(
            ["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries",
             "stream=width,height:format=duration", "-of", "json", path],
            capture_output=True, text=True, timeout=30)
        data = json.loads(out.stdout or "{}")
        st = (data.get("streams") or [{}])[0]
        return {"seconds": float(data["format"]["duration"]), "width": int(st["width"]), "height": int(st["height"])}
    except (KeyError, ValueError, IndexError, OSError, subprocess.SubprocessError):
        return {}


def clock(seconds):
    m, s = divmod(int(round(seconds)), 60)
    h, m = divmod(m, 60)
    return f"{h}:{m:02}:{s:02}" if h else f"{m}:{s:02}"


def fields_for(platform, built, by_claude):
    def f(key, label, value, limit, multiline, required=True):
        return {"key": key, "label": label, "value": value, "limit": limit, "multiline": multiline,
                "required": required, "by_claude": key in by_claude}
    comment = f("first_comment", "First comment (optional, added after the video is posted)", built["first_comment"],
                LIM[platform]["comment"], True, False)
    if platform == "youtube":
        return [f("title", "Title", built["title"], LIM["youtube"]["title"], False),
                f("description", "Description", built["description"], LIM["youtube"]["text"], True, False),
                f("tags", "Tags (comma separated)", ", ".join(built["tags"]), LIM["youtube"]["tags_chars"], False, False), comment]
    if platform == "tiktok":
        return [f("caption", "Caption", built["caption"], LIM["tiktok"]["text"], True), comment]
    return [f("text", "Text", built["text"], LIM[platform]["text"], True), comment]


def prepare(form, post, work):
    os.makedirs(work, exist_ok=True)
    warnings = list(post.get("notes") or [])
    written = set(post.get("written_by_claude") or [])
    by_claude = written | ({"description", "caption", "text"} if "description" in written else set())
    if "title" in written:
        by_claude |= {"title"}
    videos = {s: v for s, v in form["videos"].items() if v.get("video")}
    info = {s: probe(v["video"]) for s, v in videos.items()}
    lang = form.get("language") or post.get("language") or "en"
    locale = LOCALES.get(lang.split("-")[0].split("_")[0].lower())

    for s, i in info.items():
        if i and (i["width"] > i["height"]) != (s == "wide"):
            warnings.append(f"The file in the {SHAPE[s]} slot is {i['width']}×{i['height']}: it does not look {SHAPE[s]}.")

    srt = {}
    for s, v in videos.items():
        if not v.get("srt"):
            continue
        stem = os.path.splitext(os.path.basename(v["video"]))[0]
        res = check_srt.clean(v["srt"], os.path.join(work, f"{stem}.clean.srt"),
                              facebook_locale=locale if "facebook" in form["platforms"] else None, video=v["video"])
        if not res["ok"]:
            warnings.append(f"The {SHAPE[s]} SRT could not be read ({res['error']}): posting without captions.")
            continue
        srt[s] = res
        if res["problems"]:
            warnings.append(f"The {SHAPE[s]} SRT has {len(res['problems'])} timing problem(s), e.g. {res['problems'][0]}.")
        if info[s] and res["ends_ms"] / 1000 > info[s]["seconds"] + 5:
            warnings.append(f"The {SHAPE[s]} SRT runs to {res['ends_at']} but the video is {clock(info[s]['seconds'])} long: "
                            "is it the caption file of another cut?")
    if "facebook" in form["platforms"] and srt and not locale:
        warnings.append(f"Facebook needs a locale for caption language '{lang}' and none is known: Facebook posts without captions.")

    extra = {}  # shape -> [{language, file, facebook_file?}]
    for s, langs in (post.get("subtitles") or {}).items():
        if s not in videos:
            continue
        stem = os.path.splitext(os.path.basename(videos[s]["video"]))[0]
        for code, path in langs.items():
            fb = locale_of(code) if "facebook" in form["platforms"] and s == "wide" else None
            res = check_srt.clean(path, os.path.join(work, f"{stem}.{code}.clean.srt"), facebook_locale=fb, video=videos[s]["video"])
            if not res["ok"]:
                warnings.append(f"The {SHAPE[s]} {code} SRT could not be read ({res['error']}): posting without it.")
                continue
            if res["problems"]:
                warnings.append(f"The {SHAPE[s]} {code} SRT has {len(res['problems'])} timing problem(s), e.g. {res['problems'][0]}.")
            if info[s] and res["ends_ms"] / 1000 > info[s]["seconds"] + 5:
                warnings.append(f"The {SHAPE[s]} {code} SRT runs to {res['ends_at']} but the video is {clock(info[s]['seconds'])} long: "
                                "is it the caption file of another cut?")
            extra.setdefault(s, []).append({"language": code, "file": res["clean_file"], "facebook_file": res.get("facebook_file"),
                                            "cues": res["cues"]})
    titles = {code: translated(body, warnings, code) for code, body in (post.get("translations") or {}).items()}
    titles = {code: body for code, body in titles.items() if body}

    posts = []
    for platform in build_post.PLATFORMS:
        choice = form["platforms"].get(platform)
        if not choice:
            continue
        wanted = ["wide", "tall"] if choice == "both" else [choice]
        shapes = [s for s in wanted if s in videos]
        if not shapes:
            other = "tall" if wanted[0] == "wide" else "wide"
            if other in videos:
                shapes = [other]
                warnings.append(f"{NAMES[platform]}: no {SHAPE[wanted[0]]} video was chosen, so the {SHAPE[other]} one is used.")
        elif choice == "both" and len(shapes) == 1:
            warnings.append(f"{NAMES[platform]}: only the {SHAPE[shapes[0]]} video was chosen, so there is one upload, not two.")

        for s in shapes:
            v, i = videos[s], info[s]
            built = build_post.build(post, platform, VARIANT.get((platform, s)))
            for w in built["warnings"]:
                warnings.append(f"{NAMES[platform]} {KIND[(platform, s)]}: {w}. Shorten it in the box below.")
            name = os.path.basename(v["video"])
            meta = " · ".join([name] + ([clock(i["seconds"]), f"{i['width']}×{i['height']}"] if i else []))

            cap = srt.get(s)
            if platform == "tiktok":
                captions = {"ok": False, "text": "TikTok has no SRT upload: its auto captions will be turned on"}
                srt_file = None
            elif not cap:
                captions = {"ok": False, "text": f"No captions (no SRT for the {SHAPE[s]} video)"}
                srt_file = None
            elif platform == "facebook":
                srt_file = cap.get("facebook_file")
                captions = ({"ok": True, "text": f"Captions: {os.path.basename(srt_file)} (renamed for Facebook) · {cap['cues']} lines"}
                            if srt_file else {"ok": False, "text": "No captions (unknown caption locale for Facebook)"})
                if srt_file and s == "tall":
                    captions["text"] += " · Reels may only offer auto captions"
            else:
                srt_file = cap["clean_file"]
                captions = {"ok": True, "text": f"Captions: {os.path.basename(v['srt'])} · {cap['cues']} lines · {lang}"}

            takes_srt, takes_text = SUPPORTS[(platform, s)]
            extra_srt, skipped = [], []
            for t in extra.get(s, []):
                f = t["facebook_file"] if platform == "facebook" else t["file"]
                if takes_srt and f:
                    extra_srt.append({"language": t["language"], "file": f})
                else:
                    skipped.append(t["language"])
            if extra_srt:
                names = ", ".join(f"{t['language']} ({os.path.basename(t['file'])})" for t in extra_srt)
                captions["text"] += f" · also subtitles: {names}"
            if skipped:
                why = NO_EXTRA[platform] if not takes_srt else "no locale known for Facebook"
                captions["text"] += f" · {', '.join(skipped)} subtitles skipped: {why}"
            post_titles = titles if takes_text else {}
            translations_info = None
            if post_titles:
                translations_info = {"ok": True, "text": "Translated title and description: " + ", ".join(
                    f"{code} ({' + '.join(body)})" for code, body in post_titles.items())}
            elif titles:
                translations_info = {"ok": False, "text": f"{NAMES[platform]} has no translated title or description: skipped "
                                                          + ", ".join(titles)}

            thumb = v.get("thumbnail") or None
            if not thumb:
                thumbnail_info = None
            elif platform == "youtube" and s == "tall":
                thumb, thumbnail_info = None, {"ok": False, "text": "Thumbnail skipped: YouTube Shorts take no custom thumbnail on the web"}
            else:
                word = "Cover" if (platform == "tiktok" or (platform == "facebook" and s == "tall")) else "Thumbnail"
                thumbnail_info = {"ok": True, "text": f"{word}: {os.path.basename(thumb)}"}
                if platform == "youtube" and os.path.getsize(thumb) > 2 * 1024 * 1024:
                    warnings.append(f"YouTube thumbnails must be under 2 MB; {os.path.basename(thumb)} is larger.")

            if i:
                if platform == "youtube" and s == "tall" and i["seconds"] > 180:
                    warnings.append(f"YouTube: the 9:16 video is {clock(i['seconds'])}; over 3:00 it is a normal video, not a Short.")
                if platform == "linkedin" and i["seconds"] > 900:
                    warnings.append(f"LinkedIn accepts at most 15:00; this video is {clock(i['seconds'])}.")
                if platform == "facebook" and s == "tall" and i["seconds"] > 90:
                    warnings.append(f"Facebook: the 9:16 video is {clock(i['seconds'])}; over 1:30 it may post as a normal video, not a Reel.")
            if platform == "tiktok" and s == "wide":
                warnings.append("TikTok: a 16:9 video shows small on phones.")

            posts.append({
                "id": f"{platform}-{s}", "platform": NAMES[platform], "key": platform, "shape": s,
                "badges": [KIND[(platform, s)], VISIBILITY[platform][form.get("visibility", "public")]],
                "visibility": form.get("visibility", "public"),
                "meta": meta, "video": v["video"], "srt_file": srt_file, "language": lang,
                "captions": captions, "thumbnail": thumb, "thumbnail_info": thumbnail_info,
                "extra_srt": extra_srt, "translations": post_titles, "translations_info": translations_info,
                "fields": fields_for(platform, built, by_claude),
                "ai_label": form.get("ai_label") is True, "ai_info": AI_INFO[platform],
            })

    if form.get("ai_label") is True and any(p["key"] == "linkedin" for p in posts):
        warnings.append("AI label: LinkedIn has no such option on the web, so the LinkedIn post goes out without one.")
    if form.get("visibility") == "unlisted" and any(p["key"] != "youtube" for p in posts):
        warnings.append("Unlisted exists only on YouTube: the other platforms post as private / connections only.")
    if form.get("visibility") == "private" and any(p["key"] == "linkedin" for p in posts):
        warnings.append("LinkedIn has no private posts: it posts to connections only.")
    seen, unique = set(), []
    for w in warnings:
        if w not in seen:
            seen.add(w)
            unique.append(w)
    return {"warnings": unique, "posts": posts}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("submit")
    ap.add_argument("post")
    ap.add_argument("--out", required=True)
    ap.add_argument("--work")
    a = ap.parse_args()
    with open(a.submit, encoding="utf-8") as f:
        form = json.load(f)
    with open(a.post, encoding="utf-8-sig") as f:
        post = json.load(f)
    missing = [k for k in ("title", "description") if not str(post.get(k, "")).strip()]
    if missing:
        print(json.dumps({"error": f"post.json is missing: {', '.join(missing)}"}))
        sys.exit(1)
    result = prepare(form, post, a.work or os.path.dirname(os.path.abspath(a.out)))
    with open(a.out, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)
    print(json.dumps({"posts": len(result["posts"]), "warnings": len(result["warnings"]), "out": os.path.abspath(a.out)}))


if __name__ == "__main__":
    main()
