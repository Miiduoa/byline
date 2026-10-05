from __future__ import annotations

from dataclasses import dataclass

from .profile import DatasetProfile


@dataclass(frozen=True)
class ContractResult:
    breaking: list[str]
    warnings: list[str]

    @property
    def ok(self) -> bool:
        return not self.breaking


def compare_contract(contract: dict, current: DatasetProfile, null_rate_delta: float = 0.20) -> ContractResult:
    baseline = contract["dataset"]
    baseline_columns = {c["name"]: c for c in baseline.get("columns", [])}
    current_columns = {c.name: c for c in current.columns}

    breaking: list[str] = []
    warnings: list[str] = []

    for name, old in baseline_columns.items():
        new = current_columns.get(name)
        if new is None:
            breaking.append(f"column removed: {name}")
            continue
        old_type = old.get("inferred_type")
        if old_type != new.inferred_type:
            breaking.append(f"type changed: {name} ({old_type} -> {new.inferred_type})")
        old_null = float(old.get("null_rate", 0.0))
        if new.null_rate - old_null >= null_rate_delta:
            warnings.append(
                f"null rate increased: {name} ({old_null:.1%} -> {new.null_rate:.1%})"
            )

    for name in current_columns:
        if name not in baseline_columns:
            warnings.append(f"new column: {name}")

    old_rows = int(baseline.get("row_count", 0))
    if old_rows > 0 and current.row_count == 0:
        breaking.append("dataset became empty")
    elif old_rows > 0 and current.row_count < old_rows * 0.5:
        warnings.append(f"row count dropped: {old_rows} -> {current.row_count}")

    return ContractResult(breaking=breaking, warnings=warnings)
