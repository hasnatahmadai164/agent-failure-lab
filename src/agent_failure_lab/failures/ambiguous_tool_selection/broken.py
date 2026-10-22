from agent_failure_lab.failures.ambiguous_tool_selection.world import AMBIGUOUS_SPECS, play
from agent_failure_lab.scenario import Outcome, Variant


def run() -> Outcome:
    return play(Variant.BROKEN, specs=AMBIGUOUS_SPECS)
