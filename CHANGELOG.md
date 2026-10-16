# Changelog

All notable changes to this project are recorded here. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and versions follow
[Semantic Versioning](https://semver.org/).

## [Unreleased]

### Added

- Packaging with optional extras (`live`, `langgraph`, `dev`) and the `aflab` entry point.
- Command-line skeleton with `--version` and `list`.
- Simulation core: messages, tools with scheduled failures and delays, a scripted model,
  an injectable clock, a trace recorder, and an agent loop with five guard hook points.
- Scenario protocol, outcome model, registry with slug validation, and a runner that checks
  the broken and fixed variants against each other.
- CI for lint, type check, tests (Python 3.10 to 3.13) and the build check.
