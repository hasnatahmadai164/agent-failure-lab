# Security policy

## Reporting a vulnerability

Please do not open a public issue for a security problem. Use GitHub's private vulnerability reporting instead: open the repository's **Security** tab and choose **Report a vulnerability**. That opens a private conversation with the maintainer.

Include what you found, how to reproduce it, which version you tested (`aflab --version`), and what you think the impact is.

You can expect an acknowledgement within a week. This is a project maintained by one person in their own time, so I cannot promise a fixed deadline for a fix, but I will keep you informed of progress and credit you in the changelog if you would like that.

## What is in scope

- The `agent_failure_lab` package and the `aflab` command line tool.
- The release workflow and the files it publishes.
- Anything that could expose a secret, such as an API key written to a log, a trace or an error message.

## What is not

- The guards are not a security boundary. Each one closes a specific gap and its write-up says what it leaves open. A way to get past the prompt injection quarantine with a differently worded instruction, for example, is documented behaviour and not a vulnerability. The `CapabilityGate` is the dependable control, and a bypass of it would be in scope.
- The scenarios are simulations. They make no network calls and change nothing outside memory, apart from the files `aflab new` and `aflab report --output` are asked to write.
- Problems in the OpenAI client library or in other packages this project depends on belong to those projects.

## Live mode and API keys

Live mode reads `OPENAI_API_KEY` from your environment and sends requests to OpenAI with it. This library does not write the key to the trace or to any file. When a request fails, the error text from OpenAI is shown as received, and for a rejected key that text can include a masked fragment of it. If you see the full key appear anywhere, please report it.

## Supported versions

Only the latest release receives fixes.
