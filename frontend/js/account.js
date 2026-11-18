/* KubanoID: кабинет — профиль, заказы, обращения, безопасность. */
(function () {
  "use strict";
  const { $, $$, icon, money, formatDate, statusInfo, toast, setFormError, setBusy, initLayout, openModal, apiMessage } = window.CK;

  let user = null;

  function fillIcons(root) {
    $$("[data-icon]", root || document).forEach((el) => {
      el.innerHTML = icon(el.dataset.icon);
    });
  }

  function profileMarkup() {
    const rows = [
      ["Имя", user.full_name || "—"],
      ["Email", user.email],
      ["Роль", user.role === "admin" ? "Администратор" : "Пользователь"],
      ["KubanoID создан", formatDate(user.created_at, true)],
      ["Согласие на обработку ПД", user.privacy_consent_at ? formatDate(user.privacy_consent_at, true) : "не зафиксировано"],
    ];
    $("#profile-details tbody").innerHTML = rows.map(([k, v]) =>
      "<tr><td>" + window.CK.escapeHTML(k) + "</td><td>" + window.CK.escapeHTML(v) + "</td></tr>"
    ).join("");
  }

  function orderCard(order) {
    const status = statusInfo(order.status);
    const cafe = order.cafe ? order.cafe.name : "Курьер";
    const payment = order.payment && order.payment.last4 ? "Карта •••• " + order.payment.last4 : "Оплата картой";
    return (
      '<article class="history-item">' +
        '<div class="history-main">' +
          "<div><b>" + window.CK.escapeHTML(order.number) + "</b> " +
          '<span class="badge ' + status.cls + '">' + status.label + "</span></div>" +
          '<div class="muted small">' + formatDate(order.created_at, true) + " · " + window.CK.escapeHTML(order.fulfillment_label || "") + " · " + window.CK.escapeHTML(cafe) + "</div>" +
          '<div class="muted small">' + window.CK.escapeHTML(payment) + " · позиций: " + String((order.items || []).length) + "</div>" +
        "</div>" +
        '<div class="history-side"><b>' + money(order.total_cents) + "</b>" +
        '<a class="btn btn-ghost btn-sm" href="order.html?number=' + encodeURIComponent(order.number) + '">Открыть заказ</a></div>' +
      "</article>"
    );
  }

  async function loadOrders(showToast) {
    const list = $("#orders-list");
    try {
      const data = await window.CKApi.get("/api/orders");
      const orders = data.orders || [];
      list.innerHTML = orders.map(orderCard).join("");
      $("#orders-empty").hidden = orders.length > 0;
      if (showToast) toast("История обновлена", "success");
    } catch (error) {
      list.innerHTML = '<div class="empty-note"><p>' + window.CK.escapeHTML(apiMessage(error)) + "</p></div>";
      if (error.isNetwork) window.CK.showServerOverlay();
    }
  }

  function ticketCard(ticket) {
    const status = ticket.status === "answered" ? ["green", "Ответ получен"] : ticket.status === "closed" ? ["", "Закрыт"] : ["amber", "Открыт"];
    return (
      '<article class="ticket">' +
        '<div class="ticket-head"><div><h3>' + window.CK.escapeHTML(ticket.subject) + "</h3>" +
        '<span class="muted small">' + formatDate(ticket.created_at, true) + " · " + window.CK.escapeHTML(window.CK.ticketCategory(ticket.category)) + "</span></div>" +
        '<span class="badge ' + status[0] + '">' + status[1] + "</span></div>" +
        "<p>" + window.CK.escapeHTML(ticket.message) + "</p>" +
        (ticket.admin_reply ? '<div class="ticket-reply"><b>Поддержка:</b><br>' + window.CK.escapeHTML(ticket.admin_reply) + "</div>" : "") +
      "</article>"
    );
  }

  async function loadTickets() {
    try {
      const data = await window.CKApi.get("/api/tickets/my");
      const tickets = data.tickets || [];
      $("#tickets-list").innerHTML = tickets.map(ticketCard).join("");
      $("#tickets-empty").hidden = tickets.length > 0;
    } catch (error) {
      $("#tickets-list").innerHTML = '<p class="muted small">' + window.CK.escapeHTML(apiMessage(error)) + "</p>";
    }
  }

  function askDelete() {
    const body = document.createElement("div");
    body.innerHTML =
      "<p>Аккаунт и персональные данные будут анонимизированы. Заказы останутся обезличенными, сессии — отозваны. Это действие нельзя отменить.</p>" +
      '<div class="field"><label for="delete-password">Введите пароль для подтверждения</label>' +
      '<input class="input" id="delete-password" type="password" autocomplete="current-password" maxlength="128"></div>' +
      '<div class="form-error" id="delete-error" role="alert"></div>';
    const actions = document.createElement("div");
    actions.innerHTML = '<button class="btn btn-ghost" type="button" data-cancel>Отмена</button><button class="btn btn-danger" type="button" data-confirm>Удалить аккаунт</button>';
    const modal = openModal({ title: "Удалить KubanoID?", body, actions });
    const input = body.querySelector("#delete-password");
    const errorEl = body.querySelector("#delete-error");
    setTimeout(() => input.focus(), 80);
    actions.querySelector("[data-cancel]").addEventListener("click", modal.close);
    actions.querySelector("[data-confirm]").addEventListener("click", async () => {
      if (!input.value) { setFormError(errorEl, "Введите пароль"); return; }
      const button = actions.querySelector("[data-confirm]");
      setBusy(button, true, "Удаляем…");
      try {
        await window.CKApi.del("/api/auth/account", { password: input.value });
        window.CKApi.clearToken();
        toast("Аккаунт удалён. Данные анонимизированы.", "success");
        setTimeout(() => { location.replace("index.html"); }, 500);
      } catch (error) {
        setFormError(errorEl, apiMessage(error));
        setBusy(button, false);
      }
    });
  }

  async function boot() {
    user = await initLayout({ requireAuth: true, next: "account.html" });
    if (!user) return;
    fillIcons();
    $("#profile-avatar").textContent = window.CK.initials(user.full_name || user.email);
    $("#profile-name").textContent = user.full_name || "Без имени";
    $("#profile-email").textContent = user.email;
    $("#profile-role").textContent = user.role === "admin" ? "администратор" : "пользователь";
    profileMarkup();
    await Promise.all([loadOrders(false), loadTickets()]);

    $("#orders-refresh").addEventListener("click", () => loadOrders(true));

    $("#password-form").addEventListener("submit", async (event) => {
      event.preventDefault();
      setFormError($("#password-error"), "");
      const button = $("#password-submit");
      setBusy(button, true, "Меняем…");
      try {
        await window.CKApi.post("/api/auth/change-password", {
          current_password: $("#current-password").value,
          new_password: $("#new-password").value,
        });
        window.CKApi.clearToken();
        toast("Пароль изменён. Все сессии отозваны — войдите заново.", "success");
        setTimeout(() => { location.replace("login.html"); }, 600);
      } catch (error) {
        setFormError($("#password-error"), apiMessage(error));
      } finally {
        setBusy(button, false);
      }
    });

    $("#delete-account").addEventListener("click", askDelete);

    const sections = $$(".side-nav nav a");
    sections.forEach((link) => {
      link.addEventListener("click", () => {
        sections.forEach((l) => l.classList.remove("is-active"));
        link.classList.add("is-active");
      });
    });
  }

  document.addEventListener("DOMContentLoaded", boot);
})();
