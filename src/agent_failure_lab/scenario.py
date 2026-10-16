from collections.abc import Callable, Mapping
from dataclasses import dataclass, field
from enum import Enum
from typing import Protocol

from agent_failure_lab.sim.trace import Trace

MetricValue = int | float | bool | str


class Variant(str, Enum):
    BROKEN = "broken"
    FIXED = "fixed"


@dataclass(frozen=True, slots=True)
class Outcome:
    """What one run of one variant produced.

    failure_observed is the scenario's own verdict: True when the failure happened in this run.
    """

    variant: Variant
    failure_observed: bool
    trace: Trace
    metrics: Mapping[str, MetricValue] = field(default_factory=dict)
    findings: tuple[str, ...] = ()


class Scenario(Protocol):
    @property
    def slug(self) -> str: ...

    @property
    def title(self) -> str: ...

    @property
    def category(self) -> str: ...

    @property
    def summary(self) -> str: ...

    @property
    def supports_live(self) -> bool: ...

    def run(self, variant: Variant) -> Outcome: ...


@dataclass(frozen=True, slots=True)
class ScenarioDefinition:
    """The standard Scenario: metadata plus one function per variant."""

    slug: str
    title: str
    category: str
    summary: str
    broken: Callable[[], Outcome]
    fixed: Callable[[], Outcome]
    supports_live: bool = False

    def run(self, variant: Variant) -> Outcome:
        return self.broken() if variant is Variant.BROKEN else self.fixed()
