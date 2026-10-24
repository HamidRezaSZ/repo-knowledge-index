#!/usr/bin/env python3
"""Git-native Markdown knowledge retrieval: exact IDs + ranked FTS5 sections."""
from __future__ import annotations

import argparse
import json
import os
import re
import sqlite3
import sys
from pathlib import Path

import yaml

FRONTMATTER = re.compile(r"\A---\s*\n(.*?)\n---\s*\n", re.S)
HEADING = re.compile(r"^(#{1,6})[ \t]+(.+?)\s*#*\s*$")
WORD = re.compile(r"\w+", re.UNICODE)
SLUG = re.compile(r"[^\w-]+", re.UNICODE)


def parse_document(path: Path) -> tuple[dict, str]:
    raw = path.read_text(encoding="utf-8")
    match = FRONTMATTER.match(raw)
    if not match:
        raise ValueError(f"{path}: missing YAML frontmatter")
    metadata = yaml.safe_load(match.group(1))
    if not isinstance(metadata, dict):
        raise ValueError(f"{path}: YAML must be a mapping")
    for field in ("id", "title", "summary"):
        if not isinstance(metadata.get(field), str) or not metadata[field].strip():
            raise ValueError(f"{path}: missing/invalid {field}")
    for field in ("aliases", "tags", "related"):
        val = metadata.get(field, [])
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


def build(root: Path) -> dict:
    root = root.resolve()
    folder = root / "knowledge"
    if not folder.is_dir():
        raise ValueError(f"Missing knowledge directory: {folder}")
    docs, aliases, rows = {}, {}, []
    for path in sorted(folder.rglob("*.md")):
        if path.name in ("index.md", "log.md"):
            continue
        meta, body = parse_document(path)
        key = meta["id"]
        if key in docs:
            raise ValueError(f"Duplicate id: {key}")
        rel = path.relative_to(root).as_posix()
        docs[key] = {"path": rel, "title": meta["title"], "summary": meta["summary"],
                     "tags": meta.get("tags", []), "related": meta.get("related", [])}
        for alias in meta.get("aliases", []):
            alias = alias.strip().casefold()
            if not alias or alias in aliases:
                raise ValueError(f"Empty or duplicate alias: {alias!r}")
            aliases[alias] = key
        for label, slug, content in sections(body):
            rows.append((key, rel, label, slug, meta["title"],
                         " ".join(meta.get("tags", []) + meta.get("aliases", [])),
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
        with sqlite3.connect(tmp_db) as conn:
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
    sql = ("SELECT id, path, heading, slug, title, summary, "
           "snippet(sections, 7, '', '', ' … ', 18), "
           "bm25(sections, 0, 0, 4, 0, 6, 5, 4, 1) "
           "FROM sections WHERE sections MATCH ? ORDER BY rank LIMIT ?")
    # rank is the default BM25 score for FTS5; use the weighted score explicitly.
    sql = sql.replace("ORDER BY rank", "ORDER BY bm25(sections, 0, 0, 4, 0, 6, 5, 4, 1)")
    with sqlite3.connect(db_path) as conn:
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
    except (ValueError, OSError, sqlite3.Error, yaml.YAMLError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
