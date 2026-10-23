from collections.abc import Callable, Mapping
from dataclasses import dataclass, field
from enum import Enum
from typing import Protocol

from agent_failure_lab.errors import LiveNotSupportedError
from agent_failure_lab.sim import LanguageModel
from agent_failure_lab.sim.trace import Trace

MetricValue = int | float | bool | str

CATEGORIES = ("side-effects", "control-flow", "security", "tool-use", "context-and-cost")


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
    def fix(self) -> str: ...

    @property
    def guards(self) -> tuple[str, ...]: ...

    @property
    def supports_live(self) -> bool: ...

    def run(self, variant: Variant) -> Outcome: ...

    def run_live(self, variant: Variant, model: LanguageModel) -> Outcome: ...


@dataclass(frozen=True, slots=True)
class ScenarioDefinition:
    """The standard Scenario: metadata plus one function per variant.

    The live functions take the model to run against. A failure that can be tried on a real
    model provides both, and a failure without them runs only with the scripted model.
    """

    slug: str
    title: str
    category: str
    summary: str
    broken: Callable[[], Outcome]
    fixed: Callable[[], Outcome]
    fix: str = ""
    guards: tuple[str, ...] = ()
    broken_live: Callable[[LanguageModel], Outcome] | None = None
    fixed_live: Callable[[LanguageModel], Outcome] | None = None

    @property
    def supports_live(self) -> bool:
        return self.broken_live is not None and self.fixed_live is not None

    def run(self, variant: Variant) -> Outcome:
        return self.broken() if variant is Variant.BROKEN else self.fixed()

    def run_live(self, variant: Variant, model: LanguageModel) -> Outcome:
        live = self.broken_live if variant is Variant.BROKEN else self.fixed_live
        if live is None:
            raise LiveNotSupportedError(self.slug)
        return live(model)
