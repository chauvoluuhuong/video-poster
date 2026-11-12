# Rules for every upload

For whoever does the uploading: an uploader agent, or the main session when no agent is available.

- Each upload in its own tab; never touch a tab another uploader created.
- These pages change often. The reference files describe the path and the fields, not selectors: read the page (`read_page` / `find`), find the field by its label, then act. Check after each step that the page did what you expected.
- **Attach every file (video, SRT) the way `references/attach.md` describes**: `attach.py` cuts it into parts and the page joins them. Never give the video straight to `file_upload` (it refuses files over 10 MB and files outside the session's folders) and never click a button that opens the system file dialog. Only when that method fails as described there, ask the user to drag the file in.
- Use each field's `value` from `final.json` as is. Paste text into the field in one go and read it back: rich editors sometimes drop line breaks or turn `#tag` into a suggestion popup (press Escape, or pick the exact tag).
- Wait for upload and processing to finish before the final button. Long videos take minutes; check, do not guess.
- A CAPTCHA, a "verify it's you", a copyright or policy warning, or a choice you were not told about (paid promotion, made for kids, AI-content label): stop: an uploader returns `needs_user` with the question; the main session asks the user.
- The user pressed Post on the Check screen, so when the site's page shows exactly the approved text, press the site's final Post/Publish button. If anything differs from what they approved (text was cut by the site, different account or Page, different visibility), stop the same way.
- **Thumbnail**: when an upload's `thumbnail` is not null, attach it where the site's reference file says (`attach.py split ... --accept image`). If the site does not offer a custom thumbnail for this account or this kind of post, go on without it and report `--note "thumbnail not set"`; never block a post on it.
- **First comment**: when an upload's `first_comment` field is not empty, add it right after that upload is published: open the new post, write the comment exactly as given, send it, and pin it where the site offers that. It is part of what the user approved. If the post is still processing and comments are not open yet, wait and try once more. If the comment still cannot be added, the upload stays `posted`: report it with `--note "first comment not added"` and give the user the text to paste.
- A 9:16 upload to YouTube is a Short and to Facebook is a Reel; the reference files say what differs.
