import itertools
import re
from collections.abc import Sequence
from dataclasses import dataclass

from agent_failure_lab.sim import Guard, Message, RunState, Stop, ToolSpec

_WORD = re.compile(r"[a-z0-9]+")
_STOPWORDS = frozenset(
    {
        "a",
        "an",
        "the",
        "to",
        "of",
        "for",
        "and",
        "or",
        "in",
        "on",
        "is",
        "it",
        "that",
        "this",
        "with",
        "by",
        "from",
        "as",
        "at",
        "be",
        "will",
        "can",
        "not",
        "only",
    }
)


@dataclass(frozen=True, slots=True)
class LintFinding:
    tools: tuple[str, ...]
    message: str


def description_words(text: str) -> frozenset[str]:
    return frozenset(_WORD.findall(text.lower())) - _STOPWORDS


def lint_descriptions(
    specs: Sequence[ToolSpec], *, max_overlap: float = 0.5, min_words: int = 3
) -> list[LintFinding]:
    """Report tools whose descriptions are too short, or too alike to tell apart.

    Overlap is the share of meaningful words two descriptions have in common (Jaccard).
    A model that cannot tell two descriptions apart will pick one almost arbitrarily.
    """
    words = {spec.name: description_words(spec.description) for spec in specs}
    findings = [
        LintFinding((name,), f"{name} has fewer than {min_words} meaningful words")
        for name, found in words.items()
        if len(found) < min_words
    ]
    for first, second in itertools.combinations(specs, 2):
        a, b = words[first.name], words[second.name]
        overlap = len(a & b) / len(a | b) if a | b else 0.0
        if overlap > max_overlap:
            findings.append(
                LintFinding(
                    (first.name, second.name),
                    f"{first.name} and {second.name} descriptions overlap by {overlap:.0%}",
                )
            )
    return findings


class ToolDescriptionLinter(Guard):
    """Checks the tool descriptions once, before the first model call of a run.

    With strict set, ambiguous descriptions stop the run before the model can pick the wrong
    tool. Without it, the findings are only written to the trace.
    """

    def __init__(
        self, *, max_overlap: float = 0.5, min_words: int = 3, strict: bool = True
    ) -> None:
        self._max_overlap = max_overlap
        self._min_words = min_words
        self._strict = strict
        self._checked = False

    def before_model(self, run: RunState, messages: Sequence[Message]) -> Stop | None:
        if self._checked:
            return None
        self._checked = True
        findings = lint_descriptions(
            run.tool_specs, max_overlap=self._max_overlap, min_words=self._min_words
        )
        if not findings:
            return None
        detail = "; ".join(finding.message for finding in findings)
        if not self._strict:
            run.intervene(self.name, f"found unclear tool descriptions: {detail}")
            return None
        run.intervene(self.name, f"stopped the run: {detail}")
        return Stop(f"unclear tool descriptions: {detail}")
