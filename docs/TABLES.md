# Formal tables generated from molly.py

Do not edit by hand: regenerate with `python tools/gen_tables.py`.

## 1. DFA transition matrix

`·` = qR (reject). `→` start state, `*` accepting states.

| State | letter | n_t | digit | dquote | squote | backslash | equals | bang | less | greater | dot | semicolon | plus | minus | star | slash | percent | lparen | rparen | lbracket | rbracket | lbrace | rbrace | comma | colon | pipe | hash | newline | space | other | Accepts |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| →q0 | q1 | q1 | q13 | q2 | q16 | · | q5 | q7 | q9 | q11 | q35 | q22 | q23 | q24 | q25 | q26 | q27 | q28 | q29 | q30 | q31 | q32 | q33 | q34 | q36 | q37 | q20 | q21 | q21 | · | — |
| *q1 | q1 | q1 | q1 | · | · | · | · | · | · | · | · | · | · | · | · | · | · | · | · | · | · | · | · | · | · | · | · | · | · | · | IDENT |
| q2 | q2 | q2 | q2 | q4 | q2 | q3 | q2 | q2 | q2 | q2 | q2 | q2 | q2 | q2 | q2 | q2 | q2 | q2 | q2 | q2 | q2 | q2 | q2 | q2 | q2 | q2 | q2 | · | q2 | q2 | — |
| q3 | · | q2 | · | q2 | q2 | q2 | · | · | · | · | · | · | · | · | · | · | · | · | · | · | · | · | · | · | · | · | · | · | · | · | — |
| *q4 | · | · | · | · | · | · | · | · | · | · | · | · | · | · | · | · | · | · | · | · | · | · | · | · | · | · | · | · | · | · | STRING |
| *q5 | · | · | · | · | · | · | q6 | · | · | · | · | · | · | · | · | · | · | · | · | · | · | · | · | · | · | · | · | · | · | · | = |
| *q6 | · | · | · | · | · | · | · | · | · | · | · | · | · | · | · | · | · | · | · | · | · | · | · | · | · | · | · | · | · | · | == |
| q7 | · | · | · | · | · | · | q8 | · | · | · | · | · | · | · | · | · | · | · | · | · | · | · | · | · | · | · | · | · | · | · | — |
| *q8 | · | · | · | · | · | · | · | · | · | · | · | · | · | · | · | · | · | · | · | · | · | · | · | · | · | · | · | · | · | · | != |
| *q9 | · | · | · | · | · | · | q10 | · | · | · | · | · | · | · | · | · | · | · | · | · | · | · | · | · | · | · | · | · | · | · | < |
| *q10 | · | · | · | · | · | · | · | · | · | · | · | · | · | · | · | · | · | · | · | · | · | · | · | · | · | · | · | · | · | · | <= |
| *q11 | · | · | · | · | · | · | q12 | · | · | · | · | · | · | · | · | · | · | · | · | · | · | · | · | · | · | · | · | · | · | · | > |
| *q12 | · | · | · | · | · | · | · | · | · | · | · | · | · | · | · | · | · | · | · | · | · | · | · | · | · | · | · | · | · | · | >= |
| *q13 | · | · | q13 | · | · | · | · | · | · | · | q14 | · | · | · | · | · | · | · | · | · | · | · | · | · | · | · | · | · | · | · | INT |
| q14 | · | · | q15 | · | · | · | · | · | · | · | · | · | · | · | · | · | · | · | · | · | · | · | · | · | · | · | · | · | · | · | — |
| *q15 | · | · | q15 | · | · | · | · | · | · | · | · | · | · | · | · | · | · | · | · | · | · | · | · | · | · | · | · | · | · | · | FLOAT |
| q16 | q18 | q18 | q18 | q18 | · | q17 | q18 | q18 | q18 | q18 | q18 | q18 | q18 | q18 | q18 | q18 | q18 | q18 | q18 | q18 | q18 | q18 | q18 | q18 | q18 | q18 | q18 | · | q18 | q18 | — |
| q17 | · | q18 | · | q18 | q18 | q18 | · | · | · | · | · | · | · | · | · | · | · | · | · | · | · | · | · | · | · | · | · | · | · | · | — |
| q18 | · | · | · | · | q19 | · | · | · | · | · | · | · | · | · | · | · | · | · | · | · | · | · | · | · | · | · | · | · | · | · | — |
| *q19 | · | · | · | · | · | · | · | · | · | · | · | · | · | · | · | · | · | · | · | · | · | · | · | · | · | · | · | · | · | · | CHAR |
| *q20 | q20 | q20 | q20 | q20 | q20 | q20 | q20 | q20 | q20 | q20 | q20 | q20 | q20 | q20 | q20 | q20 | q20 | q20 | q20 | q20 | q20 | q20 | q20 | q20 | q20 | q20 | q20 | · | q20 | q20 | COMMENT |
| *q21 | · | · | · | · | · | · | · | · | · | · | · | · | · | · | · | · | · | · | · | · | · | · | · | · | · | · | · | q21 | q21 | · | WHITESPACE |
| *q22 | · | · | · | · | · | · | · | · | · | · | · | · | · | · | · | · | · | · | · | · | · | · | · | · | · | · | · | · | · | · | ; |
| *q23 | · | · | · | · | · | · | · | · | · | · | · | · | · | · | · | · | · | · | · | · | · | · | · | · | · | · | · | · | · | · | + |
| *q24 | · | · | · | · | · | · | · | · | · | · | · | · | · | · | · | · | · | · | · | · | · | · | · | · | · | · | · | · | · | · | - |
| *q25 | · | · | · | · | · | · | · | · | · | · | · | · | · | · | · | · | · | · | · | · | · | · | · | · | · | · | · | · | · | · | * |
| *q26 | · | · | · | · | · | · | · | · | · | · | · | · | · | · | · | · | · | · | · | · | · | · | · | · | · | · | · | · | · | · | / |
| *q27 | · | · | · | · | · | · | · | · | · | · | · | · | · | · | · | · | · | · | · | · | · | · | · | · | · | · | · | · | · | · | % |
| *q28 | · | · | · | · | · | · | · | · | · | · | · | · | · | · | · | · | · | · | · | · | · | · | · | · | · | · | · | · | · | · | ( |
| *q29 | · | · | · | · | · | · | · | · | · | · | · | · | · | · | · | · | · | · | · | · | · | · | · | · | · | · | · | · | · | · | ) |
| *q30 | · | · | · | · | · | · | · | · | · | · | · | · | · | · | · | · | · | · | · | · | · | · | · | · | · | · | · | · | · | · | [ |
| *q31 | · | · | · | · | · | · | · | · | · | · | · | · | · | · | · | · | · | · | · | · | · | · | · | · | · | · | · | · | · | · | ] |
| *q32 | · | · | · | · | · | · | · | · | · | · | · | · | · | · | · | · | · | · | · | · | · | · | · | · | · | · | · | · | · | · | { |
| *q33 | · | · | · | · | · | · | · | · | · | · | · | · | · | · | · | · | · | · | · | · | · | · | · | · | · | · | · | · | · | · | } |
| *q34 | · | · | · | · | · | · | · | · | · | · | · | · | · | · | · | · | · | · | · | · | · | · | · | · | · | · | · | · | · | · | , |
| *q35 | · | · | · | · | · | · | · | · | · | · | q38 | · | · | · | · | · | · | · | · | · | · | · | · | · | · | · | · | · | · | · | . |
| *q36 | · | · | · | · | · | · | · | · | · | · | · | · | · | · | · | · | · | · | · | · | · | · | · | · | · | · | · | · | · | · | : |
| *q37 | · | · | · | · | · | · | · | · | · | · | · | · | · | · | · | · | · | · | · | · | · | · | · | · | · | · | · | · | · | · | | |
| *q38 | · | · | · | · | · | · | · | · | · | · | · | · | · | · | · | · | · | · | · | · | · | · | · | · | · | · | · | · | · | · | .. |
| qR | · | · | · | · | · | · | · | · | · | · | · | · | · | · | · | · | · | · | · | · | · | · | · | · | · | · | · | · | · | · | reject |

