# 神田式 デカ重リサーチ

Amazon.co.jp の売価と、Keepa CSV の梱包サイズ・重量から、利益率 20% になる中国仕入上限（元）を出します。

売価は Amazon の現在値を使います。Keepa CSV の Buy Box は使いません。Alibaba / 1688 の表示価格も自動では取りません。

## 必要なもの

- Python 3.10 以上（標準ライブラリのみ。追加の pip は不要）
- Amazon 商品 URL または ASIN
- （任意）Keepa Product Finder の CSV

## セットアップ

```text
git clone https://github.com/yutakoseki/kanda_research.git
cd kanda_research
```

Keepa CSV は次のフォルダへ置きます。

```text
data/keepa/
```

Product Finder でエクスポートした `KeepaExport-*.csv` をそのまま入れてください。Git には CSV 本体はコミットしません。

## 使い方（画面）

```text
python3 -m deca.web
```

ブラウザで http://127.0.0.1:8765/ が開きます。

1. Amazon URL または ASIN を貼る
2. `data/keepa` に置いた CSV をファイル選択する（梱包サイズ・重量のみ使用）
3. バイヤー確認済みの仕入（元）があれば入れる。空なら上限だけ出る
4. 「計算する」

Amazon がブロックされたら、画面下の手入力で売価と寸法を補います。

ブラウザを開きたくないときは:

```text
python -m deca.web --no-open
```

## 使い方（コマンド）

`data/keepa` に CSV があれば、`--csv` なしでも最新ファイルを使います。

```text
python -m deca.cli "https://www.amazon.co.jp/dp/B0XXXXXXXX"
python -m deca.cli B0XXXXXXXX
python -m deca.cli B0XXXXXXXX --csv data/keepa/KeepaExport.csv
python -m deca.cli B0XXXXXXXX --yuan 200
```

Amazon から取れないときは手入力します。

```text
python -m deca.cli --price 19800 --length 125 --width 95 --height 12 --weight 12
```

## 判定の前提

- 同価格（2割引では判定しない）
- Amazon 手数料 16.5%、関税・消費税は円換算仕入の各 10%、レート初期値 22 円/元
- 国内送料は天瞳の佐川三辺合計枠。260cm 超または 50kg 超は通常便不可
- 国際運送はロット 2m3 超（17,325 円/m3）を主判定。少量（33,000 円/m3）も併記
- 先に出す数字は「利益率 20% の仕入上限（元）」。確認済み `--yuan` があるときだけ利益率の GO / NO GO を出す

## テスト

```text
python -m unittest tests.test_margin -v
```
