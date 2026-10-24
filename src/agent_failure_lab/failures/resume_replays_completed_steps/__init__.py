from agent_failure_lab.failures.resume_replays_completed_steps import broken, fixed
from agent_failure_lab.scenario import ScenarioDefinition

SCENARIO = ScenarioDefinition(
    slug="resume-replays-completed-steps",
    title="Resume replays completed steps",
    category="side-effects",
    summary="After a crash, the restarted agent repeats work that already finished",
    fix="A step journal for safe resume",
    guards=("StepJournal", "Journal"),
    broken=broken.run,
    fixed=fixed.run,
)
