<p align="center">
  <picture>
    <source media="(prefers-color-scheme: dark)" srcset="docs/brand/molly-lang-logo-dark.svg">
    <img src="docs/brand/molly-lang-logo.svg" alt="Molly Lang" height="96">
  </picture>
</p>

# Molly

[![tests](https://github.com/andresD1az/molly-lang/actions/workflows/tests.yml/badge.svg)](https://github.com/andresD1az/molly-lang/actions/workflows/tests.yml)
[![license](https://img.shields.io/badge/license-Apache%202.0-blue.svg)](LICENSE)
![python](https://img.shields.io/badge/python-3.10%2B-blue.svg)
![status](https://img.shields.io/badge/status-alpha-orange.svg)

**Let AI agents write the plan. Keep control of where the data goes.**

**MOLLY — Model Orchestration Language with Labeled Yields.** A small, analyzable language for plans written by AI agents. Every value carries a label with its origin and the recipients allowed to see it, and the engine enforces it at every step.

```text
let order = current_order();          # private: only this customer may see it
let message = draft(order);           # the label follows the data
send customer_whatsapp(message);      # ALLOWED: the owner receives it
send public_web(message);             # BLOCKED before the adapter is ever called
```

## The problem

A customer asks about their order on WhatsApp. Your application authenticates them, builds a context (company and customer) and registers the tools the agent may use. An agent writes a short program that looks up the order, rewrites the text and replies. The agent does **not** decide who the customer is, which model is authorized, or which phone number a sink points to.

The promise: **you can change the plan without giving the agent the ability to change the permissions.**

Prompt injection makes this urgent. If a malicious message convinces the agent to "also post the order to the website", the plan may contain that step, but the engine refuses to run it because the data's label does not allow that recipient.

## Quick start

Python 3.10+, no dependencies. Clone the repository and run:

```bash
python demo.py --case allowed
python demo.py --case web
python demo.py --case branch_leak
python demo.py examples/complete.molly
python -m unittest -v
```

Exit codes: `0` allowed, `1` analysis errors (all of them are listed with line and column), `2` blocked by a permission. The demo adapters use synthetic data: **no real messages are sent, no database is queried and no LLM is called.** The lexer, parser and permission decisions are real code, not hardcoded results.

Other useful flags:

```bash
python demo.py examples/conditional.molly --tree --tokens   # derivation tree and DFA tokens
python demo.py examples/errors.molly                        # every error, with position
python demo.py examples/reply.molly --json                  # everything, including the trace
python demo.py --formal grammar                             # BNF, FIRST/FOLLOW, LL(1) check
```

**Interactive local lab (experimental):** run `python molly_lab/server.py --open` to try programs in a browser editor with tokens, trees, traces and a step debugger. Its documentation is in Spanish for now: [molly_lab/README.md](molly_lab/README.md).

## The language in one minute

```text
let tax = 0.19;                              # constant, type inferred
int count = 0;                               # typed variable, can be reassigned
record order = order_details();
float total = order.total * (1 + tax);

if total > 100000 and order.status in {"shipped", "delivered"} then
  send customer_whatsapp("Total with tax: $" + total);
else
  send customer_whatsapp("Your order is being prepared.");
end

for n in [1 .. 10] do
  count = count + n;
end
```

Types: `int`, `float`, `bool`, `char`, `str`, `list`, `set`, `record`, `null`. Control flow: `if/then/else/end`, `while/do/end`, `for/in/do/end`. Operators include arithmetic, comparisons, `and/or/not/implies/iff`, and set operations (`union`, `intersect`, `-`, `subset`, `in`, `|A|`). Full reference: [docs/SYNTAX.md](docs/SYNTAX.md).

## What the engine guarantees

| Situation | Result | What is checked |
|---|---|---|
| Own order → draft → authenticated customer | Allowed | The reply reaches the adapter |
| Own order → draft → public web | Blocked | Zero calls to the publishing adapter |
| Own order → unauthorized model | Blocked | Zero calls to the external processor |
| Customer Ana → Bruno's source | Blocked | Zero reads from the source |
| Public text + order → public web | Blocked | Concatenation does not erase restrictions |
| Public catalog → draft → public web | Allowed | Public data stays usable |
| Order record → total with tax → customer | Allowed | Arithmetic and structured types keep the label |
| Private status `== "cancelled"` → public text to the web | Blocked | The chosen branch is information too (implicit flow) |
| Count the letters of a private order → publish the count | Blocked | Loops and assignments carry the label |

**Implicit flows.** Choosing a branch or repeating a loop reveals information about its condition. Before an `if`, `while` or `for` runs, the engine checks every send and external processor in the block against the condition's label. Variables the block could reassign inherit that label even if the branch never runs, so the outcome does not depend on the path taken.

## Embedding it in your application

`molly.py` is a library. Tools are registered from trusted code, never from the Molly program.

```python
from molly import Engine, Context, Source, Transform, Sink

# Adapters you implement in your backend:
# fetch_order(ctx), can_read(ctx), write_reply(ctx, text),
# verified_recipient(ctx), send_whatsapp(ctx, text).

engine = Engine(
    sources={
        "current_order": Source(
            load=fetch_order,
            authorize=can_read,
            audience=lambda ctx: frozenset({
                f"customer:{ctx.tenant}:{ctx.subject}",
                "model:authorized",
            }),
        )
    },
    transforms={
        "draft": Transform(run=write_reply, arity=1, processor="model:authorized")
    },
    sinks={
        "customer_whatsapp": Sink(identity=verified_recipient, send=send_whatsapp)
    },
)

# ctx comes from your authenticated session and backend checks.
# Never take tenant or subject from what the agent wrote or from an unverified message.
result = engine.run(agent_program, ctx)
```

This snippet shows the integration contract; the functions it mentions are not implemented here. The runnable example is [demo.py](demo.py). A source adapter must filter its query by the context *before* fetching data: loading everything and labeling it afterwards gives no such guarantee.

Install it with `pip install git+https://github.com/andresD1az/molly-lang`, or copy `molly.py` into your project: it is a single file with no dependencies.

## How it is built

- **Lexer:** a deterministic finite automaton (39 states, 30 symbol classes) run from an explicit transition table. No regex engine.
- **Parser:** LL(1) recursive descent (90 productions, 0 conflicts) with panic-mode error recovery and a full derivation tree.
- **Checks before any effect:** names, scopes, constants, tool arities and record fields.
- **Interpreter:** labels propagate through every operation, and the implicit-flow checks above run on every control structure.
- **Atomic sends:** allowed sends are queued and delivered only if the whole plan finishes, so a plan that fails halfway delivers nothing.
- **Quiet errors and trace:** an error raised on restricted data withholds its details, and the trace does not record which branch ran, how many times a loop ran or the type of restricted values.
- **Bounded work:** every value is limited in total size and depth, so a short program cannot make a comparison or a print run for an unbounded time.
- **Tests:** 73 unit tests, plus a noninterference fuzzer (`python tools/fuzz_noninterference.py 3000`) that runs random plans with two different secrets and checks that a public observer sees the same sends and trace.

The formal definition (DFA, BNF, why the grammar is unambiguous) is in [docs/GRAMMAR.md](docs/GRAMMAR.md); the generated tables are in [docs/TABLES.md](docs/TABLES.md).

## Limits

- No user-defined functions, `break` or `continue` yet.
- Labels are inherited conservatively. A summary does not become public automatically, and there is no declassification operation yet.
- Adapters are trusted. A local function must not send data elsewhere on its own, and external processors must declare their identity.
- **Abort channel.** Whether a plan finishes or fails, and at which step, can depend on restricted data. Sends are atomic (see above), so a recipient sees everything or nothing, and error messages never include restricted values, but that one outcome is still observable. This includes the stop at 10,000 loop iterations.
- A call to an external processor happens when it is evaluated, not at the end, and a sink adapter that fails during delivery does not undo earlier deliveries of the same plan.
- Timing channels are out of scope.
- Prototype limits: 12,000-character programs, 100 statements, 32 nesting levels, 64-bit integers, 4,000-character texts, 1,000-element collections, 10,000 elements in total per value, 25 reported errors. No process isolation, adapter timeouts, persistence or durable audit log.
- Protection depends on the quality of your policies, authentication and adapters. Molly is not a guarantee of total security, general prompt-injection resistance or regulatory compliance.

## Related work

Having an AI agent write a plan in a restricted language while an interpreter controls the data flow is also an active research direction. Examples include CaMeL (*Defeating Prompt Injections by Design*, Google DeepMind and ETH Zurich, 2025) and FIDES (information-flow control for agents, Microsoft, 2025). Molly does not use code from those projects; it shares the general approach, which builds on decades of information-flow-control research.

Molly started as an academic project in a Formal Language Theory course. That version, with a Spanish vocabulary inspired by time travel, lives in a separate repository.

## Security and contributing

Found a way to leak a restricted value? Please report it privately as described in [SECURITY.md](SECURITY.md). For everything else, see [CONTRIBUTING.md](CONTRIBUTING.md) and the [changelog](CHANGELOG.md).

## License

Apache License 2.0. See [LICENSE](LICENSE) and [NOTICE](NOTICE). You may use, modify and redistribute Molly, including commercially, keeping the copyright notice and the NOTICE file. The license includes an explicit patent grant.

## Author

**Eyner Andres Diaz** · [andresdiazd.com](https://andresdiazd.com/)

Academic project team (Formal Language Theory, 2026): Eyner Andres Diaz, Jose Manuel Taborda and Daniel Eduardo Celemin. Developed with the help of AI tools (ChatGPT and Claude); design, decisions and review by the author.
