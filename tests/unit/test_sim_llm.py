from collections.abc import Sequence

import pytest

from agent_failure_lab.errors import ScriptExhaustedError
from agent_failure_lab.sim import (
    Message,
    Reply,
    Role,
    ScriptedLLM,
    ToolCall,
    Usage,
    user_message,
)


def test_replies_come_back_in_script_order() -> None:
    llm = ScriptedLLM([Reply("first"), Reply("second")])

    first = llm.generate([user_message("hi")], [])
    second = llm.generate([user_message("hi")], [])

    assert [first.message.content, second.message.content] == ["first", "second"]
    assert first.message.role is Role.ASSISTANT
    assert llm.turns_taken == 2


def test_tool_calls_without_an_id_get_sequential_ids() -> None:
    llm = ScriptedLLM(
        [
            Reply(tool_calls=(ToolCall("a", {}), ToolCall("b", {}))),
            Reply(tool_calls=(ToolCall("c", {}),)),
        ]
    )

    first = llm.generate([], [])
    second = llm.generate([], [])

    assert [call.id for call in first.message.tool_calls] == ["call_1", "call_2"]
    assert [call.id for call in second.message.tool_calls] == ["call_3"]


def test_tool_calls_that_already_have_an_id_keep_it() -> None:
    llm = ScriptedLLM([Reply(tool_calls=(ToolCall("a", {}, id="mine"),))])

    turn = llm.generate([], [])

    assert turn.message.tool_calls[0].id == "mine"


def test_a_function_step_chooses_its_reply_from_the_conversation() -> None:
    def choose(messages: Sequence[Message]) -> Reply:
        mentioned = any("urgent" in message.content for message in messages)
        return Reply("escalate" if mentioned else "routine")

    llm = ScriptedLLM([choose, choose])

    calm = llm.generate([user_message("hello")], [])
    urgent = llm.generate([user_message("this is urgent")], [])

    assert [calm.message.content, urgent.message.content] == ["routine", "escalate"]


def test_running_out_of_script_raises() -> None:
    llm = ScriptedLLM([Reply("only")])
    llm.generate([], [])

    with pytest.raises(ScriptExhaustedError, match="after 1 turns"):
        llm.generate([], [])


def test_repeat_last_reuses_the_final_step() -> None:
    llm = ScriptedLLM([Reply("first"), Reply("again")], repeat_last=True)

    contents = [llm.generate([], []).message.content for _ in range(4)]

    assert contents == ["first", "again", "again", "again"]


def test_repeat_last_with_an_empty_script_still_raises() -> None:
    with pytest.raises(ScriptExhaustedError):
        ScriptedLLM([], repeat_last=True).generate([], [])


def test_prompt_tokens_grow_with_the_conversation() -> None:
    llm = ScriptedLLM([Reply("a"), Reply("b")])
    short = [user_message("hi")]
    long = [user_message("hi"), user_message("a much longer follow up message " * 5)]

    first = llm.generate(short, [])
    second = llm.generate(long, [])

    assert second.usage.prompt_tokens > first.usage.prompt_tokens
    assert first.usage.completion_tokens > 0


def test_usage_adds_field_by_field() -> None:
    total = Usage(10, 4) + Usage(1, 2)

    assert total == Usage(11, 6)
    assert total.total_tokens == 17
