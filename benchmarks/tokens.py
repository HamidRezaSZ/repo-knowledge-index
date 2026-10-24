#!/usr/bin/env python3
"""Tokens an agent receives: kb search + get versus reading whole files.

Run from the repository root: python -m benchmarks.tokens
Counts use tiktoken's o200k_base encoding when tiktoken is installed (pip install tiktoken),
otherwise a bytes/4 estimate; the output says which. Neither is Claude's own tokenizer, so
compare the methods with each other rather than reading the numbers as exact costs.
"""
import argparse
import json
import re
import tempfile
from pathlib import Path

from scripts import kb

ROOT = Path(__file__).resolve().parents[1]
STOPWORDS = {"about", "after", "from", "have", "that", "then", "this", "what", "when", "with"}


def tokenizer():
    try:
        import tiktoken
        encoding = tiktoken.get_encoding("o200k_base")
        return "o200k_base (tiktoken)", lambda text: len(encoding.encode(text))
    except Exception:  # not installed, or the encoding could not be downloaded
        return "estimate: UTF-8 bytes / 4", lambda text: round(len(text.encode()) / 4)


def kb_answer(root: Path, index: dict, query: str) -> tuple[str, str | None]:
    """What the agent reads: the search output, then `get` on the first section hit."""
    groups = kb.group_hits(kb.search(root, query, 5))
    output = kb.render_search(groups)
    refs = [section["ref"] for group in groups for section in group["sections"]]
    if refs:
        output += "\n" + kb.render_get(kb.get(root, refs[0], index=index))
    return output, refs[0] if refs else None


def grep_files(root: Path, query: str) -> list[Path]:
    """Files a plain `grep -il` for the query's distinctive words (4+ letters) would list."""
    words = [w for w in re.findall(r"\w+", query.casefold()) if len(w) >= 4 and w not in STOPWORDS]
    return [path for path in sorted((root / "knowledge").rglob("*.md")) if path.name != "index.md"
            and any(word in path.read_text(encoding="utf-8").casefold() for word in words)]


def questions_table(count, questions: list[dict]) -> dict:
    index = kb.ensure_index(ROOT)
    rows = []
    for question in questions:
        text, top = kb_answer(ROOT, index, question["query"])
        right_file = ROOT / index["by_id"][question["expect"].split("#")[0]]["path"]
        rows.append({"query": question["query"], "expect": question["expect"], "top_hit": top,
                     "kb": count(text), "right_file": count(right_file.read_text(encoding="utf-8")),
                     "grep_files": sum(count(path.read_text(encoding="utf-8"))
                                       for path in grep_files(ROOT, question["query"]))})
    totals = {key: sum(row[key] for row in rows) for key in ("kb", "right_file", "grep_files")}
    totals["top_hit_correct"] = sum(row["top_hit"] == row["expect"] for row in rows)
    return {"questions": rows, "totals": totals}


def size_sweep(count, sizes=(1, 2, 3, 5, 10, 20)) -> list[dict]:
    """One synthetic document of N ~90-word sections; the answer is in the last one."""
    words = ("alpha beta gamma delta epsilon zeta theta iota kappa lambda sigma tau upsilon "
             "omega").split()
    results = []
    for size in sizes:
        with tempfile.TemporaryDirectory() as scratch:
            root = Path(scratch)
            (root / "knowledge").mkdir()
            body = "".join(f"# Topic {i}\n"
                           + " ".join(words[(i + j) % len(words)] for j in range(90))
                           + (" needle" if i == size - 1 else "") + "\n\n" for i in range(size))
            document = ("---\nid: big\ntitle: Big reference\nsummary: A long reference.\n---\n"
                        + body)
            (root / "knowledge" / "big.md").write_text(document, encoding="utf-8")
            text, _ = kb_answer(root, kb.ensure_index(root), "needle")
            results.append({"sections": size, "whole_file": count(document), "kb": count(text)})
    return results


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--questions", type=Path, default=ROOT / "benchmarks" / "questions.json")
    args = parser.parse_args()
    name, count = tokenizer()
    report = {"tokenizer": name,
              **questions_table(count, json.loads(args.questions.read_text(encoding="utf-8"))),
              "size_sweep": size_sweep(count)}
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
