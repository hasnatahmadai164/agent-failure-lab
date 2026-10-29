# Porting a guard to a framework

The guards are written against five hooks and do not import the simulator's agent loop. To use one in another framework, you call its hooks from the points in that framework where the same things happen. This page explains what to call and when, then shows the two ports in the repository.

## What the hooks expect

A guard works with a `RunState` that holds the clock, the trace, the tool specs, the history, and the current step number. Build one for each run:

```python
from agent_failure_lab.sim import ManualClock, RunState, SystemClock, Trace

clock = SystemClock()
run = RunState(clock=clock, trace=Trace(clock), tool_specs=specs, history=[])
```

Use `SystemClock` in real code so deadlines and the trace follow real time. `ManualClock` is for tests, where time moves only when you say.

Keep the state up to date as the run goes on, because guards read it: set `run.step` to the current model turn, add each message to the history with `run.append(message)`, and add the tokens each reply used with `run.usage = run.usage + turn.usage`. `StepBudget` reads the step, `CostBudget` reads the usage, and `PostconditionCheck` and `ConflictSerializer` read the history.

Then call the hooks at these points:

| Where in your loop | Hook | What a return value means |
| --- | --- | --- |
| Before sending messages to the model | `before_model(run, messages)` | `None` to leave them, a list to send instead, `Stop` to end the run |
| After the model replies | `after_model(run, turn)` | `None`, a replacement `ModelTurn`, or `Stop` |
| Before running a tool call | `before_tool(run, call)` | `None`, a replacement call, `Block(result)` to skip the tool and use this result, or `Stop` |
| After a tool returns | `after_tool(run, call, result)` | `None`, a replacement result, or `Stop` |
| At the end of a step | `on_step_end(run)` | `None` or `Stop` |

Run the guards in order and pass each one the previous one's change. If a guard returns `Stop`, end the run. If it returns `Block`, do not call the tool and put the blocked result in the history as if the tool had returned it.

`examples/using_guards_in_your_loop.py` is a complete loop that does this with three of the hooks.

## Messages and tool calls

The hooks use the library's own `Message`, `ModelTurn`, `ToolCall`, `ToolResult` and `ToolSpec` types. Convert at the edge of your framework:

- A `ToolCall` has a name, an arguments mapping, and an id. Keep the id your provider gave you so the result can be matched to it.
- A `ToolResult` has content text and an `is_error` flag.
- A `ToolSpec` has a name, a description, a JSON Schema for the parameters, and optional `side_effects` labels. The guards that need to know which tools change the world (`IdempotencyKeys`, `CapabilityGate`) read those labels.

Arguments that arrive as malformed JSON should not be silently fixed. The live adapter in the library passes them on as `{"_invalid_arguments": "<raw text>"}`, so that `ArgumentValidator` or the tool can reject them visibly.

## Port 1: LangGraph

`examples/langgraph_duplicate_side_effect.py` has a graph with two nodes, one for the model and one for tools. The guard calls go inside the tool node:

1. Build the `ToolCall`.
2. Call `before_tool` on each guard. `IdempotencyKeys` returns the call with a stable key added.
3. Run the tool, which uses `IdempotencyStore` so a repeat with the same key returns the stored result.
4. Call `after_tool` and put the result in the graph state.

The model node and the edges do not change. Install with `pip install "agent-failure-lab[langgraph]"` and run `python examples/langgraph_duplicate_side_effect.py`. It prints two charges without the guard and one with it. If you use a prebuilt agent such as `create_react_agent`, there is no tool node of your own to edit. Replace it with a graph like the one in the example, or wrap each tool function so that it calls the hooks itself.

## Port 2: a plain OpenAI SDK loop

`examples/openai_loop_tool_output_injection.py` is the usual loop of calling `client.chat.completions.create`, running the tool calls, and appending tool messages. It places `ToolOutputQuarantine` and `CapabilityGate` between the model's request and the tool. Two details matter:

- The quarantine rewrites the page text in `after_tool`, so the model sees it wrapped as untrusted. It does not stop the model from obeying it.
- The gate refuses `send_email` to any address outside the allowed list once untrusted text has been read. This part holds even when the model obeys.

This example calls the real API. Pass a client into `main(client=...)` to run it against a fake, which is how the tests run it.

## What to check after porting

- Guards keep state for one run. Create new instances for each run, not once at import time.
- Trace output: after a run, `run.trace.events` should show a `GUARD` event whenever a guard acted. If your port shows none, the hooks are probably not being called.
- Failures that need more than the loop: `IdempotencyStore`, `Journal` and similar parts are used by the tool or the service behind it, and your framework cannot add them for you. See `docs/guards.md` for which half goes where.
