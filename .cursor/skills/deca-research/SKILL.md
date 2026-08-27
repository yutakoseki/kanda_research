---
name: deca-research
description: >-
  Calculates Amazon JP デカ重 product margin and max China purchase price (yuan)
  from an Amazon URL using Tentou shipping rates. Use when the user pastes an
  Amazon.co.jp URL, asks 利益率, 仕入上限, リサーチ表, or whether a product clears 20%.
---

# デカ重リサーチ

Amazon URL または ASIN から始める。売価は Amazon の現在値。Keepa CSV は梱包サイズと重量だけ使う（Buy Box は使わない）。Alibaba 価格は自動取得しない。

## 手順

1. 画面を開く:

```text
python -m deca.web
```

ブラウザで http://127.0.0.1:8765/ が開く。Amazon URL を貼って「計算する」。

コマンドでも可:

Keepa CSV は `data/keepa/` に置く。省略時はそこの最新 CSV を使う。

```text
python -m deca.cli "AMAZON_URL"
python -m deca.cli "AMAZON_URL" --csv data/keepa/KeepaExport.csv
```

仕入（元）がバイヤー確認済みなら:

```text
python -m deca.cli "AMAZON_URL" --yuan 200
```

Amazon がブロックしたらブラウザで商品ページを開き、売価・梱包サイズ・重量を読む。そのうえで:

```text
python -m deca.cli --price 19800 --length 125 --width 95 --height 12 --weight 12
```

2. 出力の「利益率20%にする仕入上限」を先に見せる。これがバイヤーへの交渉数字。
3. `--yuan` が無いときは利益率は出さない（上限だけ）。推測の1688価格で GO/NO GO しない。
4. 寸法は梱包サイズ。商品サイズしか無いときは仮計算と明記する。
5. ロット2m3超（17,325円/m3）を主判定、少量33,000円/m3も併記する。
6. 同価格前提。2割引では判定しない。

## 出さないもの

- Keepa CSV の売価・Buy Box
- 保護商品の可否（担当者確認が別）
- Alibaba ページからの自動価格
