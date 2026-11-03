# Code generator (M3)

The statistical phase-kernel emitter lives in `python/simproxy/synth/`:

- `kernels.py` turns an interval feature row into per-category operation counts.
- `emit.py` writes a self-contained C program with one function per phase.
- `build.py` cross-compiles it to a static ARM64 ELF
  (`aarch64-linux-gnu-gcc -O2 -static`) and records hashes for the manifest.

A C++/LLVM backend for exact AArch64 instruction scheduling may replace the C
emitter later; the `ProxySpec`/`Manifest` interface in
`python/simproxy/formats/schema.py` stays stable.
