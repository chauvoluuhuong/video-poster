"""learn.py keeps a short, replaced-not-appended notes file per platform."""
import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "skills", "post-video", "scripts"))
import attach  # noqa: E402
import learn  # noqa: E402


class Learn(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self._folder, learn.folder = learn.folder, lambda: os.path.join(self.tmp, "learned")
        self.addCleanup(lambda: setattr(learn, "folder", self._folder))

    def test_save_replaces_and_stamps(self):
        self.assertEqual(learn.show("youtube"), "")
        self.assertIsNone(learn.save("youtube", "## Do\n- first\n", today="2026-11-12"))
        self.assertIsNone(learn.save("youtube", "Updated: 2026-01-01\n## Do\n- second   \n", today="2026-11-13"))
        self.assertEqual(learn.show("youtube"), "Updated: 2026-11-13\n## Do\n- second\n")  # replaced, one date line
        self.assertEqual(learn.show("tiktok"), "")

    def test_too_long_is_refused_and_keeps_the_old_notes(self):
        learn.save("tiktok", "- ok", today="2026-11-12")
        error = learn.save("tiktok", "\n".join(f"- line {i}" for i in range(learn.MAX_LINES + 1)))
        self.assertIn("too long", error)
        self.assertEqual(learn.show("tiktok"), "Updated: 2026-11-12\n- ok\n")

    def test_empty_removes_the_file(self):
        learn.save("linkedin", "- x")
        learn.save("linkedin", "  \n")
        self.assertFalse(os.path.exists(learn.path_of("linkedin")))


class AttachTag(unittest.TestCase):
    def test_two_uploads_of_one_file_get_separate_folders(self):
        tmp = tempfile.mkdtemp()
        src = os.path.join(tmp, "v.mp4")
        with open(src, "wb") as f:
            f.write(b"x" * 100)
        a = attach.split(src, tmp, tag="youtube-wide")
        b = attach.split(src, tmp, tag="linkedin-wide")
        self.assertNotEqual(os.path.dirname(a["parts"][0]), os.path.dirname(b["parts"][0]))
        self.assertTrue(os.path.isfile(a["parts"][0]) and os.path.isfile(b["parts"][0]))  # the second did not wipe the first


if __name__ == "__main__":
    unittest.main()
