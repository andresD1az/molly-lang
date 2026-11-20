# Copyright 2026 Eyner Andres Diaz
# SPDX-License-Identifier: Apache-2.0
"""Molly as an MCP server (stdio, JSON-RPC 2.0, no dependencies).

The agent sends a plan; the server checks it against a policy chosen by the
operator at startup and answers whether it is allowed, blocked or rejected,
and which recipients would receive something. The agent can never pass or
change the policy, and it never sees the delivered texts.

    molly-mcp --policy policy.json
"""
import argparse
import json
import sys
from pathlib import Path

from molly import __version__
from molly_cli import DEFAULT_POLICY, PolicyError, build, check, describe, run

PROTOCOLS = ("2025-06-18", "2025-03-26", "2024-11-05")

SYNTAX = """Molly plan syntax (statements end with ';'):
let x = expr;            constant          int|float|bool|str|list|set|record x = expr;  typed variable
x = expr;                reassign typed     send sink(expr);   deliver to a sink
if cond then ... else ... end      while cond do ... end      for n in [1 .. 10] do ... end
Calls: source() reads data, transform(args) processes it. Operators: + - * / %, == != < <= > >=,
and or not implies iff, in, union intersect subset, |A| (size). Lists [a, b], sets {a, b}, r.field, xs[0].
Every value keeps the recipients allowed to see it; a send to anyone else is blocked."""

TOOLS = [
    {
        "name": "molly_describe",
        "description": "List the sources, transforms (with arity) and sinks (with recipient) "
                       "available to plans, plus the Molly syntax. Call this before writing a plan.",
        "inputSchema": {"type": "object", "properties": {}, "additionalProperties": False},
    },
    {
        "name": "molly_check",
        "description": "Lexical and syntax check of a Molly plan, with every error and its "
                       "line and column. Does not run anything.",
        "inputSchema": {"type": "object", "properties": {"code": {"type": "string"}},
                        "required": ["code"], "additionalProperties": False},
    },
    {
        "name": "molly_run",
        "description": "Dry run of a Molly plan under the server's policy. Returns status "
                       "'allowed', 'blocked' (a value would reach a recipient it is not allowed "
                       "to reach) or 'rejected' (analysis errors), the recipients that would "
                       "receive a message and a redacted trace. Nothing is actually sent.",
        "inputSchema": {"type": "object", "properties": {"code": {"type": "string"}},
                        "required": ["code"], "additionalProperties": False},
    },
]


class Server:
    def __init__(self, policy):
        build(policy)  # fail at startup, not on the first call
        self.policy = policy

    def call_tool(self, name, arguments):
        if name not in {tool["name"] for tool in TOOLS}:
            raise KeyError(name)
        if name == "molly_describe":
            return {**describe(self.policy), "syntax": SYNTAX}
        code = arguments.get("code")
        if not isinstance(code, str):
            raise ValueError("'code' must be a string")
        if name == "molly_check":
            result = check(code)
            result.pop("tokens", None)
            result.pop("derivation", None)
            return result
        if name == "molly_run":
            result = run(code, self.policy, show_content=False)
            for key in ("tokens", "derivation"):
                result.pop(key, None)
            return result
        raise KeyError(name)

    def handle(self, message):
        """Returns the response dict, or None for notifications."""
        method, params, ident = message.get("method"), message.get("params") or {}, message.get("id")
        if ident is None:
            return None
        try:
            if method == "initialize":
                asked = params.get("protocolVersion")
                result = {
                    "protocolVersion": asked if asked in PROTOCOLS else PROTOCOLS[0],
                    "capabilities": {"tools": {}},
                    "serverInfo": {"name": "molly", "version": __version__},
                    "instructions": "Write the agent's plan in Molly and call molly_run before "
                                    "acting. Only perform sends the result reports as allowed.",
                }
            elif method == "ping":
                result = {}
            elif method == "tools/list":
                result = {"tools": TOOLS}
            elif method == "tools/call":
                try:
                    data = self.call_tool(params.get("name"), params.get("arguments") or {})
                except KeyError:
                    return _error(ident, -32602, f"Unknown tool: {params.get('name')}")
                except ValueError as error:
                    return {"jsonrpc": "2.0", "id": ident, "result": {
                        "content": [{"type": "text", "text": str(error)}], "isError": True}}
                result = {"content": [{"type": "text",
                                       "text": json.dumps(data, ensure_ascii=False, default=str)}],
                          "structuredContent": data, "isError": False}
            else:
                return _error(ident, -32601, f"Method not found: {method}")
        except Exception as error:  # never crash the stdio loop
            return _error(ident, -32603, f"Internal error: {type(error).__name__}")
        return {"jsonrpc": "2.0", "id": ident, "result": result}


def _error(ident, code, message):
    return {"jsonrpc": "2.0", "id": ident, "error": {"code": code, "message": message}}


def serve(server, stdin=sys.stdin, stdout=sys.stdout):
    for line in stdin:
        line = line.strip().lstrip("﻿")  # some shells prepend a BOM
        if not line:
            continue
        try:
            message = json.loads(line)
        except json.JSONDecodeError:
            response = _error(None, -32700, "Parse error")
        else:
            response = server.handle(message) if isinstance(message, dict) else \
                _error(None, -32600, "Invalid request")
        if response is not None:
            stdout.write(json.dumps(response, ensure_ascii=False, default=str) + "\n")
            stdout.flush()


def main(argv=None):
    parser = argparse.ArgumentParser(prog="molly-mcp", description="Molly MCP server (stdio)")
    parser.add_argument("--policy", type=Path, help="policy JSON (default: built-in demo)")
    args = parser.parse_args(argv)
    try:
        policy = (json.loads(args.policy.read_text(encoding="utf-8-sig")) if args.policy
                  else DEFAULT_POLICY)
        server = Server(policy)
    except (OSError, json.JSONDecodeError, PolicyError) as error:
        print(f"molly-mcp: {error}", file=sys.stderr)
        return 3
    for stream in (sys.stdin, sys.stdout):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8")
    serve(server)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
