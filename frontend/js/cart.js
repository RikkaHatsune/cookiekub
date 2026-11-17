(function () {
  "use strict";
  const { $, initLayout, toast, icon, escapeHTML, money, setBusy, setFormError } = window.CK;
  const PROMO_KEY = "cookiekub.promo.v1";
  let promo = readPromo();

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

  function render() {
    const items = window.CK.Cart.detailed();
    const empty = items.length === 0;
    $("#cart-empty").hidden = !empty;
    $("#cart-layout").hidden = empty;
    if (empty) {
      savePromo(null);
      return;
    }
    const list = $("#cart-list");
    list.replaceChildren(...items.map((item) => {
      const row = document.createElement("div");
      row.className = "cart-item";
      row.innerHTML =
        '<a class="cart-thumb" href="catalog.html"><img src="' + escapeHTML(item.image_url) + '" alt=""></a>' +
        '<div><h3>' + escapeHTML(item.name) + "</h3>" +
        '<div class="meta">' + money(item.price_cents) + " за штуку · осталось " + escapeHTML(item.stock_qty) + " шт.</div></div>" +
        '<div class="cart-controls">' +
        '<div class="qty"><button type="button" data-minus aria-label="Меньше">−</button><span>' + item.quantity + '</span><button type="button" data-plus aria-label="Больше">+</button></div>' +
        '<span class="cart-line-total">' + money(item.line_total_cents) + "</span>" +
        '<button type="button" class="icon-btn" data-remove aria-label="Удалить">' + icon("trash") + "</button>" +
        "</div>";
      row.querySelector("[data-minus]").addEventListener("click", () => {
        window.CK.Cart.setQuantity(item.product_id, item.quantity - 1);
        render(); refreshPromo(true);
      });
      row.querySelector("[data-plus]").addEventListener("click", () => {
        if (item.quantity >= Number(item.stock_qty)) { toast("Больше нет на складе.", "error"); return; }
        window.CK.Cart.setQuantity(item.product_id, item.quantity + 1);
        render(); refreshPromo(true);
      });
      row.querySelector("[data-remove]").addEventListener("click", () => {
        window.CK.Cart.remove(item.product_id);
        render(); refreshPromo(true);
      });
      return row;
    }));
    $("#cart-lines-note").textContent = items.length + " " + plural(items.length, ["позиция", "позиции", "позиций"]);
    renderTotals();
  }

  function plural(n, forms) {
    const mod10 = n % 10, mod100 = n % 100;
    if (mod10 === 1 && mod100 !== 11) return forms[0];
    if (mod10 >= 2 && mod10 <= 4 && (mod100 < 10 || mod100 >= 20)) return forms[1];
    return forms[2];
  }

  function renderTotals() {
    const subtotal = window.CK.Cart.subtotal();
    const discount = promo ? Math.min(Number(promo.discount_cents) || 0, subtotal) : 0;
    const total = Math.max(0, subtotal - discount);
    $("#sum-subtotal").textContent = money(subtotal);
    $("#sum-total").textContent = money(total);
    $("#sum-discount-row").hidden = discount <= 0;
    $("#sum-discount").textContent = "−" + money(discount);
    $("#sum-promo-label").textContent = promo ? "(" + promo.code + ", " + (promo.label || "") + ")" : "";
    const applied = $("#promo-applied");
    applied.classList.toggle("is-visible", Boolean(promo));
    if (promo) {
      $("#promo-applied-text").textContent = promo.code + " · " + (promo.label || "скидка") + " · −" + money(discount);
      $("#promo-code").value = promo.code;
    }
    $("#promo-hint").hidden = Boolean(promo);
  }

  async function applyPromo(code, silent) {
    const input = $("#promo-code");
    const value = (code || input.value || "").trim().toUpperCase();
    if (!value) { if (!silent) setFormError($("#promo-error"), "Введите промокод."); return; }
    const subtotal = window.CK.Cart.subtotal();
    if (subtotal <= 0) return;
    try {
      const data = await window.CKApi.post("/api/promos/validate", { code: value, subtotal_cents: subtotal });
      savePromo(data.promo);
      setFormError($("#promo-error"), "");
      renderTotals();
      if (!silent) toast("Промокод " + data.promo.code + " применён: −" + money(data.promo.discount_cents), "success");
    } catch (error) {
      if (!silent) {
        savePromo(null);
        renderTotals();
        setFormError($("#promo-error"), window.CK.apiMessage(error));
      } else if (promo) {
        savePromo(null);
        renderTotals();
      }
    }
  }

  async function refreshPromo(silent) {
    if (!promo) return;
    await applyPromo(promo.code, silent);
  }

  async function boot() {
    await initLayout();
    render();
    if (promo) {
      if (window.CK.Cart.subtotal() > 0) refreshPromo(true);
      else savePromo(null);
    }
  }

  $("#promo-apply").addEventListener("click", async (event) => {
    const button = event.currentTarget;
    setBusy(button, true, "Проверяем");
    try { await applyPromo(); } finally { setBusy(button, false); }
  });
  $("#promo-code").addEventListener("keydown", (event) => {
    if (event.key === "Enter") { event.preventDefault(); $("#promo-apply").click(); }
  });
  $("#promo-remove").addEventListener("click", () => {
    savePromo(null);
    $("#promo-code").value = "";
    setFormError($("#promo-error"), "");
    renderTotals();
    toast("Промокод убран.", "success");
  });
  $("#to-checkout").addEventListener("click", (event) => {
    if (window.CK.Cart.count() === 0) { event.preventDefault(); toast("Сначала добавьте печеньки.", "error"); }
  });
  document.addEventListener("DOMContentLoaded", boot);
})();
