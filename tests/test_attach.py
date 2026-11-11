"""attach.py: a file cut into parts joins back to the same bytes, and the snippets carry the right facts."""
import hashlib
import json
import os
import re
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "skills", "post-video", "scripts"))
import attach  # noqa: E402


class Attach(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()

    def make(self, name, size):
        path = os.path.join(self.tmp, name)
        with open(path, "wb") as f:
            f.write(os.urandom(size))
        return path

    def want(self, res):
        return json.loads(re.search(r"const want = (\{.*?\});\n", res["finish_js"]).group(1))

    def test_large_file_is_cut_and_joins_back(self):
        src = self.make("video é.mp4", attach.PART * 2 + 12345)
        res = attach.split(src, self.tmp, accept="video")
        self.assertEqual(len(res["parts"]), 3)
        self.assertTrue(all(os.path.getsize(p) <= attach.PART for p in res["parts"]))
        self.assertTrue(all(p.startswith(os.path.join(self.tmp, attach.FOLDER)) for p in res["parts"]))
        joined = b""
        for p in res["parts"]:
            with open(p, "rb") as f:
                joined += f.read()
        with open(src, "rb") as f:
            self.assertEqual(joined, f.read())
        want = self.want(res)
        self.assertEqual(want["sha256"], hashlib.sha256(joined).hexdigest())
        self.assertEqual((want["name"], want["size"], want["type"], want["accept"]),
                         ("video é.mp4", len(joined), "video/mp4", "video"))
        self.assertEqual(want["parts"], [os.path.basename(p) for p in res["parts"]])
        self.assertNotIn("warning", res)

    def test_exact_multiple_and_small_and_empty(self):
        self.assertEqual(len(attach.split(self.make("a.mp4", attach.PART), self.tmp)["parts"]), 1)
        res = attach.split(self.make("c.srt", 10), self.tmp, accept="srt", selector="#cc")
        self.assertEqual(len(res["parts"]), 1)
        self.assertEqual(self.want(res)["selector"], "#cc")
        self.assertEqual(len(attach.split(self.make("e.srt", 0), self.tmp)["parts"]), 1)

    def test_clean(self):
        attach.split(self.make("a.mp4", 10), self.tmp)
        self.assertTrue(attach.clean(self.tmp)["removed"])
        self.assertFalse(os.path.exists(os.path.join(self.tmp, attach.FOLDER)))
        self.assertFalse(attach.clean(self.tmp)["removed"])


if __name__ == "__main__":
    unittest.main()
