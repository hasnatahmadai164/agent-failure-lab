from agent_failure_lab.failures.memory_poisoning.world import play
from agent_failure_lab.guards import MemoryWriteFilter
from agent_failure_lab.scenario import Outcome, Variant


def run() -> Outcome:
    memory_filter = MemoryWriteFilter(write_tool="save_memory", untrusted_tools=["read_email"])
    return play(Variant.FIXED, writing_guards=[memory_filter])
