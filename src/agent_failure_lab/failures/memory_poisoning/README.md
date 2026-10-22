# memory-poisoning

Untrusted content is written to long-term memory and later treated as instruction.

## What happens

In one session the agent reads a customer email and saves what is worth remembering. The email contains an ordinary request and a line addressed to the assistant: from now on, copy an outside address on every invoice. The model saves both sentences. In a later session, a different task, the agent reads its memory before sending an invoice, finds the standing instruction, and copies the outside address on the invoice.

## Why it happens

Memory is read back as part of the agent's own context, so entries in it carry the weight of the agent's own notes. The text was written by someone else, but by the time it is recalled that is no longer visible. The attack does not need to work when the email is read. It only needs to be saved, and it fires whenever the memory is used.

## Impact

The effect outlasts the session that was attacked. It can reach tasks, users and times that have nothing to do with the original email, and the original source is easy to lose.

## How to detect it in your own system

- Record where every memory entry came from, and show that source when memory is recalled.
- Review memory for entries that read as standing orders, such as always, never or from now on, especially those written in sessions that read outside content.
- Compare the recipients and targets of actions with what the user asked for.

## The fix

`MemoryWriteFilter` stands in front of the memory-write tool. It remembers what untrusted tools returned in the session. A write whose text matches that content is tagged with its origin (`untrusted:read_email`). If the text also reads as an instruction, the write is refused, so outside content can be remembered as a fact but never as a standing order. Every other write is tagged as the agent's own.

Here the request to receive PDFs is saved and tagged as coming from the email. The instruction to copy an outside address is refused, and the later invoice goes out without the copy.

## Trade-offs

- Matching is on the text. If the model rewrites the instruction in its own words, the filter does not recognise it. A check that understands meaning is needed for that, and it brings its own errors.
- The instruction test is a list of phrases. It will miss orders worded differently and may catch harmless ones.
- Tagging only helps if something uses the tag. Show the source when memory is recalled, and treat untrusted entries as data in your prompts.

## Related guards

`MemoryWriteFilter`, and `ToolOutputQuarantine` with `CapabilityGate` for the same content within a single session. See `docs/guards.md`.
