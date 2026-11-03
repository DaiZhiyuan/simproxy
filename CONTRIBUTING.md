# Contributing

## Development setup

```bash
python3 -m venv .venv
.venv/bin/pip install -e '.[dev]'
.venv/bin/python -m pytest -q
.venv/bin/python -m ruff check python tests
```

Build the AArch64 DynamoRIO client (see `docs/toolchain.md`):

```bash
make bootstrap
make drclient
```

## Layout

| Area | Path |
|---|---|
| DynamoRIO client | `drclient/` |
| Python pipeline | `python/simproxy/` |
| Proxy codegen (M3) | `codegen/` |
| Tests | `tests/` |
| Docs | `docs/` |

## Conventions

- Python: 3.10+, `ruff` (E, F, I, UP, B), line length 100.
- C: C11, no comments explaining obvious code; keep the client dependency-light.
- Every pipeline stage must be re-runnable from its on-disk artifacts and covered
  by a test.
- Data format changes require updating `docs/data-format.md` and the version field.
- No secrets, no vendored binaries; toolchains are fetched by
  `scripts/bootstrap_toolchain.sh`.

## Commit style

Short imperative subject, optional body. Do not commit generated artifacts
(`*.bbv`, `build/`, `.tools/`).
