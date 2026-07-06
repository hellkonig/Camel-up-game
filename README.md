# Camel-up-game
Python program of camel up game (2014 German Spiel des Jahres)

## Requirements

- Python 3.10+
- `uv` for local development commands

## Development

Install development dependencies:

```bash
uv sync --extra dev
```

Run the current CLI prototype:

```bash
uv run python main.py
```

Run checks:

```bash
uv run python -m pytest
uv run ruff check .
uv run ruff format --check .
uv run python -m mypy
```

The initial lint and type-check configuration covers the test baseline. The
legacy prototype modules should be brought under stricter checks as they are
refactored into the future package structure.
