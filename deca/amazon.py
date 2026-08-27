"""Amazon.co.jp 商品ページから、計算に必要な公開スペックを拾う。"""

from __future__ import annotations

import json
import re
import urllib.request
from dataclasses import dataclass
from html import unescape

USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36"
)


@dataclass
class AmazonListing:
    url: str
    asin: str | None
    title: str | None
    price_yen: float | None
    length_cm: float | None
    width_cm: float | None
    height_cm: float | None
    weight_kg: float | None
    dimension_source: str | None
    warnings: list[str]


def extract_asin(url: str) -> str | None:
    s = (url or "").strip()
    if re.fullmatch(r"[A-Z0-9]{10}", s, re.I):
        return s.upper()
    m = re.search(r"/dp/([A-Z0-9]{10})", s, re.I)
    if m:
        return m.group(1).upper()
    m = re.search(r"/gp/product/([A-Z0-9]{10})", s, re.I)
    if m:
        return m.group(1).upper()
    m = re.search(r"[?&]asin=([A-Z0-9]{10})", s, re.I)
    if m:
        return m.group(1).upper()
    m = re.search(r"#!product/\d-([A-Z0-9]{10})", s, re.I)
    return m.group(1).upper() if m else None


def amazon_url(asin_or_url: str) -> str:
    asin = extract_asin(asin_or_url)
    if not asin:
        return (asin_or_url or "").strip()
    if "amazon." in (asin_or_url or "").lower():
        return asin_or_url.strip()
    return f"https://www.amazon.co.jp/dp/{asin}"


def _nums(text: str) -> list[float]:
    return [float(x.replace(",", "")) for x in re.findall(r"\d+(?:\.\d+)?", text)]


def parse_dimension_text(text: str) -> tuple[float, float, float] | None:
    t = unescape(text).replace("×", "x").replace("＊", "x")
    named = re.search(
        r"幅\s*([\d.]+).*?奥行[き]?\s*([\d.]+).*?高さ\s*([\d.]+)",
        t,
    )
    if named:
        return float(named.group(1)), float(named.group(2)), float(named.group(3))
    t = t.replace("cm", "").replace("㎝", "")
    parts = re.split(r"\s*x\s*", t, flags=re.I)
    nums: list[float] = []
    for p in parts:
        found = _nums(p)
        if found:
            nums.append(found[0])
    if len(nums) >= 3:
        a, b, c = nums[:3]
        return a, b, c
    return None


def parse_weight_text(text: str) -> float | None:
    t = unescape(text)
    kg = re.search(r"([\d.]+)\s*kg", t, re.I)
    if kg:
        return float(kg.group(1))
    g = re.search(r"([\d.]+)\s*g(?!a)", t, re.I)
    if g:
        return float(g.group(1)) / 1000
    return None


def _json_ld_products(html: str) -> list[dict]:
    out: list[dict] = []
    for m in re.finditer(
        r'<script[^>]*type="application/ld\+json"[^>]*>(.*?)</script>',
        html,
        re.I | re.S,
    ):
        raw = m.group(1).strip()
        try:
            data = json.loads(raw)
        except json.JSONDecodeError:
            continue
        blob = data if isinstance(data, list) else [data]
        for item in blob:
            if isinstance(item, dict) and item.get("@type") in ("Product", ["Product"]):
                out.append(item)
    return out


