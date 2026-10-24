#!/usr/bin/env python3
"""Git-native Markdown knowledge retrieval: exact IDs + ranked FTS5 sections."""
from __future__ import annotations

import argparse
import json
import os
import re
import sqlite3
import sys
from contextlib import closing
from pathlib import Path

FRONTMATTER = re.compile(r"\A---\s*\n(.*?)\n---\s*\n", re.S)
FIELDS = ("id", "title", "summary", "aliases", "tags", "related")
KEY_LINE = re.compile(r"([^\W\d][\w .-]*?)[ \t]*:(?:[ \t]+(.*))?$")
QUOTED = re.compile(r'"(?:[^"\\]|\\.)*"|\'(?:[^\']|\'\')*\'')
FLOW_ITEM = re.compile(r'[ \t]*("(?:[^"\\]|\\.)*"|\'(?:[^\']|\'\')*\'|[^,\]"\'\s][^,\]]*?)?'
                       r'[ \t]*([,\]])')
COMMENT_TAIL = re.compile(r"(?:[ \t]+#.*)?")
# A closing run of #s only counts when a space precedes it, so "# C#" keeps its "#".
HEADING = re.compile(r"^(#{1,6})[ \t]+(.+?)(?:[ \t]+#+)?[ \t]*$")
WORD = re.compile(r"\w+", re.UNICODE)
SLUG = re.compile(r"[^\w-]+", re.UNICODE)
RESERVED = ("index.md", "log.md")  # OKF navigation and change-history files; never indexed


def plain(text: str) -> str:
    """A plain YAML scalar without its trailing comment (a # at the start or after a space)."""
    return re.split(r"(?:^|[ \t])#", text, maxsplit=1)[0].strip()


def scalar(text: str, here: str) -> str | None:
    """A quoted or plain YAML scalar; plain null spellings become None."""
    if text[:1] not in ("'", '"'):
        value = plain(text)
        return None if value in ("", "~", "null", "Null", "NULL") else value
    match = QUOTED.match(text)
    if not match or not COMMENT_TAIL.fullmatch(text, match.end()):
        raise ValueError(f"{here}: unterminated or malformed quoted text")
    quoted = match.group()
    if quoted[0] == "'":
        return quoted[1:-1].replace("''", "'")
    try:
        return json.loads(quoted, strict=False)  # JSON escapes are a subset of YAML's
    except ValueError:
        raise ValueError(f"{here}: unsupported escape in quoted text") from None


def flow_list(text: str, here: str) -> list:
    """A one-line YAML list such as `[a, "b, c", 'd']`."""
    items, pos = [], 1
    while True:
        match = FLOW_ITEM.match(text, pos)
        if not match:
            raise ValueError(f"{here}: a [...] list must close on the same line")
        pos = match.end()
        if match.group(1) is not None:
            items.append(scalar(match.group(1), here))
        elif match.group(2) == ",":
            raise ValueError(f"{here}: empty list item")
        if match.group(2) == "]":
            break
    if not COMMENT_TAIL.fullmatch(text, pos):
        raise ValueError(f"{here}: unexpected text after the list")
    return items


def parse_frontmatter(block: str, where: Path) -> dict:
    """Read the YAML subset used by knowledge files; keys other than FIELDS are skipped.

    Values are plain or quoted text, `[a, b]` or `- item` lists, or `|`/`>` text blocks.
    Anything else in a known field fails with its line number instead of being guessed.
    """
    data: dict = {}
    key, mode, lines = None, None, []  # mode: how indented lines below `key` are read
    for number, line in enumerate(block.split("\n"), 1):
        here = f"{where}: frontmatter line {number}"
        indented, stripped = line[:1] in (" ", "\t"), line.strip()
        if mode in ("|", ">"):
            if indented or not stripped:
                lines.append(stripped)
                continue
            data[key] = "\n".join(lines).strip() if mode == "|" else " ".join(filter(None, lines))
            mode = None
        if not stripped or stripped.startswith("#"):
            continue
        if mode == "skip" and (indented or stripped.startswith("-")):
            continue
        if mode == "plain" and indented:  # a plain value continued on the next line
            data[key] = f"{data[key]} {plain(stripped)}"
            continue
        if stripped == "-" or stripped.startswith("- "):
            if mode not in ("list", "empty"):
                raise ValueError(f"{here}: unexpected list item")
            data[key], mode = (data[key] or []) + [scalar(stripped[1:].strip(), here)], "list"
            continue
        if indented:
            if mode != "empty":
                raise ValueError(f"{here}: unexpected indented line")
            data[key], mode = plain(stripped), "plain"  # `key:` with its value on the next line
            continue
        match = KEY_LINE.match(line)
        if not match:
            raise ValueError(f"{here}: expected 'key: value'")
        key, value = match.group(1), (match.group(2) or "").strip()
        if key not in FIELDS:
            key, mode = None, "skip"
            continue
        if key in data:
            raise ValueError(f"{here}: duplicate key {key!r}")
        data[key], mode = None, "empty"
        if value[:1] == "[":
            data[key], mode = flow_list(value, here), None
        elif value[:1] in ("|", ">"):
            if not re.fullmatch(r"[|>][1-9+-]{0,2}", plain(value)):
                raise ValueError(f"{here}: unsupported block header {value!r}")
            mode, lines = value[0], []
        elif value[:1] in ("{", "&", "*", "!"):
            raise ValueError(f"{here}: unsupported YAML syntax {value[:1]!r}")
        elif value[:1] in ("'", '"'):
            data[key], mode = scalar(value, here), None
        elif plain(value):
            data[key], mode = scalar(value, here), "plain"
    if mode in ("|", ">"):
        data[key] = "\n".join(lines).strip() if mode == "|" else " ".join(filter(None, lines))
    return data


