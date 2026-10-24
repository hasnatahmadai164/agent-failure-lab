from agent_failure_lab.failures.tool_output_injection import broken, fixed
from agent_failure_lab.scenario import ScenarioDefinition

SCENARIO = ScenarioDefinition(
    slug="tool-output-injection",
    title="Instructions hidden in tool output",
    category="security",
    summary="Instructions hidden in a tool result hijack the next action",
    fix="Quarantine untrusted output and gate sensitive tools",
    guards=("ToolOutputQuarantine", "CapabilityGate"),
    broken=broken.run,
    fixed=fixed.run,
    broken_live=broken.run,
    fixed_live=fixed.run,
)
