# Release checklist

1. Update `CHANGELOG.md` and bump `version` in `pyproject.toml` and
   `python/simproxy/__init__.py`.
2. Run the full suite:

   ```bash
   ruff check python tests scripts
   python -m pytest -q
   SIMPOINT_BIN=/path/to/simpoint python scripts/benchmark_simpoint.py --cases 20
   ```

3. Build and smoke-test distributions:

   ```bash
   python -m build
   python -m pip install --force-reinstall dist/simproxy-*.whl
   simproxy --version
   ./examples/quickstart.sh
   ```

4. Build the container and run the example:

   ```bash
   docker build -t simproxy .
   docker run --rm simproxy --version
   ```

5. Tag the release and publish:

   ```bash
   git tag -a vX.Y.Z -m "SimProxy vX.Y.Z"
   git push origin vX.Y.Z
   python -m twine upload dist/*
   ```

6. Attach `dist/*` and the validation JSON to the GitHub release.

## Pre-1.0 blockers

- Extended DynamoRIO feature collection must be validated on an AArch64 host.
- M4 fidelity metrics require a QEMU build with TCG plugins.
