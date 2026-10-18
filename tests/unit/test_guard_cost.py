from collections.abc import Callable

import pytest

from agent_failure_lab.guards.cost import CostBudget, Pricing
from agent_failure_lab.sim import (
    EventKind,
    RunState,
    Stop,
    Usage,
    estimate_message_tokens,
    user_message,
)

MakeRun = Callable[..., RunState]

PRICING = Pricing(prompt_per_million=100.0, completion_per_million=200.0)
MESSAGE = user_message("hello there")
MESSAGE_TOKENS = estimate_message_tokens(MESSAGE)


def test_pricing_charges_prompt_and_completion_tokens_at_their_own_rates() -> None:
    assert PRICING.cost(Usage(prompt_tokens=1_000_000, completion_tokens=500_000)) == 200.0


def test_a_call_inside_the_token_budget_goes_ahead(make_run: MakeRun) -> None:
    guard = CostBudget(max_tokens=MESSAGE_TOKENS)

    assert guard.before_model(make_run(), [MESSAGE]) is None


def test_a_call_that_would_pass_the_token_budget_is_stopped_before_it_is_made(
    make_run: MakeRun,
) -> None:
    run = make_run()
    guard = CostBudget(max_tokens=MESSAGE_TOKENS - 1)

    outcome = guard.before_model(run, [MESSAGE])

    assert isinstance(outcome, Stop)
    assert "token budget" in outcome.reason
    assert len(run.trace.of_kind(EventKind.GUARD)) == 1


def test_tokens_already_used_count_against_the_budget(make_run: MakeRun) -> None:
    run = make_run(usage=Usage(prompt_tokens=100, completion_tokens=50))
    guard = CostBudget(max_tokens=100 + 50 + MESSAGE_TOKENS - 1)

    assert isinstance(guard.before_model(run, [MESSAGE]), Stop)


def test_the_completion_reserve_is_counted_for_the_reply_that_has_not_happened_yet(
    make_run: MakeRun,
) -> None:
    guard = CostBudget(max_tokens=MESSAGE_TOKENS + 10, completion_reserve=11)

    assert isinstance(guard.before_model(make_run(), [MESSAGE]), Stop)


def test_a_call_that_would_pass_the_cost_ceiling_is_stopped(make_run: MakeRun) -> None:
    run = make_run(usage=Usage(prompt_tokens=10_000, completion_tokens=0))
    projected = PRICING.cost(Usage(10_000 + MESSAGE_TOKENS, 0))

    assert CostBudget(max_cost=projected, pricing=PRICING).before_model(run, [MESSAGE]) is None
    stop = CostBudget(max_cost=projected - 1e-9, pricing=PRICING).before_model(run, [MESSAGE])
    assert isinstance(stop, Stop)
    assert "cost ceiling" in stop.reason


def test_a_budget_needs_at_least_one_limit() -> None:
    with pytest.raises(ValueError, match="max_tokens, max_cost or both"):
        CostBudget()


def test_a_cost_ceiling_needs_a_price() -> None:
    with pytest.raises(ValueError, match="needs pricing"):
        CostBudget(max_cost=1.0)
