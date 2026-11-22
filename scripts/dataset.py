"""Create the tidy data distribution and machine-readable catalogue description."""
import csv
import json
from pathlib import Path
from refresh import shift, validate

ROOT = Path(__file__).resolve().parents[1]
BASE = "https://coolcode.ca/releasereceipt/"


def write_csv(web, releases):
    with (web / "receipts.csv").open("w", newline="", encoding="utf-8") as stream:
        writer = csv.writer(stream)
        writer.writerow(["reference_month","industry_group","publication_date","publication_stage","monthly_growth_percent","source_table"])
        for release in releases:
            for sector, values in release["series"].items():
                for offset, rate in enumerate(values, -5):
                    writer.writerow([shift(release["month"], offset), sector, release["published"],
                                     "later table" if offset else "first table", f"{rate:.1f}", release["table"]])


def description(releases):
    begin, end = shift(releases[0]["month"], -5), releases[-1]["month"]
    return {"@context":"https://schema.org","@type":"Dataset","@id":BASE+"#dataset","url":BASE,
            "name":"Canadian monthly GDP growth estimates by publication date",
            "description":"Canada's seasonally adjusted month-over-month real GDP growth as reported in successive Statistics Canada bulletins. Each record identifies its reference month, publication date, industry aggregate, published growth rate and archived source table.",
            "creator":{"@type":"Organization","name":"CoolCode","url":"https://coolcode.ca/"},
            "isBasedOn":"https://doi.org/10.25318/3610043401-eng","spatialCoverage":"Canada",
            "temporalCoverage":f"{begin}/{end}","dateModified":releases[-1]["published"],
            "license":"https://www.statcan.gc.ca/en/terms-conditions/open-licence",
            "distribution":[{"@type":"DataDownload","encodingFormat":fmt,"contentUrl":BASE+"receipts."+ext}
                            for fmt,ext in [("text/csv","csv"),("application/json","json")]]}


if __name__ == "__main__":
    releases=json.loads((ROOT/"web/receipts.json").read_text())["releases"]
    validate(releases)
    write_csv(ROOT/"web", releases)
