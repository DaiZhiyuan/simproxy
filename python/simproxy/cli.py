"""Command line interface for SimProxy."""

from __future__ import annotations

import argparse
from pathlib import Path

import numpy as np

from . import __version__
from .cluster import cluster, select_representatives
from .formats.bbv import concat_bbv, parse_bbv, to_matrix, write_bbv
from .formats.schema import Manifest, PhaseSpec, ProxySpec, SimPoint, SimPointResult
from .profiler import (
    FeatureTable,
    merge_summaries,
    read_jsonl,
    read_opcode_mix_csv,
)
from .synth import build_proxy, emit_c, plan_kernel


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="simproxy",
        description="SimPoint-based synthetic proxy generation for program simulation.",
    )
    parser.add_argument("--version", action="version", version=f"simproxy {__version__}")
    sub = parser.add_subparsers(dest="command", required=True)

    bbv = sub.add_parser("bbv", help="BBV utilities")
    bbv_sub = bbv.add_subparsers(dest="bbv_command", required=True)

    normalize = bbv_sub.add_parser("normalize", help="normalize every interval vector")
    normalize.add_argument("input", type=Path)
    normalize.add_argument("-o", "--output", type=Path, required=True)
    normalize.set_defaults(func=_cmd_bbv_normalize)

    merge = bbv_sub.add_parser("merge", help="concatenate BBV files in order")
    merge.add_argument("inputs", nargs="+", type=Path)
    merge.add_argument("-o", "--output", type=Path, required=True)
    merge.set_defaults(func=_cmd_bbv_merge)

    simpoint = sub.add_parser("simpoint", help="cluster BBVs and pick simulation points")
    simpoint.add_argument("-i", "--input", type=Path, required=True)
    simpoint.add_argument("-o", "--output", type=Path, required=True)
    simpoint.add_argument("--interval-instructions", type=int, default=100_000_000)
    simpoint.add_argument("--k-min", type=int, default=1)
    simpoint.add_argument("--k-max", type=int, default=10)
    simpoint.add_argument("--seed", type=int, default=0)
    simpoint.add_argument("--projection-dim", type=int, default=10)
    simpoint.add_argument("--max-iter", type=int, default=100)
    simpoint.add_argument("--bic-tolerance", type=float, default=0.9)
    simpoint.set_defaults(func=_cmd_simpoint)

    synth = sub.add_parser("synth", help="emit a proxy specification and kernel ELF")
    synth.add_argument("-i", "--simpoints", type=Path, required=True)
    synth.add_argument("-o", "--output", type=Path, required=True)
    synth.add_argument(
        "--features",
        type=Path,
        default=None,
        help="feature table JSONL used to fit phase kernels",
    )
    synth.add_argument(
        "--emit-elf",
        type=Path,
        default=None,
        help="compile the statistical kernels to this ARM64 ELF",
    )
    synth.add_argument("--manifest", type=Path, default=None)
    synth.add_argument("--cc", default="aarch64-linux-gnu-gcc")
    synth.add_argument("--keep-source", action="store_true")
    synth.set_defaults(func=_cmd_synth)

    profile = sub.add_parser("profile", help="derive interval features from a BBV")
    profile.add_argument("-i", "--input", type=Path, required=True)
    profile.add_argument("-o", "--output", type=Path, required=True)
    profile.add_argument(
        "--summary",
        type=Path,
        action="append",
        default=[],
        help="per-interval summary JSONL (repeatable)",
    )
    profile.add_argument(
        "--opcode-csv",
        type=Path,
        action="append",
        default=[],
        help="opcode mix CSV with interval,opcode_class,count columns",
    )
    profile.add_argument("--parquet", type=Path, default=None)
    profile.set_defaults(func=_cmd_profile)

    features = sub.add_parser("features", help="feature table utilities")
    features_sub = features.add_subparsers(dest="features_command", required=True)
    validate = features_sub.add_parser("validate", help="validate a feature table")
    validate.add_argument("-i", "--input", type=Path, required=True)
    validate.set_defaults(func=_cmd_features_validate)

    return parser


def _cmd_bbv_normalize(args: argparse.Namespace) -> int:
    bbv = parse_bbv(args.input)
    write_bbv(args.output, bbv.normalize())
    return 0


