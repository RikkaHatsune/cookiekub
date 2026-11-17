/* KubanoID: вход. */
(function () {
  "use strict";
  const { $, initLayout, toast, setFormError, setBusy } = window.CK;

  function nextTarget() {
    const raw = new URLSearchParams(location.search).get("next") || "";
    const allowed = ["account.html", "checkout.html", "order.html", "admin.html"];
    return allowed.includes(raw) ? raw : "account.html";
  }

  async function boot() {
    const user = await initLayout();
    if (window.CKApi.getToken() && window.CK_USER) {
      location.replace(nextTarget());
      return;
    }
    const shield = $("#login-shield");
    if (shield) shield.innerHTML = window.CK.icon("shield");
  }

  $("#login-form").addEventListener("submit", async (event) => {
    event.preventDefault();
    setFormError($("#login-error"), "");
    const button = $("#login-submit");
    setBusy(button, true, "Входим…");
    try {
      const data = await window.CKApi.post("/api/auth/login", {
        email: $("#login-email").value.trim(),
        password: $("#login-password").value,
      });
      window.CKApi.setToken(data.token);
      toast("С возвращением, " + (data.user.full_name || "друг") + "!", "success");
      setTimeout(() => { location.replace(nextTarget()); }, 250);
    } catch (error) {
      setFormError($("#login-error"), window.CK.apiMessage(error));
      if (error.status === 0) window.CK.showServerOverlay();
    } finally {
      setBusy(button, false);
    }
  });

  document.addEventListener("DOMContentLoaded", boot);
})();
