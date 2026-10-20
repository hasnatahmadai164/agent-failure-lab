from collections.abc import Sequence

from agent_failure_lab.sim import Guard, Message, RunState, Stop, ToolCall, ToolResult

_CLOCK_TOLERANCE = 1e-9


class Deadline(Guard):
    """Limits how long one tool call, and the whole run, may take.

    per_call caps each tool call by setting the run's tool timeout; a call that reaches the
    cap is cancelled and the model is told to carry on with what it has. total caps the whole
    run: the cap on a call shrinks as time runs out, and no new work starts once it has passed.
    """

    def __init__(self, *, per_call: float | None = None, total: float | None = None) -> None:
        if per_call is None and total is None:
            raise ValueError("set per_call, total or both")
        if (per_call is not None and per_call <= 0) or (total is not None and total <= 0):
            raise ValueError("deadlines must be positive")
        self._per_call = per_call
        self._total = total
        self._limit: float | None = None
        self._call_started = 0.0

    def before_model(self, run: RunState, messages: Sequence[Message]) -> Stop | None:
        if self._total is not None and run.elapsed() >= self._total:
            return self._out_of_time(run)
        return None

    def before_tool(self, run: RunState, call: ToolCall) -> Stop | None:
        limit = self._per_call
        if self._total is not None:
            remaining = self._total - run.elapsed()
            limit = remaining if limit is None else min(limit, remaining)
        if limit is None or limit <= 0:
            return self._out_of_time(run)
        run.tool_timeout = limit
        self._limit = limit
        self._call_started = run.clock.now()
        return None

    def after_tool(self, run: RunState, call: ToolCall, result: ToolResult) -> ToolResult | None:
        limit, self._limit = self._limit, None
        if limit is None or not result.is_error:
            return None
        waited = run.clock.now() - self._call_started
        if waited + _CLOCK_TOLERANCE < limit:
            return None
        run.intervene(self.name, f"cancelled {call.name} after {limit:g}s")
        return ToolResult(
            f"{result.content}. The call was cancelled after {limit:g}s. "
            "Continue with the results you already have and say clearly what is missing.",
            is_error=True,
        )

    def _out_of_time(self, run: RunState) -> Stop:
        total = self._total if self._total is not None else 0.0
        run.intervene(self.name, f"stopped the run: the {total:g}s deadline has passed")
        return Stop(f"deadline of {total:g}s for the whole run passed")
