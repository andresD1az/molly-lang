# Contributing

Thanks for your interest in Molly. Issues and pull requests are welcome.

## Before you start

- For a security problem, follow [SECURITY.md](SECURITY.md) instead of opening an issue.
- For a new feature or a change to the language, open an issue first so we can agree on the design. The grammar must stay LL(1) and every operation must keep propagating labels.

## Development

Molly needs Python 3.10 or later and has no dependencies.

```bash
python -m unittest -v                         # unit tests
python tools/fuzz_noninterference.py 3000     # noninterference fuzzer
python demo.py --formal grammar               # must end with "Conflicts: 0"
```

If you change the grammar or the transition table, regenerate the tables with `python tools/gen_tables.py` and update [docs/GRAMMAR.md](docs/GRAMMAR.md).

## Pull requests

- Add a test for every bug you fix and every behaviour you add. A security fix needs a test that fails without it.
- Keep the engine free of third-party dependencies.
- Describe the change in [CHANGELOG.md](CHANGELOG.md).

By contributing you agree that your contribution is licensed under the Apache License 2.0, like the rest of the project.
