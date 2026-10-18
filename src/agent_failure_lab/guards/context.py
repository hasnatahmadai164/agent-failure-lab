from collections.abc import Sequence

from agent_failure_lab.sim import (
    Guard,
    Message,
    Role,
    RunState,
    Stop,
    estimate_message_tokens,
    system_message,
)


class ContextBudget(Guard):
    """Keeps the request within max_tokens without silently losing instructions.

    System messages are pinned and always sent. The oldest other messages are dropped first,
    a note tells the model that earlier messages were omitted, and the trace records how many
    went. If the pinned messages or the newest message alone do not fit, the run stops
    instead of sending a request that has lost something important.
    """

    def __init__(self, max_tokens: int) -> None:
        if max_tokens < 1:
            raise ValueError("max_tokens must be at least 1")
        self._max_tokens = max_tokens

    def before_model(
        self, run: RunState, messages: Sequence[Message]
    ) -> Sequence[Message] | Stop | None:
        total = _tokens(messages)
        if total <= self._max_tokens:
            return None
        pinned = [m for m in messages if m.role is Role.SYSTEM]
        rest = [m for m in messages if m.role is not Role.SYSTEM]
        reserved = _tokens([*pinned, system_message(_omission_note(len(rest)))])
        if reserved >= self._max_tokens:
            return self._refuse(
                run, f"pinned messages need {reserved} of {self._max_tokens} tokens"
            )
        kept = _newest_that_fit(rest, self._max_tokens - reserved)
        if not kept:
            return self._refuse(run, "the newest message does not fit in the budget")
        dropped = len(rest) - len(kept)
        run.intervene(
            self.name,
            f"dropped {dropped} oldest messages to fit {total} tokens into {self._max_tokens}",
            {"dropped": dropped, "tokens_before": total},
        )
        return [*pinned, system_message(_omission_note(dropped)), *kept]

    def _refuse(self, run: RunState, reason: str) -> Stop:
        run.intervene(self.name, f"stopped the run: {reason}")
        return Stop(f"context budget: {reason}")


def _tokens(messages: Sequence[Message]) -> int:
    return sum(estimate_message_tokens(message) for message in messages)


def _omission_note(count: int) -> str:
    return f"Note: {count} earlier messages were omitted to fit the context window."


def _newest_that_fit(messages: Sequence[Message], budget: int) -> list[Message]:
    kept: list[Message] = []
    used = 0
    for message in reversed(messages):
        cost = estimate_message_tokens(message)
        if used + cost > budget:
            break
        kept.append(message)
        used += cost
    kept.reverse()
    while kept and kept[0].role is Role.TOOL:
        kept.pop(0)
    return kept
