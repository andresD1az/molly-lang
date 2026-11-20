# Copyright 2026 Eyner Andres Diaz
# SPDX-License-Identifier: Apache-2.0
"""Molly: a small language for AI-agent plans with permissions that follow the data.

Python 3.10+. No dependencies.

Pipeline:
  1. Lexer: a DFA driven by an explicit transition table (TRANSITIONS).
  2. Parser: LL(1) recursive descent over GRAMMAR, with panic-mode error
     recovery and a full derivation tree.
  3. Checks: names, scopes, arities and fields before the first side effect;
     types are checked at run time.
  4. Interpreter: every value carries the set of recipients allowed to see it.
"""
import math
import sys
from dataclasses import dataclass, field
from types import MappingProxyType
from typing import Callable

__version__ = "0.8.0"

MAX_PROGRAM = 12000
MAX_STATEMENTS = 100
MAX_NESTING = 32
MAX_TERMS = 100
MAX_TEXT = 4000
MAX_ELEMENTS = 1000
MAX_FIELDS = 100
MAX_ERRORS = 25
MAX_ITERATIONS = 10000  # loop iterations, summed over the whole program
MAX_INT = 2 ** 63 - 1  # same range as a Java long
MAX_VALUE_NODES = 10000  # a value written out in full, shared parts counted every time


class MollyError(Exception):
    def __init__(self, phase, message, token=None):
        self.phase, self.message = phase, message
        self.line = token.line if token else 1
        self.column = token.column if token else 1
        super().__init__(f"{phase} [{self.line}:{self.column}]: {message}")

    def as_dict(self):
        return {"phase": self.phase, "line": self.line, "column": self.column,
                "message": self.message}


class MollyErrors(MollyError):
    """Every analysis error found, sorted by position."""

    def __init__(self, errors):
        stop = f"Analysis stopped after {MAX_ERRORS} errors"
        found = [error for error in errors if error.message != stop]
        found.sort(key=lambda error: (error.line, error.column))
        if len(found) > MAX_ERRORS:
            last = found[MAX_ERRORS - 1]
            note = MollyError("Limit", stop)
            note.line, note.column = last.line, last.column
            found = found[:MAX_ERRORS] + [note]
        elif len(found) < len(errors):
            found.append(next(error for error in errors if error.message == stop))
        self.errors = found
        first = self.errors[0]
        Exception.__init__(self, "\n".join(str(error) for error in self.errors))
        self.phase, self.message = first.phase, first.message
        self.line, self.column = first.line, first.column


@dataclass(frozen=True)
class Token:
    kind: str
    text: str
    line: int
    column: int


# ════════════════════════════════════════════════════════════ 1. Lexer (DFA)

# Keywords are recognized by the DFA as IDENT (state q1) and then looked up in
# this table. `letter` is an IDENT; `let` is a keyword.
TYPES = ["int", "float", "bool", "char", "str", "list", "set", "record"]
KEYWORDS = {name: name for name in [
    "let", "send", "if", "then", "else", "end", "while", "for", "do", "in",
    "and", "or", "not", "implies", "iff", "union", "intersect", "subset",
    "true", "false", "null", *TYPES]}

# The alphabet Σ is split into equivalence classes: each class is a column of
# the transition matrix. `n` and `t` are separate from the other letters
# because after `\` inside a string or char they form the escapes \n and \t.
CLASSES = ["letter", "n_t", "digit", "dquote", "squote", "backslash", "equals", "bang",
           "less", "greater", "dot", "semicolon", "plus", "minus", "star", "slash",
           "percent", "lparen", "rparen", "lbracket", "rbracket", "lbrace", "rbrace",
           "comma", "colon", "pipe", "hash", "newline", "space", "other"]

# Single-character symbols: class → token. Each one has its own accepting state.
SINGLES = {"semicolon": ";", "plus": "+", "minus": "-", "star": "*", "slash": "/",
           "percent": "%", "lparen": "(", "rparen": ")", "lbracket": "[", "rbracket": "]",
           "lbrace": "{", "rbrace": "}", "comma": ",", "dot": ".", "colon": ":", "pipe": "|"}

_CLASS_OF = {'"': "dquote", "'": "squote", "\\": "backslash", "=": "equals", "!": "bang",
             "<": "less", ">": "greater", "#": "hash", "\n": "newline", " ": "space",
             "\t": "space", "\r": "space",
             **{token: kind for kind, token in SINGLES.items()}}


def char_class(char):
    if char in _CLASS_OF:
        return _CLASS_OF[char]
    if char in "nt":
        return "n_t"
    if char == "_" or "a" <= char <= "z" or "A" <= char <= "Z":
        return "letter"
    if "0" <= char <= "9":
        return "digit"
    return "other"


_SINGLE_STATE = {kind: f"q{22 + index}" for index, kind in enumerate(SINGLES)}
_ESCAPES = ("dquote", "squote", "backslash", "n_t")

# δ(state, class) → state. A missing cell goes to the reject state qR.
TRANSITIONS = {
    "q0": {"letter": "q1", "n_t": "q1", "digit": "q13", "dquote": "q2", "squote": "q16",
           "equals": "q5", "bang": "q7", "less": "q9", "greater": "q11", "hash": "q20",
           "newline": "q21", "space": "q21", **_SINGLE_STATE},
    "q1": {"letter": "q1", "n_t": "q1", "digit": "q1"},
    "q2": {**{c: "q2" for c in CLASSES if c not in ("dquote", "backslash", "newline")},
           "dquote": "q4", "backslash": "q3"},
    "q3": {c: "q2" for c in _ESCAPES},
    "q4": {},
    "q5": {"equals": "q6"}, "q6": {},
    "q7": {"equals": "q8"}, "q8": {},
    "q9": {"equals": "q10"}, "q10": {},
    "q11": {"equals": "q12"}, "q12": {},
    "q13": {"digit": "q13", "dot": "q14"},
    "q14": {"digit": "q15"},
    "q15": {"digit": "q15"},
    "q16": {**{c: "q18" for c in CLASSES if c not in ("squote", "backslash", "newline")},
            "backslash": "q17"},
    "q17": {c: "q18" for c in _ESCAPES},
    "q18": {"squote": "q19"},
    "q19": {},
    "q20": {c: "q20" for c in CLASSES if c != "newline"},
    "q21": {"newline": "q21", "space": "q21"},
    **{state: {} for state in _SINGLE_STATE.values()},
    "q35": {"dot": "q38"},  # '.' followed by '.' is the range token '..'
    "q38": {},
}
REJECT = "qR"
START = "q0"

# Accepting states and the token each one recognizes.
ACCEPTING = {"q1": "IDENT", "q4": "STRING", "q5": "=", "q6": "==", "q8": "!=",
             "q9": "<", "q10": "<=", "q11": ">", "q12": ">=", "q13": "INT",
             "q15": "FLOAT", "q19": "CHAR", "q20": "COMMENT", "q21": "WHITESPACE",
             **{state: SINGLES[kind] for kind, state in _SINGLE_STATE.items()}, "q38": ".."}
DISCARDED = {"COMMENT", "WHITESPACE"}

# Regular expressions implemented by the DFA (documentation and tests).
REGULAR_EXPRESSIONS = {
    "IDENT": r"[A-Za-z_][A-Za-z_0-9]*",
    "INT": r"[0-9]+",
    "FLOAT": r"[0-9]+\.[0-9]+",
    "STRING": r'"([^"\\\n]|\\["\'\\nt])*"',
    "CHAR": r"'([^'\\\n]|\\[\"'\\nt])'",
    "=": r"=", "==": r"==", "!=": r"!=", "<": r"<", "<=": r"<=", ">": r">", ">=": r">=",
    ";": r";", "+": r"\+", "-": r"-", "*": r"\*", "/": r"/", "%": r"%", "(": r"\(",
    ")": r"\)", "[": r"\[", "]": r"\]", "{": r"\{", "}": r"\}", ",": r",", ".": r"\.",
    ":": r":", "|": r"\|", "..": r"\.\.",
    "COMMENT": r"#[^\n]*",
    "WHITESPACE": r"[ \t\r\n]+",
}

