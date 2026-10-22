# Changelog

All notable changes to this project are recorded here. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and versions follow
[Semantic Versioning](https://semver.org/).

## [Unreleased]

## [0.1.0] - 2026-10-20

First release.

### Added

- Twelve failures, each with a deterministic reproduction, a tested fix and a write-up:
  `duplicate-side-effect`, `infinite-tool-loop`, `tool-output-injection`,
  `hallucinated-tool-arguments`, `silent-context-truncation`, `runaway-cost`,
  `resume-replays-completed-steps`, `tool-timeout-hang`, `parallel-tool-race`,
  `ambiguous-tool-selection`, `false-success-claim` and `memory-poisoning`.
- Guards that can be used in any loop: `IdempotencyKeys`, `IdempotencyStore`, `LoopDetector`,
  `StepBudget`, `ToolOutputQuarantine`, `CapabilityGate`, `ArgumentValidator`, `ContextBudget`,
  `CostBudget`, `StepJournal`, `Deadline`, `ConflictSerializer`, `ToolDescriptionLinter`,
  `PostconditionCheck` and `MemoryWriteFilter`, documented in `docs/guards.md`.
- A small simulation core: messages, tools with scheduled failures and delays, a scripted model,
  an injectable clock, a trace recorder, and an agent loop with five guard hooks. Tool calls in
  one turn can run as a concurrent batch against a shared store that models lost updates.
- The `aflab` command line tool: `list`, `run`, `compare`, `report` and `new`. `run` takes
  `--variant`, `--trace`, `--format text|json|md`, `--all` and `--fail-on-unfixed`.
- Live mode (`--live`, `--model`) for the four failures that are judged by their effects in the
  fake world, using the OpenAI chat completions API through the optional `live` extra. It has
  only been tested against a fake client.
- `aflab new`, which scaffolds a working failure package, a test and a README skeleton, and
  registers it.
- `scripts/generate_catalog.py`, which keeps `docs/catalog.md` and the README table in step with
  the registry, with `--check` for CI.
- Examples of the guards in a hand-written loop, in a LangGraph graph, and in a plain OpenAI SDK
  loop, and `docs/porting.md` explaining how to move a guard into a framework.
- Documentation: taxonomy, guards reference, a guide to writing a failure, an ideas backlog,
  design decisions, a code of conduct, a security policy, and issue and pull request templates.
- CI for lint, type checking, the catalogue check, tests on Python 3.10 to 3.13 (and Windows),
  the examples, and the build. A release workflow publishes tagged versions to PyPI through
  trusted publishing.

[Unreleased]: https://github.com/hasnatahmadai164/agent-failure-lab/compare/v0.1.0...HEAD
[0.1.0]: https://github.com/hasnatahmadai164/agent-failure-lab/releases/tag/v0.1.0
