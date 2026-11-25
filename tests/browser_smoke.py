"""Exercise the built starter at a project subpath in Chromium."""
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
import os
import json
import shutil
import tempfile
import threading
from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[1]


class QuietHandler(SimpleHTTPRequestHandler):
    def log_message(self, *args):
        pass


def main():
    screenshots = ROOT / "browser-checks"
    screenshots.mkdir(exist_ok=True)
    with tempfile.TemporaryDirectory() as temporary:
        shutil.copytree(ROOT / "dist", Path(temporary) / "example-tool")
        server = ThreadingHTTPServer(("127.0.0.1", 0), partial(QuietHandler, directory=temporary))
        threading.Thread(target=server.serve_forever, daemon=True).start()
        try:
            with sync_playwright() as p:
                browser = p.chromium.launch(executable_path=os.environ.get("CHROMIUM_PATH"))
                page = browser.new_page(viewport={"width": 1280, "height": 1000})
                errors = []
                page.on("pageerror", lambda error: errors.append(str(error)))
                page.goto(f"http://127.0.0.1:{server.server_port}/example-tool/")
                page.locator("#month").select_option("2026-06")
                assert "June 2026" in page.locator("#selection").inner_text()
                assert page.locator("#first").inner_text() == "+0.3%"
                page.locator("#sector").select_option("goods")
                assert "Goods-producing" in page.locator("#selection").inner_text()
                assert page.locator("#ledger a").count() >= 3
                with page.expect_download() as pending:
                    page.locator("#download").click()
                assert pending.value.suggested_filename == "gdp-2026-06-goods.csv"
                page.locator("#ranking button").first.click()
                page.locator("#watch-cards article").first.wait_for()
                assert page.locator("#watch-cards article").count() >= 25
                page.locator("#watch-search").fill("Nova Scotia")
                assert page.locator("#watch-cards article").count() == 2
                page.locator("#watch-cards button", has_text="View observations").first.click()
                assert page.locator("#watch-history tbody tr").count() >= 36
                with page.expect_download() as calendar:
                    page.locator("#watch-ics").click()
                assert calendar.value.suggested_filename.endswith(".ics")
                page.locator("summary", has_text="Add a public vector").click()
                info=[{"status":"SUCCESS","object":{"responseStatusCode":0,"productId":18100004,"vectorId":999999999,"SeriesTitleEn":"Additional test vector","memberUomCode":17}}]
                points=[{"status":"SUCCESS","object":{"responseStatusCode":0,"vectorId":999999999,"vectorDataPoint":[{"refPer":"2026-01-01","value":123,"releaseTime":"2026-02-01T08:30","scalarFactorCode":0,"decimals":1,"symbolCode":3,"statusCode":0,"securityLevelCode":0,"frequencyCode":6}]}}]
                page.route("**/getSeriesInfoFromVector",lambda route:route.fulfill(content_type="application/json",body=json.dumps(info)))
                page.route("**/getDataFromVectorsAndLatestNPeriods",lambda route:route.fulfill(content_type="application/json",body=json.dumps(points)))
                page.locator("#custom-vector").fill("v999999999")
                page.locator("#watch-custom").click()
                page.wait_for_function("document.getElementById('watch-status').textContent.includes('Saved v999999999')")
                page.reload()
                page.locator("#watch-search").fill("Additional test vector")
                page.locator("#watch-cards article").first.wait_for()
                assert "123" in page.locator("#watch-cards").inner_text()
                assert "revised" in page.locator("#watch-cards").inner_text()
                with page.expect_download() as backup:
                    page.locator("#watch-export").click()
                assert backup.value.suggested_filename.endswith(".json")
                page.screenshot(path=str(screenshots / "desktop.png"), full_page=True)
                page.set_viewport_size({"width": 390, "height": 844})
                assert page.evaluate("document.documentElement.scrollWidth <= window.innerWidth")
                page.screenshot(path=str(screenshots / "mobile.png"), full_page=True)
                assert not errors, errors
                browser.close()
            print("Browser checks passed: GDP selection, source links, export, ranking and mobile layout")
        finally:
            server.shutdown()


if __name__ == "__main__":
    main()
