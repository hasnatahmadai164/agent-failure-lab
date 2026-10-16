import json
from collections.abc import Mapping
from dataclasses import dataclass
from enum import Enum
from typing import Any

CHARACTERS_PER_TOKEN = 4
MESSAGE_OVERHEAD_TOKENS = 4


class Role(str, Enum):
    SYSTEM = "system"
    USER = "user"
    ASSISTANT = "assistant"
    TOOL = "tool"


@dataclass(frozen=True, slots=True)
class ToolCall:
    """A request from the model to run a tool. An empty id is filled in by the model."""

    name: str
    arguments: Mapping[str, Any]
    id: str = ""


@dataclass(frozen=True, slots=True)
class Message:
    role: Role
    content: str = ""
    tool_calls: tuple[ToolCall, ...] = ()
    tool_call_id: str | None = None
    name: str | None = None
    is_error: bool = False


def system_message(content: str) -> Message:
    return Message(Role.SYSTEM, content)


def user_message(content: str) -> Message:
    return Message(Role.USER, content)


def tool_message(call: ToolCall, content: str, *, is_error: bool = False) -> Message:
    return Message(Role.TOOL, content, tool_call_id=call.id, name=call.name, is_error=is_error)


def estimate_tokens(text: str) -> int:
    """Approximate token count: one token per four characters, rounded up.

    Real tokenisers differ. A fixed rule keeps every run identical on every machine.
    """
    return (len(text) + CHARACTERS_PER_TOKEN - 1) // CHARACTERS_PER_TOKEN


def estimate_message_tokens(message: Message) -> int:
    tokens = MESSAGE_OVERHEAD_TOKENS + estimate_tokens(message.content)
    for call in message.tool_calls:
        arguments = json.dumps(dict(call.arguments), sort_keys=True)
        tokens += estimate_tokens(call.name) + estimate_tokens(arguments)
    return tokens
