# Copyright 2026 Eyner Andres Diaz
# SPDX-License-Identifier: Apache-2.0
import re
import unittest
from molly import (Engine, Source, Transform, Sink, Context, MollyError, Parser, lex, lex_all,
                   REGULAR_EXPRESSIONS, KEYWORDS, TRANSITIONS, CLASSES, ACCEPTING, GRAMMAR,
                   first_sets, follow_sets, ll1_table, left_recursion, format_tree)
from demo import CASES, CONTEXT, execute, make_engine

ORDER_TEXT = "Order DEMO-104 for Ana: silver ring, ships tomorrow."


class FunctionalTests(unittest.TestCase):
    def test_allowed_reply(self):
        result = execute(CASES["allowed"])
        self.assertTrue(result["ok"])
        self.assertEqual(result["counters"]["sends"], 1)
        self.assertIn("DEMO-104", result["outbox"][0])

    def test_public_data_can_leave(self):
        self.assertTrue(execute(CASES["public"])["ok"])

    def test_web_never_called(self):
        result = execute(CASES["web"])
        self.assertFalse(result["ok"])
        self.assertEqual(result["counters"]["sends"], 0)
        self.assertIn("current_order → draft", result["error"])

    def test_model_never_receives_secret(self):
        result = execute(CASES["model"])
        self.assertFalse(result["ok"])
        self.assertEqual(result["counters"]["external_model"], 0)
        self.assertEqual(result["counters"]["sends"], 0)

    def test_other_customer_not_retrieved(self):
        result = execute(CASES["other_customer"])
        self.assertFalse(result["ok"])
        self.assertEqual(result["counters"]["reads"], 0)

    def test_concat_and_alias_do_not_declassify(self):
        self.assertFalse(execute(CASES["concatenate"])["ok"])
        result = execute('let a = current_order(); let b = a; send public_web(b);')
        self.assertFalse(result["ok"])
        self.assertEqual(result["counters"]["sends"], 0)

    def test_preflight_catches_error_before_valid_send(self):
        for suffix in ['let b = missing();', 'let b = draft();',
                       'send public_web(undeclared);', 'let a = "duplicate";']:
            with self.subTest(suffix=suffix):
                result = execute('let a = "hello"; send public_web(a); ' + suffix)
                self.assertFalse(result["ok"])
                self.assertEqual(result["counters"]["sends"], 0)

    def test_syntax_location(self):
        result = execute('let a = "hello";\nsend public_web(a)')
        self.assertFalse(result["ok"])
        self.assertIn("[2:19]", result["error"])

    def test_no_general_python_execution(self):
        for code in ['import os;', 'let a = obj.secret;', 'let a = __import__("os");']:
            with self.subTest(code=code):
                self.assertFalse(execute(code)["ok"])

    def test_nesting_comments_and_escapes(self):
        result = execute('# comment\nlet a = draft(draft("Hello\\nAna")); send public_web(a);')
        self.assertTrue(result["ok"])
        self.assertEqual(result["outbox"], ["Hi. Hi. Hello\nAna"])

    def test_derivation_terminals_match_lexer(self):
        tokens = lex(CASES["allowed"])
        parser = Parser(tokens)
        parser.parse()
        terminals = []
        def walk(tree):
            if "terminal" in tree and tree["terminal"] != "ε":
                terminals.append((tree["terminal"], tree["lexeme"]))
            for child in tree.get("children", []):
                walk(child)
        walk(parser.derivation)
        self.assertEqual(terminals, [(t.kind, t.text) for t in tokens])

    def test_empty_intersection_is_not_public(self):
        ctx = Context("x", "a")
        received = []
        engine = Engine({
            "a": Source(lambda ctx: "secret A", lambda ctx: True, lambda ctx: frozenset({"A"})),
            "b": Source(lambda ctx: "secret B", lambda ctx: True, lambda ctx: frozenset({"B"})),
        }, {}, {"out": Sink(lambda ctx: "A", lambda ctx, text: received.append(text))})
        with self.assertRaises(MollyError):
            engine.run('let data = a() + b(); send out(data);', ctx)
        self.assertEqual(received, [])

    def test_wrong_tenant_cannot_read(self):
        engine, counters, _ = make_engine()
        with self.assertRaises(MollyError):
            engine.run(CASES["allowed"], Context("other_company", "ana"))
        self.assertEqual(counters["reads"], 0)

    def test_adapter_errors_do_not_expose_contents(self):
        def bad(ctx):
            raise ValueError("secret that must not leak")
        engine = Engine({"a": Source(bad, lambda ctx: True, lambda ctx: None)}, {}, {})
        with self.assertRaises(MollyError) as captured:
            engine.run('let a = a();', CONTEXT)
        self.assertNotIn("secret", str(captured.exception))

    def test_resource_bounds(self):
        for code in ['let a = "' + 'x' * 12000 + '";', 'let a = ' + 'draft(' * 34 + '"a"' + ')' * 34 + ';']:
            with self.subTest(length=len(code)):
                self.assertFalse(execute(code)["ok"])

    def test_long_expressions_and_arguments_are_limits_before_effects(self):
        for expression in [' + '.join(['"a"'] * 1100), 'draft(' + ','.join(['"a"'] * 1100) + ')']:
            with self.subTest(expression=expression[:40]):
                result = execute('send public_web("hello"); let a = ' + expression + ';')
                self.assertFalse(result["ok"])
                self.assertIn("Limit", result["error"])
                self.assertEqual(result["counters"]["sends"], 0)

    def test_literal_output_limit(self):
        for size, allowed in [(4000, True), (4001, False)]:
            with self.subTest(size=size):
                result = execute('send public_web("' + 'a' * size + '");')
                self.assertEqual(result["ok"], allowed)
                self.assertEqual(result["counters"]["sends"], int(allowed))
                if not allowed:
                    self.assertIn("Limit", result["error"])

    def test_expression_limit_boundary(self):
        for count, allowed in [(100, True), (101, False)]:
            with self.subTest(count=count):
                result = execute('let a = ' + ' + '.join(['"a"'] * count) + ';')
                self.assertEqual(result["ok"], allowed)


