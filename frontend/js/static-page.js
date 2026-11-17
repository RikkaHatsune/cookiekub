/* Статическая страница: общая шапка/подвал. */
(function () {
  "use strict";
  async function boot() {
    await window.CK.initLayout();
    const reload = document.getElementById("reload-page");
    if (reload) reload.addEventListener("click", () => location.reload());
  }
  document.addEventListener("DOMContentLoaded", boot);
})();
