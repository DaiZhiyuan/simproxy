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

> Status: M1 (feature extraction). BBV parsing/writing, SimPoint clustering,
> per-interval feature tables, the DynamoRIO BBV client and toolchain bootstrap
> are available. Proxy synthesis arrives in M3.

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

## Quick start

```bash
# 1. Fetch pinned DynamoRIO toolchains (host + AArch64)
SIMPROXY_TOOLS_DIR=/home/daizhiyuan/workspace/tmpdir/simproxy-tools \
  ./scripts/bootstrap_toolchain.sh

# 2. Create a virtualenv and install the package
python3 -m venv /home/daizhiyuan/workspace/tmpdir/simproxy-venv
/home/daizhiyuan/workspace/tmpdir/simproxy-venv/bin/pip install -e '.[dev]'

# 3. Run unit + end-to-end tests
/home/daizhiyuan/workspace/tmpdir/simproxy-venv/bin/python -m pytest -q

# 4. Cluster a BBV and emit a proxy spec
simproxy simpoint -i prog.bbv -o simpoints.json
simproxy synth -i simpoints.json -o proxy_spec.json

# 5. Derive per-interval features (optionally merged with profiler summaries)
simproxy profile -i prog.bbv -o features.jsonl \
  --summary summary.jsonl --opcode-csv opcode_mix.csv
simproxy features validate -i features.jsonl
```

### Verifying against reference SimPoint

SimProxy's clustering is a clean-room reimplementation, so it is checked against
the reference SimPoint 3.2 binary (used only as a test oracle):

```bash
SIMPOINT_BIN=/path/to/SimPoint.3.2/bin/simpoint \
  python scripts/validate_simpoint.py prog.bbv --k 3 --strict
```

The writer emits the canonical SimPoint dialect (`T:1:48 :3:24`), so reference
tooling can consume SimProxy `.bbv` files directly.

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

## License

Apache-2.0. See `LICENSE`.
