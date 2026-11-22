import json
from pathlib import Path
import sys
import unittest
sys.path.insert(0, str(Path(__file__).resolve().parents[1]/"scripts"))
from dataset import description
from refresh import FILE, validate, series_from_table

class ArchiveTests(unittest.TestCase):
    def test_saved_data_and_distribution(self):
        releases = json.loads(FILE.read_text())["releases"]
        validate(releases)
        self.assertEqual(len(description(releases)["distribution"]), 2)
        self.assertEqual(releases[0]["published"], "2025-10-31")
        with self.assertRaises(ValueError):
            validate(releases[:1]+releases[2:])

    def test_source_table_alignment(self):
        def row(values):
            return "<tr>"+"".join(f"<td>{v}</td>" for v in values)+"</tr>"
        html=row(["March 2026","April 2026","May 2026","June 2026","July 2026","August 2026"])
        html+=row(["month-to-month % change"])
        for group in ["All industries","Goods-producing industries","Services-producing industries"]:
            html+=row([group,"−0.1","0.0","-0.0","2.2","0.1","0.3","1,500"])
        self.assertEqual(series_from_table(html, "2026-08")["goods"][-1], 0.3)
        with self.assertRaises(ValueError):
            series_from_table(html, "2026-07")
