from pathlib import Path
from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[1]
HTML = ROOT / "docs" / "architecture" / "cookiekub-user-journey.html"
OUT = ROOT / "docs" / "screenshots" / "cookiekub-user-journey.png"

with sync_playwright() as p:
    browser = p.chromium.launch(channel="msedge", headless=True)
    page = browser.new_page(viewport={"width": 1600, "height": 1000})
    page.goto(HTML.as_uri(), wait_until="networkidle")
    page.wait_for_timeout(2500)
    page.screenshot(path=str(OUT), full_page=True)
    print(OUT, page.evaluate("document.documentElement.scrollWidth"), page.evaluate("document.documentElement.scrollHeight"))
    browser.close()
