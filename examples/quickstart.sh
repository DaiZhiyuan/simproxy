#!/usr/bin/env bash
set -euo pipefail

script_dir=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
workdir=${1:-$(mktemp -d)}
mkdir -p "$workdir"

simproxy_bin=${SIMPROXY:-simproxy}

python "$script_dir/make_sample_bbv.py" "$workdir/phase_sample.bbv"

"$simproxy_bin" profile \
  -i "$workdir/phase_sample.bbv" \
  -o "$workdir/features.jsonl"

"$simproxy_bin" simpoint \
  -i "$workdir/phase_sample.bbv" \
  -o "$workdir/simpoints.json" \
  --backend simpoint --k-min 3 --k-max 3

"$simproxy_bin" synth \
  -i "$workdir/simpoints.json" \
  -o "$workdir/proxy_spec.json" \
  --features "$workdir/features.jsonl" \
  --emit-elf "$workdir/proxy.elf" \
  --manifest "$workdir/manifest.json"

if command -v qemu-aarch64-static >/dev/null 2>&1; then
  qemu-aarch64-static "$workdir/proxy.elf"
else
  echo "qemu-aarch64-static not found; built $workdir/proxy.elf"
fi

echo "artifacts:"
ls -1 "$workdir"
