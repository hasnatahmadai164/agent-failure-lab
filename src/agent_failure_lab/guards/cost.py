from collections.abc import Sequence
from dataclasses import dataclass

from agent_failure_lab.sim import (
    Guard,
    Message,
    RunState,
    Stop,
    Usage,
    estimate_message_tokens,
)


@dataclass(frozen=True, slots=True)
class Pricing:
    """Price per million tokens, in whatever currency unit the caller budgets in."""

    prompt_per_million: float
    completion_per_million: float

    def cost(self, usage: Usage) -> float:
        prompt = usage.prompt_tokens * self.prompt_per_million
        completion = usage.completion_tokens * self.completion_per_million
        return (prompt + completion) / 1_000_000


class CostBudget(Guard):
    """Stops the run before a model call that would push usage past a token or cost ceiling.

    The prompt of the next call is known in advance, so the check includes it. The reply is
    not, so completion_reserve tokens are assumed for it. A reply longer than the reserve can
    overshoot the ceiling by the difference.
    """

    def __init__(
        self,
        *,
        max_tokens: int | None = None,
        max_cost: float | None = None,
        pricing: Pricing | None = None,
        completion_reserve: int = 0,
    ) -> None:
        if max_tokens is None and max_cost is None:
            raise ValueError("set max_tokens, max_cost or both")
        if max_cost is not None and pricing is None:
            raise ValueError("max_cost needs pricing")
        self._max_tokens = max_tokens
        self._max_cost = max_cost
        self._pricing = pricing
        self._completion_reserve = completion_reserve

    def before_model(self, run: RunState, messages: Sequence[Message]) -> Stop | None:
        projected = Usage(
            run.usage.prompt_tokens + sum(estimate_message_tokens(m) for m in messages),
            run.usage.completion_tokens + self._completion_reserve,
        )
        reason = self._breach(projected)
        if reason is None:
            return None
        run.intervene(self.name, f"stopped the run: {reason}")
        return Stop(f"cost budget: {reason}")

    def _breach(self, projected: Usage) -> str | None:
        if self._max_tokens is not None and projected.total_tokens > self._max_tokens:
            return f"the next call would exceed the {self._max_tokens} token budget"
        if (
            self._max_cost is not None
            and self._pricing is not None
            and self._pricing.cost(projected) > self._max_cost
        ):
            return f"the next call would exceed the cost ceiling of {self._max_cost:g}"
        return None
