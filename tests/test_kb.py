import json
import tempfile
import unittest
from pathlib import Path

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


if __name__ == "__main__":
    unittest.main()
