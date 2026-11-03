# Installation

## Requirements

- Python 3.10+
- NumPy (installed automatically)
- Optional: `pyarrow` for Parquet feature tables (`pip install 'simproxy[parquet]'`)
- Optional: `aarch64-linux-gnu-gcc` and `qemu-aarch64-static` to build and run
  generated ARM64 proxies on an x86 host

## From source

```bash
git clone <repo-url> simproxy
cd simproxy
python3 -m venv .venv
. .venv/bin/activate
pip install -e '.[dev]'
simproxy --version
python -m pytest -q
```

## From a wheel or sdist

```bash
python -m build
pip install dist/simproxy-*.whl
```

## Docker

The image includes the AArch64 cross compiler and `qemu-user-static`, so the
full pipeline works out of the box:

```bash
docker build -t simproxy .
docker run --rm simproxy --version

# Mount a workspace and run the pipeline
docker run --rm -v "$PWD:/work" simproxy \
  profile -i /work/prog.bbv -o /work/features.jsonl
```

## Cross toolchain (Debian/Ubuntu)

```bash
sudo apt-get install -y gcc-aarch64-linux-gnu libc6-dev-arm64-cross qemu-user-static
aarch64-linux-gnu-gcc -print-file-name=libc.a
qemu-aarch64-static --version
```

`simproxy synth --emit-elf` defaults to `aarch64-linux-gnu-gcc`; override with
`--cc`.

## DynamoRIO client

See `docs/toolchain.md` and `scripts/bootstrap_toolchain.sh`. The client must be
compiled with the AArch64 DynamoRIO package and run on an AArch64 host/VM.

## Verifying an install

```bash
simproxy --version
simproxy --help
./examples/quickstart.sh
```

The quickstart builds a synthetic three-phase workload, clusters it, generates
an ARM64 proxy, and runs it under QEMU when available.
