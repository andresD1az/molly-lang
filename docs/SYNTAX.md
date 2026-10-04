# Molly syntax reference

Everything in the language on one page. A runnable tour: [examples/complete.molly](../examples/complete.molly).

## Declarations and assignment

| What | Molly | Java equivalent |
|---|---|---|
| Constant (type inferred) | `let x = 5;` | `final var x = 5;` |
| Typed variable | `int x = 5;` | `long x = 5;` |
| Assignment (typed variables only) | `x = x + 1;` | `x = x + 1;` |
| Comment | `# text` | `// text` |

`let` values cannot be reassigned. A variable declared with its type can, and the new value must have the same type (an `int` widens to `float`).

## Data types

| Type | Literal | Java / Python |
|---|---|---|
| `int` | `42`, `0` (64-bit) | `long` / `int` |
| `float` | `3.14` | `double` / `float` |
| `bool` | `true`, `false` | `boolean` / `bool` |
| `char` | `'a'`, `'\n'` | `char` / — |
| `str` | `"hello"` | `String` / `str` |
| `list` | `[1, 2, 3]`, `[]`, `[1 .. 10]` | `List` / `list` |
| `set` | `{1, 2}`, `{}`, `{1 .. 5}` | `Set` / `set` |
| `record` | `record {name: "Ana", age: 20}` | `record` / `dict` |
| null | `null` (only for `str`, `list`, `set`, `record`) | `null` / `None` |

Escapes in `str` and `char`: `\"` `\'` `\\` `\n` `\t`. `'a' == "a"` is `false`: a char is not a one-letter str. `1 == true` is `false`: bool is not a number.

## Operators (lowest to highest precedence)

| Level | Operator | Meaning | Math | Java / Python |
|---|---|---|---|---|
| 1 | `p implies q`, `p iff q` | Conditional, biconditional | → ↔ | — |
| 2 | `p or q` | Disjunction | ∨ | `\|\|` / `or` |
| 3 | `p and q` | Conjunction | ∧ | `&&` / `and` |
| 4 | `not p` | Negation | ¬ | `!` / `not` |
| 5 | `== != < <= > >=` | Comparison | = ≠ < ≤ > ≥ | same |
| 5 | `x in C`, `A subset B` | Membership, subset | ∈ ⊆ | `in` / `<=` on sets |
| 6 | `+`, `-`, `union` | Add or concatenate; subtract or set difference; union | + − ∪ | same / `\|` |
| 7 | `*`, `/`, `%`, `intersect` | Multiply, divide (always float), modulo, intersection | × ÷ ∩ | same / `&` |
| 8 | `-a` | Negative | − | same |
| 9 | `x[i]`, `x.field` | Index from 0, record field | — | same |
| — | `\|x\|` | Cardinality or length | \|A\| | `len()` |
| — | `( … )` | Grouping | | same |

Comparisons and `implies`/`iff` do not chain: `1 < 2 < 3` is a syntax error; write the parentheses. `and` and `or` evaluate both sides.

## Control flow

| Structure | Molly | Java |
|---|---|---|
| if | `if cond then … end` | `if (cond) { … }` |
| if / else | `if cond then … else … end` | `if (cond) { … } else { … }` |
| while | `while cond do … end` | `while (cond) { … }` |
| for each | `for x in collection do … end` | `for (var x : collection) { … }` |
| for over a range | `for i in [1 .. 10] do … end` | `for (int i = 1; i <= 10; i++) { … }` |

`for` iterates over a `list`, a `set` or a `str` (one `char` at a time). Declarations inside a block end at its `end`. Every `if` closes with its own `end`, so there is no dangling else. At most 10,000 loop iterations per program.

## Tools

| What | Molly | Note |
|---|---|---|
| Read a source | `let o = current_order();` | Registered by the host application in Python |
| Transform | `let m = draft(o);` | The result inherits the permissions of its arguments |
| Send | `send customer_whatsapp(m);` | Blocked if the recipient may not see the data |

## Keywords

`let` `send` `if` `then` `else` `end` `while` `for` `do` · `and` `or` `not` `implies` `iff` `in` `union` `intersect` `subset` · `true` `false` `null` · `int` `float` `bool` `char` `str` `list` `set` `record`
