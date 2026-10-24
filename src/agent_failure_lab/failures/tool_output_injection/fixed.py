from agent_failure_lab.failures.tool_output_injection.world import CUSTOMER, play
from agent_failure_lab.guards import CapabilityGate, ToolOutputQuarantine, allow_only
from agent_failure_lab.scenario import Outcome, Variant
from agent_failure_lab.sim import LanguageModel


def run(model: LanguageModel | None = None) -> Outcome:
    quarantine = ToolOutputQuarantine(["fetch_page"])
    gate = CapabilityGate({"send_email": allow_only("to", [CUSTOMER])}, quarantine=quarantine)
    return play(Variant.FIXED, guards=[quarantine, gate], model=model)
