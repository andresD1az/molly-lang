# Copyright 2026 Eyner Andres Diaz
# SPDX-License-Identifier: Apache-2.0
"""Command line, policy files and dry runs for Molly.

A policy file is JSON written by the operator, never by the agent. It declares
the context, the sources (with fixed sample data), the transforms and the sinks.
Runs are dry: sends are recorded, nothing leaves the process.

    molly check plan.molly
    molly run plan.molly --policy policy.json
"""
import argparse
import json
import sys
from pathlib import Path

from molly import (Context, Engine, MollyError, MollyErrors, Parser, Sink, Source, Transform,
                   __version__, format_tree, lex_all, to_text)

DEFAULT_POLICY = {
    "context": {"tenant": "acme", "subject": "ana"},
    "sources": {
        "current_order": {"data": "Order DEMO-104 for Ana: silver ring, ships tomorrow.",
                          "audience": ["customer:{tenant}:{subject}"]},
        "order_status": {"data": "shipped", "audience": ["customer:{tenant}:{subject}"]},
        "order_details": {"data": {"id": "DEMO-104", "status": "shipped", "total": 120000,
                                   "quantities": [1, 2]},
                          "audience": ["customer:{tenant}:{subject}"]},
        "other_order": {"data": "Order DEMO-207 for Bruno.", "subjects": ["bruno"],
                        "audience": ["customer:{tenant}:bruno"]},
        "public_catalog": {"data": "Silver rings from $120.000 COP.", "audience": None},
    },
    "transforms": {
        "draft": {"arity": 1, "template": "Hi. {0}"},
        "external_model": {"arity": 1, "template": "External summary: {0}",
                           "processor": "model:external"},
    },
    "sinks": {
        "customer_whatsapp": "customer:{tenant}:{subject}",
        "public_web": "web:public",
    },
}


class PolicyError(ValueError):
    pass


def _fill(text, context):
    if not isinstance(text, str):
        raise PolicyError(f"Expected a string, got {text!r}")
    return text.replace("{tenant}", context.tenant).replace("{subject}", context.subject)


def build(policy):
    """Engine, context and outbox from a policy dict. The outbox collects dry-run sends."""
    if not isinstance(policy, dict):
        raise PolicyError("The policy must be a JSON object")
    raw = policy.get("context", {})
    context = Context(str(raw.get("tenant", "")), str(raw.get("subject", "")))
    outbox = []

    def source(name, spec):
        if not isinstance(spec, dict) or "data" not in spec:
            raise PolicyError(f"Source '{name}' needs a 'data' field")
        audience = spec.get("audience")
        label = None if audience is None else frozenset(_fill(a, context) for a in audience)
        subjects = spec.get("subjects")
        return Source(load=lambda ctx: spec["data"],
                      authorize=lambda ctx: subjects is None or ctx.subject in subjects,
                      audience=lambda ctx: label)

    def transform(name, spec):
        if not isinstance(spec, dict) or not isinstance(spec.get("arity"), int):
            raise PolicyError(f"Transform '{name}' needs an integer 'arity'")
        template = spec.get("template")

        def run(ctx, *args):
            texts = [to_text(arg) for arg in args]
            if template is None:
                return " ".join(texts)
            out = template
            for i, text in enumerate(texts):
                out = out.replace("{" + str(i) + "}", text)
            return out
        return Transform(run, spec["arity"], spec.get("processor"))

    def sink(name, identity):
        recipient = _fill(identity, context)
        return Sink(lambda ctx: recipient,
                    lambda ctx, text: outbox.append({"sink": name, "recipient": recipient,
                                                     "text": text}))

    engine = Engine(
        sources={n: source(n, s) for n, s in policy.get("sources", {}).items()},
        transforms={n: transform(n, s) for n, s in policy.get("transforms", {}).items()},
        sinks={n: sink(n, s) for n, s in policy.get("sinks", {}).items()},
    )
    return engine, context, outbox


def describe(policy):
    """What an agent may know to write a plan: tool names, arities and recipients, no data."""
    context = build(policy)[1]
    return {
        "sources": sorted(policy.get("sources", {})),
        "transforms": {n: s["arity"] for n, s in sorted(policy.get("transforms", {}).items())},
        "sinks": {n: _fill(s, context) for n, s in sorted(policy.get("sinks", {}).items())},
    }


