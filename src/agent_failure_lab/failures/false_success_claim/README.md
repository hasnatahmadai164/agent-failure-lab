# false-success-claim

The agent reports success after a tool returned an error.

## What happens

The agent is asked to set the stock level of a product. The update tool rejects the call because the product code does not exist and returns an error. The agent ends with "Inventory for SKU-9 has been updated to 40." The user reads that, believes it, and moves on. Nothing was changed.

## Why it happens

The final answer is text the model writes after the fact. It is shaped by what the task asked for and what the model expected to happen, and it is not checked against what the tools returned. A model can also treat an error as a detail to work around and still produce the sentence the user was hoping for.

## Impact

A confident, wrong report is worse than a visible failure. The user does not retry, the system is left in the old state, and the mismatch is found later, usually by someone else.

## How to detect it in your own system

- Compare what the agent said it did with what the tools returned in the same run. A success claim that follows an error result is the signal.
- Check the outcome in the system of record, not in the agent's own report.
- Add tests where the tool is made to fail and assert the final answer does not claim success.

## The fix

`PostconditionCheck` looks at the evidence before a final answer is accepted. Each condition inspects the conversation and returns a problem or nothing. Here the condition is `tool_succeeded("update_inventory")`: the latest result from that tool must exist and must not be an error. When it fails, the answer is replaced with a plain statement of what could not be confirmed, including the tool's own error.

## Trade-offs

- It replaces any final answer when a condition fails, including an honest one. Keep conditions narrow and tied to the outcome that was promised.
- A condition can only check what the conversation shows. It cannot tell that a tool returned success for work that did not happen, so for important actions check the real system.
- A replaced answer ends the run with a failure message. For some tasks the better behaviour is to send the model back to try again, which needs a loop that supports it.

## Related guards

`PostconditionCheck`, `tool_succeeded`. See `docs/guards.md`.
