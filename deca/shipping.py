"""天瞳 2026年9月1日適用の国内・国際運送。"""

from __future__ import annotations

from dataclasses import dataclass

# 佐川：3辺合計(cm) 上限 → 料金（北海道・沖縄・離島加算は別）
SAGAWA = (
    (60, 690),
    (80, 740),
    (100, 920),
    (140, 1150),
    (160, 1400),
    (170, 2000),
    (180, 2500),
    (200, 3200),
    (220, 3800),
    (240, 5050),
    (260, 6500),
)

INTL_CBM_SMALL = 33_000  # 発注合計 2㎥以下
INTL_CBM_LARGE = 17_325  # 発注合計 2㎥超
WEIGHT_LIMIT_KG = 50


@dataclass(frozen=True)
class DomesticQuote:
    girth_cm: float
    yen: int | None
    band: str
    notes: list[str]


def girth_cm(length: float, width: float, height: float) -> float:
    return length + width + height


def cbm(length_cm: float, width_cm: float, height_cm: float) -> float:
    return (length_cm / 100) * (width_cm / 100) * (height_cm / 100)


def sagawa_domestic(girth: float, weight_kg: float | None = None) -> DomesticQuote:
    notes: list[str] = []
    if weight_kg is not None and weight_kg > WEIGHT_LIMIT_KG:
        notes.append(f"重量 {weight_kg}kg は佐川50kg超。分割か西濃・アート便の確認が必要。")
    if girth > 260:
        notes.append("三辺合計260cm超。2個口・3個口に分けられないと佐川通常便は使えない。")
        return DomesticQuote(girth, None, "260cm超", notes)
    for limit, yen in SAGAWA:
        if girth <= limit:
            return DomesticQuote(girth, yen, f"{limit}cm枠", notes)
    return DomesticQuote(girth, None, "未該当", notes)


def intl_yen(volume_cbm: float, per_cbm: int) -> float:
    return volume_cbm * per_cbm
