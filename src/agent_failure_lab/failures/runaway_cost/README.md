# runaway-cost

No spending ceiling, so a run keeps paying for more steps.

## What happens

The agent searches a document store for the refund policy. It is never satisfied with the results and searches again with a slightly different query, over and over. Each search result is added to the conversation, so every model call carries everything before it. The cost per step rises with each step. The only limit is a generous step cap.

## Why it happens

Nothing in the loop knows what a run is allowed to cost. A step limit counts steps, not money, and the price of a step is not constant: the prompt grows. Because every query is different, the repeated-call checks that catch a plain loop do not fire.

## Impact

A single stuck run can cost far more than a normal one, and many stuck runs in parallel can use up a budget before anyone looks. The effect is silent until the invoice or a rate limit.

## How to detect it in your own system

- Record tokens and cost for every run, and alert on the tail of the distribution, not only the average.
- Track prompt tokens per step inside a run. A steady climb with no final answer is the pattern.
- Set a per-run and a per-day ceiling in your own code, in addition to any limit your provider offers.

## The fix

`CostBudget` checks, before each model call, what the run would have used if the call went ahead. It counts the prompt that is about to be sent and a reserve for the reply. If that would pass the token or cost ceiling, the run stops and the trace says why. The ceiling can be tokens, a cost computed from a price table you supply, or both.

The rates in this scenario are arbitrary cost units chosen for the example. They are not any provider's prices.

## Trade-offs

- The reply length is not known in advance. The reserve is an assumption, and a reply longer than the reserve can overshoot the ceiling by the difference.
- A hard stop ends the run, possibly with no answer. Some systems prefer to stop calling tools and ask for a final answer with what is available.
- Real prices change. Keep the price table in configuration, not in code.

## Related guards

`CostBudget`, and `StepBudget` for a step ceiling. See `docs/guards.md`.
