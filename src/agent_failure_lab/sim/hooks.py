from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Any

from agent_failure_lab.sim.clock import Clock
from agent_failure_lab.sim.llm import ModelTurn, Usage
from agent_failure_lab.sim.messages import Message, ToolCall
from agent_failure_lab.sim.tools import ToolResult, ToolSpec
from agent_failure_lab.sim.trace import EventKind, Trace


@dataclass(frozen=True, slots=True)
class Stop:
    """Returned by a guard to end the run immediately."""

    reason: str


@dataclass(frozen=True, slots=True)
class Block:
    """Returned by before_tool to skip the tool and use this result in its place."""

    result: ToolResult


class RunState:
    """What guards can see and do during one run.

    history is read-only: guards change what the model sees through before_model, not by
    editing the record. tool_timeout may be set by a guard to cap the tool calls that follow.
    """

    def __init__(
        self,
        *,
        clock: Clock,
        trace: Trace,
        tool_specs: Sequence[ToolSpec],
        history: Sequence[Message],
        tool_timeout: float | None = None,
    ) -> None:
        self.clock = clock
        self.trace = trace
        self.tool_specs = tuple(tool_specs)
        self.tool_timeout = tool_timeout
        self.step = 0
        self.usage = Usage()
        self.started_at = clock.now()
        self._history = list(history)

    @property
    def history(self) -> tuple[Message, ...]:
        return tuple(self._history)

    def append(self, message: Message) -> None:
        self._history.append(message)

    def elapsed(self) -> float:
        return self.clock.now() - self.started_at

    def intervene(self, guard: str, summary: str, data: Mapping[str, Any] | None = None) -> None:
        """Record that a guard changed what the agent did. Every guard action calls this."""
        payload = {"guard": guard, **(data or {})}
        self.trace.record(self.step, EventKind.GUARD, f"{guard}: {summary}", payload)


class Guard:
    """Base class for guards. Override only the hooks you need; each defaults to doing nothing.

    A hook returns None to leave things alone. Returning a replacement value changes what
    happens next, and returning Stop ends the run. Guards run in the order they were given.
    """

    @property
    def name(self) -> str:
        return type(self).__name__

    def before_model(
        self, run: RunState, messages: Sequence[Message]
    ) -> Sequence[Message] | Stop | None:
        return None

    def after_model(self, run: RunState, turn: ModelTurn) -> ModelTurn | Stop | None:
        return None

    def before_tool(self, run: RunState, call: ToolCall) -> ToolCall | Block | Stop | None:
        return None

    def after_tool(
        self, run: RunState, call: ToolCall, result: ToolResult
    ) -> ToolResult | Stop | None:
        return None

    def on_step_end(self, run: RunState) -> Stop | None:
        return None
