/* KubanoID: регистрация. */
(function () {
  "use strict";
  const { $, initLayout, toast, setFormError, setBusy } = window.CK;

  function nextTarget() {
    const raw = new URLSearchParams(location.search).get("next") || "";
    const allowed = ["account.html", "checkout.html", "order.html", "admin.html"];
    return allowed.includes(raw) ? raw : "account.html";
  }

  async function boot() {
    await initLayout();
    if (window.CKApi.getToken() && window.CK_USER) {
      location.replace(nextTarget());
      return;
    }
    const shield = $("#register-shield");
    if (shield) shield.innerHTML = window.CK.icon("shield");
  }

  $("#register-form").addEventListener("submit", async (event) => {
    event.preventDefault();
    setFormError($("#register-error"), "");
    if (!$("#register-consent").checked) {
      setFormError($("#register-error"), "Без согласия на обработку персональных данных аккаунт не создаётся.");
      return;
    }
    const button = $("#register-submit");
    setBusy(button, true, "Создаём…");
    try {
      const data = await window.CKApi.post("/api/auth/register", {
        full_name: $("#register-name").value.trim(),
        email: $("#register-email").value.trim(),
        password: $("#register-password").value,
        privacy_consent: true,
      });
      window.CKApi.setToken(data.token);
      toast("KubanoID создан. Добро пожаловать!", "success");
      setTimeout(() => { location.replace(nextTarget()); }, 250);
    } catch (error) {
      setFormError($("#register-error"), window.CK.apiMessage(error));
      if (error.status === 0) window.CK.showServerOverlay();
    } finally {
      setBusy(button, false);
    }
  });

  document.addEventListener("DOMContentLoaded", boot);
})();
