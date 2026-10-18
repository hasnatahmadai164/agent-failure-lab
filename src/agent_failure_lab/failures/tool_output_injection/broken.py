from agent_failure_lab.failures.tool_output_injection.world import play
from agent_failure_lab.scenario import Outcome, Variant


def run() -> Outcome:
    return play(Variant.BROKEN)
