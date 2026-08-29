"""CLI / Web 共通の調査実行。"""

from __future__ import annotations

from dataclasses import asdict
from pathlib import Path

from deca.amazon import AmazonListing, amazon_url, extract_asin, fetch_html, parse_html
from deca.keepa_csv import find_keepa_csv, lookup_keepa_package, merge_keepa_specs
from deca.margin import DEFAULT_RATE, Inputs, quote


def research(
    url: str | None = None,
    *,
    yuan: float | None = None,
    rate: float = DEFAULT_RATE,
    price: float | None = None,
    length: float | None = None,
    width: float | None = None,
    height: float | None = None,
    weight: float | None = None,
    domestic: int | None = None,
    csv_path: str | Path | None = None,
    keepa_csv_text: str | None = None,
    keepa_length: float | None = None,
    keepa_width: float | None = None,
    keepa_height: float | None = None,
    keepa_weight_kg: float | None = None,
    fetch: bool = True,
) -> dict:
    listing: AmazonListing | None = None
    fetch_error: str | None = None
    fetch_url = amazon_url(url) if url else None
    url_asin = extract_asin(url) if url else None
    asin = url_asin

    if fetch and fetch_url:
        try:
            listing = parse_html(fetch_html(fetch_url), fetch_url)
            asin = listing.asin or asin
        except Exception as e:
            fetch_error = str(e)

    keepa_specs, keepa_meta = merge_keepa_specs(csv_path, keepa_csv_text)
    keepa = lookup_keepa_package(keepa_specs, url_asin, asin)
    if keepa and keepa_length is None:
        keepa_length = keepa.length_cm
        keepa_width = keepa.width_cm
        keepa_height = keepa.height_cm
        keepa_weight_kg = keepa.weight_kg

    # 売価は Amazon（または手入力）だけ。Keepa CSV の Buy Box は使わない。
    price = price if price is not None else (listing.price_yen if listing else None)

    dim_source = None
    if length is not None and width is not None and height is not None:
        dim_source = "手入力"
    elif keepa_length is not None and keepa_width is not None and keepa_height is not None:
        length, width, height = keepa_length, keepa_width, keepa_height
        dim_source = "Keepa CSV 梱包サイズ"
    elif listing and listing.length_cm is not None:
        length, width, height = listing.length_cm, listing.width_cm, listing.height_cm
        dim_source = listing.dimension_source or "Amazon"

    if weight is None:
        if keepa_weight_kg is not None:
            weight = keepa_weight_kg
        elif listing:
            weight = listing.weight_kg

    missing: list[str] = []
    if price is None:
        missing.append("売価")
    if length is None or width is None or height is None:
        missing.append("梱包の縦・横・高")

    extra_notes: list[str] = []
    if dim_source == "Keepa CSV 梱包サイズ":
        src = keepa_meta.get("path") or ("アップロード CSV" if keepa_meta.get("uploaded") else "Keepa CSV")
        extra_notes.append(f"梱包サイズ・重量は {src}。売価は Amazon の現在値。")
    elif length is None or width is None or height is None:
        if keepa_meta["row_count"] == 0:
            extra_notes.append(
                "Keepa CSV が読み込まれていません。"
                "data/keepa/ に CSV を置くか、上のファイル選択で CSV を指定してください。"
            )
        elif keepa is None:
            lookup = asin or url_asin or "?"
            extra_notes.append(
                f"ASIN {lookup} が Keepa CSV に見つかりません（{keepa_meta['row_count']}件読込）。"
            )
    if listing and listing.warnings:
        extra_notes.extend(listing.warnings)

    result: dict = {
        "ok": not missing,
        "missing": missing,
        "fetch_error": fetch_error,
        "listing": asdict(listing) if listing else None,
        "asin": asin,
        "package_source": dim_source,
        "keepa_csv": keepa_meta,
        "quote": None,
        "notes": extra_notes,
    }
    if missing:
        return result

    inp = Inputs(
        selling_yen=price,
        length_cm=length,
        width_cm=width,
        height_cm=height,
        weight_kg=weight,
        yuan=yuan,
        fx_rate=rate or DEFAULT_RATE,
        domestic_yen_override=domestic,
    )
    q = quote(inp)
    result["inputs"] = {
        "selling_yen": inp.selling_yen,
        "length_cm": inp.length_cm,
        "width_cm": inp.width_cm,
        "height_cm": inp.height_cm,
        "weight_kg": inp.weight_kg,
        "yuan": inp.yuan,
        "fx_rate": inp.fx_rate,
        "domestic_yen_override": inp.domestic_yen_override,
        "package_source": dim_source,
    }
    result["quote"] = {
        "cbm": q["cbm"],
        "girth_cm": q["girth_cm"],
        "domestic_band": q["domestic_band"],
        "scenarios": [asdict(s) for s in q["scenarios"]],
    }
    return result
