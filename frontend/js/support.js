/* Поддержка: тикет + имитация письма. */
(function () {
  "use strict";
  const { $, $$, icon, toast, setFormError, setBusy, initLayout, apiMessage } = window.CK;

  async function boot() {
    const user = await initLayout({ next: "support.html" });
    $$("[data-icon]").forEach((el) => { el.innerHTML = icon(el.dataset.icon); });
    if (user) {
      const field = $("#support-email-field");
      const input = $("#support-email");
      input.value = user.email;
      input.required = false;
      field.hidden = true;
    }
  }

  $("#support-form").addEventListener("submit", async (event) => {
    event.preventDefault();
    setFormError($("#support-error"), "");
    const button = $("#support-submit");
    setBusy(button, true, "Отправляем…");
    try {
      const payload = {
        category: $("#support-category").value,
        subject: $("#support-subject").value.trim(),
        message: $("#support-message").value.trim(),
      };
      if (!$("#support-email-field").hidden && $("#support-email").value.trim()) {
        payload.email = $("#support-email").value.trim();
      }
      const data = await window.CKApi.post("/api/tickets", payload);
      const ticket = data.ticket || {};
      $("#support-success").hidden = false;
      $("#support-success").classList.add("is-visible");
      $("#support-success-text").textContent =
        "Тикет #" + ticket.id + " создан. " +
        (window.CK_USER ? "Ответ появится в кабинете." : "Сохраните номер обращения: " + ticket.id + ".");
      $("#support-form").reset();
      toast("Тикет создан", "success");
      $("#support-success").scrollIntoView({ behavior: "smooth", block: "center" });
    } catch (error) {
      setFormError($("#support-error"), apiMessage(error));
      if (error.isNetwork) window.CK.showServerOverlay();
    } finally {
      setBusy(button, false);
    }
  });

  document.addEventListener("DOMContentLoaded", boot);
})();
