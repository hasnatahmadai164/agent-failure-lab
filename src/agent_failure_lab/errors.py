class AflabError(Exception):
    """Base class for every error raised by agent_failure_lab."""


class UnknownScenarioError(AflabError):
    def __init__(self, slug: str) -> None:
        super().__init__(f"No failure is registered under the slug '{slug}'")
        self.slug = slug


class DuplicateScenarioError(AflabError):
    def __init__(self, slug: str) -> None:
        super().__init__(f"A failure is already registered under the slug '{slug}'")
        self.slug = slug
