import importlib
import json
import os
from collections.abc import Callable, Mapping, Sequence
from types import ModuleType
from typing import Any

from agent_failure_lab.errors import LiveModeUnavailableError, LiveRequestError
from agent_failure_lab.sim import (
    LanguageModel,
    Message,
    ModelTurn,
    Role,
    ToolCall,
    ToolSpec,
    Usage,
)

DEFAULT_MODEL = "gpt-4o-mini"


def create_client(
    *,
    environ: Mapping[str, str] | None = None,
    import_module: Callable[[str], ModuleType] = importlib.import_module,
) -> Any:
    """Build an OpenAI client, or explain what is missing.

    The openai package is optional, so it is imported here and not at the top of the module.
    """
    try:
        openai = import_module("openai")
    except ImportError as error:
        raise LiveModeUnavailableError(
            "The openai package is not installed. "
            'Install it with: pip install "agent-failure-lab[live]"'
        ) from error
    key = (os.environ if environ is None else environ).get("OPENAI_API_KEY")
    if not key:
        raise LiveModeUnavailableError(
            "OPENAI_API_KEY is not set. Set it in your environment to use live mode."
        )
    return openai.OpenAI(api_key=key)


def create_openai_model(model_name: str) -> LanguageModel:
    return OpenAIChatModel(create_client(), model_name)


def to_openai_messages(messages: Sequence[Message]) -> list[dict[str, Any]]:
    converted: list[dict[str, Any]] = []
    for message in messages:
        if message.role is Role.TOOL:
            converted.append(
                {"role": "tool", "tool_call_id": message.tool_call_id, "content": message.content}
            )
        elif message.tool_calls:
            converted.append(
                {
                    "role": "assistant",
                    "content": message.content or None,
                    "tool_calls": [_to_openai_call(call) for call in message.tool_calls],
                }
            )
        else:
            converted.append({"role": message.role.value, "content": message.content})
    return converted


def to_openai_tools(tools: Sequence[ToolSpec]) -> list[dict[str, Any]]:
    return [
        {
            "type": "function",
            "function": {
                "name": spec.name,
                "description": spec.description,
                "parameters": dict(spec.parameters),
            },
        }
        for spec in tools
    ]


def _to_openai_call(call: ToolCall) -> dict[str, Any]:
    return {
        "id": call.id,
        "type": "function",
        "function": {"name": call.name, "arguments": json.dumps(dict(call.arguments))},
    }


def _parse_call(raw: Any) -> ToolCall:
    try:
        arguments = json.loads(raw.function.arguments or "{}")
    except json.JSONDecodeError:
        arguments = {"_invalid_arguments": raw.function.arguments}
    if not isinstance(arguments, dict):
        arguments = {"_invalid_arguments": raw.function.arguments}
    return ToolCall(raw.function.name, arguments, id=raw.id)


class OpenAIChatModel:
    """A language model backed by the OpenAI chat completions API.

    The client is passed in, so tests can use a fake and nothing here touches the network
    until a real client is given.
    """

    def __init__(self, client: Any, model: str) -> None:
        self._client = client
        self._model = model

    def generate(self, messages: Sequence[Message], tools: Sequence[ToolSpec]) -> ModelTurn:
        request: dict[str, Any] = {
            "model": self._model,
            "messages": to_openai_messages(messages),
        }
        if tools:
            request["tools"] = to_openai_tools(tools)
        try:
            response = self._client.chat.completions.create(**request)
        except Exception as error:  # the openai package raises many unrelated types
            raise LiveRequestError(f"The request to {self._model} failed: {error}") from error
        message = response.choices[0].message
        calls = tuple(_parse_call(raw) for raw in (message.tool_calls or ()))
        usage = response.usage
        return ModelTurn(
            Message(Role.ASSISTANT, message.content or "", tool_calls=calls),
            Usage(usage.prompt_tokens, usage.completion_tokens) if usage else Usage(),
        )
