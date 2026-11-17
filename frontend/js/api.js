/* Тонкий клиент API CookieKub. Токен KubanoID — только в localStorage. */
(function () {
  "use strict";
  const TOKEN_KEY = "cookiekub.token";
  const base = () => (window.COOKIEKUB && window.COOKIEKUB.apiBase) || "";

  class ApiError extends Error {
    constructor(status, code, message, details) {
      super(message || "Ошибка запроса");
      this.name = "ApiError";
      this.status = status;
      this.code = code || "http_error";
      this.details = details || null;
    }
    get isNetwork() { return this.status === 0; }
    get isAuth() { return this.status === 401; }
    get isForbidden() { return this.status === 403; }
  }

  function getToken() {
    try { return localStorage.getItem(TOKEN_KEY); } catch (_) { return null; }
  }
  function setToken(token) {
    try {
      if (token) localStorage.setItem(TOKEN_KEY, token);
      else localStorage.removeItem(TOKEN_KEY);
    } catch (_) { /* приватный режим */ }
  }
  function clearToken() { setToken(null); }

  async function request(path, options) {
    const opts = options || {};
    const headers = Object.assign({ Accept: "application/json" }, opts.headers || {});
    const token = getToken();
    if (opts.auth !== false && token) headers.Authorization = "Bearer " + token;
    let body;
    if (opts.body !== undefined && opts.body !== null) {
      headers["Content-Type"] = "application/json";
      body = JSON.stringify(opts.body);
    }
    let response;
    try {
      response = await fetch(base() + path, {
        method: opts.method || "GET",
        headers,
        body,
        cache: "no-store",
      });
    } catch (_) {
      throw new ApiError(0, "network", "Не удалось связаться с сервером. Проверьте подключение.", null);
    }
    if (response.status === 204) return null;
    const text = await response.text();
    let data = null;
    if (text) {
      try { data = JSON.parse(text); } catch (_) { data = null; }
    }
    if (!response.ok) {
      const error = (data && data.error) || {};
      throw new ApiError(
        response.status,
        error.code,
        error.message || "Не получилось выполнить запрос (" + response.status + ").",
        error.details
      );
    }
    return data;
  }

  const get = (path, opts) => request(path, Object.assign({}, opts, { method: "GET" }));
  const post = (path, body, opts) => request(path, Object.assign({}, opts, { method: "POST", body }));
  const patch = (path, body, opts) => request(path, Object.assign({}, opts, { method: "PATCH", body }));
  const del = (path, body, opts) => request(path, Object.assign({}, opts, { method: "DELETE", body }));

  window.CKApi = {
    ApiError,
    request,
    get,
    post,
    patch,
    del,
    getToken,
    setToken,
    clearToken,
    base,
    isAuthenticated: () => Boolean(getToken()),
  };
})();