_ESCAPE_HELP = "use \\\" \\' \\\\ \\n or \\t"


def lex_all(code):
    """Run the DFA over the source (longest match). Returns (tokens, errors)."""
    if len(code) > MAX_PROGRAM:
        raise MollyError("Limit", f"Program longer than {MAX_PROGRAM} characters")
    tokens, errors = [], []
    position, line, column = 0, 1, 1

    def advance(text):
        nonlocal line, column
        if "\n" in text:
            line += text.count("\n")
            column = len(text.rsplit("\n", 1)[1]) + 1
        else:
            column += len(text)

    while position < len(code):
        state, index, last = START, position, None
        while index < len(code):
            following = TRANSITIONS[state].get(char_class(code[index]), REJECT)
            if following == REJECT:
                break
            state, index = following, index + 1
            if state in ACCEPTING:
                last = (index, state)
        if last is None:
            message, end = _lexical_error(code, position, state, index)
            errors.append(MollyError("Lexical", message, Token("", "", line, column)))
            advance(code[position:end])
            position = end
            continue
        end, final = last
        text, kind = code[position:end], ACCEPTING[final]
        if kind not in DISCARDED:
            if kind == "IDENT" and text in KEYWORDS:
                kind = KEYWORDS[text]  # a keyword is its own token kind
            tokens.append(Token(kind, text, line, column))
        advance(text)
        position = end
    return tokens + [Token("EOF", "", line, column)], errors


def _until(code, start, closing):
    """End of the damaged region: after the closing symbol on the same line, or end of line."""
    line_end = code.find("\n", start)
    line_end = len(code) if line_end < 0 else line_end
    close = code.find(closing, start, line_end)
    return line_end if close < 0 else close + 1


def _lexical_error(code, position, state, index):
    """Message and resume point when the DFA ends in the reject state."""
    char = code[position]
    following = code[index] if index < len(code) else ""
    if state == START:
        if char_class(char) == "backslash":
            return "'\\' can only appear inside a string or a char", position + 1
        return f"Symbol {char!r} is not in the language alphabet", position + 1
    if state == "q2":
        return "Unterminated string before end of line", index
    if state == "q3":
        return f"Invalid escape sequence in string; {_ESCAPE_HELP}", _until(code, index + 1, '"')
    if state == "q7":
        return "Expected '=' after '!'", position + 1
    if state == "q16":
        if following == "'":
            return "Empty char ''; a char holds exactly one symbol", index + 1
        return "Unterminated char before end of line", index
    if state == "q17":
        return f"Invalid escape sequence in char; {_ESCAPE_HELP}", _until(code, index + 1, "'")
    if state == "q18" and following in ("", "\n"):
        return "Unterminated char before end of line", index
    if state == "q18":
        return ("A char holds a single symbol; use double quotes for text",
                _until(code, index, "'"))
    return "Unrecognized token", position + 1


def lex(code):
    tokens, errors = lex_all(code)
    if errors:
        raise MollyErrors(errors)
    return tokens


_ESCAPE_VALUES = {'"': '"', "'": "'", "\\": "\\", "n": "\n", "t": "\t"}


def decode_string(text):
    """Turn a string or char lexeme (with its delimiters) into its value."""
    result, index, body = [], 0, text[1:-1]
    while index < len(body):
        if body[index] == "\\":
            result.append(_ESCAPE_VALUES[body[index + 1]])
            index += 2
        else:
            result.append(body[index])
            index += 1
    return "".join(result)


def transition_matrix():
    """Rows of the full matrix, including the reject state."""
    rows = []
    for state in list(TRANSITIONS) + [REJECT]:
        cells = TRANSITIONS.get(state, {})
        rows.append((state, [cells.get(c, REJECT) for c in CLASSES]))
    return rows


def dfa_markdown():
    header = "| State | " + " | ".join(CLASSES) + " | Accepts |"
    lines = [header, "|" + "---|" * (len(CLASSES) + 2)]
    for state, cells in transition_matrix():
        mark = ("→" if state == START else "") + ("*" if state in ACCEPTING else "")
        accepts = ACCEPTING.get(state, "reject" if state == REJECT else "—")
        shown = ["·" if cell == REJECT else cell for cell in cells]
        lines.append(f"| {mark}{state} | " + " | ".join(shown) + f" | {accepts} |")
    return "\n".join(lines)


def dfa_dot():
    """The DFA as a Graphviz graph (transitions to qR are omitted)."""
    lines = ["digraph DFA {", "  rankdir=LR;", '  start [shape=point];']
    for state in TRANSITIONS:
        shape = "doublecircle" if state in ACCEPTING else "circle"
        label = f"{state}\\n{ACCEPTING[state]}" if state in ACCEPTING else state
        lines.append(f'  {state} [shape={shape}, label="{label}"];')
    lines.append("  start -> q0;")
    for state, cells in TRANSITIONS.items():
        grouped = {}
        for kind, target in cells.items():
            grouped.setdefault(target, []).append(kind)
        for target, kinds in grouped.items():
            label = "Σ−{" + ", ".join(sorted(set(CLASSES) - set(kinds))) + "}" \
                if len(kinds) > 8 else ", ".join(kinds)
            lines.append(f'  {state} -> {target} [label="{label}"];')
    lines.append("}")
    return "\n".join(lines)


# ════════════════════════════════════════════════ 2. Context-free grammar (LL(1))

# The grammar the parser implements. A production [] is ε.
# Precedence, lowest to highest: implies/iff < or < and < not < relations
# < + - union < * / % intersect < unary - < [i] .field
GRAMMAR = {
    "Program": [["Statements", "EOF"]],
    "Statements": [["Statement", "Statements"], []],
    "Statement": [["let", "IDENT", "=", "Expression", ";"],
                  ["Type", "IDENT", "=", "Expression", ";"],
                  ["IDENT", "=", "Expression", ";"],
                  ["while", "Expression", "do", "Statements", "end"],
                  ["for", "IDENT", "in", "Expression", "do", "Statements", "end"],
                  ["send", "IDENT", "(", "Expression", ")", ";"],
                  ["if", "Expression", "then", "Statements", "Else", "end"]],
    "Type": [[name] for name in TYPES],
    "Else": [["else", "Statements"], []],
    "Expression": [["Disjunction", "LogicRest"]],
    "LogicRest": [["implies", "Disjunction"], ["iff", "Disjunction"], []],
    "Disjunction": [["Conjunction", "OrRest"]],
    "OrRest": [["or", "Conjunction", "OrRest"], []],
    "Conjunction": [["Negation", "AndRest"]],
    "AndRest": [["and", "Negation", "AndRest"], []],
    "Negation": [["not", "Negation"], ["Relation"]],
    "Relation": [["Sum", "RelationRest"]],
    "RelationRest": [["RelOp", "Sum"], []],
    "RelOp": [["=="], ["!="], ["<"], ["<="], [">"], [">="], ["in"], ["subset"]],
    "Sum": [["Term", "SumRest"]],
    "SumRest": [["+", "Term", "SumRest"], ["-", "Term", "SumRest"],
                ["union", "Term", "SumRest"], []],
    "Term": [["Factor", "TermRest"]],
    "TermRest": [["*", "Factor", "TermRest"], ["/", "Factor", "TermRest"],
                 ["%", "Factor", "TermRest"], ["intersect", "Factor", "TermRest"], []],
    "Factor": [["-", "Factor"], ["Postfix"]],
    "Postfix": [["Primary", "Accessors"]],
    "Accessors": [["[", "Expression", "]", "Accessors"], [".", "IDENT", "Accessors"], []],
    "Primary": [["INT"], ["FLOAT"], ["STRING"], ["CHAR"], ["true"], ["false"], ["null"],
                ["IDENT", "Suffix"], ["(", "Expression", ")"], ["[", "Elements", "]"],
                ["{", "Elements", "}"], ["record", "{", "Fields", "}"],
                ["|", "Expression", "|"]],
    "Suffix": [["(", "Arguments", ")"], []],
    "Arguments": [["Expression", "MoreArguments"], []],
    "MoreArguments": [[",", "Expression", "MoreArguments"], []],
    "Elements": [["Expression", "ElementsRest"], []],
    "ElementsRest": [["..", "Expression"], [",", "Expression", "MoreElements"], []],
    "MoreElements": [[",", "Expression", "MoreElements"], []],
    "Fields": [["IDENT", ":", "Expression", "MoreFields"], []],
    "MoreFields": [[",", "IDENT", ":", "Expression", "MoreFields"], []],
}
START_SYMBOL = "Program"


