from collections.abc import Mapping, Sequence
from typing import Any

from agent_failure_lab.guards import Journal, StepJournal
from agent_failure_lab.scenario import Outcome, Variant
from agent_failure_lab.sim import (
    Agent,
    EventKind,
    Guard,
    ManualClock,
    Message,
    Reply,
    Role,
    ScriptedLLM,
    Tool,
    ToolCall,
    ToolRegistry,
    ToolSpec,
    Trace,
    system_message,
    user_message,
)

CUSTOMER = "sam@example.com"
SETUP_FEE = 25.0
STEPS = ("create_account", "send_welcome_email", "charge_setup_fee")
SYSTEM_PROMPT = "You are an onboarding assistant. Use the tools to complete the task."
TASK = f"Onboard the new customer {CUSTOMER}."


class ProcessCrashError(Exception):
    """The process died. This is not a tool error, so the model never hears about it."""


class OnboardingWorld:
    """The outside world, which keeps what happened even when the agent process dies."""

    def __init__(self) -> None:
        self.accounts: list[str] = []
        self.welcome_emails: list[str] = []
        self.charges: list[float] = []
        self.crash_pending = True


def onboarding_tools(world: OnboardingWorld) -> list[Tool]:
    def create_account(arguments: Mapping[str, Any]) -> str:
        world.accounts.append(str(arguments["email"]))
        return f"account created for {arguments['email']}"

    def send_welcome_email(arguments: Mapping[str, Any]) -> str:
        world.welcome_emails.append(str(arguments["to"]))
        return f"welcome email sent to {arguments['to']}"

    def charge_setup_fee(arguments: Mapping[str, Any]) -> str:
        if world.crash_pending:
            world.crash_pending = False
            raise ProcessCrashError("the process was killed while charging the setup fee")
        world.charges.append(float(arguments["amount"]))
        return f"charged {arguments['amount']} EUR"

    def spec(name: str, description: str, effect: str) -> ToolSpec:
        return ToolSpec(name, description, side_effects=(effect,))

    return [
        Tool(
            spec("create_account", "Create the customer account.", "creates-account"),
            create_account,
        ),
        Tool(
            spec("send_welcome_email", "Send the welcome email.", "sends-email"), send_welcome_email
        ),
        Tool(
            spec("charge_setup_fee", "Charge the one-time setup fee.", "charges-card"),
            charge_setup_fee,
        ),
    ]


def _step_call(step: str) -> ToolCall:
    arguments: dict[str, dict[str, Any]] = {
        "create_account": {"email": CUSTOMER},
        "send_welcome_email": {"to": CUSTOMER},
        "charge_setup_fee": {"email": CUSTOMER, "amount": SETUP_FEE},
    }
    return ToolCall(step, arguments[step])


def onboarding_agent(messages: Sequence[Message]) -> Reply:
    """Follows the same plan on every start, with no memory of any earlier attempt."""
    finished = sum(1 for m in messages if m.role is Role.TOOL)
    if finished < len(STEPS):
        return Reply(tool_calls=(_step_call(STEPS[finished]),))
    return Reply(f"Onboarding for {CUSTOMER} is complete.")


def play(variant: Variant, *, journal: Journal | None = None) -> Outcome:
    world = OnboardingWorld()
    clock = ManualClock()
    trace = Trace(clock)
    tools = onboarding_tools(world)
    replays = 0
    runs = 0
    for _ in range(2):
        runs += 1
        journaling = StepJournal(journal) if journal is not None else None
        guards: list[Guard] = [journaling] if journaling is not None else []
        agent = Agent(
            ScriptedLLM([onboarding_agent], repeat_last=True),
            ToolRegistry(tools),
            clock=clock,
            guards=guards,
            max_steps=6,
            trace=trace,
        )
        try:
            agent.run([system_message(SYSTEM_PROMPT), user_message(TASK)])
        except ProcessCrashError as crash:
            trace.record(0, EventKind.STOP, f"process crashed: {crash}")
            continue
        finally:
            replays += journaling.replays if journaling is not None else 0
        break

    repeated = []
    if len(world.accounts) > 1:
        repeated.append(f"{len(world.accounts)} accounts created")
    if len(world.welcome_emails) > 1:
        repeated.append(f"{len(world.welcome_emails)} welcome emails sent")
    if len(world.charges) > 1:
        repeated.append(f"{len(world.charges)} setup fees charged")
    findings: tuple[str, ...] = ()
    if repeated:
        findings = (
            "After the restart the agent repeated finished work: " + ", ".join(repeated) + ".",
        )
    elif replays:
        findings = (f"The restart skipped {replays} steps that the journal showed as done.",)
    return Outcome(
        variant,
        failure_observed=bool(repeated),
        trace=trace,
        metrics={
            "runs": runs,
            "accounts_created": len(world.accounts),
            "welcome_emails_sent": len(world.welcome_emails),
            "setup_fees_charged": len(world.charges),
            "steps_replayed_from_journal": replays,
        },
        findings=findings,
    )
