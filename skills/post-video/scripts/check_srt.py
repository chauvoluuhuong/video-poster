#!/usr/bin/env python3
"""Check an SRT caption file and write a clean copy the platforms accept.

Usage:  check_srt.py captions.srt [--out clean.srt] [--facebook-locale vi_VN --video video.mp4]

Fixes: encoding (to UTF-8 without BOM), Windows line ends, '.' instead of ',' in
times, short times (0:01:02,5), wrong or missing numbering, empty cues, cue order.
Reports (does not fix): overlapping cues, cues that end before they start.

--facebook-locale also writes a copy named <video name>.<locale>.srt next to --out,
because Facebook only accepts caption files named like  myvideo.vi_VN.srt
Prints a JSON summary. Exit code 1 when no cue could be read.
"""
import argparse
import json
import os
import re
import shutil
import sys

TIME = r"(\d{1,2}):(\d{1,2}):(\d{1,2})[,.](\d{1,3})"
ARROW = re.compile(TIME + r"\s*-+>\s*" + TIME)


def read_text(path):
    raw = open(path, "rb").read()
    for enc in ("utf-8-sig", "utf-16", "cp1258", "cp1252"):
        try:
            return raw.decode(enc), enc
        except (UnicodeDecodeError, UnicodeError):
            continue
    return raw.decode("utf-8", errors="replace"), "utf-8 (bad bytes replaced)"


def ms(h, m, s, f):
    return ((int(h) * 60 + int(m)) * 60 + int(s)) * 1000 + int(f.ljust(3, "0"))


def stamp(t):
    h, r = divmod(t, 3600000)
    m, r = divmod(r, 60000)
    s, f = divmod(r, 1000)
    return f"{h:02}:{m:02}:{s:02},{f:03}"


def parse(text):
    cues, cur = [], None
    for line in text.replace("\r\n", "\n").replace("\r", "\n").split("\n"):
        m = ARROW.search(line)
        if m:
            g = m.groups()
            if cur and cur["lines"] and re.fullmatch(r"\d+", cur["lines"][-1].strip()):
                cur["lines"].pop()  # that was the next cue's number
            cur = {"start": ms(*g[:4]), "end": ms(*g[4:]), "lines": []}
            cues.append(cur)
        elif cur is not None:
            cur["lines"].append(line.rstrip())
    for c in cues:
        while c["lines"] and not c["lines"][-1].strip():
            c["lines"].pop()
        while c["lines"] and not c["lines"][0].strip():
            c["lines"].pop(0)
    return cues


def clean(srt, out=None, facebook_locale=None, video=None):
    """Write a clean copy of `srt`. Returns the summary dict (ok False when nothing could be read)."""
    text, enc = read_text(srt)
    cues = parse(text)
    problems, fixed = [], []
    if open(srt, "rb").read(3) == b"\xef\xbb\xbf":
        fixed.append("removed BOM")
    elif enc != "utf-8-sig":
        fixed.append(f"encoding {enc} -> utf-8")

    empty = [c for c in cues if not any(l.strip() for l in c["lines"])]
    if empty:
        fixed.append(f"removed {len(empty)} empty cues")
    cues = [c for c in cues if c not in empty]
    if not cues:
        return {"ok": False, "error": "no captions found; is this an SRT file?"}

    if cues != sorted(cues, key=lambda c: c["start"]):
        cues.sort(key=lambda c: c["start"])
        fixed.append("put cues in time order")
    for i, c in enumerate(cues, 1):
        if c["end"] <= c["start"]:
            problems.append(f"cue {i} ends before it starts ({stamp(c['start'])})")
        if i < len(cues) and c["end"] > cues[i]["start"]:
            problems.append(f"cue {i} overlaps cue {i + 1} ({stamp(c['start'])})")

    out = out or os.path.splitext(srt)[0] + ".clean.srt"
    body = "\n\n".join(
        f"{i}\n{stamp(c['start'])} --> {stamp(c['end'])}\n" + "\n".join(c["lines"])
        for i, c in enumerate(cues, 1)
    )
    with open(out, "w", encoding="utf-8", newline="\n") as f:
        f.write(body + "\n")

    res = {
        "ok": True,
        "cues": len(cues),
        "ends_ms": max(c["end"] for c in cues),
        "ends_at": stamp(max(c["end"] for c in cues)),
        "clean_file": os.path.abspath(out),
        "fixed": fixed,
        "problems": problems[:20],
    }
    if facebook_locale:
        if not re.fullmatch(r"[a-z]{2,3}_[A-Z]{2}", facebook_locale):
            res["problems"].append("facebook locale must look like vi_VN or en_US")
        else:
            stem = os.path.splitext(os.path.basename(video or srt))[0]
            fb = os.path.join(os.path.dirname(os.path.abspath(out)), f"{stem}.{facebook_locale}.srt")
            if os.path.abspath(fb) != os.path.abspath(out):
                shutil.copyfile(out, fb)
            res["facebook_file"] = fb
    return res


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("srt")
    ap.add_argument("--out")
    ap.add_argument("--facebook-locale")
    ap.add_argument("--video")
    a = ap.parse_args()
    res = clean(a.srt, a.out, a.facebook_locale, a.video)
    print(json.dumps(res, ensure_ascii=False, indent=2))
    if not res["ok"]:
        sys.exit(1)


if __name__ == "__main__":
    main()
