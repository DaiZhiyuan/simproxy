# Benchmarks

M0 ships a small microbenchmark to exercise the profiler and clustering stages
without external workloads. Real workloads (coremark, SPEC subsets) arrive in M1.

## Microbenchmarks

| Source | Behaviour |
|---|---|
| `micro/loop.c` | tight integer loop, high branch predictability |
| `micro/stream.c` | streaming memory access, large working set |
| `micro/mixed.c` | alternating compute / memory phases |

Build for ARM64:

```bash
aarch64-linux-gnu-gcc -O2 -static benchmarks/micro/loop.c -o loop.arm64
```

Run natively on an AArch64 host, or under `qemu-aarch64-static` for functional
checks (QEMU user mode does not model timing).
