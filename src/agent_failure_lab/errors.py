class AflabError(Exception):
    """Base class for every error raised by agent_failure_lab."""


class UnknownScenarioError(AflabError):
    def __init__(self, slug: str) -> None:
        super().__init__(f"No failure is registered under the slug '{slug}'. Run 'aflab list'.")
        self.slug = slug


class DuplicateScenarioError(AflabError):
    def __init__(self, slug: str) -> None:
        super().__init__(f"A failure is already registered under the slug '{slug}'")
        self.slug = slug


class InvalidSlugError(AflabError):
    def __init__(self, slug: str) -> None:
        super().__init__(
            f"'{slug}' is not a valid slug: use lowercase words separated by single hyphens"
        )
        self.slug = slug


class ScenarioContractError(AflabError):
    """A scenario returned an outcome that does not match what was asked of it."""


class LiveNotSupportedError(AflabError):
    def __init__(self, slug: str) -> None:
        super().__init__(
            f"'{slug}' has no live variant, so it can only run with the scripted model"
        )
        self.slug = slug


class LiveModeUnavailableError(AflabError):
    """Live mode could not start, for example because a package or the API key is missing."""


class LiveRequestError(AflabError):
    """A request to the model provider failed during a live run."""


class ScaffoldError(AflabError):
    """A new failure could not be created."""


class CatalogError(AflabError):
    """The catalogue markers could not be found in a document."""


class ToolError(AflabError):
    """A tool call failed in a way the agent reports back to the model as an error result."""


class UnknownToolError(ToolError):
    def __init__(self, name: str) -> None:
        super().__init__(f"unknown tool '{name}'")
        self.name = name


class ToolExecutionError(ToolError):
    """Raised by a tool function, or by a scheduled failure, when a call does not succeed."""


class ToolTimeoutError(ToolError):
    def __init__(self, name: str, seconds: float) -> None:
        super().__init__(f"tool '{name}' timed out after {seconds:g}s")
        self.name = name
        self.seconds = seconds


class DuplicateToolError(AflabError):
    def __init__(self, name: str) -> None:
        super().__init__(f"A tool named '{name}' is already registered")
        self.name = name


class ScriptExhaustedError(AflabError):
    def __init__(self, turns: int) -> None:
        super().__init__(f"The scripted model has no reply left after {turns} turns")
        self.turns = turns
