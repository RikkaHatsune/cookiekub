/* CookieKub — админ-панель. Все данные приходят из /api/admin/*. */
(function () {
  "use strict";

  const CK = window.CK;
  const API = window.CKApi;
  const { $, $$, on, money, formatDate, escapeHTML, statusInfo, toast, confirmDialog, apiMessage } = CK;

  const TABS = ["dashboard", "products", "orders", "promos", "users", "tickets", "audit"];
  const TITLES = {
    dashboard: "Обзор",
    products: "Товары",
    orders: "Заказы",
    promos: "Промокоды",
    users: "Пользователи",
    tickets: "Поддержка",
    audit: "Журнал аудита",
  };
  const CATEGORY_LABELS = {
    classic: "Классика",
    chocolate: "Шоколадные",
    fruit: "Фруктовые",
    nuts: "Ореховые",
    vegan: "Веган",
    gift: "Подарочные",
  };

  let me = null;
  let currentTab = null;
  let busy = false;

  const esc = (value) => escapeHTML(value == null ? "" : String(value));

  function field(label, control, hint, extraClass) {
    return (
      '<div class="field ' + esc(extraClass || "") + '"><label>' + label + "</label>" + control +
      (hint ? '<div class="hint">' + hint + "</div>" : "") +
      "</div>"
    );
  }

  function input(name, value, type, attrs) {
    return (
      '<input class="input" name="' + name + '" type="' + (type || "text") + '" value="' +
      esc(value == null ? "" : value) + '" ' + (attrs || "") + ">"
    );
  }

  function select(name, value, options) {
    return (
      '<select class="select" name="' + name + '">' +
      Object.entries(options)
        .map(([key, label]) => '<option value="' + esc(key) + '"' + (String(value) === String(key) ? " selected" : "") + ">" + esc(label) + "</option>")
        .join("") +
      "</select>"
    );
  }

  function badge(status) {
    const ticketMap = {
      open: { label: "Открыт", cls: "amber" },
      answered: { label: "Отвечен", cls: "green" },
      closed: { label: "Закрыт", cls: "" },
    };
    const info = ticketMap[status] || statusInfo(status);
    return '<span class="badge ' + esc(info.cls || "") + '">' + esc(info.label || status) + "</span>";
  }

  function setLoading(on) {
    const loading = $("#admin-loading");
    if (loading) loading.hidden = !on;
  }

  function setError(message) {
    const box = $("#admin-error");
    if (!box) return;
    box.textContent = message || "";
    box.hidden = !message;
  }

  function handleError(error) {
    if (error && error.isNetwork) return;
    if (error && error.isAuth) {
      API.clearToken();
      location.replace("403.html?reason=auth&next=admin.html");
      return;
    }
    if (error && error.isForbidden) {
      location.replace("403.html?reason=admin&next=admin.html");
      return;
    }
    toast(apiMessage(error), "error");
  }

  async function load(tab) {
    if (busy) return;
    busy = true;
    setError("");
    setLoading(true);
    try {
      if (tab === "dashboard") await loadDashboard();
      else if (tab === "products") await loadProducts();
      else if (tab === "orders") await loadOrders();
      else if (tab === "promos") await loadPromos();
      else if (tab === "users") await loadUsers();
      else if (tab === "tickets") await loadTickets();
      else if (tab === "audit") await loadAudit();
    } catch (error) {
      handleError(error);
    } finally {
      setLoading(false);
      busy = false;
      const refresh = $("#admin-refresh");
      if (refresh) refresh.disabled = false;
    }
  }

  function switchTab(tab, updateHash) {
    if (!TABS.includes(tab)) tab = "dashboard";
    currentTab = tab;
    $$(".admin-tab").forEach((section) => { section.hidden = section.id !== "tab-" + tab; });
    $$("#admin-nav a").forEach((link) => {
      const active = link.dataset.tab === tab;
      link.classList.toggle("is-active", active);
      if (active) link.setAttribute("aria-current", "page");
      else link.removeAttribute("aria-current");
    });
    const title = $("#admin-title");
    if (title) title.textContent = TITLES[tab] || "Админ-панель";
    if (updateHash !== false) history.replaceState(null, "", "#" + tab);
    load(tab);
  }

  /* ---------- Dashboard ---------- */
  async function loadDashboard() {
    const data = await API.get("/api/admin/stats");
    const stats = data.stats || {};
    const cards = [
      ["Клиенты", stats.users, "user"],
      ["Товары", stats.products, "cookie"],
      ["Заказы", stats.orders_total, "bag"],
      ["Выручка", money(stats.revenue_cents || 0), "card"],
      ["В обработке", stats.orders_processing, "clock"],
      ["Выполнено", stats.orders_completed, "checkCircle"],
      ["Открытых тикетов", stats.tickets_open, "mail"],
    ];
    $("#stats-grid").innerHTML = cards
      .map(
        ([label, value, icon]) =>
          '<div class="stat"><span>' + esc(label) + '</span><b>' + esc(value) + "</b></div>"
      )
      .join("");

    const rows = data.recent_orders || [];
    $("#recent-orders").innerHTML = rows.length
      ? rows
          .map(
            (order) =>
              "<tr><td><b>" + esc(order.number) + "</b></td><td>" + esc(order.customer?.name || "Гость") +
              '<div class="muted small">' + esc(order.customer?.email || "") + "</div></td><td>" +
              money(order.total_cents) + "</td><td>" + badge(order.status) + "</td><td>" +
              esc(formatDate(order.created_at)) + "</td></tr>"
          )
          .join("")
      : '<tr><td colspan="5" class="empty">Заказов пока нет.</td></tr>';
  }

  /* ---------- Products ---------- */
  async function loadProducts() {
    const search = ($("#products-search") || {}).value || "";
    const data = await API.get("/api/admin/products" + (search ? "?search=" + encodeURIComponent(search) : ""));
    const products = data.products || [];
    const body = $("#products-body");
    const empty = $("#products-empty");
    if (empty) empty.hidden = products.length > 0;
    if (!products.length) { body.innerHTML = ""; return; }
    body.innerHTML = products
      .map(
        (product) =>
          "<tr><td>" +
          '<img src="' + esc(product.image_url) + '" alt="" style="width:40px;height:40px;border-radius:10px;object-fit:cover" loading="lazy">' +
          "</td><td><b>" + esc(product.name) + '</b><div class="muted small">' + esc(product.slug) + "</div></td><td>" +
          esc(CATEGORY_LABELS[product.category] || product.category) + "</td><td>" + money(product.price_cents) +
          "</td><td>" + esc(product.stock_qty) + "</td><td>" +
          (product.is_active ? '<span class="badge green">да</span>' : '<span class="badge red">архив</span>') +
          '</td><td><div class="actions"><button class="btn btn-ghost btn-sm" data-product-edit="' + product.id + '">Изменить</button>' +
          '<button class="btn btn-ghost btn-sm" data-product-archive="' + product.id + '">В архив</button></div></td></tr>'
      )
      .join("");
    $$("[data-product-edit]", body).forEach((button) =>
      on(button, "click", () => openProductForm(products.find((p) => p.id === Number(button.dataset.productEdit))))
    );
    $$("[data-product-archive]", body).forEach((button) =>
      on(button, "click", () => archiveProduct(Number(button.dataset.productArchive)))
    );
  }

  function openProductForm(product) {
    const isNew = !product;
    const p = product || {
      name: "", slug: "", short_description: "", description: "", price_cents: 14900,
      image_url: "assets/cookies/klassicheskiy-kubik.svg", category: "classic", stock_qty: 10,
      is_active: true, sort_order: 0,
    };
    const form = document.createElement("form");
    form.className = "form-grid";
    form.innerHTML =
      field("Название", input("name", p.name, "text", "required maxlength=120")) +
      field("Slug", input("slug", p.slug, "text", "maxlength=80 placeholder=avto"), "Оставьте пустым — сгенерируется из названия") +
      field("Цена, ₽", input("price", (p.price_cents / 100).toFixed(2), "text", "inputmode=decimal required")) +
      field("Остаток, шт.", input("stock_qty", p.stock_qty, "number", "min=0 max=100000")) +
      field("Категория", select("category", p.category, CATEGORY_LABELS)) +
      field("Сортировка", input("sort_order", p.sort_order, "number", "min=-1000 max=1000")) +
      field("Короткое описание", input("short_description", p.short_description, "text", "maxlength=200"), "", "full") +
      '<div class="field full"><label>Описание</label><textarea class="textarea" name="description" maxlength="3000">' + esc(p.description) + "</textarea></div>" +
      field("Картинка (URL или assets/...)", input("image_url", p.image_url, "text", "maxlength=500"), "", "full") +
      '<div class="field full"><label class="checkbox"><input type="checkbox" name="is_active"' + (p.is_active ? " checked" : "") + "> Показывать в каталоге</label></div>";

    const modal = CK.openModal({
      title: isNew ? "Новый товар" : "Товар: " + p.name,
      body: form,
      actions: '<button class="btn btn-ghost" data-cancel>Отмена</button><button class="btn btn-primary" id="modal-save" type="button">Сохранить</button>',
    });
    on(form.querySelector("[data-cancel]") || modal.element.querySelector("[data-cancel]"), "click", modal.close);
    on(modal.element.querySelector("#modal-save"), "click", async () => {
      const save = modal.element.querySelector("#modal-save");
      save.disabled = true;
      try {
        const fd = new FormData(form);
        const price = Number(String(fd.get("price")).replace(",", "."));
        if (!Number.isFinite(price) || price <= 0) throw new Error("Укажите цену больше нуля");
        const payload = {
          name: String(fd.get("name") || "").trim(),
          slug: String(fd.get("slug") || "").trim(),
          short_description: String(fd.get("short_description") || "").trim(),
          description: String(fd.get("description") || "").trim(),
          price_cents: Math.round(price * 100),
          image_url: String(fd.get("image_url") || "").trim(),
          category: String(fd.get("category") || "classic"),
          stock_qty: Number(fd.get("stock_qty") || 0),
          sort_order: Number(fd.get("sort_order") || 0),
          is_active: Boolean(fd.get("is_active")),
        };
        if (isNew) await API.post("/api/admin/products", payload);
        else await API.patch("/api/admin/products/" + p.id, payload);
        modal.close();
        toast(isNew ? "Товар добавлен" : "Товар обновлён", "success");
        loadProducts();
      } catch (error) {
        handleError(error);
        if (error && !error.status) toast(error.message, "error");
      } finally {
        save.disabled = false;
      }
    });
  }

  async function archiveProduct(id) {
    const ok = await confirmDialog({
      title: "Убрать товар?",
      message: "Товар останется в истории заказов, но исчезнет из каталога.",
      confirmText: "В архив",
    });
    if (!ok) return;
    try {
      await API.del("/api/admin/products/" + id);
      toast("Товар отправлен в архив", "success");
      loadProducts();
    } catch (error) { handleError(error); }
  }

  /* ---------- Orders ---------- */
  async function loadOrders() {
    const status = ($("#orders-status") || {}).value || "";
    const search = ($("#orders-search") || {}).value || "";
    const query = new URLSearchParams();
    if (status) query.set("status", status);
    if (search) query.set("search", search);
    const data = await API.get("/api/admin/orders" + (query.toString() ? "?" + query.toString() : ""));
    const orders = data.orders || [];
    $("#orders-count").textContent = orders.length + " шт.";
    const body = $("#orders-body");
    const empty = $("#orders-empty");
    if (empty) empty.hidden = orders.length > 0;
    if (!orders.length) { body.innerHTML = ""; return; }
    body.innerHTML = orders
      .map((order) => {
        const customer = order.customer || {};
        const actions = [];
        if (order.status === "processing") actions.push('<button class="btn btn-ghost btn-sm" data-complete="' + order.id + '">Завершить</button>');
        if (order.status !== "cancelled") actions.push('<button class="btn btn-ghost btn-sm" data-cancel-order="' + order.id + '">Отменить</button>');
        actions.push('<a class="btn btn-ghost btn-sm" href="order.html?number=' + encodeURIComponent(order.number) + '">Открыть</a>');
        return (
          "<tr><td><b>" + esc(order.number) + "</b></td><td>" + esc(customer.name || "Гость") +
          '<div class="muted small">' + esc(customer.email || "") + "</div></td><td>" +
          esc(order.fulfillment_label || order.fulfillment) + "</td><td>" + money(order.total_cents) +
          "</td><td>" + badge(order.status) + "</td><td>" + esc(formatDate(order.created_at)) +
          '</td><td><div class="actions">' + actions.join("") + "</div></td></tr>"
        );
      })
      .join("");
    $$("[data-complete]", body).forEach((button) =>
      on(button, "click", () => changeOrder(Number(button.dataset.complete), "completed"))
    );
    $$("[data-cancel-order]", body).forEach((button) =>
      on(button, "click", () => changeOrder(Number(button.dataset.cancelOrder), "cancelled"))
    );
  }

  async function changeOrder(id, status) {
    if (status === "cancelled") {
      const ok = await confirmDialog({
        title: "Отменить заказ?",
        message: "Остатки товаров вернутся на склад, а промокод — в лимит использований.",
        confirmText: "Отменить заказ",
        danger: true,
      });
      if (!ok) return;
    }
    try {
      await API.patch("/api/admin/orders/" + id + "/status", { status });
      toast(status === "completed" ? "Заказ выполнен" : "Заказ отменён", "success");
      loadOrders();
    } catch (error) { handleError(error); }
  }

  /* ---------- Promos ---------- */
  async function loadPromos() {
    const data = await API.get("/api/admin/promos");
    const promos = data.promos || [];
    const body = $("#promos-body");
    if (!promos.length) { body.innerHTML = '<tr><td colspan="7" class="empty">Промокодов нет.</td></tr>'; return; }
    body.innerHTML = promos
      .map((promo) => {
        const discount = promo.discount_type === "percent" ? "−" + promo.percent_value + "%" : "−" + money(promo.amount_cents);
        const period = [promo.starts_at ? formatDate(promo.starts_at) : "сейчас", promo.ends_at ? formatDate(promo.ends_at) : "бессрочно"].join(" — ");
        return (
          "<tr><td><b>" + esc(promo.code) + "</b></td><td>" + esc(discount) + "</td><td>" +
          money(promo.min_order_cents || 0) + "</td><td>" + esc(promo.used_count) +
          (promo.max_uses ? " / " + esc(promo.max_uses) : "") + "</td><td>" + esc(period) + "</td><td>" +
          (promo.is_active ? '<span class="badge green">да</span>' : '<span class="badge red">нет</span>') +
          '</td><td><div class="actions"><button class="btn btn-ghost btn-sm" data-promo-edit="' + promo.id + '">Изменить</button>' +
          '<button class="btn btn-ghost btn-sm" data-promo-archive="' + promo.id + '">Отключить</button></div></td></tr>'
        );
      })
      .join("");
    $$("[data-promo-edit]", body).forEach((button) =>
      on(button, "click", () => openPromoForm(promos.find((p) => p.id === Number(button.dataset.promoEdit))))
    );
    $$("[data-promo-archive]", body).forEach((button) =>
      on(button, "click", () => archivePromo(Number(button.dataset.promoArchive)))
    );
  }

  function toLocalInput(iso) {
    if (!iso) return "";
    const date = new Date(iso);
    if (Number.isNaN(date.getTime())) return "";
    const pad = (n) => String(n).padStart(2, "0");
    return date.getFullYear() + "-" + pad(date.getMonth() + 1) + "-" + pad(date.getDate()) + "T" + pad(date.getHours()) + ":" + pad(date.getMinutes());
  }

  function openPromoForm(promo) {
    const isNew = !promo;
    const p = promo || {
      code: "", discount_type: "percent", percent_value: 10, amount_cents: 50000,
      min_order_cents: 0, max_uses: null, starts_at: null, ends_at: null, is_active: true,
    };
    const form = document.createElement("form");
    form.className = "form-grid";
    form.innerHTML =
      field("Код", input("code", p.code, "text", "required maxlength=40 placeholder=COOKIE10")) +
      field("Тип скидки", select("discount_type", p.discount_type, { percent: "Процент", fixed: "Фиксированная сумма" })) +
      field("Процент", input("percent", p.percent_value == null ? "" : p.percent_value, "number", "min=1 max=100"), "", "percent-field") +
      field("Сумма, ₽", input("amount", p.amount_cents == null ? "" : (p.amount_cents / 100).toFixed(2), "text", "inputmode=decimal"), "", "fixed-field") +
      field("Мин. сумма, ₽", input("min_order", (p.min_order_cents || 0) / 100, "text", "inputmode=decimal")) +
      field("Лимит использований", input("max_uses", p.max_uses == null ? "" : p.max_uses, "number", "min=1"), "Пусто — без лимита") +
      field("Начало", input("starts_at", toLocalInput(p.starts_at), "datetime-local")) +
      field("Окончание", input("ends_at", toLocalInput(p.ends_at), "datetime-local")) +
      '<div class="field full"><label class="checkbox"><input type="checkbox" name="is_active"' + (p.is_active ? " checked" : "") + "> Промокод активен</label></div>";

    const modal = CK.openModal({
      title: isNew ? "Новый промокод" : "Промокод " + p.code,
      body: form,
      actions: '<button class="btn btn-ghost" data-cancel>Отмена</button><button class="btn btn-primary" id="modal-save" type="button">Сохранить</button>',
    });
    const syncType = () => {
      const type = form.querySelector('[name="discount_type"]').value;
      form.querySelector(".percent-field").hidden = type !== "percent";
      form.querySelector(".fixed-field").hidden = type !== "fixed";
    };
    on(form.querySelector('[name="discount_type"]'), "change", syncType);
    syncType();
    on(modal.element.querySelector("[data-cancel]"), "click", modal.close);
    on(modal.element.querySelector("#modal-save"), "click", async () => {
      const save = modal.element.querySelector("#modal-save");
      save.disabled = true;
      try {
        const fd = new FormData(form);
        const type = String(fd.get("discount_type"));
        const min = Number(String(fd.get("min_order") || "0").replace(",", "."));
        const amount = Number(String(fd.get("amount") || "0").replace(",", "."));
        const maxUses = String(fd.get("max_uses") || "").trim();
        const payload = {
          code: String(fd.get("code") || "").trim(),
          discount_type: type,
          percent_value: type === "percent" ? Number(fd.get("percent")) : null,
          amount_cents: type === "fixed" ? Math.round(amount * 100) : null,
          min_order_cents: Number.isFinite(min) ? Math.round(min * 100) : 0,
          max_uses: maxUses ? Number(maxUses) : null,
          starts_at: fd.get("starts_at") ? new Date(String(fd.get("starts_at"))).toISOString() : null,
          ends_at: fd.get("ends_at") ? new Date(String(fd.get("ends_at"))).toISOString() : null,
          is_active: Boolean(fd.get("is_active")),
        };
        if (isNew) await API.post("/api/admin/promos", payload);
        else await API.patch("/api/admin/promos/" + p.id, payload);
        modal.close();
        toast(isNew ? "Промокод создан" : "Промокод обновлён", "success");
        loadPromos();
      } catch (error) {
        handleError(error);
      } finally {
        save.disabled = false;
      }
    });
  }

  async function archivePromo(id) {
    const ok = await confirmDialog({
      title: "Отключить промокод?",
      message: "Он перестанет применяться в корзине, история использований сохранится.",
      confirmText: "Отключить",
    });
    if (!ok) return;
    try {
      await API.del("/api/admin/promos/" + id);
      toast("Промокод отключён", "success");
      loadPromos();
    } catch (error) { handleError(error); }
  }

  /* ---------- Users ---------- */
  async function loadUsers() {
    const search = ($("#users-search") || {}).value || "";
    const data = await API.get("/api/admin/users" + (search ? "?search=" + encodeURIComponent(search) : ""));
    const users = data.users || [];
    $("#users-count").textContent = users.length + " чел.";
    const body = $("#users-body");
    if (!users.length) { body.innerHTML = '<tr><td colspan="6" class="empty">Пользователей нет.</td></tr>'; return; }
    body.innerHTML = users
      .map((user) => {
        const isMe = me && user.id === me.id;
        const anonymized = Boolean(user.anonymized_at);
        const role = isMe
          ? '<span class="badge blue">admin · вы</span>'
          : '<select class="select" data-user-role="' + user.id + '"' + (anonymized ? " disabled" : "") + ">" +
            '<option value="user"' + (user.role === "user" ? " selected" : "") + ">user</option>" +
            '<option value="admin"' + (user.role === "admin" ? " selected" : "") + ">admin</option></select>";
        const active = user.is_active ? '<span class="badge green">да</span>' : '<span class="badge red">нет</span>';
        const actions = isMe || anonymized
          ? ""
          : '<button class="btn btn-ghost btn-sm" data-user-block="' + user.id + '" data-active="' + (user.is_active ? "1" : "0") + '">' +
            (user.is_active ? "Блок" : "Разблок") + "</button>" +
            '<button class="btn btn-ghost btn-sm" data-user-delete="' + user.id + '">Удалить</button>';
        return (
          "<tr><td><b>" + esc(user.full_name || "Без имени") + '</b><div class="muted small">' + esc(user.email) + "</div></td><td>" +
          role + "</td><td>" + active + "</td><td>" + (user.privacy_consent_at ? esc(formatDate(user.privacy_consent_at)) : "—") +
          "</td><td>" + esc(formatDate(user.created_at)) + '</td><td><div class="actions">' + actions + "</div></td></tr>"
        );
      })
      .join("");
    $$("[data-user-role]", body).forEach((select) =>
      on(select, "change", () => updateUser(Number(select.dataset.userRole), { role: select.value }))
    );
    $$("[data-user-block]", body).forEach((button) =>
      on(button, "click", () => updateUser(Number(button.dataset.userBlock), { is_active: button.dataset.active !== "1" }))
    );
    $$("[data-user-delete]", body).forEach((button) =>
      on(button, "click", () => deleteUser(Number(button.dataset.userDelete)))
    );
  }

  async function updateUser(id, payload) {
    try {
      await API.patch("/api/admin/users/" + id, payload);
      toast("Пользователь обновлён", "success");
      loadUsers();
    } catch (error) { handleError(error); }
  }

  async function deleteUser(id) {
    const ok = await confirmDialog({
      title: "Удалить аккаунт?",
      message: "Аккаунт и персональные данные будут анонимизированы. История заказов сохранится без имени и контактов.",
      confirmText: "Удалить",
      danger: true,
    });
    if (!ok) return;
    try {
      await API.del("/api/admin/users/" + id);
      toast("Аккаунт анонимизирован", "success");
      loadUsers();
    } catch (error) { handleError(error); }
  }

  /* ---------- Tickets ---------- */
  async function loadTickets() {
    const status = ($("#tickets-status") || {}).value || "";
    const data = await API.get("/api/admin/tickets" + (status ? "?status=" + encodeURIComponent(status) : ""));
    const tickets = data.tickets || [];
    $("#tickets-count").textContent = tickets.length + " шт.";
    const list = $("#tickets-list");
    const empty = $("#tickets-empty");
    if (empty) empty.hidden = tickets.length > 0;
    if (!tickets.length) { list.innerHTML = ""; return; }
    list.innerHTML = tickets
      .map(
        (ticket) =>
          '<article class="ticket"><div class="ticket-head"><div><h3>' + esc(ticket.subject) + '</h3><div class="muted small">' +
          esc(ticket.email) + " · " + esc(formatDate(ticket.created_at)) + " · " + esc(window.CK.ticketCategory(ticket.category)) +
          "</div></div>" + badge(ticket.status) + "</div><p>" + esc(ticket.message) + "</p>" +
          (ticket.admin_reply ? '<div class="ticket-reply">' + esc(ticket.admin_reply) + "</div>" : "") +
          '<div class="form-grid" style="margin-top:12px"><div class="field full"><label>Ответ</label><textarea class="textarea" data-ticket-reply="' +
          ticket.id + '" maxlength="4000" placeholder="Текст ответа (симуляция письма)">' + esc(ticket.admin_reply || "") + "</textarea></div>" +
          '<div class="field"><label>Статус</label><select class="select" data-ticket-status="' + ticket.id + '">' +
          '<option value="open"' + (ticket.status === "open" ? " selected" : "") + ">Открыт</option>" +
          '<option value="answered"' + (ticket.status === "answered" ? " selected" : "") + ">Отвечен</option>" +
          '<option value="closed"' + (ticket.status === "closed" ? " selected" : "") + ">Закрыт</option></select></div>" +
          '<div class="field" style="display:flex;align-items:flex-end"><button class="btn btn-primary" type="button" data-ticket-save="' +
          ticket.id + '">Сохранить ответ</button></div></div></article>'
      )
      .join("");
    $$("[data-ticket-save]", list).forEach((button) =>
      on(button, "click", () => saveTicket(Number(button.dataset.ticketSave)))
    );
  }

  async function saveTicket(id) {
    const reply = document.querySelector('[data-ticket-reply="' + id + '"]');
    const status = document.querySelector('[data-ticket-status="' + id + '"]');
    try {
      await API.patch("/api/admin/tickets/" + id, {
        admin_reply: reply ? reply.value.trim() : "",
        status: status ? status.value : "answered",
      });
      toast("Тикет обновлён", "success");
      loadTickets();
    } catch (error) { handleError(error); }
  }

  /* ---------- Audit ---------- */
  async function loadAudit() {
    const data = await API.get("/api/admin/audit");
    const entries = data.entries || [];
    const body = $("#audit-body");
    if (!entries.length) { body.innerHTML = '<tr><td colspan="5" class="empty">Журнал пуст.</td></tr>'; return; }
    body.innerHTML = entries
      .map((entry) => {
        let details = "";
        try { details = entry.details ? JSON.stringify(entry.details) : ""; } catch (_) { details = ""; }
        if (details.length > 160) details = details.slice(0, 157) + "…";
        return (
          "<tr><td>" + esc(formatDate(entry.created_at)) + "</td><td>" + esc(entry.actor_email || "—") +
          "</td><td><b>" + esc(entry.action) + "</b></td><td>" + esc(entry.entity_type) +
          (entry.entity_id ? " #" + esc(entry.entity_id) : "") + "</td><td><code>" + esc(details) + "</code></td></tr>"
        );
      })
      .join("");
  }

  /* ---------- Init ---------- */
  document.addEventListener("DOMContentLoaded", async () => {
    me = await CK.initLayout({ admin: true, next: "admin.html" });
    if (!me) return;
    $("#admin-admin-email").textContent = me.email;

    $$("#admin-nav a").forEach((link) =>
      on(link, "click", (event) => {
        event.preventDefault();
        switchTab(link.dataset.tab);
      })
    );
    $$("[data-goto]").forEach((link) =>
      on(link, "click", (event) => {
        event.preventDefault();
        switchTab(link.dataset.goto);
      })
    );
    on($("#admin-refresh"), "click", () => {
      const refresh = $("#admin-refresh");
      refresh.disabled = true;
      load(currentTab || "dashboard");
    });
    on(window, "hashchange", () => switchTab(location.hash.slice(1) || "dashboard", false));

    const searchProducts = $("#products-search");
    if (searchProducts) on(searchProducts, "input", CK.debounce(() => loadProducts(), 220));
    const ordersStatus = $("#orders-status");
    if (ordersStatus) on(ordersStatus, "change", loadOrders);
    const ordersSearch = $("#orders-search");
    if (ordersSearch) on(ordersSearch, "input", CK.debounce(() => loadOrders(), 220));
    const usersSearch = $("#users-search");
    if (usersSearch) on(usersSearch, "input", CK.debounce(() => loadUsers(), 220));
    const ticketsStatus = $("#tickets-status");
    if (ticketsStatus) on(ticketsStatus, "change", loadTickets);
    on($("#product-add"), "click", () => openProductForm(null));
    on($("#promo-add"), "click", () => openPromoForm(null));

    switchTab(location.hash.slice(1) || "dashboard", false);
  });
})();
