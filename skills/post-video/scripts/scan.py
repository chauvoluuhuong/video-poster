#!/usr/bin/env python3
"""Find the files for a post in a folder (or among given files) and write prefill.json for the form.

Usage:  scan.py PATH [PATH ...] --out prefill.json

PATH is a folder or a file. The result fills the form's Files screen; the user still checks it
and submits. Rules:
  - A description file in the video-poster structure (Markdown or JSON) that names its files decides
    everything it names.
  - Otherwise: videos are sorted into 16:9 and 9:16 by their real size (ffprobe), or by words in the
    name when ffprobe is missing; images the same way (PNG/JPEG size is read from the file);
    an SRT goes to the video whose name it resembles most; the description file is the .md/.txt file.
  - When several files fit one slot, the newest is taken and the others are listed in "hints",
    which the form shows, so nothing is chosen silently. For thumbnails a name with "thumb" or
    "cover" wins over a newer image.
"""
import argparse
import json
import os
import re
import shutil
import struct
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import parse_post  # noqa: E402

VIDEO = (".mp4", ".mov", ".m4v", ".webm", ".mkv")
IMAGE = (".png", ".jpg", ".jpeg", ".webp")
TEXT = (".md", ".txt")
WIDE_WORDS = ("16x9", "16-9", "16_9", "wide", "ngang", "horizontal", "landscape", "youtube")
TALL_WORDS = ("9x16", "9-16", "9_16", "tall", "doc", "dọc", "vertical", "portrait", "short", "reel", "tiktok")
DESC_WORDS = ("post", "dang-bai", "đăng", "description", "mo-ta", "caption", "upload")


def video_size(path):
    if not shutil.which("ffprobe"):
        return None
    try:
        out = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries",
                              "stream=width,height", "-of", "csv=p=0", path], capture_output=True, text=True, timeout=30)
        w, h = out.stdout.strip().split(",")[:2]
        return int(w), int(h)
    except (ValueError, OSError, subprocess.SubprocessError):
        return None


def image_size(path):
    try:
        with open(path, "rb") as f:
            head = f.read(32)
            if head[:8] == b"\x89PNG\r\n\x1a\n":
                return struct.unpack(">II", head[16:24])
            if head[:2] == b"\xff\xd8":
                f.seek(2)
                while True:
                    marker = f.read(4)
                    if len(marker) < 4 or marker[0] != 0xFF:
                        return None
                    length = struct.unpack(">H", marker[2:4])[0]
                    if 0xC0 <= marker[1] <= 0xCF and marker[1] not in (0xC4, 0xC8, 0xCC):
                        h, w = struct.unpack(">HH", f.read(5)[1:5])
                        return w, h
                    f.seek(length - 2, 1)
    except (OSError, struct.error):
        pass
    return None


def shape_of(path, size):
    if size:
        return "wide" if size[0] >= size[1] else "tall"
    words = re.split(r"[^0-9a-zà-ỹ]+", os.path.basename(path).lower())
    name = os.path.basename(path).lower()
    if any(w in name for w in WIDE_WORDS[:3]) or any(w in words for w in WIDE_WORDS):
        return "wide"
    if any(w in name for w in TALL_WORDS[:3]) or any(w in words for w in TALL_WORDS):
        return "tall"
    return None


def common(a, b):
    a, b = os.path.splitext(os.path.basename(a))[0].lower(), os.path.splitext(os.path.basename(b))[0].lower()
    n = 0
    while n < min(len(a), len(b)) and a[n] == b[n]:
        n += 1
    return n


