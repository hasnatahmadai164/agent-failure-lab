from agent_failure_lab.failures.parallel_tool_race.world import play
from agent_failure_lab.guards import ConflictSerializer
from agent_failure_lab.scenario import Outcome, Variant


def run() -> Outcome:
    return play(Variant.FIXED, guards=[ConflictSerializer(["ticket_id"])])
