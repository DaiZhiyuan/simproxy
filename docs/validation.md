# Validation

## SimPoint 3.2 equivalence (M2)

SimProxy ships two clustering backends:

- `achlioptas` (default): sparse Achlioptas projection + k-means++, fast but not
  bit-identical to the reference toolkit.
- `simpoint`: reproduces the reference implementation exactly — dense
  `[-1, 1]` projection from the Numerical Recipes `ran2` generator, random-sample
  initialization with SimPoint's seed progression, and exact-equality Lloyd
  convergence.

Both use the reference BIC formula and threshold rule. Use `--backend simpoint`
when output must match SimPoint 3.2.

### Method

For each synthetic workload:

1. Generate a BBV with 2–5 well-separated phases, 3–8 blocks per phase, 8–20
   intervals per phase, and 0–40% count noise.
2. Run the reference binary with a fixed `k` equal to the number of phases.
3. Run `simproxy.cluster.cluster_reference` on the same `.bbv`.
4. Compare the selected interval set, the cluster weights, and the best BIC.

The benchmark also verifies the canonical `.bbv` dialect, since the reference
binary parses the file produced by `simproxy.formats.bbv.write_bbv`.

### Results

20 randomized cases (`scripts/benchmark_simpoint.py --cases 20`):

| Metric | Result |
|---|---|
| Representative interval set | 20/20 exact match |
| Cluster weights | max absolute error `3.33e-7` |
| Best BIC | max delta `4.95e-3` (reference prints 6 significant digits) |
| `.bbv` parse compatibility | 20/20 |

The weight error is at the level of the reference's printed precision
(`1/3` vs `0.333333`); BIC deltas come from comparing against the rounded value
in the reference log.

### Reproduce

```bash
SIMPOINT_BIN=/path/to/SimPoint.3.2/bin/simpoint \
  python scripts/benchmark_simpoint.py --cases 20 --json results.json

SIMPOINT_BIN=/path/to/SimPoint.3.2/bin/simpoint \
  python scripts/validate_simpoint.py prog.bbv --k 3 --strict
```

The same checks run in `tests/e2e/test_simpoint_reference.py` when
`SIMPOINT_BIN` is set.
