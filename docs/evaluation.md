# Reproducible evaluation and limitations

## What has and has not been measured

The checked-in benchmark compares **a Python linear file scan** with **SQLite FTS5 ranked search** on synthetic Markdown documents. It runs in-process with warmed caches and includes the Python search logic, but not interpreter startup, network, model inference or LLM tokenization. It does **not** benchmark native ripgrep, vectors, ANN, hybrid retrieval, knowledge graphs, MCP, token counts, real-question relevance, or end-to-end answer accuracy.

## Reproduce

```bash
python -m pip install -r requirements.txt
python -m unittest discover -s tests -v
python -m benchmarks.compare --docs 300 --repeats 30
python -m benchmarks.compare --docs 3000 --repeats 30
python -m benchmarks.compare --docs 300 --repeats 30 --query auth
```

Synthetic documents use six repeated software topics. Default query is absent from all files, forcing the scan to inspect the full corpus. Results below were collected locally on 2026-10-24 using Python 3.13.5 and SQLite FTS5 in a container; timings are medians from 30 warm iterations without CPU/cache controls.

## Observed local results

| Documents | Query | Build (ms) | Python scan median (ms) | FTS5 median (ms) |
| ---: | --- | ---: | ---: | ---: |
| 300 | unlikelymissingkeyword | 99.8191 | 2.2043 | 0.2410 |
| 3,000 | unlikelymissingkeyword | 904.6460 | 22.8087 | 0.1940 |
| 300 | auth | 96.6490 | 0.0896 | 0.2278 |

The early-positive linear scan is faster than FTS5 here; on absent terms, FTS5 is faster. **These methods are not functionality-identical**: the scan returns the first matching files, while FTS5 returns BM25-ranked sections. Neither a relevance benchmark nor hardware-neutral performance guarantee should be inferred. The synthetic repeating corpus is deliberately limited.

Seven Python unittest checks passed locally, covering duplicate IDs, alias lookup, related-ID validation, section-level search, fenced heading parsing, missing indexes, and rebuild after deletion. CI is configured to rerun tests and a build/search smoke test on GitHub Actions; GitHub run status must be independently verified.

## Next meaningful research experiment

Build a labeled set of 50–200 real questions and their relevant sections, including exact IDs, jargon, paraphrases, multi-hop questions and outdated knowledge. Evaluate ripgrep, manual markdown navigation, FTS5 BM25, embeddings-only and hybrid under matched output budgets. Record Recall@1/5, MRR@10, NDCG@10, measured context tokens (declared tokenizer), answer correctness, p50/p95 whole retrieval time including process startup and embedding overhead, index build time, and change/update time. Run warm and cold trials separately, publish raw data and uncertainties. Until then, avoid claiming that the chosen architecture has universally highest retrieval accuracy or lowest token cost.
