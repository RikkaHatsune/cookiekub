"""Быстрая проверка админки через Playwright + установленный Edge."""
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

        page.goto(BASE + "/login.html", wait_until="networkidle")
        page.fill('input[name="email"]', "admin@cookiekub.ru")
        page.fill('input[name="password"]', "Admin123!")
        page.click("#login-submit")
        page.wait_for_url("**/account.html", timeout=10000)

        page.goto(BASE + "/admin.html", wait_until="networkidle")
        page.wait_for_selector("#tab-dashboard:not([hidden])", timeout=10000)
        page.wait_for_timeout(600)
        stats = page.locator("#stats-grid .stat").count()
        print("stats cards:", stats)
        page.screenshot(path=str(OUT / "dev-admin-dashboard.png"), full_page=True)

        page.click('#admin-nav a[data-tab="products"]')
        page.wait_for_selector("#tab-products:not([hidden])", timeout=10000)
        page.wait_for_timeout(500)
        rows = page.locator("#products-body tr").count()
        print("product rows:", rows)
        page.screenshot(path=str(OUT / "dev-admin-products.png"), full_page=True)

        page.click("#product-add")
        page.wait_for_selector(".modal", timeout=5000)
        page.fill('.modal input[name="name"]', "Тестовый кубик")
        page.fill('.modal input[name="price"]', "199")
        page.fill('.modal input[name="stock_qty"]', "7")
        page.click("#modal-save")
        page.wait_for_timeout(1200)
        print("modal still open:", page.locator(".modal").count())
        print("rows after add:", page.locator("#products-body tr").count())

        page.click('#admin-nav a[data-tab="orders"]')
        page.wait_for_timeout(700)
        page.screenshot(path=str(OUT / "dev-admin-orders.png"), full_page=True)

        page.click('#admin-nav a[data-tab="promos"]')
        page.wait_for_timeout(700)
        page.screenshot(path=str(OUT / "dev-admin-promos.png"), full_page=True)

        page.click('#admin-nav a[data-tab="users"]')
        page.wait_for_timeout(700)
        page.screenshot(path=str(OUT / "dev-admin-users.png"), full_page=True)

        page.click('#admin-nav a[data-tab="tickets"]')
        page.wait_for_timeout(700)
        page.screenshot(path=str(OUT / "dev-admin-tickets.png"), full_page=True)

        page.click('#admin-nav a[data-tab="audit"]')
        page.wait_for_timeout(700)
        page.screenshot(path=str(OUT / "dev-admin-audit.png"), full_page=True)

        browser.close()

    if errors:
        print("ERRORS:")
        for error in errors:
            print(" ", error)
        return 1
    print("ADMIN OK")
    return 0


if __name__ == "__main__":
    sys.exit(main())
