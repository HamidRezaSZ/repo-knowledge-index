# Repo Knowledge Index

A small, Git-native knowledge-retrieval tool for AI coding agents. Knowledge stays in readable Markdown files with YAML frontmatter. A generated JSON ID/alias index and a SQLite FTS5 section index let an agent search those files and fetch one section instead of putting whole files or the repository into its context. Output is compact plain text, or compact JSON with `--json`.

**Status:** working lexical-retrieval prototype with reproducible token-usage and latency benchmarks. [docs/evaluation.md](docs/evaluation.md) covers what has been measured and what the numbers do not show; [docs/comparison.md](docs/comparison.md) compares this approach with others.

## Quick start

Requires Python 3.10+ with SQLite FTS5 enabled (standard in python.org and most Linux builds). There are no third-party dependencies, so agents can run the CLI without installing anything.

```bash
python scripts/kb.py build
python scripts/kb.py list
python scripts/kb.py search "refresh token" --limit 5
python scripts/kb.py get authentication --summary
python scripts/kb.py get auth#refresh-tokens
python -m unittest discover -s tests -v
python -m benchmarks.tokens
python -m benchmarks.compare --docs 300 --repeats 20
```

`search` prints one header line per matching document, then one line per section starting with a ready-to-use reference:

```text
knowledge/authentication.md  Authentication and Session Lifecycle
  authentication#refresh-tokens  Refresh tokens: Refresh tokens allow a client to obtain another access token. Rotate refresh credentials and reject replay of an...
```

`get` accepts that reference, or an id, alias or file path with an optional `#slug`, and prints the citation path on its first line, then the text. `get <id> --summary` prints the document's metadata and its sections as references, and `list` prints every document as one `id  title: summary` line. Add `--json` to any command for compact JSON; search scores there are BM25-based, and higher is better.

## Use in another repository

Copy `scripts/kb.py` into that repository's `scripts/` folder, put documents in `knowledge/`, and paste the "Answering questions from the knowledge base" section of [AGENTS.md](AGENTS.md) into its `AGENTS.md` or `CLAUDE.md`. The CLI treats the folder above `scripts/` as the repository root; `--root` overrides it.

## Index and catalog

Source knowledge lives in `knowledge/`; the generated index lives in `.knowledge/`, which Git ignores. `list`, `search` and `get` rebuild the index automatically when any knowledge file (or `kb.py` itself) changes, detected by a content hash. `build` does the same on demand and is what CI runs to validate the documents.

`build` also writes [`knowledge/index.md`](knowledge/index.md), a catalog for people browsing the repository with one linked line per document. Commit it with your document changes; CI fails when it is out of date. A hand-written `knowledge/index.md` (one without the generated first line) is never overwritten.

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

- Required fields: `id`, `title`, `summary`. Optional: `aliases`, `tags`, `related` (lists of strings). IDs must be unique lowercase path-safe strings, and `related` IDs must exist. Files can move freely as long as their IDs stay the same.
- Frontmatter is read as a small YAML subset: one `key: value` per line, where a value is plain or quoted text, a `[a, b]` list, indented `- item` lines, or a `|`/`>` text block, plus `#` comments. Other keys (for example OKF's `type`) are allowed and ignored; anything else in the six fields above fails with its line number.
- Files must live inside the repository: a symlinked file that points outside it is rejected, and symlinked directories are not followed. Files named `index.md` or `log.md` are reserved for navigation and change history (as in OKF) and are never indexed; the build fails if one declares an `id`.
- The schema is inspired by the [Open Knowledge Format](https://github.com/GoogleCloudPlatform/knowledge-catalog/blob/main/okf/SPEC.md) but does not conform to OKF v0.2, which requires a `type` field and derives concept IDs from file paths.

## How retrieval works

1. A user asks about a project topic.
2. If the agent knows an ID or alias, it looks it up in the JSON index, or scans `list` to find one; `get <id> --summary` shows the document's sections.
3. Otherwise it searches. Query words are quoted and combined with OR. Each Markdown section (split at ATX headings) is indexed with its heading path, for example `Postgres > Configuration`, so parent headings are searchable. A section is returned only when its own heading path or text matches; BM25 ranks it on those, plus its document's title, tags and summary. A document that matches only on those fields, for example through an alias, is returned once with its summary.
4. The agent reads titles, heading paths and snippets, then fetches the section it needs by its `id#slug` reference.
5. Only that text reaches the model, along with the original file path for citations.

## Repository contents

- `scripts/kb.py`: builder and `build`, `list`, `search`, `get` CLI
- `knowledge/`: sample corpus and its generated catalog
- `tests/`: correctness and validation tests
- `benchmarks/tokens.py` and `benchmarks/questions.json`: tokens an agent receives versus reading whole files, on labeled questions
- `benchmarks/compare.py`: repeatable warm in-process lexical baseline
- `docs/comparison.md`: comparative methods research and references
- `docs/evaluation.md`: benchmarking protocol, results and limitations
- `AGENTS.md`: retrieval instructions for coding agents

## Limitations

Search is lexical. SQLite's Porter stemmer runs over Unicode tokens, so English word forms match ("revoke" finds "revoked"), other languages match whole words only, and paraphrases that share no words are missed. There is no semantic recall, incremental reindexing, graph query or MCP server, and the index rebuilds in full. Markdown parsing handles ATX headings and fenced code blocks, not every CommonMark edge case. Token counts use OpenAI's `o200k_base` encoding as a proxy for Claude's tokenizer, and no end-to-end agent test is included.

## License

MIT — see [LICENSE](LICENSE). Contributions: [CONTRIBUTING.md](CONTRIBUTING.md).
