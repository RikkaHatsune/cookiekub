/* CookieKub: публичная конфигурация. Секретов здесь нет. */
(function () {
  "use strict";
  const isPages = /\.github\.io$/i.test(location.hostname);
  const override = localStorage.getItem("cookiekub.apiBase");
  const production = "https://cookiekub-api.onrender.com";
  window.COOKIEKUB = {
    apiBase: override !== null ? override.replace(/\/$/, "") : isPages ? production : "",
    supportEmail: "support@cookiekub.ru",
    brand: "CookieKub",
    authBrand: "KubanoID",
    version: "1.0.0",
  };
})();
