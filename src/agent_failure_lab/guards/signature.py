import json
from collections.abc import Mapping
from typing import Any

from agent_failure_lab.sim import ToolCall


def canonical_arguments(arguments: Mapping[str, Any]) -> str:
    return json.dumps(dict(arguments), sort_keys=True, separators=(",", ":"))


def call_signature(call: ToolCall) -> str:
    return f"{call.name}:{canonical_arguments(call.arguments)}"
