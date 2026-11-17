"""Финальные скриншоты CookieKub 1600px на чистом сиде."""
from __future__ import annotations

import sys
from pathlib import Path

import requests
from playwright.sync_api import sync_playwright

BASE = "http://127.0.0.1:5000"
OUT = Path(__file__).resolve().parents[1] / "docs" / "screenshots"
SCREENSHOT_CSS = """
document.addEventListener('DOMContentLoaded', function () {
  var style = document.createElement('style');
  style.textContent = '.site-header{position:relative!important} .summary,.side-nav,.admin-side{position:static!important}';
  document.head.appendChild(style);
});
"""


def clear_toasts(page):
    page.evaluate("document.querySelectorAll('.toast-wrap').forEach((el) => el.remove())")


def main() -> int:
    api = requests.Session()
    products = api.get(BASE + "/api/products", timeout=10).json()["products"]
    cafes = api.get(BASE + "/api/cafes", timeout=10).json()["cafes"]
    cafe_id = cafes[0]["id"]
    guest_email = "guest-final@example.com"

    order = api.post(BASE + "/api/orders", json={
        "items": [{"product_id": products[0]["id"], "quantity": 1},
                  {"product_id": products[1]["id"], "quantity": 1},
                  {"product_id": products[2]["id"], "quantity": 1}],
        "fulfillment": "pickup",
        "cafe_id": cafe_id,
        "customer_name": "Иван Тестов",
        "customer_phone": "+7 900 123-45-67",
        "customer_email": guest_email,
        "promo_code": "COOKIE10",
        "privacy_consent": True,
        "payment": {"last4": "3456"},
    }, timeout=10)
    order.raise_for_status()
    guest_number = order.json()["order"]["number"]
    print("guest order:", guest_number)

    login = api.post(BASE + "/api/auth/login", json={"email": "user@cookiekub.ru", "password": "User123!"}, timeout=10)
    login.raise_for_status()
    user_token = login.json()["token"]
    user_order = api.post(BASE + "/api/orders", headers={"Authorization": "Bearer " + user_token}, json={
        "items": [{"product_id": products[3]["id"], "quantity": 2}],
        "fulfillment": "delivery",
        "delivery_address": "Краснодар, ул. Красная, 10, кв. 5",
        "customer_name": "Кубик Денис",
        "customer_phone": "+7 900 765-43-21",
        "privacy_consent": True,
        "payment": {"last4": "1111"},
    }, timeout=10)
    user_order.raise_for_status()
    print("user order:", user_order.json()["order"]["number"])

    ticket = api.post(BASE + "/api/tickets", json={
        "email": "guest-final@example.com",
        "subject": "Не пришло письмо о заказе",
        "category": "bug",
        "message": "Оформил заказ, но письмо на почту не пришло. Проверьте, пожалуйста.",
    }, timeout=10)
    ticket.raise_for_status()

    errors: list[str] = []
    with sync_playwright() as p:
        browser = p.chromium.launch(channel="msedge", headless=True)
        page = browser.new_page(viewport={"width": 1600, "height": 1000})
        page.add_init_script(SCREENSHOT_CSS)
        page.on("console", lambda msg: errors.append(f"console {msg.type}: {msg.text}") if msg.type == "error" else None)
        page.on("pageerror", lambda exc: errors.append(f"pageerror: {exc}"))

        page.goto(BASE + "/index.html", wait_until="networkidle")
        page.wait_for_timeout(700)
        page.screenshot(path=str(OUT / "cookiekub-home.png"), full_page=True)

        page.goto(BASE + "/catalog.html", wait_until="networkidle")
        page.wait_for_selector(".product-card", timeout=10000)
        page.wait_for_timeout(500)
        page.screenshot(path=str(OUT / "cookiekub-catalog.png"), full_page=True)

        for index in range(3):
            page.locator("[data-add]").nth(index).click()
        page.goto(BASE + "/cart.html", wait_until="networkidle")
        page.wait_for_selector(".cart-item", timeout=10000)
        page.fill("#promo-code", "COOKIE10")
        page.click("#promo-apply")
        page.wait_for_selector("#promo-applied.is-visible", timeout=10000)
        page.wait_for_timeout(500)
        clear_toasts(page)
        page.screenshot(path=str(OUT / "cookiekub-cart.png"), full_page=True)

        page.click("#to-checkout")
        page.wait_for_url("**/checkout.html", timeout=10000)
        page.wait_for_selector("#checkout-form:not([hidden])", timeout=10000)
        page.fill("#customer-name", "Иван Тестов")
        page.fill("#customer-phone", "+7 900 123-45-67")
        page.fill("#customer-email", guest_email)
        page.fill("#card-number", "1234 5678 9012 3456")
        page.fill("#card-expiry", "12/29")
        page.fill("#card-cvv", "123")
        page.fill("#card-holder", "IVAN TEST")
        page.check("#privacy-consent")
        page.wait_for_timeout(400)
        page.screenshot(path=str(OUT / "cookiekub-checkout.png"), full_page=True)

        page.evaluate(
            """(order) => {
              localStorage.setItem('cookiekub.guestOrders.v1', JSON.stringify([{number: order.number, email: order.email, created_at: new Date().toISOString()}]));
              localStorage.setItem('cookiekub.lastOrder.v1', JSON.stringify({number: order.number, email: order.email}));
            }""",
            {"number": guest_number, "email": guest_email},
        )
        page.goto(BASE + "/order.html?number=" + guest_number + "&new=1", wait_until="networkidle")
        page.wait_for_selector("#success-banner.is-visible", timeout=15000)
        page.wait_for_timeout(700)
        page.screenshot(path=str(OUT / "cookiekub-order-success.png"), full_page=True)
        page.click(".modal-close")
        page.wait_for_timeout(500)
        page.screenshot(path=str(OUT / "cookiekub-order-processing.png"), full_page=True)

        page.goto(BASE + "/login.html", wait_until="networkidle")
        page.wait_for_timeout(400)
        page.screenshot(path=str(OUT / "cookiekub-login.png"), full_page=True)

        page.goto(BASE + "/register.html", wait_until="networkidle")
        page.wait_for_timeout(400)
        page.screenshot(path=str(OUT / "cookiekub-register.png"), full_page=True)

        page.goto(BASE + "/support.html", wait_until="networkidle")
        page.wait_for_timeout(400)
        page.screenshot(path=str(OUT / "cookiekub-support.png"), full_page=True)

        page.goto(BASE + "/privacy.html", wait_until="networkidle")
        page.screenshot(path=str(OUT / "cookiekub-privacy.png"), full_page=True)

        page.goto(BASE + "/404.html", wait_until="networkidle")
        page.screenshot(path=str(OUT / "cookiekub-404.png"), full_page=True)

        page.goto(BASE + "/500.html", wait_until="networkidle")
        page.screenshot(path=str(OUT / "cookiekub-500.png"), full_page=True)

        # 403 гость
        guest = browser.new_context(viewport={"width": 1600, "height": 1000}).new_page()
        guest.add_init_script(SCREENSHOT_CSS)
        guest.goto(BASE + "/admin.html", wait_until="networkidle")
        guest.wait_for_url("**/403.html?reason=auth&next=admin.html", timeout=10000)
        guest.screenshot(path=str(OUT / "cookiekub-403-guest.png"), full_page=True)

        # Пользователь
        page.goto(BASE + "/login.html", wait_until="networkidle")
        page.fill("#login-email", "user@cookiekub.ru")
        page.fill("#login-password", "User123!")
        page.click("#login-submit")
        page.wait_for_url("**/account.html", timeout=10000)
        page.wait_for_timeout(800)
        page.screenshot(path=str(OUT / "cookiekub-account.png"), full_page=True)

        page.goto(BASE + "/admin.html", wait_until="networkidle")
        page.wait_for_url("**/403.html?reason=admin&next=admin.html", timeout=10000)
        page.wait_for_timeout(500)
        page.screenshot(path=str(OUT / "cookiekub-403-user.png"), full_page=True)

        # Админ
        admin = browser.new_context(viewport={"width": 1600, "height": 1000}).new_page()
        admin.add_init_script(SCREENSHOT_CSS)
        admin.goto(BASE + "/login.html", wait_until="networkidle")
        admin.fill("#login-email", "admin@cookiekub.ru")
        admin.fill("#login-password", "Admin123!")
        admin.click("#login-submit")
        admin.wait_for_url("**/account.html", timeout=10000)
        admin.goto(BASE + "/admin.html", wait_until="networkidle")
        admin.wait_for_selector("#tab-dashboard:not([hidden])", timeout=10000)
        admin.wait_for_timeout(700)
        admin.screenshot(path=str(OUT / "cookiekub-admin-dashboard.png"), full_page=True)

        for tab, name in [("products", "cookiekub-admin-products"), ("orders", "cookiekub-admin-orders"),
                          ("promos", "cookiekub-admin-promos"), ("users", "cookiekub-admin-users"),
                          ("tickets", "cookiekub-admin-tickets"), ("audit", "cookiekub-admin-audit")]:
            admin.click('#admin-nav a[data-tab="' + tab + '"]')
            admin.wait_for_selector("#tab-" + tab + ":not([hidden])", timeout=10000)
            admin.wait_for_timeout(900)
            clear_toasts(admin)
            admin.screenshot(path=str(OUT / (name + ".png")), full_page=True)

        browser.close()

    if errors:
        print("ERRORS:")
        for error in errors:
            print(" ", error)
        return 1
    print("FINAL SCREENSHOTS OK")
    return 0


if __name__ == "__main__":
    sys.exit(main())
