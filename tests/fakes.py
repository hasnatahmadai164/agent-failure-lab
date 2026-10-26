"""Stand-ins for the OpenAI client, shaped like the objects the real package returns."""

from types import SimpleNamespace
from typing import Any


def usage(prompt: int = 10, completion: int = 5) -> SimpleNamespace:
    return SimpleNamespace(prompt_tokens=prompt, completion_tokens=completion)


def raw_call(call_id: str, name: str, arguments: str) -> SimpleNamespace:
    return SimpleNamespace(id=call_id, function=SimpleNamespace(name=name, arguments=arguments))


def reply(
    content: str | None = None, calls: list[SimpleNamespace] | None = None
) -> SimpleNamespace:
    message = SimpleNamespace(content=content, tool_calls=calls or None)
    return SimpleNamespace(choices=[SimpleNamespace(message=message)], usage=usage())


class FakeChatClient:
    """Hands back the prepared replies in order and records every request it was given."""

    def __init__(self, replies: list[SimpleNamespace]) -> None:
        self._replies = list(replies)
        self.requests: list[dict[str, Any]] = []
        self.chat = SimpleNamespace(completions=SimpleNamespace(create=self._create))

    def _create(self, **request: Any) -> SimpleNamespace:
        self.requests.append(request)
        return self._replies.pop(0)
