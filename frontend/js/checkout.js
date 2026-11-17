(function () {
  "use strict";
  const { $, money, escapeHTML, toast, setBusy, setFormError, initLayout, Cart, GuestOrders, apiMessage } = window.CK;
  const PROMO_KEY = "cookiekub.promo.v1";

  let user = null;
  let cafes = [];
  let promo = readPromo();
  let submitting = false;

  function readPromo() {
    try { return JSON.parse(sessionStorage.getItem(PROMO_KEY) || "null"); } catch (_) { return null; }
  }
  function savePromo(value) {
    promo = value;
    try {
      if (value) sessionStorage.setItem(PROMO_KEY, JSON.stringify(value));
      else sessionStorage.removeItem(PROMO_KEY);
    } catch (_) { /* ignore */ }
  }

  function renderItems() {
    const items = Cart.detailed();
    const box = $("#checkout-items");
    if (!items.length) return;
    box.replaceChildren(...items.map((item) => {
      const row = document.createElement("div");
      row.className = "summary-item";
      row.innerHTML =
        '<img src="' + escapeHTML(item.image_url) + '" alt="">' +
        '<div class="summary-item-main"><strong>' + escapeHTML(item.name) + "</strong>" +
        '<span class="muted">' + item.quantity + " × " + money(item.price_cents) + "</span></div>" +
        '<span class="summary-item-total">' + money(item.line_total_cents) + "</span>";
      return row;
    }));
  }

  function renderTotals() {
    const subtotal = Cart.subtotal();
    const discount = promo ? Math.min(Number(promo.discount_cents) || 0, subtotal) : 0;
    const total = Math.max(0, subtotal - discount);
    $("#checkout-subtotal").textContent = money(subtotal);
    $("#checkout-discount-row").hidden = discount <= 0;
    $("#checkout-discount").textContent = "−" + money(discount);
    $("#checkout-promo-label").textContent = promo ? "(" + promo.code + ")" : "";
    $("#checkout-total").textContent = money(total);
  }

  async function refreshPromo() {
    if (!promo) return;
    try {
      const data = await window.CKApi.post("/api/promos/validate", {
        code: promo.code,
        subtotal_cents: Cart.subtotal(),
      });
      savePromo(data.promo);
    } catch (_) {
      savePromo(null);
    }
    renderTotals();
  }

  function renderCafes() {
    const list = $("#cafe-list");
    if (!cafes.length) {
      list.innerHTML = '<p class="muted">Кафе временно недоступны. Выберите доставку.</p>';
      return;
    }
    list.replaceChildren(...cafes.map((cafe, index) => {
      const label = document.createElement("label");
      label.className = "cafe-choice-item" + (cafe.is_open ? "" : " is-closed");
      label.innerHTML =
        '<input type="radio" name="cafe" value="' + cafe.id + '"' + (index === 0 ? " checked" : "") + ">" +
        '<span class="cafe-choice-main"><strong>' + escapeHTML(cafe.name) + "</strong>" +
        '<span class="muted">' + escapeHTML(cafe.address) + " · " + escapeHTML(cafe.opens_at + "–" + cafe.closes_at) + "</span></span>" +
        '<span class="badge ' + (cafe.is_open ? "green" : "red") + '">' + escapeHTML(cafe.status_text) + "</span>";
      label.querySelector("input").addEventListener("change", updateFulfillment);
      return label;
    }));
  }

  function updateFulfillment() {
    const mode = document.querySelector('input[name="fulfillment"]:checked').value;
    $("#pickup-block").hidden = mode !== "pickup";
    $("#delivery-block").hidden = mode !== "delivery";
    $("#delivery-address").required = mode === "delivery";
  }

  function cardBrand(number) {
    const digits = number.replace(/\D/g, "");
    if (/^4/.test(digits)) return "VISA";
    if (/^5[1-5]/.test(digits) || /^2[2-7]/.test(digits)) return "MC";
    if (/^2/.test(digits)) return "MIR";
    if (/^3[47]/.test(digits)) return "AMEX";
    return "CARD";
  }

  function bindCardInputs() {
    const number = $("#card-number");
    number.addEventListener("input", () => {
      const digits = number.value.replace(/\D/g, "").slice(0, 19);
      number.value = digits.replace(/(.{4})/g, "$1 ").trim();
      $("#card-brand").textContent = cardBrand(digits);
    });
    const expiry = $("#card-expiry");
    expiry.addEventListener("input", () => {
      const digits = expiry.value.replace(/\D/g, "").slice(0, 4);
      expiry.value = digits.length > 2 ? digits.slice(0, 2) + "/" + digits.slice(2) : digits;
    });
    $("#card-cvv").addEventListener("input", (event) => {
      event.target.value = event.target.value.replace(/\D/g, "").slice(0, 4);
    });
  }

  function validate() {
    const name = $("#customer-name").value.trim();
    const email = $("#customer-email").value.trim();
    const phone = $("#customer-phone").value.trim();
    if (name.length < 2) return "Напишите имя — хотя бы два символа.";
    if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email)) return "Проверьте email: на него придёт «письмо» и доступ к заказу.";
    if (phone.replace(/\D/g, "").length < 6) return "Укажите телефон для связи.";
    const mode = document.querySelector('input[name="fulfillment"]:checked').value;
    if (mode === "pickup" && !document.querySelector('input[name="cafe"]:checked')) return "Выберите кафе для самовывоза.";
    if (mode === "delivery" && $("#delivery-address").value.trim().length < 5) return "Укажите адрес доставки.";
    if (!user && !$("#privacy-consent").checked) return "Для гостевого заказа нужно согласие на обработку персональных данных.";
    return "";
  }

  function payload() {
    const mode = document.querySelector('input[name="fulfillment"]:checked').value;
    const input = {
      items: Cart.read().map((item) => ({ product_id: item.product_id, quantity: item.quantity })),
      fulfillment: mode,
      customer_name: $("#customer-name").value.trim(),
      customer_phone: $("#customer-phone").value.trim(),
      customer_comment: $("#customer-comment").value.trim(),
      promo_code: promo ? promo.code : null,
    };
    if (mode === "pickup") {
      const cafe = document.querySelector('input[name="cafe"]:checked');
      input.cafe_id = cafe ? Number(cafe.value) : null;
    } else {
      input.delivery_address = $("#delivery-address").value.trim();
    }
    if (!user) {
      input.customer_email = $("#customer-email").value.trim();
      input.privacy_consent = $("#privacy-consent").checked;
    } else {
      input.privacy_consent = true;
    }
    const digits = $("#card-number").value.replace(/\D/g, "");
    if (digits.length >= 4) input.payment = { last4: digits.slice(-4) };
    return input;
  }

  async function submit(event) {
    event.preventDefault();
    if (submitting) return;
    const error = validate();
    if (error) { setFormError($("#checkout-error"), error); return; }
    setFormError($("#checkout-error"), "");
    submitting = true;
    const button = $("#pay-button");
    setBusy(button, true, "Печём заказ…");
    try {
      const data = await window.CKApi.post("/api/orders", payload());
      const order = data.order;
      if (!user) GuestOrders.remember(order.number, order.customer.email);
      Cart.clear();
      savePromo(null);
      sessionStorage.setItem("cookiekub.lastOrder", JSON.stringify({ number: order.number, email: order.customer.email, new: true }));
      location.href = "order.html?number=" + encodeURIComponent(order.number) + "&new=1";
    } catch (err) {
      if (err.isAuth) {
        location.href = "403.html?reason=auth&next=" + encodeURIComponent("checkout.html");
        return;
      }
      setFormError($("#checkout-error"), apiMessage(err));
      if (err.status === 0) window.CK.showServerOverlay();
    } finally {
      submitting = false;
      setBusy(button, false);
    }
  }

  async function main() {
    user = await initLayout({ next: "checkout.html" });
    if (!user && window.CKApi.getToken()) return; // идёт редирект на 403
    if (!Cart.count()) {
      $("#checkout-form").hidden = true;
      $("#checkout-empty").hidden = false;
      return;
    }
    $("#checkout-form").hidden = false;
    $("#who-badge").textContent = user ? "KubanoID" : "гость";
    if (user) {
      $("#customer-name").value = user.full_name || "";
      $("#customer-email").value = user.email || "";
      $("#customer-email").readOnly = true;
      $("#guest-note").innerHTML = "Вы вошли как <strong>" + escapeHTML(user.full_name || user.email) + "</strong>. Email заказа привязан к аккаунту KubanoID.";
      $("#consent-block").hidden = true;
    }
    renderItems();
    renderTotals();
    bindCardInputs();
    updateFulfillment();
    document.querySelectorAll('input[name="fulfillment"]').forEach((radio) => radio.addEventListener("change", updateFulfillment));
    $("#checkout-form").addEventListener("submit", submit);

    try {
      const data = await window.CKApi.get("/api/cafes");
      cafes = data.cafes || [];
      renderCafes();
    } catch (err) {
      $("#cafe-list").innerHTML = '<p class="muted">Не удалось загрузить кафе. Обновите страницу.</p>';
      if (err.isNetwork) window.CK.showServerOverlay();
    }
    refreshPromo();
  }

  main();
})();
