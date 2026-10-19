from agent_failure_lab.failures.silent_context_truncation.world import (
    CONTEXT_TOKENS,
    NaiveWindow,
    play,
)
from agent_failure_lab.scenario import Outcome, Variant


def run() -> Outcome:
    return play(Variant.BROKEN, guards=[NaiveWindow(CONTEXT_TOKENS)])
