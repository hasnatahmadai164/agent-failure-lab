# parallel-tool-race

Two parallel tool calls overwrite each other's state.

## What happens

The agent is asked to add two tags to one ticket. Models often request independent calls together, so it asks for both in the same turn. The tool adds a tag by reading the ticket's current tags, appending one, and writing the whole list back. When the two calls run at the same time, both read an empty list, one writes `["urgent"]` and the other writes `["billing"]`. The second write replaces the first. Both calls report success, the agent says both tags were added, and only one is on the ticket.

## Why it happens

Each call is correct on its own. The problem is a read-modify-write on shared state with no protection, which loses updates when two callers interleave. Running tool calls in parallel is what turns a latent weakness into a real one, and nothing in the result shows it.

## Impact

Silent data loss that is hard to reproduce, because it needs two calls to overlap. The agent's report is wrong and so are the downstream decisions that rely on the data.

## How to detect it in your own system

- Look for tools that read a value and write it back, especially on lists and counters.
- Log when several calls from one model turn touch the same record, and compare the record afterwards with what the calls were meant to do.
- Test with two calls on the same record in the same turn, not only with calls on different records.

## The fix

`ConflictSerializer` lets only one side-effecting call per resource run in each turn. The others are held back with a message asking the model to repeat them in its next step, so they run one after another and the second read sees the first write. Calls that only read are never held back, and calls on different resources still run together.

Here the second tag is held back, the model repeats it in the next step, and both tags end up on the ticket.

## Trade-offs

- It costs an extra model step for each held-back call, and it relies on the model repeating the call. A model that forgets leaves the change undone, so the agent should check the result before it reports.
- The guard decides what counts as the same resource from the argument names you give it. A wrong choice either misses a conflict or holds back calls that were safe.
- The better fix is usually in the tool: an atomic append, a version check with retry, or a database transaction. Serialising the calls is for when you cannot change the tool.

## Related guards

`ConflictSerializer`. See `docs/guards.md`.
