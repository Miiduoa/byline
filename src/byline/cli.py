from __future__ import annotations

import argparse
from pathlib import Path

from .contract import compare_contract
from .profile import load_contract, profile_csv, save_contract


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="byline",
        description="Check small CSV datasets against a saved contract.",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    snapshot = sub.add_parser("snapshot", help="Create a contract from a CSV file")
    snapshot.add_argument("dataset")
    snapshot.add_argument("--out", required=True)

    check = sub.add_parser("check", help="Compare a CSV file with a saved contract")
    check.add_argument("dataset")
    check.add_argument("--contract", required=True)
    check.add_argument("--null-rate-delta", type=float, default=0.20)
    return parser


def _print_result(
    contract_path: str,
    dataset_path: str,
    breaking: list[str],
    warnings: list[str],
) -> None:
    print(f"contract: {contract_path}")
    print(f"dataset:  {dataset_path}")
    print()

    if breaking:
        print("BREAKING")
        for item in breaking:
            print(f"- {item}")
        print()

    if warnings:
        print("WARNING")
        for item in warnings:
            print(f"- {item}")
        print()

    if not breaking and not warnings:
        print("OK — contract unchanged")
    elif not breaking:
        print("OK — no breaking changes")


def main(argv: list[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)

    try:
        current = profile_csv(args.dataset)
    except (FileNotFoundError, ValueError) as exc:
        print(f"error: {exc}")
        return 1

    if args.command == "snapshot":
        save_contract(current, args.out)
        print(f"saved contract: {Path(args.out)}")
        print(f"rows: {current.row_count}; columns: {len(current.columns)}")
        return 0

    try:
        contract = load_contract(args.contract)
    except (FileNotFoundError, ValueError) as exc:
        print(f"error: {exc}")
        return 1

    result = compare_contract(contract, current, null_rate_delta=args.null_rate_delta)
    _print_result(args.contract, args.dataset, result.breaking, result.warnings)
    return 0 if result.ok else 2


if __name__ == "__main__":
    raise SystemExit(main())
