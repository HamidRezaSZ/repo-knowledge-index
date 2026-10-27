# Contributing

Submit small, testable changes. Use Python 3.10+ (no third-party packages are needed) and run `python -m unittest discover -s tests -v` and `python scripts/kb.py build` before opening a pull request, and commit the regenerated `knowledge/index.md`. If changing retrieval behavior, add a regression test and describe its impact on precision/recall (`python -m benchmarks.retrieval`), latency, and context size. Do not commit `.knowledge/` or claim numerical improvements without reproducible evidence.
