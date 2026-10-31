# Contributing

Thanks for taking an interest. Bug reports, new failures and fixes to existing ones are all welcome. Please read the [code of conduct](CODE_OF_CONDUCT.md) first.

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

The examples test needs LangGraph, so add the extra if you want it to run: `python -m pip install -e ".[dev,langgraph]"`. Without it, that test is skipped.

On Windows, if PowerShell refuses to run the activation script, run `Set-ExecutionPolicy -Scope CurrentUser RemoteSigned` once. Save files with LF line endings (the repository's `.editorconfig` and `.gitattributes` ask for it) and without a byte order mark.

## Checks

Run all of these before opening a pull request. CI runs the same commands.

```bash
ruff check .
ruff format --check .
mypy
python -m pytest
python scripts/generate_catalog.py --check
aflab run --all --fail-on-unfixed
```

The default test run never touches the network. Tests that need a real external service carry the `live` marker and run only when `RUN_LIVE=1`.

## Adding a failure

Open an issue with the "New failure" template first, so that the idea can be discussed before you write it. Then:

```bash
aflab new my-new-failure --category tool-use
```

and follow [docs/writing-a-failure.md](docs/writing-a-failure.md). When the failure works, regenerate the catalogue:

```bash
python scripts/generate_catalog.py
```

This rewrites `docs/catalog.md` and the table in the README. Do not edit either by hand. CI fails if they are out of date.

A reviewer will look for these things:

- The failure is measured by an effect in the fake world, not by whether a guard fired.
- The broken and fixed variants differ only in the fix.
- The README says what the fix costs and what it does not cover.
- No claim goes further than the scripted model can show.

## Writing documentation

Plain and specific. No emojis, no dashes used as punctuation (use commas, colons or brackets), and no marketing words. Every number in a document must come from a run you made. Do not state that something was verified against a live service unless it was. A test checks the markdown files for some of these rules.

## Commit messages

Use Conventional Commits: `feat`, `fix`, `refactor`, `test`, `docs`, `chore`, `ci`, `build`, `perf`. Write the subject in the imperative mood, keep it under 72 characters, and omit the trailing period.

## Pull requests

- One logical change per pull request.
- Tests are committed together with the code they cover.
- Behaviour changes add a regression test.
- Documentation that describes behaviour is updated in the same pull request.
- Add a line to `CHANGELOG.md` under Unreleased.

## Releasing

Releases are made by the maintainer.

1. Move the Unreleased entries in `CHANGELOG.md` under a new heading with the version and date.
2. Set `__version__` in `src/agent_failure_lab/__init__.py` to the same version.
3. Run the checks above, then `python -m build` and `twine check dist/*`.
4. Commit, and push to `main` once CI is green.
5. Tag the commit `vX.Y.Z` and push the tag.

The release workflow builds the package, refuses to continue if the tag does not match `__version__`, and publishes to PyPI through trusted publishing (no token is stored). Publishing waits for the `pypi` environment, which can require approval.
