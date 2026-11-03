"""Command line interface for SimProxy."""

from __future__ import annotations

import argparse
from pathlib import Path

import numpy as np

from . import __version__
from .cluster import cluster, select_representatives
from .formats.bbv import concat_bbv, parse_bbv, to_matrix, write_bbv
from .formats.schema import PhaseSpec, ProxySpec, SimPoint, SimPointResult


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

    synth = sub.add_parser("synth", help="emit a proxy specification skeleton")
    synth.add_argument("-i", "--simpoints", type=Path, required=True)
    synth.add_argument("-o", "--output", type=Path, required=True)
    synth.set_defaults(func=_cmd_synth)

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
    phases = [
        PhaseSpec(
            cluster=point.cluster,
            interval=point.interval,
            weight=point.weight,
            instructions=int(round(point.weight * total_instructions)),
            kernel={"mode": "statistical", "status": "pending"},
        )
        for point in simpoints.simpoints
    ]
    spec = ProxySpec(
        source=simpoints.source,
        total_instructions=total_instructions,
        interval_instructions=simpoints.interval_instructions,
        phases=phases,
    )
    spec.to_json(args.output)
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)
    return int(args.func(args))


if __name__ == "__main__":
    raise SystemExit(main())
