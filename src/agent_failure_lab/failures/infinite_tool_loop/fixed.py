from agent_failure_lab.failures.infinite_tool_loop.world import play
from agent_failure_lab.guards import LoopDetector, StepBudget
from agent_failure_lab.scenario import Outcome, Variant


def run() -> Outcome:
    guards = [LoopDetector(max_repeats=3, max_warnings=1), StepBudget(10)]
    return play(Variant.FIXED, guards=guards)
