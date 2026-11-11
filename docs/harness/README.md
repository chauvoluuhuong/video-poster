# Harness
One command, the same locally and in CI (GitHub Actions, `.github/workflows/ci.yml`):

```bash
./scripts/ci.sh
```

It checks the manifests are valid JSON, compiles the scripts, and runs `python3 -m unittest discover -s tests`. Needs only Python 3.9+; no network, no accounts.

- `tests/test_text.py` — text limits, hashtags, SRT fixes.
- `tests/test_attach.py` — a file cut into parts joins back to the same bytes; the page snippet carries name, size, hash.
- `tests/test_structure.py` — the structure parser against the example and heading list in the spec itself, and the folder scan.
- `tests/test_form_e2e.py` — starts the real form server through the CLI in a temp folder (`HOME` is redirected there), then acts as the page over HTTP: token and Host checks, validation, submit, prepare, preview, edits, Post, progress, Back, Cancel. `VIDEO_POSTER_PICK` replaces the native file picker with a command.

To look at the page by hand: `python3 skills/post-video/scripts/form.py --state /tmp/vp start`, then follow the commands in `form.py --help`.

Not covered: the uploads to the four sites. They need real accounts and are checked by hand.
