"""Update the saved archive from Statistics Canada's monthly GDP-by-industry releases."""
from calendar import month_name
from datetime import date
from html.parser import HTMLParser
import json
from pathlib import Path
import re
from urllib.error import HTTPError
from urllib.parse import urljoin, urlsplit
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[1]
FILE = ROOT / "web/receipts.json"
DOMAIN = "www150.statcan.gc.ca"
INDICATOR = "https://www150.statcan.gc.ca/t1/tbl1/en/tv.action?pid=3610043401"
GROUPS = {"All industries": "all", "Goods-producing industries": "goods", "Services-producing industries": "services"}
MONTHS = {month.lower(): n for n, month in enumerate(month_name) if n}
MONTH_RE = r"(" + "|".join(MONTHS) + r")\s*(20\d{2})"


def tidy(s):
    return " ".join(s.replace("−", "-").split())


class Page(HTMLParser):
    def __init__(self, html):
        super().__init__(convert_charrefs=True)
        self.links, self.rows, self.items = [], [], {}
        self.current = {}
        self.row = []
        self.feed(html)

    def handle_starttag(self, tag, attrs):
        if tag == "tr":
            self.row = []
        if tag in ("a", "td", "th", "h1"):
            self.current[tag] = [dict(attrs), []]

    def handle_data(self, data):
        for _, values in self.current.values():
            values.append(data)

    def handle_endtag(self, tag):
        if tag == "tr" and self.row:
            self.rows.append(self.row)
        if tag not in self.current:
            return
        attrs, chunks = self.current.pop(tag)
        value = tidy(" ".join(chunks))
        if tag == "a" and "href" in attrs:
            self.links.append((value, attrs["href"]))
        elif tag in ("td", "th"):
            self.row.append(value)
        elif tag == "h1":
            self.items[tag] = value


def fetch(url):
    parts = urlsplit(url)
    if parts.scheme != "https" or parts.hostname != DOMAIN:
        raise ValueError(f"Unexpected source URL {url}")
    request = Request(url, headers={"User-Agent": "CoolCode-ReleaseReceipt/1.0 (+https://coolcode.ca/releasereceipt/)"})
    with urlopen(request, timeout=40) as response:
        return response.read().decode("utf-8-sig")


def iso_month(match):
    return f"{match[2]}-{MONTHS[match[1].lower()]:02d}"


def shift(month, delta):
    y, m = map(int, month.split("-"))
    y, m = divmod(y * 12 + m - 1 + delta, 12)
    return f"{y:04d}-{m + 1:02d}"


def series_from_table(html, month):
    rows = Page(html).rows
    expected = [shift(month, i) for i in range(-5, 1)]
    periods = [[iso_month(match) for cell in row if (match := re.search(MONTH_RE, cell, re.I))] for row in rows]
    if not any(period[:6] == expected for period in periods):
        raise ValueError(f"Month columns changed in {month}")
    if "month-to-month % change" not in tidy(" ".join(cell for row in rows for cell in row)).lower():
        raise ValueError(f"Unit changed in {month}")
    series = {}
    for row in rows:
        if row[0] in GROUPS:
            cells = row[1:7]
            if len(cells) != 6 or not all(re.fullmatch(r"[+-]?\d+(\.\d+)?", cell) for cell in cells):
                raise ValueError(f"Missing or unrecognized rate in {row}")
            series[GROUPS[row[0]]] = [float(cell) for cell in cells]
    if len(series) != len(GROUPS):
        raise ValueError(f"Missing industry group in {month}")
    return series


def matching_link(page, pattern, base):
    for text, href in page.links:
        if re.search(pattern, text, re.I):
            return urljoin(base, href).replace(".ca/daily-quotidien/", ".ca/n1/daily-quotidien/")
    raise ValueError(f"Expected link missing in {base}: {pattern}")


def latest_article():
    # The main table's source release date identifies the day's edition of The Daily.
    html = fetch(INDICATOR)
    match = re.search(r"Release date:\s*(?:<[^>]+>\s*)*(20\d\d-\d\d-\d\d)", html, re.I)
    if not match:
        raise ValueError("The indicator table's release date could not be read")
    code = date.fromisoformat(match[1]).strftime("%y%m%d")
    for letter in "abcdefgh":
        url = f"https://{DOMAIN}/n1/daily-quotidien/{code}/dq{code}{letter}-eng.htm"
        try:
            page = Page(fetch(url))
        except HTTPError as err:
            if err.code == 404:
                continue
            raise
        if re.match(r"Gross domestic product by industry,\s*" + MONTH_RE, page.items.get("h1",""), re.I):
            return url
    raise ValueError(f"Monthly GDP bulletin not found for {match[1]}")


def collect(known, url):
    additions = []
    last = known[-1]["published"]
    while True:
        match = re.search(r"/(\d{6})/dq\d{6}[a-z]-eng.htm$", url)
        if not match:
            raise ValueError(f"Unexpected bulletin URL {url}")
        code = match[1]
        published = f"20{code[:2]}-{code[2:4]}-{code[4:]}"
        if published == last:
            return list(reversed(additions))
        if published < last or (additions and published >= additions[-1]["published"]) or len(additions) >= 120:
            raise ValueError("Release chronology does not join the saved history")
        article = Page(fetch(url))
        match = re.match(r"Gross domestic product by industry,\s*"+MONTH_RE, article.items.get("h1", ""), re.I)
        if not match:
            raise ValueError(f"Unrecognized bulletin title {url}")
        month = iso_month(match)
        table = matching_link(article, r"Table\s*1\s*Monthly gross domestic product by industry", url)
        additions.append(dict(published=published, month=month, article=url, table=table, series=series_from_table(fetch(table), month)))
        url = matching_link(article, r"^Previous release$", url)


def validate(releases):
    if not releases:
        raise ValueError("No releases")
    for index, release in enumerate(releases):
        if index and (shift(releases[index-1]["month"], 1) != release["month"] or releases[index-1]["published"] >= release["published"]):
            raise ValueError("Missing or duplicate release")
        assert date.fromisoformat(release["published"])
        if set(release["series"]) != set(GROUPS.values()) or any(len(v) != 6 for v in release["series"].values()):
            raise ValueError("Incomplete industry data")
        for key in ("table", "article"):
            if not release[key].startswith(f"https://{DOMAIN}/n1/daily-quotidien/"):
                raise ValueError("Unknown source")


def main():
    saved = json.loads(FILE.read_text())
    releases = saved["releases"] + collect(saved["releases"], latest_article())
    validate(releases)
    snapshot = {"checked": date.today().isoformat(), "releases": releases}
    tmp = FILE.with_suffix(".tmp")
    tmp.write_text(json.dumps(snapshot, indent=2, ensure_ascii=False)+"\n", encoding="utf-8")
    tmp.replace(FILE)
    print(f"{len(releases)} releases through {releases[-1]['published']}")

if __name__ == "__main__":
    main()
