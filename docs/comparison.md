# Research: retrieval strategies for AI coding agents

## Question and decision

How should a coding agent discover relevant, Git-versioned project knowledge without loading the full repository into its context? The compared methods are **not all competitors**: Markdown/OKF are source formats; AGENTS.md and CLAUDE.md provide agent instructions; MCP is an integration interface; grep, FTS, vector and graph retrieval are discovery mechanisms.

**Default recommendation:** keep human-readable Markdown with YAML metadata in Git; provide stable IDs and a generated JSON alias index for known-key lookups; use SQLite FTS5/BM25 on sections for unfamiliar lexical questions; return small snippets before fetching the selected section. Where agents ask in different words from the documents, add an optional vector search over the same sections. This is a low-dependency design choice; what has actually been measured is in [evaluation.md](evaluation.md).

## Comparison matrix

| Approach | Strength | Limitations and costs |
| --- | --- | --- |
| AGENTS.md / CLAUDE.md | Standard agent entry point, rules and navigation | Instruction context itself can grow; not a search engine |
| Plain Markdown with links/index.md | Portable human browsing and progressive disclosure | Without search, unfamiliar-topic navigation takes multiple steps |
| OKF-style YAML + Markdown | Structured metadata, portability, provenance | OKF doesn't prescribe a retrieval runtime |
| grep / ripgrep | Efficient, fresh literal searches without building an index | Worst-case corpus scan; relevance ranking is limited |
| JSON hash map | Average O(1) **in-memory** known-ID or alias lookup | Loading the map is O(N); cannot answer arbitrary search by itself |
| SQLite FTS5 / BM25 | Inverted-index lexical discovery and ranked section snippets | Index freshness, tokenizer configuration and synonym misses |
| Vector embeddings / ANN | Synonyms and paraphrases even without literal overlap | Embedding latency, model/index memory, update cost and relevance tuning |
| Hybrid lexical + vector | Exact identifiers plus paraphrased queries | Two indexes, fusion/reranking and evaluation overhead |
| Knowledge graph | Explicit entities, multi-hop relationships and structured constraints | Extraction/modeling cost and consistency maintenance |
| MCP | Standard tool/resource interface for agent clients | Adds transport and permission surface; not a ranking algorithm |

## Complexity is more nuanced than a single big-O number

For N documents and T bytes of text: a full text scan has O(T) worst-case work, although practical implementations such as ripgrep are highly optimized, and an early positive scan may finish quickly. Loading a JSON mapping costs O(N), then keyed in-memory lookup is expected O(1), *excluding loading and file IO*. FTS5 uses inverted lists: retrieval and rank costs depend on postings touched, query and result sizes. Brute-force vector search compares N vectors of d dimensions with O(Nd) arithmetic; ANN complexity is algorithm- and data-dependent, with recall trade-offs. Graph queries depend on their graph pattern and cardinality. Neither average query latency nor agent token cost is O(1) merely because a JSON map exists.

**Token efficiency is a policy.** All methods can return either a short section or the entire document. Compare them under equal context budgets, with a declared tokenizer, answer quality labels, search/tool latency and indexing/maintenance measurements.

## Practical decision path

1. Keep AGENTS.md concise; organize canonical Markdown; use ripgrep as a no-index baseline.
2. Add YAML metadata and stable IDs when reuse, links, aliases or summary previews justify them.
3. Add JSON and FTS5 when discovery calls are frequent enough to repay indexing and maintenance costs.
4. Index sections, return paths and snippets, then fetch only relevant content. Rebuild when sources change.
5. Collect real questions labeled by relevant section IDs. Measure Recall@k, MRR, answer accuracy, p50/p95 end-to-end latency, token counts and index update costs.
6. Add semantic or hybrid retrieval only after demonstrating that lexical methods miss significant paraphrased queries. Use knowledge graphs for explicit multi-hop requirements and MCP only when client interoperability is needed.

## Existing tools

Checked on 2026-10-27 against each project's README, and for QMD also its source. QMD 2.8.3 was also installed and benchmarked ([results](evaluation.md#retrieval-quality)); Cognee and LangGraph were not run.

### QMD

