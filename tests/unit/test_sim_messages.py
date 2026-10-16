import pytest

from agent_failure_lab.sim import (
    Message,
    Role,
    ToolCall,
    estimate_message_tokens,
    estimate_tokens,
    tool_message,
)
from agent_failure_lab.sim.messages import MESSAGE_OVERHEAD_TOKENS


@pytest.mark.parametrize(
    ("text", "expected"),
    [("", 0), ("a", 1), ("abcd", 1), ("abcde", 2), ("a" * 40, 10)],
)
def test_estimate_tokens_rounds_up_to_whole_tokens(text: str, expected: int) -> None:
    assert estimate_tokens(text) == expected


def test_message_estimate_includes_per_message_overhead() -> None:
    message = Message(Role.USER, "abcd")

    assert estimate_message_tokens(message) == MESSAGE_OVERHEAD_TOKENS + 1


def test_message_estimate_counts_tool_call_name_and_arguments() -> None:
    without_calls = Message(Role.ASSISTANT, "")
    with_call = Message(Role.ASSISTANT, "", tool_calls=(ToolCall("charge", {"amount": 10}),))

    assert estimate_message_tokens(with_call) > estimate_message_tokens(without_calls)


def test_message_estimate_is_the_same_whatever_the_argument_order() -> None:
    first = Message(Role.ASSISTANT, tool_calls=(ToolCall("t", {"a": 1, "b": 2}),))
    second = Message(Role.ASSISTANT, tool_calls=(ToolCall("t", {"b": 2, "a": 1}),))

    assert estimate_message_tokens(first) == estimate_message_tokens(second)


def test_tool_message_carries_the_call_id_name_and_error_flag() -> None:
    call = ToolCall("charge", {"amount": 10}, id="call_7")

    message = tool_message(call, "declined", is_error=True)

    assert message.role is Role.TOOL
    assert message.tool_call_id == "call_7"
    assert message.name == "charge"
    assert message.is_error
