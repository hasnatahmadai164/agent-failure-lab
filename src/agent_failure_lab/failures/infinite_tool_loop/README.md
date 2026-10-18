# infinite-tool-loop

The model repeats the same call without progress and burns tokens.

## What happens

The agent asks a status tool about an order. The tool answers "pending, no update available". The model reads that, decides to check again, and gets the same answer. It keeps going. Each pass adds the earlier calls and results to the prompt, so every step costs more than the last. Nothing ends the run until the loop's own step limit does.

## Why it happens

The model has no sense of having already tried something. A result that does not answer the question looks like a reason to try again, and nothing in the loop compares this call with the previous ones. A generous step limit only caps the damage at a large number.

## Impact

Wasted tokens and time, a user waiting for an answer that never comes, and load on whatever the tool calls. In a hosted setup the bill grows while nobody is watching.

## How to detect it in your own system

- Log a signature of each tool call (name plus normalised arguments) and its result. Several identical pairs in a row is the signal.
- Track steps per run and alert on runs that end at the step limit rather than with an answer.
- Compare tokens per run to a baseline and look at the tail.

## The fix

`LoopDetector` watches calls that return the same result repeatedly. After a set number it blocks the next identical call and tells the model to change approach. If the model repeats the call anyway, it stops the run. `StepBudget` is the backstop for any loop the detector does not recognise.

In this scenario the scripted model ignores the warning, so the run ends by guard stop. A model that follows the warning would answer instead.

## Trade-offs

- Polling is legitimate. The detector only counts repeats that return an identical result, so a job-status call whose answer changes is left alone.
- Two calls with slightly different arguments look different to it. Loops that vary the input each time need `StepBudget` or a cost ceiling.
- The threshold is a judgement call. Too low and it interrupts honest retries; too high and the loop runs longer.

## Related guards

`LoopDetector`, `StepBudget`. See `docs/guards.md`.
