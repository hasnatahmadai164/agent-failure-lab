from collections.abc import Callable, Sequence
from dataclasses import replace

from agent_failure_lab.sim import Guard, Message, ModelTurn, Role, RunState

Postcondition = Callable[[Sequence[Message]], str | None]


def tool_succeeded(tool_name: str) -> Postcondition:
    """Require that the latest result from the tool exists and is not an error."""

    def check(history: Sequence[Message]) -> str | None:
        results = [m for m in history if m.role is Role.TOOL and m.name == tool_name]
        if not results:
            return f"{tool_name} was never called"
        if results[-1].is_error:
            return f"the last call to {tool_name} failed: {results[-1].content}"
        return None

    return check


class PostconditionCheck(Guard):
    """Checks evidence in the conversation before a final answer is accepted.

    Each condition looks at the history and returns a problem, or None when it holds. If any
    fails, the answer is replaced with a plain statement of what could not be confirmed.
    It replaces any final answer when a condition fails, even an honest one, so keep the
    conditions narrow and tied to the outcome that was promised.
    """

    def __init__(self, conditions: Sequence[Postcondition]) -> None:
        self._conditions = tuple(conditions)

    def after_model(self, run: RunState, turn: ModelTurn) -> ModelTurn | None:
        if turn.message.tool_calls:
            return None
        problems = [p for condition in self._conditions if (p := condition(run.history))]
        if not problems:
            return None
        detail = "; ".join(problems)
        run.intervene(self.name, f"replaced an unsupported answer: {detail}")
        corrected = replace(
            turn.message, content=f"I could not confirm that this was completed: {detail}."
        )
        return ModelTurn(corrected, turn.usage)