## 2. Numbered productions

| # | Production |
|---|---|
| 1 | `<Program>` → `<Statements>` `EOF` |
| 2 | `<Statements>` → `<Statement>` `<Statements>` |
| 3 | `<Statements>` → ε |
| 4 | `<Statement>` → `let` `IDENT` `=` `<Expression>` `;` |
| 5 | `<Statement>` → `<Type>` `IDENT` `=` `<Expression>` `;` |
| 6 | `<Statement>` → `IDENT` `=` `<Expression>` `;` |
| 7 | `<Statement>` → `while` `<Expression>` `do` `<Statements>` `end` |
| 8 | `<Statement>` → `for` `IDENT` `in` `<Expression>` `do` `<Statements>` `end` |
| 9 | `<Statement>` → `send` `IDENT` `(` `<Expression>` `)` `;` |
| 10 | `<Statement>` → `if` `<Expression>` `then` `<Statements>` `<Else>` `end` |
| 11 | `<Type>` → `int` |
| 12 | `<Type>` → `float` |
| 13 | `<Type>` → `bool` |
| 14 | `<Type>` → `char` |
| 15 | `<Type>` → `str` |
| 16 | `<Type>` → `list` |
| 17 | `<Type>` → `set` |
| 18 | `<Type>` → `record` |
| 19 | `<Else>` → `else` `<Statements>` |
| 20 | `<Else>` → ε |
| 21 | `<Expression>` → `<Disjunction>` `<LogicRest>` |
| 22 | `<LogicRest>` → `implies` `<Disjunction>` |
| 23 | `<LogicRest>` → `iff` `<Disjunction>` |
| 24 | `<LogicRest>` → ε |
| 25 | `<Disjunction>` → `<Conjunction>` `<OrRest>` |
| 26 | `<OrRest>` → `or` `<Conjunction>` `<OrRest>` |
| 27 | `<OrRest>` → ε |
| 28 | `<Conjunction>` → `<Negation>` `<AndRest>` |
| 29 | `<AndRest>` → `and` `<Negation>` `<AndRest>` |
| 30 | `<AndRest>` → ε |
| 31 | `<Negation>` → `not` `<Negation>` |
| 32 | `<Negation>` → `<Relation>` |
| 33 | `<Relation>` → `<Sum>` `<RelationRest>` |
| 34 | `<RelationRest>` → `<RelOp>` `<Sum>` |
| 35 | `<RelationRest>` → ε |
| 36 | `<RelOp>` → `==` |
| 37 | `<RelOp>` → `!=` |
| 38 | `<RelOp>` → `<` |
| 39 | `<RelOp>` → `<=` |
| 40 | `<RelOp>` → `>` |
| 41 | `<RelOp>` → `>=` |
| 42 | `<RelOp>` → `in` |
| 43 | `<RelOp>` → `subset` |
| 44 | `<Sum>` → `<Term>` `<SumRest>` |
| 45 | `<SumRest>` → `+` `<Term>` `<SumRest>` |
| 46 | `<SumRest>` → `-` `<Term>` `<SumRest>` |
| 47 | `<SumRest>` → `union` `<Term>` `<SumRest>` |
| 48 | `<SumRest>` → ε |
| 49 | `<Term>` → `<Factor>` `<TermRest>` |
| 50 | `<TermRest>` → `*` `<Factor>` `<TermRest>` |
| 51 | `<TermRest>` → `/` `<Factor>` `<TermRest>` |
| 52 | `<TermRest>` → `%` `<Factor>` `<TermRest>` |
| 53 | `<TermRest>` → `intersect` `<Factor>` `<TermRest>` |
| 54 | `<TermRest>` → ε |
| 55 | `<Factor>` → `-` `<Factor>` |
| 56 | `<Factor>` → `<Postfix>` |
| 57 | `<Postfix>` → `<Primary>` `<Accessors>` |
| 58 | `<Accessors>` → `[` `<Expression>` `]` `<Accessors>` |
| 59 | `<Accessors>` → `.` `IDENT` `<Accessors>` |
| 60 | `<Accessors>` → ε |
| 61 | `<Primary>` → `INT` |
| 62 | `<Primary>` → `FLOAT` |
| 63 | `<Primary>` → `STRING` |
| 64 | `<Primary>` → `CHAR` |
| 65 | `<Primary>` → `true` |
| 66 | `<Primary>` → `false` |
| 67 | `<Primary>` → `null` |
| 68 | `<Primary>` → `IDENT` `<Suffix>` |
| 69 | `<Primary>` → `(` `<Expression>` `)` |
| 70 | `<Primary>` → `[` `<Elements>` `]` |
| 71 | `<Primary>` → `{` `<Elements>` `}` |
| 72 | `<Primary>` → `record` `{` `<Fields>` `}` |
| 73 | `<Primary>` → `|` `<Expression>` `|` |
| 74 | `<Suffix>` → `(` `<Arguments>` `)` |
| 75 | `<Suffix>` → ε |
| 76 | `<Arguments>` → `<Expression>` `<MoreArguments>` |
| 77 | `<Arguments>` → ε |
| 78 | `<MoreArguments>` → `,` `<Expression>` `<MoreArguments>` |
| 79 | `<MoreArguments>` → ε |
| 80 | `<Elements>` → `<Expression>` `<ElementsRest>` |
| 81 | `<Elements>` → ε |
| 82 | `<ElementsRest>` → `..` `<Expression>` |
| 83 | `<ElementsRest>` → `,` `<Expression>` `<MoreElements>` |
| 84 | `<ElementsRest>` → ε |
| 85 | `<MoreElements>` → `,` `<Expression>` `<MoreElements>` |
| 86 | `<MoreElements>` → ε |
| 87 | `<Fields>` → `IDENT` `:` `<Expression>` `<MoreFields>` |
| 88 | `<Fields>` → ε |
| 89 | `<MoreFields>` → `,` `IDENT` `:` `<Expression>` `<MoreFields>` |
| 90 | `<MoreFields>` → ε |

