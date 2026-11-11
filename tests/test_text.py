"""Unit tests for build_post.py and check_srt.py."""
import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "skills", "post-video", "scripts"))
import build_post  # noqa: E402
import check_srt  # noqa: E402

POST = {
    "title": "Tự động hoá trình duyệt <demo>",
    "description": "Dòng 1   \r\n\r\n\r\n\r\nDòng 2 https://example.com",
    "tags": ["#AI agent", "lập trình", "ai agent", "browser-workflow", "tự động hoá", "chrome"],
    "overrides": {"tiktok": {"description": "Bản ngắn"}, "youtube_short": {"title": "Short title"}},
}


class BuildPost(unittest.TestCase):
    def test_youtube(self):
        y = build_post.build(POST, "youtube")
        self.assertEqual(y["title"], "Tự động hoá trình duyệt demo")  # no < >
        self.assertTrue(y["description"].startswith("Dòng 1\n\nDòng 2"))  # spaces and blank lines cleaned
        self.assertTrue(y["description"].endswith("#AIagent #lậptrình #browserworkflow"))  # 3 hashtags, accents kept
        self.assertEqual(y["tags"][:2], ["AI agent", "lập trình"])  # '#' dropped
        self.assertEqual(len(y["tags"]), 5)  # duplicate 'ai agent' removed

    def test_variant_override(self):
        self.assertEqual(build_post.build(POST, "youtube", "youtube_short")["title"], "Short title")
        self.assertEqual(build_post.build(POST, "youtube")["title"], "Tự động hoá trình duyệt demo")

    def test_tiktok_override_and_hashtags(self):
        t = build_post.build(POST, "tiktok")
        self.assertIn("Bản ngắn", t["caption"])
        self.assertNotIn("Dòng 1", t["caption"])
        self.assertEqual(t["caption"].count("#"), 5)

    def test_description_that_starts_with_title_is_kept(self):
        post = {"title": "Hook.", "description": "Hook. And the rest of the text.", "tags": ["a"]}
        for platform, key in (("tiktok", "caption"), ("linkedin", "text"), ("facebook", "text")):
            self.assertEqual(build_post.build(post, platform)[key], "Hook. And the rest of the text.\n\n#a")

    def test_first_comment(self):
        post = {"title": "t", "description": "d", "first_comment": " Link: https://example.com ",
                "overrides": {"tiktok": {"first_comment": "x" * 200}, "linkedin": {"first_comment": ""}}}
        self.assertEqual(build_post.build(post, "youtube")["first_comment"], "Link: https://example.com")
        self.assertEqual(build_post.build(post, "youtube", "youtube_short")["first_comment"], "Link: https://example.com")
        self.assertEqual(build_post.build(post, "linkedin")["first_comment"], "")  # override can clear it
        tk = build_post.build(post, "tiktok")
        self.assertLessEqual(len(tk["first_comment"]), 150)
        self.assertTrue(tk["warnings"])
        self.assertEqual(build_post.build({"title": "t", "description": "d"}, "facebook")["first_comment"], "")

    def test_limits(self):
        long = {"title": "t", "description": "word " * 1200, "tags": ["a"]}
        for platform, key in (("tiktok", "caption"), ("linkedin", "text")):
            out = build_post.build(long, platform)
            self.assertLessEqual(len(out[key]), build_post.LIMITS[platform]["text"])
            self.assertTrue(out["warnings"])
            self.assertTrue(out[key].endswith("#a"))  # hashtags survive the cut

    def test_youtube_tag_budget(self):
        out = build_post.build({"title": "t", "description": "d", "tags": [f"tag number {i}" for i in range(80)]}, "youtube")
        used = sum(len(t) + 2 for t in out["tags"]) + len(out["tags"]) - 1
        self.assertLessEqual(used, 500)
        self.assertTrue(out["warnings"])


class CheckSrt(unittest.TestCase):
    def run_clean(self, raw, **kw):
        d = tempfile.mkdtemp()
        src = os.path.join(d, "c.srt")
        with open(src, "wb") as f:
            f.write(raw)
        res = check_srt.clean(src, os.path.join(d, "out.srt"), **kw)
        text = ""
        if res["ok"]:
            with open(res["clean_file"], encoding="utf-8") as f:
                text = f.read()
        return res, text, d

    def test_fixes(self):
        raw = ("﻿2\r\n0:00:03.5 --> 0:00:05.000\r\nXin chào\r\n\r\n"
               "1\r\n00:00:01,000 --> 00:00:02,000\r\nDòng đầu\r\nhai dòng\r\n\r\n"
               "7\r\n00:00:06,000 --> 00:00:07,000\r\n\r\n").encode("utf-8")
        res, text, _ = self.run_clean(raw)
        self.assertEqual(res["cues"], 2)
        self.assertEqual(text, "1\n00:00:01,000 --> 00:00:02,000\nDòng đầu\nhai dòng\n\n"
                               "2\n00:00:03,500 --> 00:00:05,000\nXin chào\n")
        self.assertEqual(res["problems"], [])
        self.assertIn("removed BOM", res["fixed"])

    def test_utf16_and_overlap(self):
        raw = "1\n00:00:01,000 --> 00:00:04,000\nMột\n\n2\n00:00:03,000 --> 00:00:05,000\nHai\n".encode("utf-16")
        res, text, _ = self.run_clean(raw)
        self.assertIn("Một", text)
        self.assertEqual(len(res["problems"]), 1)

    def test_facebook_copy(self):
        raw = b"1\n00:00:01,000 --> 00:00:02,000\nHi\n"
        res, _, d = self.run_clean(raw, facebook_locale="vi_VN", video="/x/demo.mp4")
        self.assertEqual(os.path.basename(res["facebook_file"]), "demo.vi_VN.srt")
        self.assertTrue(os.path.isfile(res["facebook_file"]))

    def test_not_srt(self):
        res, _, _ = self.run_clean(b"hello world\n")
        self.assertFalse(res["ok"])


if __name__ == "__main__":
    unittest.main()
