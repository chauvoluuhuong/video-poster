# YouTube

Start: `https://studio.youtube.com` → **Create** → **Upload videos**.

Check the channel shown at the top right is the one the user means; if they have several and did not say, ask.

Fields come from this upload\'s entry in `final.json` (`fields`, by `key`):

1. **Select files** → attach the video.
2. **Details**
   - Title ← `title` (100 characters at most; the box is pre-filled with the file name, clear it first).
   - Description ← `description` (hashtags are already at the end; the first three show above the title).
   - Audience: "made for kids" is required. Choose **No, it's not made for kids** unless the user said otherwise; it is their legal statement, so if the video could be for children, ask.
   - **Show more** → Tags ← `tags`, typed with a comma after each. Video language ← the caption language.
   - Altered or synthetic content question, paid promotion: leave at the default "No" only if the user's text gives no reason to think otherwise; if it mentions AI-made voice or footage or a sponsor, ask.
3. **Video elements** → **Add subtitles** → pick the language → **Upload file** → **With timing** → attach `srt_file` (skip this step when it is null) → check a few lines appear → **Done**.
   If the subtitles row is greyed out, the video is still processing: finish the upload, then open the video in Studio → **Subtitles** and add them there.
4. **Checks**: wait. A copyright or ad-suitability issue → stop and tell the user.
5. **Visibility**: Public unless told otherwise (Private, Unlisted, or Schedule with the date and time they gave).
6. Final button: **Publish** (or **Save** / **Schedule**). Press only with the user's yes.
7. The dialog then shows the video link (`https://youtu.be/...`). Copy it for the report.

Notes
- A `tall` upload (`id` `youtube-tall`) is the Short: same steps, YouTube decides it is a Short from the shape and length. When both uploads exist, do the 16:9 video first.
- A vertical or square video of 3 minutes or less is treated as a Short automatically; there is nothing to choose.
- A channel that is not phone-verified cannot upload videos longer than 15 minutes; the page says so. Tell the user, do not try to verify for them.
- A daily upload limit message means stop; retrying will not help.
