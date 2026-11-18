(function () {
  "use strict";
  const {
    $, money, formatDate, escapeHTML, icon, toast,
    initLayout, openModal, on, GuestOrders, Cart, showServerOverlay, hideServerOverlay, apiMessage,
  } = window.CK;

  const params = new URLSearchParams(location.search);
  let number = (params.get("number") || "").trim().toUpperCase();
  let user = null;
  let order = null;
  let cafes = [];
  let lookupEmail = params.get("email") || (number ? GuestOrders.emailFor(number) : "");
  let pollTimer = null;
  let tickTimer = null;
  let isNew = params.get("new") === "1";

  function stopTimers() {
    if (pollTimer) { clearInterval(pollTimer); pollTimer = null; }
    if (tickTimer) { clearInterval(tickTimer); tickTimer = null; }
  }

  function showLookup(message) {
    $("#order-loading").hidden = true;
    $("#order-content").hidden = true;
    $("#order-error").hidden = true;
    $("#order-lookup").hidden = false;
    $("#lookup-number").value = number;
    $("#lookup-email").value = lookupEmail;
    if (message) {
      $("#lookup-error").textContent = message;
      $("#lookup-error").classList.add("is-visible");
    }
    renderHistory();
  }

  function showError(message) {
    $("#order-loading").hidden = true;
    $("#order-content").hidden = true;
    $("#order-lookup").hidden = true;
    $("#order-error").hidden = false;
    $("#order-error-text").textContent = message;
  }

  async function fetchOrder() {
    if (!number) throw Object.assign(new Error("no_number"), { needsLookup: true });
    if (user) {
      const data = await window.CKApi.get("/api/orders/" + encodeURIComponent(number));
      return data.order;
    }
    if (!lookupEmail) throw Object.assign(new Error("no_email"), { needsLookup: true });
    const data = await window.CKApi.post("/api/orders/lookup", { number, email: lookupEmail });
    return data.order;
  }

  function statusMarkup() {
    const status = order.status;
    if (status === "processing") {
      return {
        cls: "processing", pill: "В обработке", icon: "cookie",
        title: "Печеньки уже в печи",
        sub: "Мы замесили тесто и поставили партию. Страница обновится сама, когда заказ будет готов.",
        steps: { paid: "done", cooking: "active", ready: "" },
      };
    }
    if (status === "completed") {
      const where = order.fulfillment === "pickup" && order.cafe
        ? "Ждём вас в кафе «" + order.cafe.name + "» до " + order.cafe.closes_at + "."
        : "Курьер передал заказ. Приятного аппетита!";
      return {
        cls: "completed", pill: "Выполнен", icon: "checkCircle",
        title: "Заказ готов!",
        sub: "Печеньки остыли до идеальной температуры. " + where,
        steps: { paid: "done", cooking: "done", ready: "done" },
      };
    }
    return {
      cls: "cancelled", pill: "Отменён", icon: "alert",
      title: "Заказ отменён",
      sub: "Если это ошибка или нужна помощь — напишите в поддержку.",
      steps: { paid: "done", cooking: "", ready: "" },
    };
  }

  function renderStatus() {
    const info = statusMarkup();
    const card = $("#status-card");
    card.className = "status-card " + info.cls;
    $("#status-icon").innerHTML = icon(info.icon);
    $("#status-pill").className = "status-pill";
    $("#status-pill").textContent = info.pill;
    $("#status-title").textContent = info.title;
    $("#status-sub").textContent = info.sub;
    $("#order-number-top").textContent = order.number;
    $("#timeline").querySelectorAll(".tl-step").forEach((step) => {
      step.className = "tl-step " + (info.steps[step.dataset.step] || "");
    });
    $("#countdown").hidden = order.status !== "processing";
    $("#refresh-order").hidden = order.status !== "processing";
    updateCountdown();
  }

  function updateCountdown() {
    if (!order || order.status !== "processing") return;
    const el = $("#countdown");
    el.textContent = "Скоро будет готово";
  }

  function renderMeta() {
    const parts = [
      ["Создан", formatDate(order.created_at, true)],
      ["Оплачен", order.paid_at ? formatDate(order.paid_at, true) : "—"],
    ];
    if (order.completed_at) parts.push(["Выполнен", formatDate(order.completed_at, true)]);
    parts.push(["Номер", order.number]);
    $("#order-meta").innerHTML = parts.map(([label, value]) =>
      "<span>" + escapeHTML(label) + ": <b>" + escapeHTML(value) + "</b></span>").join("");
  }

  function renderItems() {
    $("#order-items").innerHTML = order.items.map((item) =>
      '<div class="summary-item">' +
      '<div class="summary-item-main"><strong>' + escapeHTML(item.name) + "</strong>" +
      '<span class="muted">' + item.quantity + " × " + money(item.unit_price_cents) + "</span></div>" +
      '<span class="summary-item-total">' + money(item.line_total_cents) + "</span></div>").join("");
    $("#sum-subtotal").textContent = money(order.subtotal_cents);
    $("#sum-discount-row").hidden = !order.discount_cents;
    $("#sum-discount").textContent = "−" + money(order.discount_cents);
    $("#sum-promo-label").textContent = order.promo ? "(" + order.promo.code + ")" : "";
    $("#sum-total").textContent = money(order.total_cents);
  }

  function renderDetails() {
    const rows = [];
    rows.push(["Способ получения", escapeHTML(order.fulfillment_label)]);
    if (order.fulfillment === "pickup" && order.cafe) {
      rows.push(["Кафе", escapeHTML(order.cafe.name)]);
      rows.push(["Адрес", escapeHTML(order.cafe.address)]);
      rows.push(["Часы", escapeHTML(order.cafe.opens_at + "–" + order.cafe.closes_at)]);
    } else {
      rows.push(["Адрес доставки", escapeHTML(order.delivery_address || "—")]);
    }
    rows.push(["Получатель", escapeHTML(order.customer.name)]);
    rows.push(["Email", escapeHTML(order.customer.email)]);
    rows.push(["Телефон", escapeHTML(order.customer.phone)]);
    if (order.customer.comment) rows.push(["Комментарий", escapeHTML(order.customer.comment)]);
    if (order.promo) rows.push(["Промокод", escapeHTML(order.promo.code + " · " + (order.promo.label || ""))]);
    rows.push(["Оплата", escapeHTML(order.payment.last4 ? "Карта •••• " + order.payment.last4 : "Карта")]);
    rows.push(["Номер платежа", escapeHTML(order.payment.reference || "—")]);
    $("#details-body").innerHTML =
      '<table class="detail-list">' + rows.map(([k, v]) => "<tr><td>" + k + "</td><td>" + v + "</td></tr>").join("") + "</table>" +
      '<p class="form-note" style="margin-top:12px">Полный номер карты, срок и CVV не сохраняются: сервер получает только последние 4 цифры и факт оплаты.</p>';
  }

  function kitchenCafe() {
    return cafes.find((cafe) => cafe.slug === "sadovaya") || cafes[0] || null;
  }

  function renderCafe() {
    const cafe = order.fulfillment === "pickup" ? order.cafe : kitchenCafe();
    if (!cafe) {
      $("#cafe-body").innerHTML = '<p class="muted">Кафе временно недоступны.</p>';
      $("#cafe-pill").className = "open-pill closed";
      $("#cafe-pill").textContent = "нет данных";
      return;
    }
    $("#cafe-pill").className = "open-pill" + (cafe.is_open ? "" : " closed");
    $("#cafe-pill").textContent = cafe.status_text;
    const note = order.status === "cancelled"
      ? "Заказ отменён. Если нужна помощь — напишите в поддержку."
      : order.status === "completed"
        ? (order.fulfillment === "pickup"
          ? "Заказ выдан. Спасибо, что заглянули в CookieKub!"
          : "Курьер передал заказ. Приятного аппетита!")
        : order.fulfillment === "pickup"
          ? (cafe.is_open ? "Заберите заказ на кассе — назовите номер " + order.number + "." :
            "Кафе закрыто. Заказ будет ждать вас с " + cafe.opens_at + ".")
          : "Это кухня, где готовят ваш заказ. Курьер привезёт его по адресу: " + order.delivery_address + ".";
    $("#cafe-body").innerHTML =
      '<div class="cafe-card"><div><h3>' + escapeHTML(cafe.name) + "</h3>" +
      "<p>" + escapeHTML(cafe.address) + "</p>" +
      "<p>" + escapeHTML(cafe.opens_at + "–" + cafe.closes_at) + (cafe.phone ? " · " + escapeHTML(cafe.phone) : "") + "</p></div></div>" +
      '<p class="muted" style="font-size:.84rem;margin-top:10px">' + escapeHTML(note) + "</p>";
  }

  function renderMap() {
    const wrap = $("#map-wrap");
    wrap.querySelectorAll(".map-marker").forEach((el) => el.remove());
    const list = cafes.length ? cafes : (order.cafe ? [order.cafe] : []);
    const active = order.fulfillment === "pickup" ? order.cafe : kitchenCafe();
    list.forEach((cafe) => {
      const marker = document.createElement("button");
      marker.type = "button";
      marker.className = "map-marker" + (cafe.is_open ? "" : " is-closed") +
        (active && active.id === cafe.id ? " is-active" : "");
      marker.style.left = Number(cafe.map_x) + "%";
      marker.style.top = Number(cafe.map_y) + "%";
      marker.setAttribute("aria-label", cafe.name + ": " + cafe.address + ", " + cafe.status_text);
      marker.title = cafe.name + " — " + cafe.address;
      marker.addEventListener("click", () => {
        $("#map-hint").textContent = cafe.name + " · " + cafe.address + " · " + cafe.opens_at + "–" + cafe.closes_at + " · " + cafe.status_text;
      });
      wrap.appendChild(marker);
    });
  }

  function renderPayment() {
    const p = order.payment || {};
    const badge = $("#payment-badge");
    if (badge) {
      const refunded = order.status === "cancelled";
      badge.textContent = refunded ? "Возврат" : "Оплачено";
      badge.className = "badge " + (refunded ? "red" : "green");
    }
    $("#payment-body").innerHTML =
      "<p><strong>" + escapeHTML(p.last4 ? "Карта •••• " + p.last4 : "Карта") + "</strong></p>" +
      "<p>Платёж: " + escapeHTML(p.reference || "—") + "</p>" +
      "<p>Оплачен: " + escapeHTML(formatDate(p.paid_at, true)) + "</p>";
  }

  function renderHistory() {
    const list = GuestOrders.list();
    const blocks = [$("#guest-history"), $("#guest-history-content-list")];
    const wraps = [$("#guest-history-block"), $("#guest-history-content")];
    if (user) {
      wraps.forEach((el) => { el.hidden = true; });
      return;
    }
    wraps.forEach((el) => { el.hidden = list.length === 0; });
    if (!list.length) return;
    const html = list.map((entry) =>
      '<div class="history-item"><div class="info"><b>' + escapeHTML(entry.number) + "</b>" +
      "<span>" + escapeHTML(formatDate(entry.created_at, true)) + " · " + escapeHTML(entry.email) + "</span></div>" +
      '<a class="btn btn-ghost btn-sm" href="order.html?number=' + encodeURIComponent(entry.number) + '">Открыть</a>' +
      '<button class="icon-btn" type="button" data-forget="' + escapeHTML(entry.number) + '" aria-label="Забыть заказ">' + icon("trash") + "</button></div>").join("");
    blocks.forEach((block) => {
      block.innerHTML = html;
      block.querySelectorAll("[data-forget]").forEach((button) => {
        button.addEventListener("click", () => {
          GuestOrders.forget(button.dataset.forget);
          renderHistory();
        });
      });
    });
  }

  function clearHistory() {
    GuestOrders.list().forEach((entry) => GuestOrders.forget(entry.number));
    renderHistory();
    toast("История на этом устройстве очищена.", "success");
  }

  function maybeShowSuccess() {
    const wasNew = isNew || (() => {
      try {
        const last = JSON.parse(sessionStorage.getItem("cookiekub.lastOrder") || "null");
        return last && last.number === order.number && last.new;
      } catch (_) { return false; }
    })();
    if (!wasNew) return;
    const bannerKey = "cookiekub.bannerClosed." + order.number;
    let bannerClosed = false;
    try { bannerClosed = sessionStorage.getItem(bannerKey) === "1"; } catch (_) { /* ignore */ }
    if (!bannerClosed) {
      $("#success-icon").innerHTML = icon("checkCircle");
      $("#success-banner").classList.add("is-visible");
      $("#success-text").textContent = "Печеньки уже в печи. Номер заказа — " + order.number + ".";
    }
    const modalKey = "cookiekub.successModal." + order.number;
    let shown = false;
    try { shown = sessionStorage.getItem(modalKey) === "1"; } catch (_) { /* ignore */ }
    if (!shown) {
      try { sessionStorage.setItem(modalKey, "1"); } catch (_) { /* ignore */ }
      const body = document.createElement("div");
      body.innerHTML =
        '<div class="success-hero">' + icon("checkCircle") + "</div>" +
        '<p style="font-size:1.05rem"><strong>Спасибо! Заказ ' + escapeHTML(order.number) + " принят.</strong></p>" +
        '<p class="muted">' + escapeHTML(order.fulfillment === "pickup" ? "Самовывоз: " + (order.cafe ? order.cafe.name + ", " + order.cafe.address : "") : "Доставка: " + order.delivery_address) + "</p>" +
        '<div class="summary-row"><span>Позиций</span><span>' + order.items.reduce((n, i) => n + i.quantity, 0) + "</span></div>" +
        '<div class="summary-total"><span>Итого</span><span>' + money(order.total_cents) + "</span></div>" +
        '<p class="form-note">Мы уже готовим ваш заказ. Статус обновится автоматически.</p>';
      const actions = document.createElement("div");
      actions.innerHTML =
        '<button class="btn btn-primary" type="button" data-details>К деталям заказа</button>' +
        '<a class="btn btn-ghost" href="catalog.html">Заказать ещё</a>';
      const modal = openModal({ title: "Заказ оформлен!", body, actions, onClose: () => {} });
      on(actions.querySelector("[data-details]"), "click", () => {
        modal.close();
        $("#details-panel").scrollIntoView({ behavior: "smooth", block: "start" });
      });
    }
    isNew = false;
    try {
      const last = JSON.parse(sessionStorage.getItem("cookiekub.lastOrder") || "null");
      if (last && last.number === order.number) {
        last.new = false;
        sessionStorage.setItem("cookiekub.lastOrder", JSON.stringify(last));
      }
    } catch (_) { /* ignore */ }
    const clean = "order.html?number=" + encodeURIComponent(order.number);
    history.replaceState(null, "", clean);
  }

  function render(nextOrder) {
    order = nextOrder;
    document.title = "Заказ " + order.number + " — CookieKub";
    $("#order-loading").hidden = true;
    $("#order-lookup").hidden = true;
    $("#order-error").hidden = true;
    $("#order-content").hidden = false;
    $("#order-items").replaceChildren();
    renderStatus();
    renderMeta();
    renderItems();
    renderDetails();
    renderCafe();
    renderMap();
    renderPayment();
    renderHistory();
    maybeShowSuccess();
    stopTimers();
    if (order.status === "processing") {
      pollTimer = setInterval(refresh, 5000);
      tickTimer = setInterval(updateCountdown, 1000);
    }
  }

  async function refresh() {
    try {
      const next = await fetchOrder();
      render(next);
      hideServerOverlay();
    } catch (error) {
      stopTimers();
      if (error.isNetwork) {
        showServerOverlay();
        pollTimer = setInterval(refresh, 10000);
      } else if (error.isAuth) {
        window.CKApi.clearToken();
        user = null;
        if (lookupEmail) refresh();
        else showLookup("Сессия истекла. Введите email, чтобы открыть заказ.");
      } else if (error.needsLookup) {
        showLookup("");
      } else {
        showError(apiMessage(error));
      }
    }
  }

  async function submitLookup(event) {
    event.preventDefault();
    const num = $("#lookup-number").value.trim().toUpperCase();
    const email = $("#lookup-email").value.trim();
    const error = $("#lookup-error");
    error.classList.remove("is-visible");
    if (!num) { error.textContent = "Введите номер заказа."; error.classList.add("is-visible"); return; }
    if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email)) { error.textContent = "Введите email, указанный при заказе."; error.classList.add("is-visible"); return; }
    number = num;
    lookupEmail = email;
    const button = event.target.querySelector('button[type="submit"]');
    button.disabled = true;
    try {
      const data = await window.CKApi.post("/api/orders/lookup", { number, email });
      GuestOrders.remember(number, email);
      if (!params.get("number")) history.replaceState(null, "", "order.html?number=" + encodeURIComponent(number));
      render(data.order);
    } catch (err) {
      error.textContent = apiMessage(err);
      error.classList.add("is-visible");
    } finally {
      button.disabled = false;
    }
  }

  async function main() {
    user = await initLayout({ next: "order.html" });
    if (window.CKApi.getToken() && !user) return; // редирект
    $("#lookup-form").addEventListener("submit", submitLookup);
    $("#show-lookup").addEventListener("click", () => showLookup(""));
    $("#refresh-order").addEventListener("click", refresh);
    $("#banner-close").addEventListener("click", () => {
      $("#success-banner").classList.remove("is-visible");
      try { sessionStorage.setItem("cookiekub.bannerClosed." + (order ? order.number : number), "1"); } catch (_) { /* ignore */ }
    });
    $("#clear-history").addEventListener("click", clearHistory);
    $("#clear-history-content").addEventListener("click", clearHistory);
    try {
      const data = await window.CKApi.get("/api/cafes");
      cafes = data.cafes || [];
    } catch (_) { cafes = []; }
    if (!number) { showLookup(""); return; }
    if (!user && !lookupEmail) { showLookup(""); return; }
    await refresh();
  }

  main();
})();
