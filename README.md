# agent-failure-lab

A catalogue of the ways LLM agents fail in production. Each failure is reproduced deterministically without an API key, and each comes with a tested fix you can import as a guard.

[![CI](https://github.com/hasnatahmadai164/agent-failure-lab/actions/workflows/ci.yml/badge.svg)](https://github.com/hasnatahmadai164/agent-failure-lab/actions/workflows/ci.yml)
[![PyPI](https://img.shields.io/pypi/v/agent-failure-lab.svg)](https://pypi.org/project/agent-failure-lab/)
[![Python versions](https://img.shields.io/pypi/pyversions/agent-failure-lab.svg)](https://pypi.org/project/agent-failure-lab/)
[![License: MIT](https://img.shields.io/badge/license-MIT-blue.svg)](https://github.com/hasnatahmadai164/agent-failure-lab/blob/main/LICENSE)

```bash
pip install agent-failure-lab
aflab run duplicate-side-effect
```

<!-- terminal-output:start -->
<!-- terminal-output:end -->

## The catalogue

Twelve failures so far. Each links to a write-up of what happens, why, how to spot it in your own system, the fix, and what the fix costs.

<!-- catalog:start -->
| Failure | Category | What goes wrong | Fix |
| --- | --- | --- | --- |
| [`duplicate-side-effect`](https://github.com/hasnatahmadai164/agent-failure-lab/blob/main/src/agent_failure_lab/failures/duplicate_side_effect/README.md) | side-effects | A retried tool call charges the customer twice | Idempotency keys |
| [`infinite-tool-loop`](https://github.com/hasnatahmadai164/agent-failure-lab/blob/main/src/agent_failure_lab/failures/infinite_tool_loop/README.md) | control-flow | The model repeats the same call without progress and burns tokens | Loop detection and a step budget |
| [`tool-output-injection`](https://github.com/hasnatahmadai164/agent-failure-lab/blob/main/src/agent_failure_lab/failures/tool_output_injection/README.md) | security | Instructions hidden in a tool result hijack the next action | Quarantine untrusted output and gate sensitive tools |
| [`hallucinated-tool-arguments`](https://github.com/hasnatahmadai164/agent-failure-lab/blob/main/src/agent_failure_lab/failures/hallucinated_tool_arguments/README.md) | tool-use | The model invents an enum value and the tool stores it | Schema validation with bounded repair |
| [`silent-context-truncation`](https://github.com/hasnatahmadai164/agent-failure-lab/blob/main/src/agent_failure_lab/failures/silent_context_truncation/README.md) | context-and-cost | History is cut without any error and the model loses a constraint | A context budget that pins instructions and fails loudly |
| [`runaway-cost`](https://github.com/hasnatahmadai164/agent-failure-lab/blob/main/src/agent_failure_lab/failures/runaway_cost/README.md) | context-and-cost | With no spending ceiling, a run keeps paying for more steps | A cost and token ceiling with a hard stop |
| [`resume-replays-completed-steps`](https://github.com/hasnatahmadai164/agent-failure-lab/blob/main/src/agent_failure_lab/failures/resume_replays_completed_steps/README.md) | side-effects | After a crash, the restarted agent repeats work that already finished | A step journal for safe resume |
| [`tool-timeout-hang`](https://github.com/hasnatahmadai164/agent-failure-lab/blob/main/src/agent_failure_lab/failures/tool_timeout_hang/README.md) | control-flow | A tool never returns and the whole run stalls waiting for it | Deadlines with cancellation and partial results |
| [`parallel-tool-race`](https://github.com/hasnatahmadai164/agent-failure-lab/blob/main/src/agent_failure_lab/failures/parallel_tool_race/README.md) | side-effects | Two parallel tool calls overwrite each other's update | Serialise calls that change the same resource |
| [`ambiguous-tool-selection`](https://github.com/hasnatahmadai164/agent-failure-lab/blob/main/src/agent_failure_lab/failures/ambiguous_tool_selection/README.md) | tool-use | Two tools with overlapping descriptions get confused | Description linting and clearer descriptions |
| [`false-success-claim`](https://github.com/hasnatahmadai164/agent-failure-lab/blob/main/src/agent_failure_lab/failures/false_success_claim/README.md) | tool-use | The agent reports success after a tool returned an error | Postcondition checks before an answer is accepted |
| [`memory-poisoning`](https://github.com/hasnatahmadai164/agent-failure-lab/blob/main/src/agent_failure_lab/failures/memory_poisoning/README.md) | security | Untrusted content saved to memory is later followed as an instruction | Provenance tags and a filter on memory writes |
<!-- catalog:end -->

The same list, with the guards each fix uses and which failures can also run against a real model, is in [docs/catalog.md](https://github.com/hasnatahmadai164/agent-failure-lab/blob/main/docs/catalog.md). [docs/taxonomy.md](https://github.com/hasnatahmadai164/agent-failure-lab/blob/main/docs/taxonomy.md) groups the failures by where they come from.

## Why this exists

Most write-ups about agent failures describe them in prose. You read that an agent "retried a payment and charged twice", agree it sounds bad, and have no way to check whether your own loop would do the same. The fixes are usually a paragraph of advice.

This project turns each failure into something you can run. A scripted model plays the part of an agent that misbehaves in one specific way, and a fake world records what actually happened: how many charges, which emails went out, how many tokens were spent. The same scenario runs twice, once without protection and once with the fix, and the difference in the world is the result. The fixes are ordinary classes you can use in your own loop.

## Using it

List the failures:

```bash
aflab list
```

Run one, with both variants and a verdict:

```bash
aflab run tool-output-injection
aflab run tool-output-injection --trace     # include the step by step trace
aflab compare tool-output-injection         # side by side metrics and traces
```

Run all of them, which is also what CI does:

```bash
aflab run --all --fail-on-unfixed
```

`--fail-on-unfixed` exits with status 1 only when a fixed variant still shows its failure. Output can be switched to `--format json` or `--format md`, and `aflab report` writes a Markdown or JSON summary of every failure to a file with `--output`.

Exit status 2 means the command was wrong (an unknown failure name, options that do not go together). The message is one line, not a traceback.

## Using the guards in your own loop

The guards do not depend on the simulator. Each is a small object with up to five hooks that your loop calls: `before_model`, `after_model`, `before_tool`, `after_tool` and `on_step_end`. A hook returns `None` to leave things alone, a replacement value, `Block(result)` to skip a tool call, or `Stop(reason)` to end the run.

```python
from agent_failure_lab.guards import LoopDetector, StepBudget

guards = [LoopDetector(max_repeats=3), StepBudget(25)]
```

Three runnable examples show how to wire them up:

- [examples/using_guards_in_your_loop.py](https://github.com/hasnatahmadai164/agent-failure-lab/blob/main/examples/using_guards_in_your_loop.py): a hand-written loop with no framework.
- [examples/langgraph_duplicate_side_effect.py](https://github.com/hasnatahmadai164/agent-failure-lab/blob/main/examples/langgraph_duplicate_side_effect.py): the duplicate charge failure and its fix inside a LangGraph graph (`pip install "agent-failure-lab[langgraph]"`).
- [examples/openai_loop_tool_output_injection.py](https://github.com/hasnatahmadai164/agent-failure-lab/blob/main/examples/openai_loop_tool_output_injection.py): the prompt injection fix in a plain loop on the OpenAI SDK.

[docs/guards.md](https://github.com/hasnatahmadai164/agent-failure-lab/blob/main/docs/guards.md) documents every guard, and [docs/porting.md](https://github.com/hasnatahmadai164/agent-failure-lab/blob/main/docs/porting.md) explains how to move one into a framework.

## Running against a real model

Four failures can run against a live model, because they are judged by what happened in the fake world and not by how a scripted model was written: `duplicate-side-effect`, `tool-output-injection`, `hallucinated-tool-arguments` and `parallel-tool-race`.

```bash
pip install "agent-failure-lab[live]"
export OPENAI_API_KEY=...        # on Windows PowerShell: $env:OPENAI_API_KEY = "..."
aflab run duplicate-side-effect --live --model gpt-4o-mini
```

A live run is labelled as such, calls the API and costs money, and its result is not deterministic. The output says what happened and does not claim that the fix works or fails for that model. Live mode has not been checked against the real OpenAI API by the author, so treat it as unverified until you have run it yourself. The tests exercise it against a fake client only.

## Adding a failure

```bash
aflab new my-new-failure --category tool-use
```

This creates the package, a README skeleton and a test, and registers the failure. Then it is your turn to describe the failure properly. [docs/writing-a-failure.md](https://github.com/hasnatahmadai164/agent-failure-lab/blob/main/docs/writing-a-failure.md) walks through it, and [CONTRIBUTING.md](https://github.com/hasnatahmadai164/agent-failure-lab/blob/main/CONTRIBUTING.md) covers the checks. Ideas that are not built yet are in [docs/ideas.md](https://github.com/hasnatahmadai164/agent-failure-lab/blob/main/docs/ideas.md).

## What this is, and what it is not

The scenarios use a scripted model that misbehaves on purpose. They show a failure mechanism and the effect of a fix. They say nothing about how often a real model fails, or whether yours would.

- It is not a benchmark of model reliability. No figure here compares models.
- It is not an agent framework. It has a small loop so the scenarios can run, and the guards are meant to be used in whatever loop you already have.
- It is not a hosted service.
- No guard makes an agent safe. Each closes one specific gap, and each write-up says what it leaves open. The prompt injection quarantine, for example, only labels untrusted text. The capability gate is the control you can rely on.
- Token and cost figures use a rough estimate of four characters per token and illustrative prices. They show proportions, not real bills.
- It has been tested on Linux. The CI runs the tests on Windows as well, but the author has not used the tool on Windows by hand.

## Roadmap

Not promises, only the direction. Possible new failures (schema drift in tool responses, retry storms, stale retrieval, truncated structured output) are listed in [docs/ideas.md](https://github.com/hasnatahmadai164/agent-failure-lab/blob/main/docs/ideas.md). Live mode for more of the failures, and live adapters for providers other than OpenAI, would need a way to judge the result that does not depend on how the model phrases things.

## Contributing

Bug reports, new failure ideas and fixes are welcome. Start with [CONTRIBUTING.md](https://github.com/hasnatahmadai164/agent-failure-lab/blob/main/CONTRIBUTING.md). Please report security problems privately, as described in [SECURITY.md](https://github.com/hasnatahmadai164/agent-failure-lab/blob/main/SECURITY.md).

## License

MIT. See [LICENSE](https://github.com/hasnatahmadai164/agent-failure-lab/blob/main/LICENSE).

## Author

Hasnat Ahmad ([GitHub](https://github.com/hasnatahmadai164), [LinkedIn](https://www.linkedin.com/in/hasnat-ahmad-ai/)).
