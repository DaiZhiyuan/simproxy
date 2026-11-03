# Data formats

All artifacts are versioned and produced deterministically from the inputs so that
each pipeline stage can be re-run independently.

## 1. Basic Block Vector (`.bbv`)

Two textual dialects are accepted by `simproxy bbv`:

```
# Canonical SimPoint toolkit / DynamoRIO drpoints (default output)
T:1:12 :3:7 :8:1
T:2:5 :3:9
```

```
# SimProxy labeled extension (explicit interval id; accepted on input)
T0: 1:12 3:7 8:1
T1: 2:5 3:9
```

Rules:

- Each line is one **interval**.
- A pair `bbid:count` gives the execution frequency of a static basic block,
  **weighted by the number of instructions in that block**. The sum of a line is
  therefore the number of instructions executed in the interval.
- The canonical SimPoint dialect is ordered and the interval id is implicit (line
  index). This is the only dialect the official SimPoint 3.2 binary parses.
- The labeled dialect is a SimProxy extension; `write_bbv(..., dialect="labeled")`
  emits it.
- `.bbv.gz` is transparently supported by the parser.
- Normalization divides each interval by its sum so that weights sum to 1.

## 2. Interval features (`features.parquet`, M1)

One row per interval. Extended features are *not* used for clustering; they drive
proxy synthesis and fidelity evaluation.

One JSON object per line (JSONL), or a Parquet table with the same columns. Fields
with map types are stored as JSON strings in Parquet.

| Column | Type | Source | Description |
|---|---|---|---|
| `interval` | int64 | BBV | Interval id (0-based) |
| `instructions` | int64 | BBV | Retired instructions in the interval |
| `num_blocks` | int64 | BBV | Distinct basic blocks executed |
| `bbv_entropy` | float | BBV | Shannon entropy of the normalized BBV |
| `top_block_share` | float | BBV | Largest normalized block share |
| `opcode_mix` | map<string,float> | summary | Fraction per instruction class (sums to 1) |
| `loads` / `stores` | int64 | summary | Memory operation counts |
| `distinct_lines` | int64 | summary | Distinct cache lines touched |
| `stride_hist` | map<string,int64> | summary | Access stride histogram |
| `read_write_ratio` | float | summary | Loads / stores |
| `branch_taken_rate` | float | summary | Fraction of taken branches |
| `branch_entropy` | float | summary | Shannon entropy of branch outcomes |
| `dep_chain_len` | float | summary | Mean dependency chain length |
| `working_set_bytes` | int64 | summary | Estimated working set |
| `extras` | map<string,float> | summary | Forward-compatible extra metrics |

The schema is frozen in `simproxy.profiler.schema` and versioned by
`FEATURE_SCHEMA_VERSION`.

```bash
simproxy profile -i prog.bbv -o features.jsonl \
  --summary summary.jsonl --opcode-csv opcode_mix.csv --parquet features.parquet
simproxy features validate -i features.jsonl
```

## 3. Simulation points (`simpoints.json`)

```json
{
  "source": "prog.bbv",
  "interval_instructions": 100000000,
  "num_intervals": 6,
  "k": 2,
  "bic": 19.228,
  "simpoints": [
    {"cluster": 0, "interval": 2, "weight": 0.5, "start_pc": null},
    {"cluster": 1, "interval": 1, "weight": 0.5, "start_pc": null}
  ],
  "trials": [{"k": 1, "inertia": 9.25, "bic": -23.13}],
  "version": 1
}
```

- `interval` is the representative interval id from the source `.bbv`.
- `weight` is the cluster's share of all intervals; weights sum to 1.
- `trials` records the BIC search for reproducibility.
- `start_pc` is reserved for the high-fidelity trace-stitching mode (M3).

## 4. Proxy specification (`proxy_spec.json`)

```json
{
  "source": "prog.bbv",
  "total_instructions": 600000000,
  "interval_instructions": 100000000,
  "phases": [
    {
      "cluster": 0,
      "interval": 2,
      "weight": 0.5,
      "instructions": 300000000,
      "kernel": {"mode": "statistical", "status": "pending"}
    }
  ],
  "version": 1
}
```

`instructions` is `round(weight * total_instructions)`. `kernel` is filled in by the
synthesizer in M3 with the concrete loop nest / memory model parameters.

## 5. Proxy manifest (`manifest.json`)

Emitted next to the proxy executable.

| Field | Description |
|---|---|
| `proxy` | Path to the generated ARM64 ELF |
| `source` | Original program or `.bbv` |
| `total_instructions` | Target dynamic instruction count |
| `phases` | Phase list copied from `proxy_spec.json` |
| `metrics` | Optional validation metrics (IPC, MPKI, branch rate) |
| `version` | Schema version |

## Conventions

- Interval ids are **0-based** everywhere.
- Counts and weights are floats after normalization; integer values are printed
  without a decimal point.
- JSON is UTF-8, two-space indented, and ends with a newline.
