# Design decisions

Each entry has the context, the decision, the alternatives I rejected, and the consequences. New entries go at the end.

## D-001: The project brief wins over my generic rules

**Context.** My working rules were written for web services (pydantic-settings, structlog, FastAPI, async). This project is a small CLI library with its own stack.

**Decision.** Follow the project brief: Python 3.10 or newer, dataclasses and Protocols, standard library plus typer and rich. No settings class, no structlog, no async. The only environment variable is `OPENAI_API_KEY`, read in one place (`live.py`).

**Alternatives rejected.** Adding pydantic-settings and structlog to match the generic rules. Nothing in the core needs them.

**Consequences.** Smaller install. If logging is needed later, it gets its own entry.

## D-002: hatchling, with the version kept in `__init__.py`

**Context.** I need a `src/` layout, extras, a console script, and one place for the version.

**Decision.** Use hatchling. The version lives in `__version__` in `src/agent_failure_lab/__init__.py` and hatchling reads it from there. 

**Alternatives rejected.** setuptools-scm ties the version to git tags and history during builds. Poetry is heavy for two dependencies. A version in two files drifts.

**Consequences.** A release bump is a one-line edit. The license is an SPDX string, so building needs hatchling 1.27 or newer.

## D-003: Two runtime dependencies, everything else is an extra

**Context.** The core should install small and rarely clash with other packages.

**Decision.** Runtime dependencies are typer and rich only. OpenAI is the `live` extra, LangGraph is the `langgraph` extra, and the development tools are the `dev` extra. Each range has a lower bound and the next major version as the upper bound. The `dev` extra needs twine 7 or newer: twine 6.2 rejected the metadata hatchling writes, and I found that by running the build check. typer has to be 0.16 or newer: I ran the test suite against older releases, and 0.12.3 and earlier fail on `str | None` annotations, while 0.12.4 to 0.15.x break with click 8.2 and newer.

**Alternatives rejected.** Exact pins clash with other packages. No upper bounds means a future major release could break the CLI. argparse avoids a dependency but I would write the help text and tables by hand.

**Consequences.** The suite passes with typer 0.16.0 and rich 13.7.0 on Python 3.10, and with the newest releases on 3.10 to 3.13. The LangGraph example passes with langgraph 0.2.60 and with 1.2.16. The openai lower bound and the dev tools' lower bounds are not tested.

## D-004: The CLI is built by a function that takes the registry

**Context.** Tests have to run the CLI with their own scenarios, and I want no global state and nothing happening at import time.

**Decision.** `build_app(registry)` returns the Typer app, and its commands use the registry passed in. `main()` builds the real registry and runs the app. There is no module-level app.

**Alternatives rejected.** A module-level app with a global registry filled on import. Tests would then depend on import order.

**Consequences.** CLI tests build a throwaway registry. The entry point is `agent_failure_lab.cli:main`.

## D-005: CI runs in three separate jobs

**Context.** The brief wants ruff, mypy, pytest on Python 3.10 to 3.13, `aflab run --all --fail-on-unfixed`, and a build check. I develop on Windows.

**Decision.** Four jobs: lint (ruff check, ruff format check, mypy, the catalogue check), test (3.10 to 3.13 on Ubuntu, plus 3.12 on Windows, then `aflab run --all --fail-on-unfixed`), examples (installs the langgraph extra and runs the examples test), and build (`python -m build`, `twine check`).

**Alternatives rejected.** One job that does everything is slower and the failures are harder to read. A full OS matrix costs more minutes for little extra signal.

**Consequences.** A lint failure does not hide a test failure, and the LangGraph install cannot break the main test matrix.

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

**Consequences.** Token and cost figures are consistent but not real costs, and the README says so. Model calls take no simulated time. Tools run one after another unless a turn is run as a batch (D-016).

## D-009: An injectable clock, and the trace uses it

**Context.** Timeout and TTL scenarios cannot wait in real time, but a deadline guard also has to work in a live loop.

**Decision.** `Clock` is a Protocol with two implementations: `ManualClock`, which moves only when told to, and `SystemClock`, which uses monotonic time and real sleep. `Trace` takes a clock and stamps every event with it.

**Alternatives rejected.** Patching `time` in tests hides the dependency. Passing timestamps by hand is easy to get wrong.

**Consequences.** Scenarios run instantly and still show elapsed time. `SystemClock` has one small test and is otherwise used only in live runs.

## D-010: Scenarios, the runner, and two changes from the brief

**Context.** The brief asks for a Scenario protocol and a registry. It also says each failure's `__init__.py` registers it, and that failure folders are named after the slug.

**Decision.** `Scenario` is a Protocol and `ScenarioDefinition` is the normal implementation, with one function per variant. `Outcome` holds the variant, `failure_observed`, the trace, metrics and findings. The runner returns a `PairResult`, and its `contract_holds` means the broken variant fails and the fixed one does not. Slugs must be lowercase words joined by single hyphens. Two changes from the brief. Folders and test files use the slug with underscores, because a hyphenated folder cannot be imported. Failure packages do not register themselves on import. They expose a scenario, and `builtin_scenarios()` lists them. I also added `scenario.py` and `sim/hooks.py`, which the layout in the brief did not list.

**Alternatives rejected.** Registering on import breaks the no side effects rule and makes test order matter. Loading folders by name with importlib hides what the catalogue contains.