def parse_document(path: Path) -> tuple[dict, str]:
    raw = path.read_text(encoding="utf-8-sig")  # -sig: tolerate a byte-order mark from Windows editors
    match = FRONTMATTER.match(raw)
    if not match:
        raise ValueError(f"{path}: missing YAML frontmatter")
    metadata = parse_frontmatter(match.group(1), path)
    for field in ("id", "title", "summary"):
        if not isinstance(metadata.get(field), str) or not metadata[field].strip():
            raise ValueError(f"{path}: missing/invalid {field}")
    for field in ("aliases", "tags", "related"):
        val = metadata.get(field)
        if val is None:  # absent, or an empty `field:` line
            val = metadata[field] = []
        if not isinstance(val, list) or not all(isinstance(v, str) for v in val):
            raise ValueError(f"{path}: {field} must be a list of strings")
    if not re.fullmatch(r"[a-z0-9][a-z0-9._/-]*", metadata["id"]):
        raise ValueError(f"{path}: id must be lowercase path-safe ASCII")
    return metadata, raw[match.end():]


def sections(body: str) -> list[tuple[str, str, str]]:
    """Split on Markdown ATX headings, excluding fenced code blocks."""
    result: list[tuple[str, str, str]] = []
    heading, lines = "Overview", []
    used: dict[str, int] = {}
    fence_char, fence_len = "", 0

    def flush() -> None:
        nonlocal lines
        content = "".join(lines).strip()
        if content:
            slug = SLUG.sub("-", heading.casefold()).strip("-") or "section"
            used[slug] = used.get(slug, 0) + 1
            if used[slug] > 1:
                slug += f"-{used[slug]}"
            result.append((heading, slug, content))
        lines = []

    for line in body.splitlines(keepends=True):
        fence = re.match(r"^\s{0,3}(\x60{3,}|~{3,})", line)
        if fence:
            marker = fence.group(1)
            if not fence_char:
                fence_char, fence_len = marker[0], len(marker)
            elif marker[0] == fence_char and len(marker) >= fence_len:
                fence_char, fence_len = "", 0
        match = HEADING.match(line.rstrip("\r\n")) if not fence_char else None
        if match:
            flush()
            heading = match.group(2).strip()
        else:
            lines.append(line)
    flush()
    return result or [("Overview", "overview", "")]


def locations(root: Path) -> tuple[Path, Path]:
    return root / ".knowledge" / "index.json", root / ".knowledge" / "search.db"


def source_files(root: Path) -> list[Path]:
    """Markdown files under knowledge/. Directory symlinks are not followed."""
    folder = root / "knowledge"
    if not folder.is_dir():
        raise ValueError(f"Missing knowledge directory: {folder}")
    found = [Path(directory, name) for directory, _, names in os.walk(folder)
             for name in names if name.endswith(".md")]
    for path in found:
        if not path.resolve().is_relative_to(root):
            rel = path.relative_to(root).as_posix()
            raise ValueError(f"{rel}: resolves outside the repository")
    return sorted(found)


