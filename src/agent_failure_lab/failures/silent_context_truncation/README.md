# silent-context-truncation

The history is cut and the model loses a constraint without any error.

## What happens

The assistant has a system prompt with a rule: refunds above 100 EUR need manager approval. The conversation grows long. To stay within the context window, the application keeps only the newest messages that fit. The system prompt is the oldest message, so it goes first. The model, which can no longer see the rule, refunds 250 EUR directly.

## Why it happens

Trimming is usually written as "keep the last N". It treats every message as equal, and the instructions are the oldest message of all. Nothing is raised when something is dropped, so the model behaves as if the rule had never existed, and the logs show a normal run.

## Impact

A policy the operator believes is in force quietly stops applying once a conversation is long enough. The failure depends on length, so it shows up in production on the longest and often the most valuable conversations, and rarely in short tests.

## How to detect it in your own system

- Record how many messages and tokens were dropped on every model call. A non-zero count should be visible, not silent.
- Check that the system prompt is present in the request that was actually sent, not just in the stored history.
- Test with a conversation long enough to hit the limit and assert that each rule still holds.

## The fix

`ContextBudget` keeps the request inside a token limit while treating system messages as pinned. It drops the oldest other messages first, puts a note in the request saying how many earlier messages were omitted, and records the drop in the trace. If the pinned messages alone do not fit, or the newest message does not fit, it stops the run instead of sending a damaged request.

It changes only the request. The stored history stays complete.

## Trade-offs

- Dropping old messages still loses information. The note tells the model that something is missing, but it cannot recover the content. Summarising older messages is a common alternative and carries its own risk of getting the summary wrong.
- Only system messages are pinned. A constraint stated by the user early in the chat is not protected unless you move it into a pinned message.
- The token count here is an estimate. Real limits need the model's own tokenizer.

## Related guards

`ContextBudget`. See `docs/guards.md`.
