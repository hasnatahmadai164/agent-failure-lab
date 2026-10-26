from types import ModuleType, SimpleNamespace
from typing import Any

import pytest

from agent_failure_lab.errors import LiveModeUnavailableError, LiveRequestError
from agent_failure_lab.live import (
    OpenAIChatModel,
    create_client,
    to_openai_messages,
    to_openai_tools,
)
from agent_failure_lab.sim import (
    Message,
    Role,
    ToolCall,
    ToolSpec,
    system_message,
    tool_message,
    user_message,
)
from fakes import FakeChatClient, raw_call, reply

SPEC = ToolSpec(
    "charge_card",
    "Charge the card.",
    {"type": "object", "properties": {"order_id": {"type": "string"}}},
)


def test_plain_messages_keep_their_role_and_text() -> None:
    converted = to_openai_messages([system_message("rules"), user_message("hello")])

    assert converted == [
        {"role": "system", "content": "rules"},
        {"role": "user", "content": "hello"},
    ]


def test_an_assistant_turn_with_tool_calls_becomes_a_function_call_request() -> None:
    call = ToolCall("charge_card", {"order_id": "A-1"}, id="call_1")

    (converted,) = to_openai_messages([Message(Role.ASSISTANT, tool_calls=(call,))])

    assert converted["content"] is None
    assert converted["tool_calls"] == [
        {
            "id": "call_1",
            "type": "function",
            "function": {"name": "charge_card", "arguments": '{"order_id": "A-1"}'},
        }
    ]


def test_a_tool_result_is_sent_back_with_the_id_of_its_call() -> None:
    call = ToolCall("charge_card", {}, id="call_1")

    (converted,) = to_openai_messages([tool_message(call, "charged", is_error=False)])

    assert converted == {"role": "tool", "tool_call_id": "call_1", "content": "charged"}


def test_tool_specs_become_function_tools() -> None:
    (tool,) = to_openai_tools([SPEC])

    assert tool["type"] == "function"
    assert tool["function"]["name"] == "charge_card"
    assert tool["function"]["description"] == "Charge the card."
    assert tool["function"]["parameters"]["properties"] == {"order_id": {"type": "string"}}


def test_a_text_reply_is_returned_with_its_token_usage() -> None:
    model = OpenAIChatModel(FakeChatClient([reply("All done.")]), "gpt-test")

    turn = model.generate([user_message("hi")], [])

    assert turn.message.role is Role.ASSISTANT
    assert turn.message.content == "All done."
    assert turn.message.tool_calls == ()
    assert (turn.usage.prompt_tokens, turn.usage.completion_tokens) == (10, 5)


def test_tool_calls_keep_the_ids_and_arguments_the_model_gave() -> None:
    raw = raw_call("call_9", "charge_card", '{"order_id": "A-1", "amount": 49}')
    model = OpenAIChatModel(FakeChatClient([reply(calls=[raw])]), "gpt-test")

    turn = model.generate([user_message("hi")], [SPEC])

    (call,) = turn.message.tool_calls
    assert call.id == "call_9"
    assert call.name == "charge_card"
    assert call.arguments == {"order_id": "A-1", "amount": 49}


@pytest.mark.parametrize("arguments", ["not json at all", "[1, 2]"])
def test_arguments_that_are_not_a_json_object_are_kept_visible_for_the_tool_to_reject(
    arguments: str,
) -> None:
    raw = raw_call("call_1", "charge_card", arguments)
    model = OpenAIChatModel(FakeChatClient([reply(calls=[raw])]), "gpt-test")

    (call,) = model.generate([user_message("hi")], [SPEC]).message.tool_calls

    assert call.arguments == {"_invalid_arguments": arguments}


def test_the_request_names_the_model_and_offers_the_tools_only_when_there_are_some() -> None:
    client = FakeChatClient([reply("a"), reply("b")])
    model = OpenAIChatModel(client, "gpt-test")

    model.generate([user_message("hi")], [])
    model.generate([user_message("hi")], [SPEC])

    assert client.requests[0]["model"] == "gpt-test"
    assert "tools" not in client.requests[0]
    assert client.requests[1]["tools"][0]["function"]["name"] == "charge_card"


def test_a_reply_without_usage_figures_counts_as_zero() -> None:
    answer = reply("ok")
    answer.usage = None
    model = OpenAIChatModel(FakeChatClient([answer]), "gpt-test")

    assert model.generate([user_message("hi")], []).usage.total_tokens == 0


def test_a_failed_request_becomes_a_clear_error_that_names_the_model() -> None:
    class Broken:
        chat = SimpleNamespace(completions=SimpleNamespace(create=lambda **_: 1 / 0))

    model = OpenAIChatModel(Broken(), "gpt-test")

    with pytest.raises(LiveRequestError, match="gpt-test"):
        model.generate([user_message("hi")], [])


def _fake_openai(received: dict[str, Any]) -> ModuleType:
    module = ModuleType("openai")

    class OpenAI:
        def __init__(self, **kwargs: Any) -> None:
            received.update(kwargs)

    module.OpenAI = OpenAI  # type: ignore[attr-defined]
    return module


def test_a_client_is_built_with_the_key_from_the_environment() -> None:
    received: dict[str, Any] = {}

    client = create_client(
        environ={"OPENAI_API_KEY": "sk-test-value"},
        import_module=lambda name: _fake_openai(received),
    )

    assert received == {"api_key": "sk-test-value"}
    assert client is not None


def test_a_missing_key_is_reported_without_echoing_anything_secret() -> None:
    with pytest.raises(LiveModeUnavailableError, match="OPENAI_API_KEY is not set"):
        create_client(environ={}, import_module=lambda name: _fake_openai({}))


def test_a_missing_package_tells_the_user_how_to_install_it() -> None:
    def missing(name: str) -> ModuleType:
        raise ImportError(name)

    with pytest.raises(LiveModeUnavailableError, match=r"agent-failure-lab\[live\]"):
        create_client(environ={"OPENAI_API_KEY": "x"}, import_module=missing)