## 3. FIRST and FOLLOW sets

| Nonterminal | FIRST | FOLLOW |
|---|---|---|
| Program | `EOF`, `IDENT`, `bool`, `char`, `float`, `for`, `if`, `int`, `let`, `list`, `record`, `send`, `set`, `str`, `while` | — |
| Statements | `IDENT`, `bool`, `char`, `float`, `for`, `if`, `int`, `let`, `list`, `record`, `send`, `set`, `str`, `while`, `ε` | `EOF`, `else`, `end` |
| Statement | `IDENT`, `bool`, `char`, `float`, `for`, `if`, `int`, `let`, `list`, `record`, `send`, `set`, `str`, `while` | `EOF`, `IDENT`, `bool`, `char`, `else`, `end`, `float`, `for`, `if`, `int`, `let`, `list`, `record`, `send`, `set`, `str`, `while` |
| Type | `bool`, `char`, `float`, `int`, `list`, `record`, `set`, `str` | `IDENT` |
| Else | `else`, `ε` | `end` |
| Expression | `(`, `-`, `CHAR`, `FLOAT`, `IDENT`, `INT`, `STRING`, `[`, `false`, `not`, `null`, `record`, `true`, `{`, `|` | `)`, `,`, `..`, `;`, `]`, `do`, `then`, `|`, `}` |
| LogicRest | `iff`, `implies`, `ε` | `)`, `,`, `..`, `;`, `]`, `do`, `then`, `|`, `}` |
| Disjunction | `(`, `-`, `CHAR`, `FLOAT`, `IDENT`, `INT`, `STRING`, `[`, `false`, `not`, `null`, `record`, `true`, `{`, `|` | `)`, `,`, `..`, `;`, `]`, `do`, `iff`, `implies`, `then`, `|`, `}` |
| OrRest | `or`, `ε` | `)`, `,`, `..`, `;`, `]`, `do`, `iff`, `implies`, `then`, `|`, `}` |
| Conjunction | `(`, `-`, `CHAR`, `FLOAT`, `IDENT`, `INT`, `STRING`, `[`, `false`, `not`, `null`, `record`, `true`, `{`, `|` | `)`, `,`, `..`, `;`, `]`, `do`, `iff`, `implies`, `or`, `then`, `|`, `}` |
| AndRest | `and`, `ε` | `)`, `,`, `..`, `;`, `]`, `do`, `iff`, `implies`, `or`, `then`, `|`, `}` |
| Negation | `(`, `-`, `CHAR`, `FLOAT`, `IDENT`, `INT`, `STRING`, `[`, `false`, `not`, `null`, `record`, `true`, `{`, `|` | `)`, `,`, `..`, `;`, `]`, `and`, `do`, `iff`, `implies`, `or`, `then`, `|`, `}` |
| Relation | `(`, `-`, `CHAR`, `FLOAT`, `IDENT`, `INT`, `STRING`, `[`, `false`, `null`, `record`, `true`, `{`, `|` | `)`, `,`, `..`, `;`, `]`, `and`, `do`, `iff`, `implies`, `or`, `then`, `|`, `}` |
| RelationRest | `!=`, `<`, `<=`, `==`, `>`, `>=`, `in`, `subset`, `ε` | `)`, `,`, `..`, `;`, `]`, `and`, `do`, `iff`, `implies`, `or`, `then`, `|`, `}` |
| RelOp | `!=`, `<`, `<=`, `==`, `>`, `>=`, `in`, `subset` | `(`, `-`, `CHAR`, `FLOAT`, `IDENT`, `INT`, `STRING`, `[`, `false`, `null`, `record`, `true`, `{`, `|` |
| Sum | `(`, `-`, `CHAR`, `FLOAT`, `IDENT`, `INT`, `STRING`, `[`, `false`, `null`, `record`, `true`, `{`, `|` | `!=`, `)`, `,`, `..`, `;`, `<`, `<=`, `==`, `>`, `>=`, `]`, `and`, `do`, `iff`, `implies`, `in`, `or`, `subset`, `then`, `|`, `}` |
| SumRest | `+`, `-`, `union`, `ε` | `!=`, `)`, `,`, `..`, `;`, `<`, `<=`, `==`, `>`, `>=`, `]`, `and`, `do`, `iff`, `implies`, `in`, `or`, `subset`, `then`, `|`, `}` |
| Term | `(`, `-`, `CHAR`, `FLOAT`, `IDENT`, `INT`, `STRING`, `[`, `false`, `null`, `record`, `true`, `{`, `|` | `!=`, `)`, `+`, `,`, `-`, `..`, `;`, `<`, `<=`, `==`, `>`, `>=`, `]`, `and`, `do`, `iff`, `implies`, `in`, `or`, `subset`, `then`, `union`, `|`, `}` |
| TermRest | `%`, `*`, `/`, `intersect`, `ε` | `!=`, `)`, `+`, `,`, `-`, `..`, `;`, `<`, `<=`, `==`, `>`, `>=`, `]`, `and`, `do`, `iff`, `implies`, `in`, `or`, `subset`, `then`, `union`, `|`, `}` |
| Factor | `(`, `-`, `CHAR`, `FLOAT`, `IDENT`, `INT`, `STRING`, `[`, `false`, `null`, `record`, `true`, `{`, `|` | `!=`, `%`, `)`, `*`, `+`, `,`, `-`, `..`, `/`, `;`, `<`, `<=`, `==`, `>`, `>=`, `]`, `and`, `do`, `iff`, `implies`, `in`, `intersect`, `or`, `subset`, `then`, `union`, `|`, `}` |
| Postfix | `(`, `CHAR`, `FLOAT`, `IDENT`, `INT`, `STRING`, `[`, `false`, `null`, `record`, `true`, `{`, `|` | `!=`, `%`, `)`, `*`, `+`, `,`, `-`, `..`, `/`, `;`, `<`, `<=`, `==`, `>`, `>=`, `]`, `and`, `do`, `iff`, `implies`, `in`, `intersect`, `or`, `subset`, `then`, `union`, `|`, `}` |
| Accessors | `.`, `[`, `ε` | `!=`, `%`, `)`, `*`, `+`, `,`, `-`, `..`, `/`, `;`, `<`, `<=`, `==`, `>`, `>=`, `]`, `and`, `do`, `iff`, `implies`, `in`, `intersect`, `or`, `subset`, `then`, `union`, `|`, `}` |
| Primary | `(`, `CHAR`, `FLOAT`, `IDENT`, `INT`, `STRING`, `[`, `false`, `null`, `record`, `true`, `{`, `|` | `!=`, `%`, `)`, `*`, `+`, `,`, `-`, `.`, `..`, `/`, `;`, `<`, `<=`, `==`, `>`, `>=`, `[`, `]`, `and`, `do`, `iff`, `implies`, `in`, `intersect`, `or`, `subset`, `then`, `union`, `|`, `}` |
| Suffix | `(`, `ε` | `!=`, `%`, `)`, `*`, `+`, `,`, `-`, `.`, `..`, `/`, `;`, `<`, `<=`, `==`, `>`, `>=`, `[`, `]`, `and`, `do`, `iff`, `implies`, `in`, `intersect`, `or`, `subset`, `then`, `union`, `|`, `}` |
| Arguments | `(`, `-`, `CHAR`, `FLOAT`, `IDENT`, `INT`, `STRING`, `[`, `false`, `not`, `null`, `record`, `true`, `{`, `|`, `ε` | `)` |
| MoreArguments | `,`, `ε` | `)` |
| Elements | `(`, `-`, `CHAR`, `FLOAT`, `IDENT`, `INT`, `STRING`, `[`, `false`, `not`, `null`, `record`, `true`, `{`, `|`, `ε` | `]`, `}` |
| ElementsRest | `,`, `..`, `ε` | `]`, `}` |
| MoreElements | `,`, `ε` | `]`, `}` |
| Fields | `IDENT`, `ε` | `}` |
| MoreFields | `,`, `ε` | `}` |

