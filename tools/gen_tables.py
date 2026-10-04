# Copyright 2026 Eyner Andres Diaz
# SPDX-License-Identifier: Apache-2.0
"""Generate the formal tables in docs/TABLES.md and docs/dfa.dot from molly.py.

Usage, from the project root:  python tools/gen_tables.py
The tables are generated from the same data the lexer and parser run on, so the
documentation can never drift from the implementation.
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from molly import (GRAMMAR, dfa_dot, dfa_markdown, first_sets, follow_sets,  # noqa: E402
                   left_recursion, ll1_table)


def symbol(s):
    return f"`<{s}>`" if s in GRAMMAR else f"`{s}`"


def main():
    numbers, lines = {}, []
    for name, productions in GRAMMAR.items():
        for production in productions:
            numbers[(name, tuple(production))] = len(numbers) + 1

    lines += ["# Formal tables generated from molly.py", "",
              "Do not edit by hand: regenerate with `python tools/gen_tables.py`.", "",
              "## 1. DFA transition matrix", "",
              "`·` = qR (reject). `→` start state, `*` accepting states.", "",
              dfa_markdown(), "",
              "## 2. Numbered productions", "", "| # | Production |", "|---|---|"]
    for (name, production), number in numbers.items():
        body = " ".join(symbol(s) for s in production) or "ε"
        lines.append(f"| {number} | `<{name}>` → {body} |")

    first = first_sets()
    follow = follow_sets(first=first)
    lines += ["", "## 3. FIRST and FOLLOW sets", "", "| Nonterminal | FIRST | FOLLOW |",
              "|---|---|---|"]
    for name in GRAMMAR:
        f = ", ".join(f"`{t}`" for t in sorted(first[name]))
        g = ", ".join(f"`{t}`" for t in sorted(follow[name])) or "—"
        lines.append(f"| {name} | {f} | {g} |")

    table, conflicts = ll1_table()
    lines += ["", "## 4. LL(1) parsing table", "",
              "For each nonterminal, which production applies for each lookahead token. "
              "A token missing from its row is a syntax error.", "",
              "| Nonterminal | Lookahead → production |", "|---|---|"]
    for name in GRAMMAR:
        grouped = {}
        for (row, terminal), production in table.items():
            if row == name:
                grouped.setdefault(numbers[(name, tuple(production))], []).append(terminal)
        cells = "; ".join(", ".join(f"`{t}`" for t in sorted(terms)) + f" → {number}"
                          for number, terms in sorted(grouped.items()))
        lines.append(f"| {name} | {cells} |")
    lines += ["", f"**Entries: {len(table)}. Conflicts: {len(conflicts)}. "
              f"Left-recursion cycles: {len(left_recursion())}.**", ""]

    (ROOT / "docs" / "TABLES.md").write_text("\n".join(lines), encoding="utf-8")
    (ROOT / "docs" / "dfa.dot").write_text(dfa_dot() + "\n", encoding="utf-8")
    print("Wrote docs/TABLES.md and docs/dfa.dot")


if __name__ == "__main__":
    main()
