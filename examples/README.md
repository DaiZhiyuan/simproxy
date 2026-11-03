# Examples

## Cluster a BBV and emit a proxy specification

```bash
# 1. Cluster intervals into phases
simproxy simpoint -i prog.bbv -o simpoints.json \
  --interval-instructions 100000000 --k-min 1 --k-max 10

# 2. Emit the proxy specification consumed by the synthesizer (M3)
simproxy synth -i simpoints.json -o proxy_spec.json

# 3. Inspect
python3 -m json.tool simpoints.json
```

## Collect a BBV with DynamoRIO

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
