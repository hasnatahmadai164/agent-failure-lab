# Taxonomy

The failures are grouped by where the problem comes from, because that decides where the fix goes. A category is a label on a failure (the `category` field), and the command line accepts only these five.

## side-effects

The agent changes something in the outside world, and the change happens the wrong number of times or in the wrong order. The model may have done nothing unusual. The trouble is that a retry, a restart or a parallel call meets an operation that cannot tell a repeat from new work.

| Failure | One line |
| --- | --- |
| `duplicate-side-effect` | A retried tool call charges the customer twice |
| `resume-replays-completed-steps` | After a crash, the restarted agent repeats work that already finished |
| `parallel-tool-race` | Two parallel tool calls overwrite each other's update |

The fixes live mostly on the tool's side: keys the operation can check, a journal that survives a crash, calls that touch the same resource run one at a time. A guard on the agent can supply the key or the ordering, but something has to check it.

## control-flow

The loop itself misbehaves. It does not stop, or it waits forever. Nothing is wrong with any single step, and the problem shows up only when you look at the run as a whole.

| Failure | One line |
| --- | --- |
| `infinite-tool-loop` | The model repeats the same call without progress and burns tokens |
| `tool-timeout-hang` | A tool never returns and the whole run stalls waiting for it |

The fixes are limits the loop enforces: how many times, how many steps, how long.

## security

Text the agent reads from outside gets treated as an instruction, either right away or later through memory.

| Failure | One line |
| --- | --- |
| `tool-output-injection` | Instructions hidden in a tool result hijack the next action |
| `memory-poisoning` | Untrusted content saved to memory is later followed as an instruction |

Labelling untrusted text helps a careful model and does nothing for a careless one. The dependable fixes restrict what the agent is allowed to do after it has read something untrusted.

## tool-use

The agent calls tools wrongly, picks the wrong tool, or reports what happened wrongly.

| Failure | One line |
| --- | --- |
| `hallucinated-tool-arguments` | The model invents an enum value and the tool stores it |
| `ambiguous-tool-selection` | Two tools with overlapping descriptions get confused |
| `false-success-claim` | The agent reports success after a tool returned an error |

The fixes check what goes into a tool, what the tools are called and described as, and whether the final answer matches what the tools returned.

## context-and-cost

The agent runs out of room or money, and either is not noticed until too late.

| Failure | One line |
| --- | --- |
| `silent-context-truncation` | History is cut without any error and the model loses a constraint |
| `runaway-cost` | With no spending ceiling, a run keeps paying for more steps |

The fixes are budgets that act before the call is made and say what they did.

## Choosing a category for a new failure

Ask where the fix goes. If it goes in the tool or the system behind it, the category is probably `side-effects`. If it is a limit on the loop, it is `control-flow`. If it concerns text the agent should not trust, it is `security`. If it concerns the shape of calls and answers, it is `tool-use`. If it concerns tokens, money or the context window, it is `context-and-cost`.

A failure that fits two categories gets the one where its fix lives. If none fit, open an issue before adding a sixth category.
