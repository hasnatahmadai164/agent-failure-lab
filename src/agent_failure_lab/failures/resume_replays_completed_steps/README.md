# resume-replays-completed-steps

After a crash, the restarted agent repeats work that already finished.

## What happens

The agent onboards a customer in three steps: create the account, send a welcome email, charge a setup fee. The process is killed while it is charging the fee. When the job is started again, the agent has no record of the first run. It follows the same plan from the top, creates a second account and sends a second welcome email, then charges the fee.

## Why it happens

A restart gives the agent an empty conversation. The model decides what to do from what it can see, and it cannot see what the previous run did. The outside world remembers, but the agent does not, so every finished step looks unfinished.

## Impact

Duplicate accounts, duplicate emails, and in the worst case duplicate payments, all triggered by an infrastructure event rather than a mistake in the task. The longer the job and the later the crash, the more work is repeated.

## How to detect it in your own system

- Give each job a stable id and count side effects per job, not per run. More than one of the same side effect for one job after a restart is the signal.
- Alert when a job is started again after an unclean exit, and review what it did the second time.
- Test by killing the process at each step of a job and checking the result.

## The fix

`StepJournal` keeps a record of completed side-effecting steps in a `Journal` that outlives the run. On a restart the guard answers a step that is already in the journal from the record instead of running it, so the agent moves through the finished steps and does only the unfinished one. Failed steps are not recorded, so they run again.

Here the account and the email are replayed from the journal and the fee is charged once.

## Trade-offs

- The journal has to be durable. The one in this library lives in memory, which is enough to show the mechanism but would not survive a real crash.
- Steps are matched by tool, arguments and how many times the same call has been made. If the model changes its plan on the restart, a step it no longer takes is never replayed, and a changed argument counts as new work.
- A step that crashed halfway, after its effect but before it was recorded, will run again. Pair the journal with idempotency keys for steps where that matters.
- Only side-effecting tools are journaled. Reads run again, so they see fresh data.

## Related guards

`StepJournal`, `Journal`, and `IdempotencyKeys` for the halfway case. See `docs/guards.md`.