## 4. LL(1) parsing table

For each nonterminal, which production applies for each lookahead token. A token missing from its row is a syntax error.

| Nonterminal | Lookahead → production |
|---|---|
| Program | `EOF`, `IDENT`, `bool`, `char`, `float`, `for`, `if`, `int`, `let`, `list`, `record`, `send`, `set`, `str`, `while` → 1 |
| Statements | `IDENT`, `bool`, `char`, `float`, `for`, `if`, `int`, `let`, `list`, `record`, `send`, `set`, `str`, `while` → 2; `EOF`, `else`, `end` → 3 |
| Statement | `let` → 4; `bool`, `char`, `float`, `int`, `list`, `record`, `set`, `str` → 5; `IDENT` → 6; `while` → 7; `for` → 8; `send` → 9; `if` → 10 |
| Type | `int` → 11; `float` → 12; `bool` → 13; `char` → 14; `str` → 15; `list` → 16; `set` → 17; `record` → 18 |
| Else | `else` → 19; `end` → 20 |
| Expression | `(`, `-`, `CHAR`, `FLOAT`, `IDENT`, `INT`, `STRING`, `[`, `false`, `not`, `null`, `record`, `true`, `{`, `|` → 21 |
| LogicRest | `implies` → 22; `iff` → 23; `)`, `,`, `..`, `;`, `]`, `do`, `then`, `|`, `}` → 24 |
| Disjunction | `(`, `-`, `CHAR`, `FLOAT`, `IDENT`, `INT`, `STRING`, `[`, `false`, `not`, `null`, `record`, `true`, `{`, `|` → 25 |
| OrRest | `or` → 26; `)`, `,`, `..`, `;`, `]`, `do`, `iff`, `implies`, `then`, `|`, `}` → 27 |
| Conjunction | `(`, `-`, `CHAR`, `FLOAT`, `IDENT`, `INT`, `STRING`, `[`, `false`, `not`, `null`, `record`, `true`, `{`, `|` → 28 |
| AndRest | `and` → 29; `)`, `,`, `..`, `;`, `]`, `do`, `iff`, `implies`, `or`, `then`, `|`, `}` → 30 |
| Negation | `not` → 31; `(`, `-`, `CHAR`, `FLOAT`, `IDENT`, `INT`, `STRING`, `[`, `false`, `null`, `record`, `true`, `{`, `|` → 32 |
| Relation | `(`, `-`, `CHAR`, `FLOAT`, `IDENT`, `INT`, `STRING`, `[`, `false`, `null`, `record`, `true`, `{`, `|` → 33 |
| RelationRest | `!=`, `<`, `<=`, `==`, `>`, `>=`, `in`, `subset` → 34; `)`, `,`, `..`, `;`, `]`, `and`, `do`, `iff`, `implies`, `or`, `then`, `|`, `}` → 35 |
| RelOp | `==` → 36; `!=` → 37; `<` → 38; `<=` → 39; `>` → 40; `>=` → 41; `in` → 42; `subset` → 43 |
| Sum | `(`, `-`, `CHAR`, `FLOAT`, `IDENT`, `INT`, `STRING`, `[`, `false`, `null`, `record`, `true`, `{`, `|` → 44 |
| SumRest | `+` → 45; `-` → 46; `union` → 47; `!=`, `)`, `,`, `..`, `;`, `<`, `<=`, `==`, `>`, `>=`, `]`, `and`, `do`, `iff`, `implies`, `in`, `or`, `subset`, `then`, `|`, `}` → 48 |
| Term | `(`, `-`, `CHAR`, `FLOAT`, `IDENT`, `INT`, `STRING`, `[`, `false`, `null`, `record`, `true`, `{`, `|` → 49 |
| TermRest | `*` → 50; `/` → 51; `%` → 52; `intersect` → 53; `!=`, `)`, `+`, `,`, `-`, `..`, `;`, `<`, `<=`, `==`, `>`, `>=`, `]`, `and`, `do`, `iff`, `implies`, `in`, `or`, `subset`, `then`, `union`, `|`, `}` → 54 |
| Factor | `-` → 55; `(`, `CHAR`, `FLOAT`, `IDENT`, `INT`, `STRING`, `[`, `false`, `null`, `record`, `true`, `{`, `|` → 56 |
| Postfix | `(`, `CHAR`, `FLOAT`, `IDENT`, `INT`, `STRING`, `[`, `false`, `null`, `record`, `true`, `{`, `|` → 57 |
| Accessors | `[` → 58; `.` → 59; `!=`, `%`, `)`, `*`, `+`, `,`, `-`, `..`, `/`, `;`, `<`, `<=`, `==`, `>`, `>=`, `]`, `and`, `do`, `iff`, `implies`, `in`, `intersect`, `or`, `subset`, `then`, `union`, `|`, `}` → 60 |
| Primary | `INT` → 61; `FLOAT` → 62; `STRING` → 63; `CHAR` → 64; `true` → 65; `false` → 66; `null` → 67; `IDENT` → 68; `(` → 69; `[` → 70; `{` → 71; `record` → 72; `|` → 73 |
| Suffix | `(` → 74; `!=`, `%`, `)`, `*`, `+`, `,`, `-`, `.`, `..`, `/`, `;`, `<`, `<=`, `==`, `>`, `>=`, `[`, `]`, `and`, `do`, `iff`, `implies`, `in`, `intersect`, `or`, `subset`, `then`, `union`, `|`, `}` → 75 |
| Arguments | `(`, `-`, `CHAR`, `FLOAT`, `IDENT`, `INT`, `STRING`, `[`, `false`, `not`, `null`, `record`, `true`, `{`, `|` → 76; `)` → 77 |
| MoreArguments | `,` → 78; `)` → 79 |
| Elements | `(`, `-`, `CHAR`, `FLOAT`, `IDENT`, `INT`, `STRING`, `[`, `false`, `not`, `null`, `record`, `true`, `{`, `|` → 80; `]`, `}` → 81 |
| ElementsRest | `..` → 82; `,` → 83; `]`, `}` → 84 |
| MoreElements | `,` → 85; `]`, `}` → 86 |
| Fields | `IDENT` → 87; `}` → 88 |
| MoreFields | `,` → 89; `}` → 90 |

**Entries: 422. Conflicts: 0. Left-recursion cycles: 0.**
