from agent_failure_lab.failures.hallucinated_tool_arguments.world import play
from agent_failure_lab.scenario import Outcome, Variant


def run() -> Outcome:
    return play(Variant.BROKEN)