def build(root: Path) -> dict:
    root = root.resolve()
    docs, aliases, rows = {}, {}, []
    for path in source_files(root):
        rel = path.relative_to(root).as_posix()
        if path.name in RESERVED:
            match = FRONTMATTER.match(path.read_text(encoding="utf-8-sig"))
            if match and re.search(r"^id[ \t]*:", match.group(1), re.MULTILINE):
                raise ValueError(f"{rel}: index.md and log.md are reserved and never indexed; "
                                 "rename the file to index it")
            continue
        meta, body = parse_document(path)
        key = meta["id"]
        if key in docs:
            raise ValueError(f"Duplicate id: {key}")
        docs[key] = {"path": rel, "title": meta["title"], "summary": meta["summary"],
                     "tags": meta["tags"], "related": meta["related"]}
        for alias in meta["aliases"]:
            alias = alias.strip().casefold()
            if not alias or alias in aliases:
                raise ValueError(f"Empty or duplicate alias: {alias!r}")
            aliases[alias] = key
        for label, slug, content in sections(body):
            rows.append((key, rel, label, slug, meta["title"],
                         " ".join(meta["tags"] + meta["aliases"]),
                         meta["summary"], content))
    for key, entry in docs.items():
        if key in aliases and aliases[key] != key:
            raise ValueError(f"ID conflicts with alias: {key}")
        for related in entry["related"]:
            if related not in docs:
                raise ValueError(f"Unknown related id {related!r} in {key}")
    index = {"by_id": docs, "by_alias": aliases}
    index_path, db_path = locations(root)
    db_path.parent.mkdir(parents=True, exist_ok=True)
    tmp_db = db_path.with_suffix(".tmp.db")
    tmp_json = index_path.with_suffix(".tmp.json")
    try:
        tmp_db.unlink(missing_ok=True)
        with closing(sqlite3.connect(tmp_db)) as conn:
            conn.execute("CREATE VIRTUAL TABLE sections USING fts5("
                         "id UNINDEXED, path UNINDEXED, heading, slug UNINDEXED, "
                         "title, tags, summary, content, tokenize='unicode61')")
            conn.executemany("INSERT INTO sections VALUES (?, ?, ?, ?, ?, ?, ?, ?)", rows)
            conn.commit()
        tmp_json.write_text(json.dumps(index, indent=2, ensure_ascii=False, sort_keys=True) + "\n",
                            encoding="utf-8")
        os.replace(tmp_db, db_path)
        os.replace(tmp_json, index_path)
    finally:
        tmp_db.unlink(missing_ok=True)
        tmp_json.unlink(missing_ok=True)
    return {"documents": len(docs), "sections": len(rows)}


def load_index(root: Path) -> dict:
    path, _ = locations(root)
    if not path.is_file():
        raise ValueError("Index missing; run 'build' first")
    return json.loads(path.read_text(encoding="utf-8"))


def get(root: Path, identifier: str, *, summary: bool = False, section: str | None = None) -> dict:
    index = load_index(root)
    key = identifier.casefold()
    key = index["by_alias"].get(key, key)
    entry = index["by_id"].get(key)
    if entry is None:
        raise ValueError(f"Unknown id or alias: {identifier}")
    result = {"id": key, **entry}
    if summary:
        return result
    path = (root.resolve() / entry["path"]).resolve()
    if not path.is_relative_to(root.resolve()):
        raise ValueError("Unsafe indexed path")
    _, body = parse_document(path)
    if section is not None:
        found = next((content for heading, slug, content in sections(body)
                      if section.casefold() in (heading.casefold(), slug.casefold())), None)
        if found is None:
            raise ValueError(f"Unknown section: {section}")
        body = found
    result["content"] = body
    return result


def search(root: Path, query: str, limit: int = 5) -> list[dict]:
    _, db_path = locations(root)
    if not db_path.is_file():
        raise ValueError("Search database missing; run 'build' first")
    tokens = WORD.findall(query.casefold())[:24]
    if not tokens:
        return []
    expression = " OR ".join('"' + token.replace('"', '""') + '"' for token in tokens)
    # bm25 weights per column: id, path, heading, slug, title, tags, summary, content.
    sql = ("SELECT id, path, heading, slug, title, summary, "
           "snippet(sections, 7, '', '', ' … ', 18), "
           "bm25(sections, 0, 0, 4, 0, 6, 5, 4, 1) AS score "
           "FROM sections WHERE sections MATCH ? ORDER BY score LIMIT ?")
    with closing(sqlite3.connect(db_path)) as conn:
        records = conn.execute(sql, (expression, limit)).fetchall()
    return [dict(zip(("id", "path", "heading", "slug", "title", "summary", "snippet", "score"), r))
            for r in records]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("build")
    q = commands.add_parser("search")
    q.add_argument("query")
    q.add_argument("--limit", type=int, default=5)
    g = commands.add_parser("get")
    g.add_argument("id")
    g.add_argument("--summary", action="store_true")
    g.add_argument("--section")
    args = parser.parse_args()
    try:
        if args.command == "build":
            output = build(args.root)
        elif args.command == "search":
            if not 1 <= args.limit <= 100:
                raise ValueError("--limit must be between 1 and 100")
            output = search(args.root, args.query, args.limit)
        else:
            if args.summary and args.section:
                raise ValueError("--summary and --section are mutually exclusive")
            output = get(args.root, args.id, summary=args.summary, section=args.section)
        print(json.dumps(output, indent=2, ensure_ascii=False))
        return 0
    except (ValueError, OSError, sqlite3.Error) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
