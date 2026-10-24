from agent_failure_lab.failures.tool_output_injection.world import play
from agent_failure_lab.scenario import Outcome, Variant
from agent_failure_lab.sim import LanguageModel


def run(model: LanguageModel | None = None) -> Outcome:
    return play(Variant.BROKEN, model=model)
