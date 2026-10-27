#!/usr/bin/env python3
"""Retrieval quality on labeled questions: kb search, and optionally QMD.

Run from the repository root:
    python -m benchmarks.retrieval
    python -m benchmarks.retrieval --qmd qmd --collection kb-corpus

benchmarks/corpus/ holds 25 knowledge files and 78 questions written for this benchmark, each
labeled with the one section that answers it and with a kind: exact (shares the section's words),
paraphrase (shares no content word with the section or its document's title, summary, tags and
aliases), partial (abbreviations such as "perms") and identifier (names such as ERR_RATE_LIMITED).
`--qmd` adds `kb search --semantic` and QMD's own modes over whole documents; for the latter,
index the corpus first: `qmd collection add benchmarks/corpus/knowledge --name kb-corpus`, then
`qmd embed`. Latency is the wall time of one CLI call per question, start-up included; tokens
are those of each tool's default text output.
"""
import argparse
import json
import os
import re
import sqlite3
import statistics
import subprocess
import sys
import time
from contextlib import closing
from pathlib import Path

from benchmarks.tokens import tokenizer
from scripts import kb

ROOT = Path(__file__).resolve().parents[1]
CORPUS = ROOT / "benchmarks" / "corpus"
KINDS = ("exact", "paraphrase", "partial", "identifier")
LIMIT = 5
STOPWORDS = set("""a about after again all an and any are as at be been before being both but by
can could did do does doesn don each every for from get gets got had has have he her here his how i
if in into is it its me might must my no not of off on once one only or our out over s she should so
some such t than that the their them then there these they this those to too two under up us was we
were what when where which who whom why will with would you your""".split())


def questions() -> list[dict]:
    return json.loads((CORPUS / "questions.json").read_text(encoding="utf-8"))


def stems(text: str) -> set[str]:
    """The Porter-stemmed terms FTS5 would index for this text."""
    with closing(sqlite3.connect(":memory:")) as conn:
        conn.execute("CREATE VIRTUAL TABLE t USING fts5(x, tokenize='porter unicode61')")
        conn.execute("CREATE VIRTUAL TABLE v USING fts5vocab(t, 'row')")
        conn.execute("INSERT INTO t VALUES (?)", (text,))
        return {term for (term,) in conn.execute("SELECT term FROM v")}


def shared_words(question: dict, index: dict, root: Path = CORPUS) -> set[str]:
    """Content stems a question shares with its section and its document's indexed fields."""
    doc = question["expect"].split("#")[0]
    entry = index["by_id"][doc]
    section = kb.get(root, question["expect"], index=index)
    aliases = [alias for alias, key in index["by_alias"].items() if key == doc]
    target = " ".join([section["heading"], section["content"], entry["title"], entry["summary"],
                       *entry["tags"], *aliases])
    return (stems(question["query"]) & stems(target)) - stems(" ".join(STOPWORDS))


def section_at(path: Path, line: int) -> str:
    """The slug of the section holding a 1-based line of a file, split the way kb splits it."""
    raw = path.read_text(encoding="utf-8-sig")
    head = kb.FRONTMATTER.match(raw)
    skip = raw[:head.end()].count("\n") if head else 0
    upto = raw.splitlines(keepends=True)[skip:max(line, skip + 1)]
    return kb.sections("".join(upto) + "\nx\n")[-1].slug  # "x" keeps a bare heading a section


def timed(command: list[str]) -> tuple[str, float]:
    start = time.perf_counter()
    done = subprocess.run(command, capture_output=True, text=True, check=True)
    return done.stdout, (time.perf_counter() - start) * 1000


def kb_method(*flags: str):
    def run(query: str) -> tuple[list[tuple], str, float]:
        output, ms = timed([sys.executable, str(ROOT / "scripts" / "kb.py"), "--root",
                            str(CORPUS), "search", query, "--limit", str(LIMIT), "--json", *flags])
        groups = json.loads(output)
        hits = [(group["id"], None, group["score"]) for group in groups if "summary" in group]
        hits += [(group["id"], section["ref"].partition("#")[2], section["score"])
                 for group in groups for section in group["sections"]]
        hits.sort(key=lambda hit: -hit[2])  # output is grouped by document; rank by score
        return [hit[:2] for hit in hits], kb.render_search(groups), ms
    return run


QMD_MODES = {"search": ["search"], "vsearch": ["vsearch"], "query": ["query"],
             "query-no-rerank": ["query", "--no-rerank"]}
QMD_HIT = re.compile(r"^qmd://[^/\s]+/(\S+?)(?:\?\S*)?:(\d+) #", re.MULTILINE)  # a hit's header


def qmd_method(binary: str, mode: str, collection: str, docs: dict):
    def run(query: str) -> tuple[list[tuple], str, float]:
        command = [binary, *QMD_MODES[mode][:1], query, *QMD_MODES[mode][1:], "-n", str(LIMIT),
                   "-c", collection]
        output, ms = timed(command)
        hits = []
        for rel, line in QMD_HIT.findall(output):  # qmd://<collection>/<path>:<line> #<docid>
            doc = docs.get(f"knowledge/{rel}")
            hits.append((doc, section_at(CORPUS / "knowledge" / rel, int(line)) if doc else None))
        return hits, output, ms
    return run


def score(method, items: list[dict], count) -> dict:
    rows = []
    for item in items:
        hits, output, ms = method(item["query"])
        doc, _, slug = item["expect"].partition("#")
        rank = next((n for n, hit in enumerate(hits, 1) if hit == (doc, slug)), 0)
        rows.append({"kind": item["kind"], "rank": rank, "ms": ms, "tokens": count(output),
                     "doc_top": bool(hits) and hits[0][0] == doc, "empty": not hits})

    def summary(selected: list[dict]) -> dict:
        return {"questions": len(selected),
                "hit_at_1": sum(row["rank"] == 1 for row in selected),
                "hit_at_5": sum(row["rank"] > 0 for row in selected),
                "mrr_at_5": round(sum(1 / row["rank"] for row in selected if row["rank"])
                                  / len(selected), 3),
                "document_hit_at_1": sum(row["doc_top"] for row in selected),
                "no_results": sum(row["empty"] for row in selected)}

    report = {kind: summary([row for row in rows if row["kind"] == kind]) for kind in KINDS}
    times = [row["ms"] for row in rows]
    report["all"] = {**summary(rows), "median_ms": round(statistics.median(times), 1),
                     "p95_ms": round(statistics.quantiles(times, n=20)[18], 1),
                     "mean_output_tokens": round(statistics.mean(row["tokens"] for row in rows))}
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--qmd", help="the qmd command; adds kb search --semantic and QMD's "
                                      "own search modes to the report")
    parser.add_argument("--collection", default="kb-corpus",
                        help="the QMD collection that indexes benchmarks/corpus/knowledge")
    parser.add_argument("--modes", default=",".join(QMD_MODES),
                        help=f"comma-separated QMD modes: {', '.join(QMD_MODES)}")
    args = parser.parse_args()
    name, count = tokenizer()
    index = kb.ensure_index(CORPUS)
    docs = {entry["path"]: key for key, entry in index["by_id"].items()}
    methods = {"kb search": kb_method()}
    if args.qmd:
        os.environ["KB_QMD"] = args.qmd
        methods["kb search --semantic"] = kb_method("--semantic")
        for mode in filter(None, args.modes.split(",")):
            methods[f"qmd {mode}"] = qmd_method(args.qmd, mode, args.collection, docs)
    items = questions()
    report = {"tokenizer": name, "limit": LIMIT,
              "methods": {label: score(method, items, count) for label, method in methods.items()}}
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
