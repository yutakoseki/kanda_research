"""リサーチ表と同じ損益式。同価格前提で判定する。"""

from __future__ import annotations

from dataclasses import dataclass

from deca.shipping import (
    INTL_CBM_LARGE,
    INTL_CBM_SMALL,
    cbm,
    sagawa_domestic,
)

AMAZON_FEE_RATE = 0.165
TAX_RATE = 0.10
DUTY_RATE = 0.10
TARGET_MARGIN = 0.20
IDEAL_MARGIN = 0.30
DEFAULT_RATE = 22.0


@dataclass
class Inputs:
    selling_yen: float
    length_cm: float
    width_cm: float
    height_cm: float
    weight_kg: float | None = None
    yuan: float | None = None
    fx_rate: float = DEFAULT_RATE
    domestic_yen_override: int | None = None


@dataclass
class Scenario:
    label: str
    per_cbm: int
    yen_cost: float | None
    amazon_fee: float
    tax: float | None
    duty: float | None
    intl: float
    domestic: int | None
    gross: float | None
    margin: float | None
    max_yuan_20: float | None
    max_yuan_30: float | None
    notes: list[str]


def _max_yuan(
    selling: float,
    domestic: int | None,
    intl: float,
    fx_rate: float,
    target: float,
) -> float | None:
    if domestic is None or fx_rate <= 0:
        return None
    # profit = G*(1-fee) - K - P - yuan*rate*(1+tax+duty)
    # margin >= t  =>  yuan <= (G*(1-fee-t) - K - P) / (rate * 1.2)
    numerator = selling * (1 - AMAZON_FEE_RATE - target) - domestic - intl
    denom = fx_rate * (1 + TAX_RATE + DUTY_RATE)
    return numerator / denom


def quote(inp: Inputs) -> dict:
    volume = cbm(inp.length_cm, inp.width_cm, inp.height_cm)
    domestic = sagawa_domestic(
        inp.length_cm + inp.width_cm + inp.height_cm,
        inp.weight_kg,
    )
    dom_yen = (
        inp.domestic_yen_override
        if inp.domestic_yen_override is not None
        else domestic.yen
    )
    amazon_fee = inp.selling_yen * AMAZON_FEE_RATE

    scenarios: list[Scenario] = []
    for label, per_cbm in (
        ("ロット2m3超（17,325円/m3）", INTL_CBM_LARGE),
        ("少量2m3以下（33,000円/m3）", INTL_CBM_SMALL),
    ):
        intl = volume * per_cbm
        notes = list(domestic.notes)
        yen_cost = tax = duty = gross = margin = None
        if inp.yuan is not None:
            yen_cost = inp.yuan * inp.fx_rate
            tax = yen_cost * TAX_RATE
            duty = yen_cost * DUTY_RATE
            if dom_yen is not None:
                gross = (
                    inp.selling_yen
                    - yen_cost
                    - dom_yen
                    - amazon_fee
                    - tax
                    - duty
                    - intl
                )
                margin = gross / inp.selling_yen if inp.selling_yen else None
            else:
                notes.append("国内送料が出せないため利益率は未計算。")
        scenarios.append(
            Scenario(
                label=label,
                per_cbm=per_cbm,
                yen_cost=yen_cost,
                amazon_fee=amazon_fee,
                tax=tax,
                duty=duty,
                intl=intl,
                domestic=dom_yen,
                gross=gross,
                margin=margin,
                max_yuan_20=_max_yuan(
                    inp.selling_yen, dom_yen, intl, inp.fx_rate, TARGET_MARGIN
                ),
                max_yuan_30=_max_yuan(
                    inp.selling_yen, dom_yen, intl, inp.fx_rate, IDEAL_MARGIN
                ),
                notes=notes,
            )
        )

    return {
        "cbm": volume,
        "girth_cm": inp.length_cm + inp.width_cm + inp.height_cm,
        "domestic_band": domestic.band,
        "scenarios": scenarios,
    }
