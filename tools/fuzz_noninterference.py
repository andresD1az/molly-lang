# Copyright 2026 Eyner Andres Diaz
# SPDX-License-Identifier: Apache-2.0
"""Noninterference fuzzer: the same random plan runs with two different secrets.

A recipient who may not see the secrets must observe the same thing in both runs:
the same public sends and the same trace. The one accepted difference is whether
the plan finishes or fails, and at which step (the documented abort channel).

Usage:  python tools/fuzz_noninterference.py [plans] [seed]
"""
import collections
import random
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from molly import Context, Engine, MollyError, Sink, Source, Transform, to_text  # noqa: E402

SECRETS = ({"n": 2, "s": "ab", "l": [1, 2], "b": True},
           {"n": 7, "s": "xyz9", "l": [5, 0, 9, 4], "b": False})
HEAD = 'int a = 0; int b = 1; bool q = false; str t = "p"; list l = [1, 2];\n'
INTS = ["a", "b", "1", "2", "0", "sn()", "pn()", "|t|", "|l|", "l[0]", "l[a]"]
TEXTS = ["t", "ss()", "f(t)", '"k"', 't + "z"', '"n=" + a', '"q=" + q', "f(a)", '"" + l']


def run(code, secret):
    """Returns what a public observer sees: public sends, error text and trace."""
    public = []
    owner = frozenset({"owner"})
    engine = Engine(
        sources={"sn": Source(lambda c: secret["n"], lambda c: True, lambda c: owner),
                 "ss": Source(lambda c: secret["s"], lambda c: True, lambda c: owner),
                 "sl": Source(lambda c: secret["l"], lambda c: True, lambda c: owner),
                 "sb": Source(lambda c: secret["b"], lambda c: True, lambda c: owner),
                 "pn": Source(lambda c: 3, lambda c: True, lambda c: None)},
        transforms={"f": Transform(lambda c, value: to_text(value) + "!", arity=1)},
        sinks={"pub": Sink(lambda c: "public", lambda c, text: public.append(text)),
               "own": Sink(lambda c: "owner", lambda c, text: None)})
    try:
        engine.run(code, Context("t", "u"))
        error = None
    except MollyError as failure:
        error = str(failure)
    return public, error, [(event["operation"], event["detail"]) for event in engine.trace]


def random_plan(rng):
    def integer(depth=0):
        if depth > 1 or rng.random() < .4:
            return rng.choice(INTS)
        return f"({integer(depth + 1)} {rng.choice('+-*%')} {integer(depth + 1)})"

    def boolean():
        roll = rng.random()
        if roll < .5:
            return f"{integer()} {rng.choice(['<', '==', '>', '!='])} {integer()}"
        if roll < .7:
            return rng.choice(["sb()", "q", "not q", "q and sb()"])
        return f"{integer()} in l"

    def statement(depth=0):
        roll = rng.random()
        if roll < .2:
            return f"{rng.choice('ab')} = {integer()};"
        if roll < .28:
            return f"q = {boolean()};"
        if roll < .36:
            return f"t = {rng.choice(TEXTS)};"
        if roll < .44:
            return f"l = {rng.choice(['sl()', '[1, 2, 3]', '[a, b]', '[1 .. a]'])};"
        if roll < .62:
            return f"send {rng.choice(['pub', 'pub', 'own'])}({rng.choice(TEXTS)});"
        if depth > 1:
            return f"a = {integer()};"
        if roll < .8:
            return (f"if {boolean()} then {statement(depth + 1)} {statement(depth + 1)} "
                    f"else {statement(depth + 1)} end")
        if roll < .9:
            collection = rng.choice(["l", "t", "[1 .. a]", "sl()", "ss()"])
            return f"for i{depth} in {collection} do {statement(depth + 1)} end"
        return f"while a < {integer()} do a = a + 1; {statement(depth + 1)} end"

    return HEAD + "\n".join(statement() for _ in range(rng.randint(1, 5)))


def check(plans=300, seed=11):
    """Runs `plans` random plans; returns (stats, list of leaking plans)."""
    rng = random.Random(seed)
    stats, leaks = collections.Counter(), []
    for _ in range(plans):
        code = random_plan(rng)
        (out_a, err_a, trace_a), (out_b, err_b, trace_b) = (run(code, s) for s in SECRETS)
        # Atomic sends: a plan that fails must deliver nothing.
        if (err_a is not None and out_a) or (err_b is not None and out_b):
            leaks.append(("sends from a failed plan", code))
        elif err_a is None and err_b is None:
            stats["both finish"] += 1
            if out_a != out_b:
                leaks.append(("public output", code))
            elif trace_a != trace_b:
                leaks.append(("trace", code))
        elif err_a == err_b and trace_a == trace_b:
            stats["both fail alike"] += 1
        else:
            # Whether the plan fails, and at which step, may depend on a secret.
            stats["abort channel"] += 1
    return stats, leaks


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    count = int(sys.argv[1]) if len(sys.argv) > 1 else 300
    stats, leaks = check(count, int(sys.argv[2]) if len(sys.argv) > 2 else 11)
    print(dict(stats))
    for kind, code in leaks[:5]:
        print(f"--- LEAK ({kind})\n{code}")
    print(f"{len(leaks)} leaks in {count} plans")
    sys.exit(1 if leaks else 0)
