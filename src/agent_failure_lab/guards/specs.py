from agent_failure_lab.sim import RunState


def has_side_effects(run: RunState, tool_name: str) -> bool:
    """True when the named tool declares that a call changes something in the world."""
    return any(spec.name == tool_name and spec.side_effects for spec in run.tool_specs)
