/* CookieKub: общие утилиты, шапка, подвал, модалки, тосты. */
(function () {
  "use strict";

  const $ = (selector, root) => (root || document).querySelector(selector);
  const $$ = (selector, root) => Array.from((root || document).querySelectorAll(selector));
  const on = (el, event, handler, opts) => el && el.addEventListener(event, handler, opts);

  const ICONS = {
    cart: '<circle cx="9" cy="20" r="1.5"/><circle cx="18" cy="20" r="1.5"/><path d="M3 4h2l2.5 11.5a2 2 0 0 0 2 1.5h8.7a2 2 0 0 0 2-1.5L22 8H6"/>',
    user: '<circle cx="12" cy="8" r="3.6"/><path d="M4.5 21a7.5 7.5 0 0 1 15 0"/>',
    lock: '<rect x="4.5" y="10" width="15" height="10" rx="2.5"/><path d="M8 10V7.5a4 4 0 0 1 8 0V10"/>',
    check: '<path d="m4 12.5 5 5L20 6.5"/>',
    checkCircle: '<circle cx="12" cy="12" r="9"/><path d="m8 12 3 3 5-6"/>',
    arrowRight: '<path d="M4 12h16"/><path d="m14 6 6 6-6 6"/>',
    arrowLeft: '<path d="M20 12H4"/><path d="m10 6-6 6 6 6"/>',
    plus: '<path d="M12 5v14M5 12h14"/>',
    minus: '<path d="M5 12h14"/>',
    trash: '<path d="M4 7h16"/><path d="M9 7V5h6v2"/><path d="M6 7l1 14h10l1-14"/><path d="M10 11v6M14 11v6"/>',
    close: '<path d="M6 6l12 12M18 6 6 18"/>',
    menu: '<path d="M4 7h16M4 12h16M4 17h16"/>',
    search: '<circle cx="11" cy="11" r="6.5"/><path d="m16 16 4.5 4.5"/>',
    pin: '<path d="M12 21s7-6 7-11a7 7 0 1 0-14 0c0 5 7 11 7 11Z"/><circle cx="12" cy="10" r="2.5"/>',
    phone: '<path d="M6 3h3l1.5 4-2 1.5a12 12 0 0 0 6 6l1.5-2 4 1.5v3a2 2 0 0 1-2 2A16 16 0 0 1 4 5a2 2 0 0 1 2-2Z"/>',
    clock: '<circle cx="12" cy="12" r="9"/><path d="M12 7v5l3 2"/>',
    shield: '<path d="M12 3 5 6v6c0 4.5 3 7.5 7 9 4-1.5 7-4.5 7-9V6l-7-3Z"/><path d="m9 12 2 2 4-4"/>',
    mail: '<rect x="3" y="5" width="18" height="14" rx="2"/><path d="m3 7 9 6 9-6"/>',
    card: '<rect x="3" y="5" width="18" height="14" rx="2"/><path d="M3 10h18"/>',
    bag: '<path d="M5 8h14l-1 12H6L5 8Z"/><path d="M8 8V6a4 4 0 0 1 8 0v2"/>',
    truck: '<path d="M3 6h11v10H3z"/><path d="M14 9h4l3 3v4h-7z"/><circle cx="7" cy="18" r="2"/><circle cx="17" cy="18" r="2"/>',
    cookie: '<circle cx="12" cy="12" r="9"/><circle cx="9" cy="10" r="1"/><circle cx="14" cy="9" r="1"/><circle cx="15" cy="14" r="1"/><circle cx="9" cy="15" r="1"/>',
    sparkles: '<path d="M12 3v4M12 17v4M3 12h4M17 12h4M6 6l2.5 2.5M15.5 15.5 18 18M18 6l-2.5 2.5M8.5 15.5 6 18"/>',
    edit: '<path d="M4 20h4L20 8l-4-4L4 16v4Z"/><path d="m14 6 4 4"/>',
    eye: '<path d="M2 12s4-7 10-7 10 7 10 7-4 7-10 7S2 12 2 12Z"/><circle cx="12" cy="12" r="3"/>',
    logout: '<path d="M10 4H5v16h5"/><path d="M15 8l4 4-4 4M19 12H9"/>',
    home: '<path d="m3 11 9-8 9 8"/><path d="M5 10v10h14V10"/>',
    alert: '<path d="M12 3 2.5 20h19L12 3Z"/><path d="M12 9v5M12 17.5v.5"/>',
    info: '<circle cx="12" cy="12" r="9"/><path d="M12 11v5M12 7.5v.5"/>',
    refresh: '<path d="M20 11a8 8 0 1 0-2.3 6.7"/><path d="M20 4v7h-7"/>',
    copy: '<rect x="8" y="8" width="12" height="12" rx="2"/><path d="M16 8V6a2 2 0 0 0-2-2H6a2 2 0 0 0-2 2v8a2 2 0 0 0 2 2h2"/>',
    star: '<path d="m12 3 2.8 5.7 6.2.9-4.5 4.4 1 6.2-5.5-2.9-5.5 2.9 1-6.2L3 9.6l6.2-.9L12 3Z"/>',
  };

  function icon(name, cls) {
    const path = ICONS[name] || ICONS.cookie;
    return '<svg class="icon ' + (cls || "") + '" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">' + path + "</svg>";
  }

  function money(cents) {
    const value = Number(cents) || 0;
    return (value / 100).toLocaleString("ru-RU", {
      style: "currency", currency: "RUB", minimumFractionDigits: value % 100 === 0 ? 0 : 2, maximumFractionDigits: 2,
    });
  }

  function formatDate(value, withTime) {
    if (!value) return "—";
    const date = new Date(value);
    if (Number.isNaN(date.getTime())) return "—";
    return date.toLocaleString("ru-RU", withTime
      ? { day: "2-digit", month: "long", hour: "2-digit", minute: "2-digit" }
      : { day: "2-digit", month: "long", year: "numeric" });
  }

  function escapeHTML(value) {
    return String(value == null ? "" : value)
      .replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;").replace(/'/g, "&#39;");
  }

  function initials(name) {
    return String(name || "?").trim().split(/\s+/).slice(0, 2).map((p) => p[0] || "").join("").toUpperCase();
  }

  function statusInfo(status) {
    const map = {
      processing: { label: "В обработке", cls: "amber" },
      completed: { label: "Выполнен", cls: "green" },
      cancelled: { label: "Отменён", cls: "red" },
    };
    return map[status] || { label: status || "—", cls: "" };
  }

  function ticketCategory(value) {
    const map = { bug: "Баг", question: "Вопрос", other: "Другое" };
    return map[value] || value || "—";
  }

  function ticketStatus(value) {
    const map = { open: "Открыт", answered: "Отвечен", closed: "Закрыт" };
    return map[value] || value || "—";
  }

  function toast(message, type) {
    let wrap = $(".toast-wrap");
    if (!wrap) {
      wrap = document.createElement("div");
      wrap.className = "toast-wrap";
      wrap.setAttribute("role", "status");
      wrap.setAttribute("aria-live", "polite");
      document.body.appendChild(wrap);
    }
    const el = document.createElement("div");
    el.className = "toast " + (type || "");
    el.innerHTML = icon(type === "error" ? "alert" : type === "success" ? "checkCircle" : "info");
    const text = document.createElement("div");
    text.textContent = message;
    el.appendChild(text);
    wrap.appendChild(el);
    setTimeout(() => {
      el.style.opacity = "0";
      el.style.transform = "translateY(8px)";
      setTimeout(() => el.remove(), 220);
    }, 4200);
  }

  function setBusy(button, busy, label) {
    if (!button) return;
    if (busy) {
      button.dataset.original = button.innerHTML;
      button.disabled = true;
      button.innerHTML = '<span class="spinner" aria-hidden="true"></span><span>' + escapeHTML(label || "Секунду…") + "</span>";
    } else {
      if (button.dataset.original) button.innerHTML = button.dataset.original;
      button.disabled = false;
      delete button.dataset.original;
    }
  }

  function setFormError(el, message) {
    if (!el) return;
    el.textContent = message || "";
    el.classList.toggle("is-visible", Boolean(message));
  }

  function debounce(fn, delay) {
    let timer = null;
    return function () {
      const args = arguments;
      clearTimeout(timer);
      timer = setTimeout(() => fn.apply(this, args), delay == null ? 260 : delay);
    };
  }

  /* ---------- Модалки ---------- */
  function openModal(options) {
    const opts = options || {};
    const backdrop = document.createElement("div");
    backdrop.className = "modal-backdrop";
    const modal = document.createElement("div");
    modal.className = "modal";
    modal.setAttribute("role", "dialog");
    modal.setAttribute("aria-modal", "true");
    modal.setAttribute("aria-labelledby", "modal-title");
    const head = document.createElement("div");
    head.className = "modal-head";
    const title = document.createElement("h2");
    title.id = "modal-title";
    title.textContent = opts.title || "";
    const close = document.createElement("button");
    close.className = "modal-close";
    close.type = "button";
    close.setAttribute("aria-label", "Закрыть");
    close.innerHTML = icon("close");
    head.appendChild(title);
    head.appendChild(close);
    const body = document.createElement("div");
    body.className = "modal-body";
    if (opts.body instanceof Node) body.appendChild(opts.body);
    else body.innerHTML = opts.body || "";
    modal.appendChild(head);
    modal.appendChild(body);
    if (opts.actions) {
      const actions = document.createElement("div");
      actions.className = "modal-actions";
      if (opts.actions instanceof Node) actions.appendChild(opts.actions);
      else actions.innerHTML = opts.actions;
      modal.appendChild(actions);
    }
    backdrop.appendChild(modal);
    document.body.appendChild(backdrop);
    document.body.style.overflow = "hidden";
    const closeModal = () => {
      backdrop.classList.remove("is-open");
      document.body.style.overflow = "";
      setTimeout(() => backdrop.remove(), 220);
      if (typeof opts.onClose === "function") opts.onClose();
    };
    on(close, "click", closeModal);
    on(backdrop, "click", (event) => { if (event.target === backdrop) closeModal(); });
    const esc = (event) => {
      if (event.key === "Escape") { closeModal(); document.removeEventListener("keydown", esc); }
    };
    document.addEventListener("keydown", esc);
    requestAnimationFrame(() => backdrop.classList.add("is-open"));
    setTimeout(() => close.focus(), 60);
    return { element: backdrop, close: closeModal };
  }

  function confirmDialog(options) {
    const opts = options || {};
    return new Promise((resolve) => {
      const wrap = document.createElement("div");
      const p = document.createElement("p");
      p.textContent = opts.message || "Вы уверены?";
      p.style.margin = "0";
      wrap.appendChild(p);
      const actions = document.createElement("div");
      const cancel = document.createElement("button");
      cancel.type = "button";
      cancel.className = "btn btn-ghost";
      cancel.textContent = opts.cancelText || "Отмена";
      const ok = document.createElement("button");
      ok.type = "button";
      ok.className = "btn " + (opts.danger ? "btn-danger" : "btn-primary");
      ok.textContent = opts.confirmText || "Подтвердить";
      actions.appendChild(cancel);
      actions.appendChild(ok);
      const modal = openModal({ title: opts.title || "Подтверждение", body: wrap, actions, onClose: () => resolve(false) });
      on(cancel, "click", () => { modal.close(); resolve(false); });
      on(ok, "click", () => { modal.close(); resolve(true); });
    });
  }

  /* ---------- Корзина (localStorage) ---------- */
  const CART_KEY = "cookiekub.cart.v1";
  const Cart = {
    read() {
      try {
        const raw = JSON.parse(localStorage.getItem(CART_KEY) || "[]");
        return Array.isArray(raw) ? raw.filter((item) => item && item.product_id && item.quantity > 0) : [];
      } catch (_) { return []; }
    },
    write(items) {
      localStorage.setItem(CART_KEY, JSON.stringify(items));
      document.dispatchEvent(new CustomEvent("cart:change", { detail: { items } }));
      updateCartCount();
    },
    add(product, quantity) {
      const qty = Math.max(1, Number(quantity) || 1);
      const items = this.read();
      const existing = items.find((item) => Number(item.product_id) === Number(product.id));
      if (existing) {
        existing.quantity = Math.min(99, Number(existing.stock_qty || 99), existing.quantity + qty);
        existing.price_cents = product.price_cents;
        existing.name = product.name;
      } else {
        items.push({
          product_id: product.id, slug: product.slug, name: product.name,
          price_cents: product.price_cents, image_url: product.image_url,
          stock_qty: product.stock_qty, quantity: Math.min(qty, Number(product.stock_qty || 99)),
        });
      }
      this.write(items);
      return items;
    },
    setQuantity(productId, quantity) {
      const items = this.read();
      const item = items.find((x) => Number(x.product_id) === Number(productId));
      if (!item) return items;
      if (quantity <= 0) return this.remove(productId);
      item.quantity = Math.min(99, Number(item.stock_qty || 99), Number(quantity) || 1);
      this.write(items);
      return items;
    },
    remove(productId) {
      const items = this.read().filter((x) => Number(x.product_id) !== Number(productId));
      this.write(items);
      return items;
    },
    clear() { this.write([]); },
    count() { return this.read().reduce((sum, item) => sum + Number(item.quantity || 0), 0); },
    subtotal() { return this.read().reduce((sum, item) => sum + Number(item.price_cents) * Number(item.quantity), 0); },
    detailed() { return this.read().map((item) => Object.assign({}, item, { line_total_cents: Number(item.price_cents) * Number(item.quantity) })); },
  };

  function updateCartCount() {
    const count = Cart.count();
    $$("[data-cart-count]").forEach((el) => {
      el.textContent = String(count);
      el.hidden = count === 0;
    });
  }

  /* ---------- Гостевые заказы ---------- */
  const GUEST_KEY = "cookiekub.guestOrders.v1";
  const GuestOrders = {
    list() {
      try {
        const raw = JSON.parse(localStorage.getItem(GUEST_KEY) || "[]");
        return Array.isArray(raw) ? raw : [];
      } catch (_) { return []; }
    },
    remember(number, email) {
      const list = this.list().filter((item) => item.number !== number);
      list.unshift({ number, email, created_at: new Date().toISOString() });
      localStorage.setItem(GUEST_KEY, JSON.stringify(list.slice(0, 20)));
    },
    emailFor(number) {
      const found = this.list().find((item) => item.number === number);
      return found ? found.email : "";
    },
    forget(number) {
      localStorage.setItem(GUEST_KEY, JSON.stringify(this.list().filter((item) => item.number !== number)));
    },
  };

  /* ---------- Сеть / оверлей ---------- */
  let overlay = null;
  function showServerOverlay() {
    if (!overlay) {
      overlay = document.createElement("div");
      overlay.className = "server-overlay";
      overlay.innerHTML =
        '<div class="server-card">' +
        '<div class="oven" aria-hidden="true">🍪</div>' +
        "<h2>Печка остыла — сервер просыпается</h2>" +
        "<p>Бесплатный сервер засыпает после простоя. Первый запуск занимает до минуты. Мы уже будим его.</p>" +
        '<div class="cluster" style="justify-content:center">' +
        '<button type="button" class="btn btn-primary" data-retry>Повторить</button>' +
        '<a class="btn btn-ghost" href="index.html">На главную</a>' +
        "</div></div>";
      document.body.appendChild(overlay);
      on(overlay.querySelector("[data-retry]"), "click", () => {
        overlay.hidden = true;
        document.dispatchEvent(new CustomEvent("server:retry"));
      });
    }
    overlay.hidden = false;
  }
  function hideServerOverlay() { if (overlay) overlay.hidden = true; }

  function apiMessage(error) {
    if (!error) return "Что-то пошло не так.";
    if (error.status === 0) return "Сервер не отвечает. Проверьте подключение и попробуйте ещё раз.";
    if (error.status === 429) {
      const retry = error.details && error.details.retry_after;
      return "Слишком много попыток." + (retry ? " Попробуйте через " + retry + " сек." : " Подождите немного.");
    }
    return error.message || "Не получилось выполнить запрос.";
  }

  /* ---------- Шапка / подвал ---------- */
  function navItems(user) {
    const page = document.body.dataset.page || "";
    const items = [
      ["home", "index.html", "Главная"],
      ["catalog", "catalog.html", "Каталог"],
      ["support", "support.html", "Поддержка"],
    ];
    if (user && user.role === "admin") items.push(["admin", "admin.html", "Админ-панель"]);
    return items.map(([key, href, label]) =>
      '<a href="' + href + '"' + (page === key ? ' aria-current="page"' : "") + (key === "admin" ? ' class="nav-admin"' : "") + ">" + label + "</a>"
    ).join("");
  }

  function authSlot(user) {
    if (!user) {
      return '<a class="btn btn-ghost btn-sm" href="login.html" aria-label="Войти"><span class="long">Войти</span><span class="short">Вход</span></a>' +
        '<a class="btn btn-primary btn-sm" href="register.html" aria-label="Регистрация"><span class="long">Регистрация</span><span class="short">Создать</span></a>';
    }
    return '<a class="user-chip" href="account.html" title="Аккаунт KubanoID">' +
      '<span class="avatar">' + escapeHTML(initials(user.full_name)) + "</span>" +
      '<span class="name">' + escapeHTML(user.full_name || "Мой KubanoID") + "</span></a>" +
      '<button type="button" class="btn btn-ghost btn-sm" data-logout title="Выйти">' + icon("logout") + "</button>";
  }

  function renderHeader(user) {
    const host = $("#site-header");
    if (!host) return;
    host.className = "site-header";
    host.innerHTML =
      '<div class="container header-inner">' +
      '<a class="brand" href="index.html"><img src="assets/logo.svg" alt=""><span>CookieKub<small>Пекарня-симулятор</small></span></a>' +
      '<nav class="main-nav" id="main-nav" aria-label="Основная навигация">' + navItems(user) + "</nav>" +
      '<div class="header-actions">' +
      '<a class="cart-link" href="cart.html" aria-label="Корзина">' + icon("cart") + '<span class="label">Корзина</span><span class="cart-count" data-cart-count hidden>0</span></a>' +
      '<div class="auth-slot">' + authSlot(user) + "</div>" +
      '<button type="button" class="nav-toggle" aria-label="Меню" aria-expanded="false" aria-controls="main-nav"><span></span><span></span><span></span></button>' +
      "</div></div>";
    updateCartCount();
    const toggle = $(".nav-toggle", host);
    const nav = $(".main-nav", host);
    on(toggle, "click", () => {
      const open = nav.classList.toggle("is-open");
      toggle.setAttribute("aria-expanded", String(open));
    });
    $$(".main-nav a", host).forEach((link) => on(link, "click", () => {
      nav.classList.remove("is-open");
      toggle.setAttribute("aria-expanded", "false");
    }));
    on($("[data-logout]", host), "click", async () => {
      try { await window.CKApi.post("/api/auth/logout", {}); } catch (_) { /* токен всё равно чистим */ }
      window.CKApi.clearToken();
      toast("Вы вышли из KubanoID.", "success");
      setTimeout(() => { location.href = "index.html"; }, 350);
    });
  }

  function renderFooter() {
    const host = $("#site-footer");
    if (!host) return;
    host.className = "site-footer";
    host.innerHTML =
      '<div class="container"><div class="footer-grid">' +
      '<div class="footer-brand"><a class="brand" href="index.html"><img src="assets/logo.svg" alt=""><span>CookieKub<small>Пекарня-симулятор</small></span></a>' +
      "<p>Печеньки, которые не нужно печь. Магазин-симулятор: заказы и оплата вымышленные, но всё работает по-настоящему.</p></div>" +
      '<div><h4>Магазин</h4><a href="catalog.html">Каталог</a><a href="cart.html">Корзина</a><a href="account.html">Мои заказы</a></div>' +
      '<div><h4>Помощь</h4><a href="support.html">Поддержка</a><a href="support.html#faq">Вопросы и ответы</a><a href="privacy.html">Персональные данные</a></div>' +
      '<div><h4>Связь</h4><a href="mailto:support@cookiekub.ru">support@cookiekub.ru</a><a href="support.html">Форма обращения</a><span class="small muted">Ежедневно 9:00–21:00 МСК</span></div>' +
      "</div><div class=\"footer-bottom\"><span>© <span data-year></span> CookieKub. Учебный проект, не настоящий магазин.</span>" +
      '<span class="footer-badge">' + icon("shield") + " KubanoID · данные под защитой</span></div></div>";
    $$("[data-year]").forEach((el) => { el.textContent = String(new Date().getFullYear()); });
  }

  /* ---------- Инициализация ---------- */
  async function initLayout(options) {
    const opts = options || {};
    document.body.dataset.page = document.body.dataset.page || "";
    let user = null;
    if (window.CKApi.getToken()) {
      try {
        const data = await window.CKApi.get("/api/auth/me");
        user = data.user;
        window.CK_USER = user;
      } catch (error) {
        if (error.isAuth) window.CKApi.clearToken();
        else if (error.isNetwork) showServerOverlay();
      }
    }
    if (opts.requireAuth && !user) {
      const next = encodeURIComponent(opts.next || location.pathname.split("/").pop() || "account.html");
      location.replace("403.html?reason=auth&next=" + next);
      return null;
    }
    if (opts.admin && (!user || user.role !== "admin")) {
      const next = encodeURIComponent(opts.next || "admin.html");
      location.replace("403.html?reason=" + (user ? "admin" : "auth") + "&next=" + next);
      return null;
    }
    renderHeader(user);
    renderFooter();
    updateCartCount();
    document.addEventListener("cart:change", updateCartCount);
    window.addEventListener("storage", (event) => {
      if (event.key === "cookiekub.cart.v1") updateCartCount();
    });
    return user;
  }

  window.CK = {
    $, $$, on, icon, money, formatDate, escapeHTML, initials, statusInfo,
    ticketCategory, ticketStatus,
    toast, setBusy, setFormError, debounce, openModal, confirmDialog,
    Cart, GuestOrders, updateCartCount, showServerOverlay, hideServerOverlay,
    apiMessage, initLayout, renderHeader, renderFooter,
  };
})();
