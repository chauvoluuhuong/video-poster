# video-poster

A Claude Code plugin that posts one video to YouTube, Facebook, TikTok and LinkedIn from your own Chrome, with a description, tags and an SRT caption file.

## What it does

1. Takes your video, your text in any shape (notes, a README, hashtags mixed in) and an SRT file.
2. Turns the text into one clean post, then into the exact text each platform accepts (length limits, hashtags, YouTube tags).
3. Cleans the SRT (UTF-8, numbering, time format) and makes the specially named copy Facebook needs.
4. Shows you the final text per platform and waits for your yes.
5. Uploads through the upload pages in your Chrome and reports the links.

## Needs

- The Claude in Chrome extension, connected, and you logged in to each platform in that Chrome.
- `python3`. `ffprobe` / `ffmpeg` are optional (video checks, burned-in captions for TikTok).

## Install

```bash
claude plugin marketplace add /path/to/video-poster
```

```bash
claude plugin install video-poster@video-poster-local
```

## Use

```
/video-poster:post-video ~/Videos/demo.mp4 to youtube and tiktok, captions demo.srt
<paste your description and tags, in any format>
```

Or just say "post this video to YouTube and LinkedIn" and give the files.

## Limits

- TikTok's web upload has no SRT upload: the plugin offers TikTok's auto captions or burning the SRT into a copy of the video.
- The upload pages change. The steps in `skills/post-video/references/` describe fields, not selectors, so small changes are handled; a redesign may need those files updated.