def first_of_sequence(sequence, first):
    result = set()
    for symbol in sequence:
        if symbol not in first:  # terminal
            result.add(symbol)
            return result
        result |= first[symbol] - {"ε"}
        if "ε" not in first[symbol]:
            return result
    result.add("ε")
    return result


def first_sets(grammar=GRAMMAR):
    first = {name: set() for name in grammar}
    changed = True
    while changed:
        changed = False
        for name, productions in grammar.items():
            for production in productions:
                found = first_of_sequence(production, first)
                if not found <= first[name]:
                    first[name] |= found
                    changed = True
    return first


def follow_sets(grammar=GRAMMAR, first=None):
    first = first or first_sets(grammar)
    follow = {name: set() for name in grammar}
    changed = True
    while changed:
        changed = False
        for name, productions in grammar.items():
            for production in productions:
                for index, symbol in enumerate(production):
                    if symbol not in grammar:
                        continue
                    rest = first_of_sequence(production[index + 1:], first)
                    found = (rest - {"ε"}) | (follow[name] if "ε" in rest else set())
                    if not found <= follow[symbol]:
                        follow[symbol] |= found
                        changed = True
    return follow


def ll1_table(grammar=GRAMMAR):
    """Returns (table, conflicts). No conflicts ⇒ the grammar is LL(1)."""
    first = first_sets(grammar)
    follow = follow_sets(grammar, first)
    table, conflicts = {}, []
    for name, productions in grammar.items():
        for production in productions:
            found = first_of_sequence(production, first)
            lookaheads = (found - {"ε"}) | (follow[name] if "ε" in found else set())
            for terminal in lookaheads:
                if (name, terminal) in table:
                    conflicts.append((name, terminal, table[(name, terminal)], production))
                else:
                    table[(name, terminal)] = production
    return table, conflicts


def left_recursion(grammar=GRAMMAR):
    """Cycles A ⇒+ A… (direct or indirect, through nullable prefixes)."""
    first = first_sets(grammar)
    edges = {name: set() for name in grammar}
    for name, productions in grammar.items():
        for production in productions:
            for symbol in production:
                if symbol not in grammar:
                    break
                edges[name].add(symbol)
                if "ε" not in first[symbol]:
                    break
    cycles = []
    for start in grammar:
        stack, seen = [(start, [start])], set()
        while stack:
            node, path = stack.pop()
            for target in edges[node]:
                if target == start:
                    cycles.append(path + [start])
                elif target not in seen:
                    seen.add(target)
                    stack.append((target, path + [target]))
    return cycles


def bnf():
    lines = []
    for name, productions in GRAMMAR.items():
        body = " | ".join(" ".join(f"<{s}>" if s in GRAMMAR else s for s in p) or "ε"
                          for p in productions)
        lines.append(f"<{name}> ::= {body}")
    return "\n".join(lines)


# ═══════════════════════════════════════════════ 3. Recursive-descent parser

@dataclass
class Node:
    kind: str
    token: Token
    children: list = field(default_factory=list)
    branches: tuple = ()  # if: (then, else); while/for: (body,)
    extra: object = None  # declared type in "bind"; field names in "record"; loop variable


def token_name(kind):
    return kind if kind in ("IDENT", "STRING", "INT", "FLOAT", "CHAR", "EOF") else f"'{kind}'"


LITERALS = {"INT", "FLOAT", "STRING", "CHAR", "true", "false", "null"}
RELATIONAL_OPERATORS = {"==", "!=", "<", "<=", ">", ">=", "in", "subset"}


