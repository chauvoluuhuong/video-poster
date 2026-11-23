"""Translations: extra subtitle languages and a translated title/description reach only the platforms that take them."""
import json
import os
import sys
import tempfile
import unittest

ROOT = os.path.join(os.path.dirname(__file__), "..")
sys.path.insert(0, os.path.join(ROOT, "skills", "post-video", "scripts"))
import parse_post  # noqa: E402
import prepare  # noqa: E402

SRT = "1\n00:00:00,000 --> 00:00:01,500\n{}\n\n2\n00:00:01,500 --> 00:00:03,000\n{}\n"


class Translations(unittest.TestCase):
    def setUp(self):
        self.d = tempfile.mkdtemp()
        self.work = os.path.join(self.d, "work")
        for name, body in (("v-16x9.mp4", "x"), ("v-9x16.mp4", "x"), ("v.srt", SRT.format("Xin chào", "Tạm biệt")),
                           ("v.en.srt", SRT.format("Hello", "Bye"))):
            with open(os.path.join(self.d, name), "w", encoding="utf-8") as f:
                f.write(body)
        self.md = ("<!-- video-poster: v1 -->\n# Tiêu đề\nMô tả\n## Files\n- Wide video: v-16x9.mp4\n- Wide SRT: v.srt\n"
                   "- Wide SRT en: v.en.srt\n- Tall video: v-9x16.mp4\n- Tall SRT: v.srt\n- Tall SRT en: v.en.srt\n"
                   "## Settings\n- Language: vi\n## Translation en\n### Title\nEnglish <title>\n### Description\nEnglish text\n")

    def run_prepare(self, platforms):
        res = parse_post.parse(self.md, self.d)
        self.assertEqual(res["problems"], [])
        form = {"videos": {s: dict(f) for s, f in res["files"].items()}, "platforms": platforms,
                "visibility": "public", "language": "vi"}
        return {p["id"]: p for p in prepare.prepare(form, res["post"], self.work)["posts"]}

    def test_each_platform_gets_what_it_takes(self):
        posts = self.run_prepare({"youtube": "both", "facebook": "both", "linkedin": "wide", "tiktok": "tall"})
        for pid in ("youtube-wide", "youtube-tall"):
            p = posts[pid]
            self.assertEqual([t["language"] for t in p["extra_srt"]], ["en"])
            self.assertTrue(p["extra_srt"][0]["file"].endswith("v-16x9.en.clean.srt" if pid == "youtube-wide" else "v-9x16.en.clean.srt"))
            self.assertEqual(p["translations"], {"en": {"title": "English title", "description": "English text"}})
            self.assertTrue(p["translations_info"]["ok"])
            self.assertIn("also subtitles: en", p["captions"]["text"])
        fb = posts["facebook-wide"]
        self.assertEqual(os.path.basename(fb["extra_srt"][0]["file"]), "v-16x9.en_US.srt")
        self.assertEqual(os.path.basename(fb["srt_file"]), "v-16x9.vi_VN.srt")
        self.assertEqual(fb["translations"], {})
        self.assertFalse(fb["translations_info"]["ok"])
        for pid, why in (("facebook-tall", "Reels"), ("linkedin-wide", "one caption file"), ("tiktok-tall", "TikTok")):
            self.assertEqual(posts[pid]["extra_srt"], [])
            self.assertIn("en subtitles skipped", posts[pid]["captions"]["text"])
            self.assertIn(why, posts[pid]["captions"]["text"])
        with open(fb["extra_srt"][0]["file"], encoding="utf-8") as f:
            self.assertIn("Hello", f.read())

    def test_no_translations_changes_nothing(self):
        self.md = self.md.split("- Wide SRT en")[0] + "- Tall video: v-9x16.mp4\n## Settings\n- Language: vi\n"
        p = self.run_prepare({"youtube": "wide"})["youtube-wide"]
        self.assertEqual((p["extra_srt"], p["translations"], p["translations_info"]), ([], {}, None))
        self.assertNotIn("subtitles", p["captions"]["text"])

    def test_json_form(self):
        data = {"video_poster": 1, "title": "T", "description": "d",
                "files": {"wide": {"video": "v-16x9.mp4", "srt": "v.srt", "translations": {"en": "v.en.srt"}}},
                "translations": {"en": {"title": "E"}}, "settings": {"language": "vi"}}
        res = parse_post.parse(json.dumps(data), self.d)
        self.assertEqual(res["problems"], [])
        self.assertEqual(res["post"]["subtitles"], {"wide": {"en": os.path.join(self.d, "v.en.srt")}})
        self.assertEqual(res["post"]["translations"], {"en": {"title": "E"}})
        self.assertEqual(set(res["files"]["wide"]), {"video", "srt"})  # translations never reach the form's slots


if __name__ == "__main__":
    unittest.main()
