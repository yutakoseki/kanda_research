"""Amazon URL → 利益率と、交渉用の仕入上限（元）。"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from deca.amazon import AmazonListing, parse_html
from deca.keepa_csv import find_keepa_csv
from deca.margin import DEFAULT_RATE, Inputs, quote
from deca.service import research


def _fmt_yen(v: float | int | None) -> str:
    if v is None:
        return "—"
    return f"{round(v):,}円"


def _fmt_yuan(v: float | None) -> str:
    if v is None:
        return "—"
    return f"{v:,.1f} 元"


def _fmt_pct(v: float | None) -> str:
    if v is None:
        return "—"
    mark = "GO" if v >= 0.20 else "NO GO"
    return f"{v * 100:.1f}%  {mark}"


def render(
    listing: AmazonListing | None,
    q: dict,
    inp: Inputs,
    package_source: str | None = None,
) -> str:
    lines: list[str] = []
    if listing:
        lines.append(listing.title or "(タイトル不明)")
        lines.append(listing.url)
        if listing.asin:
            lines.append(f"ASIN: {listing.asin}")
        for w in listing.warnings:
            lines.append(f"注意: {w}")
    src = package_source or (listing.dimension_source if listing else None)
    if src:
        lines.append(f"寸法出典: {src}")
    if listing or src:
        lines.append("")
    lines.append(
        f"売価 { _fmt_yen(inp.selling_yen) }  /  梱包 {inp.length_cm:.1f}×{inp.width_cm:.1f}×{inp.height_cm:.1f}cm  "
        f"/ 三辺 {q['girth_cm']:.0f}cm（{q['domestic_band']}）  /  {q['cbm']:.4f}m3  /  レート {inp.fx_rate}"
    )
    if inp.yuan is not None:
        lines.append(f"入力した仕入: {inp.yuan} 元")
    lines.append("")
    for s in q["scenarios"]:
        lines.append(f"## {s.label}")
        lines.append(
            f"国内送料 { _fmt_yen(s.domestic) }  /  国際運送 { _fmt_yen(s.intl) }  /  Amazon手数料 { _fmt_yen(s.amazon_fee) }"
        )
        lines.append(
            f"利益率20%にする仕入上限: {_fmt_yuan(s.max_yuan_20)}　"
            f"（30%なら {_fmt_yuan(s.max_yuan_30)}）"
        )
        if s.margin is not None:
            lines.append(
                f"この仕入での粗利 {_fmt_yen(s.gross)}  /  利益率 {_fmt_pct(s.margin)}"
            )
        for n in s.notes:
            lines.append(f"- {n}")
        lines.append("")
    lines.append("同価格前提。Alibaba表示価格は信用せず、上限元をバイヤーに渡して確認する。")
    return "\n".join(lines).rstrip() + "\n"


def print_result(result: dict) -> int:
    if result.get("fetch_error"):
        print(f"Amazon取得失敗: {result['fetch_error']}", file=sys.stderr)
    if not result["ok"]:
        print("計算に不足: " + ", ".join(result["missing"]), file=sys.stderr)
        return 1
    listing = AmazonListing(**result["listing"]) if result.get("listing") else None
    inp_raw = dict(result.get("inputs") or {})
    package_source = inp_raw.pop("package_source", None)
    inp = Inputs(**inp_raw)
    q = quote(inp)
    print(render(listing, q, inp, package_source))
    return 0


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="Amazon URL から利益率 / 仕入上限を出す")
    p.add_argument("url", nargs="?", help="Amazon.co.jp の商品URL")
    p.add_argument("--html", help="保存済みHTML（取得失敗時）")
    p.add_argument("--price", type=float)
    p.add_argument("--length", type=float)
    p.add_argument("--width", type=float)
    p.add_argument("--height", type=float)
    p.add_argument("--weight", type=float)
    p.add_argument("--yuan", type=float, help="確認済み仕入（元）。無いときは上限だけ出す")
    p.add_argument("--rate", type=float, default=DEFAULT_RATE)
    p.add_argument("--domestic", type=int, help="国内送料を手で上書き（円）")
    p.add_argument(
        "--csv",
        help="Keepa Product Finder CSV。省略時は data/keepa の最新ファイル",
    )
    p.add_argument("--json", action="store_true")
    args = p.parse_args(argv)
    csv_path = find_keepa_csv(args.csv)

    if args.html:
        listing = parse_html(Path(args.html).read_text(encoding="utf-8"), args.url or "")
        result = research(
            None,
            yuan=args.yuan,
            rate=args.rate,
            price=args.price or listing.price_yen,
            length=args.length or listing.length_cm,
            width=args.width or listing.width_cm,
            height=args.height or listing.height_cm,
            weight=args.weight or listing.weight_kg,
            domestic=args.domestic,
            csv_path=csv_path,
        )
        result["listing"] = listing.__dict__
    else:
        result = research(
            args.url,
            yuan=args.yuan,
            rate=args.rate,
            price=args.price,
            length=args.length,
            width=args.width,
            height=args.height,
            weight=args.weight,
            domestic=args.domestic,
            csv_path=csv_path,
        )

    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2, default=str))
        return 0 if result["ok"] else 1
    return print_result(result)


if __name__ == "__main__":
    raise SystemExit(main())
