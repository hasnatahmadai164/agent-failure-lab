import json
from collections.abc import Mapping
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from agent_failure_lab.sim.clock import Clock


class EventKind(str, Enum):
    MODEL = "model"
    TOOL_CALL = "tool_call"
    TOOL_RESULT = "tool_result"
    GUARD = "guard"
    STOP = "stop"


@dataclass(frozen=True, slots=True)
class TraceEvent:
    step: int
    at: float
    kind: EventKind
    summary: str
    data: Mapping[str, Any] = field(default_factory=dict)


class Trace:
    """Ordered record of everything that happened in a run, stamped by the run's clock."""

    def __init__(self, clock: Clock) -> None:
        self._clock = clock
        self._events: list[TraceEvent] = []

    @property
    def events(self) -> tuple[TraceEvent, ...]:
        return tuple(self._events)

    def record(
        self,
        step: int,
        kind: EventKind,
        summary: str,
        data: Mapping[str, Any] | None = None,
    ) -> TraceEvent:
        event = TraceEvent(step, self._clock.now(), kind, summary, dict(data or {}))
        self._events.append(event)
        return event

    def of_kind(self, kind: EventKind) -> list[TraceEvent]:
        return [event for event in self._events if event.kind is kind]

    def render(self) -> str:
        return "\n".join(
            f"{event.step:>3} {event.at:>8.1f}s {event.kind.value:<11} {event.summary}"
            for event in self._events
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "events": [
                {
                    "step": event.step,
                    "at": event.at,
                    "kind": event.kind.value,
                    "summary": event.summary,
                    "data": dict(event.data),
                }
                for event in self._events
            ]
        }

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), indent=2)
