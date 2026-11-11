---
name: post-video
description: Post one video to YouTube, Facebook, TikTok and/or LinkedIn from the user's own Chrome, with title, description, tags and an SRT caption file. Cleans up a messy description first (pasted notes, a README, mixed platforms, hashtags everywhere) into one post that fits each platform's limits. Use whenever the user wants to post, upload, publish or share a video to any of these platforms, or to prepare the upload text and captions for them — including "đăng video", "up video lên YouTube/Facebook/TikTok/LinkedIn", "đăng lên các kênh", "post this video everywhere" — even if they only give a video file and some rough text.
---

# Post a video to YouTube, Facebook, TikTok, LinkedIn

You upload through the upload pages in the user's own Chrome, where they are already logged in. No API keys. The user chooses files and approves the posts on a local page, the **form**, that you open for them.

Two rules that hold whatever else happens:

- **Nothing is published until the user presses Post on the form's Check screen.** That click is their approval for exactly the uploads and text that `wait decision` returns, nothing more. A message in chat like "post it" before the Check screen is not that approval: still show the form.
- **Never type a password or log in for the user.** If a site asks for a login, ask them to log in in Chrome and tell you when it is done.

`S="${CLAUDE_PLUGIN_ROOT}/skills/post-video/scripts"` in the commands below. Everything for one run lives in `~/.video-poster/current/` (`$W`): `submit.json`, `post.json`, `preview.json`, `final.json`, cleaned SRT files.

## 1. Open the form

Always start here. All four platforms are ticked by default; the user unticks what they do not want.

