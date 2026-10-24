# Repo Knowledge Index

A small, Git-native knowledge-retrieval prototype for AI coding agents. Source knowledge remains readable Markdown with YAML frontmatter; generated artifacts are a JSON ID/alias index and a local SQLite FTS5 section index. The CLI returns compact JSON results so agents can fetch selected sections rather than putting an entire repository into context.

**Status:** Functional lexical retrieval prototype and reproducible synthetic benchmark. Not a semantic/vector search engine or a validated winner across all projects. Read [the comparative research](docs/comparison.md) and [evaluation limitations](docs/evaluation.md).

## Quick start

Requires Python 3.10+ with SQLite FTS5 enabled (standard in python.org and most Linux builds). There are no third-party dependencies, so agents can run the CLI without installing anything.

```bash
python scripts/kb.py build
python scripts/kb.py search "refresh token" --limit 5
python scripts/kb.py get authentication --summary
python scripts/kb.py get auth --section refresh-tokens
python -m unittest discover -s tests -v
python -m benchmarks.compare --docs 300 --repeats 20
```

The source knowledge directory is `knowledge/`. The generated local artifacts live in `.knowledge/` and are ignored by Git. `search` and `get` rebuild them automatically when any knowledge file (or `kb.py` itself) changes, detected by a content hash. `build` does the same on demand and is what CI runs to validate the documents.

## Knowledge format

```markdown
---
id: authentication
title: Authentication and Session Lifecycle
summary: Login, access tokens, refresh tokens, and session revocation.
aliases: [auth, jwt]
tags: [identity, security]
related: [authorization]
---
# Refresh tokens
Rotate refresh tokens and reject replay.
```

Required fields: `id`, `title`, `summary`. Optional: `aliases`, `tags`, `related` (all lists of strings). Frontmatter is read as a small YAML subset: one `key: value` per line, where a value is plain or quoted text, a `[a, b]` list, indented `- item` lines, or a `|`/`>` text block, plus `#` comments. Other keys (for example OKF's `type`) are allowed and ignored; anything else in the six fields above fails with its line number. IDs must be unique lowercase path-safe strings and related IDs must exist. Files and IDs may be relocated independently, provided identifiers remain stable. Files must live inside the repository: a symlinked file that points outside it is rejected, and symlinked directories are not followed. Files named `index.md` or `log.md` are reserved for navigation and change history (as in OKF) and are never indexed; the build fails if one declares an `id`. Markdown is split into ATX-heading sections, each indexed with its heading path (for example `Postgres > Configuration`) so parent headings are searchable; SQL BM25 ranks heading path, title, tags, summary and section text. This schema is **OKF-inspired, not fully OKF-v0.2-compliant** (OKF requires `type` and uses path-derived concept IDs).

## Retrieval flow

1. A user asks about a project topic.
2. An agent tries a known ID or alias through the JSON index (average O(1) map lookup *after loading the JSON*).
3. If no known ID exists, the agent queries FTS5 for ranked sections. Query terms are safely quoted and combined with OR. Search is lexical, not semantic.
4. The agent inspects titles, snippets, scores, and paths, then requests the exact section it needs.
5. Only selected text is presented to the model, preserving original file paths for citations.

FTS5 query costs depend on posting-list sizes and ranking; the `O(1)` claim applies **only** to an in-memory hash lookup of a known ID or alias, not natural-language search or disk I/O.

## Repository contents

- `scripts/kb.py`: builder and `build`, `search`, `get` CLI
- `knowledge/`: sample corpus
- `tests/`: correctness and validation tests
- `benchmarks/compare.py`: repeatable warm in-process lexical baseline
- `docs/comparison.md`: comparative methods research and references
- `docs/evaluation.md`: benchmarking protocol, results and limitations
- `AGENTS.md`: retrieval instructions for coding agents

## Limitations

The index rebuilds in full and uses SQLite's Porter stemmer over Unicode tokens, so English word forms match ("revoke" finds "revoked") while other languages match whole words only. It doesn't implement semantic recall, incremental reindexing, graph queries or an MCP server. Markdown parsing handles ATX headings and fenced code blocks, not every CommonMark edge case. No LLM tokenizer or end-to-end agent test is included. See the docs for tradeoffs.

## License

MIT — see [LICENSE](LICENSE). Contributions: [CONTRIBUTING.md](CONTRIBUTING.md).
