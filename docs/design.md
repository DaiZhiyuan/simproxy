# Design

## Goal

Given a real ARM64 program, produce a small native executable (the **proxy**) that
reproduces the architecture-independent behaviour relevant to simulation, so that
a long full-program simulation can be replaced by a short proxy run.

## Pipeline

```
target ELF
  │
  ├─(A) DynamoRIO: BBV + extended interval features
  │        drmemtrace / drpoints / simproxy_bbv
  │
  ├─(B) QEMU TCG plugins: independent BBV + cache/branch metrics
  │        libbbv, libcache, libhowvec
  │
  ▼
profiler ──▶ features.parquet + prog.bbv
  │
  ▼
cluster  ──▶ simpoints.json   (random projection + k-means + SimPoint BIC)
  │
  ▼
synthesize ──▶ proxy_spec.json ──▶ codegen ──▶ proxy.elf + manifest.json
  │
  ▼
validate ──▶ fidelity report (original vs. proxy)
```

## Feature abstraction

Two layers:

1. **Clustering layer** — the standard Basic Block Vector (BBV): execution count of
   each static basic block per interval, weighted by block size and normalized.
   This is architecture-independent and cheap to collect.
2. **Synthesis layer** — richer per-interval descriptors:
   instruction mix, load/store counts, distinct cache lines, stride histogram,
   working-set size, branch taken rate/entropy, dependency-chain length. These are
   collected alongside the BBV but do not influence phase boundaries.

The DynamoRIO `DR_ISA_REGDEPS` synthetic ISA is a candidate representation for the
synthesis layer because it preserves register dependencies and operation categories
while removing architecture-specific opcodes.

## Clustering

SimPoint methodology:

1. Sparse Achlioptas random projection to a low-dimensional space.
2. k-means++ seeding, Lloyd iterations.
3. BIC scoring using the reference SimPoint formula (cluster probabilities, means,
   and a single variance; parameter count `(k-1) + k*dim + 1`).
4. Choose the smallest `k` with `BIC >= min + 0.9 * (max - min)`.
5. Representative interval per cluster = the member closest to its centroid;
   weight = cluster size / total intervals.

The implementation is a clean-room Python/NumPy version, validated against the
reference SimPoint 3.2 binary in M2.

## Proxy synthesis (M3)

Primary mode: **statistical phase kernels**.

For each selected phase, fit a kernel whose parameters reproduce the phase's
feature vector:

| Feature | Kernel parameter |
|---|---|
| instruction mix | counts of ALU / mul / FP / SIMD / load / store ops |
| memory footprint | array sizes, strides, pointer-chase chains |
| branch behaviour | branch structure and taken probabilities |
| dependency structure | chain length / ILP shaping |
| working set | total touched bytes |

`main()` runs each kernel for `weight * total_intervals` repetitions (optionally
interleaved to preserve phase transitions). The output is an ordinary ARM64 ELF with
no interpreter overhead, directly runnable under QEMU.

Fallback modes:

- **Trace stitching** (high fidelity, validation only): copy the recorded dynamic
  basic blocks of each representative interval into a new ELF and reconnect them
  following the recorded control flow.
- **Trace replay** (correctness only): table-driven replay; simplest, but adds
  interpreter overhead.

## Fidelity evaluation

Metrics collected on both the original program and the proxy:

- IPC / CPI
- cache MPKI (L1/L2/LLC)
- branch misprediction rate
- weighted BBV distance
- phase coverage error
- instructions executed (proxy vs. target)

Target: relative error < 10% on the primary metrics, with the baseline and
confidence intervals recorded in `manifest.json`.

## Scope

- v0: single-threaded Linux user-mode programs, AArch64.
- Out of scope: multi-threaded workloads, system calls with side effects,
  dynamically generated code, SVE-length changes.
