(function () {
  "use strict";
  const { $, initLayout, toast, icon, escapeHTML, money } = window.CK;

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
      '<div class="product-body">' +
      "<h3>" + escapeHTML(product.name) + "</h3>" +
      '<p class="product-desc">' + escapeHTML(product.short_description) + "</p>" +
      '<div class="product-foot"><span class="price">' + money(product.price_cents) + "</span>" +
      '<button type="button" class="btn btn-accent btn-sm" data-add' + (disabled ? " disabled" : "") + ">" + icon("plus") + "В корзину</button></div>" +
      "</div>";
    el.querySelector(".product-media").addEventListener("click", () => openProduct(product.slug));
    el.querySelector("h3").addEventListener("click", () => openProduct(product.slug));
    el.querySelector("h3").style.cursor = "pointer";
    el.querySelector("[data-add]").addEventListener("click", (event) => {
      event.stopPropagation();
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
        '<div style="display:grid;grid-template-columns:180px 1fr;gap:18px;align-items:center">' +
        '<div class="cart-thumb" style="width:180px;height:150px"><img src="' + escapeHTML(p.image_url) + '" alt="" style="width:140px"></div>' +
        "<div><span class=\"badge\">" + escapeHTML(p.category_label) + "</span>" +
        "<p class=\"muted small\" style=\"margin:10px 0 12px\">" + escapeHTML(p.description || p.short_description) + "</p>" +
        '<div class="price" style="font-size:1.3rem">' + money(p.price_cents) + "</div></div></div>";
      const actions = document.createElement("div");
      const add = document.createElement("button");
      add.type = "button";
      add.className = "btn btn-primary";
      add.textContent = p.in_stock ? "Добавить в корзину" : "Нет в наличии";
      add.disabled = !p.in_stock;
      const close = document.createElement("button");
      close.type = "button";
      close.className = "btn btn-ghost";
      close.textContent = "Закрыть";
      actions.append(close, add);
      const modal = window.CK.openModal({ title: p.name, body: wrap, actions });
      close.addEventListener("click", modal.close);
      add.addEventListener("click", () => {
        window.CK.Cart.add(p, 1);
        toast("«" + p.name + "» в корзине.", "success");
        modal.close();
      });
    } catch (error) {
      toast(window.CK.apiMessage(error), "error");
    }
  }

  function cafeCard(cafe) {
    const el = document.createElement("div");
    el.className = "support-card";
    el.innerHTML =
      '<div class="panel-title"><h3 style="margin:0">' + escapeHTML(cafe.name) + "</h3>" +
      '<span class="open-pill' + (cafe.is_open ? "" : " closed") + '">' + escapeHTML(cafe.status_text) + "</span></div>" +
      '<p class="small muted" style="margin:6px 0 10px">' + icon("pin") + " " + escapeHTML(cafe.address) + "</p>" +
      '<p class="small" style="margin:0">' + icon("phone") + ' <a href="tel:' + escapeHTML(String(cafe.phone || "").replace(/[^+\d]/g, "")) + '">' + escapeHTML(cafe.phone || "") + "</a></p>";
    return el;
  }

  async function boot() {
    await initLayout();
    const grid = $("#popular-grid");
    const cafes = $("#cafes-grid");
    try {
      const [products, cafesData] = await Promise.all([
        window.CKApi.get("/api/products"),
        window.CKApi.get("/api/cafes"),
      ]);
      const list = products.products.filter((p) => p.in_stock).slice(0, 5);
      grid.replaceChildren(...list.map(card));
      cafes.replaceChildren(...cafesData.cafes.map(cafeCard));
    } catch (error) {
      grid.innerHTML = '<div class="empty" style="grid-column:1/-1"><p>Не удалось загрузить печеньки.</p><button type="button" class="btn btn-ghost" data-retry>Повторить</button></div>';
      $("[data-retry]", grid).addEventListener("click", boot);
      if (error.isNetwork) window.CK.showServerOverlay();
      else toast(window.CK.apiMessage(error), "error");
      cafes.innerHTML = "";
    }
  }

  document.addEventListener("DOMContentLoaded", boot);
})();
