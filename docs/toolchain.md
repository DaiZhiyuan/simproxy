# Toolchain

## Pinned versions

| Component | Version | Notes |
|---|---|---|
| DynamoRIO | `11.91.20756` (cronbuild) | host + AArch64 release tarballs |
| Python | >= 3.10 | tested on 3.12 |
| NumPy | >= 1.24 | clustering core |
| CMake | >= 3.14 | client build |
| QEMU | >= 9.0 recommended | TCG plugins required for metrics |

DynamoRIO is fetched by `scripts/bootstrap_toolchain.sh`; override the version with
`SIMPROXY_DR_VERSION`.

## Host vs. target

The development host in this workspace is **x86_64**. DynamoRIO instrumentation
must run on the same architecture as the target binary, so profiling ARM64
programs requires an **AArch64 execution environment**.

What works on the x86_64 host:

- Building the AArch64 client with `aarch64-linux-gnu-gcc`.
- Running the Python pipeline and unit tests.
- Cross-compiling benchmarks with `aarch64-linux-gnu-gcc`.
- Functional checks of ARM64 binaries under `qemu-aarch64-static` (no timing).

What does **not** work on the x86_64 host:

- Running DynamoRIO itself under `qemu-aarch64-static`. Even an empty client
  crashes because DynamoRIO's code cache and signal handling are not compatible
  with QEMU user-mode emulation. Use an ARM64 host, VM, or container for profiling.

## Build the AArch64 client

```bash
TOOLS=/home/daizhiyuan/workspace/tmpdir/simproxy-tools
cmake -S . -B build -G Ninja \
  -DCMAKE_SYSTEM_NAME=Linux \
  -DCMAKE_SYSTEM_PROCESSOR=aarch64 \
  -DCMAKE_C_COMPILER=aarch64-linux-gnu-gcc \
  -DDynamoRIO_DIR=$TOOLS/DynamoRIO-AArch64-Linux-11.91.20756/cmake
cmake --build build
file build/drclient/libsimproxy_bbv.so   # ELF 64-bit LSB shared object, ARM aarch64
```

## Run on an AArch64 machine

```bash
export DYNAMORIO_HOME=/path/to/DynamoRIO-AArch64-Linux-11.91.20756
export PATH="$DYNAMORIO_HOME/bin64:$PATH"

# Reference fast path shipped with DynamoRIO
drrun -t drpoints -instr_interval 100000000 -out_bbv_file prog.bbv -- ./app

# SimProxy client (clean-call implementation)
drrun -c /path/to/libsimproxy_bbv.so \
  -instr_interval 100000000 -out_file prog.bbv -- ./app
```

## QEMU TCG plugins

QEMU user-mode emulation does not model timing; performance metrics come from TCG
plugins. The plugins live in `contrib/plugins` and require a QEMU built with
`--enable-plugins`.

Useful plugins:

| Plugin | Purpose |
|---|---|
| `libbbv.so` | SimPoint BBVs for cross-checking DynamoRIO |
| `libcache.so` | cache hit/miss metrics |
| `libhowvec.so` | instruction class breakdown |
| `libhotblocks.so` | hot basic blocks |
| `libhotpages.so` | hot memory pages |

The distro `qemu-user-static` package (8.2 here) does **not** ship plugins. Build
QEMU 10.x from source or use a distribution that packages `qemu-plugin`.

```bash
qemu-aarch64 \
  -plugin /path/to/contrib/plugins/libbbv.so,interval=100000000,outfile=app \
  ./app.arm64
```

## Reproducing this workspace

```bash
# Python environment (kept outside the repo in the workspace temp dir)
python3 -m venv /home/daizhiyuan/workspace/tmpdir/simproxy-venv
/home/daizhiyuan/workspace/tmpdir/simproxy-venv/bin/pip install -e '.[dev]'

# Toolchains
SIMPROXY_TOOLS_DIR=/home/daizhiyuan/workspace/tmpdir/simproxy-tools \
  ./scripts/bootstrap_toolchain.sh

# Tests
/home/daizhiyuan/workspace/tmpdir/simproxy-venv/bin/python -m pytest -q
```
