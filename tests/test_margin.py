import unittest

from deca.amazon import parse_dimension_text, parse_html, parse_weight_text
from deca.margin import Inputs, quote
from deca.shipping import sagawa_domestic


class ShippingTest(unittest.TestCase):
    def test_whiteboard_band(self):
        q = sagawa_domestic(125 + 95 + 12)
        self.assertEqual(q.yen, 5050)
        self.assertEqual(q.band, "240cm枠")


class MarginTest(unittest.TestCase):
    def test_whiteboard_forward(self):
        q = quote(
            Inputs(
                selling_yen=19800,
                length_cm=125,
                width_cm=95,
                height_cm=12,
                yuan=4000 / 22,
                fx_rate=22,
            )
        )
        large = q["scenarios"][0]
        self.assertAlmostEqual(large.intl, 125 * 95 * 12 / 1_000_000 * 17325, places=0)
        self.assertEqual(large.domestic, 5050)
        self.assertGreater(large.margin, 0.20)
        self.assertLess(large.margin, 0.22)

    def test_reverse_positive(self):
        q = quote(
            Inputs(
                selling_yen=19800,
                length_cm=125,
                width_cm=95,
                height_cm=12,
                fx_rate=22,
            )
        )
        large = q["scenarios"][0]
        self.assertIsNotNone(large.max_yuan_20)
        self.assertGreater(large.max_yuan_20, 150)
        # 上限ちょうどなら約20%
        q2 = quote(
            Inputs(
                selling_yen=19800,
                length_cm=125,
                width_cm=95,
                height_cm=12,
                yuan=large.max_yuan_20,
                fx_rate=22,
            )
        )
        self.assertAlmostEqual(q2["scenarios"][0].margin, 0.20, places=3)


class AmazonParseTest(unittest.TestCase):
    def test_dims(self):
        self.assertEqual(parse_dimension_text("125 x 95 x 12 cm"), (125.0, 95.0, 12.0))
        self.assertEqual(
            parse_dimension_text("幅189.2×奥行56.2×高さ179cm"),
            (189.2, 56.2, 179.0),
        )

    def test_weight(self):
        self.assertEqual(parse_weight_text("12 kg"), 12.0)

    def test_html_table(self):
        html = """
        <title>テストWB: Amazon.co.jp</title>
        <th>梱包サイズ</th><td>125 x 95 x 12 cm</td>
        <th>梱包重量</th><td>12 kg</td>
        <div id="corePriceDisplay_desktop_feature_div"><span class="a-price-whole">19,800</span></div>
        """
        listing = parse_html(html, "https://www.amazon.co.jp/dp/B0CD26RQ17")
        self.assertEqual(listing.asin, "B0CD26RQ17")
        self.assertEqual(listing.price_yen, 19800)
        self.assertEqual(listing.length_cm, 125)
        self.assertEqual(listing.weight_kg, 12)


class KeepaCsvTest(unittest.TestCase):
    def test_package_only(self):
        from pathlib import Path

        from deca.keepa_csv import find_keepa_csv, load_keepa_csv
        from deca.service import research

        path = Path(__file__).parent / "keepa_sample.csv"
        spec = load_keepa_csv(path)["B0CZR85NB2"]
        self.assertEqual(spec.length_cm, 175)
        self.assertEqual(spec.width_cm, 154)
        self.assertEqual(spec.height_cm, 49)
        self.assertEqual(spec.weight_kg, 45)
        self.assertEqual(find_keepa_csv(path), path)

        r = research(
            "B0CZR85NB2",
            price=44800,
            csv_path=path,
            fetch=False,
        )
        self.assertEqual(r["package_source"], "Keepa CSV 梱包サイズ")
        self.assertEqual(r["inputs"]["length_cm"], 175)
        self.assertEqual(r["quote"]["girth_cm"], 378)

        no_price = research("B0CZR85NB2", csv_path=path, fetch=False)
        self.assertIn("売価", no_price["missing"])
        self.assertEqual(no_price["package_source"], "Keepa CSV 梱包サイズ")


class AsinParseTest(unittest.TestCase):
    def test_extract(self):
        from deca.amazon import amazon_url, extract_asin

        self.assertEqual(extract_asin("B0CZR85NB2"), "B0CZR85NB2")
        self.assertEqual(
            extract_asin("https://keepa.com/#!product/5-B0CZR85NB2"),
            "B0CZR85NB2",
        )
        self.assertEqual(
            amazon_url("B0CZR85NB2"),
            "https://www.amazon.co.jp/dp/B0CZR85NB2",
        )


if __name__ == "__main__":
    unittest.main()
