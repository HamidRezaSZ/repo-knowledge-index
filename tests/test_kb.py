import io
import json
import sqlite3
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
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

    def cli(self, *args):
        out, err = io.StringIO(), io.StringIO()
        with redirect_stdout(out), redirect_stderr(err):
            code = kb.main(["--root", str(self.root), *args])
        return code, out.getvalue(), err.getvalue()

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
        self.assertEqual(scores, sorted(scores, reverse=True))  # higher is better, best first
        self.assertEqual(kb.search(self.root, "!!!!"), [])

    def test_search_returns_only_matching_sections(self):
        self.put("auth.md", "---\nid: auth\ntitle: Authentication\nsummary: Login and refresh "
                            "tokens.\naliases: [jwt]\n---\n# Refresh tokens\nRotate them.\n"
                            "# Revoking sessions\nRefuse revoked ids.\n")
        kb.build(self.root)
        # The summary mentions refresh tokens, but only one section does.
        self.assertEqual([hit.get("slug") for hit in kb.search(self.root, "refresh token")],
                         ["refresh-tokens"])
        hits = kb.search(self.root, "jwt")  # only the alias matches: one document-level hit
        self.assertEqual([(hit["id"], hit.get("slug"), hit["summary"]) for hit in hits],
                         [("auth", None, "Login and refresh tokens.")])
        self.assertEqual(self.cli("search", "jwt")[1],
                         "knowledge/auth.md  Authentication\n  auth  Login and refresh tokens.\n")

    def test_document_fields_raise_section_rank(self):
        body = "# Notes\nA cache appears in this otherwise ordinary sentence.\n"
        self.put("a.md", sample("a", title="Notes", body=body))
        self.put("b.md", sample("b", title="Caching", body=body))
        kb.build(self.root)
        self.assertEqual([hit["id"] for hit in kb.search(self.root, "cache")], ["b", "a"])

    def test_search_matches_other_word_forms(self):
        body = ("# Refresh\nRotate refresh credentials. Revoked sessions are refused. "
                "Invalidate keys.\n")
        self.put("a.md", sample("auth", body=body))
        kb.build(self.root)
        for query in ("rotating", "revoke", "invalidation", "credential"):
            slugs = [hit["slug"] for hit in kb.search(self.root, query)]
            self.assertEqual(slugs, ["refresh"], query)

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
        self.assertEqual([section.heading for section in result], ["Usage", "Real"])
        self.assertIn("# Fake heading", result[0].content)

    def test_duplicate_headings_resolve_unambiguously(self):
        body = ("# Redis\n## Configuration\nSet maxmemory-policy.\n"
                "# Postgres\n## Configuration\nSet shared_buffers.\n"
                "# Example\na\n# Example-2\nb\n# Example\nc\n")
        self.put("db.md", sample("db", body=body))
        kb.build(self.root)
        self.assertEqual([section.slug for section in kb.sections(body)],
                         ["configuration", "configuration-2", "example", "example-2", "example-3"])
        hit = kb.search(self.root, "shared_buffers")[0]
        self.assertEqual(kb.get(self.root, "db", section=hit["slug"])["content"],
                         "Set shared_buffers.")
        self.assertEqual(kb.get(self.root, "db", section="example-3")["content"], "c")
        self.assertEqual(kb.get(self.root, "db", section="Example-2")["content"], "b")
        self.assertEqual(kb.get(self.root, "db", section="configuration")["content"],
                         "Set maxmemory-policy.")  # an exact slug, not the shared heading
        with self.assertRaisesRegex(ValueError, "ambiguous; use a slug: configuration, configur"):
            kb.get(self.root, "db", section="Configuration")
        with self.assertRaisesRegex(ValueError, "Unknown section 'nope'; sections: configuration,"):
            kb.get(self.root, "db", section="nope")

    def test_heading_text_keeps_trailing_hash(self):
        body = "# C#\na\n# F# tips\nb\n# Use C#  \nc\n# Closed ##\nd\n## Spaced  ###  \ne\n#hashtag\nf\n"
        self.assertEqual([section.heading for section in kb.sections(body)],
                         ["C#", "F# tips", "Use C#", "Closed", "Spaced"])

    def test_parent_headings_are_searchable(self):
        body = ("# Redis\n## Configuration\nSet maxmemory-policy.\n"
                "# Postgres\n## Configuration\nSet shared_buffers.\n"
                "### Pooling\nUse a pooler.\n## Backups\nNightly.\n")
        self.assertEqual([section.heading_path for section in kb.sections(body)],
                         ["Redis > Configuration", "Postgres > Configuration",
                          "Postgres > Configuration > Pooling", "Postgres > Backups"])
        self.put("db.md", sample("db", body=body))
        kb.build(self.root)
        hits = kb.search(self.root, "redis")
        self.assertEqual([(hit["slug"], hit["heading"]) for hit in hits],
                         [("configuration", "Redis > Configuration")])
        self.assertEqual(kb.get(self.root, "db", section="postgres > configuration")["content"],
                         "Set shared_buffers.")

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

    def test_frontmatter_yaml_subset(self):
        def parse(block):
            return kb.parse_frontmatter(block, Path("x.md"))

        block = ("id: a\ntitle: 'It''s: quoted'  # note\nsummary: Use C# here # comment\n"
                 "aliases: [auth, \"x, y\"]\ntags:\n  - one\n- two\nrelated:\n"
                 "type: concept\nowner:\n  team: platform\n")
        self.assertEqual(parse(block), {"id": "a", "title": "It's: quoted",
                                        "summary": "Use C# here", "aliases": ["auth", "x, y"],
                                        "tags": ["one", "two"], "related": None})
        folded = parse("summary: >\n  Folded\n  text\ntitle: Long\n  plain title\n")
        self.assertEqual(folded, {"summary": "Folded text", "title": "Long plain title"})
        for block, message in [("id: a\nid: b", "line 2: duplicate key"),
                               ("tags: [a,\n  b]", r"line 1: a \[...\] list must close"),
                               ('title: "open', "line 1: unterminated"),
                               ("title: {x: 1}", "line 1: unsupported YAML syntax"),
                               ("title T", "line 1: expected 'key: value'")]:
            with self.assertRaisesRegex(ValueError, message):
                parse(block)

    def test_empty_or_missing_list_fields(self):
        self.put("a.md", "---\nid: a\ntitle: A\nsummary: S\naliases:\ntags:\n---\n# A\nText.\n")
        kb.build(self.root)
        self.assertEqual(kb.get(self.root, "a", summary=True)["tags"], [])
        self.assertEqual(kb.get(self.root, "a", summary=True)["related"], [])
        self.put("b.md", "---\nid: b\ntitle: B\nsummary: S\ntags: oops\n---\n# B\nText.\n")
        with self.assertRaisesRegex(ValueError, "tags must be a list"):
            kb.build(self.root)

    def test_reserved_file_names(self):
        self.put("a.md", sample("a"))
        self.put("index.md", "# Catalog\n- [A](a.md)\n")
        self.put("guides/log.md", "---\ntype: log\n---\n# 2026-10-24\nChanged A.\n")
        self.assertEqual(kb.build(self.root)["documents"], 1)  # reserved files are skipped
        self.put("guides/log.md", sample("changelog"))
        with self.assertRaisesRegex(ValueError, "guides/log.md: index.md and log.md are reserved"):
            kb.build(self.root)

    def test_files_outside_repository_are_not_indexed(self):
        outside = tempfile.TemporaryDirectory()
        self.addCleanup(outside.cleanup)
        (Path(outside.name) / "secret.md").write_text(sample("ext"), encoding="utf-8")
        try:
            (self.root / "knowledge" / "shared").symlink_to(outside.name, target_is_directory=True)
        except OSError:
            self.skipTest("symlinks are not available")
        self.assertEqual(kb.build(self.root)["documents"], 0)  # directory links are not followed
        (self.root / "knowledge" / "ext.md").symlink_to(Path(outside.name) / "secret.md")
        with self.assertRaisesRegex(ValueError, "ext.md: resolves outside the repository"):
            kb.build(self.root)

    def test_file_with_byte_order_mark(self):
        (self.root / "knowledge" / "bom.md").write_bytes(b"\xef\xbb\xbf" + sample("bom").encode())
        self.assertEqual(kb.build(self.root), {"documents": 1, "sections": 1})
        self.assertEqual(kb.get(self.root, "bom")["content"], "# How it works\nToken rotation protects accounts.\n")

    def test_index_follows_source_changes(self):
        self.put("a.md", sample("alpha", body="# Intro\nalpha beta.\n"))
        kb.build(self.root)
        self.put("a.md", sample("alpha", body="# Intro\nzebra beta.\n"))  # same size, new content
        kb.ensure_index(self.root)
        self.assertEqual(kb.search(self.root, "zebra")[0]["id"], "alpha")
        (self.root / "knowledge" / "a.md").rename(self.root / "knowledge" / "b.md")
        index = kb.ensure_index(self.root)
        self.assertEqual(kb.get(self.root, "alpha", index=index)["path"], "knowledge/b.md")
        with mock.patch.object(kb, "build", wraps=kb.build) as spy:
            kb.ensure_index(self.root)
        spy.assert_not_called()  # nothing changed, nothing rebuilt
        (self.root / "knowledge" / "b.md").unlink()
        with self.assertRaisesRegex(ValueError, "no longer exists; the index is stale"):
            kb.get(self.root, "alpha")  # library calls do not rebuild by themselves

    def test_cli_rebuilds_stale_or_missing_index(self):
        self.put("a.md", sample("alpha"))
        code, out, _ = self.cli("search", "token", "--json")  # no build has run yet
        self.assertEqual((code, json.loads(out)[0]["id"]), (0, "alpha"))
        self.put("a.md", sample("alpha", title="Renamed"))
        code, out, _ = self.cli("get", "alpha", "--summary", "--json")
        self.assertEqual((code, json.loads(out)["title"]), (0, "Renamed"))

    def test_cli_text_output_and_refs(self):
        self.put("auth.md", sample("auth", title="Auth", aliases="[login]",
                                   body="# Refresh tokens\nRotate refresh\ntokens on use.\n"
                                        "# Other\nUnrelated.\n"))
        self.assertEqual(self.cli("build"), (0, "indexed 1 documents, 2 sections\n", ""))
        self.assertEqual(self.cli("search", "rotate")[1],
                         "knowledge/auth.md  Auth\n"
                         "  auth#refresh-tokens  Refresh tokens: Rotate refresh tokens on use.\n")
        self.assertEqual(self.cli("get", "login#refresh-tokens")[1],
                         "knowledge/auth.md#refresh-tokens  Auth > Refresh tokens\n\n"
                         "Rotate refresh\ntokens on use.\n")
        self.assertEqual(self.cli("get", "knowledge/auth.md#other")[1].splitlines()[-1],
                         "Unrelated.")
        self.assertEqual(self.cli("get", "auth", "--summary")[1],
                         "auth  Auth\npath: knowledge/auth.md\nsummary: About auth.\n"
                         "tags: security\n")
        self.assertEqual(self.cli("search", "zebra")[1], "no matches\n")
        self.assertEqual(self.cli("get", "auth#other", "--section", "other"),
                         (1, "", "error: give the section either as <id>#<slug> or with "
                                 "--section, not both\n"))

    def test_cli_json_output_is_compact(self):
        self.put("auth.md", sample("auth"))
        code, out, _ = self.cli("search", "rotation", "--json")
        groups = json.loads(out)
        self.assertEqual((code, out.count("\n")), (0, 1))  # one line, no indentation
        self.assertEqual(groups[0]["sections"][0]["ref"], "auth#how-it-works")
        self.assertEqual(sorted(groups[0]), ["id", "path", "sections", "title"])
        self.assertEqual(json.loads(self.cli("get", "auth#how-it-works", "--json")[1])["content"],
                         "Token rotation protects accounts.")

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
