#!/usr/bin/env python3
"""Small per-platform notes that the next run reads before posting: the latest instructions and errors.

  learn.py show PLATFORM            print the notes (empty when there are none)
  learn.py save PLATFORM --file F   replace the notes with the content of F
  learn.py path PLATFORM            print where the notes are

The file is replaced, never appended to, and is refused when it grows past the limits below, so it
stays a short list of what is true now, not a log. Location: ~/.video-poster/learned/<platform>.md
"""
import argparse
import datetime
import os
import sys

PLATFORMS = ("youtube", "facebook", "tiktok", "linkedin")
MAX_LINES, MAX_CHARS = 40, 4000


def folder():
    return os.path.join(os.path.expanduser("~/.video-poster"), "learned")


def path_of(platform):
    return os.path.join(folder(), f"{platform}.md")


def show(platform):
    try:
        with open(path_of(platform), encoding="utf-8") as f:
            return f.read()
    except OSError:
        return ""


def save(platform, text, today=None):
    body = "\n".join(line.rstrip() for line in text.strip().splitlines() if not line.startswith("Updated: "))
    lines = [line for line in body.splitlines() if line.strip()]
    if len(lines) > MAX_LINES or len(body) > MAX_CHARS:
        return (f"too long ({len(lines)} lines, {len(body)} characters; limits {MAX_LINES} lines, {MAX_CHARS} characters): "
                "keep only what the next run needs, drop what is no longer true")
    os.makedirs(folder(), exist_ok=True)
    if not lines:
        if os.path.exists(path_of(platform)):
            os.remove(path_of(platform))
        return None
    stamp = today or datetime.date.today().isoformat()
    with open(path_of(platform), "w", encoding="utf-8") as f:
        f.write(f"Updated: {stamp}\n{body}\n")
    return None


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("cmd", choices=("show", "save", "path"))
    ap.add_argument("platform", choices=PLATFORMS)
    ap.add_argument("--file")
    a = ap.parse_args()
    if a.cmd == "show":
        sys.stdout.write(show(a.platform))
    elif a.cmd == "path":
        print(path_of(a.platform))
    else:
        if not a.file:
            sys.exit("save needs --file")
        with open(a.file, encoding="utf-8") as f:
            error = save(a.platform, f.read())
        if error:
            sys.exit(error)
        print(f"saved {path_of(a.platform)}")


if __name__ == "__main__":
    main()
