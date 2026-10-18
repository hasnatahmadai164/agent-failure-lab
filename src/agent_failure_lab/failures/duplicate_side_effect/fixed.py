from agent_failure_lab.failures.duplicate_side_effect.world import play
from agent_failure_lab.guards import IdempotencyKeys, IdempotencyStore
from agent_failure_lab.scenario import Outcome, Variant


def run() -> Outcome:
    store = IdempotencyStore()
    guards = [IdempotencyKeys(key_fields=["order_id"])]
    return play(Variant.FIXED, guards=guards, store=store)
