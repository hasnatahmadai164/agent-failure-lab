from dataclasses import dataclass

from agent_failure_lab.errors import DuplicateScenarioError, UnknownScenarioError


@dataclass(frozen=True, slots=True)
class ScenarioInfo:
    slug: str
    title: str
    category: str
    summary: str


class ScenarioRegistry:
    def __init__(self) -> None:
        self._by_slug: dict[str, ScenarioInfo] = {}

    def register(self, info: ScenarioInfo) -> None:
        if info.slug in self._by_slug:
            raise DuplicateScenarioError(info.slug)
        self._by_slug[info.slug] = info

    def get(self, slug: str) -> ScenarioInfo:
        try:
            return self._by_slug[slug]
        except KeyError:
            raise UnknownScenarioError(slug) from None

    def scenarios(self) -> list[ScenarioInfo]:
        return list(self._by_slug.values())


def build_registry() -> ScenarioRegistry:
    return ScenarioRegistry()
