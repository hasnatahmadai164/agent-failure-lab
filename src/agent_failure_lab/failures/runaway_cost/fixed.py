from agent_failure_lab.failures.runaway_cost.world import (
    COMPLETION_RESERVE,
    COST_CEILING,
    PRICING,
    play,
)
from agent_failure_lab.guards import CostBudget
from agent_failure_lab.scenario import Outcome, Variant


def run() -> Outcome:
    budget = CostBudget(
        max_cost=COST_CEILING,
        pricing=PRICING,
        completion_reserve=COMPLETION_RESERVE,
    )
    return play(Variant.FIXED, guards=[budget])