class LexicalAutomatonTests(unittest.TestCase):
    def kinds(self, code):
        return [token.kind for token in lex(code)][:-1]

    def test_matrix_is_deterministic_over_the_alphabet_classes(self):
        for state, cells in TRANSITIONS.items():
            self.assertTrue(set(cells) <= set(CLASSES), state)
            self.assertTrue(set(cells.values()) <= set(TRANSITIONS), state)
        self.assertTrue(set(ACCEPTING) <= set(TRANSITIONS))

    def test_maximal_munch_and_keywords(self):
        self.assertEqual(self.kinds('a == b = c != d'),
                         ["IDENT", "==", "IDENT", "=", "IDENT", "!=", "IDENT"])
        self.assertEqual(self.kinds('letter let lets in then'),
                         ["IDENT", "let", "IDENT", "in", "then"])
        self.assertEqual(self.kinds('{ "x", "y" } # note'), ["{", "STRING", ",", "STRING", "}"])

    def test_dfa_agrees_with_regular_expressions(self):
        samples = ['abc_1', 'nt', '_', '""', '"a\\"b"', '"\\\\ \\n \\t ñ €"', '=', '==', '!=',
                   '<', '<=', '>', '>=', ';', '+', '-', '*', '/', '%', '(', ')', '[', ']', '{',
                   '}', ',', '.', ':', '|', '..', '0', '2026', '3.14', "'a'", "'\\n'", "'ñ'", "'\"'"]
        for sample in samples:
            with self.subTest(sample=sample):
                tokens = lex(sample)
                self.assertEqual(len(tokens), 2)
                kind = "IDENT" if tokens[0].text in KEYWORDS else tokens[0].kind
                self.assertTrue(re.fullmatch(REGULAR_EXPRESSIONS[kind], sample))

    def test_rejected_inputs_report_cause(self):
        cases = {"''": "Empty char", "'ab'": "single symbol", "'\\q'": "escape", "'a": "Unterminated",
                 '"open': "Unterminated", '"\\q"': "escape", '!': "'='",
                 '@': "alphabet", 'a \\ b': "inside a string"}
        for code, fragment in cases.items():
            with self.subTest(code=code):
                _, errors = lex_all(code)
                self.assertEqual(len(errors), 1)
                self.assertIn(fragment, errors[0].message)

    def test_lexer_lists_every_error(self):
        _, errors = lex_all('let a = "x" @;\nlet b = \'\';\nlet c = "\\z";')
        self.assertEqual([(e.line, e.column) for e in errors], [(1, 13), (2, 9), (3, 9)])

    def test_range_token(self):
        self.assertEqual(self.kinds("[1..5]"), ["[", "INT", "..", "INT", "]"])
        self.assertEqual(self.kinds("1.5 3.x"), ["FLOAT", "INT", ".", "IDENT"])