class Parser:
    # Tokens where a statement can start or end: synchronization points.
    SYNC = {"let", "send", "if", "while", "for", "else", "end", "EOF", *TYPES}

    def __init__(self, tokens):
        self.tokens, self.position = tokens, 0
        self.errors, self.statements, self.blocks = [], 0, 0
        self.derivation = {"production": START_SYMBOL, "children": []}
        self.stack = [self.derivation]

    @property
    def current(self):
        return self.tokens[self.position]

    def take(self, kind):
        token = self.current
        if token.kind != kind:
            found = token_name(token.kind) if token.kind == token.text or not token.text \
                else f"{token.kind} «{token.text}»"
            raise MollyError("Syntax", f"Expected {token_name(kind)}; found {found}", token)
        self.position += 1
        self.stack[-1]["children"].append({"terminal": token.kind, "lexeme": token.text,
                                           "line": token.line, "column": token.column})
        return token

    def rule(self, name, callback):
        branch = {"production": name, "children": []}
        self.stack[-1]["children"].append(branch)
        self.stack.append(branch)
        try:
            result = callback()
            if not branch["children"]:
                branch["children"].append({"terminal": "ε"})
            return result
        finally:
            self.stack.pop()

    def report(self, error):
        """Record a recoverable error. Limits and too many errors stop the analysis."""
        if isinstance(error, MollyErrors) or error.phase == "Limit":
            raise error
        self.errors.append(error)
        self.stack[-1]["children"].append({"error": str(error)})
        if len(self.errors) >= MAX_ERRORS:
            raise MollyErrors(self.errors + [MollyError(
                "Limit", f"Analysis stopped after {MAX_ERRORS} errors", self.current)])

    def synchronize(self, start):
        """Panic mode: skip tokens until after ';' or before a statement."""
        while self.current.kind not in self.SYNC:
            kind = self.current.kind
            self.position += 1
            if kind == ";":
                return
        if self.position == start and self.current.kind != "EOF":
            self.position += 1  # always advance past a stray 'else' or 'end'

    def parse(self, raise_errors=True):
        program = self.statement_list({"EOF"})
        self.take("EOF")
        if self.errors and raise_errors:
            raise MollyErrors(self.errors)
        return program

    def statement_list(self, ends):
        """<Statements> ::= <Statement> <Statements> | ε, choosing ε on FOLLOW(Statements)."""
        ends = ends | {"EOF"}

        def statements():
            if self.current.kind in ends:
                return []
            start = self.position
            try:
                nodes = [self.rule("Statement", self.statement)]
            except MollyError as error:
                self.report(error)
                self.synchronize(start)
                nodes = []
            return nodes + self.rule("Statements", statements)
        return self.rule("Statements", statements)

    def statement(self):
        self.statements += 1
        if self.statements > MAX_STATEMENTS:
            raise MollyError("Limit", f"At most {MAX_STATEMENTS} statements", self.current)
        kind = self.current.kind
        if kind == "let":
            self.take("let")
            return self.binding(None)
        if kind in TYPES:
            return self.binding(self.rule("Type", lambda: self.take(kind).kind))
        if kind == "send":
            self.take("send")
            target = self.take("IDENT")
            self.take("(")
            expression = self.rule("Expression", lambda: self.expression(0))
            self.take(")")
            self.take(";")
            return Node("send", target, [expression])
        if kind == "IDENT":
            name = self.take("IDENT")
            self.take("=")
            expression = self.rule("Expression", lambda: self.expression(0))
            self.take(";")
            return Node("assign", name, [expression])
        if kind == "if":
            return self.conditional()
        if kind in ("while", "for"):
            return self.loop(kind)
        raise MollyError("Syntax", "Expected a statement (let, a type, an assignment, send, if, "
                         f"while, for); found {token_name(kind)}", self.current)

    def loop(self, kind):
        """while <Expression> do <Statements> end  |  for IDENT in <Expression> do <Statements> end"""
        if self.blocks >= MAX_NESTING:
            raise MollyError("Limit", f"More than {MAX_NESTING} nested blocks", self.current)
        keyword = self.take(kind)
        variable = self.take("IDENT") if kind == "for" else None
        if kind == "for":
            self.take("in")
        head = self.rule("Expression", lambda: self.expression(0))
        self.take("do")
        self.blocks += 1
        try:
            body = self.statement_list({"end"})
        finally:
            self.blocks -= 1
        self.take("end")
        return Node(kind, keyword, [head], (body,), extra=variable)

    def binding(self, declared):
        """let IDENT = <Expression> ;  |  <Type> IDENT = <Expression> ;"""
        name = self.take("IDENT")
        self.take("=")
        expression = self.rule("Expression", lambda: self.expression(0))
        self.take(";")
        return Node("bind", name, [expression], extra=declared)

    def conditional(self):
        """if <Expression> then <Statements> <Else> end. Every if has its own end."""
        if self.blocks >= MAX_NESTING:
            raise MollyError("Limit", f"More than {MAX_NESTING} nested blocks", self.current)
        keyword = self.take("if")
        condition = None
        try:
            condition = self.rule("Expression", lambda: self.expression(0))
            self.take("then")
        except MollyError as error:
            self.report(error)
            # Resume in the body: after 'then' or at the start of a statement.
            while self.current.kind not in self.SYNC | {"then"}:
                self.position += 1
            if self.current.kind == "then":
                self.take("then")
        self.blocks += 1
        try:
            then = self.statement_list({"else", "end"})
            otherwise = self.rule("Else", self.else_part)
        finally:
            self.blocks -= 1
        self.take("end")
        return Node("if", keyword, [condition] if condition else [], (then, otherwise))

    def else_part(self):
        if self.current.kind != "else":
            return []
        self.take("else")
        return self.statement_list({"end"})

    # ── Expressions: one grammar level per precedence level ──

    def level(self, operand, rest, operators, parse_operand):
        """<N> ::= <operand> <rest>;  <rest> ::= op <operand> <rest> | ε.

        <rest> is right-recursive (LL(1)); the AST is folded to the left, so
        a - b - c is (a - b) - c.
        """
        node = self.rule(operand, parse_operand)
        pairs = []

        def tail():
            if self.current.kind not in operators:
                return
            if len(pairs) >= MAX_TERMS - 1:
                raise MollyError("Limit", f"At most {MAX_TERMS} terms per expression",
                                 self.current)
            operator = self.take(self.current.kind)
            pairs.append((operator, self.rule(operand, parse_operand)))
            self.rule(rest, tail)
        self.rule(rest, tail)
        for operator, right in pairs:
            node = Node("binary", operator, [node, right])
        return node

    def expression(self, depth):
        if depth > MAX_NESTING:
            raise MollyError("Limit", f"Nesting deeper than {MAX_NESTING}", self.current)
        return self.logic(depth)

    def logic(self, depth):
        """Propositional connectives (→, ↔): non-associative, like relations."""
        left = self.rule("Disjunction", lambda: self.disjunction(depth))

        def rest():
            if self.current.kind not in ("implies", "iff"):
                return None
            operator = self.take(self.current.kind)
            return operator, self.rule("Disjunction", lambda: self.disjunction(depth))
        found = self.rule("LogicRest", rest)
        return Node("binary", found[0], [left, found[1]]) if found else left

    def disjunction(self, depth):
        return self.level("Conjunction", "OrRest", {"or"}, lambda: self.conjunction(depth))

    def conjunction(self, depth):
        return self.level("Negation", "AndRest", {"and"}, lambda: self.negation(depth))

    def negation(self, depth):
        if self.current.kind != "not":
            return self.rule("Relation", lambda: self.relation(depth))
        if depth > MAX_NESTING:
            raise MollyError("Limit", f"Nesting deeper than {MAX_NESTING}", self.current)
        operator = self.take("not")
        return Node("unary", operator, [self.rule("Negation", lambda: self.negation(depth + 1))])

    def relation(self, depth):
        """Non-associative relation: a < b < c is a syntax error."""
        left = self.rule("Sum", lambda: self.sum(depth))

        def rest():
            if self.current.kind not in RELATIONAL_OPERATORS:
                return None
            operator = self.rule("RelOp", lambda: self.take(self.current.kind))
            return operator, self.rule("Sum", lambda: self.sum(depth))
        found = self.rule("RelationRest", rest)
        return Node("binary", found[0], [left, found[1]]) if found else left

    def sum(self, depth):
        return self.level("Term", "SumRest", {"+", "-", "union"}, lambda: self.term(depth))

    def term(self, depth):
        return self.level("Factor", "TermRest", {"*", "/", "%", "intersect"},
                          lambda: self.factor(depth))

    def factor(self, depth):
        if self.current.kind != "-":
            return self.rule("Postfix", lambda: self.postfix(depth))
        if depth > MAX_NESTING:
            raise MollyError("Limit", f"Nesting deeper than {MAX_NESTING}", self.current)
        operator = self.take("-")
        return Node("unary", operator, [self.rule("Factor", lambda: self.factor(depth + 1))])

    def postfix(self, depth):
        node = self.rule("Primary", lambda: self.primary(depth))
        count = 0

        def accessors():
            nonlocal node, count
            kind = self.current.kind
            if kind not in ("[", "."):
                return
            count += 1
            if count > MAX_TERMS:
                raise MollyError("Limit", f"At most {MAX_TERMS} chained accessors", self.current)
            if kind == "[":
                bracket = self.take("[")
                index = self.rule("Expression", lambda: self.expression(depth + 1))
                self.take("]")
                node = Node("index", bracket, [node, index])
            else:
                self.take(".")
                node = Node("field", self.take("IDENT"), [node])
            self.rule("Accessors", accessors)
        self.rule("Accessors", accessors)
        return node

    def primary(self, depth):
        kind = self.current.kind
        if kind in LITERALS:
            return Node("literal", self.take(kind))
        if kind == "IDENT":
            return self.call_or_variable(depth)
        if kind == "(":
            self.take("(")
            inner = self.rule("Expression", lambda: self.expression(depth + 1))
            self.take(")")
            return inner
        if kind in ("[", "{"):
            opening = self.take(kind)
            items, is_range = self.rule("Elements", lambda: self.elements(depth))
            self.take("]" if kind == "[" else "}")
            node_kind = "list" if kind == "[" else "set"
            return Node("range" if is_range else node_kind, opening, items, extra=node_kind)
        if kind == "|":
            bar = self.take("|")
            inner = self.rule("Expression", lambda: self.expression(depth + 1))
            self.take("|")
            return Node("unary", bar, [inner])  # |x|: cardinality or length
        if kind == "record":
            keyword = self.take("record")
            self.take("{")
            names, values = self.rule("Fields", lambda: self.fields(depth))
            self.take("}")
            return Node("record", keyword, values, extra=names)
        raise MollyError("Syntax", "Expected an expression (literal, IDENT, '(', '[', '{', '|' or "
                         f"record); found {token_name(kind)}", self.current)

    def arguments(self, depth):
        """<Arguments> ::= <Expression> <MoreArguments> | ε"""
        if self.current.kind == ")":
            return []
        items = [self.rule("Expression", lambda: self.expression(depth + 1))]

        def more():
            if self.current.kind != ",":
                return
            if len(items) >= MAX_TERMS:
                raise MollyError("Limit", f"At most {MAX_TERMS} arguments", self.current)
            self.take(",")
            items.append(self.rule("Expression", lambda: self.expression(depth + 1)))
            self.rule("MoreArguments", more)
        self.rule("MoreArguments", more)
        return items

    def elements(self, depth):
        """<Elements> ::= <Expression> <ElementsRest> | ε;  <ElementsRest> ::= .. <Expression> | , … | ε"""
        if self.current.kind in ("]", "}"):
            return [], False
        first = self.rule("Expression", lambda: self.expression(depth + 1))

        def rest():
            if self.current.kind == "..":
                self.take("..")
                return [first, self.rule("Expression", lambda: self.expression(depth + 1))], True
            if self.current.kind != ",":
                return [first], False
            self.take(",")
            items = [first, self.rule("Expression", lambda: self.expression(depth + 1))]

            def more():
                if self.current.kind != ",":
                    return
                if len(items) >= MAX_TERMS:
                    raise MollyError("Limit", f"At most {MAX_TERMS} elements", self.current)
                self.take(",")
                items.append(self.rule("Expression", lambda: self.expression(depth + 1)))
                self.rule("MoreElements", more)
            self.rule("MoreElements", more)
            return items, False
        return self.rule("ElementsRest", rest)

    def fields(self, depth):
        """<Fields> ::= IDENT : <Expression> <MoreFields> | ε"""
        names, values = [], []
        if self.current.kind != "IDENT":
            return names, values

        def field_pair():
            names.append(self.take("IDENT"))
            self.take(":")
            values.append(self.rule("Expression", lambda: self.expression(depth + 1)))

        def more():
            if self.current.kind != ",":
                return
            if len(names) >= MAX_FIELDS:
                raise MollyError("Limit", f"At most {MAX_FIELDS} fields per record", self.current)
            self.take(",")
            field_pair()
            self.rule("MoreFields", more)
        field_pair()
        self.rule("MoreFields", more)
        return names, values

    def call_or_variable(self, depth):
        name = self.take("IDENT")

        def suffix():
            if self.current.kind != "(":
                return Node("variable", name)
            self.take("(")
            children = self.rule("Arguments", lambda: self.arguments(depth))
            self.take(")")
            return Node("call", name, children)
        return self.rule("Suffix", suffix)


