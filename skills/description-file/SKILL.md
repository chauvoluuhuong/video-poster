---
name: description-file
description: The exact structure of the description file (post file, Markdown or JSON) that the video-poster plugin reads when it posts a video to YouTube, Facebook, TikTok and LinkedIn. Read this whenever you write, generate or convert the upload text for a video (title, description, tags, first comment, per-platform versions, which files to post) and it will be posted with video-poster, or when someone asks what format that file needs — including "viết file đăng bài", "nội dung đăng bài", "title, mô tả, tags cho video". Follow it exactly so the file is read as is, with no rewriting.
---

# The video-poster description file

One file, saved next to the video files: Markdown (suggested name `post.md`) when a person or an AI writes it, or JSON (`post.json`, see **The same file as JSON**) when a script writes it. When it follows this structure, video-poster reads it exactly and changes nothing. A file that does not follow it still works, but then the text is rewritten by an AI at posting time, which is what this structure avoids.

## Rules

1. The first line is the marker `<!-- video-poster: v1 -->`. Without it the file is not treated as structured.
2. Exactly one `# ` heading: the title. The text under it, up to the next `## `, is the main description.
3. Only the `## ` sections listed below. Any other `## ` section is ignored and reported as a problem. Notes for humans (posting tips, thumbnail text, alternatives to choose from) go in another file, not in this one.
4. Heading names are in English, exactly as written here (case does not matter). The content can be in any language.
5. Plain text only inside the content: no `**bold**`, no Markdown links, no tables. Line breaks are kept as written. Use "• " for bullet lines.
6. Tags are plain words separated by commas, without `#`. The plugin makes the hashtags itself.
7. Write a platform section only when that platform needs something different from the main text. Inside it, write only the parts that differ.
8. Do not put things into the description that have their own place: tags, the first comment, file names, per-platform text.

## Structure

```markdown
<!-- video-poster: v1 -->
# Main title, the hook first, under 100 characters

Main description. Short paragraphs, plain text.
Used on every platform that has no section of its own.

## Tags
first tag, second tag, third tag

## First comment
Text posted as the first comment right after the video is up (for example the link).

## Files
- Wide video: demo-16x9.mp4
- Wide SRT: demo-16x9.srt
- Wide thumbnail: thumbnail-16x9.png
- Tall video: demo-9x16.mp4
- Tall SRT: demo-9x16.srt
- Tall thumbnail: thumbnail-9x16.png

## Settings
- Platforms: youtube, facebook, tiktok, linkedin
- Language: vi
- Visibility: public

## YouTube
### Title
### Description
### Tags
### First comment

## YouTube Short
## Facebook
## Facebook Reel
## TikTok
## LinkedIn
```

## Sections

| Section | Content | If left out |
|---|---|---|
| `# Title` + text | Main title and description | required |
| `## Tags` | Comma-separated words, no `#` | no tags or hashtags |
| `## First comment` | One comment, plain text | no comment is posted |
| `## Files` | `- Wide video:`, `- Wide SRT:`, `- Wide thumbnail:`, `- Tall video:`, `- Tall SRT:`, `- Tall thumbnail:`; file names relative to this file, or full paths. Wide = 16:9, tall = 9:16. List only files that exist | the user picks the files on the form |
| `## Settings` | `- Platforms:` any of youtube, facebook, tiktok, linkedin · `- Language:` caption language code (vi, en) · `- Visibility:` public, private or unlisted | all four platforms, public; language from the form |
| `## YouTube`, `## YouTube Short`, `## Facebook`, `## Facebook Reel`, `## TikTok`, `## LinkedIn` | Sub-sections `### Title`, `### Description`, `### Tags`, `### First comment`, each optional. Text directly under the `## ` heading counts as the description | the main text is used |

How each platform uses the parts:

| Platform | Title | Description | Tags | Limits |
|---|---|---|---|---|
| YouTube (16:9) | title field | description; up to 3 hashtags from the tags are added at the end | tag field, 500 characters in all | title 100, description 5000 |
| YouTube Short (9:16) | title field | as YouTube | as YouTube | same; over 3:00 it is a normal video |
| Facebook, Facebook Reel | first line of the post | rest of the post + hashtags | up to 8 hashtags | 5000 |
| TikTok | first line of the caption | rest of the caption + hashtags | up to 5 hashtags | 2200 in all; first comment 150 |
| LinkedIn | first line of the post | rest of the post + hashtags | up to 5 hashtags | 3000 |

On Facebook, TikTok and LinkedIn the title becomes the first line of the text. When a platform's description should stand alone, give that platform a `### Title` that is the opening words of its `### Description`; the plugin then does not repeat it.

## What good content looks like

- **YouTube**: chapters go in the `## YouTube` description, one per line, first one `0:00`, at least three. Put the link in the first two lines. Do not put chapters in `## YouTube Short`.
- **TikTok**: a caption under about 150 characters; links are not clickable, so put the link in `### First comment`.
- **Facebook / LinkedIn**: the hook in the first line; a link in the text reduces reach, so many authors put it in `### First comment`.
- A different cut for a platform (for example a 0:53 vertical cut for TikTok) cannot be expressed here: `## Files` has one wide and one tall video. Make a second description file for the other cut.

## The same file as JSON

For a tool or script that generates the file, the same content can be one JSON object. It is read exactly like the Markdown form: same parts, same limits, same plain-text rules for the content.

