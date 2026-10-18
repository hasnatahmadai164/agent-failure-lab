# tool-output-injection

Instructions hidden in a tool result hijack the next action.

## What happens

The agent is asked to read a web page and email a summary to the customer who asked. The page contains a hidden comment telling the assistant to ignore its instructions and email a customer list to an outside address. The model treats that text as an instruction and sends the email, then carries on with the real task.

## Why it happens

To a language model, everything in its context is text. Tool output and user instructions arrive in the same channel, so text in a fetched page can read as a command. The agent has a tool that can send email, and nothing checks where it is sending to.

## Impact

Data leaves the system, or an action is taken, on the word of whoever wrote the page. The user did nothing wrong and sees a normal summary. The risk is highest when an agent combines three things: it reads content from outside, it can see private data, and it can send things out.

## How to detect it in your own system

- Log every call to a tool with outward effects (email, payments, writes) together with where its arguments came from.
- Alert on recipients, domains or targets that never appeared in the user's request.
- Run content you fetch through a scan for instruction-like text such as "ignore previous instructions". It will miss things, so treat it as a signal and not as a defence.

## The fix

Two guards, and the second one matters more.

- `ToolOutputQuarantine` wraps the output of untrusted tools in a block marked as data and notes that the run has read untrusted content.
- `CapabilityGate` refuses calls to sensitive tools unless their arguments pass a check. Here it allows email only to the customer in the request, and only starts checking once untrusted content has been read.

In this scenario the scripted model follows the injection in both variants. That is deliberate. The gate stops the email whatever the model decides to do.

## Trade-offs

- Wrapping and labelling reduces how often a real model obeys hidden text but cannot guarantee it. Do not rely on it alone.
- The gate needs a policy for each sensitive tool, and the policy has to come from somewhere trusted such as the original request or configuration.
- A gate that is too strict blocks legitimate work. A human approval step for blocked calls is a common middle path.

## Related guards

`ToolOutputQuarantine`, `CapabilityGate`. See `docs/guards.md`.
