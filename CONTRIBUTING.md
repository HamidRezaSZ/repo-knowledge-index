# Contributing

Submit small, testable changes. Use Python 3.10+, install `requirements.txt`, and run `python -m unittest discover -s tests -v` and `python scripts/kb.py build` before opening a pull request. If changing retrieval behavior, add a regression test and describe its impact on precision/recall, latency, and context size. Do not commit `.knowledge/` or claim numerical improvements without reproducible evidence.