def parse_html(html: str, url: str) -> AmazonListing:
    warnings: list[str] = []
    asin = extract_asin(url)
    title = None
    price = None
    dims = None
    dim_src = None
    weight = None

    m = re.search(r"<title>(.*?)</title>", html, re.I | re.S)
    if m:
        title = unescape(re.sub(r"\s+", " ", m.group(1))).split(":")[0].strip()
        title = re.sub(r"\s*[:：].*Amazon\.co\.jp.*$", "", title).strip()

    asin_m = re.search(r'"asin"\s*:\s*"([A-Z0-9]{10})"', html)
    if asin_m:
        asin = asin_m.group(1)

    for prod in _json_ld_products(html):
        title = title or prod.get("name")
        offers = prod.get("offers") or {}
        if isinstance(offers, list) and offers:
            offers = offers[0]
        if isinstance(offers, dict) and offers.get("price"):
            try:
                price = float(str(offers["price"]).replace(",", ""))
            except ValueError:
                pass

    asin_input = re.search(r'id="ASIN"[^>]*value="([A-Z0-9]{10})"', html)
    if asin_input:
        asin = asin_input.group(1)

    if price is None:
        pm = re.search(r'class="a-offscreen">[￥¥]([\d,]+)', html)
        if pm:
            price = float(pm.group(1).replace(",", ""))
        else:
            pm = re.search(r'class="a-price-whole">([\d,]+)', html)
            if pm:
                price = float(pm.group(1).replace(",", ""))
            else:
                pm = re.search(r'"priceAmount":\s*([\d.]+)', html)
                if pm:
                    price = float(pm.group(1))

    # 梱包サイズを優先、なければ商品サイズ
    pack = re.search(
        r"(梱包サイズ|パッケージサイズ|Package Dimensions)[^<]{0,40}</[^>]+>\s*<[^>]+>([^<]+)",
        html,
        re.I,
    )
    prod_dim = re.search(
        r"(商品の寸法|製品サイズ|商品サイズ|Item Dimensions)[^<]{0,40}</[^>]+>\s*<[^>]+>([^<]+)",
        html,
        re.I,
    )
    # 表形式 prodDetails
    def detail(label: str) -> str | None:
        pat = rf"<th[^>]*>\s*{label}\s*</th>\s*<td[^>]*>(.*?)</td>"
        mm = re.search(pat, html, re.I | re.S)
        if not mm:
            pat = rf"<span[^>]*>\s*{label}\s*</span>\s*</td>\s*<td[^>]*>(.*?)</td>"
            mm = re.search(pat, html, re.I | re.S)
        if not mm:
            return None
        return re.sub(r"<[^>]+>", " ", mm.group(1))

    pack_text = detail("梱包サイズ") or detail("パッケージサイズ")
    item_text = (
        detail("商品の寸法")
        or detail("製品サイズ")
        or detail("商品サイズ")
    )
    weight_text = (
        detail("梱包重量")
        or detail("商品の重量")
        or detail("重量")
        or detail("Item Weight")
    )

    ov = re.search(
        r"商品の寸法</span>[\s\S]{0,200}?po-break-word\">([^<]+)",
        html,
    )
    bm = re.search(r"サイズ[：:]\s*幅[^<]{0,160}", html)

    candidates: list[tuple[str | None, str, bool]] = [
        (pack_text, "梱包サイズ", False),
        (pack.group(2) if pack else None, "梱包サイズ", False),
        (item_text, "商品サイズ（梱包ではない）", True),
        (prod_dim.group(2) if prod_dim else None, "商品サイズ（梱包ではない）", True),
        (ov.group(1) if ov else None, "商品の寸法（梱包ではない）", True),
        (bm.group(0) if bm else None, "箇条書きサイズ（梱包ではない）", True),
    ]
    for text, src, estimated in candidates:
        if not text:
            continue
        parsed = parse_dimension_text(text)
        if parsed:
            dims = parsed
            dim_src = src
            if estimated:
                warnings.append("梱包サイズが無いので商品サイズで仮計算。送料が過小になりやすい。")
            break

    if weight_text:
        weight = parse_weight_text(weight_text) or weight
    if weight is None and bm:
        weight = parse_weight_text(bm.group(0))

    if price is None:
        warnings.append("売価を自動取得できなかった。")
    if dims is None:
        warnings.append("寸法を自動取得できなかった。縦横高を手動で渡す。")

    l = w = h = None
    if dims:
        l, w, h = dims
    return AmazonListing(
        url=url,
        asin=asin,
        title=title,
        price_yen=price,
        length_cm=l,
        width_cm=w,
        height_cm=h,
        weight_kg=weight,
        dimension_source=dim_src,
        warnings=warnings,
    )


def fetch_html(url: str, timeout: int = 25) -> str:
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT, "Accept-Language": "ja-JP,ja;q=0.9"})
    with urllib.request.urlopen(req, timeout=timeout) as res:
        return res.read().decode("utf-8", errors="replace")
