from agent_failure_lab.failures.ambiguous_tool_selection.world import CLEAR_SPECS, play
from agent_failure_lab.guards import ToolDescriptionLinter
from agent_failure_lab.scenario import Outcome, Variant


def run() -> Outcome:
    return play(Variant.FIXED, specs=CLEAR_SPECS, guards=[ToolDescriptionLinter()])
