import hashlib
from collections.abc import Callable, Collection
from dataclasses import replace

from agent_failure_lab.guards.signature import canonical_arguments
from agent_failure_lab.sim import Guard, RunState, ToolCall

KEY_ARGUMENT = "idempotency_key"


class IdempotencyStore:
    """Remembers each operation's result under its key, so a repeated key repeats the answer.

    It belongs on the side that performs the side effect. A failed attempt is not stored,
    so it can still be retried.
    """

    def __init__(self) -> None:
        self._results: dict[str, str] = {}
        self.replays = 0

    def execute(self, key: str, operation: Callable[[], str]) -> str:
        if key in self._results:
            self.replays += 1
            return self._results[key]
        result = operation()
        self._results[key] = result
        return result


class IdempotencyKeys(Guard):
    """Gives every attempt at the same side-effecting call the same idempotency key.

    key_fields names the arguments that identify the operation, for example the order id.
    By default all arguments count, which cannot tell a retry from an intentional repeat.
    """

    def __init__(self, key_fields: Collection[str] | None = None) -> None:
        self._key_fields = tuple(key_fields) if key_fields is not None else None

    def before_tool(self, run: RunState, call: ToolCall) -> ToolCall | None:
        if KEY_ARGUMENT in call.arguments or not _has_side_effects(run, call.name):
            return None
        key = self._key_for(call)
        run.intervene(self.name, f"attached key {key} to {call.name}", {"key": key})
        return replace(call, arguments={**call.arguments, KEY_ARGUMENT: key})

    def _key_for(self, call: ToolCall) -> str:
        fields = self._key_fields if self._key_fields is not None else tuple(call.arguments)
        identifying = {name: call.arguments[name] for name in fields if name in call.arguments}
        payload = f"{call.name}:{canonical_arguments(identifying)}"
        return hashlib.sha256(payload.encode()).hexdigest()[:16]


def _has_side_effects(run: RunState, tool_name: str) -> bool:
    return any(spec.name == tool_name and spec.side_effects for spec in run.tool_specs)
