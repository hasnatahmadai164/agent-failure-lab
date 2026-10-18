# duplicate-side-effect

A retried tool call charges the customer twice.

## What happens

The agent asks the payment tool to charge an order. The charge reaches the gateway, but the reply is lost and the tool reports a timeout. The model sees an error, does what most agents do with an error, and calls the tool again. The gateway charges a second time.

## Why it happens

A timeout does not tell you whether the work was done. The agent loop cannot know, so it treats the call as failed and the model retries. If the operation has no way to recognise a repeat, every retry is new work.

## Impact

The customer is charged twice for one order. The same pattern applies to anything with a real-world effect: emails sent twice, tickets opened twice, records inserted twice.

## How to detect it in your own system

- Count side effects per logical operation, not per tool call. Alert when one order, ticket or recipient has more than one.
- Look for tool errors that are followed by an identical call within the same run.
- Reconcile what your agent says it did with what the downstream system recorded.

## The fix

Give every side-effecting call an idempotency key that stays the same across retries, and make the system that performs the work remember keys it has already completed.

- `IdempotencyKeys` is a guard that attaches a key derived from the arguments that identify the operation (here, the order id).
- `IdempotencyStore` is the other half. The tool uses it to run the operation once per key and replay the stored result on a repeat.

Neither half is enough alone. A key that nothing checks changes nothing, and a store with no stable key sees each retry as a new request.

## Trade-offs

- A key built from arguments cannot tell a retry from an intentional repeat. Choose `key_fields` so they identify the operation, not the attempt.
- The store here is in memory. A real one needs durable storage and an expiry.
- Many payment and messaging APIs accept an idempotency key natively. Use that rather than building your own wherever it exists.

## Related guards

`IdempotencyKeys`, `IdempotencyStore`. See `docs/guards.md`.
