# tool-timeout-hang

A tool never returns and the whole run stalls waiting for it.

## What happens

The agent builds a daily summary from two systems. The sales system answers at once. The inventory system accepts the request and then does not answer for an hour. Nothing in the loop sets a limit on a tool call, so the agent waits the full hour before it can write anything, and the user gets nothing in the meantime.

## Why it happens

A tool call is an ordinary function call, and a function call blocks until it returns. Many client libraries have no timeout by default, or one so long it never fires. The model is not involved: it asked for data and is waiting for it, like any caller.

## Impact

One slow dependency holds up the whole run, and every run that touches it. Workers pile up waiting, and the user sees a hung request instead of a partial answer that would have been useful.

## How to detect it in your own system

- Record the duration of every tool call and alert on the slowest ones, not the average.
- Track total run time against the promise you make to users, and look at runs that exceed it.
- Check that every tool you call over a network has an explicit timeout set.

## The fix

`Deadline` puts a time limit on each tool call and on the run as a whole. A call that reaches its limit is cancelled and the model is told to carry on with the results it already has and to say what is missing. The limit on a call shrinks as the total deadline gets closer, and no new work starts once the total has passed.

Here the inventory call is cancelled after 5 seconds and the agent finishes with a summary that says inventory data is missing.

## Trade-offs

- Cancelling a call does not always stop the work on the other side. A write that was cancelled may still have happened, so combine this with idempotency keys for tools that change things.
- A partial answer is only acceptable if the task allows one. For some tasks, stopping with an error is the better outcome.
- Limits that are too tight turn slow but healthy calls into failures. Base them on observed durations.

## Related guards

`Deadline`, and `IdempotencyKeys` for cancelled writes. See `docs/guards.md`.
