# Changelog

All notable changes to this project are documented here. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/) and the project uses
[Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added

- Canonical SimPoint `.bbv` parsing/writing (`T:1:48 :3:24`), plus the
  SimProxy-labeled dialect.
- Clean-room clustering with two backends: fast Achlioptas/k-means++ and a
  reference-compatible SimPoint backend (`--backend simpoint`).
- Per-interval feature tables (JSONL/Parquet), summary adapters, and the
  `profile` / `features validate` commands.
- Statistical phase-kernel synthesis to a static ARM64 ELF, with manifest
  hashes (`synth --emit-elf`).
- DynamoRIO AArch64 BBV client and toolchain bootstrap script.
- Reference equivalence benchmark (`scripts/benchmark_simpoint.py`) and
  validation docs.
- Docker image, examples, install/release documentation, and a CI matrix
  covering Python, cross-target end-to-end, packaging, and SimPoint reference
  checks.

### Known limitations

- DynamoRIO runtime profiling requires an AArch64 host/VM; QEMU user-mode
  emulation is not supported for the client.
- Extended feature collection (opcode mix, cache lines, branch/dependency
  metrics) is not yet emitted by the client; the feature table accepts these
  fields from summary streams.
- Physical instruction-count calibration and QEMU-plugin fidelity metrics
  (M4) are pending.
