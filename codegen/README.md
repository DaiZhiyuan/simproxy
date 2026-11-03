# Code generator (M3)

This directory will host the phase-kernel emitter that turns a `ProxySpec` into a
native ARM64 executable.

Planned structure:

```
codegen/
├── CMakeLists.txt
├── include/simproxy/codegen.h
└── src/
    ├── kernel.cpp        # statistical phase kernel model
    ├── emit_aarch64.cpp  # IR -> AArch64 assembly / object
    └── link.cpp          # driver + linker invocation
```

M0 intentionally leaves this empty; the interface is frozen in
`python/simproxy/synthesize` and `docs/data-format.md` first.
