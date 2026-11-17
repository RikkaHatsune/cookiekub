/* 403: дружелюбный отказ + inline-вход KubanoID. */
(function () {
  "use strict";
  const { $, initLayout, toast, setFormError, setBusy, apiMessage } = window.CK;

  function safeNext() {
    const raw = new URLSearchParams(location.search).get("next") || "";
    const page = raw.split("?")[0];
    const allowed = ["admin.html", "account.html", "order.html", "checkout.html", "catalog.html", "index.html", "support.html"];
    return allowed.includes(page) ? page : "index.html";
  }

  function applyCopy(reason, user) {
    if (reason === "auth") {
      $("#forbidden-title").textContent = "Лучше закажите печеньку, а здесь - мы лучше сами";
      $("#forbidden-sub").textContent = "Сначала войдите в KubanoID — и мы вернём вас туда, куда вы шли. Или загляните в каталог: там печеньки.";
    } else {
      $("#forbidden-title").textContent = "Лучше закажите печеньку, а здесь - мы лучше сами";
      $("#forbidden-sub").textContent = "Эта страница только для администраторов CookieKub. Если у вас есть админ-доступ — войдите. Если нет — печеньки ждут в каталоге.";
    }
    if (user && user.role !== "admin") {
      $("#forbidden-user-note").hidden = false;
      $("#forbidden-user-text").textContent =
        "Вы вошли как " + (user.full_name || user.email) + " (" + user.email + "), но админ-права есть только у сотрудников CookieKub.";
    }
  }

  async function boot() {
    const params = new URLSearchParams(location.search);
    const reason = params.get("reason") === "auth" ? "auth" : "admin";
    const user = await initLayout();
    applyCopy(reason, user);
    if (user && user.role === "admin") {
      location.replace(safeNext());
      return;
    }
    const note = $("#forbidden-user-note");
    $("#forbidden-logout").addEventListener("click", async () => {
      try { await window.CKApi.post("/api/auth/logout", {}); } catch (_) { /* всё равно чистим */ }
      window.CKApi.clearToken();
      location.reload();
    });
    if (user) note.hidden = false;
  }

  $("#forbidden-form").addEventListener("submit", async (event) => {
    event.preventDefault();
    setFormError($("#forbidden-error"), "");
    const button = $("#forbidden-submit");
    setBusy(button, true, "Входим…");
    try {
      const data = await window.CKApi.post("/api/auth/login", {
        email: $("#forbidden-email").value.trim(),
        password: $("#forbidden-password").value,
      });
      window.CKApi.setToken(data.token);
      if (data.user.role === "admin") {
        toast("Добро пожаловать, администратор", "success");
        setTimeout(() => { location.replace(safeNext()); }, 250);
      } else {
        setFormError($("#forbidden-error"), "Вы вошли как " + (data.user.full_name || data.user.email) + ", но админ-права есть только у сотрудников. Попробуйте аккаунт администратора.");
        $("#forbidden-user-note").hidden = false;
        $("#forbidden-user-text").textContent =
          "Вы вошли как " + (data.user.full_name || data.user.email) + " (" + data.user.email + "), но админ-права есть только у сотрудников CookieKub.";
        setBusy(button, false);
      }
    } catch (error) {
      setFormError($("#forbidden-error"), apiMessage(error));
      if (error.isNetwork) window.CK.showServerOverlay();
      setBusy(button, false);
    }
  });

  document.addEventListener("DOMContentLoaded", boot);
})();