class GrammarTests(unittest.TestCase):
    def test_grammar_is_ll1_and_not_left_recursive(self):
        self.assertEqual(ll1_table()[1], [])
        self.assertEqual(left_recursion(), [])

    def test_original_forms_are_rejected_by_the_same_checks(self):
        recursive = dict(GRAMMAR, Sum=[["Sum", "+", "Term"], ["Term"]])
        self.assertTrue(left_recursion(recursive))
        self.assertTrue(ll1_table(recursive)[1])
        unfactored = dict(GRAMMAR, Primary=[["STRING"], ["IDENT"], ["IDENT", "(", "Arguments", ")"]])
        self.assertTrue(ll1_table(unfactored)[1])

    def test_first_and_follow(self):
        first, follow = first_sets(), follow_sets()
        self.assertEqual(first["Statement"], {"let", "send", "if", "while", "for", "IDENT", "int",
                                              "float", "bool", "char", "str", "list", "set",
                                              "record"})
        self.assertEqual(follow["Statements"], {"EOF", "else", "end"})
        self.assertEqual(follow["Relation"], {"and", "or", "implies", "iff", ";", ")", "]", "}",
                                              ",", "|", "..", "then", "do"})
        self.assertEqual(first["Factor"], {"-", "INT", "FLOAT", "STRING", "CHAR", "true", "false",
                                           "null", "IDENT", "(", "[", "{", "record", "|"})


class ParserTests(unittest.TestCase):
    def test_syntax_errors_are_all_listed(self):
        result = execute('let a = ;\nlet b = "ok";\nsend public_web(b\nlet c = "x";\nend')
        self.assertFalse(result["ok"])
        self.assertEqual([(e["line"], e["phase"]) for e in result["errors"]],
                         [(1, "Syntax"), (4, "Syntax"), (5, "Syntax")])
        self.assertEqual(result["counters"]["sends"], 0)

    def test_semantic_errors_are_all_listed(self):
        result = execute('let a = x; let b = draft(); send nobody("c"); let a = "d";')
        self.assertEqual(len(result["errors"]), 4)

    def test_derivation_tree_for_conditional(self):
        parser = Parser(lex(CASES["conditional"]))
        parser.parse()
        text = format_tree(parser.derivation)
        for production in ["<Relation>", "<RelOp>", "<Elements>", "<Else>", "<Postfix>"]:
            self.assertIn(production, text)

    def test_unclosed_conditional_and_stray_keywords(self):
        for code in ['if "a" == "a" then send public_web("x");', 'end', 'else end',
                     'if "a" then send public_web("x"); end']:
            with self.subTest(code=code):
                result = execute(code)
                self.assertFalse(result["ok"])
                self.assertEqual(result["counters"]["sends"], 0)


