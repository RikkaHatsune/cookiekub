(function () {
  "use strict";
  const { $, $$, initLayout, toast, icon, escapeHTML, money, debounce } = window.CK;
  let all = [];
  let category = "all";
  let query = "";
  let sort = "default";

  function card(product) {
    const el = document.createElement("article");
    el.className = "product-card";
    const disabled = !product.in_stock;
    el.innerHTML =
      '<div class="product-media">' +
      '<span class="product-badge">' + escapeHTML(product.category_label) + "</span>" +
      '<img src="' + escapeHTML(product.image_url) + '" alt="' + escapeHTML(product.name) + '">' +
      (disabled ? '<span class="product-stock low">нет в наличии</span>' : '<span class="product-stock">' + product.stock_qty + " шт.</span>") +
      "</div>" +
      '<div class="product-body"><h3>' + escapeHTML(product.name) + "</h3>" +
      '<p class="product-desc">' + escapeHTML(product.short_description) + "</p>" +
      '<div class="product-foot"><span class="price">' + money(product.price_cents) + "</span>" +
      '<button type="button" class="btn btn-accent btn-sm" data-add' + (disabled ? " disabled" : "") + ">" + icon("plus") + "В корзину</button>" +
      "</div></div>";
    const open = () => openProduct(product.slug);
    el.querySelector(".product-media").addEventListener("click", open);
    el.querySelector("h3").addEventListener("click", open);
    el.querySelector("h3").style.cursor = "pointer";
    el.querySelector("[data-add]").addEventListener("click", () => {
      window.CK.Cart.add(product, 1);
      toast("«" + product.name + "» в корзине.", "success");
    });
    return el;
  }

  async function openProduct(slug) {
    try {
      const data = await window.CKApi.get("/api/products/" + encodeURIComponent(slug));
      const p = data.product;
      const wrap = document.createElement("div");
      wrap.innerHTML =
        '<div style="display:grid;grid-template-columns:170px 1fr;gap:18px;align-items:center">' +
        '<div class="cart-thumb" style="width:170px;height:140px"><img src="' + escapeHTML(p.image_url) + '" alt="" style="width:130px"></div>' +
        "<div><span class=\"badge\">" + escapeHTML(p.category_label) + "</span>" +
        "<p class=\"muted small\" style=\"margin:10px 0 12px\">" + escapeHTML(p.description || p.short_description) + "</p>" +
        '<div class="price" style="font-size:1.3rem">' + money(p.price_cents) + ' <small>· ' + p.stock_qty + " шт.</small></div></div></div>";
      const actions = document.createElement("div");
      const close = document.createElement("button");
      close.type = "button"; close.className = "btn btn-ghost"; close.textContent = "Закрыть";
      const add = document.createElement("button");
      add.type = "button"; add.className = "btn btn-primary"; add.textContent = "В корзину"; add.disabled = !p.in_stock;
      actions.append(close, add);
      const modal = window.CK.openModal({ title: p.name, body: wrap, actions });
      close.addEventListener("click", modal.close);
      add.addEventListener("click", () => {
        window.CK.Cart.add(p, 1);
        toast("«" + p.name + "» в корзине.", "success");
        modal.close();
      });
    } catch (error) { toast(window.CK.apiMessage(error), "error"); }
  }

  function apply() {
    const q = query.trim().toLowerCase();
    let list = all.filter((p) => {
      const catOk = category === "all" || p.category === category;
      const textOk = !q || (p.name + " " + p.short_description + " " + p.category_label).toLowerCase().includes(q);
      return catOk && textOk;
    });
    if (sort === "price-asc") list.sort((a, b) => a.price_cents - b.price_cents);
    else if (sort === "price-desc") list.sort((a, b) => b.price_cents - a.price_cents);
    else if (sort === "name") list.sort((a, b) => a.name.localeCompare(b.name, "ru"));
    else list.sort((a, b) => (a.sort_order || 0) - (b.sort_order || 0));
    const grid = $("#catalog-grid");
    grid.replaceChildren(...list.map(card));
    $("#catalog-empty").hidden = list.length > 0;
    grid.hidden = list.length === 0;
    const note = $("#stock-note");
    if (note) note.textContent = list.length + " из " + all.length + " печенек";
  }

  function buildChips() {
    const host = $("#category-chips");
    const cats = [];
    all.forEach((p) => { if (!cats.some((c) => c.key === p.category)) cats.push({ key: p.category, label: p.category_label }); });
    const buttons = [{ key: "all", label: "Все" }].concat(cats);
    host.replaceChildren(...buttons.map((c) => {
      const b = document.createElement("button");
      b.type = "button"; b.className = "chip" + (c.key === category ? " is-active" : "");
      b.dataset.category = c.key; b.textContent = c.label;
      b.addEventListener("click", () => {
        category = c.key;
        $$(".chip", host).forEach((x) => x.classList.toggle("is-active", x.dataset.category === category));
        apply();
      });
      return b;
    }));
  }

  async function boot() {
    await initLayout();
    try {
      const data = await window.CKApi.get("/api/products");
      all = data.products;
      buildChips();
      apply();
    } catch (error) {
      $("#catalog-grid").innerHTML = '<div class="empty" style="grid-column:1/-1"><p>Печка не отвечает.</p><button type="button" class="btn btn-ghost" data-retry>Повторить</button></div>';
      $("[data-retry]").addEventListener("click", boot);
      if (error.isNetwork) window.CK.showServerOverlay();
      else toast(window.CK.apiMessage(error), "error");
    }
  }

  $("#catalog-search").addEventListener("input", debounce((event) => { query = event.target.value; apply(); }, 180));
  $("#catalog-sort").addEventListener("change", (event) => { sort = event.target.value; apply(); });
  document.addEventListener("DOMContentLoaded", boot);
})();
