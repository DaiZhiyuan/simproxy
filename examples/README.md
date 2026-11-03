# Examples

## Quickstart: synthetic workload to ARM64 proxy

`quickstart.sh` creates a three-phase BBV, extracts features, clusters it,
builds a static ARM64 proxy, and runs it under `qemu-aarch64-static` when
available:

```bash
./examples/quickstart.sh
# or choose an output directory
./examples/quickstart.sh /tmp/simproxy-demo
```

Artifacts written to the work directory:

| File | Description |
|---|---|
| `phase_sample.bbv` | Canonical SimPoint BBV |
| `features.jsonl` | Per-interval feature table |
| `simpoints.json` | Selected intervals, weights, BIC |
| `proxy_spec.json` | Phase kernels and instruction budgets |
| `proxy.elf` | Static ARM64 proxy executable |
| `manifest.json` | Hashes, toolchain, and kernel parameters |

## Docker

```bash
docker build -t simproxy .
docker run --rm -v "$PWD:/work" simproxy \
  profile -i /work/prog.bbv -o /work/features.jsonl
docker run --rm -v "$PWD:/work" \
  --entrypoint /opt/simproxy/examples/quickstart.sh simproxy /work
```

## Cluster a BBV and build a proxy

```bash
simproxy profile -i prog.bbv -o features.jsonl \
  --summary summary.jsonl --opcode-csv opcode_mix.csv

simproxy simpoint -i prog.bbv -o simpoints.json \
  --backend simpoint --k-min 1 --k-max 10

simproxy synth -i simpoints.json -o proxy_spec.json \
  --features features.jsonl --emit-elf proxy.elf --manifest manifest.json

qemu-aarch64-static ./proxy.elf
```

Inspect the results:

```bash
python3 -m json.tool simpoints.json
python3 -m json.tool manifest.json
```

## Collect a BBV with DynamoRIO

Requires an AArch64 host/VM:

```bash
export DYNAMORIO_HOME=/path/to/DynamoRIO-AArch64-Linux-11.91.20756
export PATH="$DYNAMORIO_HOME/bin64:$PATH"

./scripts/collect_bbv.sh ./app.arm64 100000000 app.bbv
```

## Collect a BBV with QEMU TCG plugins (cross-check)

Requires a QEMU build with `--enable-plugins`:

```bash
qemu-aarch64 \
  -plugin /path/to/contrib/plugins/libbbv.so,interval=100000000,outfile=app \
  ./app.arm64
```
