# Changelog

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
