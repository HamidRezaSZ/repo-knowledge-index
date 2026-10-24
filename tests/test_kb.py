import json
import sqlite3
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from scripts import kb


def sample(id_, title="Sample", aliases="[]", related="[]", body="# How it works\nToken rotation protects accounts.\n"):
    return (f"---\nid: {id_}\ntitle: {title}\nsummary: About {id_}.\n"
            f"aliases: {aliases}\ntags: [security]\nrelated: {related}\n---\n{body}")


class KBTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        (self.root / "knowledge").mkdir()

    def put(self, filename, content):
        target = self.root / "knowledge" / filename
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content, encoding="utf-8")

    def test_build_and_get_alias(self):
        self.put("auth.md", sample("auth", aliases="[login, jwt]"))
        self.assertEqual(kb.build(self.root), {"documents": 1, "sections": 1})
        self.assertEqual(kb.get(self.root, "jwt", summary=True)["id"], "auth")
        self.assertEqual(kb.get(self.root, "login", section="how-it-works")["content"],
                         "Token rotation protects accounts.")
        self.assertTrue((self.root / ".knowledge" / "index.json").exists())

    def test_search_returns_section(self):
        self.put("auth.md", sample("auth", aliases="[login]"))
        self.put("cache.md", sample("cache", body="# Cache\nInvalidation of cache keys.\n"))
        kb.build(self.root)
        hits = kb.search(self.root, "token rotation")
        self.assertEqual(hits[0]["id"], "auth")
        self.assertEqual(hits[0]["slug"], "how-it-works")
        scores = [hit["score"] for hit in kb.search(self.root, "token cache security")]
        self.assertEqual(scores, sorted(scores))  # bm25: lower is better, best first
        self.assertEqual(kb.search(self.root, "!!!!"), [])

    def test_duplicates_and_conflicts(self):
        self.put("a.md", sample("auth", aliases="[login]"))
        self.put("b.md", sample("auth"))
        with self.assertRaisesRegex(ValueError, "Duplicate id"):
            kb.build(self.root)
        (self.root / "knowledge" / "b.md").write_text(sample("login"), encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "ID conflicts"):
            kb.build(self.root)

    def test_bad_related_reference(self):
        self.put("a.md", sample("auth", related="[missing]"))
        with self.assertRaisesRegex(ValueError, "Unknown related"):
            kb.build(self.root)

    def test_fenced_headings_not_sections(self):
        body = "# Usage\nRun command.\n" + "\x60\x60\x60markdown\n# Fake heading\n\x60\x60\x60\n## Real\nActual details.\n"
        result = kb.sections(body)
        self.assertEqual([row[0] for row in result], ["Usage", "Real"])
        self.assertIn("# Fake heading", result[0][2])

    def test_heading_text_keeps_trailing_hash(self):
        body = "# C#\na\n# F# tips\nb\n# Use C#  \nc\n# Closed ##\nd\n## Spaced  ###  \ne\n#hashtag\nf\n"
        self.assertEqual([row[0] for row in kb.sections(body)],
                         ["C#", "F# tips", "Use C#", "Closed", "Spaced"])

    def test_rebuild_discards_deleted_document(self):
        self.put("a.md", sample("old"))
        kb.build(self.root)
        (self.root / "knowledge" / "a.md").unlink()
        self.put("b.md", sample("new"))
        kb.build(self.root)
        self.assertEqual(kb.search(self.root, "token")[0]["id"], "new")
        self.assertNotIn("old", json.loads((self.root / ".knowledge" / "index.json").read_text())["by_id"])

    def test_invalid_yaml_and_absent_build(self):
        self.put("a.md", "# Without frontmatter")
        with self.assertRaisesRegex(ValueError, "frontmatter"):
            kb.build(self.root)
        with self.assertRaisesRegex(ValueError, "run 'build'"):
            kb.search(self.root, "token")

    def test_empty_or_missing_list_fields(self):
        self.put("a.md", "---\nid: a\ntitle: A\nsummary: S\naliases:\ntags:\n---\n# A\nText.\n")
        kb.build(self.root)
        self.assertEqual(kb.get(self.root, "a", summary=True)["tags"], [])
        self.assertEqual(kb.get(self.root, "a", summary=True)["related"], [])
        self.put("b.md", "---\nid: b\ntitle: B\nsummary: S\ntags: oops\n---\n# B\nText.\n")
        with self.assertRaisesRegex(ValueError, "tags must be a list"):
            kb.build(self.root)

    def test_file_with_byte_order_mark(self):
        (self.root / "knowledge" / "bom.md").write_bytes(b"\xef\xbb\xbf" + sample("bom").encode())
        self.assertEqual(kb.build(self.root), {"documents": 1, "sections": 1})
        self.assertEqual(kb.get(self.root, "bom")["content"], "# How it works\nToken rotation protects accounts.\n")

    def test_database_connections_are_closed(self):
        opened = []
        real_connect = sqlite3.connect

        def tracking_connect(*args, **kwargs):
            opened.append(real_connect(*args, **kwargs))
            return opened[-1]

        self.put("a.md", sample("auth"))
        with mock.patch.object(sqlite3, "connect", tracking_connect):
            kb.build(self.root)
            kb.search(self.root, "token")
        self.assertEqual(len(opened), 2)
        for conn in opened:
            with self.assertRaises(sqlite3.ProgrammingError):  # raised only by closed connections
                conn.execute("SELECT 1")


if __name__ == "__main__":
    unittest.main()
