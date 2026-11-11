#!/usr/bin/env python3
"""Attach a local file of any size to a web page's file input through Claude in Chrome.

The browser tool's file_upload only takes files inside the session's folders and at most 10 MB
per call. This helper works around both: it cuts the file into parts under that limit inside a
folder the session can read, and prints two JavaScript snippets. The first adds a temporary file
input to the page that collects the parts; the second joins them into one file, byte for byte,
and hands it to the site's own file input (or drops it on a drop zone).

  attach.py split FILE [--dir DIR] [--accept video|srt|any] [--selector CSS] [--drop CSS]
      Prints JSON: parts (paths, in order), setup_js, finish_js, cleanup_js, name, size.
      --dir      a folder the session can read; default: the current directory
      --accept   which of the site's file inputs to use when --selector is not given
      --selector CSS selector of the site's file input
      --drop     CSS selector of a drop zone: drop the file there instead of using an input
  attach.py clean [--dir DIR]
      Removes the parts folder.

See references/attach.md for the steps.
"""
import argparse
import hashlib
import json
import mimetypes
import os
import shutil
import sys

PART = 8 * 1024 * 1024       # under file_upload's 10 MB per call
MANY = 60                    # more parts than this (about 480 MB): better to ask the user to drag the file in
FOLDER = ".video-poster-parts"
LABEL = "video poster part input"

SETUP_JS = """(() => {
  document.getElementById('vp-part-input')?.remove();
  const i = document.createElement('input');
  i.type = 'file'; i.id = 'vp-part-input'; i.setAttribute('aria-label', %(label)s);
  i.style.cssText = 'position:fixed;top:8px;left:8px;z-index:2147483647;background:#fff;color:#000';
  window.__vpParts = [];
  i.addEventListener('change', e => { e.stopPropagation(); if (i.files[0]) window.__vpParts.push(i.files[0]); });
  document.body.append(i);
  return 'ready: upload each part, in order, to the file input labelled ' + %(label)s;
})()"""

FINISH_JS = """(async () => {
  const want = %(want)s;
  // one File per part name (a part sent twice counts once), in name order whatever order they arrived in
  const parts = [...new Map((window.__vpParts || []).map(p => [p.name, p])).values()].sort((a, b) => a.name < b.name ? -1 : 1);
  const got = parts.map(p => p.name);
  if (JSON.stringify(got) !== JSON.stringify(want.parts))
    return {ok: false, error: 'parts on the page do not match', got, expected: want.parts};
  const file = new File(parts, want.name, {type: want.type});
  if (file.size !== want.size) return {ok: false, error: 'size mismatch', size: file.size, expected: want.size};
  const hash = await crypto.subtle.digest('SHA-256', await file.arrayBuffer());
  const hex = [...new Uint8Array(hash)].map(b => b.toString(16).padStart(2, '0')).join('');
  if (hex !== want.sha256) return {ok: false, error: 'the joined file differs from the original'};
  const dt = new DataTransfer(); dt.items.add(file);
  const done = extra => { document.getElementById('vp-part-input')?.remove(); delete window.__vpParts;
                          return Object.assign({ok: true, name: file.name, size: file.size}, extra); };
  if (want.drop) {
    const zone = document.querySelector(want.drop);
    if (!zone) return {ok: false, error: 'drop zone not found: ' + want.drop};
    for (const type of ['dragenter', 'dragover', 'drop'])
      zone.dispatchEvent(new DragEvent(type, {dataTransfer: dt, bubbles: true, cancelable: true}));
    return done({how: 'dropped on ' + want.drop});
  }
  const all = [...document.querySelectorAll('input[type=file]')].filter(i => i.id !== 'vp-part-input');
  const fits = i => { const a = (i.accept || '').toLowerCase();
    return want.accept === 'video' ? (!a || /video|mp4|mov|\\*/.test(a))
         : want.accept === 'srt' ? (!a || /srt|vtt|text|\\*|caption|subtitle/.test(a)) && !/^(video|image)\\/[^,]*$/.test(a)
         : true; };
  const target = want.selector ? document.querySelector(want.selector) : (all.filter(fits)[0] || null);
  const seen = all.map(i => ({accept: i.accept, name: i.name, id: i.id}));
  if (!target) return {ok: false, error: 'no matching file input on the page', inputs: seen};
  target.files = dt.files;
  target.dispatchEvent(new Event('input', {bubbles: true}));
  target.dispatchEvent(new Event('change', {bubbles: true}));
  return done({how: 'set on input', input: {accept: target.accept, name: target.name, id: target.id}, inputs: seen.length});
})()"""

CLEANUP_JS = "(() => { document.getElementById('vp-part-input')?.remove(); delete window.__vpParts; return 'removed'; })()"


def split(path, base, accept="any", selector=None, drop=None):
    path = os.path.abspath(os.path.expanduser(path))
    size = os.path.getsize(path)
    digest = hashlib.sha256()
    key = hashlib.sha256(f"{path}:{size}:{os.path.getmtime(path)}".encode()).hexdigest()[:12]
    folder = os.path.join(os.path.abspath(os.path.expanduser(base)), FOLDER, key)
    shutil.rmtree(folder, ignore_errors=True)
    os.makedirs(folder)
    parts = []
    with open(path, "rb") as src:
        while True:
            chunk = src.read(PART)
            if not chunk and parts:
                break
            digest.update(chunk)
            part = os.path.join(folder, f"part-{len(parts) + 1:04}.bin")
            with open(part, "wb") as out:
                out.write(chunk)
            parts.append(part)
            if len(chunk) < PART:
                break
    name = os.path.basename(path)
    want = {"parts": [os.path.basename(p) for p in parts], "name": name, "size": size, "sha256": digest.hexdigest(),
            "type": mimetypes.guess_type(name)[0] or ("text/plain" if name.lower().endswith(".srt") else "application/octet-stream"),
            "accept": accept, "selector": selector, "drop": drop}
    result = {"name": name, "size": size, "parts": parts,
              "setup_js": SETUP_JS % {"label": json.dumps(LABEL)},
              "finish_js": FINISH_JS % {"want": json.dumps(want, ensure_ascii=False)},
              "cleanup_js": CLEANUP_JS, "part_input_label": LABEL}
    if len(parts) > MANY:
        result["warning"] = (f"{len(parts)} parts ({size // (1024 * 1024)} MB): this takes many upload calls. "
                             "Asking the user to drag the file into the page is faster.")
    return result


def clean(base):
    folder = os.path.join(os.path.abspath(os.path.expanduser(base)), FOLDER)
    existed = os.path.isdir(folder)
    shutil.rmtree(folder, ignore_errors=True)
    return {"removed": existed, "folder": folder}


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("split")
    s.add_argument("file")
    s.add_argument("--dir", default=".")
    s.add_argument("--accept", choices=("video", "srt", "any"), default="any")
    s.add_argument("--selector")
    s.add_argument("--drop")
    c = sub.add_parser("clean")
    c.add_argument("--dir", default=".")
    a = ap.parse_args()
    if a.cmd == "split":
        if not os.path.isfile(os.path.expanduser(a.file)):
            print(json.dumps({"error": f"file not found: {a.file}"}))
            sys.exit(1)
        print(json.dumps(split(a.file, a.dir, a.accept, a.selector, a.drop), ensure_ascii=False, indent=2))
    else:
        print(json.dumps(clean(a.dir)))


if __name__ == "__main__":
    main()
