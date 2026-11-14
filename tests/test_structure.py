"""parse_post.py reads the documented structure exactly; scan.py fills the form from a folder."""
import json
import os
import re
import struct
import sys
import tempfile
import time
import unittest

ROOT = os.path.join(os.path.dirname(__file__), "..")
sys.path.insert(0, os.path.join(ROOT, "skills", "post-video", "scripts"))
import build_post  # noqa: E402
import parse_post  # noqa: E402
import scan  # noqa: E402


def png(path, w, h):
    with open(path, "wb") as f:
        f.write(b"\x89PNG\r\n\x1a\n" + struct.pack(">I", 13) + b"IHDR" + struct.pack(">II", w, h) + b"\x08\x02\x00\x00\x00")


class ParsePost(unittest.TestCase):
    def example(self):
        with open(os.path.join(ROOT, "skills", "description-file", "SKILL.md"), encoding="utf-8") as f:
            return f.read().split("## Example")[1].split("```markdown\n")[1].split("\n```")[0]

    def test_documented_example_parses_without_text_problems(self):
        res = parse_post.parse(self.example(), "/nowhere")
        self.assertTrue(res["structured"])
        self.assertTrue(all(p.startswith("Files:") for p in res["problems"]), res["problems"])  # only: files do not exist here
        post = res["post"]
        self.assertTrue(post["title"].endswith("| Chorus 2.0"))
        self.assertEqual(post["tags"], ["Chorus", "AI agent", "Claude Code", "lập trình với AI"])
        self.assertIn("0:00 Mở đầu", post["overrides"]["youtube"]["description"])
        self.assertEqual(post["overrides"]["youtube_short"]["title"], "Đừng cầm tay chỉ việc cho AI #Shorts")
        self.assertEqual(post["overrides"]["tiktok"]["first_comment"], "Tải Chorus: https://example.com")
        self.assertEqual(post["language"], "vi")
        self.assertEqual(res["settings"]["platforms"], ["youtube", "tiktok", "linkedin"])
        # and the builder accepts it: the TikTok caption is the given description, not title + description
        caption = build_post.build(post, "tiktok")["caption"]
        self.assertTrue(caption.startswith("Đừng cầm tay chỉ việc cho AI nữa. Xây môi trường"))
        self.assertEqual(build_post.build(post, "linkedin")["first_comment"], "Tải Chorus: https://example.com")

    def test_every_documented_heading_is_understood(self):
        with open(os.path.join(ROOT, "skills", "description-file", "SKILL.md"), encoding="utf-8") as f:
            block = f.read().split("## Structure")[1].split("```markdown\n")[1].split("\n```")[0]
        res = parse_post.parse(block, "/nowhere")
        self.assertEqual([p for p in res["problems"] if not p.startswith("Files:")], [])

    def test_unstructured_and_problems(self):
        self.assertEqual(parse_post.parse("# Title\ntext"), {"structured": False})
        res = parse_post.parse("<!-- video-poster: v1 -->\n# T\nd\n## Notes\nx\n### Title\ny\n## Settings\n- Platforms: youtube, myspace\n")
        self.assertEqual(len(res["problems"]), 3)  # unknown section, stray ###, unknown platform
        self.assertEqual(res["post"]["description"], "d")

    def json_example(self):
        with open(os.path.join(ROOT, "skills", "description-file", "SKILL.md"), encoding="utf-8") as f:
            return f.read().split("## The same file as JSON")[1].split("```json\n")[1].split("\n```")[0]

    def test_json_form_reads_the_same_as_markdown(self):
        md = parse_post.parse(self.example(), "/nowhere")
        js = parse_post.parse(self.json_example(), "/nowhere")
        self.assertTrue(js["structured"])
        self.assertTrue(all(p.startswith("Files:") for p in js["problems"]), js["problems"])
        self.assertEqual(js["post"], md["post"])
        self.assertEqual(js["files"], md["files"])
        self.assertEqual(js["settings"], md["settings"])

    def test_json_problems_and_other_json(self):
        self.assertEqual(parse_post.parse('{"name": "package"}'), {"structured": False})
        self.assertEqual(parse_post.parse('{"video_poster": 1,'), {"structured": False})
        res = parse_post.parse(json.dumps({
            "video_poster": 1, "title": "T", "description": "d\r\nline", "tags": "#a, b", "notes": "x",
            "overrides": {"YouTube Short": {"title": "S", "cover": "x"}, "myspace": {}},
            "files": {"square": {}, "wide": {"poster": "x"}}, "settings": {"platforms": "youtube, myspace", "speed": 2}}))
        self.assertEqual(len(res["problems"]), 7, res["problems"])
        self.assertEqual(res["post"]["description"], "d\nline")
        self.assertEqual(res["post"]["tags"], ["a", "b"])
        self.assertEqual(res["post"]["overrides"], {"youtube_short": {"title": "S"}})
        self.assertIn("No title", parse_post.parse('{"video_poster": 1, "description": "d"}')["problems"])

    def test_hashtag_style_tags(self):
        res = parse_post.parse("<!-- video-poster: v1 -->\n# T\nd\n## Tags\n#AI #AIAgent #ClaudeCode\n")
        self.assertEqual(res["post"]["tags"], ["AI", "AIAgent", "ClaudeCode"])


