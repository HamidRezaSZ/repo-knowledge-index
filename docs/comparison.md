# Research: retrieval strategies for AI coding agents

## Question and decision

How should a coding agent discover relevant, Git-versioned project knowledge without loading the full repository into its context? The compared methods are **not all competitors**: Markdown/OKF are source formats; AGENTS.md and CLAUDE.md provide agent instructions; MCP is an integration interface; grep, FTS, vector and graph retrieval are discovery mechanisms.

**Default recommendation:** keep human-readable Markdown with YAML metadata in Git; provide stable IDs and a generated JSON alias index for known-key lookups; use SQLite FTS5/BM25 on sections for unfamiliar lexical questions; return small snippets before fetching the selected section. This is a low-dependency design recommendation, not proof that the method outperforms everything.

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

**Token efficiency is a policy.** All methods can return either a short section or the entire document. Compare them under equal context budgets, with a declared tokenizer, answer quality labels, search/tool latency and indexing/maintenance measurements before claiming a winner.

## Practical decision path

1. Keep AGENTS.md concise; organize canonical Markdown; use ripgrep as a no-index baseline.
2. Add YAML metadata and stable IDs when reuse, links, aliases or summary previews justify them.
3. Add JSON and FTS5 when discovery calls are frequent enough to repay indexing and maintenance costs.
4. Index sections, return paths and snippets, then fetch only relevant content. Rebuild when sources change.
5. Collect real questions labeled by relevant section IDs. Measure Recall@k, MRR, answer accuracy, p50/p95 end-to-end latency, token counts and index update costs.
6. Add semantic or hybrid retrieval only after demonstrating that lexical methods miss significant paraphrased queries. Use knowledge graphs for explicit multi-hop requirements and MCP only when client interoperability is needed.

## Primary sources

- [Google Cloud Open Knowledge Format v0.2](https://github.com/GoogleCloudPlatform/knowledge-catalog/blob/main/okf/SPEC.md) — Markdown/YAML structure, optional index.md, provenance, format vs runtime. **This project's schema is inspired by OKF but not conformant**: OKF requires a type field and derives concept IDs from paths.
- [AGENTS.md](https://agents.md/) — agent instructions convention, not retrieval indexing.
- [SQLite FTS5 manual](https://www.sqlite.org/fts5.html) — MATCH, tokenizer, snippets, BM25 ranking.
- [ripgrep](https://github.com/BurntSushi/ripgrep) — text-search implementation and baseline.
- [FAISS](https://github.com/facebookresearch/faiss) — vector index and similarity retrieval.
- [MCP specification](https://modelcontextprotocol.io/specification/2025-06-18) — client/tool protocol.
- [OpenAI retrieval documentation](https://platform.openai.com/docs/guides/retrieval) — semantic retrieval concepts.

None of these references establishes a numerical victory of this implementation over vector/hybrid or native ripgrep. Local synthetic data is documented separately in [evaluation.md](evaluation.md).