class ConditionalTests(unittest.TestCase):
    def test_membership_selects_branch(self):
        result = execute(CASES["conditional"])
        self.assertTrue(result["ok"])
        self.assertIn("DEMO-104", result["outbox"][0])

    def test_else_branch_operators_and_nesting(self):
        cases = [
            ('if "a" == "b" then send public_web("1"); else send public_web("2"); end', ["2"]),
            ('if "a" != "b" then send public_web("1"); end', ["1"]),
            ('if "a" in {} then send public_web("1"); else send public_web("3"); end', ["3"]),
            ('if "a" in {"a"} then if "c" in {"b"} then send public_web("4"); end end', []),
        ]
        for code, expected in cases:
            with self.subTest(code=code):
                result = execute(code)
                self.assertTrue(result["ok"])
                self.assertEqual(result["outbox"], expected)

    def test_branch_on_secret_cannot_reach_public_sink(self):
        for value in ["shipped", "other"]:  # blocked whichever branch is taken
            with self.subTest(value=value):
                result = execute(f'if order_status() == "{value}" then send public_web("yes"); '
                                 'else send public_web("no"); end')
                self.assertFalse(result["ok"])
                self.assertIn("condition", result["error"])
                self.assertEqual(result["counters"]["sends"], 0)

    def test_branch_on_secret_cannot_reach_external_model(self):
        result = execute('if order_status() == "x" then let a = external_model("hello"); end')
        self.assertFalse(result["ok"])
        self.assertEqual(result["counters"]["external_model"], 0)

    def test_branch_on_secret_can_answer_its_owner(self):
        result = execute('if order_status() == "shipped" then send customer_whatsapp("On its way"); end')
        self.assertTrue(result["ok"])
        self.assertEqual(result["outbox"], ["On its way"])

    def test_branch_declarations_do_not_escape(self):
        result = execute('if "a" == "a" then let x = "1"; end send public_web(x);')
        self.assertIn("Undeclared variable", result["error"])
        result = execute('let x = "0"; if "a" == "a" then let x = "1"; end')
        self.assertIn("already declared", result["error"])