def format_tree(tree):
    """The derivation tree as text, with └── / ├── branches."""
    lines = []

    def label(node):
        if "production" in node:
            return f"<{node['production']}>"
        if "error" in node:
            return f"[ERROR] {node['error']}"
        if node["terminal"] == "ε" or node["terminal"] == node["lexeme"]:
            return node["terminal"]
        return f"{node['terminal']} «{node['lexeme']}»"

    def walk(node, prefix, last, root):
        lines.append(label(node) if root else prefix + ("└── " if last else "├── ") + label(node))
        children = node.get("children", [])
        inner = "" if root else prefix + ("    " if last else "│   ")
        for index, child in enumerate(children):
            walk(child, inner, index == len(children) - 1, False)
    walk(tree, "", True, True)
    return "\n".join(lines)


# ═════════════════════════════════════════════════════════════════ Data types
#
# Python representation of each Molly type. All of them are immutable, so an
# adapter cannot change the value of a Molly variable.
#   int → int · float → float · bool → bool · str → str · char → Char(str)
#   list → tuple · set → MollySet(tuple) · record → MappingProxyType · null → None

class Char(str):
    """A single character; different from a one-letter str ('a' != "a")."""
    __slots__ = ()


class MollySet(tuple):
    """Unique elements in insertion order; different from a list."""
    __slots__ = ()


NUMERIC = ("int", "float")
NULLABLE = ("str", "list", "set", "record")  # accept null, like Java reference types
SCALARS = ("int", "float", "bool", "char", "str", "null")


def type_of(value):
    if value is None:
        return "null"
    if isinstance(value, bool):  # before int: in Python bool is a subclass of int
        return "bool"
    if isinstance(value, int):
        return "int"
    if isinstance(value, float):
        return "float"
    if isinstance(value, Char):
        return "char"
    if isinstance(value, str):
        return "str"
    if isinstance(value, MollySet):
        return "set"
    if isinstance(value, tuple):
        return "list"
    if isinstance(value, MappingProxyType):
        return "record"
    raise TypeError(type(value).__name__)


def equal(a, b):
    """Molly equality: 1 == 1.0, but 1 != true and 'a' != "a"."""
    ta, tb = type_of(a), type_of(b)
    if ta in NUMERIC and tb in NUMERIC:
        return a == b
    if ta != tb:
        return False
    if ta == "list":
        return len(a) == len(b) and all(equal(x, y) for x, y in zip(a, b))
    if ta == "set":
        return len(a) == len(b) and all(contains(b, x) for x in a)
    if ta == "record":
        return a.keys() == b.keys() and all(equal(a[k], b[k]) for k in a)
    return a == b


def contains(collection, value):
    return any(equal(value, item) for item in collection)


def _escape(text, delimiter):
    text = text.replace("\\", "\\\\").replace("\n", "\\n").replace("\t", "\\t")
    return delimiter + text.replace(delimiter, "\\" + delimiter) + delimiter


def literal_repr(value, limit=MAX_TEXT, token=None):
    """The value written as a Molly literal. Stops as soon as it passes `limit` characters."""
    parts, used = [], 0

    def emit(text):
        nonlocal used
        used += len(text)
        if used > limit:
            raise MollyError("Limit", f"Text longer than {limit} characters", token)
        parts.append(text)

    def write(item):
        kind = type_of(item)
        if kind in ("list", "set", "record"):
            emit({"list": "[", "set": "{", "record": "record {"}[kind])
            pairs = item.items() if kind == "record" else ((None, x) for x in item)
            for index, (name, element) in enumerate(pairs):
                emit(", " if index else "")
                if name is not None:
                    emit(f"{name}: ")
                write(element)
            emit("}" if kind != "list" else "]")
        elif kind == "null":
            emit("null")
        elif kind == "bool":
            emit("true" if item else "false")
        elif kind in NUMERIC:
            emit(repr(item))
        else:
            emit(_escape(item, '"' if kind == "str" else "'"))

    write(value)
    return "".join(parts)


def to_text(value, limit=MAX_TEXT, token=None):
    """Text used for concatenation and sending: str and char go without quotes."""
    if type_of(value) in ("str", "char"):
        if len(value) > limit:
            raise MollyError("Limit", f"Text longer than {limit} characters", token)
        return str(value)
    return literal_repr(value, limit, token)


