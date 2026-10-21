import re
from collections.abc import Collection
from dataclasses import replace

from agent_failure_lab.sim import Block, Guard, RunState, ToolCall, ToolResult

_INSTRUCTION = re.compile(
    r"\b(always|never|from now on|whenever|every time|ignore|must|do not|don't|make sure)\b",
    re.IGNORECASE,
)
_SENTENCE_BREAK = re.compile(r"(?<=[.!?])\s+|\n+")
_MIN_SENTENCE = 20


class MemoryWriteFilter(Guard):
    """Tags every memory write with where its text came from, and refuses poisoned ones.

    A write whose text matches content read from an untrusted tool is tagged as untrusted.
    If that text also reads as an instruction (always, never, from now on, and so on), the
    write is refused, so untrusted content can be remembered as a fact but never as a
    standing order. Matching is on the text itself: a paraphrase will not be recognised.
    """

    def __init__(
        self,
        *,
        write_tool: str,
        untrusted_tools: Collection[str],
        text_argument: str = "text",
        source_argument: str = "source",
    ) -> None:
        self._write_tool = write_tool
        self._untrusted = frozenset(untrusted_tools)
        self._text_argument = text_argument
        self._source_argument = source_argument
        self._outputs: list[tuple[str, str]] = []

    def after_tool(self, run: RunState, call: ToolCall, result: ToolResult) -> None:
        if call.name in self._untrusted and not result.is_error:
            self._outputs.append((call.name, _normalise(result.content)))

    def before_tool(self, run: RunState, call: ToolCall) -> ToolCall | Block | None:
        if call.name != self._write_tool:
            return None
        text = str(call.arguments.get(self._text_argument, ""))
        origin = self._origin_of(_normalise(text))
        if origin is None:
            source = "agent"
        else:
            source = f"untrusted:{origin}"
            if _INSTRUCTION.search(text):
                run.intervene(
                    self.name, f"refused a memory that came from {origin} and reads as an order"
                )
                return Block(
                    ToolResult(
                        f"Not saved: this text came from {origin} and reads as an instruction. "
                        "Content from untrusted sources can be remembered as a fact, "
                        "not as a standing instruction.",
                        is_error=True,
                    )
                )
        run.intervene(self.name, f"tagged a memory write as {source}", {"source": source})
        return replace(call, arguments={**call.arguments, self._source_argument: source})

    def _origin_of(self, text: str) -> str | None:
        for tool, output in self._outputs:
            if text and text in output:
                return tool
            sentences = (s for s in _SENTENCE_BREAK.split(output) if len(s) >= _MIN_SENTENCE)
            if any(sentence in text for sentence in sentences):
                return tool
        return None


def _normalise(text: str) -> str:
    return " ".join(text.lower().split())
