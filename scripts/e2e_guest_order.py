"""Полный e2e: гость оформляет заказ, админ завершает/отменяет, проверка статусов."""
from __future__ import annotations

import re
import sys
import time
from pathlib import Path

import requests
from playwright.sync_api import sync_playwright

BASE = "http://127.0.0.1:5000"
OUT = Path(__file__).resolve().parents[1] / "docs" / "screenshots"


def admin_api():
    session = requests.Session()
    response = session.post(
        BASE + "/api/auth/login",
        json={"email": "admin@cookiekub.ru", "password": "Admin123!"},
        timeout=10,
    )
    response.raise_for_status()
    session.headers["Authorization"] = "Bearer " + response.json()["token"]
    return session


def find_order(session, number: str) -> dict:
    response = session.get(BASE + "/api/admin/orders", params={"search": number}, timeout=10)
    response.raise_for_status()
    for order in response.json()["orders"]:
        if order["number"] == number:
            return order
    raise AssertionError("order not found: " + number)


def fill_checkout(page, *, pickup: bool, address: str = "") -> None:
    page.fill("#customer-name", "Иван Тестов")
    page.fill("#customer-phone", "+7 900 123-45-67")
    page.fill("#customer-email", "guest-e2e@example.com")
    if not pickup:
        page.locator("label.choice", has_text="Доставка").click()
        page.fill("#delivery-address", address)
    page.fill("#card-number", "1234 5678 9012 3456")
    page.fill("#card-expiry", "12/29")
    page.fill("#card-cvv", "123")
    page.fill("#card-holder", "IVAN TEST")
    page.check("#privacy-consent")


def main() -> int:
    errors: list[str] = []
    api = admin_api()
    with sync_playwright() as p:
        browser = p.chromium.launch(channel="msedge", headless=True)
        page = browser.new_page(viewport={"width": 1600, "height": 1000})
        page.on("console", lambda msg: errors.append(f"console {msg.type}: {msg.text}") if msg.type == "error" and "404 (NOT FOUND)" not in msg.text else None)
        page.on("pageerror", lambda exc: errors.append(f"pageerror: {exc}"))

        page.goto(BASE + "/catalog.html", wait_until="networkidle")
        page.wait_for_selector(".product-card")
        for index in range(3):
            page.locator("[data-add]").nth(index).click()
        page.goto(BASE + "/cart.html", wait_until="networkidle")
        page.wait_for_selector(".cart-item")
        page.fill("#promo-code", "COOKIE10")
        page.click("#promo-apply")
        page.wait_for_selector("#promo-applied.is-visible")
        page.click("#to-checkout")

        page.wait_for_url("**/checkout.html", timeout=10000)
        page.wait_for_selector("#checkout-form:not([hidden])")
        page.wait_for_timeout(500)
        fill_checkout(page, pickup=True)
        page.click("#pay-button")
        page.wait_for_url(re.compile(r"order\.html\?number=CK-.*"), timeout=20000)
        page.wait_for_selector("#success-banner.is-visible", timeout=15000)
        page.wait_for_selector(".modal", timeout=5000)
        number = page.locator("#order-number-top").inner_text().strip()
        print("guest order:", number)
        print("status processing:", page.locator("#status-title").inner_text())
        page.click(".modal-close")
        page.wait_for_timeout(400)
        page.screenshot(path=str(OUT / "e2e-order-processing.png"), full_page=True)

        order = find_order(api, number)
        print("order id:", order["id"], "total:", order["total_cents"], "last4:", order["payment"]["last4"])
        assert order["payment"]["last4"] == "3456"
        assert "1234" not in str(order)

        response = api.patch(BASE + f"/api/admin/orders/{order['id']}/status", json={"status": "completed"}, timeout=10)
        response.raise_for_status()
        page.reload(wait_until="networkidle")
        page.wait_for_function("document.querySelector('#status-title')?.textContent.includes('Заказ готов')", timeout=15000)
        print("status completed:", page.locator("#status-title").inner_text())
        page.screenshot(path=str(OUT / "e2e-order-completed.png"), full_page=True)

        # Второй заказ: доставка, отмена админом.
        page.goto(BASE + "/catalog.html", wait_until="networkidle")
        page.wait_for_selector(".product-card")
        page.locator("[data-add]").nth(1).click()
        page.goto(BASE + "/checkout.html", wait_until="networkidle")
        page.wait_for_selector("#checkout-form:not([hidden])")
        page.wait_for_timeout(500)
        fill_checkout(page, pickup=False, address="Краснодар, ул. Тестовая, 1, кв. 2")
        page.click("#pay-button")
        page.wait_for_url(re.compile(r"order\.html\?number=CK-.*"), timeout=20000)
        page.wait_for_selector("#success-banner.is-visible", timeout=15000)
        page.click(".modal-close")
        second = page.locator("#order-number-top").inner_text().strip()
        print("delivery order:", second)
        assert "Краснодар" in page.locator("#details-body").inner_text() or "ул. Тестовая" in page.locator("#details-body").inner_text()
        order2 = find_order(api, second)
        response = api.patch(BASE + f"/api/admin/orders/{order2['id']}/status", json={"status": "cancelled"}, timeout=10)
        response.raise_for_status()
        page.reload(wait_until="networkidle")
        page.wait_for_function("document.querySelector('#status-title')?.textContent.includes('отменён')", timeout=15000)
        print("status cancelled:", page.locator("#status-title").inner_text())
        page.screenshot(path=str(OUT / "e2e-order-cancelled.png"), full_page=True)

        # 404 от Flask для несуществующего пути.
        page.goto(BASE + "/no-such-page.html", wait_until="networkidle")
        print("404 response:", page.title())
        browser.close()

    if errors:
        print("ERRORS:")
        for error in errors:
            print(" ", error)
        return 1
    print("E2E OK")
    return 0


if __name__ == "__main__":
    sys.exit(main())
