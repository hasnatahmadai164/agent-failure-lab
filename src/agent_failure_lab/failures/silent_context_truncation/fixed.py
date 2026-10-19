from agent_failure_lab.failures.silent_context_truncation.world import CONTEXT_TOKENS, play
from agent_failure_lab.guards import ContextBudget
from agent_failure_lab.scenario import Outcome, Variant


def run() -> Outcome:
    return play(Variant.FIXED, guards=[ContextBudget(CONTEXT_TOKENS)])
