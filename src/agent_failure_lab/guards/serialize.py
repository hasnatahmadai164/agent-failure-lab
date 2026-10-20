from collections.abc import Collection

from agent_failure_lab.guards.signature import canonical_arguments
from agent_failure_lab.guards.specs import has_side_effects
from agent_failure_lab.sim import Block, Guard, Role, RunState, ToolCall, ToolResult


class ConflictSerializer(Guard):
    """Lets only one side-effecting call per resource run in each model turn.

    When a model asks for several calls at once, calls that change the same resource (the
    same values for key_fields) can race if the tools run concurrently. Later ones are held
    back with a message asking the model to repeat them in its next step, so they run one
    after another. Calls that only read are never held back.
    """

    def __init__(self, key_fields: Collection[str]) -> None:
        if not key_fields:
            raise ValueError("key_fields cannot be empty")
        self._key_fields = tuple(key_fields)

    def before_tool(self, run: RunState, call: ToolCall) -> Block | None:
        key = self._resource(call)
        if key is None or not has_side_effects(run, call.name):
            return None
        turn = _calls_in_turn(run, call)
        position = next((i for i, other in enumerate(turn) if other.id == call.id), len(turn))
        for earlier in turn[:position]:
            if has_side_effects(run, earlier.name) and self._resource(earlier) == key:
                run.intervene(
                    self.name, f"held back {call.name}: {earlier.name} is already changing {key}"
                )
                return Block(
                    ToolResult(
                        f"Not run: {earlier.name} in this same step is already changing the "
                        "same resource, and running both at once could lose one of the "
                        "changes. Repeat this call in your next step.",
                        is_error=True,
                    )
                )
        return None

    def _resource(self, call: ToolCall) -> str | None:
        identifying = {f: call.arguments[f] for f in self._key_fields if f in call.arguments}
        return canonical_arguments(identifying) if identifying else None


def _calls_in_turn(run: RunState, call: ToolCall) -> tuple[ToolCall, ...]:
    for message in reversed(run.history):
        if message.role is Role.ASSISTANT and any(c.id == call.id for c in message.tool_calls):
            return message.tool_calls
    return (call,)
