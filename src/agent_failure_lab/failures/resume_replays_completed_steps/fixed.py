from agent_failure_lab.failures.resume_replays_completed_steps.world import play
from agent_failure_lab.guards import Journal
from agent_failure_lab.scenario import Outcome, Variant


def run() -> Outcome:
    return play(Variant.FIXED, journal=Journal())
