# agent-failure-lab

A Python library and command-line tool that catalogues the ways LLM agents fail in production, reproduces each failure deterministically without an API key, and ships the tested fix as a reusable guard.

## Install

The package is not on PyPI yet. Install from source:

```bash
git clone https://github.com/hasnatahmadai164/agent-failure-lab.git
cd agent-failure-lab
python -m pip install -e .
```

Then:

```bash
aflab --version
aflab list
```

`aflab list` currently reports an empty catalogue. Failures are being added to the repository one at a time.

## What this is, and what it is not

The scenarios use a scripted model that misbehaves on purpose. They demonstrate failure mechanisms and their fixes, not how often real models fail.

Non-goals: a benchmark of model reliability, a framework, a hosted service, a guarantee that any guard makes an agent safe.

## Development

See [CONTRIBUTING.md](CONTRIBUTING.md).

## License

MIT. See [LICENSE](LICENSE).

## Author

Hasnat Ahmad ([GitHub](https://github.com/hasnatahmadai164), [LinkedIn](https://www.linkedin.com/in/hasnat-ahmad-ai/)).
