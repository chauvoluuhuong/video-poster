# Facebook

Ask once where it goes if the user did not say: a **Page** (usual for a channel) or their **personal profile**, and which Page.

## Page (Meta Business Suite)

Start: `https://business.facebook.com/latest/composer` for a `wide` upload (post with video), `https://business.facebook.com/latest/reels_composer` for a `tall` upload (Reel).

Check the Page name shown in the composer. Wrong Page → switch with the account picker at the top left, or ask.

Fields come from this upload\'s entry in `final.json` (`fields`, by `key`):

1. **Add video** → attach the video.
2. Text / description ← `text` (title, description and hashtags are already joined).
3. Leave a separate title field, if there is one, empty: the first line of `text` is the title.
4. Captions: open the video's options (**Edit video** / **Captions** / **Video options**, the name varies) → **Upload** → attach `srt_file`, the copy named like `video.vi_VN.srt` (skip when it is null). Facebook rejects any other file name. Set it as the default caption language.
   Reels composer often has no SRT upload, only auto captions; if so, say that and ask whether to use auto captions or post as a normal video instead.
5. Placement: Facebook only, unless the user asked for Instagram too. Untick anything they did not ask for.
6. Final button: **Publish** (or **Schedule**). Press only with the user's yes.
7. After publishing, open the Page's latest post and copy its link for the report.

## Personal profile

Start: `https://www.facebook.com` → "What's on your mind" → **Photo/video** → attach the video → text ← `text` → audience **Public** unless told otherwise → **Post**.
The profile composer has no SRT upload. After posting, the video's **⋯ → Edit video → Captions** sometimes offers it; try once, and report if it is not there.

First comment (when `first_comment` is not empty): open the published post (or Reel) as the Page, write the comment under it, press Enter. Pinning is not offered on most Page posts; skip it when there is no such option.

Notes
- Do not accept or dismiss permission and policy dialogs for the user; show them what it says.
- If Business Suite opens an ad-boost offer after posting, close it.
