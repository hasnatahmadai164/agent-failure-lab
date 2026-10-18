from agent_failure_lab.guards.signature import call_signature
from agent_failure_lab.sim import Block, Guard, RunState, Stop, ToolCall, ToolResult


class LoopDetector(Guard):
    """Catches an agent repeating the same call and getting the same result.

    Once a call has returned an identical result max_repeats times in a row, the next
    identical call is blocked with a message telling the model to change approach. If it
    repeats the call again after max_warnings such messages, the run is stopped.
    Polling a tool whose result changes is not treated as a loop.
    """

    def __init__(self, max_repeats: int = 3, max_warnings: int = 1) -> None:
        if max_repeats < 2:
            raise ValueError("max_repeats must be at least 2")
        if max_warnings < 0:
            raise ValueError("max_warnings cannot be negative")
        self._max_repeats = max_repeats
        self._max_warnings = max_warnings
        self._results: dict[str, list[str]] = {}
        self._warnings: dict[str, int] = {}
        self._skip_next_result = False

    def before_tool(self, run: RunState, call: ToolCall) -> Block | Stop | None:
        signature = call_signature(call)
        if not self._is_stuck(signature):
            return None
        warnings = self._warnings.get(signature, 0) + 1
        self._warnings[signature] = warnings
        if warnings > self._max_warnings:
            run.intervene(
                self.name, f"stopped the run: {call.name} keeps returning the same result"
            )
            return Stop(f"loop detected: {call.name} repeated with identical arguments and results")
        run.intervene(self.name, f"blocked a repeated call to {call.name}")
        self._skip_next_result = True
        return Block(
            ToolResult(
                f"Loop detected: {call.name} was called {self._max_repeats} times with the same "
                "arguments and returned the same result each time. Do not repeat it. "
                "Try a different approach or answer with what you have.",
                is_error=True,
            )
        )

    def after_tool(self, run: RunState, call: ToolCall, result: ToolResult) -> None:
        if self._skip_next_result:
            self._skip_next_result = False
            return
        self._results.setdefault(call_signature(call), []).append(result.content)

    def _is_stuck(self, signature: str) -> bool:
        recent = self._results.get(signature, [])[-self._max_repeats :]
        return len(recent) == self._max_repeats and len(set(recent)) == 1


class StepBudget(Guard):
    """Ends the run once max_steps model steps have been used.

    The Agent has its own step limit as a last resort. This guard does the same job for any
    loop that has none, and leaves a note in the trace saying why the run ended.
    """

    def __init__(self, max_steps: int) -> None:
        if max_steps < 1:
            raise ValueError("max_steps must be at least 1")
        self._max_steps = max_steps

    def on_step_end(self, run: RunState) -> Stop | None:
        if run.step < self._max_steps:
            return None
        run.intervene(self.name, f"step budget of {self._max_steps} used up")
        return Stop(f"step budget of {self._max_steps} reached")