class DataTypeTests(unittest.TestCase):
    def value_of(self, expression, declared="let"):
        result = execute(f"{declared} x = {expression}; send public_web(x);")
        self.assertTrue(result["ok"], result.get("error"))
        return result["outbox"][0]

    def test_literals_of_every_type(self):
        cases = {"42": "42", "3.5": "3.5", "true": "true", "false": "false", "null": "null",
                 "'a'": "a", '"hello"': "hello", '[1, "two", 3.0]': '[1, "two", 3.0]',
                 "{1, 2, 2, 1}": "{1, 2}", "{}": "{}", "[]": "[]", "[[1], [2]]": "[[1], [2]]",
                 'record {n: "Ana", a: 20}': 'record {n: "Ana", a: 20}'}
        for expression, expected in cases.items():
            with self.subTest(expression=expression):
                self.assertEqual(self.value_of(expression), expected)

    def test_arithmetic_and_precedence(self):
        cases = {"1 + 2 * 3": "7", "(1 + 2) * 3": "9", "10 - 4 - 3": "3", "7 / 2": "3.5",
                 "7 % 3": "1", "-2 * -3": "6", "2 + 0.5": "2.5", "-(1 + 1)": "-2"}
        for expression, expected in cases.items():
            with self.subTest(expression=expression):
                self.assertEqual(self.value_of(expression), expected)

    def test_logic_and_comparisons(self):
        cases = {"1 < 2 and 2 < 3": "true", "not 1 == 1 or false": "false",
                 "not (1 == 2)": "true", "1 == 1.0": "true", "1 == true": "false",
                 "'a' == \"a\"": "false", '"abc" < "abd"': "true", "2 in [1, 2]": "true",
                 '"b" in {"a"}': "false", "'o' in \"hello\"": "true",
                 "[1, 2] == [1, 2]": "true", "{1, 2} == {2, 1}": "true"}
        for expression, expected in cases.items():
            with self.subTest(expression=expression):
                self.assertEqual(self.value_of(expression), expected)

    def test_access_and_concatenation(self):
        cases = {"[10, 20][1]": "20", '"hello"[0]': "h", "record {a: [1, 2]}.a[1]": "2",
                 '"Total: " + 5': "Total: 5", "[1] + [2]": "[1, 2]", "'a' + 'b'": "ab"}
        for expression, expected in cases.items():
            with self.subTest(expression=expression):
                self.assertEqual(self.value_of(expression), expected)

    def test_typed_declarations(self):
        self.assertEqual(self.value_of("5", "int"), "5")
        self.assertEqual(self.value_of("5", "float"), "5.0")
        self.assertEqual(self.value_of("null", "record"), "null")
        for expression, declared in [('"5"', "int"), ("null", "int"), ("1", "bool"),
                                     ("[1]", "set"), ("'a'", "str")]:
            with self.subTest(expression=expression, declared=declared):
                result = execute(f"{declared} x = {expression};")
                self.assertFalse(result["ok"])
                self.assertEqual(result["errors"][0]["phase"], "Type")

    def test_runtime_errors(self):
        cases = {"1 / 0": "Division by zero", "[1][5]": "out of range", "null.a": "null",
                 "record {a: 1}.b": "field", '"a" - 1': "does not apply",
                 "1 and true": "bools", "{[1]}": "simple values",
                 '1 < "a"': "Cannot order", "9223372036854775807 + 1": "64-bit",
                 "99999999999999999999": "64-bit"}
        for expression, fragment in cases.items():
            with self.subTest(expression=expression):
                result = execute(f'send public_web("start"); let x = {expression};')
                self.assertFalse(result["ok"])
                self.assertIn(fragment, result["error"])

    def test_condition_must_be_boolean(self):
        result = execute('if 1 then send public_web("x"); end')
        self.assertIn("bool", result["error"])
        self.assertEqual(result["counters"]["sends"], 0)

    def test_relations_are_not_associative(self):
        result = execute("let x = 1 < 2 < 3;")
        self.assertEqual(result["errors"][0]["phase"], "Syntax")

    def test_labels_follow_every_operation(self):
        for expression in ["[current_order()]", "record {p: current_order()}",
                           "order_details().total * 2", "order_details().total > 0",
                           "{order_status()}", "current_order()[0]"]:
            with self.subTest(expression=expression):
                result = execute(f"let x = {expression}; send public_web(x);")
                self.assertFalse(result["ok"])
                self.assertEqual(result["errors"][0]["phase"], "Policy")
                self.assertEqual(result["counters"]["sends"], 0)

    def test_record_from_source_reaches_its_owner(self):
        result = execute(CASES["types"])
        self.assertTrue(result["ok"], result.get("error"))
        self.assertEqual(result["counters"]["sends"], 1)

    def test_adapters_receive_immutable_values(self):
        received = []
        engine = Engine({}, {"take": Transform(lambda ctx, v: received.append(v) or "ok", arity=1)},
                        {"s": Sink(lambda ctx: "x", lambda ctx, text: None)})
        engine.run("let r = take(record {a: [1, 2]});", CONTEXT)
        with self.assertRaises(TypeError):
            received[0]["a"] = 3


