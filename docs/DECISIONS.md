# Design decisions

Each entry has the context, the decision, the alternatives I rejected, and the consequences. New entries go at the end.

## D-001: The project brief wins over my generic rules

**Context.** My working rules were written for web services (pydantic-settings, structlog, FastAPI, async). This project is a small CLI library with its own stack.

**Decision.** Follow the project brief: Python 3.10 or newer, dataclasses and Protocols, standard library plus typer and rich. No settings class, no structlog, no async. The only environment variable is `OPENAI_API_KEY`, read in one place when live mode is added.

**Alternatives rejected.** Adding pydantic-settings and structlog to match the generic rules. Nothing in the core needs them.

**Consequences.** Smaller install. If logging is needed later, it gets its own entry.

## D-002: hatchling, with the version kept in `__init__.py`

**Context.** I need a `src/` layout, extras, a console script, and one place for the version.

**Decision.** Use hatchling. The version lives in `__version__` in `src/agent_failure_lab/__init__.py` and hatchling reads it from there. It starts at `0.1.0.dev0`.

**Alternatives rejected.** setuptools-scm ties the version to git tags and history during builds. Poetry is heavy for two dependencies. A version in two files drifts.

**Consequences.** A release bump is a one-line edit. The license is an SPDX string, so building needs hatchling 1.27 or newer.

## D-003: Two runtime dependencies, everything else is an extra

**Context.** The core should install small and rarely clash with other packages.

**Decision.** Runtime dependencies are typer and rich only. OpenAI is the `live` extra, LangGraph is the `langgraph` extra, and the development tools are the `dev` extra. Each range has a lower bound and the next major version as the upper bound. The `dev` extra needs twine 7 or newer: twine 6.2 rejected the metadata hatchling writes, and I found that by running the build check.

**Alternatives rejected.** Exact pins clash with other packages. No upper bounds means a future major release could break the CLI. argparse avoids a dependency but I would write the help text and tables by hand.

**Consequences.** I have not tested the lower bounds. They need checking before the first release.

## D-004: The CLI is built by a function that takes the registry

**Context.** Tests have to run the CLI with their own scenarios, and I want no global state and nothing happening at import time.

**Decision.** `build_app(registry)` returns the Typer app, and its commands use the registry passed in. `main()` builds the real registry and runs the app. There is no module-level app.

**Alternatives rejected.** A module-level app with a global registry filled on import. Tests would then depend on import order.

**Consequences.** CLI tests build a throwaway registry. The entry point is `agent_failure_lab.cli:main`.

## D-005: CI runs in three separate jobs

**Context.** The brief wants ruff, mypy, pytest on Python 3.10 to 3.13, `aflab run --all --fail-on-unfixed`, and a build check. I develop on Windows.

**Decision.** Three jobs: lint (ruff check, ruff format check, mypy), test (3.10 to 3.13 on Ubuntu, plus 3.12 on Windows), and build (`python -m build`, `twine check`). The `aflab run --all` step is added in Stage 7, when the command exists.

**Alternatives rejected.** One job that does everything is slower and the failures are harder to read. A full OS matrix costs more minutes for little extra signal.

**Consequences.** A lint failure does not hide a test failure. `ci.yml` gets edited once more in Stage 7.

## D-006: Guards are objects with five hooks that return decisions

**Context.** Fixes plug into the agent loop at five points and have to work in someone else's loop too. The broken variant runs with no guards.

**Decision.** `Guard` is a plain base class with five hooks that do nothing by default: `before_model`, `after_model`, `before_tool`, `after_tool`, `on_step_end`. A hook returns None for no change, a replacement value, `Block(result)` to skip a tool call, or `Stop(reason)` to end the run. Guards run in the order given, and each sees the previous one's change. Every guard action goes through `run.intervene(...)`, which writes a trace event.

**Alternatives rejected.** A Protocol with all five methods required would force four empty methods on every guard. Exceptions for control flow hide the outcomes in the code. A mutable context that guards edit makes it unclear who changed what.

**Consequences.** Guards are easy to unit test. The cost is one level of inheritance, and a guard that forgets `intervene` is silent in the trace, so each guard's tests check for it.

## D-007: The history is read-only

**Context.** Silent truncation needs the model to see less than what happened, and the fix has to show what was dropped.

**Decision.** `before_model` returns the messages for that one call. A guard never edits the recorded history.

**Alternatives rejected.** Letting guards rewrite the history would lose the difference between what happened and what the model saw.

**Consequences.** The full history is always there for tests and post-mortems. A guard that needs to remember what it hid keeps its own state.

## D-008: Scripted model, estimated tokens, scheduled tool failures

**Context.** Scenarios have to misbehave the same way on every run, with no network and no randomness. Some failures depend on cost, and some on work that happens before an error is reported.

**Decision.** `ScriptedLLM` plays back `Reply` steps, which are either fixed or a function of the conversation. Tool call ids are `call_1`, `call_2` and so on, and `repeat_last` covers endless loops. Tokens are estimated as four characters per token plus four per message. Tools take a per-call schedule: `Fail` errors before any work, `Fail(effects_applied=True)` does the work and then reports failure, and `Delay(seconds)` slows the call, with an optional timeout that cuts it off. Tool errors go back to the model as error results. Any other exception ends the run.

