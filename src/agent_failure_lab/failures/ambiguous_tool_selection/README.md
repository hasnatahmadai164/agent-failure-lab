# ambiguous-tool-selection

Two tools with overlapping descriptions get confused.

## What happens

A support assistant has two tools for writing on a ticket. One sends a message the customer will read. The other adds a note only staff can see. Their descriptions are almost the same: "Add a message to a support ticket" and "Add a comment to a support ticket". Asked to leave an internal note, the model has nothing in the descriptions to tell the tools apart and picks the first one. The internal remark about a refund goes to the customer.

## Why it happens

The model chooses a tool from its name and description. When two descriptions say nearly the same thing, the choice is close to arbitrary and tends to follow the order they are listed in. The names were chosen by people who knew the difference. The model only has the words.

## Impact

The action is valid and succeeds, so nothing looks wrong. The effect is wrong and often cannot be undone, as with a message the customer has already read.

## How to detect it in your own system

- Read your tool descriptions side by side and ask whether someone new could tell which to use.
- Measure how much their wording overlaps, as the linter here does.
- Review calls where a tool was used and then followed by a correction or a complaint.

## The fix

The fix is in the descriptions: say who sees the result and when not to use the tool. The new descriptions are "Send a reply that the customer will see. Not for internal remarks." and "Add an internal note to the ticket that only staff can see."

`ToolDescriptionLinter` keeps it that way. It compares the descriptions before the first model call and stops the run if two overlap too much, or if one is too short to mean anything. The same check can run in your test suite so a careless edit fails the build.

In this scenario the scripted model chooses by how many words a description shares with the request. That stands in for a real model's behaviour and shows the mechanism, not how often real models choose wrongly.

## Trade-offs

- Word overlap is a blunt measure. Two descriptions can use different words for the same thing, or share words and still be clear. Treat the linter as a prompt to review, and tune its limit.
- Better descriptions lower the chance of a wrong choice. They do not remove it. For actions that cannot be undone, add a confirmation step or merge the two tools into one with an explicit audience argument.
- The linter stops the run in strict mode. Use the non-strict setting to log findings without blocking.

## Related guards

`ToolDescriptionLinter`, and `CapabilityGate` for actions that need a check on their arguments. See `docs/guards.md`.