**When the user named a folder or files** (in the command's arguments or in their message), find the files first, so the form opens with the Files screen already filled in. The user still looks at it and submits; never skip the Files screen.

```bash
python3 "$S/scan.py" "/path/to/folder" --out ~/.video-poster/prefill.json
```

Give it the folder, or the files one by one. It sorts videos and images into 16:9 and 9:16, matches SRT files, finds the description file, and lists in `hints` what it was unsure about (the form shows them). Then start the form with `--prefill ~/.video-poster/prefill.json`. With no folder or files named, start it empty:

```bash
python3 "$S/form.py" start
```

It opens the page in the user's browser and prints `{"url": ...}`. **Right away, before any other tool call, write the link to the user on its own line**, every time the skill runs:

> **Open the form:** http://127.0.0.1:PORT/?t=...
> Choose your files and press **Check the posts**. I continue by myself when you do.

The user needs that link when the page did not come to the front or was closed (`form.py url` prints it again). Then wait for them:

```bash
python3 "$S/form.py" wait submit --timeout 3000
```

**Run every `wait` in the background** (Bash `run_in_background: true`) and end your turn; you are woken when the user presses the button, and the chat does not show a command that looks stuck. Only where background commands are not available, run it in the foreground with `--timeout 540` and a 10-minute tool timeout, and run it again on `{"waiting": true}`.

Results of `wait submit`: the form (below); `{"waiting": true}` after the timeout: start the wait again, no message to the user; `{"action": "cancel"}`: run `form.py stop` and say nothing was posted.

If the user writes in chat while a wait is running ("continue", "I submitted", "it is stuck"), do not start a second form: run `form.py wait submit --timeout 5` (or `wait decision`) in the foreground to read where things stand and go on from there.

The result is the form: `videos.wide` (16:9) and `videos.tall` (9:16), each with `video`, `srt` and `thumbnail`; `description_file` and/or `description_text`; `platforms` with which video each one gets (`wide`, `tall`, `both`); `visibility`; `language`.

If the form cannot open (no browser, the command fails), fall back to asking in chat for the same things, then continue from step 2 with a `submit.json` you write yourself.

## 2. Turn the text into post.json

First try to read the description file exactly:

```bash
python3 "$S/parse_post.py" "<description_file>" --out "$W/post.json"
```

`"structured": true` means the file follows the video-poster structure (the `description-file` skill of this plugin describes it): `post.json` is written from it word for word. Do not rewrite anything; only add its `problems`, if any, to `notes` in `post.json`, and go to step 3. Pasted `description_text` together with a structured file: treat the pasted text as an instruction for what to change in `post.json`.

`"structured": false` means a free-form file: read `description_file` and `description_text` (when both are given, the pasted text is the newer word) and write `post.json` yourself as described below. The text is often not ready: a pasted README with sections per platform, notes with no title, hashtags mixed into sentences, markdown, several languages. Make one clean post from it and write `$W/post.json`:

```json
{
  "title": "Under 100 characters, the hook first",
  "description": "Plain text.\n\nShort paragraphs.",
  "tags": ["plain words", "no hash sign"],
  "language": "vi",
  "first_comment": "Tải về: https://example.com",
  "overrides": { "tiktok": { "description": "shorter text for TikTok" } },
  "written_by_claude": ["tags"],
  "notes": ["The file had two titles; I used the first."]
}
```

How to transform:

- **Keep the user's words and meaning.** Fix shape, not voice: remove markdown marks (`**`, `#` headings; `-` bullets become lines starting with "• " or plain lines), fix broken line breaks, remove duplicate lines, keep their language. Do not add claims, numbers or links that are not in their text.
- **Title**: use theirs if there is one. If not, write one from the first idea of the text and list `"title"` in `written_by_claude`.
- **Tags**: collect every `#hashtag` and every "tags:" list, remove them from the description, drop the `#`. If they gave none, propose 5–8 from the text and list `"tags"` in `written_by_claude`.
- **Per-platform sections** in the source ("YouTube:", "TikTok:", "Short description:") go into `overrides`, not into the main description. Override keys: `youtube`, `youtube_short`, `facebook`, `facebook_reel`, `tiktok`, `linkedin`; each may set `title`, `description`, `tags`, `first_comment`.
- **First comment**: a "first comment" / "bình luận đầu tiên" / "pinned comment" part in the source goes into `first_comment` (or the platform's override), never into the description. Do not write one yourself; when the source has none, leave it out. The Check screen shows a First comment box for every upload, which the user can fill or clear.
- **Chapters / timestamps** (`0:00 Intro`) belong to the 16:9 cut: put the description with chapters in the `youtube` override and give `youtube_short` the plain one. YouTube needs the first chapter to be `0:00`.
- **Links**: keep on YouTube, Facebook and LinkedIn. TikTok captions do not make links clickable; leave them out of a `tiktok` override unless the user wants them.
- **`written_by_claude`** marks parts you wrote (`title`, `description`, `tags`); the Check screen labels them. **`notes`** are short lines the user should see at the top of the Check screen: choices you made, things you left out.
- Do not ask in chat about things the user can simply fix on the Check screen. Ask only when you cannot tell what the video is about.

## 3. Prepare and show the Check screen

```bash
python3 "$S/prepare.py" "$W/submit.json" "$W/post.json" --out "$W/preview.json"
```

This makes one entry per upload (YouTube with both videos is two: a video and a Short), fits the text to each platform's limits, cleans each SRT (and makes the copy Facebook needs, named like `video.vi_VN.srt`), and collects warnings. If it reports that text was cut for a platform, write a shorter override for that platform and run it again; a cut-off sentence is not acceptable.

```bash
python3 "$S/form.py" preview "$W/preview.json"
```

```bash
python3 "$S/form.py" wait decision --timeout 3000
```

Run it in the background like the first wait, and tell the user in one line that the Check screen is ready, with the number of uploads and of notes to check, and the link again. The user edits the text on the page if they want and presses a button.

- `{"action": "refine", "instruction": "...", "file": ".../refine.json"}`: the user wrote on the Check screen what to change. The page shows "Claude is applying your changes…" until you answer. `file` holds the posts as they are on the page now, including what the user typed in the boxes. Edit the `value` of the fields in that file to do what the instruction says, and only that: keep every other value and the user's own edits untouched, keep each value within its `limit`. To add a line for the user ("I shortened the caption to 140 characters"), put it first in `warnings`. Then show it and wait again:

  ```bash
  python3 "$S/form.py" preview "$W/refine.json"
  ```

  If the instruction is unclear, or asks for something a text change cannot do (another video, another platform), do not guess: put one line saying so first in `warnings` (for another file or platform: "press Back to change files"), push the file unchanged, and wait again. Refine can happen any number of times; nothing is posted by it.
- `{"action": "back"}`: they went back to the form. Go to `wait submit` in step 1 and redo steps 2–3.
- `{"action": "cancel"}`: `form.py stop`, say nothing was posted.
- `{"action": "post", "posts": [...]}`: the approval. `posts` is the final list, with the user's edits. Upload exactly these: for each one `video`, `thumbnail` (may be null), `fields` (by `key`: `title`, `description`, `tags`, `text`, `caption`), `srt_file` (may be null), `visibility`, `key` (platform), `shape` (`wide` / `tall`), `id`.

Where captions go:

| Platform | SRT upload |
|---|---|
| YouTube | yes |
| Facebook | yes, with the renamed copy in `srt_file`; Reels often offer only auto captions |
| LinkedIn | yes |
| TikTok | no upload on the web: turn on TikTok's auto captions |

## 4. Report progress on the page

The page shows a row per upload. Around each upload:

```bash
python3 "$S/form.py" progress youtube-wide uploading
```

```bash
python3 "$S/form.py" progress youtube-wide posted --link https://youtu.be/...
```

Statuses: `uploading`, `posted`, `failed` (add `--note "why"`), `skipped`. When all are finished: `form.py done`, `form.py stop`, and `attach.py clean`.

## 5. Upload in Chrome

Use the Claude in Chrome tools (`mcp__claude-in-chrome__*`); load them with ToolSearch in one call, including `file_upload`, `javascript_tool` and `find`. The built-in browser pane is not logged in to these sites and cannot attach local files, so do not use it here. If Claude in Chrome is not connected, say so and stop; the text and the clean SRT are still ready for the user to post by hand.

For each platform, read its file first and follow it:

- YouTube → `references/youtube.md`
- Facebook → `references/facebook.md`
- TikTok → `references/tiktok.md`
- LinkedIn → `references/linkedin.md`

How to work on every one of them:

- One platform at a time, each in its own tab. Finish or fail one before the next.
- These pages change often. The reference files describe the path and the fields, not selectors: read the page (`read_page` / `find`), find the field by its label, then act. Check after each step that the page did what you expected.
- **Attach every file (video, SRT) the way `references/attach.md` describes**: `attach.py` cuts it into parts and the page joins them. Never give the video straight to `file_upload` (it refuses files over 10 MB and files outside the session's folders) and never click a button that opens the system file dialog. Only when that method fails as described there, ask the user to drag the file in.
- Use each field's `value` from `final.json` as is. Paste text into the field in one go and read it back: rich editors sometimes drop line breaks or turn `#tag` into a suggestion popup (press Escape, or pick the exact tag).
- Wait for upload and processing to finish before the final button. Long videos take minutes; check, do not guess.
- A CAPTCHA, a "verify it's you", a copyright or policy warning, or a choice you were not told about (paid promotion, made for kids, AI-content label): stop and ask the user.
- The user pressed Post on the Check screen, so when the site's page shows exactly the approved text, press the site's final Post/Publish button. If anything differs from what they approved (text was cut by the site, different account or Page, different visibility), stop and ask in chat.
- **Thumbnail**: when an upload's `thumbnail` is not null, attach it where the site's reference file says (`attach.py split ... --accept image`). If the site does not offer a custom thumbnail for this account or this kind of post, go on without it and report `--note "thumbnail not set"`; never block a post on it.
- **First comment**: when an upload's `first_comment` field is not empty, add it right after that upload is published: open the new post, write the comment exactly as given, send it, and pin it where the site offers that. It is part of what the user approved. If the post is still processing and comments are not open yet, wait and try once more. If the comment still cannot be added, the upload stays `posted`: report it with `--note "first comment not added"` and give the user the text to paste.
- A 9:16 upload to YouTube is a Short and to Facebook is a Reel; the reference files say what differs.

## 6. Report

A short table in chat: upload, result (posted / failed / skipped), link to the post if the site gave one, captions attached or not, thumbnail set or not, first comment added or not. For a failure, say at which step and what the page said; do not retry a publish more than once, a double post is worse than a missing one. The files in `~/.video-poster/current/` stay until the next run, so a failed upload can be redone from `final.json`.