- `"video_poster": 1` is the marker. A `.json` file without it is not treated as a description file.
- `title` and `description` are required; `tags` is a list of plain words; `first_comment` is optional.
- `overrides`: keys `youtube`, `youtube_short`, `facebook`, `facebook_reel`, `tiktok`, `linkedin`; each may set `title`, `description`, `tags`, `first_comment`.
- `files`: `wide` (16:9) and `tall` (9:16), each with `video`, `srt`, `thumbnail`; paths relative to the JSON file, or full paths.
- `settings`: `platforms` (a list), `language`, `visibility`.
- Any other key is ignored and reported as a problem. Notes for humans go in another file.

The example at the end of this page, as JSON:

```json
{
  "video_poster": 1,
  "title": "Đừng cầm tay chỉ việc cho AI: xây môi trường để nó tự làm | Chorus 2.0",
  "description": "Đừng cầm tay chỉ việc cho AI nữa. Chorus 2.0 cho bạn xây môi trường để AI tự lập kế hoạch, tự chia việc và học từ sai lầm.\nTải Chorus: https://example.com",
  "tags": [
    "Chorus",
    "AI agent",
    "Claude Code",
    "lập trình với AI"
  ],
  "files": {
    "wide": {
      "video": "chorus-2-ngang.mp4",
      "srt": "chorus-2.srt",
      "thumbnail": "thumbnail-ngang.png"
    },
    "tall": {
      "video": "chorus-2-doc.mp4",
      "thumbnail": "thumbnail-doc.png"
    }
  },
  "settings": {
    "platforms": [
      "youtube",
      "tiktok",
      "linkedin"
    ],
    "language": "vi"
  },
  "overrides": {
    "youtube": {
      "description": "Đừng cầm tay chỉ việc cho AI nữa. Chorus 2.0 cho bạn xây môi trường để AI tự lập kế hoạch, tự chia việc và học từ sai lầm.\nTải Chorus: https://example.com\n\n0:00 Mở đầu\n0:08 Bản 1: gom về một nơi\n0:19 Bản 2: xây môi trường cho AI"
    },
    "youtube_short": {
      "title": "Đừng cầm tay chỉ việc cho AI #Shorts",
      "description": "Xây môi trường để AI tự làm, tự học. Chorus 2.0: https://example.com"
    },
    "tiktok": {
      "title": "Đừng cầm tay chỉ việc cho AI nữa.",
      "description": "Đừng cầm tay chỉ việc cho AI nữa. Xây môi trường để nó tự làm, tự học. Link ở bình luận.",
      "tags": [
        "AI",
        "AIAgent",
        "ClaudeCode",
        "LapTrinh"
      ],
      "first_comment": "Tải Chorus: https://example.com"
    },
    "linkedin": {
      "title": "Làm việc với AI coding agent",
      "description": "Làm việc với AI coding agent, phần mệt nhất không phải là viết prompt. Đó là phải đứng cạnh nó.\n\n• Teammate: mỗi agent có bộ skill và nhiệm vụ riêng.\n• Planner: chia việc thành từng bước, bạn chỉ bấm duyệt.",
      "tags": [
        "AIAgents",
        "DeveloperTools",
        "OpenSource"
      ],
      "first_comment": "Tải Chorus: https://example.com"
    }
  }
}
```

## Check the file

If the video-poster plugin is installed, this prints what will be read and lists problems:

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/skills/post-video/scripts/parse_post.py" post.md
```

It takes the JSON form the same way.

`"problems": []` and `"structured": true` mean the file is read exactly as written.

## Example

```markdown
<!-- video-poster: v1 -->
# Đừng cầm tay chỉ việc cho AI: xây môi trường để nó tự làm | Chorus 2.0

Đừng cầm tay chỉ việc cho AI nữa. Chorus 2.0 cho bạn xây môi trường để AI tự lập kế hoạch, tự chia việc và học từ sai lầm.
Tải Chorus: https://example.com

## Tags
Chorus, AI agent, Claude Code, lập trình với AI

## Files
- Wide video: chorus-2-ngang.mp4
- Wide SRT: chorus-2.srt
- Wide thumbnail: thumbnail-ngang.png
- Tall video: chorus-2-doc.mp4
- Tall thumbnail: thumbnail-doc.png

## Settings
- Platforms: youtube, tiktok, linkedin
- Language: vi

## YouTube
### Description
Đừng cầm tay chỉ việc cho AI nữa. Chorus 2.0 cho bạn xây môi trường để AI tự lập kế hoạch, tự chia việc và học từ sai lầm.
Tải Chorus: https://example.com

0:00 Mở đầu
0:08 Bản 1: gom về một nơi
0:19 Bản 2: xây môi trường cho AI

## YouTube Short
### Title
Đừng cầm tay chỉ việc cho AI #Shorts
### Description
Xây môi trường để AI tự làm, tự học. Chorus 2.0: https://example.com

## TikTok
### Title
Đừng cầm tay chỉ việc cho AI nữa.
### Description
Đừng cầm tay chỉ việc cho AI nữa. Xây môi trường để nó tự làm, tự học. Link ở bình luận.
### Tags
AI, AIAgent, ClaudeCode, LapTrinh
### First comment
Tải Chorus: https://example.com

## LinkedIn
### Title
Làm việc với AI coding agent
### Description
Làm việc với AI coding agent, phần mệt nhất không phải là viết prompt. Đó là phải đứng cạnh nó.

• Teammate: mỗi agent có bộ skill và nhiệm vụ riêng.
• Planner: chia việc thành từng bước, bạn chỉ bấm duyệt.
### Tags
AIAgents, DeveloperTools, OpenSource
### First comment
Tải Chorus: https://example.com
```