def value_shape(value):
    """(nodes, depth) of a value written out in full. Shared parts count every time they
    appear, because comparing or printing the value visits them every time."""
    seen = {}

    def walk(item):
        kind = type_of(item)
        if kind not in ("list", "set", "record"):
            return 1, 0
        key = id(item)
        if key not in seen:
            nodes, depth = 1, 0
            for element in (item.values() if kind == "record" else item):
                n, d = walk(element)
                nodes, depth = nodes + n, max(depth, d)
                if nodes > MAX_VALUE_NODES:
                    break
            seen[key] = (nodes, depth + 1)
        return seen[key]

    return walk(value)


def check_size(value, token=None):
    """Size and range limits for a newly created value."""
    kind = type_of(value)
    if kind == "str" and len(value) > MAX_TEXT:
        raise MollyError("Limit", f"Text longer than {MAX_TEXT} characters", token)
    if kind == "int" and abs(value) > MAX_INT:
        raise MollyError("Limit", "Integer outside the 64-bit range", token)
    if kind == "float" and not math.isfinite(value):
        raise MollyError("Limit", "Infinite or undefined float", token)
    if kind in ("list", "set") and len(value) > MAX_ELEMENTS:
        raise MollyError("Limit", f"More than {MAX_ELEMENTS} elements", token)
    if kind == "record" and len(value) > MAX_FIELDS:
        raise MollyError("Limit", f"More than {MAX_FIELDS} fields", token)
    if kind in ("list", "set", "record"):
        nodes, depth = value_shape(value)
        if nodes > MAX_VALUE_NODES:
            raise MollyError("Limit", f"Value larger than {MAX_VALUE_NODES} elements in total", token)
        if depth > MAX_NESTING:
            raise MollyError("Limit", f"Value nested deeper than {MAX_NESTING} levels", token)
    return value


def build_set(items, token=None):
    result = []
    for item in items:
        if type_of(item) not in SCALARS:
            raise MollyError("Type", f"A set only holds simple values, not {type_of(item)}", token)
        if not contains(result, item):
            result.append(item)
    return check_size(MollySet(result), token)


def to_molly(obj, depth=0):
    """Convert what a Python adapter returns into a Molly value."""
    if depth > MAX_NESTING:
        raise MollyError("Adapter", "Structure nested too deeply")
    if obj is None or isinstance(obj, (bool, int, float, str)):
        return check_size(obj)
    if isinstance(obj, (set, frozenset, MollySet)):
        return build_set([to_molly(item, depth + 1) for item in obj])
    if isinstance(obj, (list, tuple)):
        return check_size(tuple(to_molly(item, depth + 1) for item in obj))
    if isinstance(obj, (dict, MappingProxyType)):
        if not all(isinstance(k, str) and k.isidentifier() and k.isascii() for k in obj):
            raise MollyError("Adapter", "Record field names must be identifiers")
        return check_size(MappingProxyType({k: to_molly(v, depth + 1) for k, v in obj.items()}))
    raise MollyError("Adapter", f"Unsupported type: {type(obj).__name__}")


def _type_error(message, token):
    return MollyError("Type", message, token)


def binary_operation(operator, a, b, token):
    ta, tb = type_of(a), type_of(b)
    if operator in ("and", "or", "implies", "iff"):
        if ta != "bool" or tb != "bool":
            raise _type_error(f"'{operator}' needs bools; got {ta} and {tb}", token)
        return {"and": a and b, "or": a or b, "implies": (not a) or b, "iff": a == b}[operator]
    if operator in ("union", "intersect", "subset") or (operator == "-" and ta == tb == "set"):
        if ta != "set" or tb != "set":
            raise _type_error(f"'{operator}' needs sets; got {ta} and {tb}", token)
        if operator == "subset":
            return all(contains(b, x) for x in a)
        if operator == "union":
            return build_set(a + b, token)
        keep = operator == "intersect"  # intersect: elements in b; difference: elements not in b
        return MollySet(x for x in a if contains(b, x) == keep)
    if operator == "==":
        return equal(a, b)
    if operator == "!=":
        return not equal(a, b)
    if operator in ("<", "<=", ">", ">="):
        comparable = (ta in NUMERIC and tb in NUMERIC) or (ta == tb and ta in ("str", "char"))
        if not comparable:
            raise _type_error(f"Cannot order {ta} and {tb}", token)
        return {"<": a < b, "<=": a <= b, ">": a > b, ">=": a >= b}[operator]
    if operator == "in":
        if tb in ("list", "set"):
            return contains(b, a)
        if tb == "str" and ta in ("str", "char"):
            return a in b
        raise _type_error(f"'in' needs a list, set or str on the right; got {tb}", token)
    if operator == "+":
        if ta in ("str", "char") or tb in ("str", "char"):
            return to_text(a, token=token) + to_text(b, token=token)
        if ta == "list" and tb == "list":
            return a + b
    if ta not in NUMERIC or tb not in NUMERIC:
        raise _type_error(f"'{operator}' does not apply to {ta} and {tb}", token)
    if operator in ("/", "%") and b == 0:
        raise MollyError("Runtime", "Division by zero", token)
    if operator == "+":
        return a + b
    if operator == "-":
        return a - b
    if operator == "*":
        if ta == tb == "int" and a and b and abs(a) > MAX_INT // abs(b):
            raise MollyError("Limit", "Integer outside the 64-bit range", token)
        return a * b
    if operator == "/":
        return a / b  # always a float, as in Python 3
    return a % b


def unary_operation(operator, a, token):
    kind = type_of(a)
    if operator == "|":
        if kind not in ("set", "list", "str", "record"):
            raise _type_error(f"|x| needs a set, list, str or record; got {kind}", token)
        return len(a)
    if operator == "not":
        if kind != "bool":
            raise _type_error(f"'not' needs a bool; got {kind}", token)
        return not a
    if kind not in NUMERIC:
        raise _type_error(f"'-' needs an int or float; got {kind}", token)
    return -a


def index_value(container, index, token):
    kind, index_kind = type_of(container), type_of(index)
    if kind == "null":
        raise MollyError("Runtime", "Index on null", token)
    if kind not in ("list", "str") or index_kind != "int":
        raise _type_error(f"Cannot index {kind} with {index_kind}", token)
    if not 0 <= index < len(container):
        raise MollyError("Runtime", f"Index {index} out of range (size {len(container)})", token)
    item = container[index]
    return Char(item) if kind == "str" else item


def field_value(record, name, token):
    kind = type_of(record)
    if kind == "null":
        raise MollyError("Runtime", f"Field '{name}' accessed on null", token)
    if kind != "record":
        raise _type_error(f"{kind} has no fields", token)
    if name not in record:
        raise MollyError("Runtime", f"The record has no field '{name}'", token)
    return record[name]


def build_range(start, end, kind, token):
    """[a .. b]: the ints from a to b, both included ({a .. b} builds a set)."""
    if type_of(start) != "int" or type_of(end) != "int":
        raise _type_error(f"A range needs ints; got {type_of(start)} and {type_of(end)}", token)
    if end - start + 1 > MAX_ELEMENTS:
        raise MollyError("Limit", f"Range with more than {MAX_ELEMENTS} elements", token)
    values = tuple(range(start, end + 1))
    return MollySet(values) if kind == "set" else values


def coerce(declared, value, token):
    """Check the declaration `type x = …`. An int widens to float."""
    if declared is None:  # let: the type is inferred from the value
        return value
    kind = type_of(value)
    if kind == declared:
        return value
    if declared == "float" and kind == "int":
        return float(value)
    if kind == "null" and declared in NULLABLE:
        return value
    raise _type_error(f"Declared {declared} but the value is {kind}", token)


def literal_value(token):
    kind, text = token.kind, token.text
    if kind == "INT":
        if len(text.lstrip("0")) > 19:
            raise MollyError("Limit", "Integer outside the 64-bit range", token)
        return check_size(int(text), token)
    if kind == "FLOAT":
        return check_size(float(text), token)
    if kind == "STRING":
        return check_size(decode_string(text), token)
    if kind == "CHAR":
        return Char(decode_string(text))
    return {"true": True, "false": False, "null": None}[kind]


