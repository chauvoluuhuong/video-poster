# video-poster

A Claude Code plugin that posts one video to YouTube, Facebook, TikTok and LinkedIn from your own Chrome, with a description, tags and SRT captions. No API keys.

## How it works

1. Run `/video-poster:post-video`. A form opens in your browser with all four platforms ticked.
2. Drag in or choose a 16:9 video and/or a 9:16 video, an SRT for each, and a description file (or paste the text). The text can be messy: notes, a README, hashtags mixed in.
3. Press **Check the posts**. Claude turns your text into one clean post, fits it to each platform's limits, cleans the SRT, and shows every upload on the same page. Edit anything.
4. Press **Post**. Only then does Claude upload, through the upload pages in the Chrome where you are logged in. The page shows progress and the links.

| Platform | Default video | SRT captions |
|---|---|---|
| YouTube | 16:9 as a video and 9:16 as a Short | uploaded |
| Facebook | 16:9 (9:16 as a Reel if you choose it) | uploaded, renamed to `name.vi_VN.srt` |
| TikTok | 9:16 | no upload on the web; TikTok's auto captions are turned on |
| LinkedIn | 16:9 | uploaded |

## Install

```bash
claude plugin marketplace add chauvoluuhuong/video-poster
```

```bash
claude plugin install video-poster@video-poster
```

Update later with `claude plugin marketplace update video-poster`.

Needs: the Claude in Chrome extension, connected, with you logged in to each platform; `python3`. `ffprobe` is optional (video length and size on the check screen). The file picker is macOS only; elsewhere, paste the path.

## Status

The form, the check screen, the text and SRT clean-up are covered by automatic tests. The uploads themselves are driven by written steps per site (`skills/post-video/references/`) and are **not tested automatically**: the sites change, so the first post on each platform may need a correction. Please open an issue with what the page showed.

Each upload can also get a **first comment** (for example the download link), added and pinned where the site allows right after the video is posted.

Not included: platform APIs, scheduling, thumbnails, Instagram.

## Contributing

### Set up
```bash
git clone https://github.com/chauvoluuhuong/video-poster && cd video-poster
./scripts/ci.sh   # unit + form end-to-end tests, see docs/harness/README.md
```

### Git flow
- Branch from `dev`: `feature/<name>` for features, `fix/<name>` for bugs.
- Open a PR into `dev` with a short "what / tested" summary; CI must pass.
- Maintainers merge `dev → main` and tag the release `vX.Y.Z`. Installed plugins update from `main`.
- Found a bug? Open an issue with steps to reproduce and evidence (what the upload page showed, logs).

### Working with an AI agent
Point your agent at [docs/map.md](docs/map.md) before it changes anything. Example prompts:
- "Read docs/map.md, then explain how the form and the check screen work and which files implement them."
- "Read docs/features/post-video.md. The YouTube upload page changed: update skills/post-video/references/youtube.md to match what I describe."
- "Fix issue #<n>: reproduce it, add a regression test, run ./scripts/ci.sh, and open a PR into dev."

### License
MIT — see [LICENSE](LICENSE).
