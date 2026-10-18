from agent_failure_lab.failures.infinite_tool_loop.world import play
from agent_failure_lab.scenario import Outcome, Variant


def run() -> Outcome:
    return play(Variant.BROKEN)
