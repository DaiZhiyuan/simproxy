# SimProxy

SimProxy turns a real ARM64 program into a small, self-contained **synthetic proxy
executable** that reproduces the architecture-independent behaviour of the original
program (instruction mix, memory footprint, branch behaviour, dependency structure).
The proxy is intended to be fed to a simulator (QEMU) so that a multi-day full-program
simulation can be replaced by a minute-scale proxy run.

The pipeline combines:

- **DynamoRIO** dynamic binary instrumentation for feature collection on AArch64.
- A clean-room implementation of the **SimPoint** phase-clustering algorithm
  (random projection + k-means + BIC model selection).
- A **phase-kernel synthesizer** that emits a native ARM64 proxy program, plus a
  high-fidelity trace-stitching mode used only for validation.
- **QEMU TCG plugins** as the metric/validation backend.

> Status: M5 (packaging). BBV parsing/writing, reference-compatible SimPoint
> clustering, per-interval feature tables and ARM64 proxy code generation are
> available, with a Docker image, examples, and a CI matrix. Fidelity tuning and
> the extended profiler remain pending; see `CHANGELOG.md`.

## Architecture

```
target ELF ──▶ DynamoRIO (drmemtrace / bbv client) ──▶ BBV + extended features
                                                             │
                                                             ▼
                                                     SimPoint clustering
                                                             │
                                                             ▼
                                          phase kernels ──▶ proxy.elf + manifest
                                                             │
                                                             ▼
                                                   qemu-aarch64 (+ plugins)
```

## Install

```bash
pip install -e '.[dev]'
```

Full instructions (Docker, cross toolchain, wheels) are in
[`docs/install.md`](docs/install.md). The Docker image bundles
`aarch64-linux-gnu-gcc` and `qemu-user-static`:

```bash
docker build -t simproxy .
docker run --rm simproxy --version
```

## Quick start

The shortest path is the self-contained example:

```bash
./examples/quickstart.sh
```

### Verifying against reference SimPoint

SimProxy's clustering is a clean-room reimplementation, so it is checked against
the reference SimPoint 3.2 binary (used only as a test oracle):

```bash
SIMPOINT_BIN=/path/to/SimPoint.3.2/bin/simpoint \
  python scripts/validate_simpoint.py prog.bbv --k 3 --strict

SIMPOINT_BIN=/path/to/SimPoint.3.2/bin/simpoint \
  python scripts/benchmark_simpoint.py --cases 20
```

`--backend simpoint` reproduces the reference projection, initialization and
convergence exactly. A 20-case randomized matrix matched all representative
intervals with weight error `<= 3.33e-7`; see `docs/validation.md`. The writer
emits the canonical SimPoint dialect (`T:1:48 :3:24`), so reference tooling can
consume SimProxy `.bbv` files directly.

### Building the DynamoRIO client (AArch64)

```bash
TOOLS=/home/daizhiyuan/workspace/tmpdir/simproxy-tools
cmake -S . -B build -G Ninja \
  -DCMAKE_SYSTEM_NAME=Linux \
  -DCMAKE_SYSTEM_PROCESSOR=aarch64 \
  -DCMAKE_C_COMPILER=aarch64-linux-gnu-gcc \
  -DDynamoRIO_DIR=$TOOLS/DynamoRIO-AArch64-Linux-11.91.20756/cmake
cmake --build build
```

Profiling requires an **AArch64 host/VM**; DynamoRIO does not run correctly under
QEMU user-mode emulation. See `docs/toolchain.md`.

## Repository layout

| Path | Purpose |
|---|---|
| `drclient/` | DynamoRIO client (BBV + extended features) |
| `python/simproxy/` | Profiler, clustering, synthesis, validation, CLI |
| `codegen/` | Proxy kernel emitter |
| `docs/` | Design, data formats, fidelity methodology |
| `tests/` | Unit and end-to-end tests |
| `scripts/` | Toolchain bootstrap and helpers |
| `benchmarks/` | Microbenchmarks and workload drivers |
| `examples/` | Quickstart script and usage examples |
| `Dockerfile` | Image with cross compiler and QEMU |
| `CHANGELOG.md` | Release notes and known limitations |

## License

Apache-2.0. See `LICENSE`.