class SetAndLogicTests(unittest.TestCase):
    """Set operations and propositional-logic connectives."""

    def value_of(self, expression):
        result = execute(f"let x = {expression}; send public_web(x);")
        self.assertTrue(result["ok"], result.get("error"))
        return result["outbox"][0]

    def test_set_operations(self):
        cases = {"{1, 2} union {2, 3}": "{1, 2, 3}", "{1, 2, 3} intersect {2, 3, 4}": "{2, 3}",
                 "{1, 2, 3} - {2}": "{1, 3}", "{1} subset {1, 2}": "true",
                 "{3} subset {1, 2}": "false", "{} subset {}": "true",
                 "|{1, 2, 2}|": "2", "|{}|": "0", '|"hello"|': "5", "|[1, [2, 3]]|": "2",
                 "{1} union {2} intersect {2}": "{1, 2}", "({1} union {2}) intersect {2}": "{2}"}
        for expression, expected in cases.items():
            with self.subTest(expression=expression):
                self.assertEqual(self.value_of(expression), expected)

    def test_truth_table_of_connectives(self):
        literal = {True: "true", False: "false"}
        for p in (True, False):
            for q in (True, False):
                for operator, expected in [("implies", (not p) or q), ("iff", p == q),
                                           ("and", p and q), ("or", p or q)]:
                    with self.subTest(p=p, operator=operator, q=q):
                        self.assertEqual(self.value_of(f"{literal[p]} {operator} {literal[q]}"),
                                         literal[expected])

    def test_connective_precedence(self):
        self.assertEqual(self.value_of("false or true implies false"), "false")  # (F or T) → F
        self.assertEqual(self.value_of("not true iff false"), "true")
        result = execute("let x = true implies false implies true;")
        self.assertEqual(result["errors"][0]["phase"], "Syntax")  # → does not chain without parentheses

    def test_set_operations_require_sets(self):
        for expression in ["[1] union [2]", "{1} intersect 2", "|5|", "1 implies true",
                           "[1] subset {1}"]:
            with self.subTest(expression=expression):
                result = execute(f"let x = {expression};")
                self.assertEqual(result["errors"][0]["phase"], "Type")

    def test_typed_and_inferred_declarations_mix(self):
        result = execute("int a = 2; let b = a * 3; set c = {a, b}; send public_web(|c|);")
        self.assertEqual(result["outbox"], ["2"])


class LoopTests(unittest.TestCase):
    """while, for, assignment and ranges."""

    def outbox(self, code):
        result = execute(code)
        self.assertTrue(result["ok"], result.get("error"))
        return result["outbox"]

    def test_while_loop(self):
        self.assertEqual(self.outbox("int i = 0; int total = 0; while i < 5 do "
                                     "total = total + i; i = i + 1; end send public_web(total);"),
                         ["10"])
        self.assertEqual(self.outbox("while false do send public_web(1); end"), [])

    def test_for_loop_over_collections_and_ranges(self):
        self.assertEqual(self.outbox("int s = 0; for x in [1 .. 10] do s = s + x; end "
                                     "send public_web(s);"), ["55"])
        self.assertEqual(self.outbox('for c in "hola" do send public_web(c); end'),
                         ["h", "o", "l", "a"])
        self.assertEqual(self.outbox("for n in {3, 1, 3} do send public_web(n); end"), ["3", "1"])
        self.assertEqual(self.outbox("send public_web([5 .. 1]); send public_web({1 .. 3});"),
                         ["[]", "{1, 2, 3}"])

    def test_nested_loops_and_block_scope(self):
        self.assertEqual(self.outbox("int t = 0; for i in [1 .. 3] do for j in [1 .. i] do "
                                     "int p = i * j; t = t + p; end end send public_web(t);"),
                         ["25"])

    def test_assignment_rules(self):
        cases = {"let k = 1; k = 2;": "constant", "x = 3;": "Undeclared",
                 "for x in [1] do x = 2; end": "constant",
                 "for x in [1] do let x = 3; end": "already declared"}
        for code, fragment in cases.items():
            with self.subTest(code=code):
                result = execute(code)
                self.assertEqual(result["errors"][0]["phase"], "Semantic")
                self.assertIn(fragment, result["error"])
        result = execute('int i = 0; i = "a";')
        self.assertEqual(result["errors"][0]["phase"], "Type")

    def test_limits_and_types(self):
        result = execute("int i = 0; while true do i = i + 1; end")
        self.assertIn("iterations", result["error"])
        for code in ["for x in 5 do end", "while 1 do end", 'let r = [1 .. "a"];']:
            with self.subTest(code=code):
                self.assertEqual(execute(code)["errors"][0]["phase"], "Type")
        self.assertIn("Limit", execute("let r = [1 .. 5000];")["error"])

    def test_loop_over_secret_cannot_publish_what_it_counted(self):
        result = execute("int n = 0; for c in current_order() do n = n + 1; end send public_web(n);")
        self.assertEqual(result["errors"][0]["phase"], "Policy")
        self.assertEqual(result["counters"]["sends"], 0)
        self.assertEqual(self.outbox("int n = 0; for c in current_order() do n = n + 1; end "
                                     "send customer_whatsapp(n);"), [str(len(ORDER_TEXT))])

    def test_while_on_secret_blocks_public_effects(self):
        result = execute('while order_status() == "shipped" do send public_web("x"); end')
        self.assertEqual(result["errors"][0]["phase"], "Policy")
        self.assertEqual(result["counters"]["sends"], 0)

    def test_variable_assigned_in_branch_not_taken_is_still_protected(self):
        # The branch does not run, but f still being false reveals the condition.
        result = execute('bool f = false; if order_status() == "other" then f = true; end '
                         'send public_web(f);')
        self.assertEqual(result["errors"][0]["phase"], "Policy")
        self.assertEqual(result["counters"]["sends"], 0)


