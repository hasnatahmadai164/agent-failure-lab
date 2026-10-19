# Guards

A guard is an object with up to five hooks that the agent loop calls: `before_model`, `after_model`, `before_tool`, `after_tool` and `on_step_end`. It overrides the ones it needs. Each hook returns None to leave things alone, a replacement value, `Block(result)` to skip a tool call, or `Stop(reason)` to end the run. Guards run in the order you list them, and each one sees the previous one's change.

```python
from agent_failure_lab.guards import LoopDetector, StepBudget
from agent_failure_lab.sim import Agent, SystemClock

agent = Agent(
    model,
    tools,
    clock=SystemClock(),
    guards=[LoopDetector(), StepBudget(25)],
)
result = agent.run(messages)
```

Notes that apply to every guard:

- Guards keep state for one run. Create fresh instances for each run.
- Every guard that changes behaviour records it in the trace through `run.intervene(...)`.
- A guard does not make an agent safe. It closes one specific gap, and each entry below says which.

## IdempotencyKeys and IdempotencyStore

**Protects against.** Duplicate side effects when a call is retried after a lost response (`duplicate-side-effect`).

**Wire it.** Both halves are needed. `IdempotencyKeys` is a guard that adds the same key to every attempt at the same side-effecting call. `IdempotencyStore` is used inside the tool, or by the service behind it, to run the operation once per key.

```python
guards = [IdempotencyKeys(key_fields=["order_id"])]

store = IdempotencyStore()


def charge(arguments):
    return store.execute(arguments["idempotency_key"], lambda: gateway.charge(arguments))
```

**Trade-offs.** A key built from arguments cannot tell a retry from an intentional repeat, so pick `key_fields` that identify the operation. The store is in memory and keeps results forever. Use your payment or messaging API's own idempotency support where it exists.

## LoopDetector

**Protects against.** An agent repeating the same call and getting the same result (`infinite-tool-loop`).

**Wire it.** `LoopDetector(max_repeats=3, max_warnings=1)`. After three identical call and result pairs, the next identical call is blocked with a message to the model. A further repeat stops the run.

**Trade-offs.** It only counts repeats with identical results, so polling a changing status is fine. Loops that vary their arguments each time are not caught. Use `StepBudget` or `CostBudget` for those.

## StepBudget

**Protects against.** A run that never ends.

**Wire it.** `StepBudget(max_steps)`. The `Agent` has its own step limit as a last resort; this guard does the same for any loop that has none, and records why the run ended.

**Trade-offs.** It stops the run, possibly without an answer. It counts steps, not cost.

## ToolOutputQuarantine and CapabilityGate

**Protects against.** Instructions hidden in tool output that hijack the next action (`tool-output-injection`).

**Wire it.** List the quarantine before the gate, and give the gate a check for each sensitive tool.

```python
quarantine = ToolOutputQuarantine(["fetch_page"])
gate = CapabilityGate(
    {"send_email": allow_only("to", [customer_address])},
    quarantine=quarantine,
)
guards = [quarantine, gate]
```

**Trade-offs.** The quarantine only labels output as data. A model may still obey it, so the gate is the control that counts. The gate needs a policy for each sensitive tool, and the policy must come from something the page cannot influence. With a quarantine linked, checks start only after untrusted content has been read.

## ArgumentValidator

**Protects against.** Invented IDs and enum values reaching a tool (`hallucinated-tool-arguments`).

**Wire it.** `ArgumentValidator(max_repairs=2)`. It validates each call against the tool's own schema. A bad call is not run, and the model gets the list of problems. After `max_repairs` bad calls in a row to one tool, the run stops.

**Trade-offs.** It understands a small part of JSON Schema: required, type, enum, pattern, length, bounds and no extra properties. A schema cannot check that an ID exists. Each repair costs a model call.

## ContextBudget

**Protects against.** History being cut without anyone noticing (`silent-context-truncation`).

**Wire it.** `ContextBudget(max_tokens)`. System messages are pinned. Older messages are dropped first, the request carries a note saying so, and the trace records the count. It stops the run if the pinned messages or the newest message do not fit.

**Trade-offs.** Dropping messages still loses information. Only system messages are pinned. Token counts are estimates, so use your model's tokenizer for real limits.

## CostBudget

**Protects against.** A run with no spending ceiling (`runaway-cost`).

**Wire it.** `CostBudget(max_cost=..., pricing=Pricing(...), completion_reserve=...)`, or `max_tokens`, or both. It checks before each model call whether the call would pass the ceiling.

**Trade-offs.** The reply size is unknown beforehand, so the reserve is an assumption. A longer reply can overshoot by the difference. Prices belong in configuration.
