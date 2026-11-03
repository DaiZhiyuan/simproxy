from __future__ import annotations

import pytest
from simproxy.profiler import IntervalFeatures
from simproxy.synth import emit_c, normalize_mix, plan_kernel


def test_normalize_mix_maps_aliases():
    mix = normalize_mix({"alu": 2, "ldr": 1, "str": 1})
    assert mix is not None
    assert mix["alu"] == pytest.approx(0.5)
    assert mix["load"] == pytest.approx(0.25)
    assert mix["store"] == pytest.approx(0.25)
    assert sum(mix.values()) == pytest.approx(1.0)


def test_plan_kernel_counts_sum_to_budget():
    features = IntervalFeatures(
        interval=0,
        instructions=1000,
        loads=200,
        stores=100,
        working_set_bytes=1 << 20,
    )
    plan = plan_kernel(0, 1000, features)
    assert sum(plan.counts.values()) == 1000
    assert plan.counts["load"] > 0
    assert plan.counts["store"] > 0


def test_plan_kernel_uses_defaults_when_memory_unmeasured():
    features = IntervalFeatures(interval=0, instructions=1000)
    plan = plan_kernel(0, 1000, features)
    assert plan.counts["load"] > 0
    assert plan.counts["store"] > 0


def test_plan_kernel_defaults_without_features():
    plan = plan_kernel(0, 100, None)
    assert sum(plan.counts.values()) == 100
    assert plan.array_bytes == 1 << 20
    assert plan.branch_taken_percent == 50


def test_plan_kernel_array_is_power_of_two():
    features = IntervalFeatures(interval=0, instructions=1, working_set_bytes=100_000)
    plan = plan_kernel(0, 1, features)
    assert plan.array_bytes & (plan.array_bytes - 1) == 0


def test_emit_c_contains_all_phases():
    plans = [plan_kernel(index, 10, None) for index in range(2)]
    source = emit_c(plans, 20, "prog")
    assert "run_phase_0" in source
    assert "run_phase_1" in source
    assert "logical_instructions" in source
