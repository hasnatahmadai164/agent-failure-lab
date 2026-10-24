from agent_failure_lab.failures.hallucinated_tool_arguments.world import play
from agent_failure_lab.scenario import Outcome, Variant
from agent_failure_lab.sim import LanguageModel


def run(model: LanguageModel | None = None) -> Outcome:
    return play(Variant.BROKEN, model=model)