def scan(paths):
    files = []
    for p in paths:
        p = os.path.abspath(os.path.expanduser(p))
        if os.path.isdir(p):
            files += [os.path.join(p, n) for n in sorted(os.listdir(p)) if not n.startswith(".")]
        elif os.path.isfile(p):
            files.append(p)
    files = [f for f in files if os.path.isfile(f)]
    newest = lambda fs: sorted(fs, key=os.path.getmtime, reverse=True)  # noqa: E731
    hints = []
    out = {"videos": {"wide": {}, "tall": {}}}

    # description file: a structured one wins, then a telling name, then the only text file
    texts = [f for f in files if f.lower().endswith(TEXT) and not os.path.basename(f).lower().startswith("readme")]
    structured = None
    for f in newest(texts + [f for f in files if f.lower().endswith(".json")]):  # .json only when it is structured
        try:
            with open(f, encoding="utf-8-sig") as fh:
                res = parse_post.parse(fh.read(), os.path.dirname(f))
        except (OSError, UnicodeDecodeError):
            continue
        if not res["structured"]:
            continue
        if structured:
            hints.append(f"Description: used {os.path.basename(out['description_file'])}; also found {os.path.basename(f)}"
                         " (give that file instead of the folder to post it)")
            break
        structured, out["description_file"] = res, f
    if not structured and texts:
        named = [f for f in texts if any(w in os.path.basename(f).lower() for w in DESC_WORDS)]
        pick = newest(named or texts)
        out["description_file"] = pick[0]
        if len(pick) > 1:
            hints.append("Description: also found " + ", ".join(os.path.basename(f) for f in pick[1:4]))

    if structured:
        for shape, slot in structured["files"].items():
            out["videos"][shape].update({k: v for k, v in slot.items() if os.path.isfile(v)})
        s = structured["settings"]
        if s.get("platforms"):
            out["platforms"] = {p: None for p in s["platforms"]}
        for key in ("visibility", "language"):
            if s.get(key):
                out[key] = s[key]
        hints += [f"{os.path.basename(out['description_file'])}: {p}" for p in structured["problems"]]

    def fill(kind, exts, sizer, label):
        found = {"wide": [], "tall": [], None: []}
        for f in files:
            if f.lower().endswith(exts):
                found[shape_of(f, sizer(f))].append(f)
        for shape in ("wide", "tall"):
            if out["videos"][shape].get(kind):
                continue  # named in the description file
            cands = newest(found[shape])
            if kind == "thumbnail":  # a file that says it is a thumbnail beats a newer screenshot
                cands.sort(key=lambda f: not any(w in os.path.basename(f).lower() for w in ("thumb", "cover", "poster", "bia", "bìa")))
            if cands:
                out["videos"][shape][kind] = cands[0]
                if len(cands) > 1:
                    hints.append(f"{'16:9' if shape == 'wide' else '9:16'} {label}: used "
                                 f"{os.path.basename(cands[0])}; also found " + ", ".join(os.path.basename(c) for c in cands[1:4]))
        if found[None]:
            hints.append(f"Could not tell 16:9 from 9:16 for: " + ", ".join(os.path.basename(f) for f in found[None][:4]))

    fill("video", VIDEO, video_size, "video")
    fill("thumbnail", IMAGE, image_size, "thumbnail")

    srts = [f for f in files if f.lower().endswith(".srt") and not f.lower().endswith(".clean.srt")]
    taken = {v.get("srt") for v in out["videos"].values()}
    for f in newest(srts):
        if f in taken:
            continue
        open_slots = [s for s in ("wide", "tall") if out["videos"][s].get("video") and not out["videos"][s].get("srt")]
        if not open_slots:
            hints.append(f"SRT not used: {os.path.basename(f)}")
            continue
        best = max(open_slots, key=lambda s: (common(f, out["videos"][s]["video"]), s == "wide"))
        out["videos"][best]["srt"] = f
    for shape in ("wide", "tall"):  # a thumbnail or SRT without its video would be rejected by the form
        if not out["videos"][shape].get("video"):
            for kind in ("srt", "thumbnail"):
                if out["videos"][shape].pop(kind, None):
                    hints.append(f"{'16:9' if shape == 'wide' else '9:16'} {kind} left out: no video of that shape was found")
    if not any(v.get("video") for v in out["videos"].values()):
        hints.append("No video file was found: choose one below.")
    out["hints"] = hints
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("paths", nargs="+")
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    res = scan(a.paths)
    with open(a.out, "w", encoding="utf-8") as f:
        json.dump(res, f, ensure_ascii=False, indent=2)
    print(json.dumps(res, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