# ════════════════════════════════════════════════ 4. Execution with permissions

@dataclass(frozen=True)
class Context:
    tenant: str
    subject: str


@dataclass(frozen=True)
class Value:
    data: object = None
    # None = public. Empty set = no allowed recipient. Never confuse them.
    audience: frozenset | None = None
    origin: tuple = ()


def combine(values):
    audience, origin = None, []
    for value in values:
        if value.audience is not None:
            audience = value.audience if audience is None else audience & value.audience
        origin.extend(value.origin)
    return audience, tuple(dict.fromkeys(origin))


@dataclass(frozen=True)
class Source:
    load: Callable[[Context], object]
    authorize: Callable[[Context], bool]
    audience: Callable[[Context], frozenset | None]


@dataclass(frozen=True)
class Transform:
    run: Callable
    arity: int
    # None: trusted local computation. An external processor must have an identity.
    processor: str | None = None


@dataclass(frozen=True)
class Sink:
    identity: Callable[[Context], str]
    send: Callable[[Context, str], None]


PUBLIC = Value()


class Slot:
    """Where a variable lives: its current value and declared type (None = let)."""
    __slots__ = ("value", "declared")

    def __init__(self, value, declared):
        self.value, self.declared = value, declared


class Scope:
    """Chained block scope: reads and assignments look outward; declarations are local."""

    def __init__(self, parent):
        self.parent, self.slots = parent, {}

    def declare(self, name, value, declared):
        self.slots[name] = Slot(value, declared)

    def find(self, name):
        scope = self
        while scope is not None:
            if name in scope.slots:
                return scope.slots[name]
            scope = scope.parent
        return None


def assigned_names(blocks):
    """Names that some statement in the blocks reassigns (static analysis)."""
    names = set()
    for nodes in blocks:
        for node in nodes:
            if node.kind == "assign":
                names.add(node.token.text)
            for branch in node.branches:
                names |= assigned_names([branch])
    return names


def shown_type(value):
    """Type for the trace; the type of restricted data is not disclosed."""
    return type_of(value.data) if value.audience is None else "restricted value"


