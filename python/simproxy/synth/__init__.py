"""Statistical phase-kernel synthesis (M3)."""

from .build import BuildError, BuildResult, build_proxy
from .emit import emit_c
from .kernels import CATEGORIES, DEFAULT_MIX, KernelPlan, normalize_mix, plan_kernel

__all__ = [
    "CATEGORIES",
    "DEFAULT_MIX",
    "BuildError",
    "BuildResult",
    "KernelPlan",
    "build_proxy",
    "emit_c",
    "normalize_mix",
    "plan_kernel",
]
