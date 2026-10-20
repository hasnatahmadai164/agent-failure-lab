from agent_failure_lab.guards.signature import call_signature
from agent_failure_lab.guards.specs import has_side_effects
from agent_failure_lab.sim import Block, Guard, RunState, ToolCall, ToolResult


class Journal:
    """A record of completed side-effecting steps that outlives a single run.

    This one lives in memory. In a real system it has to be written to durable storage,
    otherwise a crash loses exactly what it exists to remember.
    """

    def __init__(self) -> None:
        self._entries: dict[str, ToolResult] = {}

    def get(self, key: str) -> ToolResult | None:
        return self._entries.get(key)

    def record(self, key: str, result: ToolResult) -> None:
        self._entries[key] = result

    def __len__(self) -> int:
        return len(self._entries)


class StepJournal(Guard):
    """Skips side-effecting steps that an earlier, interrupted run already completed.

    Each call is keyed by its tool, its arguments and how many times this run has made that
    same call, so a deliberate repeat is not mistaken for a replay. A completed call is
    answered from the journal without running. A failed call is not recorded and runs again.
    List this guard last, so a block by another guard is never recorded as completed work.
    """

    def __init__(self, journal: Journal) -> None:
        self._journal = journal
        self._occurrences: dict[str, int] = {}
        self._current_key: str | None = None
        self._replaying = False
        self.replays = 0

    def before_tool(self, run: RunState, call: ToolCall) -> Block | None:
        self._current_key = None
        if not has_side_effects(run, call.name):
            return None
        signature = call_signature(call)
        occurrence = self._occurrences.get(signature, 0) + 1
        self._occurrences[signature] = occurrence
        key = f"{signature}#{occurrence}"
        self._current_key = key
        recorded = self._journal.get(key)
        if recorded is None:
            return None
        self._replaying = True
        self.replays += 1
        run.intervene(self.name, f"skipped {call.name}, completed before the restart", {"key": key})
        return Block(recorded)

    def after_tool(self, run: RunState, call: ToolCall, result: ToolResult) -> None:
        if self._replaying:
            self._replaying = False
            return
        if self._current_key is not None and not result.is_error:
            self._journal.record(self._current_key, result)
        self._current_key = None