class Engine:
    def __init__(self, sources, transforms, sinks):
        if set(sources) & set(transforms):
            raise ValueError("Source and transform names must be unique")
        self.sources, self.transforms, self.sinks = dict(sources), dict(transforms), dict(sinks)
        self.trace = []

    def event(self, operation, detail, pc=PUBLIC):
        # No raw source or generated text in the trace. Steps that only run
        # because of restricted data (pc not public) are not recorded either:
        # the trace would reveal which branch ran or how many times a loop did.
        if pc.audience is None:
            self.trace.append({"operation": operation, "detail": detail})

    def validate(self, program):
        """Checks before running: names, scopes, arities, sinks and fields."""
        errors = []

        def expr(node, scope):
            if node is None:
                return
            name = node.token.text
            if node.kind == "variable" and name not in scope:
                errors.append(MollyError("Semantic", f"Undeclared variable: {name}", node.token))
            elif node.kind == "call":
                if name in self.sources:
                    count = 0
                elif name in self.transforms:
                    count = self.transforms[name].arity
                else:
                    errors.append(MollyError("Semantic", f"Unregistered tool: {name}", node.token))
                    count = len(node.children)
                if len(node.children) != count:
                    errors.append(MollyError("Semantic", f"Tool {name} takes {count} arguments",
                                             node.token))
            elif node.kind == "record":
                seen = set()
                for token in node.extra:
                    if token.text in seen:
                        errors.append(MollyError("Semantic", f"Repeated field: {token.text}", token))
                    seen.add(token.text)
            for child in node.children:
                expr(child, scope)

        def declare(scope, token, mutable):
            if token.text in scope:
                errors.append(MollyError("Semantic", f"Variable already declared: {token.text}",
                                         token))
            scope[token.text] = mutable

        def block(nodes, outer):
            # name → can it be reassigned? (let: no; declared with a type: yes)
            scope = dict(outer)  # declarations inside a block do not leave it
            for node in nodes:
                expr(node.children[0] if node.children else None, scope)
                name = node.token.text
                if node.kind == "if":
                    for branch in node.branches:
                        block(branch, scope)
                elif node.kind in ("while", "for"):
                    inner = dict(scope)
                    if node.kind == "for":
                        declare(inner, node.extra, False)
                    block(node.branches[0], inner)
                elif node.kind == "send" and name not in self.sinks:
                    errors.append(MollyError("Semantic", f"Unregistered sink: {name}", node.token))
                elif node.kind == "bind":
                    declare(scope, node.token, node.extra is not None)
                elif node.kind == "assign":
                    if name not in scope:
                        errors.append(MollyError("Semantic", f"Undeclared variable: {name}",
                                                 node.token))
                    elif not scope[name]:
                        errors.append(MollyError("Semantic", f"{name} is a let constant and cannot "
                                                 "be reassigned; declare it with its type",
                                                 node.token))
        block(program, {})
        if errors:
            raise MollyErrors(errors)

    def effects(self, blocks, context):
        """Identities that would receive data in any of the blocks (sinks and processors)."""
        found = []

        def expr(node):
            if node.kind == "call" and node.token.text in self.transforms:
                processor = self.transforms[node.token.text].processor
                if processor is not None:
                    found.append((processor, node.token))
            for child in node.children:
                expr(child)

        def block(nodes):
            for node in nodes:
                for child in node.children:
                    expr(child)
                if node.kind == "send":
                    found.append((self.sinks[node.token.text].identity(context), node.token))
                for branch in node.branches:
                    block(branch)
        for item in blocks:
            block(item)
        return found

    def require(self, value, identity, token):
        if value.audience is not None and identity not in value.audience:
            path = " → ".join(value.origin)
            raise MollyError("Policy", f"Recipient not allowed: {identity}. Origin: {path}", token)

    def run(self, code, context):
        self.trace = []
        # Each precedence level is a recursive call; 32 nesting levels need
        # more stack than Python's default recursion limit.
        previous_limit = sys.getrecursionlimit()
        sys.setrecursionlimit(max(previous_limit, 6000))
        try:
            return self._run(code, context)
        finally:
            sys.setrecursionlimit(previous_limit)

    def _run(self, code, context):
        try:
            tokens, errors = lex_all(code)
            parser = Parser(tokens)
            program = parser.parse(raise_errors=False)
            errors += parser.errors
            if errors:
                raise MollyErrors(errors)
            self.validate(program)
            self.event("ANALYSIS", "Tokens, syntax and tools checked")

            iterations = 0
            outbox = []  # sends are delivered only if the whole plan succeeds

            def shield(values, token, operation):
                """Runs `operation`; if it fails on restricted data, withholds the details.

                Messages such as "Index 4271 out of range" would hand the value
                to whoever reads the error (the agent that wrote the plan).
                """
                try:
                    return operation()
                except MollyError as error:
                    if error.phase in ("Policy", "Access") or combine(values)[0] is None:
                        raise
                    raise MollyError(error.phase, "Operation failed on restricted data; "
                                     "details withheld", token) from None

            def evaluate(node, scope, pc):
                kind, token = node.kind, node.token
                if kind == "literal":
                    return Value(literal_value(token))
                if kind == "variable":
                    return scope.find(token.text).value
                if kind == "call":
                    return call(node, scope, pc)
                values = [evaluate(child, scope, pc) for child in node.children]
                data = [value.data for value in values]

                def compute():
                    if kind == "binary":
                        result = binary_operation(token.kind, data[0], data[1], token)
                    elif kind == "unary":
                        result = unary_operation(token.kind, data[0], token)
                    elif kind == "index":
                        result = index_value(data[0], data[1], token)
                    elif kind == "field":
                        result = field_value(data[0], token.text, token)
                    elif kind == "list":
                        result = tuple(data)
                    elif kind == "set":
                        result = build_set(data, token)
                    elif kind == "range":
                        result = build_range(data[0], data[1], node.extra, token)
                    else:  # record
                        result = MappingProxyType({name.text: item
                                                   for name, item in zip(node.extra, data)})
                    return check_size(result, token)
                # Any result depends on all of its inputs: their audiences intersect.
                return Value(shield(values + [pc], token, compute), *combine(values))

            def call(node, scope, pc):
                name, token = node.token.text, node.token
                if name in self.sources:
                    source = self.sources[name]
                    if not source.authorize(context):
                        raise MollyError("Access", "Context not authorized for this source", token)
                    label = source.audience(context)
                    if label is not None and not isinstance(label, frozenset):
                        raise MollyError("Adapter", "A source must declare a frozenset or None",
                                         token)
                    data = to_molly(source.load(context))
                    self.event("READ", f"{name}: permission checked before querying", pc)
                    return Value(data, label, (name,))
                transform = self.transforms[name]
                values = [evaluate(child, scope, pc) for child in node.children]
                label, origin = combine(values)
                if transform.processor is not None:
                    self.require(Value(None, *combine(values + [pc])), transform.processor, token)
                data = to_molly(transform.run(context, *(value.data for value in values)))
                self.event("TRANSFORM", f"{name}: input restrictions preserved", pc)
                return Value(data, label, origin + (name,))

            def execute(nodes, scope, pc):
                scope = Scope(scope)  # block declarations do not escape
                for node in nodes:
                    if node.kind == "bind":
                        value = evaluate(node.children[0], scope, pc)
                        if node.extra:
                            raw = value
                            data = shield([raw, pc], node.token,
                                          lambda: coerce(node.extra, raw.data, node.token))
                            value = Value(data, raw.audience, raw.origin)
                        scope.declare(node.token.text, value, node.extra)
                        self.event("VARIABLE", f"{node.token.text}: {shown_type(value)}; "
                                   "origin and permissions preserved", pc)
                    elif node.kind == "assign":
                        value = evaluate(node.children[0], scope, pc)
                        slot = scope.find(node.token.text)
                        data = shield([value, pc], node.token,
                                      lambda: coerce(slot.declared, value.data, node.token))
                        # The assignment also depends on having reached this point (pc).
                        slot.value = Value(data, *combine([value, pc]))
                        self.event("ASSIGN", f"{node.token.text}: {shown_type(slot.value)}", pc)
                    elif node.kind == "while":
                        while_loop(node, scope, pc)
                    elif node.kind == "for":
                        for_loop(node, scope, pc)
                    elif node.kind == "send":
                        value = evaluate(node.children[0], scope, pc)
                        sink = self.sinks[node.token.text]
                        identity = sink.identity(context)
                        # pc: having reached this send is information too.
                        self.require(Value(None, *combine([value, pc])), identity, node.token)
                        text = shield([value, pc], node.token,
                                      lambda: to_text(value.data, token=node.token))
                        # Deferred: an allowed send must not go out if a later step fails.
                        outbox.append((sink, text, identity, pc))
                    else:
                        conditional(node, scope, pc)

            def guard(test, pc, blocks, scope, what):
                """Control context (pc) for a block whose execution depends on `test`.

                Implicit flow: choosing a branch or repeating a loop reveals information
                about the condition. Before running, the effects of ALL possible blocks
                are checked, and the variables they could reassign inherit the label
                whether they run or not. The outcome does not depend on the path taken.
                """
                label, origin = combine([test, pc])
                block_pc = Value(None, label, origin + (what,))
                for identity, token in self.effects(blocks, context):
                    self.require(block_pc, identity, token)
                for name in assigned_names(blocks):
                    slot = scope.find(name)
                    if slot is not None:
                        slot.value = Value(slot.value.data, *combine([slot.value, block_pc]))
                return block_pc

            def condition(node, scope, pc, what):
                test = evaluate(node.children[0], scope, pc)

                def is_bool():
                    if type_of(test.data) != "bool":
                        raise _type_error(f"The {what} condition must be a bool; got "
                                          f"{type_of(test.data)}", node.token)
                shield([test, pc], node.token, is_bool)
                return test

            def count_iteration(token):
                nonlocal iterations
                iterations += 1
                if iterations > MAX_ITERATIONS:
                    raise MollyError("Limit", f"More than {MAX_ITERATIONS} loop iterations", token)

            def while_loop(node, scope, pc):
                laps, restricted = 0, False
                loop_pc = pc
                while True:
                    # Evaluating the condition again depends on the earlier tests,
                    # so from the second lap on it runs under their label.
                    test = condition(node, scope, loop_pc, "while")
                    restricted = restricted or test.audience is not None
                    body_pc = loop_pc = guard(test, loop_pc, node.branches, scope, "while")
                    if not test.data:
                        break
                    count_iteration(node.token)
                    laps += 1
                    execute(node.branches[0], scope, body_pc)
                self.event("WHILE", f"line {node.token.line}: " + (
                    "loop over restricted data" if restricted else f"{laps} iterations"), pc)

            def for_loop(node, scope, pc):
                collection = evaluate(node.children[0], scope, pc)
                kind = type_of(collection.data)

                def iterable():
                    if kind not in ("list", "set", "str"):
                        raise _type_error(f"for iterates over a list, set or str; got {kind}",
                                          node.token)
                shield([collection, pc], node.token, iterable)
                # How many iterations run, and which items arrive, reveals the collection.
                body_pc = guard(collection, pc, node.branches, scope, "for")
                for item in collection.data:
                    count_iteration(node.token)
                    body = Scope(scope)
                    item = Char(item) if kind == "str" else item
                    body.declare(node.extra.text, Value(item, collection.audience, collection.origin),
                                 None)
                    execute(node.branches[0], body, body_pc)
                self.event("FOR", f"line {node.token.line}: " + (
                    "loop over restricted data" if collection.audience is not None
                    else f"{len(collection.data)} iterations"), pc)

            def conditional(node, scope, pc):
                test = condition(node, scope, pc, "if")
                branch_pc = guard(test, pc, node.branches, scope, "condition")
                branch = ("branch chosen on restricted data" if test.audience is not None
                          else f"{'then' if test.data else 'else'} branch")
                self.event("CONDITION", f"line {node.token.line}: {branch}; "
                           "effects of both branches checked", pc)
                execute(node.branches[0] if test.data else node.branches[1], scope, branch_pc)

            execute(program, None, PUBLIC)
            # Commit: every check passed, so the queued sends go out, in order.
            for sink, text, identity, pc in outbox:
                sink.send(context, text)
                self.event("SEND", f"{identity}: recipient allowed; adapter called", pc)
            return {"tokens": [vars(t) for t in tokens], "derivation": parser.derivation,
                    "trace": list(self.trace)}
        except MollyError as error:
            self.event("BLOCKED" if error.phase in ("Policy", "Access") else "REJECTED", str(error))
            raise
        except RecursionError:
            error = MollyError("Limit", "Structural complexity above the allowed maximum")
            self.event("REJECTED", str(error))
            raise error from None
        except Exception:
            # Adapter exceptions might contain sensitive payloads; do not expose them.
            error = MollyError("Adapter", "A registered tool failed")
            self.event("ERROR", str(error))
            raise error from None
