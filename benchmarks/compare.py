#!/usr/bin/env python3
"""Reproducible *lexical* comparison: linear Python scan vs indexed FTS5.

Results include process start-up? No. They measure warm in-process retrieval only.
No embedding, vector, LLM tokenization or generation is benchmarked here.
"""
import argparse
import json
import statistics
import tempfile
import time
from pathlib import Path

from scripts import kb

TOPICS = ("authentication", "authorization", "caching", "transactions", "observability", "deployment")


def corpus(root: Path, size: int) -> list[Path]:
    docs = []
    directory = root / "knowledge"
    directory.mkdir(parents=True)
    for i in range(size):
        topic = TOPICS[i % len(TOPICS)]
        path = directory / f"doc-{i:05}.md"
        path.write_text(f"---\nid: doc-{i:05}\ntitle: {topic} reference {i}\n"
                        f"summary: Guidance about {topic}.\naliases: []\ntags: [{topic}]\n"
                        f"related: []\n---\n# Procedure\n"
                        + (f"This {topic} guide explains setup validation monitoring and recovery. " * 8)
                        + "\n", encoding="utf-8")
        docs.append(path)
    return docs


def linear(paths, term, limit):
    matches = []
    for path in paths:
        if term in path.read_text(encoding="utf-8").casefold():
            matches.append(path)
            if len(matches) >= limit:
                break
    return matches


def median_ms(fn, repeats):
    samples = []
    for _ in range(repeats):
        start = time.perf_counter_ns()
        fn()
        samples.append((time.perf_counter_ns() - start) / 1e6)
    return round(statistics.median(samples), 4)


def run(size, repeats, term):
    with tempfile.TemporaryDirectory() as scratch:
        root = Path(scratch)
        paths = corpus(root, size)
        start = time.perf_counter_ns()
        indexed = kb.build(root)
        build_ms = (time.perf_counter_ns() - start) / 1e6
        # A full linear scan is required to discover ranked candidates; don't
        # compare against early-exit scan for an absent term.
        linear(paths, term, 5)
        kb.search(root, term, 5)
        linear_median = median_ms(lambda: linear(paths, term, 5), repeats)
        indexed_median = median_ms(lambda: kb.search(root, term, 5), repeats)
        return {"docs": size, "query": term, "repeats": repeats,
                "indexed_sections": indexed["sections"],
                "build_ms": round(build_ms, 4),
                "linear_scan_median_ms": linear_median,
                "fts5_median_ms": indexed_median,
                "note": "Synthetic repeating corpus; includes Python disk/cache overhead; not a relevance benchmark."}


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--docs", type=int, default=300)
    p.add_argument("--repeats", type=int, default=20)
    p.add_argument("--query", default="unlikelymissingkeyword")
    args = p.parse_args()
    if not 1 <= args.docs <= 20000 or not 1 <= args.repeats <= 10000:
        p.error("Invalid sample size/repeat count")
    print(json.dumps(run(args.docs, args.repeats, args.query), indent=2))


if __name__ == "__main__":
    main()