class Scan(unittest.TestCase):
    def setUp(self):
        self.d = tempfile.mkdtemp()
        self._ffprobe, scan.video_size = scan.video_size, lambda p: None  # sort videos by name here
        self.addCleanup(lambda: setattr(scan, "video_size", self._ffprobe))

    def touch(self, name, body="x", age=0):
        p = os.path.join(self.d, name)
        with open(p, "w", encoding="utf-8") as f:
            f.write(body)
        os.utime(p, (time.time() - age, time.time() - age))
        return p

    def test_free_folder(self):
        wide, tall = self.touch("demo-ngang.mp4"), self.touch("demo-doc.mp4")
        old_tall = self.touch("demo-doc-old.mp4", age=100)
        srt = self.touch("demo-ngang.srt")
        self.touch("demo-ngang.clean.srt")
        desc = self.touch("dang-bai.md", "# hi")
        self.touch("README.md", "# readme")
        png(os.path.join(self.d, "thumbnail-wide.png"), 1920, 1080)
        png(os.path.join(self.d, "zz-screenshot.png"), 1280, 720)
        png(os.path.join(self.d, "thumbnail-tall.png"), 1080, 1920)
        res = scan.scan([self.d])
        self.assertEqual(res["videos"]["wide"], {"video": wide, "thumbnail": os.path.join(self.d, "thumbnail-wide.png"), "srt": srt})
        self.assertEqual(res["videos"]["tall"]["video"], tall)
        self.assertEqual(res["videos"]["tall"]["thumbnail"], os.path.join(self.d, "thumbnail-tall.png"))
        self.assertNotIn("srt", res["videos"]["tall"])
        self.assertEqual(res["description_file"], desc)
        self.assertTrue(any(os.path.basename(old_tall) in h for h in res["hints"]))

    def test_structured_file_decides(self):
        self.touch("a-ngang.mp4")
        chosen = self.touch("b-ngang.mp4", age=500)  # older, but named in the file
        desc = self.touch("post.md", "<!-- video-poster: v1 -->\n# T\nd\n## Files\n- Wide video: b-ngang.mp4\n- Wide SRT: gone.srt\n"
                                     "## Settings\n- Platforms: youtube, tiktok\n- Visibility: private\n")
        res = scan.scan([self.d])
        self.assertEqual(res["videos"]["wide"]["video"], chosen)
        self.assertEqual(res["description_file"], desc)
        self.assertEqual(sorted(res["platforms"]), ["tiktok", "youtube"])
        self.assertEqual(res["visibility"], "private")
        self.assertTrue(any("gone.srt" in h for h in res["hints"]))

    def test_json_file_decides_and_other_json_is_left_alone(self):
        wide = self.touch("out-16x9.mp4")
        srt = self.touch("out.srt")
        self.touch("package.json", '{"name": "x"}')
        body = {"video_poster": 1, "title": "T", "description": "d", "files": {"wide": {"video": "out-16x9.mp4", "srt": "out.srt"}},
                "settings": {"platforms": ["youtube"], "language": "en"}}
        self.touch("post-short.json", json.dumps(body), age=50)
        desc = self.touch("post-full.json", json.dumps(body))
        res = scan.scan([self.d])
        self.assertEqual(res["description_file"], desc)
        self.assertEqual(res["videos"]["wide"], {"video": wide, "srt": srt})
        self.assertEqual((list(res["platforms"]), res["language"]), (["youtube"], "en"))
        self.assertTrue(any("post-short.json" in h for h in res["hints"]))
        only = scan.scan([os.path.join(self.d, "post-short.json")])  # a file given by itself brings its videos along
        self.assertEqual(only["videos"]["wide"]["video"], wide)
        self.assertEqual(only["hints"], [])
        os.remove(desc), os.remove(os.path.join(self.d, "post-short.json"))
        self.assertNotIn("description_file", scan.scan([self.d]))  # package.json is never taken as the description

    def test_nothing_found(self):
        res = scan.scan([self.d])
        self.assertTrue(any("No video" in h for h in res["hints"]))


if __name__ == "__main__":
    unittest.main()
