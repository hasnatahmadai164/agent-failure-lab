# Writing a failure

This is for adding a new failure to the catalogue. A good one can be explained in a sentence, reproduced in a few lines of fake world, and fixed by something a reader could copy into their own agent.

## Before you start

Check [docs/ideas.md](ideas.md) and the open issues, so that you are not duplicating a failure that is already planned. If your failure is new, open an issue with the "New failure" template first. It is cheaper to agree on the idea than to review a finished pull request that goes another way.

A failure belongs here when:

- you have seen it, or read a credible account of it, in a real agent;
- it can be shown with a fake world, whose outcome can be counted (charges, emails, tokens, rows) and not argued about;
- the fix is something a reader can put in their own loop or tool.

It does not belong here when it depends on a particular model being unreliable in a particular way. A scripted model cannot show that.

## Scaffolding

From the repository root:

```bash
aflab new stale-cache-read --category tool-use
```

This creates `src/agent_failure_lab/failures/stale_cache_read/` with a `__init__.py`, `world.py`, `broken.py`, `fixed.py` and `README.md`, adds `tests/failures/test_stale_cache_read.py`, and adds the failure to `builtin_scenarios()` in `failures/__init__.py`. The slug is lowercase words joined by single hyphens, and the folder uses underscores because a hyphenated folder cannot be imported.

The scaffold is a small working failure about a job that runs more than once. It passes its own test until you change it, which makes it a safe place to start editing. Replace everything that talks about jobs and ledgers.

## The files

**`world.py`** holds everything both variants share: the fake systems, the tools, the scripted model, and the code that works out whether the failure happened. Keeping it in one file is what makes the comparison honest. The broken and fixed variants must differ only in the fix.

**`broken.py` and `fixed.py`** each define `run()` and return an `Outcome`. They choose guards and nothing else. The broken variant runs with no guards. The fixed variant adds the fix.

**`__init__.py`** exposes `SCENARIO`, a `ScenarioDefinition` with the slug, a title, a category, a one sentence `summary` with no trailing full stop, a short `fix` label, the names of the guards used, and the two runners.

**`README.md`** has seven sections in this order, and a test fails if one is missing: What happens, Why it happens, Impact, How to detect it in your own system, The fix, Trade-offs, Related guards.

## Measuring the failure

`failure_observed` must come from an effect in the fake world: a charge that was made, an email that was delivered, a row that was lost, tokens that were spent. It must not come from asking whether a guard fired. If you decide the failure by looking for a guard intervention, the fixed variant passes by definition and the result means nothing.

Put the numbers in `metrics`. Both variants report the same keys, so `aflab compare` can line them up. Put one plain sentence in `findings` for each way the failure showed up.

## The scripted model

`ScriptedLLM` plays back a list of `Reply` steps. A step is either a fixed reply or a function of the conversation so far. Use a function when the reply depends on what the tools returned, for example to retry after an error. Set `repeat_last=True` for a model that keeps doing the same thing.

The model should do what a careless real one plausibly would, and nothing cleverer. If the failure only happens because you scripted something nobody would see, it will not convince anyone.

Tools are scripted too: a call can fail before doing any work, do the work and then report failure (`Fail(effects_applied=True)`), or take a long time (`Delay`).

## The fix

Write the fix as a guard if it works inside the loop. Guards go in `src/agent_failure_lab/guards/`, subclass `Guard`, override the hooks they need, and call `run.intervene(...)` whenever they change something, so that the trace shows what they did. Export the guard from `guards/__init__.py`, add a section to [docs/guards.md](guards.md), and write unit tests for it in `tests/unit/`.

If the fix needs something on the tool's side, as idempotency does, ship that half too and say that both halves are needed. A guard that looks like a fix and changes nothing is worse than none.

Be honest in the Trade-offs section. What does the fix cost? What does it miss? A fix that can be bypassed by rephrasing should say so.

## Live mode (optional)

If the failure is judged by what happened in the fake world, it may also be able to run against a real model. `world.play` then takes an optional `model` and uses it in place of the scripted one, and `__init__.py` passes `broken_live` and `fixed_live`. Look at `failures/duplicate_side_effect/` for the pattern. Do this only when the outcome stays meaningful whatever words the model uses.

## Tests

The scaffold writes a test for the two variants. Keep it, and add tests that pin the numbers you care about. The shared catalogue tests then check, for every failure, that:

- the broken variant shows the failure and the fixed one does not;
- two runs give the same metrics and trace;
- the metadata is filled in and the category is a known one;
- the README has all seven sections and uses no dashes as punctuation.

## Finishing

```bash
python scripts/generate_catalog.py       # updates docs/catalog.md and the README table
ruff check . && ruff format --check . && mypy && python -m pytest
aflab run --all --fail-on-unfixed
```

Then add an entry to `CHANGELOG.md` under Unreleased and open a pull request. [CONTRIBUTING.md](../CONTRIBUTING.md) lists what a reviewer will look for.
