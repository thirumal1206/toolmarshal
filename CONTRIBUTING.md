# Contributing

## Workflow

1. Open an issue first for anything bigger than a small fix, so the design is agreed before code is written.
2. Branch from `main`: `feat/<short-name>`, `fix/<short-name>`, `docs/<short-name>`, `chore/<short-name>`.
3. Keep pull requests small and focused on one change. Large changes are split.
4. Every pull request needs green CI and one review. Squash merge only; the PR title becomes the commit on `main`.

## Local setup

```bash
uv sync
uv run pre-commit install --hook-type pre-commit --hook-type commit-msg
```

## Quality gates

All gates run in pre-commit and in CI. A pull request cannot merge if any gate fails.

| Gate | Tool | Rule |
|---|---|---|
| Format | `ruff format` | No diff |
| Lint | `ruff check` | No findings; rule set in `pyproject.toml` |
| Types | `mypy --strict` | No errors |
| Tests | `pytest` | All pass |
| Coverage | `pytest-cov` | At least 90% line and branch coverage |
| Commit messages | `commitizen` | Conventional Commits |
| Secrets | `gitleaks` | No findings |

Run everything at once:

```bash
uv run pre-commit run --all-files && uv run pytest
```

## Commit messages

[Conventional Commits](https://www.conventionalcommits.org/):

```
<type>(<scope>): <summary in imperative mood, lower case, no full stop>

<body: why the change was needed, not what the diff shows>

<footer: Refs #12, BREAKING CHANGE: ...>
```

Types: `feat`, `fix`, `docs`, `refactor`, `perf`, `test`, `build`, `ci`, `chore`.
Summary at most 72 characters. Body wrapped at 72. One logical change per commit.

## Code standards

- Type hints on every function. No `Any` without a comment saying why.
- Pure functions where possible; I/O at the edges.
- Errors: fail loudly at trust boundaries, never swallow an exception without logging it.
- No new dependency without a reason in the PR description.
- Tests describe behaviour, not implementation. One test per behaviour, named `test_<behaviour>`.
- Comments explain why, never what.

## Design decisions

Any decision that is expensive to reverse gets an Architecture Decision Record in `docs/adr/`, using `docs/adr/0000-template.md`.

## Releases

Semantic Versioning. Release notes are generated from commit messages.
