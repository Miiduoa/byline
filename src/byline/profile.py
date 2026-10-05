from __future__ import annotations

import csv
import hashlib
import json
from dataclasses import dataclass, asdict
from datetime import date, datetime
from pathlib import Path
from typing import Iterable

NULL_TOKENS = {"", "null", "none", "na", "n/a"}


@dataclass(frozen=True)
class ColumnProfile:
    name: str
    inferred_type: str
    null_rate: float
    unique_count: int


@dataclass(frozen=True)
class DatasetProfile:
    path: str
    sha256: str
    row_count: int
    columns: list[ColumnProfile]

    def to_dict(self) -> dict:
        return {
            "version": 1,
            "dataset": {
                "path": self.path,
                "sha256": self.sha256,
                "row_count": self.row_count,
                "columns": [asdict(c) for c in self.columns],
            },
        }


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _is_null(value: str) -> bool:
    return value.strip().lower() in NULL_TOKENS


def _fits_bool(value: str) -> bool:
    return value.strip().lower() in {"true", "false", "yes", "no"}


def _fits_int(value: str) -> bool:
    value = value.strip()
    if not value:
        return False
    if value.startswith(("+", "-")):
        value = value[1:]
    return value.isdigit()


def _fits_float(value: str) -> bool:
    try:
        float(value)
        return True
    except ValueError:
        return False


def _fits_datetime(value: str) -> bool:
    try:
        parsed = datetime.fromisoformat(value.strip().replace("Z", "+00:00"))
        return parsed.time() != datetime.min.time() or "T" in value or " " in value
    except ValueError:
        return False


def _fits_date(value: str) -> bool:
    try:
        date.fromisoformat(value.strip())
        return True
    except ValueError:
        return False


def infer_type(values: Iterable[str]) -> str:
    sample = [v.strip() for v in values if not _is_null(v)]
    if not sample:
        return "text"

    checks = (
        ("boolean", _fits_bool),
        ("integer", _fits_int),
        ("float", _fits_float),
        ("datetime", _fits_datetime),
        ("date", _fits_date),
    )
    for name, predicate in checks:
        if all(predicate(v) for v in sample):
            return name
    return "text"


def profile_csv(path: str | Path) -> DatasetProfile:
    file_path = Path(path)
    if not file_path.exists():
        raise FileNotFoundError(file_path)

    with file_path.open("r", encoding="utf-8-sig", newline="") as fh:
        reader = csv.DictReader(fh)
        if reader.fieldnames is None:
            raise ValueError("CSV header is missing")
        headers = [h.strip() for h in reader.fieldnames]
        if len(headers) != len(set(headers)):
            raise ValueError("CSV contains duplicate column names")

        values: dict[str, list[str]] = {name: [] for name in headers}
        row_count = 0
        for row in reader:
            row_count += 1
            for name in headers:
                values[name].append((row.get(name) or "").strip())

    columns: list[ColumnProfile] = []
    for name in headers:
        column_values = values[name]
        null_count = sum(_is_null(v) for v in column_values)
        non_null = [v for v in column_values if not _is_null(v)]
        columns.append(
            ColumnProfile(
                name=name,
                inferred_type=infer_type(column_values),
                null_rate=round(null_count / row_count, 6) if row_count else 0.0,
                unique_count=len(set(non_null)),
            )
        )

    return DatasetProfile(
        path=file_path.name,
        sha256=_sha256(file_path),
        row_count=row_count,
        columns=columns,
    )


def save_contract(profile: DatasetProfile, out_path: str | Path) -> None:
    path = Path(out_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(profile.to_dict(), ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def load_contract(path: str | Path) -> dict:
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    if data.get("version") != 1 or "dataset" not in data:
        raise ValueError("Unsupported or invalid contract")
    return data
