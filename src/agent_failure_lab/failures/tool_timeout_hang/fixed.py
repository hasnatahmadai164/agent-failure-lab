from agent_failure_lab.failures.tool_timeout_hang.world import play
from agent_failure_lab.guards import Deadline
from agent_failure_lab.scenario import Outcome, Variant


def run() -> Outcome:
    return play(Variant.FIXED, guards=[Deadline(per_call=5, total=20)])
