"""Keepa Product Finder CSV。売価は使わず、梱包サイズと重量だけ読む。"""

from __future__ import annotations

import csv
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class PackageSpec:
    asin: str
    length_cm: float
    width_cm: float
    height_cm: float
    weight_kg: float | None


def _num(v: str | None) -> float | None:
    if v is None:
        return None
    s = str(v).strip().replace(",", "")
    if not s or s in ("-", "N/A", "na"):
        return None
    try:
        return float(s)
    except ValueError:
        return None


def load_keepa_csv(path: str | Path) -> dict[str, PackageSpec]:
    out: dict[str, PackageSpec] = {}
    with Path(path).open(encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            asin = (row.get("ASIN") or "").strip().upper()
            if len(asin) != 10:
                continue
            length = _num(row.get("Package: Length (cm)"))
            width = _num(row.get("Package: Width (cm)"))
            height = _num(row.get("Package: Height (cm)"))
            if length is None or width is None or height is None:
                continue
            grams = _num(row.get("Package: Weight (g)"))
            out[asin] = PackageSpec(
                asin=asin,
                length_cm=length,
                width_cm=width,
                height_cm=height,
                weight_kg=(grams / 1000.0) if grams is not None else None,
            )
    return out
