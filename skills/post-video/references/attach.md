# Attaching a file to an upload page

The browser tool's `file_upload` takes only files inside the session's folders and at most 10 MB per call. Videos are bigger and usually live elsewhere, so never call `file_upload` on the video directly, and do not click a site's "Select files" button (it opens a system dialog you cannot use). Use `attach.py`: it cuts the file into parts inside the session folder, and the page joins them back into the same file, checked by size and SHA-256.

Use it for every file you attach: videos and SRT files alike.

## Steps

1. Get the page to the point where its file input exists (the upload dialog is open, the captions "Upload file" option is chosen). Do not click the button that opens the file dialog.
2. Split, from the session's working directory:

   ```bash
   python3 "$S/attach.py" split "/path/to/video.mp4" --accept video
   ```

   `--accept srt` for a caption file. It prints JSON: `parts` (paths, in order), `setup_js`, `finish_js`, `cleanup_js`. A `warning` means the file is very large (over about 480 MB): ask the user to drag it into the page instead.
3. Run `setup_js` in the tab with `javascript_tool`. It adds a small file input at the top left of the page, labelled "video poster part input".
4. `find` that input ("video poster part input") to get its ref, then call `file_upload` once per part with that ref, one part per call. All parts must go to this input, none to the site's own input.
5. Run `finish_js` in the tab. It joins the parts, verifies them, gives the file to the site's file input and fires the events the site listens for. Read the result:
   - `{"ok": true, "how": "set on input", ...}`: done. Now check on the page that the site reacted (file name shown, upload progress started).
   - `"no matching file input on the page"`: the result lists the inputs it saw. Split again with `--selector "<css of the right input>"`, or, when the site only has a drop zone, with `--drop "<css of the drop zone>"`, then repeat steps 3–5.
   - `"parts on the page do not match"` or a size/hash error: run `cleanup_js`, then repeat steps 3–5.
   - `ok` but the site shows nothing after a few seconds: its input ignores scripted changes. Split again with `--drop "<css of the drop zone>"` and repeat.
6. When all uploads of the run are finished:

   ```bash
   python3 "$S/attach.py" clean
   ```

## If it cannot work

If `file_upload` refuses the part files too (the session folder is not readable by the browser tool), or both the input and the drop zone fail, ask the user to drag that one file into the page, name the file and the folder it is in, and carry on with the text once they say the upload started. Report it in the final table so the site's steps can be corrected.