class AuditTests(unittest.TestCase):
    """Regression tests for the leaks found in the 0.7 security audit."""

    def test_sends_are_atomic(self):
        # An allowed send must not go out when a later statement fails.
        result = execute('send public_web("first"); let x = 1 / 0; send public_web("second");')
        self.assertFalse(result["ok"])
        self.assertEqual(result["counters"]["sends"], 0)
        self.assertEqual(result["outbox"], [])

    def test_sends_keep_their_order(self):
        result = execute('send public_web("a"); send public_web("b");')
        self.assertEqual(result["outbox"], ["a", "b"])

    def test_error_on_restricted_data_withholds_details(self):
        result = execute("let o = order_details(); let x = [0][o.total];")
        self.assertEqual(result["errors"][0]["phase"], "Runtime")
        self.assertNotIn("120000", result["error"])
        self.assertIn("details withheld", result["error"])

    def test_error_on_public_data_keeps_details(self):
        result = execute("let x = [0][7];")
        self.assertIn("Index 7 out of range", result["error"])

    def test_trace_does_not_reveal_restricted_control_flow(self):
        result = execute('let s = order_status(); int n = 0; '
                         'if s == "shipped" then n = 1; else n = 2; end '
                         'for c in s do n = n + 1; end')
        text = " ".join(event["detail"] for event in result["trace"])
        self.assertNotIn("then branch", text)
        self.assertNotIn("iterations", text)
        self.assertNotIn("s: str", text)
        self.assertIn("restricted", text)

    def test_while_condition_runs_under_the_label_of_earlier_laps(self):
        # Re-evaluating the condition depends on the previous test, so an external
        # processor called there must be allowed to learn about it.
        engine, counters, _ = make_engine()
        code = ('int i = 0; str s = order_status(); '
                'while i < |s| and external_model("x") != "" do i = i + 1; end')
        with self.assertRaises(MollyError) as caught:
            engine.run(code, CONTEXT)
        self.assertEqual(caught.exception.phase, "Policy")
        self.assertLessEqual(counters["external_model"], 1)

    def test_random_plans_do_not_interfere(self):
        import sys
        from pathlib import Path
        sys.path.insert(0, str(Path(__file__).parent / "tools"))
        from fuzz_noninterference import check
        stats, leaks = check(plans=150, seed=11)
        self.assertEqual(leaks, [])
        self.assertGreater(stats["both finish"], 20)

    def test_trace_still_describes_public_control_flow(self):
        result = execute("int n = 0; if 1 < 2 then n = 1; end for i in [1 .. 3] do n = n + i; end")
        text = " ".join(event["detail"] for event in result["trace"])
        self.assertIn("then branch", text)
        self.assertIn("3 iterations", text)


if __name__ == "__main__":
    unittest.main()
