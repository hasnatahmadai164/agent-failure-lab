import json
import re
from collections.abc import Callable, Mapping
from typing import Any

from agent_failure_lab.sim import Block, Guard, RunState, Stop, ToolCall, ToolResult

_TYPE_CHECKS: dict[str, Callable[[Any], bool]] = {
    "string": lambda value: isinstance(value, str),
    "integer": lambda value: isinstance(value, int) and not isinstance(value, bool),
    "number": lambda value: isinstance(value, int | float) and not isinstance(value, bool),
    "boolean": lambda value: isinstance(value, bool),
    "array": lambda value: isinstance(value, list),
    "object": lambda value: isinstance(value, Mapping),
}


def validate_arguments(schema: Mapping[str, Any], arguments: Mapping[str, Any]) -> list[str]:
    """Check arguments against a small subset of JSON Schema and list the problems found.

    Supported: required, additionalProperties false, and per property type, enum, pattern,
    minLength, maxLength, minimum and maximum. Other keywords are ignored.
    """
    problems = [
        f"missing required argument '{name}'"
        for name in schema.get("required", [])
        if name not in arguments
    ]
    properties = schema.get("properties", {})
    for name, value in arguments.items():
        rules = properties.get(name)
        if rules is None:
            if schema.get("additionalProperties") is False:
                problems.append(f"unknown argument '{name}'")
            continue
        problems.extend(_check_value(name, value, rules))
    return problems


def _check_value(name: str, value: Any, rules: Mapping[str, Any]) -> list[str]:
    expected = rules.get("type")
    if expected in _TYPE_CHECKS and not _TYPE_CHECKS[expected](value):
        return [f"'{name}' must be of type {expected}, got {type(value).__name__}"]
    problems: list[str] = []
    if "enum" in rules and value not in rules["enum"]:
        allowed = json.dumps(list(rules["enum"]))
        problems.append(f"'{name}' got {value!r}, allowed values: {allowed}")
    if isinstance(value, str):
        problems.extend(_check_string(name, value, rules))
    if isinstance(value, int | float) and not isinstance(value, bool):
        problems.extend(_check_number(name, value, rules))
    return problems


def _check_string(name: str, value: str, rules: Mapping[str, Any]) -> list[str]:
    problems: list[str] = []
    if "pattern" in rules and not re.search(rules["pattern"], value):
        problems.append(f"'{name}' got {value!r}, which does not match {rules['pattern']}")
    if "minLength" in rules and len(value) < rules["minLength"]:
        problems.append(f"'{name}' must be at least {rules['minLength']} characters")
    if "maxLength" in rules and len(value) > rules["maxLength"]:
        problems.append(f"'{name}' must be at most {rules['maxLength']} characters")
    return problems


def _check_number(name: str, value: float, rules: Mapping[str, Any]) -> list[str]:
    problems: list[str] = []
    if "minimum" in rules and value < rules["minimum"]:
        problems.append(f"'{name}' must be at least {rules['minimum']}")
    if "maximum" in rules and value > rules["maximum"]:
        problems.append(f"'{name}' must be at most {rules['maximum']}")
    return problems


class ArgumentValidator(Guard):
    """Checks tool arguments against the tool's schema before the tool runs.

    An invalid call is not executed. The model gets the list of problems and may try again.
    After max_repairs invalid calls to the same tool in a row, the run is stopped, so the
    repair loop stays bounded. A valid call resets the count for that tool.
    """

    def __init__(self, max_repairs: int = 2) -> None:
        if max_repairs < 0:
            raise ValueError("max_repairs cannot be negative")
        self._max_repairs = max_repairs
        self._failures: dict[str, int] = {}

    def before_tool(self, run: RunState, call: ToolCall) -> Block | Stop | None:
        spec = next((s for s in run.tool_specs if s.name == call.name), None)
        if spec is None:
            return None
        problems = validate_arguments(spec.parameters, call.arguments)
        if not problems:
            self._failures.pop(call.name, None)
            return None
        failures = self._failures.get(call.name, 0) + 1
        self._failures[call.name] = failures
        detail = "; ".join(problems)
        if failures > self._max_repairs:
            run.intervene(self.name, f"gave up on {call.name} after {self._max_repairs} repairs")
            return Stop(f"arguments for {call.name} still invalid after repairs: {detail}")
        run.intervene(self.name, f"rejected {call.name}: {detail}")
        return Block(
            ToolResult(
                f"Invalid arguments for {call.name}: {detail}. Correct them and call again.",
                is_error=True,
            )
        )