**Consequences.** Adding a failure means writing its package and adding one line to `builtin_scenarios()`. `aflab new` does both: it writes the package and edits `failures/__init__.py` itself, and prints what to do by hand if the file has an unexpected shape.

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

## D-016: Parallel tool calls are a batch against a snapshot

**Context.** The race needs two calls in one turn to overlap, and the agent runs tools one after another.

**Decision.** `Agent(batch=...)` opens a batch around any turn with more than one tool call. `SharedStore` makes reads inside a batch see the data from when it began and applies writes together at the end, so a read-modify-write loses an update.

**Alternatives rejected.** Real threads would make the failure depend on timing. A fake guard that simulates it would hide the mechanism in the wrong place.

**Consequences.** The race is exact and repeatable. It models lost updates only, not every concurrency bug.

## D-017: Some fixes need the model, or the tool, to cooperate

**Context.** `ConflictSerializer` holds a call back and asks the model to repeat it. `StepJournal` needs a durable journal. `Deadline` cancels a call but cannot undo work on the other side.

**Decision.** Ship them with their limits written next to them in the README and in `docs/guards.md`, and pair them with idempotency keys where an effect may have happened.

**Alternatives rejected.** Hiding the limits would make the fixes look complete when they are not.

**Consequences.** Users read the trade-offs before relying on a guard.

## D-018: Detection by matching text is limited, and says so

**Context.** `PostconditionCheck` and `MemoryWriteFilter` decide from the words in the conversation.

**Decision.** Keep them simple and testable. The memory filter matches the saved text against untrusted output and a list of instruction phrases. A test documents that a paraphrase gets through.

**Alternatives rejected.** A classifier would add a model, a dependency and its own errors.

**Consequences.** They are a first line of defence. The READMEs say what they miss.

## D-019: The CLI has three output formats and two exit codes

**Context.** The same results are read by people in a terminal, pasted into issues, and checked by CI.

**Decision.** `run` and `compare` print text by default, with `--format json` and `--format md` for the other two. `report` writes Markdown or JSON, to the terminal or a file. Exit status 0 means the command worked. Status 2 means the command was wrong (an unknown slug, options that do not go together, live mode not set up) and prints one line starting with `error:`. Status 1 is used only by `--fail-on-unfixed`, when a fixed variant still shows its failure. A broken variant that does not fail is a different problem and is not reported through status.

**Alternatives rejected.** Using status 1 for every error would make CI unable to tell a bad command from a bad fix.

**Consequences.** The three formats come from the same data (`report.py`), so they cannot disagree. JSON never contains a trace unless `--trace` is given.

## D-020: Every console turns Rich markup off

**Context.** Rich reads square brackets as styling. A tool result such as `[end of untrusted content]` was silently deleted from the output, which is the opposite of what a reproduction should do.

**Decision.** Every console is created with `markup=False` and `highlight=False`. Colour comes from styles passed in code, never from text.

**Alternatives rejected.** Escaping brackets by hand would be forgotten the next time a string is printed.

**Consequences.** Tool output is printed exactly as it was. A test prints a bracketed string to prove it.

## D-021: Live mode is a thin adapter around an injected client

**Context.** Four failures are judged by what happened in the fake world, so they can run against a real model. The default test run must not touch the network or need a key.

**Decision.** `OpenAIChatModel` takes a client as an argument, and only `create_client` imports `openai`, lazily, with the import function injectable. `openai` is an optional extra and not a dev dependency, so type checking sees the client as `Any`. A missing package or key is reported as a one line error. Request failures are wrapped in `LiveRequestError`. Live runs are labelled non-deterministic and make no claim that the fix worked. Malformed tool arguments are kept as `{"_invalid_arguments": raw}` so a validator can reject them visibly.

**Alternatives rejected.** Importing `openai` at the top of the module would make the core need it. Mocking `openai` with a patch hides the interface being used.

**Consequences.** Tests use a fake client shaped like the real responses. The adapter has not been run against the real API, and no document says it has.

## D-022: Rendering, reporting and the catalogue are separate modules

**Context.** The same results are printed, serialised and written into documentation.

**Decision.** `report.py` turns results into plain data, JSON and Markdown. `render.py` only draws with Rich. `catalog.py` builds the table and splices it between markers, and `scripts/generate_catalog.py` writes it, with `--check` for CI. The README table uses absolute links so that it also works on PyPI. Tests compare the committed README and `docs/catalog.md` with what the registry generates, and scan the documentation for dashes, banned words and broken links.

**Alternatives rejected.** Writing the table by hand drifts the first time a failure is added.

**Consequences.** Adding a failure means running one script. A documentation rule that is only written down gets broken, so the rules are tests.

## D-023: Releases go out through PyPI trusted publishing

**Context.** A long-lived PyPI token in repository secrets is a thing to leak and rotate.

**Decision.** Pushing a tag `v*` runs the release workflow. It builds, runs `twine check`, fails if the tag differs from `__version__`, and publishes with `pypa/gh-action-pypi-publish` using an OpenID Connect token from a `pypi` environment. No secret is stored.

**Alternatives rejected.** An API token in secrets works but must be created, scoped and rotated by hand.

**Consequences.** The publisher has to be registered on PyPI once, before the first tag. The `pypi` environment can require approval before anything is published.
