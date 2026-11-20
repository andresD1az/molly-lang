# Security policy

Molly is a security tool, so a flaw in it matters more than a flaw in most libraries. Thank you for reporting one responsibly.

## Reporting a vulnerability

Please **do not open a public issue**. Report it privately through GitHub: go to the repository's **Security** tab and choose **Report a vulnerability**. You will get an answer within seven days.

Useful things to include:

- The Molly program, the engine configuration (sources, transforms, sinks and their audiences) and the context used.
- What a public observer could learn or what reached a sink that should not have.
- The Molly version (`molly.__version__`) and the Python version.

## What counts as a vulnerability

- A restricted value, or information derived from it, reaches a sink or an external processor whose identity is not in the value's audience.
- A source is read although its `authorize` check fails.
- Error messages or the trace reveal restricted data or restricted control flow.
- A program that respects the documented limits makes the engine run for an unbounded time or use unbounded memory.

## Known limits (not vulnerabilities)

These are documented in the README and are out of scope for now:

- The abort channel: whether a plan finishes or fails, and at which step, can depend on restricted data.
- Timing channels.
- Adapters are trusted code. An adapter that sends data elsewhere on its own, or a sink whose declared identity does not match the real recipient, breaks the guarantees.

## Supported versions

Only the latest release receives fixes while the project is in alpha.
