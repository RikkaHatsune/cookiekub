"""Скриншоты основных страниц витрины через Edge."""
from __future__ import annotations

import sys
from pathlib import Path

from playwright.sync_api import sync_playwright

BASE = "http://127.0.0.1:5000"
OUT = Path(__file__).resolve().parents[1] / "docs" / "screenshots"


def main() -> int:
    errors: list[str] = []
    with sync_playwright() as p:
        browser = p.chromium.launch(channel="msedge", headless=True)
        page = browser.new_page(viewport={"width": 1600, "height": 1000})
        page.on("console", lambda msg: errors.append(f"console {msg.type}: {msg.text}") if msg.type == "error" else None)
        page.on("pageerror", lambda exc: errors.append(f"pageerror: {exc}"))

        page.goto(BASE + "/index.html", wait_until="networkidle")
        page.wait_for_timeout(500)
        print("home cards:", page.locator(".product-card").count())
        page.screenshot(path=str(OUT / "dev-home.png"), full_page=True)

        page.goto(BASE + "/catalog.html", wait_until="networkidle")
        page.wait_for_selector(".product-card", timeout=10000)
        page.wait_for_timeout(500)
        print("catalog cards:", page.locator(".product-card").count())
        page.screenshot(path=str(OUT / "dev-catalog.png"), full_page=True)

        for index in range(3):
            page.locator("[data-add]").nth(index).click()
        page.wait_for_timeout(400)
        page.goto(BASE + "/cart.html", wait_until="networkidle")
        page.wait_for_selector(".cart-item", timeout=10000)
        page.wait_for_timeout(400)
        page.screenshot(path=str(OUT / "dev-cart.png"), full_page=True)

        page.fill("#promo-code", "COOKIE10")
        page.click("#promo-apply")
        page.wait_for_selector("#promo-applied.is-visible", timeout=10000)
        page.wait_for_timeout(600)
        print("cart total:", page.locator("#sum-total").inner_text())
        page.screenshot(path=str(OUT / "dev-cart-promo.png"), full_page=True)

        page.goto(BASE + "/privacy.html", wait_until="networkidle")
        page.screenshot(path=str(OUT / "dev-privacy.png"), full_page=True)

        page.goto(BASE + "/404.html", wait_until="networkidle")
        page.screenshot(path=str(OUT / "dev-404.png"), full_page=True)

        page.goto(BASE + "/500.html", wait_until="networkidle")
        page.screenshot(path=str(OUT / "dev-500.png"), full_page=True)

        page.set_viewport_size({"width": 390, "height": 844})
        page.goto(BASE + "/index.html", wait_until="networkidle")
        page.wait_for_timeout(500)
        page.screenshot(path=str(OUT / "dev-mobile-home.png"), full_page=True)
        page.goto(BASE + "/catalog.html", wait_until="networkidle")
        page.wait_for_selector(".product-card", timeout=10000)
        page.wait_for_timeout(500)
        page.screenshot(path=str(OUT / "dev-mobile-catalog.png"), full_page=True)

        browser.close()

    if errors:
        print("ERRORS:")
        for error in errors:
            print(" ", error)
        return 1
    print("PAGES OK")
    return 0


if __name__ == "__main__":
    sys.exit(main())