[QMD](https://github.com/tobi/qmd) (MIT; latest release 2.8.3, 2026-08-16) is the closest existing tool: a local search engine for Markdown notes, documentation and transcripts, built for agents, that also ranks with SQLite FTS5 and BM25. Unlike plain search here, it adds vector and hybrid search.

| | `kb.py` (this project) | QMD |
| --- | --- | --- |
| Install | One Python 3.10+ file, standard library only, copied into the repository; QMD as well for `--semantic` | npm or Bun package; Node.js 22+ or Bun 1.0+; Homebrew SQLite on macOS |
| Models | None; `--semantic` uses QMD's embedding model only | About 2.3 GB of local models for embeddings (~330 MB), reranking (~640 MB) and query expansion (~1.3 GB), downloaded on first use; BM25 `search` uses no LLM, while `vsearch` and `query` run the expansion model |
| Corpus | The repository's `knowledge/` folder | Any number of named collections, selected by glob (default `**/*.md`) |
| Metadata | Required `id`, `title`, `summary`; optional `aliases`, `tags`, `related`; the build fails on invalid, duplicate or dangling values | Optional; only a `qmd.metadata` frontmatter block becomes filterable fields, and the rest stays searchable text. Per-folder descriptions ("context") live in QMD's config |
| Keyword index | One FTS5 row per Markdown section, plus one per document for title, tags, aliases and summary; Porter stemming | One FTS5 row per document (path, title, body); Porter stemming |
| Keyword query | Any query word can match (OR); BM25 ranks sections, raised by matches on their document's fields | Every query word must match (AND), and plain words also match as prefixes |
| Semantic search | Optional: `--semantic` has QMD embed one file per section and merges its vector ranking with sections holding every query word | `vsearch` over ~900-token chunks with 15% overlap; `query` expands the query with a local LLM, fuses BM25 and vector ranks (reciprocal rank fusion), then reranks with a second model |
| Results | One line per matching section with an `id#slug` reference; `get` returns that section | Path, docid, line number and snippet per document; `get` takes a path or docid, optionally with a line range |
| Reference stability | IDs survive file moves and edits; a slug changes only when its heading does | Paths change when files move; the docid is the first 6 characters of the content hash, so it changes on every edit |
| Index | `.knowledge/` in the repository (Git-ignored), rebuilt in full by any command after a knowledge file or `kb.py` changes; `--semantic` also keeps a QMD index in QMD's cache, refreshed the same way | `~/.cache/qmd/index.sqlite` by default, or project-local after `qmd init`; refreshed by running `qmd update`, then `qmd embed` for vectors |
| Agent interface | CLI, plus instructions pasted into AGENTS.md or CLAUDE.md | CLI (`--json`, `--files`), MCP server over stdio or HTTP, Claude Code plugin, Node/Bun library |

QMD covers what plain search here leaves out: reworded questions, many collections and MCP clients. The price is a Node runtime, up to 2.3 GB of models and an index each machine builds and refreshes with `qmd update`. This project targets knowledge kept and reviewed in one repository and read by agents that may not be able to install anything: the index rebuilds itself, and search points straight at a section by a reference that survives file moves. QMD's keyword search ranks whole documents, and an agent narrows them with a line range.

This project therefore uses QMD as an optional engine, not a replacement. `search --semantic` writes each section to its own file, has QMD embed them, and merges QMD's vector ranking with the sections that contain every query word ([how it works](../README.md#optional-semantic-search-with-qmd)). On the [retrieval benchmark](evaluation.md#retrieval-quality), it put the right section first for 19 of 28 reworded questions, against none for plain search, without losing any other question, at about 4.4 s per call against 0.1 s. QMD's own keyword search found nothing for 34 of the 78 questions because it requires every word, and its full `query` pipeline took 72 s for a new question on the benchmark's CPU. Its keyword rules did not improve plain search either, so plain search is unchanged.

### Cognee

[Cognee](https://github.com/topoteretes/cognee) (Apache-2.0; release 1.6.1, 2026-09-24) is a memory platform for agents. `remember` turns documents, code and conversations into a knowledge graph plus vector embeddings, and `recall` searches them. It runs locally, using a GLiNER extraction model and a local embedding model when no LLM key is set, and ships an MCP server. It is the knowledge-graph row above as a product: knowledge lives in Cognee's databases instead of reviewed Markdown, a model extracts the graph instead of authors writing it, and the dependency stack is large (`dlt` is now a core dependency). Here, the `related` field is a small hand-written graph. Cognee becomes a candidate baseline once real questions need multi-hop answers.

### LangGraph

[LangGraph](https://github.com/langchain-ai/langgraph) (MIT; release 1.2.18, 2026-10-26) is a framework for building stateful agents, with durable execution, human-in-the-loop and short- and long-term memory. It works one layer above retrieval, so it does not compete with this project: an agent built with it would call `kb.py` or QMD as a tool.

## Primary sources

- [Google Cloud Open Knowledge Format v0.2](https://github.com/GoogleCloudPlatform/knowledge-catalog/blob/main/okf/SPEC.md) — Markdown/YAML structure, optional index.md, provenance, format vs runtime. How this project's schema differs is in the [README](../README.md#knowledge-format).
- [AGENTS.md](https://agents.md/) — agent instructions convention, not retrieval indexing.
- [SQLite FTS5 manual](https://www.sqlite.org/fts5.html) — MATCH, tokenizer, snippets, BM25 ranking.
- [ripgrep](https://github.com/BurntSushi/ripgrep) — text-search implementation and baseline.
- [FAISS](https://github.com/facebookresearch/faiss) — vector index and similarity retrieval.
- [MCP specification](https://modelcontextprotocol.io/specification/2025-06-18) — client/tool protocol.
- [OpenAI retrieval documentation](https://platform.openai.com/docs/guides/retrieval) — semantic retrieval concepts.
- [QMD](https://github.com/tobi/qmd) — README and `src/store.ts`: FTS5 schema, keyword query syntax, docids, hybrid pipeline.
- [Cognee](https://github.com/topoteretes/cognee) — memory API, local models, MCP server.
- [LangGraph](https://github.com/langchain-ai/langgraph) — agent orchestration framework.
