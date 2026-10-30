# Ideas

Failures and improvements that are not built yet. Nothing here is a promise. If you want to take one, open an issue first so that we can agree on how to measure it.

## Possible new failures

**Schema drift in tool responses.** A tool's response gains, renames or retypes a field. The model keeps reading the old shape and quietly uses a missing value. A fix might validate tool output against the schema the agent was written for, and fail visibly when it no longer matches.

**Thundering-herd retries.** Many agents (or many steps of one) retry a struggling service at the same moment, which keeps it down. A fix would be backoff with jitter and a shared retry budget. The measurable outcome is the number of calls reaching the service in a window.

**Stale retrieval.** The agent answers from a document that has since changed, and gives no sign of its age. A fix could attach a retrieval time to each passage and refuse or flag answers built on passages past a limit.

**Truncated structured output.** The model hits its output limit in the middle of a JSON object, and the parser either throws away the run or accepts half an object. Fixes include detecting the finish reason and continuing, or asking for a smaller structure.

**Wrong-tenant data.** A tool call uses an identifier the model took from earlier in the conversation, and it belongs to another customer. A fix would bind identifiers to the session in the tool, not trust the model to pass the right one.

**Unbounded fan-out.** A planning step spawns one sub-task per item in a list that turns out to hold thousands. A fix is a limit on branching, set before the work starts.

## Possible improvements

- Live adapters for providers other than OpenAI, behind the same small model interface.
- Live mode for more failures, which needs a measure of success that does not depend on how the model words things.
- A way to run your own agent loop against a scenario's fake world, so that you can find out whether your loop shows the failure.
- Exporting a run's trace in a format that tracing tools can read.
- Saving a run's JSON and comparing it with an earlier one, to see whether a change to a guard altered an outcome.

## Not planned

- Benchmarks that rank models. This project shows mechanisms, and a scripted model cannot support claims about real models.
- A hosted service or dashboard.
- Guards that call a model to judge another model. They are interesting, but they bring a second source of error and a dependency, and they are hard to test deterministically.
