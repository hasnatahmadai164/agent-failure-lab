import re
from dataclasses import dataclass
from pathlib import Path
from string import Template

from agent_failure_lab.errors import ScaffoldError
from agent_failure_lab.registry import module_name, validate_slug
from agent_failure_lab.scenario import CATEGORIES

INIT_TEMPLATE = Template("""\
from agent_failure_lab.failures.$module import broken, fixed
from agent_failure_lab.scenario import ScenarioDefinition

SCENARIO = ScenarioDefinition(
    slug="$slug",
    title="$title",
    category="$category",
    summary="Describe what goes wrong in one sentence",
    fix="Name the fix",
    guards=("StepBudget",),
    broken=broken.run,
    fixed=fixed.run,
)
""")

WORLD_TEMPLATE = '''\
from collections.abc import Mapping, Sequence
from typing import Any

from agent_failure_lab.scenario import Outcome, Variant
from agent_failure_lab.sim import (
    Agent,
    EventKind,
    Guard,
    ManualClock,
    Message,
    Reply,
    ScriptedLLM,
    Tool,
    ToolCall,
    ToolRegistry,
    ToolSpec,
    system_message,
    user_message,
)

SYSTEM_PROMPT = "You are an assistant. Use the tools to complete the task."
TASK = "Run the nightly job once."


class Ledger:
    """The fake system the tool changes. Replace it with whatever your failure needs."""

    def __init__(self) -> None:
        self.jobs: list[str] = []


def job_tool(ledger: Ledger) -> Tool:
    def run_job(arguments: Mapping[str, Any]) -> str:
        ledger.jobs.append(str(arguments["name"]))
        return f"job {arguments['name']} done"

    spec = ToolSpec(
        "run_job",
        "Run a named job.",
        parameters={
            "type": "object",
            "properties": {"name": {"type": "string"}},
            "required": ["name"],
        },
        side_effects=("runs-job",),
    )
    return Tool(spec, run_job)


def eager_agent(messages: Sequence[Message]) -> Reply:
    """Asks for the same job again and again, which is what makes the failure happen."""
    return Reply(tool_calls=(ToolCall("run_job", {"name": "nightly"}),))


def play(variant: Variant, *, guards: Sequence[Guard] = ()) -> Outcome:
    ledger = Ledger()
    agent = Agent(
        ScriptedLLM([eager_agent], repeat_last=True),
        ToolRegistry([job_tool(ledger)]),
        clock=ManualClock(),
        guards=guards,
        max_steps=4,
    )
    agent.run([system_message(SYSTEM_PROMPT), user_message(TASK)])

    repeated = len(ledger.jobs) > 1
    findings: tuple[str, ...] = ()
    if repeated:
        findings = (f"The job ran {len(ledger.jobs)} times when it should have run once.",)
    return Outcome(
        variant,
        failure_observed=repeated,
        trace=agent.trace,
        metrics={
            "jobs_run": len(ledger.jobs),
            "guard_interventions": len(agent.trace.of_kind(EventKind.GUARD)),
        },
        findings=findings,
    )
'''

BROKEN_TEMPLATE = Template("""\
from agent_failure_lab.failures.$module.world import play
from agent_failure_lab.scenario import Outcome, Variant


def run() -> Outcome:
    return play(Variant.BROKEN)
""")

FIXED_TEMPLATE = Template("""\
from agent_failure_lab.failures.$module.world import play
from agent_failure_lab.guards import StepBudget
from agent_failure_lab.scenario import Outcome, Variant


def run() -> Outcome:
    return play(Variant.FIXED, guards=[StepBudget(1)])
""")

README_TEMPLATE = Template("""\
# $slug

Describe the failure in one sentence.

## What happens

Say what the agent does and what goes wrong, in a few plain sentences.

## Why it happens

Explain the mechanism. Why does the loop, the model or the tool allow this?

## Impact

Say who or what is affected, and how badly.

## How to detect it in your own system

- Name a signal someone could look for in their own logs or data.
- Add a check they could run.

## The fix

Describe the guard and how it works here.

## Trade-offs

- Say what the fix costs or what it does not cover.

## Related guards

`StepBudget`. See `docs/guards.md`.
""")

TEST_TEMPLATE = Template("""\
from agent_failure_lab.failures.$module import SCENARIO
from agent_failure_lab.scenario import Variant


def test_broken_variant_shows_the_failure() -> None:
    outcome = SCENARIO.run(Variant.BROKEN)

    assert outcome.failure_observed
    assert outcome.metrics["jobs_run"] > 1


def test_fixed_variant_avoids_the_failure() -> None:
    outcome = SCENARIO.run(Variant.FIXED)

    assert not outcome.failure_observed
    assert outcome.metrics["jobs_run"] == 1
""")

_IMPORTS = re.compile(r"(from agent_failure_lab\.failures import \(\n)((?:    \w+,\n)+)(\))")
_RETURN = re.compile(r"(    return \(\n(?:        \w+\.SCENARIO,\n)+)(    \)\n)")


@dataclass(frozen=True, slots=True)
class ScaffoldResult:
    created: tuple[Path, ...]
    registered: bool


def register_in_catalogue(init_path: Path, module: str) -> bool:
    """Add the new package to failures/__init__.py. Returns False if the file has another shape."""
    text = init_path.read_text(encoding="utf-8")
    if f"{module}.SCENARIO" in text:
        return True
    imports, returned = _IMPORTS.search(text), _RETURN.search(text)
    if imports is None or returned is None:
        return False
    names = sorted({*re.findall(r"\w+", imports.group(2)), module})
    text = text[: imports.start(2)] + "".join(f"    {n},\n" for n in names) + text[imports.end(2) :]
    returned = _RETURN.search(text)
    if returned is None:
        return False
    text = text[: returned.end(1)] + f"        {module}.SCENARIO,\n" + text[returned.end(1) :]
    init_path.write_text(text, encoding="utf-8", newline="\n")
    return True


def _write(path: Path, content: str) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8", newline="\n")
    return path


def scaffold_failure(root: Path, slug: str, *, category: str) -> ScaffoldResult:
    validate_slug(slug)
    if category not in CATEGORIES:
        raise ScaffoldError(
            f"Unknown category '{category}'. Choose one of: {', '.join(CATEGORIES)}"
        )
    failures = root / "src" / "agent_failure_lab" / "failures"
    if not failures.is_dir():
        raise ScaffoldError(
            f"Could not find {failures}. Run this from the repository root, or pass --root."
        )
    module = module_name(slug)
    package = failures / module
    if package.exists():
        raise ScaffoldError(f"{package} already exists")
    values = {
        "slug": slug,
        "module": module,
        "title": slug.replace("-", " ").capitalize(),
        "category": category,
    }
    created = (
        _write(package / "__init__.py", INIT_TEMPLATE.substitute(values)),
        _write(package / "world.py", WORLD_TEMPLATE),
        _write(package / "broken.py", BROKEN_TEMPLATE.substitute(values)),
        _write(package / "fixed.py", FIXED_TEMPLATE.substitute(values)),
        _write(package / "README.md", README_TEMPLATE.substitute(values)),
        _write(root / "tests" / "failures" / f"test_{module}.py", TEST_TEMPLATE.substitute(values)),
    )
    registered = register_in_catalogue(failures / "__init__.py", module)
    return ScaffoldResult(created, registered)
