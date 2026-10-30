## What this changes

<!-- One or two sentences. Link the issue if there is one. -->

## Why

<!-- The problem this solves, or the failure it adds. -->

## How I checked it

- [ ] `ruff check .` and `ruff format --check .`
- [ ] `mypy`
- [ ] `python -m pytest`
- [ ] `aflab run --all --fail-on-unfixed`
- [ ] `python scripts/generate_catalog.py --check`

## If this adds or changes a failure

- [ ] `failure_observed` comes from an effect in the fake world, not from a guard firing
- [ ] The failure README has all seven sections and says what the fix does not cover
- [ ] The catalogue was regenerated

## If this changes behaviour

- [ ] There is a test that fails without the change
- [ ] `CHANGELOG.md` has an entry under Unreleased
