# LinkedIn

Ask once if the user did not say: post as **themselves** or as a **company page** (and which).

Start
- As themselves: `https://www.linkedin.com/feed/` → **Start a post** → the video / media button.
- As a company page: open the page's admin view (`https://www.linkedin.com/company/<name>/admin/`) → **Create** → **Start a post**, or in the post dialog use the author picker at the top to switch to the page.

Fields come from this upload\'s entry in `final.json` (`fields`, by `key`):

1. Attach the video in the media step.
2. In the same media editor, before pressing **Next**: **Captions** (a "CC" or "Add captions" control) → attach `srt_file` (skip when it is null). Leave the video title field, if there is one, as it is. If there is no captions control, look for **Edit** on the video thumbnail after it is attached; if it is still not there, say so and ask whether to post without captions.
3. **Next** → post text ← `text` (3000 characters at most, hashtags at the end). After typing a `#tag` a suggestion list may open: press Escape, then check the text reads the same as `text`.
4. Audience: **Anyone** unless told otherwise.
5. Final button: **Post** (or the clock icon to schedule). Press only with the user's yes.
6. LinkedIn processes the video after posting and shows a "your post is ready" notice with **View post**. Open it and copy the link for the report; if it is still processing, say so.

7. First comment (when `first_comment` is not empty): on the published post, **Comment**, paste the text, **Comment** / **Post**. Check that it is written as the same author (you or the company page) as the post.

Notes
- Limits: 15 minutes and 5 GB on the web. Longer → tell the user; do not cut the video unless asked.
- Keep links where the user put them; do not move them to a comment unless asked.
- Do not use "Rewrite with AI" or other suggestions the dialog offers; the text is already approved.