**Alternatives rejected.** A real tokenizer adds a dependency and its numbers change between versions. Random failure injection is not reproducible.

**Consequences.** Token and cost figures are consistent but not real costs, and the README says so. Model calls take no simulated time. Tools run one after another, so the parallel-race failure needs a small addition in Stage 5.

## D-009: An injectable clock, and the trace uses it

**Context.** Timeout and TTL scenarios cannot wait in real time, but a deadline guard also has to work in a live loop.

**Decision.** `Clock` is a Protocol with two implementations: `ManualClock`, which moves only when told to, and `SystemClock`, which uses monotonic time and real sleep. `Trace` takes a clock and stamps every event with it.

**Alternatives rejected.** Patching `time` in tests hides the dependency. Passing timestamps by hand is easy to get wrong.

**Consequences.** Scenarios run instantly and still show elapsed time. `SystemClock` has one small test and is otherwise used only in live runs.

## D-010: Scenarios, the runner, and two changes from the brief

**Context.** The brief asks for a Scenario protocol and a registry. It also says each failure's `__init__.py` registers it, and that failure folders are named after the slug. In Stage 1, a placeholder `ScenarioInfo` let `aflab list` work before the real model existed.

**Decision.** `Scenario` is a Protocol and `ScenarioDefinition` is the normal implementation, with one function per variant. `Outcome` holds the variant, `failure_observed`, the trace, metrics and findings. The runner returns a `PairResult`, and its `contract_holds` means the broken variant fails and the fixed one does not. Slugs must be lowercase words joined by single hyphens. Two changes from the brief. Folders and test files use the slug with underscores, because a hyphenated folder cannot be imported. Failure packages do not register themselves on import. They expose a scenario, and `builtin_scenarios()` lists them. I also added `scenario.py` and `sim/hooks.py`, which the layout in the brief did not list.

**Alternatives rejected.** Registering on import breaks the no side effects rule and makes test order matter. Loading folders by name with importlib hides what the catalogue contains.

**Consequences.** Adding a failure means writing its package and adding one line to `builtin_scenarios()`. `aflab new` will do both. `ScenarioInfo` is gone.

## D-011: A fix that needs the other side ships both halves

**Context.** Idempotency only works if the caller sends a stable key and the system doing the work checks it.

**Decision.** `IdempotencyKeys` is the guard that attaches the key. `IdempotencyStore` is used inside the tool. The scenario and `docs/guards.md` use both.

**Alternatives rejected.** Shipping only the guard would look like a fix and change nothing.

**Consequences.** Users must change their tool as well as their loop. The docs say so.

## D-012: Each failure has a `world.py` shared by both variants

**Context.** The broken and fixed variants must differ only in the fix, or the comparison means nothing.

**Decision.** `world.py` holds the fake systems, tools, scripted model and the outcome measurement. `broken.py` and `fixed.py` only choose guards. `failure_observed` always measures an effect in the fake world (charges made, emails delivered, tokens spent), never whether a guard fired.

**Alternatives rejected.** Two separate copies of each scenario would drift. Deciding failure by looking for a guard intervention would make the fixed variant pass by definition.

**Consequences.** A contributor reads one file for the setup and one line of difference per variant.

## D-013: The scripted model obeys the injection in both variants

**Context.** A scripted model cannot show that wrapping text makes a real model ignore hidden instructions, and claiming it would be dishonest.

**Decision.** In `tool-output-injection` the model follows the hidden instruction either way. `ToolOutputQuarantine` only labels the output. `CapabilityGate` does the real work by blocking the call.

**Alternatives rejected.** Making the model obey only when the output is unwrapped. That would present an unproven defence as working.

**Consequences.** The README and guard docs call the quarantine advisory and the gate the dependable control.

## D-014: Argument validation uses a small JSON Schema subset

**Context.** `ArgumentValidator` needs schema checks, and the core install should stay small.

**Decision.** Implement required, type, enum, pattern, string length, number bounds and additionalProperties false. Ignore other keywords and say so in the docstring.

**Alternatives rejected.** A `jsonschema` dependency would be more complete but is a larger install for a core that does not need it.

**Consequences.** Complex schemas are only partly checked. The docs list what is covered.

## D-015: Budgets check before the call and say what they did

**Context.** Context and cost limits fail quietly if they trim or overrun without telling anyone.

**Decision.** `ContextBudget` only changes the request, pins system messages, adds a visible note, and stops the run if pinned or newest messages do not fit. `CostBudget` checks before each call, using the known prompt plus a reserve for the reply. Prices are supplied by the caller, and the scenario's rates are labelled illustrative.

**Alternatives rejected.** Checking after the call overspends by one call. Summarising old messages adds a second model and its own error cases.

**Consequences.** A reply longer than the reserve can pass the ceiling slightly. The docs state it.
