# Copyright 2026 Eyner Andres Diaz
# SPDX-License-Identifier: Apache-2.0
"""Tests for the command line, policy files and the MCP server."""
import io
import json
import unittest
from contextlib import redirect_stdout

import molly_cli
from molly_cli import DEFAULT_POLICY, PolicyError, build, check, describe, run
from molly_mcp import Server, serve

ALLOWED = 'let o = current_order();\nsend customer_whatsapp(draft(o));'
LEAK = 'let o = current_order();\nsend public_web(draft(o));'


class PolicyTests(unittest.TestCase):
    def test_allowed_plan_records_the_delivery(self):
        result = run(ALLOWED)
        self.assertEqual(result["status"], "allowed")
        self.assertEqual(result["deliveries"][0]["recipient"], "customer:acme:ana")
        self.assertIn("DEMO-104", result["deliveries"][0]["text"])

    def test_leak_is_blocked_and_nothing_is_delivered(self):
        result = run(LEAK)
        self.assertEqual(result["status"], "blocked")
        self.assertEqual(result["deliveries"], [])

    def test_analysis_errors_are_rejected(self):
        self.assertEqual(run("let = ;")["status"], "rejected")
        self.assertEqual(check("let = ;")["status"], "rejected")
        self.assertEqual(check(ALLOWED)["status"], "valid")

    def test_hidden_content_for_the_agent(self):
        result = run(ALLOWED, show_content=False)
        self.assertNotIn("text", result["deliveries"][0])

    def test_placeholders_and_subject_authorization(self):
        policy = json.loads(json.dumps(DEFAULT_POLICY))
        policy["context"]["subject"] = "bruno"
        self.assertEqual(run('send customer_whatsapp(other_order());', policy)["status"], "allowed")
        self.assertEqual(run('send customer_whatsapp(current_order());', policy)["status"],
                         "allowed")  # audience follows {subject}
        policy["context"]["subject"] = "ana"
        self.assertEqual(run('send customer_whatsapp(other_order());', policy)["status"], "blocked")

    def test_bad_policy_is_reported(self):
        with self.assertRaises(PolicyError):
            build({"sources": {"x": {}}})
        with self.assertRaises(PolicyError):
            build({"transforms": {"t": {"arity": "1"}}})

    def test_describe_shows_no_data(self):
        text = json.dumps(describe(DEFAULT_POLICY))
        self.assertNotIn("DEMO-104", text)
        self.assertIn("customer_whatsapp", text)

    def test_cli_exit_codes(self):
        out = io.StringIO()
        with redirect_stdout(out):
            self.assertEqual(molly_cli.main(["init-policy"]), 0)
        self.assertEqual(json.loads(out.getvalue()), DEFAULT_POLICY)
        self.assertEqual(molly_cli.EXIT["blocked"], 2)


class McpTests(unittest.TestCase):
    def exchange(self, *messages):
        stdin = io.StringIO("\n".join(json.dumps(m) for m in messages) + "\n")
        stdout = io.StringIO()
        serve(Server(DEFAULT_POLICY), stdin, stdout)
        return [json.loads(line) for line in stdout.getvalue().splitlines()]

    def test_handshake_and_tool_list(self):
        replies = self.exchange(
            {"jsonrpc": "2.0", "id": 1, "method": "initialize",
             "params": {"protocolVersion": "2025-03-26", "capabilities": {}}},
            {"jsonrpc": "2.0", "method": "notifications/initialized"},
            {"jsonrpc": "2.0", "id": 2, "method": "tools/list"})
        self.assertEqual(len(replies), 2)  # notifications get no reply
        self.assertEqual(replies[0]["result"]["protocolVersion"], "2025-03-26")
        names = [t["name"] for t in replies[1]["result"]["tools"]]
        self.assertEqual(names, ["molly_describe", "molly_check", "molly_run"])

    def test_run_blocks_a_leak_and_hides_texts(self):
        replies = self.exchange(
            {"jsonrpc": "2.0", "id": 1, "method": "tools/call",
             "params": {"name": "molly_run", "arguments": {"code": LEAK}}},
            {"jsonrpc": "2.0", "id": 2, "method": "tools/call",
             "params": {"name": "molly_run", "arguments": {"code": ALLOWED}}})
        self.assertEqual(replies[0]["result"]["structuredContent"]["status"], "blocked")
        allowed = replies[1]["result"]
        self.assertEqual(allowed["structuredContent"]["status"], "allowed")
        self.assertNotIn("DEMO-104", allowed["content"][0]["text"])

    def test_agent_cannot_pass_a_policy(self):
        policy = {"sinks": {"public_web": "customer:acme:ana"}}
        replies = self.exchange(
            {"jsonrpc": "2.0", "id": 1, "method": "tools/call",
             "params": {"name": "molly_run", "arguments": {"code": LEAK, "policy": policy}}})
        self.assertEqual(replies[0]["result"]["structuredContent"]["status"], "blocked")

    def test_errors(self):
        replies = self.exchange(
            {"jsonrpc": "2.0", "id": 1, "method": "nope"},
            {"jsonrpc": "2.0", "id": 2, "method": "tools/call", "params": {"name": "x"}},
            {"jsonrpc": "2.0", "id": 3, "method": "tools/call",
             "params": {"name": "molly_run", "arguments": {"code": 5}}})
        self.assertEqual(replies[0]["error"]["code"], -32601)
        self.assertEqual(replies[1]["error"]["code"], -32602)
        self.assertTrue(replies[2]["result"]["isError"])


if __name__ == "__main__":
    unittest.main()
