from agent_failure_lab.failures.false_success_claim.world import play
from agent_failure_lab.guards import PostconditionCheck, tool_succeeded
from agent_failure_lab.scenario import Outcome, Variant


def run() -> Outcome:
    return play(Variant.FIXED, guards=[PostconditionCheck([tool_succeeded("update_inventory")])])
