# Reproducible evaluation and limitations

## What has and has not been measured

Two checked-in benchmarks run on this repository:

- **Token usage** (`benchmarks/tokens.py`): tokens an agent receives from `search` plus `get` on the top hit, compared with reading whole files, on 8 labeled questions about the sample corpus and on a synthetic document of growing size. Counts use tiktoken's `o200k_base` encoding when tiktoken is installed, otherwise a bytes/4 estimate; the output names the one used. Neither is Claude's tokenizer, so compare the methods with each other rather than reading the numbers as exact costs.
- **Search latency** (`benchmarks/compare.py`): a Python linear file scan versus SQLite FTS5 ranked search on synthetic documents, in-process with warm caches. It excludes interpreter startup, network, model inference and tokenization.

Not measured: native ripgrep, vectors, ANN, hybrid retrieval, knowledge graphs, MCP, relevance on real questions at scale, and end-to-end answer accuracy.

## Reproduce

```bash
python -m unittest discover -s tests -v
python -m pip install tiktoken  # optional: exact o200k_base counts instead of an estimate
python -m benchmarks.tokens
python -m benchmarks.compare --docs 300 --repeats 30
python -m benchmarks.compare --docs 3000 --repeats 30
python -m benchmarks.compare --docs 300 --repeats 30 --query auth
```

Results below were collected locally on Linux on 2026-10-24 with Python 3.13.5 and SQLite 3.46.1, without CPU or cache controls.

## Token usage

Per question, "kb" is the text an agent reads from `search "<query>" --limit 5` plus `get` on the first section hit. "Right file" is reading the one file that holds the answer, a best case that assumes the agent already knows where to look. "Grep files" is reading every knowledge file that contains one of the query's words of four or more letters, excluding the generated catalog.

| Question | Expected section | Top hit right | kb | Right file | Grep files |
| --- | --- | :---: | ---: | ---: | ---: |
| how do refresh tokens rotate | `authentication#refresh-tokens` | yes | 141 | 125 | 125 |
| short-lived access token after login | `authentication#login` | yes | 195 | 125 | 221 |
| revoke a session | `authentication#revoking-sessions` | yes | 198 | 125 | 125 |
| check ownership before accessing an object | `authorization#object-level-permissions` | yes | 205 | 96 | 96 |
| missing authorization policy | `authorization#default-deny` | yes | 116 | 96 | 317 |
| read from cache then fall back to the database | `caching#cache-aside` | yes | 219 | 96 | 221 |
| invalidate cache keys after writes | `caching#invalidation` | yes | 104 | 96 | 96 |
| stale values after a database write | `caching#invalidation` | yes | 207 | 96 | 96 |
| **Total** | | **8/8** | **1,385** | **855** | **1,297** |

The same 8 questions through the original CLI (commit `ecf0368`, indented JSON) cost 4,221 tokens with the same 8/8 top hits. That figure was measured once by counting that version's output; `benchmarks/tokens.py` measures only the current code.

The sample documents are tiny (two or three sections of one or two sentences each), so reading the right file whole is still cheaper than searching: most of the kb text is the search listing itself. The synthetic size sweep shows where sections pay off. It uses one document of N sections of about 90 words each, with the answer in the last section:

| Sections | Whole file | kb |
| ---: | ---: | ---: |
| 1 | 139 | 176 |
| 2 | 260 | 176 |
| 3 | 382 | 178 |
| 5 | 628 | 179 |
| 10 | 1,239 | 176 |
| 20 | 2,455 | 178 |

The kb cost stays flat while the file grows. Break-even is about two sections; at 10 sections the agent reads about 7 times fewer tokens, at 20 about 14 times fewer. Eight questions over three documents is a smoke test, not evidence of retrieval quality in general.

## Search latency

| Documents | Query | Build (ms) | Python scan median (ms) | FTS5 median (ms) |
| ---: | --- | ---: | ---: | ---: |
| 300 | unlikelymissingkeyword | 51.0 | 3.01 | 0.34 |
| 3,000 | unlikelymissingkeyword | 491.0 | 30.79 | 0.34 |
| 300 | auth | 50.5 | 0.13 | 0.34 |

Synthetic documents repeat six software topics. The default query appears in no file, so the scan reads the whole corpus; `auth` appears early, so the scan stops after five matches and beats FTS5. **The methods are not functionally identical**: the scan finds substrings and returns the first matching files, while FTS5 matches whole words (with English stemming, so `auth` does not match `authentication`) and returns BM25-ranked sections. Medians come from 30 warm iterations; no hardware-neutral guarantee should be inferred.

## Tests

`tests/test_kb.py` covers frontmatter parsing and validation, section splitting, ranking, CLI output, the generated catalog and index freshness. CI runs it on Python 3.10–3.14, then builds the index, checks that `knowledge/index.md` is up to date, and runs a search and a get. Check the GitHub Actions page for the current run status.

## Next meaningful research experiment

Extend `benchmarks/questions.json` to 50–200 real questions and their relevant sections, including exact IDs, jargon, paraphrases, multi-hop questions and outdated knowledge. Evaluate ripgrep, manual Markdown navigation, FTS5 BM25, embeddings-only and hybrid retrieval under matched output budgets. Record Recall@1/5, MRR@10, NDCG@10, measured context tokens (declared tokenizer), answer correctness, p50/p95 whole retrieval time including process startup and embedding overhead, index build time, and update time. Run warm and cold trials separately and publish raw data and uncertainties. Until then, avoid claiming that the chosen architecture has universally highest retrieval accuracy or lowest token cost.
