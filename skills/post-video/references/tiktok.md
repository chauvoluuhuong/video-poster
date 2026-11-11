# TikTok

Start: `https://www.tiktok.com/tiktokstudio/upload`.

Fields come from this upload\'s entry in `final.json` (`fields`, by `key`):

1. **Select video** → attach the video. Wait until the preview and the form appear.
2. Description ← `caption`. The box is pre-filled with the file name: select all and replace it. It is a rich editor: after each `#tag` a suggestion list opens; press Escape or pick the exact tag, then check the caption reads the same as `caption`. Line breaks may be lost; if they are, type the text line by line with Enter between.
3. Cover: leave the default unless the user gave one.
4. Who can watch: **Everyone** unless told otherwise. Leave comment, duet and stitch at their defaults.
5. Captions: there is no SRT upload here. If the page offers auto captions, turn them on.
   - Only if the user asked in chat for burned-in captions, the video you attach in step 1 must be a burned copy:
     `ffmpeg -i video.mp4 -vf "subtitles=captions.clean.srt:force_style='FontSize=14,Outline=2,MarginV=60'" -c:a copy video.captioned.mp4`
     (needs an ffmpeg built with libass; show one frame to the user before uploading).
6. "AI-generated content" switch, "Disclose post content" (brand or paid): leave off unless the user's text says the video is AI-made or sponsored; then ask.
7. Wait for the copyright / content check under the form if it runs. An issue → stop and tell the user.
8. Final button: **Post** (or **Schedule**, or **Save draft** if they asked). Press only with the user's yes.
9. After posting, the page goes to the post list in TikTok Studio. Open the newest post and copy its link for the report; if it is still "processing" and has no link yet, say so.

Notes
- Vertical 9:16 is expected. A wide video uploads but shows small; tell the user before posting.
- Links in the caption are not clickable.
- A "too many attempts" or verification puzzle: stop and hand over to the user.
