# Copyright 2026 Eyner Andres Diaz
# SPDX-License-Identifier: Apache-2.0
"""Fake adapters with synthetic data; the lexer, parser and permission checks are real."""
import argparse
import json
import sys
from pathlib import Path
from molly import (Context, Source, Transform, Sink, Engine, MollyError, MollyErrors,
                   bnf, dfa_dot, dfa_markdown, first_sets, follow_sets, format_tree,
                   left_recursion, ll1_table, to_text)

CONTEXT = Context("acme", "ana")
CASES = {
    "allowed": 'let order = current_order();\nlet message = draft(order);\nsend customer_whatsapp(message);',
    "web": 'let order = current_order();\nlet message = draft(order);\nsend public_web(message);',
    "model": 'let order = current_order();\nlet message = external_model(order);\nsend customer_whatsapp(message);',
    "other_customer": 'let order = other_order();\nsend customer_whatsapp(order);',
    "concatenate": 'let order = current_order();\nlet copy = "Notice: " + order;\nsend public_web(copy);',
    "public": 'let catalog = public_catalog();\nlet message = draft(catalog);\nsend public_web(message);',
    "conditional": ('let status = order_status();\n'
                    'if status in {"shipped", "delivered"} then\n'
                    '  send customer_whatsapp(draft(current_order()));\n'
                    'else\n'
                    '  send customer_whatsapp("Your order is still being prepared.");\n'
                    'end'),
    "branch_leak": ('if order_status() == "cancelled" then\n'
                    '  send public_web("There was a cancellation");\n'
                    'end'),
    "types": ('record order = order_details();\n'
              'float tax = 0.19;\n'
              'float total = order.total * (1 + tax);\n'
              'int items = order.quantities[0] + order.quantities[1];\n'
              'if total > 100000 and order.status in {"shipped", "delivered"} then\n'
              '  send customer_whatsapp("Order " + order.id + ": " + items\n'
              '                         + " items, total with tax $" + total);\n'
              'end'),
}


def make_engine():
    counters = {"reads": 0, "external_model": 0, "sends": 0}
    outbox = []
    def load_order(ctx):
        counters["reads"] += 1
        return "Order DEMO-104 for Ana: silver ring, ships tomorrow."
    def external(ctx, text):
        counters["external_model"] += 1
        return "External summary: " + text
    def deliver(ctx, text):
        counters["sends"] += 1
        outbox.append(text)
    def allowed(ctx):
        return frozenset({f"customer:{ctx.tenant}:{ctx.subject}"})
    engine = Engine(
        sources={
            "current_order": Source(load_order, lambda ctx: ctx == CONTEXT, allowed),
            "order_status": Source(lambda ctx: "shipped", lambda ctx: ctx == CONTEXT, allowed),
            "other_order": Source(load_order, lambda ctx: ctx == Context("acme", "bruno"),
                                  lambda ctx: frozenset({"customer:acme:bruno"})),
            "public_catalog": Source(lambda ctx: "Silver rings from $120.000 COP.",
                                     lambda ctx: ctx == CONTEXT, lambda ctx: None),
            # A record: structured types carry labels too.
            "order_details": Source(lambda ctx: {"id": "DEMO-104", "status": "shipped",
                                                 "total": 120000, "quantities": [1, 2]},
                                    lambda ctx: ctx == CONTEXT, allowed),
        },
        transforms={
            # Deliberately local: no model, credentials, Internet or paid calls.
            "draft": Transform(lambda ctx, value: "Hi. " + to_text(value), arity=1),
            "external_model": Transform(external, arity=1, processor="model:external"),
        },
        sinks={
            "customer_whatsapp": Sink(lambda ctx: f"customer:{ctx.tenant}:{ctx.subject}", deliver),
            "public_web": Sink(lambda ctx: "web:public", deliver),
        },
    )
    return engine, counters, outbox


def execute(code):
    engine, counters, outbox = make_engine()
    try:
        result = engine.run(code, CONTEXT)
        return {"ok": True, "code": code, **result, "counters": counters, "outbox": outbox}
    except MollyError as error:
        listed = error.errors if isinstance(error, MollyErrors) else [error]
        return {"ok": False, "code": code, "error": str(error),
                "errors": [item.as_dict() for item in listed], "trace": engine.trace,
                "counters": counters, "outbox": outbox}


def print_formal(what):
    if what == "dfa":
        print(dfa_markdown())
    elif what == "dot":
        print(dfa_dot())
    else:
        first = first_sets()
        follow = follow_sets(first=first)
        table, conflicts = ll1_table()
        print(bnf(), "\n")
        print("| Nonterminal | FIRST | FOLLOW |\n|---|---|---|")
        for name in first:
            print(f"| {name} | {', '.join(sorted(first[name]))} | {', '.join(sorted(follow[name]))} |")
        print(f"\nLL(1) table entries: {len(table)}. Conflicts: {len(conflicts)}. "
              f"Left-recursion cycles: {len(left_recursion())}.")
        for name, terminal, old, new in conflicts:
            print(f"  conflict M[{name}, {terminal}]: {old} / {new}")


def main():
    sys.stdout.reconfigure(encoding="utf-8")  # → ε └── on cp1252 consoles and redirects
    parser = argparse.ArgumentParser(description="Molly: runnable demo with synthetic data")
    parser.add_argument("file", nargs="?", type=Path)
    parser.add_argument("--case", choices=CASES, default="allowed")
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--tree", action="store_true", help="print the derivation tree")
    parser.add_argument("--tokens", action="store_true", help="print the DFA tokens")
    parser.add_argument("--formal", choices=["dfa", "dot", "grammar"],
                        help="print the DFA matrix, its DOT graph, or FIRST/FOLLOW/LL(1)")
    parser.add_argument("--export-cases", type=Path)
    args = parser.parse_args()
    if args.formal:
        print_formal(args.formal)
        return 0
    if args.export_cases:
        args.export_cases.write_text(json.dumps({k: execute(v) for k, v in CASES.items()},
                                                ensure_ascii=False, indent=2), encoding="utf-8")
        return 0
    result = execute(args.file.read_text(encoding="utf-8") if args.file else CASES[args.case])
    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        if args.tokens and "tokens" in result:
            for token in result["tokens"]:
                print(f'{token["line"]}:{token["column"]}\t{token["kind"]}\t{token["text"]}')
        if args.tree and "derivation" in result:
            print(format_tree(result["derivation"]))
        if result["ok"]:
            print("ALLOWED")
        elif result["errors"][0]["phase"] in ("Policy", "Access"):
            print("BLOCKED")
        else:
            print(f"REJECTED: {len(result['errors'])} analysis error(s)")
            for item in result["errors"]:
                print(f'  {item["phase"]} [{item["line"]}:{item["column"]}]: {item["message"]}')
        for row in result["trace"]:
            if row["operation"] != "REJECTED":  # already listed above
                print(f'{row["operation"]}: {row["detail"]}')
        print("Adapter calls:", result["counters"])
        for message in result["outbox"]:
            print("Simulated output:", message)
    if result["ok"]:
        return 0
    return 2 if result["errors"][0]["phase"] in ("Policy", "Access") else 1


if __name__ == "__main__":
    raise SystemExit(main())
