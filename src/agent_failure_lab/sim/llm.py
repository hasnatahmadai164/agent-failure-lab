from collections.abc import Callable, Sequence
from dataclasses import dataclass, replace
from typing import Protocol

from agent_failure_lab.errors import ScriptExhaustedError
from agent_failure_lab.sim.messages import (
    Message,
    Role,
    ToolCall,
    estimate_message_tokens,
)
from agent_failure_lab.sim.tools import ToolSpec


@dataclass(frozen=True, slots=True)
class Usage:
    prompt_tokens: int = 0
    completion_tokens: int = 0

    @property
    def total_tokens(self) -> int:
        return self.prompt_tokens + self.completion_tokens

    def __add__(self, other: "Usage") -> "Usage":
        return Usage(
            self.prompt_tokens + other.prompt_tokens,
            self.completion_tokens + other.completion_tokens,
        )


@dataclass(frozen=True, slots=True)
class ModelTurn:
    message: Message
    usage: Usage


class LanguageModel(Protocol):
    def generate(self, messages: Sequence[Message], tools: Sequence[ToolSpec]) -> ModelTurn: ...


@dataclass(frozen=True, slots=True)
class Reply:
    """One scripted assistant turn: text, tool calls, or both."""

    content: str = ""
    tool_calls: tuple[ToolCall, ...] = ()


ScriptStep = Reply | Callable[[Sequence[Message]], Reply]


class ScriptedLLM:
    """A model that plays back a fixed script, so a scenario misbehaves identically every run.

    A step is either a Reply or a function that picks a Reply from the conversation so far.
    Tool calls without an id get call_1, call_2, ... in the order they are issued.
    With repeat_last, the final step is reused once the script runs out.
    """

    def __init__(self, steps: Sequence[ScriptStep], *, repeat_last: bool = False) -> None:
        self._steps = tuple(steps)
        self._repeat_last = repeat_last
        self._turns = 0
        self._issued_calls = 0

    @property
    def turns_taken(self) -> int:
        return self._turns

    def generate(self, messages: Sequence[Message], tools: Sequence[ToolSpec]) -> ModelTurn:
        step = self._next_step()
        reply = step if isinstance(step, Reply) else step(messages)
        message = Message(
            Role.ASSISTANT,
            reply.content,
            tool_calls=tuple(self._with_id(call) for call in reply.tool_calls),
        )
        usage = Usage(
            prompt_tokens=sum(estimate_message_tokens(m) for m in messages),
            completion_tokens=estimate_message_tokens(message),
        )
        return ModelTurn(message, usage)

    def _next_step(self) -> ScriptStep:
        if self._turns < len(self._steps):
            step = self._steps[self._turns]
        elif self._repeat_last and self._steps:
            step = self._steps[-1]
        else:
            raise ScriptExhaustedError(self._turns)
        self._turns += 1
        return step

    def _with_id(self, call: ToolCall) -> ToolCall:
        if call.id:
            return call
        self._issued_calls += 1
        return replace(call, id=f"call_{self._issued_calls}")
