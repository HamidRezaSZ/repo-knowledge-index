# Reproducible evaluation and limitations

## What has and has not been measured

Three checked-in benchmarks run on this repository:

- **Retrieval quality** (`benchmarks/retrieval.py`): how often `search`, `search --semantic` and QMD's own modes put the labeled section first or in the top five, on 78 questions over a 25-document corpus written for the benchmark, with each call's latency and output size.
- **Token usage** (`benchmarks/tokens.py`): tokens an agent receives from `search` plus `get` on the top hit, compared with reading whole files, on 8 labeled questions about the sample corpus and on a synthetic document of growing size. Counts use tiktoken's `o200k_base` encoding when tiktoken is installed, otherwise a bytes/4 estimate; the output names the one used. Neither is Claude's tokenizer, so compare the methods with each other rather than reading the numbers as exact costs.
- **Search latency** (`benchmarks/compare.py`): a Python linear file scan versus SQLite FTS5 ranked search on synthetic documents, in-process with warm caches. It excludes interpreter startup, network, model inference and tokenization.

Not measured: native ripgrep, vector search over large corpora (ANN), knowledge graphs, MCP, relevance on real repositories' questions, and end-to-end answer accuracy.

## Reproduce

```bash
python -m unittest discover -s tests -v
python -m pip install tiktoken  # optional: exact o200k_base counts instead of an estimate
python -m benchmarks.retrieval
# with QMD installed: index the corpus for QMD's own modes, then add them and --semantic
qmd collection add benchmarks/corpus/knowledge --name kb-corpus && qmd embed
python -m benchmarks.retrieval --qmd "$(command -v qmd)" --modes search
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

## Retrieval quality

`benchmarks/corpus/` is an invented knowledge base for a web service: 25 documents and 89 sections on sign-in, deployment, caching, payments and similar topics. Each of its 78 questions is labeled with the one section that answers it:

| Kind | Questions | Example |
| --- | ---: | --- |
| Exact | 20 | "rollback a bad release" |
| Reworded | 28 | "restore the last good build after shipping something broken" |
| Abbreviated | 13 | "perms check", "env vars naming" |
| Identifier | 17 | `ERR_RATE_LIMITED`, `X-Request-Id` |

A reworded question shares no content word, after stemming and ignoring common function words, with its section or with its document's title, summary, tags and aliases. A test enforces this, and also that `search` keeps ranking the right section first for every exact and identifier question.

Each method returns at most five results. QMD's own modes index whole documents and report a line, which is mapped to the section that holds it. Results were collected on 2026-10-27 with Python 3.13.5, SQLite 3.46.1, Node.js 25.2.1 and QMD 2.8.3 with its default models, on an Intel Core i7-10610U (4 cores) without GPU acceleration while other programs were running, so latencies are rough. Latency is the wall time of one CLI call, start-up included; tokens are `o200k_base` counts of each tool's default text output.

Questions whose labeled section came first, with the number found in the top five in brackets:

| Method | Exact (20) | Reworded (28) | Abbreviated (13) | Identifier (17) | All (78) | MRR@5 | Median / p95 latency | Output tokens |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| `search` | 20 (20) | 0 (2) | 12 (13) | 17 (17) | 49 (52) | 0.64 | 0.10 / 0.14 s | 160 |
| `search --semantic` | 20 (20) | 19 (27) | 13 (13) | 17 (17) | 69 (77) | 0.93 | 4.4 / 4.7 s | 203 |
| QMD `search` | 12 (12) | 0 (0) | 7 (7) | 16 (16) | 35 (35) | 0.45 | 0.27 / 0.30 s | 47 |

What the numbers show:

- Plain search ranks the right section first for every exact and identifier question and 12 of 13 abbreviated ones, but for none of the reworded ones. It never comes back empty, so for a reworded question it lists wrong sections that share a stray word.
- `search --semantic` ranks the right section first for 19 of the 28 reworded questions and in the top five for 27, with no loss on the other kinds. It is about 45 times slower; nearly all of that is QMD starting and loading its embedding model on every call. The first `--semantic` search on this corpus took 26 s, mostly to embed its 89 sections, plus QMD's model download the first time QMD runs.
- Merging the vector ranking with plain search's any-word ranking instead put the right section first for only 1 of the 28 reworded questions (24 in the top five): they share stray words with wrong sections, and those hits tie with or outrank the right one. Requiring every word removes them. On this corpus the merged ranking then equals the vector ranking alone, so the value of the word side for exact names in larger corpora is expected, not shown. To reproduce the any-word merge, drop `match_all=True` from the `search` call in `semantic_search`.
- QMD's keyword search requires every word, so 34 of the 78 questions got no results. Because it ranks whole documents, it put the right document first for 44 questions but the right section for only 35. Its recommended `query` mode, which runs local language models for query expansion and reranking, took 72 s for one new question on this CPU (4 s when repeated, from its cache), so it was not run on all 78.
- Porting QMD's keyword rules into plain search did not help, in a throwaway experiment that is not checked in: requiring every word found nothing for most natural-language questions, and prefix matching (`perms` finding `permissions`) changed the count by at most one question either way. Plain search keeps its any-word, whole-word ranking.

What the numbers do not show: the documents, the questions and the code have the same author, and the reworded questions were built to share no words with their answers, so their row shows how large the gap is when it happens, not how often agents ask that way. 89 sections is small; vector search over thousands of similar sections, where exact names blur more, is untested.

## Tests

`tests/test_kb.py` covers frontmatter parsing and validation, section splitting, ranking, CLI output, the generated catalog, index freshness, the retrieval benchmark's labels, and `--semantic` against a stand-in for QMD (CI does not install QMD). CI runs it on Python 3.10–3.14, then builds the index, checks that `knowledge/index.md` is up to date, and runs a search and a get. Check the GitHub Actions page for the current run status.

## Next meaningful research experiment

The retrieval benchmark covers part of this on invented data. Next, collect 50–200 real questions from agent sessions on real repositories, including multi-hop questions and outdated knowledge, labeled by their relevant sections. Repeat the comparison on a corpus of thousands of sections, where exact names are likelier to blur in vector search, and add ripgrep and manual Markdown navigation as baselines under matched output budgets. Record answer correctness and NDCG@10 as well, measure warm latency through QMD's MCP server next to cold CLI calls, and publish raw data and uncertainties. Until then, avoid claiming that the chosen architecture has universally highest retrieval accuracy or lowest token cost.
