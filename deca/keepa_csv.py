"""Keepa Product Finder CSV。売価は使わず、梱包サイズと重量だけ読む。"""

from __future__ import annotations

import csv
from dataclasses import dataclass
from io import StringIO
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


def _parse_keepa_rows(reader: csv.DictReader) -> dict[str, PackageSpec]:
    out: dict[str, PackageSpec] = {}
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
        spec = PackageSpec(
            asin=asin,
            length_cm=length,
            width_cm=width,
            height_cm=height,
            weight_kg=(grams / 1000.0) if grams is not None else None,
        )
        out[asin] = spec
        parent = (row.get("Parent ASIN") or "").strip().upper()
        if len(parent) == 10 and parent != asin and parent not in out:
            out[parent] = spec
    return out


def load_keepa_csv(path: str | Path) -> dict[str, PackageSpec]:
    with Path(path).open(encoding="utf-8-sig", newline="") as f:
        return _parse_keepa_rows(csv.DictReader(f))


def load_keepa_csv_text(text: str) -> dict[str, PackageSpec]:
    cleaned = text.lstrip("\ufeff")
    return _parse_keepa_rows(csv.DictReader(StringIO(cleaned)))


def merge_keepa_specs(
    csv_path: str | Path | None = None,
    csv_text: str | None = None,
) -> tuple[dict[str, PackageSpec], dict]:
    """data/keepa のファイルと、Web から送られた CSV 本文を統合する。"""
    specs: dict[str, PackageSpec] = {}
    meta = {"path": None, "uploaded": False, "row_count": 0}
    if csv_path:
        try:
            path = Path(csv_path)
            specs.update(load_keepa_csv(path))
            meta["path"] = str(path)
        except FileNotFoundError:
            pass
    if csv_text and csv_text.strip():
        specs.update(load_keepa_csv_text(csv_text))
        meta["uploaded"] = True
    meta["row_count"] = len(specs)
    return specs, meta


def lookup_keepa_package(
    specs: dict[str, PackageSpec],
    *asins: str | None,
) -> PackageSpec | None:
    seen: set[str] = set()
    for asin in asins:
        if not asin:
            continue
        key = asin.upper()
        if key in seen:
            continue
        seen.add(key)
        hit = specs.get(key)
        if hit:
            return hit
    return None


KEEP_CSV_DIR = Path(__file__).resolve().parents[1] / "data" / "keepa"


def find_keepa_csv(explicit: str | Path | None = None) -> Path | None:
    """手指定が無ければ data/keepa の最新 CSV。"""
    if explicit:
        return Path(explicit)
    if not KEEP_CSV_DIR.is_dir():
        return None
    files = sorted(
        KEEP_CSV_DIR.glob("*.csv"),
        key=lambda p: p.stat().st_mtime,
        reverse=True,
    )
    return files[0] if files else None
