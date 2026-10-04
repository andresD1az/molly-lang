# Molly grammar and lexer

How the language is defined formally. The full transition matrix, numbered productions, FIRST/FOLLOW sets and LL(1) table are in [TABLES.md](TABLES.md), generated from the code with `python tools/gen_tables.py`.

## 1. Lexer: a deterministic finite automaton

The lexer is a DFA M = (Q, Σ, δ, q0, F) executed from the table `TRANSITIONS` in [molly.py](../molly.py). It does not use regular-expression libraries.

- **Alphabet.** Σ is split into 30 equivalence classes (letters, digits, quotes, operators, whitespace, other…). Each class is one column of the matrix.
- **States.** 39 states, q0–q38, plus the reject state qR. Every missing cell goes to qR.
- **Longest match.** The DFA reads symbol by symbol without going back. The lexer remembers the last accepting state, so `<=` is one token, `3.14` is a FLOAT, and `3.x` is INT, `.`, IDENT.
- **Keywords.** The DFA recognizes them as IDENT (state q1); a table lookup turns them into their own token. `letter` is an IDENT, `let` is a keyword. Adding a keyword never changes the matrix.
- **Errors.** Every lexical error is reported with line and column. The message depends on the state where the DFA stopped (for example, q2 means an unterminated string). Lexing then resumes.

| Token | Regular expression |
|---|---|
| IDENT | `[A-Za-z_][A-Za-z_0-9]*` |
| INT | `[0-9]+` |
| FLOAT | `[0-9]+\.[0-9]+` |
| STRING | `"([^"\\\n] \| \\["'\\nt])*"` |
| CHAR | `'([^'\\\n] \| \\["'\\nt])'` |
| Operators | `= == != < <= > >= ; + - * / % ( ) [ ] { } , . : \| ..` |
| Comment / whitespace (discarded) | `#[^\n]*` / `[ \t\r\n]+` |

## 2. Grammar (BNF)

```bnf
<Program>       ::= <Statements> EOF
<Statements>    ::= <Statement> <Statements> | ε
<Statement>     ::= let IDENT = <Expression> ;
                  | <Type> IDENT = <Expression> ;
                  | IDENT = <Expression> ;
                  | while <Expression> do <Statements> end
                  | for IDENT in <Expression> do <Statements> end
                  | send IDENT ( <Expression> ) ;
                  | if <Expression> then <Statements> <Else> end
<Type>          ::= int | float | bool | char | str | list | set | record
<Else>          ::= else <Statements> | ε
<Expression>    ::= <Disjunction> <LogicRest>
<LogicRest>     ::= implies <Disjunction> | iff <Disjunction> | ε
<Disjunction>   ::= <Conjunction> <OrRest>
<OrRest>        ::= or <Conjunction> <OrRest> | ε
<Conjunction>   ::= <Negation> <AndRest>
<AndRest>       ::= and <Negation> <AndRest> | ε
<Negation>      ::= not <Negation> | <Relation>
<Relation>      ::= <Sum> <RelationRest>
<RelationRest>  ::= <RelOp> <Sum> | ε
<RelOp>         ::= == | != | < | <= | > | >= | in | subset
<Sum>           ::= <Term> <SumRest>
<SumRest>       ::= + <Term> <SumRest> | - <Term> <SumRest> | union <Term> <SumRest> | ε
<Term>          ::= <Factor> <TermRest>
<TermRest>      ::= * <Factor> <TermRest> | / <Factor> <TermRest> | % <Factor> <TermRest>
                  | intersect <Factor> <TermRest> | ε
<Factor>        ::= - <Factor> | <Postfix>
<Postfix>       ::= <Primary> <Accessors>
<Accessors>     ::= [ <Expression> ] <Accessors> | . IDENT <Accessors> | ε
<Primary>       ::= INT | FLOAT | STRING | CHAR | true | false | null
                  | IDENT <Suffix> | ( <Expression> ) | | <Expression> |
                  | [ <Elements> ] | { <Elements> } | record { <Fields> }
<Suffix>        ::= ( <Arguments> ) | ε
<Arguments>     ::= <Expression> <MoreArguments> | ε
<MoreArguments> ::= , <Expression> <MoreArguments> | ε
<Elements>      ::= <Expression> <ElementsRest> | ε
<ElementsRest>  ::= .. <Expression> | , <Expression> <MoreElements> | ε
<MoreElements>  ::= , <Expression> <MoreElements> | ε
<Fields>        ::= IDENT : <Expression> <MoreFields> | ε
<MoreFields>    ::= , IDENT : <Expression> <MoreFields> | ε
```

90 productions, 31 nonterminals.

## 3. Why the grammar is unambiguous

- **One nonterminal per precedence level.** A single rule such as `E ::= E + E | E * E` gives `1 + 2 * 3` two parse trees, with results 7 and 9. Molly gives each level its own nonterminal (`Disjunction` → `Conjunction` → … → `Term` → `Factor`), so `*` can only appear inside the operand of `+`.
- **No left recursion.** Rules like `Sum ::= Sum + Term | Term` are rewritten as `Sum ::= Term SumRest` and `SumRest ::= + Term SumRest | ε`, which generate the same language. The parser folds the operands to the left, so `10 - 4 - 3` is `(10 - 4) - 3`.
- **Left factoring.** Common prefixes (`IDENT` vs `IDENT ( … )`, `if … end` vs `if … else … end`, `[a, b]` vs `[a .. b]`) are factored into `Suffix`, `Else` and `ElementsRest`.
- **Non-associative levels.** Relations and `implies`/`iff` take exactly one operator, so `a < b < c` and `p implies q implies r` are syntax errors instead of silently meaning something unexpected.
- **No dangling else.** Every `if` closes with its own `end`.
- **LL(1).** The code computes FIRST, FOLLOW and the parsing table: 422 entries, 0 conflicts, 0 left-recursion cycles. In an LL(1) grammar each lookahead token selects exactly one production, so every program has exactly one leftmost derivation and therefore one parse tree. The test suite checks this on every run.

## 4. Error recovery

The parser does not stop at the first error. In panic mode it records the error with line and column, then skips tokens until after a `;` or until a token that can start or close a statement (`let`, a type, `send`, `if`, `while`, `for`, `else`, `end`, EOF). Inside an `if`, an error in the condition resynchronizes at `then`. It stops after 25 errors.

Lexical and syntax errors are listed together, sorted by position. If there are none, the semantic check lists every undeclared or repeated variable, reassigned constant, unknown tool, wrong arity and repeated record field. No side effect runs while any of these errors exist.

## 5. Permissions (information-flow control)

Every value carries an *audience*: the set of recipients allowed to see it (`None` means public).

- **Explicit flow.** The result of any operation (arithmetic, comparison, indexing, building a list or record, a tool call) may only go to recipients that could see **all** of its inputs: the audiences intersect.
- **Implicit flow.** Choosing a branch or repeating a loop reveals information about the condition. Before an `if`, `while` or `for` runs, the engine checks that every send and external processor in the block is allowed for the condition's label. Variables the block could reassign inherit that label even if the branch does not run, so the outcome never depends on the path taken.
- **Checks before effects.** A source's authorization runs before it is queried, an external processor's identity is checked before data reaches it, and a sink's recipient is checked before anything is sent.
