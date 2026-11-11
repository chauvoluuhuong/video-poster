---
name: post-video
description: Post one video to YouTube, Facebook, TikTok and/or LinkedIn from the user's own Chrome, with title, description, tags and an SRT caption file. Cleans up a messy description first (pasted notes, a README, mixed platforms, hashtags everywhere) into one post that fits each platform's limits. Use whenever the user wants to post, upload, publish or share a video to any of these platforms, or to prepare the upload text and captions for them — including "đăng video", "up video lên YouTube/Facebook/TikTok/LinkedIn", "đăng lên các kênh", "post this video everywhere" — even if they only give a video file and some rough text.
---

# Post a video to YouTube, Facebook, TikTok, LinkedIn

You upload through the upload pages in the user's own Chrome, where they are already logged in. No API keys.

Two rules that hold whatever else happens:

- **Nothing is published until the user says yes** to the exact text, in the chat, in this conversation. Fill everything in, stop before the final Post/Publish button, show them, wait. One yes covers the platforms and text you showed, nothing more.
- **Never type a password or log in for the user.** If a site asks for a login, ask them to log in in Chrome and tell you when it is done.

## 1. Collect

You need:

| Thing | Required | If missing |
|---|---|---|
| Video file (absolute path) | yes | ask |
| Platforms | yes | ask; do not assume all four |
| Text: title, description, tags | yes, in any shape | ask for at least a few lines about the video |
| SRT file | no | post without captions and say so |
| Caption language | with an SRT | take it from the SRT's text; ask only if unclear |
| Visibility | no | public |

Check the video exists (`ls -l`). Run `ffprobe` on it if available to get length and width × height: TikTok and Reels want vertical, LinkedIn takes at most 15 minutes, a YouTube video of 3 minutes or less that is vertical or square becomes a Short. Tell the user about a mismatch; do not re-encode unless they ask.

## 2. Turn the text into post.json

The user's text is often not ready: a pasted README with sections per platform, notes with no title, hashtags mixed into sentences, markdown, several languages, links without labels. Your job is to make one clean post from it. Write `post.json` next to the video:

```json
{
  "title": "Under 100 characters, the hook first",
  "description": "Plain text.\n\nShort paragraphs.",
  "tags": ["plain words", "no hash sign"],
  "language": "vi",
  "overrides": { "tiktok": { "description": "shorter text for TikTok" } }
}
```

How to transform:

- **Keep the user's words and meaning.** Fix shape, not voice: remove markdown marks (`**`, `#` headings, `-` bullets become lines starting with "• " or plain lines), fix broken line breaks, remove duplicate lines, keep their language. Do not add claims, numbers or links that are not in their text.
- **Title**: use theirs if there is one. If not, write one from the first idea of the text and say that you wrote it.
- **Tags**: collect every `#hashtag` and every "tags:" list, remove them from the description, drop the `#`, split joined words back only when it is obvious (`#aiagent` stays `aiagent`). If they gave none, propose 5–8 from the text and mark them as yours.
- **Per-platform sections** in the source ("YouTube:", "TikTok:", "Short description:") go into `overrides` for that platform, not into the main description.
- **Chapters / timestamps** (`0:00 Intro`) stay in the description, one per line; YouTube needs the first one to be `0:00`. Put them in a YouTube override if the description is shared, since they mean nothing on the other platforms.
- **Links**: keep on YouTube, Facebook and LinkedIn. TikTok captions do not make links clickable; leave them out of the TikTok override unless the user wants them.
- If something essential cannot be worked out (what the video is about, which of two titles), ask one question. Do not ask about things you can decide.

Then build the per-platform text:

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/skills/post-video/scripts/build_post.py" post.json --platforms youtube,tiktok --out post.ready.json
```

It enforces each platform's length limits, makes the hashtags, and lists warnings (something was cut). If text was cut, write a shorter override for that platform yourself and run it again; a cut-off sentence is not acceptable.

## 3. Check the SRT

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/skills/post-video/scripts/check_srt.py" captions.srt --out captions.clean.srt --facebook-locale vi_VN --video video.mp4
```

It rewrites the file as clean UTF-8 SRT and fixes numbering, time format and order. Use the clean file for uploads. `--facebook-locale` (only when Facebook is a target) makes the copy Facebook demands, named `video.vi_VN.srt`. If it reports overlaps or cues past the end of the video, tell the user; upload anyway unless the times are clearly from another video (`ends_at` much longer than the video).

Where captions go:

| Platform | SRT upload |
|---|---|
| YouTube | yes |
| Facebook | yes, file name must end `.<locale>.srt` |
| LinkedIn | yes |
| TikTok | no upload on the web. Offer: turn on TikTok's own auto captions, or burn the SRT into a copy of the video with ffmpeg (ask first; it takes time and makes a new file) |

## 4. Show the plan and get the yes

Before touching a browser, show per platform: the title, the full text exactly as it will be posted, the tags, captions yes/no, visibility. Keep it compact. Say what you wrote or changed yourself. Ask: post these? Apply any edits to `post.json`, rebuild, show the changed part again.

## 5. Upload in Chrome

Use the Claude in Chrome tools (`mcp__claude-in-chrome__*`); load them with ToolSearch in one call, including `file_upload`. The built-in browser pane is not logged in to these sites and cannot attach local files, so do not use it here. If Claude in Chrome is not connected, say so and stop; the text and the clean SRT are still ready for the user to post by hand.

For each platform, read its file first and follow it:

- YouTube → `references/youtube.md`
- Facebook → `references/facebook.md`
- TikTok → `references/tiktok.md`
- LinkedIn → `references/linkedin.md`

How to work on every one of them:

- One platform at a time, each in its own tab. Finish or fail one before the next.
- These pages change often. The reference files describe the path and the fields, not selectors: read the page (`read_page` / `find`), find the field by its label, then act. Check after each step that the page did what you expected.
- Attach files with `file_upload` on the page's file input. If the input cannot be reached or the upload does not start, ask the user to drag the file in themselves, then carry on with the text.
- Paste text into the field in one go and read it back: rich editors sometimes drop line breaks or turn `#tag` into a suggestion popup (press Escape, or pick the exact tag).
- Wait for upload and processing to finish before the final button. Long videos take minutes; check, do not guess.
- A CAPTCHA, a "verify it's you", a copyright or policy warning, or a choice you were not told about (paid promotion, made for kids, AI-content label): stop and ask the user.
- If the user already said yes in step 4 and the page shows exactly that text, press the final Post/Publish button. If anything differs from what they approved (text was cut by the site, different account or Page, different visibility), stop and ask again.

## 6. Report

A short table: platform, result (posted / scheduled / failed / skipped), link to the post if the site gave one, captions attached or not. For a failure, say at which step and what the page said; do not retry a publish more than once, a double post is worse than a missing one. Leave `post.json`, `post.ready.json` and the clean SRT in place so a failed platform can be redone.
