import json
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from enum import Enum
from typing import Any

from agent_failure_lab.errors import ToolError
from agent_failure_lab.sim.clock import Clock
from agent_failure_lab.sim.hooks import Block, Guard, RunState, Stop
from agent_failure_lab.sim.llm import LanguageModel, ModelTurn, Usage
from agent_failure_lab.sim.messages import Message, ToolCall, tool_message
from agent_failure_lab.sim.state import BatchScope
from agent_failure_lab.sim.tools import ToolRegistry, ToolResult
from agent_failure_lab.sim.trace import EventKind, Trace

SUMMARY_LIMIT = 70


class StopReason(str, Enum):
    FINAL_ANSWER = "final_answer"
    STEP_LIMIT = "step_limit"
    GUARD_STOP = "guard_stop"


@dataclass(frozen=True, slots=True)
class RunResult:
    stop_reason: StopReason
    stop_detail: str
    final_answer: str | None
    steps: int
    messages: tuple[Message, ...]
    usage: Usage
    elapsed_seconds: float


@dataclass(frozen=True, slots=True)
class _Finish:
    reason: StopReason
    detail: str = ""
    answer: str | None = None


class Agent:
    """A minimal agent loop: call the model, run its tool calls, repeat until it answers.

    One step is one model call plus the tool calls it asked for. Guards hook into the loop
    at five points; with no guards the loop does exactly what the model says. Errors raised by
    tools are reported to the model as error results. Any other exception ends the run.

    With a batch scope, the tool calls of a turn that asks for more than one run as a single
    concurrent batch, so calls that share state can overwrite each other.
    """

    def __init__(
        self,
        model: LanguageModel,
        tools: ToolRegistry,
        *,
        clock: Clock,
        guards: Sequence[Guard] = (),
        max_steps: int = 20,
        tool_timeout: float | None = None,
        trace: Trace | None = None,
        batch: BatchScope | None = None,
    ) -> None:
        if max_steps < 1:
            raise ValueError("max_steps must be at least 1")
        self._model = model
        self._tools = tools
        self._clock = clock
        self._guards = tuple(guards)
        self._max_steps = max_steps
        self._tool_timeout = tool_timeout
        self._trace = trace if trace is not None else Trace(clock)
        self._batch = batch

    @property
    def trace(self) -> Trace:
        return self._trace

    def run(self, messages: Sequence[Message]) -> RunResult:
        state = RunState(
            clock=self._clock,
            trace=self._trace,
            tool_specs=self._tools.specs(),
            history=messages,
            tool_timeout=self._tool_timeout,
        )
        finish = self._loop(state)
        summary = finish.reason.value + (f": {finish.detail}" if finish.detail else "")
        self._trace.record(state.step, EventKind.STOP, summary)
        return RunResult(
            stop_reason=finish.reason,
            stop_detail=finish.detail,
            final_answer=finish.answer,
            steps=state.step,
            messages=state.history,
            usage=state.usage,
            elapsed_seconds=state.elapsed(),
        )

    def _loop(self, state: RunState) -> _Finish:
        for step in range(1, self._max_steps + 1):
            state.step = step
            finish = self._run_step(state)
            if finish is not None:
                return finish
        return _Finish(StopReason.STEP_LIMIT, f"step limit of {self._max_steps} reached")

    def _run_step(self, state: RunState) -> _Finish | None:
        request = self._before_model(state)
        if isinstance(request, Stop):
            return _guard_stop(request)
        turn = self._model.generate(request, state.tool_specs)
        state.usage = state.usage + turn.usage
        self._record_turn(state, turn)
        checked = self._after_model(state, turn)
        if isinstance(checked, Stop):
            return _guard_stop(checked)
        state.append(checked.message)
        if not checked.message.tool_calls:
            return _Finish(StopReason.FINAL_ANSWER, answer=checked.message.content)
        finish = self._run_tool_calls(state, checked.message.tool_calls)
        if finish is not None:
            return finish
        return self._step_end(state)

    def _run_tool_calls(self, state: RunState, calls: Sequence[ToolCall]) -> _Finish | None:
        batch = self._batch if len(calls) > 1 else None
        if batch is not None:
            batch.begin()
        try:
            for call in calls:
                finish = self._run_tool_call(state, call)
                if finish is not None:
                    return finish
        finally:
            if batch is not None:
                batch.end()
        return None

    def _run_tool_call(self, state: RunState, call: ToolCall) -> _Finish | None:
        state.trace.record(
            state.step,
            EventKind.TOOL_CALL,
            _format_call(call),
            {"tool": call.name, "arguments": dict(call.arguments), "call_id": call.id},
        )
        prepared = self._before_tool(state, call)
        if isinstance(prepared, Stop):
            return _guard_stop(prepared)
        if isinstance(prepared, Block):
            executed, result = call, prepared.result
        else:
            executed, result = prepared, self._invoke(state, prepared)
        checked = self._after_tool(state, executed, result)
        if isinstance(checked, Stop):
            return _guard_stop(checked)
        state.trace.record(
            state.step,
            EventKind.TOOL_RESULT,
            f"{executed.name} -> {_clip(checked.content)}",
            {"tool": executed.name, "is_error": checked.is_error, "content": checked.content},
        )
        state.append(tool_message(executed, checked.content, is_error=checked.is_error))
        return None

    def _invoke(self, state: RunState, call: ToolCall) -> ToolResult:
        try:
            tool = self._tools.get(call.name)
            content = tool.run(call.arguments, self._clock, timeout=state.tool_timeout)
        except ToolError as error:
            return ToolResult(f"error: {error}", is_error=True)
        return ToolResult(content)

    def _record_turn(self, state: RunState, turn: ModelTurn) -> None:
        message = turn.message
        if message.tool_calls:
            summary = "requests " + ", ".join(_format_call(call) for call in message.tool_calls)
        else:
            summary = f'says "{_clip(message.content)}"'
        state.trace.record(
            state.step,
            EventKind.MODEL,
            summary,
            {
                "prompt_tokens": turn.usage.prompt_tokens,
                "completion_tokens": turn.usage.completion_tokens,
            },
        )

    def _before_model(self, state: RunState) -> Sequence[Message] | Stop:
        request: Sequence[Message] = state.history
        for guard in self._guards:
            outcome = guard.before_model(state, request)
            if isinstance(outcome, Stop):
                return outcome
            if outcome is not None:
                request = outcome
        return request

    def _after_model(self, state: RunState, turn: ModelTurn) -> ModelTurn | Stop:
        for guard in self._guards:
            outcome = guard.after_model(state, turn)
            if isinstance(outcome, Stop):
                return outcome
            if outcome is not None:
                turn = outcome
        return turn

    def _before_tool(self, state: RunState, call: ToolCall) -> ToolCall | Block | Stop:
        for guard in self._guards:
            outcome = guard.before_tool(state, call)
            if isinstance(outcome, Block | Stop):
                return outcome
            if outcome is not None:
                call = outcome
        return call

    def _after_tool(self, state: RunState, call: ToolCall, result: ToolResult) -> ToolResult | Stop:
        for guard in self._guards:
            outcome = guard.after_tool(state, call, result)
            if isinstance(outcome, Stop):
                return outcome
            if outcome is not None:
                result = outcome
        return result

    def _step_end(self, state: RunState) -> _Finish | None:
        for guard in self._guards:
            stop = guard.on_step_end(state)
            if stop is not None:
                return _guard_stop(stop)
        return None


def _guard_stop(stop: Stop) -> _Finish:
    return _Finish(StopReason.GUARD_STOP, stop.reason)


def _clip(text: str) -> str:
    flat = " ".join(text.split())
    if len(flat) <= SUMMARY_LIMIT:
        return flat
    return flat[: SUMMARY_LIMIT - 3] + "..."


def _format_call(call: ToolCall) -> str:
    return f"{call.name}({_format_arguments(call.arguments)})"


def _format_arguments(arguments: Mapping[str, Any]) -> str:
    return _clip(json.dumps(dict(arguments), sort_keys=True))
