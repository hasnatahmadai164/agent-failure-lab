# Contributing

## Development setup

Python 3.10 or newer is required.

Windows PowerShell:

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -e ".[dev]"
```

macOS and Linux:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -e ".[dev]"
```

## Checks

Run all four before opening a pull request. CI runs the same commands.

```bash
ruff check .
ruff format --check .
mypy
python -m pytest
```

The default test run never touches the network. Tests that need a real external service carry the `live` marker and run only when `RUN_LIVE=1`.

## Commit messages

Use Conventional Commits: `feat`, `fix`, `refactor`, `test`, `docs`, `chore`, `ci`, `build`, `perf`. Write the subject in the imperative mood, keep it under 72 characters, and omit the trailing period.

## Pull requests

- One logical change per pull request.
- Tests are committed together with the code they cover.
- Behaviour changes add a regression test.
- Documentation changes that describe behaviour are updated in the same pull request.