def _errors(error):
    return [e.as_dict() for e in (error.errors if isinstance(error, MollyErrors) else [error])]


def check(code):
    """Lexical and syntax analysis only (no tools needed)."""
    try:
        tokens, errors = lex_all(code)
        parser = Parser(tokens)
        parser.parse(raise_errors=False)
        errors += parser.errors
        if errors:
            raise MollyErrors(errors)
        return {"status": "valid", "tokens": [vars(t) for t in tokens],
                "derivation": parser.derivation}
    except MollyError as error:
        return {"status": "rejected", "errors": _errors(error)}


def run(code, policy=None, show_content=True):
    """Dry run. status: allowed | blocked | rejected.

    With show_content=False the delivered texts are omitted: whoever wrote the
    plan (an agent) must not read data addressed to someone else.
    """
    engine, context, outbox = build(DEFAULT_POLICY if policy is None else policy)
    try:
        result = engine.run(code, context)
        status, errors = "allowed", []
    except MollyError as error:
        result = {"trace": engine.trace}
        errors = _errors(error)
        status = "blocked" if errors[0]["phase"] in ("Policy", "Access") else "rejected"
    deliveries = outbox if show_content else [{k: d[k] for k in ("sink", "recipient")}
                                              for d in outbox]
    return {"status": status, "errors": errors, "deliveries": deliveries,
            "trace": result["trace"], "tokens": result.get("tokens"),
            "derivation": result.get("derivation")}


EXIT = {"valid": 0, "allowed": 0, "rejected": 1, "blocked": 2}


def _print(result, args):
    if getattr(args, "tokens", False) and result.get("tokens"):
        for t in result["tokens"]:
            print(f'{t["line"]}:{t["column"]}\t{t["kind"]}\t{t["text"]}')
    if getattr(args, "tree", False) and result.get("derivation"):
        print(format_tree(result["derivation"]))
    print(result["status"].upper())
    for e in result.get("errors", []):
        print(f'  {e["phase"]} [{e["line"]}:{e["column"]}]: {e["message"]}')
    for row in result.get("trace", []):
        if row["operation"] not in ("REJECTED", "BLOCKED"):
            print(f'{row["operation"]}: {row["detail"]}')
    for d in result.get("deliveries", []):
        print(f'Would send to {d["recipient"]} via {d["sink"]}: {d.get("text", "")}')


def main(argv=None):
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(prog="molly", description="Molly language tools")
    parser.add_argument("--version", action="version", version=f"molly {__version__}")
    sub = parser.add_subparsers(dest="command", required=True)
    p_check = sub.add_parser("check", help="lexical and syntax analysis")
    p_run = sub.add_parser("run", help="dry run against a policy")
    p_desc = sub.add_parser("describe", help="tools an agent may use under a policy")
    p_init = sub.add_parser("init-policy", help="print a sample policy file")
    for p in (p_check, p_run):
        p.add_argument("file", type=Path, help="Molly program ('-' reads stdin)")
        p.add_argument("--json", action="store_true")
        p.add_argument("--tokens", action="store_true", help="print the DFA tokens")
        p.add_argument("--tree", action="store_true", help="print the derivation tree")
    for p in (p_run, p_desc):
        p.add_argument("--policy", type=Path, help="policy JSON (default: built-in demo)")
    args = parser.parse_args(argv)

    if args.command == "init-policy":
        print(json.dumps(DEFAULT_POLICY, indent=2, ensure_ascii=False))
        return 0
    try:
        policy = json.loads(args.policy.read_text(encoding="utf-8-sig")) if getattr(
            args, "policy", None) else DEFAULT_POLICY
        if args.command == "describe":
            print(json.dumps(describe(policy), indent=2, ensure_ascii=False))
            return 0
        code = sys.stdin.read() if str(args.file) == "-" else args.file.read_text(encoding="utf-8")
        code = code.lstrip("﻿")  # editors and PowerShell pipes may add a BOM
        result = check(code) if args.command == "check" else run(code, policy)
    except (OSError, json.JSONDecodeError, PolicyError) as error:
        print(f"molly: {error}", file=sys.stderr)
        return 3
    if args.json:
        print(json.dumps(result, indent=2, ensure_ascii=False, default=str))
    else:
        _print(result, args)
    return EXIT[result["status"]]


if __name__ == "__main__":
    raise SystemExit(main())