def _cmd_bbv_merge(args: argparse.Namespace) -> int:
    bbv = concat_bbv([parse_bbv(path) for path in args.inputs])
    write_bbv(args.output, bbv)
    return 0


def _cmd_simpoint(args: argparse.Namespace) -> int:
    bbv = parse_bbv(args.input)
    _, matrix = to_matrix(bbv, normalize=True)
    result = cluster(
        matrix,
        k_min=args.k_min,
        k_max=args.k_max,
        seed=args.seed,
        projection_dim=args.projection_dim,
        max_iter=args.max_iter,
        bic_tolerance=args.bic_tolerance,
    )
    representatives = select_representatives(
        result.projected, result.labels, result.centers
    )
    weights = np.bincount(result.labels, minlength=result.k) / len(matrix)
    simpoints = [
        SimPoint(
            cluster=cluster_id,
            interval=bbv.interval_ids[representative],
            weight=float(weights[cluster_id]),
        )
        for cluster_id, representative in enumerate(representatives)
    ]
    payload = SimPointResult(
        source=str(args.input),
        interval_instructions=args.interval_instructions,
        num_intervals=len(bbv),
        k=result.k,
        bic=result.bic,
        simpoints=simpoints,
        trials=result.trials,
    )
    payload.to_json(args.output)
    return 0


def _cmd_synth(args: argparse.Namespace) -> int:
    simpoints = SimPointResult.from_json(args.simpoints)
    total_instructions = simpoints.num_intervals * simpoints.interval_instructions

    features = FeatureTable.from_jsonl(args.features) if args.features else None
    by_interval = {row.interval: row for row in features} if features else {}

    plans = []
    phases = []
    for point in simpoints.simpoints:
        budget = int(round(point.weight * total_instructions))
        plan = plan_kernel(
            point.cluster,
            budget,
            by_interval.get(point.interval),
            seed=point.cluster,
        )
        plans.append(plan)
        phases.append(
            PhaseSpec(
                cluster=point.cluster,
                interval=point.interval,
                weight=point.weight,
                instructions=budget,
                kernel={"mode": "statistical", **plan.to_dict()},
            )
        )

    spec = ProxySpec(
        source=simpoints.source,
        total_instructions=total_instructions,
        interval_instructions=simpoints.interval_instructions,
        phases=phases,
    )
    spec.to_json(args.output)

    if args.emit_elf is None:
        return 0

    c_source = emit_c(plans, total_instructions, simpoints.source)
    build = build_proxy(
        c_source,
        args.emit_elf,
        compiler=args.cc,
        keep_source=args.keep_source,
    )
    manifest_path = args.manifest or args.emit_elf.with_suffix(".manifest.json")
    manifest = Manifest(
        proxy=str(args.emit_elf),
        source=simpoints.source,
        total_instructions=total_instructions,
        phases=phases,
        metrics={
            "backend": "statistical-kernel",
            "compiler": build.compiler,
            "elf_sha256": build.elf_sha256,
            "source_sha256": build.source_sha256,
            "k": simpoints.k,
            "bic": simpoints.bic,
            "num_intervals": simpoints.num_intervals,
            "interval_instructions": simpoints.interval_instructions,
        },
    )
    manifest.to_json(manifest_path)
    return 0


def _cmd_profile(args: argparse.Namespace) -> int:
    bbv = parse_bbv(args.input)
    table = FeatureTable.from_bbv(bbv)
    summaries = [read_jsonl(path) for path in args.summary]
    summaries += [read_opcode_mix_csv(path) for path in args.opcode_csv]
    if summaries:
        table.merge_summary(merge_summaries(*summaries))
    table.to_jsonl(args.output)
    if args.parquet is not None:
        table.to_parquet(args.parquet)
    return 0


def _cmd_features_validate(args: argparse.Namespace) -> int:
    table = FeatureTable.from_jsonl(args.input)
    instructions = sum(row.instructions for row in table)
    print(f"ok: {len(table)} intervals, {instructions} instructions")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)
    return int(args.func(args))


if __name__ == "__main__":
    raise SystemExit(main())
