from agent_failure_lab.failures.parallel_tool_race.world import play
from agent_failure_lab.guards import ConflictSerializer
from agent_failure_lab.scenario import Outcome, Variant
from agent_failure_lab.sim import LanguageModel


def run(model: LanguageModel | None = None) -> Outcome:
    return play(Variant.FIXED, guards=[ConflictSerializer(["ticket_id"])], model=model)
