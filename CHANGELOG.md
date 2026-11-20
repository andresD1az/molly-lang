# Changelog

## 0.9.0 (2026-11-20): command line, MCP server and playground

### Added

- **`molly` command:** `check`, `run` (dry run against a policy), `describe` and `init-policy`. Policies are JSON files written by the operator: context, sources with sample data and audience, transforms and sinks, with `{tenant}` and `{subject}` placeholders.
- **`molly-mcp`:** a Model Context Protocol server over stdio, without dependencies, with the tools `molly_describe`, `molly_check` and `molly_run`. The policy is fixed at startup; the agent cannot change it and never sees delivered texts or source data.
- **Playground:** a browser page that runs the real engine with Pyodide, published on GitHub Pages.
- 12 tests for the command line, policies and MCP server (85 in total).

## 0.8.0 (2026-11-19): resource limits and public release

### Fixed

- **A tiny program could run for minutes.** `x = [x, x]` in a loop builds a value whose written-out size doubles every lap, because both halves are the same object. Comparing or printing it visits every copy. Every new list, set and record is now limited to 10,000 elements in total (shared parts counted every time) and 32 levels of nesting.
- **Rendering a large value used unbounded memory.** Turning a value into text for concatenation or sending now stops as soon as it passes the 4,000-character limit, instead of building the whole string first.
- **The error cap only applied to the parser.** A program with 30 lexical errors reported 30. Every phase now stops at 25 errors plus a final "Analysis stopped" note.
- `molly.__version__` now matches the package version.

### Changed

- The wheel installs only the `molly` module. `demo.py` and the examples stay in the repository; the `molly-demo` command was removed.
- The experimental Spanish lab (`molly_lab`) was removed from this repository; it belongs to the course version.

### Added

- 4 regression tests (73 in total).
- Continuous integration on Python 3.10 to 3.13, release publishing to PyPI, `SECURITY.md`, `CONTRIBUTING.md`, a code of conduct and issue templates.

## 0.7.0 (2026-11-09): security audit

Found by attacking the engine with plans written to leak a restricted value, and by a new noninterference fuzzer.

### Fixed

- **Error messages carried restricted values.** `let x = [0][pin()];` reported `Index 4271 out of range` to whoever read the error. Errors raised on restricted data now withhold their details.
- **The trace revealed restricted control flow.** It recorded which branch ran, how many times a loop ran and the type of restricted values. Those details are now omitted, and steps inside a restricted block are not recorded.
- **Partial effects.** An allowed send went out even when a later statement failed. Sends are now queued and delivered only if the whole plan finishes.
- **`while` condition on later laps.** Re-evaluating the condition depends on the earlier tests, but it ran under the outer label, so an external processor called there (and the trace) could learn how many laps ran. It now runs under the label of the previous tests.

### Added

- `tools/fuzz_noninterference.py`: runs random plans with two different secrets and checks that public sends and the trace match. 6,000 plans pass.
- 8 regression tests (69 in total).

### Known limits

- Abort channel: whether a plan finishes or fails, and at which step, can depend on restricted data.
- External processors run when evaluated, not at commit.

## 0.6.0 (2026-10-04)

Baseline: DFA lexer, LL(1) parser, types, sets and logic, `if`/`while`/`for`, information-flow labels with implicit-flow checks.
