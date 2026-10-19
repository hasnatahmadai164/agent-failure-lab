# hallucinated-tool-arguments

The model invents an ID or enum value and the tool acts on it.

## What happens

The user asks for next-day delivery. The shipping tool accepts three speeds: standard, express and overnight. The model calls it with `next_day`, a value that sounds right and does not exist. The tool is a thin wrapper over a database and writes the value as given. The order now holds a shipping speed the warehouse cannot fulfil, and the agent tells the user it is done.

## Why it happens

The model fills in arguments from what it infers, not from what it checked. A schema in the tool description is guidance, not enforcement, and nothing in the loop compares the call with the schema before the tool runs. Tools that trust their caller turn a plausible guess into stored data.

## Impact

Bad data that surfaces later and somewhere else, with a confident success message in the meantime. The same failure with an invented ID writes to the wrong record or none at all.

## How to detect it in your own system

- Validate every tool call against its schema in logging, even if you do not yet reject. Count violations per tool.
- Look for values in your data that are not in the enums your tools declare.
- Watch for runs where a tool call is followed by a downstream failure unrelated to the tool itself.

## The fix

`ArgumentValidator` checks each call against the tool's schema before it runs. An invalid call is not executed. The model receives a message listing the problems and the allowed values and may try again. After a set number of failed repairs in a row, the run stops, so the repair loop is bounded.

Here the validator rejects `next_day` and the model corrects itself to `overnight` on the second call.

## Trade-offs

- A schema can say what a value looks like but not whether it exists. An order id that matches the pattern but belongs to nobody needs a lookup in the tool itself.
- The validator supports a small part of JSON Schema (required, type, enum, pattern, length, bounds, no extra properties). Complex schemas need a full validator.
- Each repair costs a model call. Keep the limit low.

## Related guards

`ArgumentValidator`. See `docs/guards.md`.
