from collections.abc import Callable, Iterable, Mapping, Sequence
from dataclasses import dataclass, field
from typing import Any

from agent_failure_lab.errors import (
    DuplicateToolError,
    ToolExecutionError,
    ToolTimeoutError,
    UnknownToolError,
)
from agent_failure_lab.sim.clock import Clock

ToolFn = Callable[[Mapping[str, Any]], str]


def _empty_schema() -> dict[str, Any]:
    return {"type": "object", "properties": {}}


@dataclass(frozen=True, slots=True)
class ToolSpec:
    """What the model sees about a tool. side_effects names what a call changes in the world."""

    name: str
    description: str
    parameters: Mapping[str, Any] = field(default_factory=_empty_schema)
    side_effects: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class ToolResult:
    content: str
    is_error: bool = False


@dataclass(frozen=True, slots=True)
class Fail:
    """Scheduled failure. With effects_applied, the tool does its work and then reports failure."""

    message: str
    effects_applied: bool = False


@dataclass(frozen=True, slots=True)
class Delay:
    """Scheduled slow response, taking this many seconds of clock time."""

    seconds: float


ScheduledOutcome = Fail | Delay | None


class Tool:
    """A callable tool whose Nth call can be scheduled to fail or respond slowly.

    schedule[0] applies to the first call, schedule[1] to the second, and so on.
    None, or running past the end of the schedule, means a normal call.
    """

    def __init__(
        self,
        spec: ToolSpec,
        fn: ToolFn,
        schedule: Sequence[ScheduledOutcome] = (),
    ) -> None:
        self._spec = spec
        self._fn = fn
        self._schedule = tuple(schedule)
        self._calls = 0

    @property
    def spec(self) -> ToolSpec:
        return self._spec

    @property
    def call_count(self) -> int:
        return self._calls

    def run(
        self,
        arguments: Mapping[str, Any],
        clock: Clock,
        *,
        timeout: float | None = None,
    ) -> str:
        self._calls += 1
        planned = self._planned()
        if isinstance(planned, Fail):
            self._fail(planned, arguments)
        if isinstance(planned, Delay):
            self._wait(planned.seconds, clock, timeout)
        return self._fn(arguments)

    def _planned(self) -> ScheduledOutcome:
        if self._calls <= len(self._schedule):
            return self._schedule[self._calls - 1]
        return None

    def _fail(self, planned: Fail, arguments: Mapping[str, Any]) -> None:
        if planned.effects_applied:
            self._fn(arguments)
        raise ToolExecutionError(planned.message)

    def _wait(self, seconds: float, clock: Clock, timeout: float | None) -> None:
        if timeout is not None and seconds > timeout:
            clock.sleep(timeout)
            raise ToolTimeoutError(self._spec.name, timeout)
        clock.sleep(seconds)


class ToolRegistry:
    def __init__(self, tools: Iterable[Tool] = ()) -> None:
        self._by_name: dict[str, Tool] = {}
        for tool in tools:
            self.add(tool)

    def add(self, tool: Tool) -> None:
        name = tool.spec.name
        if name in self._by_name:
            raise DuplicateToolError(name)
        self._by_name[name] = tool

    def get(self, name: str) -> Tool:
        try:
            return self._by_name[name]
        except KeyError:
            raise UnknownToolError(name) from None

    def specs(self) -> tuple[ToolSpec, ...]:
        return tuple(tool.spec for tool in self._by_name.values())
