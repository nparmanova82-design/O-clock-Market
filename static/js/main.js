/* O’clock market — sahifa ichidagi harakatlar.
   Hammasi JS’siz ham ishlaydi (oddiy formalar va havolalar); JS faqat qulaylik qo‘shadi. */
(() => {
  "use strict";

  const $ = (sel, root = document) => root.querySelector(sel);
  const $$ = (sel, root = document) => Array.from(root.querySelectorAll(sel));
  const html = document.documentElement;
  const desktop = window.matchMedia("(min-width: 1024px)");
  const AJAX = { "X-Requested-With": "XMLHttpRequest" };

  // Joriy tildagi matnlar va manzillar: base.html dagi <script id="i18n"> (context_processors._js_texts)
  let T = {};
  try { T = JSON.parse(document.getElementById("i18n")?.textContent || "{}"); } catch (e) { /* bo‘sh qoladi */ }
  const U = T.urls || {};
  const tpl = (text, vars) => String(text || "").replace(/%\((\w+)\)s/g, (_, k) => (k in vars ? vars[k] : ""));

  const debounce = (fn, ms) => {
    let t;
    return (...args) => { clearTimeout(t); t = setTimeout(() => fn(...args), ms); };
  };
  const store = {
    get(k) { try { return localStorage.getItem(k); } catch (e) { return null; } },
    set(k, v) { try { localStorage.setItem(k, v); } catch (e) { /* xususiy rejim */ } },
  };
  const parse = (text) => new DOMParser().parseFromString(text, "text/html");
  const esc = (s) => String(s).replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));

  async function postForm(form) {
    const res = await fetch(form.action, { method: "POST", body: new FormData(form), headers: AJAX, credentials: "same-origin" });
    if (!res.ok) throw new Error(res.status);
    return res.json();
  }

  /* ———— Bildirishnomalar ———— */
  const toastBox = $("[data-toasts]");
  function toast(message, level = "success", link) {
    if (!toastBox || !message) return;
    const el = document.createElement("div");
    const icon = level === "error" || level === "warning" ? "i-close" : "i-check";
    el.className = `toast toast--${level}`;
    el.setAttribute("role", level === "error" ? "alert" : "status");
    el.innerHTML = `<svg class="i"><use href="#${icon}"/></svg><span>${esc(message)}</span>` +
      (link ? `<a href="${esc(link.href)}"${link.open ? ` data-open="${esc(link.open)}"` : ""}>${esc(link.label)}</a>` : "");
    toastBox.appendChild(el);
    setTimeout(() => {
      el.classList.add("is-leaving");
      el.addEventListener("animationend", () => el.remove(), { once: true });
    }, 3800);
  }
  $$("[data-message]").forEach((m) => { toast(m.textContent.trim(), m.dataset.level || "success"); m.remove(); });

  /* ———— Hisoblagichlar (savatcha, sevimlilar) ———— */
  function setCount(sel, n) {
    $$(sel).forEach((el) => {
      el.textContent = n;
      el.classList.toggle("is-zero", !n);
      el.classList.remove("is-bump");
      void el.offsetWidth;
      if (n) el.classList.add("is-bump");
    });
  }

  /* ———— Yon panellar: menyu, savatcha, qidiruv, filtr ———— */
  const overlay = $("[data-overlay]");
  let openDrawer = null;
  let lastFocus = null;

  function open(name) {
    const drawer = $(`[data-drawer="${name}"]`);
    if (!drawer) return;
    if (openDrawer && openDrawer !== drawer) close(true);
    lastFocus = document.activeElement;
    openDrawer = drawer;
    drawer.classList.add("is-open");
    drawer.setAttribute("aria-hidden", "false");
    overlay.hidden = false;
    requestAnimationFrame(() => overlay.classList.add("is-visible"));
    document.body.classList.add("is-locked");
    $$(`[data-open="${name}"]`).forEach((b) => b.setAttribute("aria-expanded", "true"));
    if (name === "cart") loadCart();
    if (name === "search") setTimeout(() => $("[data-search-input]")?.focus(), 80);
    else setTimeout(() => $("[data-close]", drawer)?.focus({ preventScroll: true }), 80);
  }

  function close(instant) {
    if (!openDrawer) return;
    const drawer = openDrawer;
    openDrawer = null;
    drawer.classList.remove("is-open");
    drawer.setAttribute("aria-hidden", "true");
    $$(`[data-open="${drawer.dataset.drawer}"]`).forEach((b) => b.setAttribute("aria-expanded", "false"));
    if (instant === true) return;
    overlay.classList.remove("is-visible");
    setTimeout(() => { if (!openDrawer) overlay.hidden = true; }, 350);
    document.body.classList.remove("is-locked");
    if (lastFocus && lastFocus.focus) lastFocus.focus({ preventScroll: true });
  }

  document.addEventListener("click", (e) => {
    const opener = e.target.closest("[data-open]");
    if (opener) {
      // Savatcha sahifasida savatcha tugmasi oddiy havola bo‘lib qoladi
      if (opener.dataset.open === "cart" && $("[data-cart-page]")) return;
      e.preventDefault();
      open(opener.dataset.open);
      return;
    }
    if (e.target.closest("[data-close]") || e.target === overlay) close();
  });
  document.addEventListener("keydown", (e) => { if (e.key === "Escape" && openDrawer) close(); });

  /* ———— Sarlavha soyasi ———— */
  const header = $("[data-header]");
  if (header) {
    const onScroll = () => header.classList.toggle("is-scrolled", window.scrollY > 8);
    window.addEventListener("scroll", onScroll, { passive: true });
    onScroll();
  }

  /* ———— Jonli soatlar (logotip va bosh sahifadagi soat) ———— */
  const tz = "Asia/Tashkent";
  const fmt = new Intl.DateTimeFormat("en-GB", { timeZone: tz, hour: "2-digit", minute: "2-digit", second: "2-digit", hour12: false });
  function tashkentNow() {
    const [h, m, s] = fmt.format(new Date()).split(":").map(Number);
    return { h: h % 24, m, s };
  }
  const liveHands = $$(".hand-h, .hand-m, .hand-s").filter((g) => g.dataset.c && !g.closest(".clock404"));
  const liveText = $$("[data-live-time]");
  // Strelkalar faqat soat ekranda ko‘rinib turganda buriladi — aks holda brauzer bekorga qayta chizadi
  const visibleClocks = new Set();
  const clockSvgs = [...new Set(liveHands.map((g) => g.ownerSVGElement).filter(Boolean))];
  if ("IntersectionObserver" in window) {
    const io = new IntersectionObserver((entries) => entries.forEach((e) => {
      if (e.isIntersecting) visibleClocks.add(e.target); else visibleClocks.delete(e.target);
    }));
    clockSvgs.forEach((svg) => io.observe(svg));
  } else {
    clockSvgs.forEach((svg) => visibleClocks.add(svg));
  }
  function tick() {
    if (document.hidden) return;
    const { h, m, s } = tashkentNow();
    const deg = { h: (h % 12) * 30 + m * 0.5 + s / 120, m: m * 6 + s * 0.1, s: s * 6 };
    liveHands.forEach((g) => {
      if (!visibleClocks.has(g.ownerSVGElement)) return;
      const which = g.classList.contains("hand-h") ? "h" : g.classList.contains("hand-m") ? "m" : "s";
      g.setAttribute("transform", `rotate(${deg[which].toFixed(2)} ${g.dataset.c})`);
    });
    const pad = (n) => String(n).padStart(2, "0");
    liveText.forEach((el) => { el.textContent = `${pad(h)}:${pad(m)}:${pad(s)}`; });
  }
  if (liveHands.length || liveText.length) { tick(); setInterval(tick, 1000); }

  /* ———— Aksiya taymeri ———— */
  function initCountdowns(root = document) {
    $$("[data-countdown]", root).forEach((el) => {
      if (el.dataset.ready) return;
      el.dataset.ready = "1";
      const end = new Date(el.dataset.countdown).getTime();
      if (!end) return;
      const names = T.units || ["kun", "soat", "daqiqa", "soniya"];
      const units = [[names[0], 86400], [names[1], 3600], [names[2], 60], [names[3], 1]];
      el.innerHTML = units.map(([label]) => `<span class="countdown__unit"><b>00</b><small>${label}</small></span>`).join("");
      const nums = $$("b", el);
      const draw = () => {
        let left = Math.max(0, Math.floor((end - Date.now()) / 1000));
        units.forEach(([, size], i) => {
          const v = Math.floor(left / size);
          left -= v * size;
          nums[i].textContent = String(v).padStart(2, "0");
        });
      };
      draw();
      setInterval(draw, 1000);
    });
  }
  initCountdowns();

  /* ———— Savatchaga qo‘shish ———— */
  document.addEventListener("submit", async (e) => {
    const form = e.target;
    if (form.matches("[data-cart-form]")) {
      e.preventDefault();
      const btn = $("button[type=submit], button:not([type])", form);
      btn?.classList.add("is-loading");
      try {
        const data = await postForm(form);
        setCount("[data-cart-count]", data.count);
        toast(data.message, data.ok ? "success" : "warning", data.ok ? { href: U.cart || "/savat/", label: T.cart || "Savatcha", open: "cart" } : null);
        if (data.ok && btn) {
          btn.classList.add("is-added");
          const use = $("use", btn);
          const prev = use?.getAttribute("href");
          if (use) use.setAttribute("href", "#i-check");
          setTimeout(() => { btn.classList.remove("is-added"); if (use && prev) use.setAttribute("href", prev); }, 1600);
        }
        const note = $("[data-incart]");
        if (data.ok && note && form.closest(".pdp")) { note.hidden = false; }
      } catch (err) {
        form.submit();
      } finally {
        btn?.classList.remove("is-loading");
      }
      return;
    }

    /* ———— Sevimlilar ———— */
    if (form.matches("[data-wish-form]")) {
      e.preventDefault();
      try {
        const data = await postForm(form);
        $$(`[data-wish-form][action="${form.getAttribute("action")}"] button`).forEach((b) => {
          b.classList.toggle("is-active", data.added);
          b.setAttribute("aria-pressed", String(data.added));
          b.classList.remove("is-pop"); void b.offsetWidth; b.classList.add("is-pop");
        });
        setCount("[data-wish-count]", data.count);
        toast(data.message, "success", data.added ? { href: U.wishlist || "/sevimlilar/", label: T.view || "Ko‘rish" } : null);
        if (!data.added && document.body.classList.contains("page-wishlist")) {
          const card = form.closest(".card");
          card?.animate([{ opacity: 1 }, { opacity: 0, transform: "scale(.96)" }], { duration: 250 }).finished.then(() => {
            card.remove();
            if (!$(".card")) location.reload();
          });
        }
      } catch (err) {
        form.submit();
      }
      return;
    }

    /* ———— Savatcha ichidagi o‘zgarishlar (son, o‘chirish) ———— */
    if (form.matches("[data-swap-form]")) {
      e.preventDefault();
      const zone = form.closest("[data-swap]");
      zone?.classList.add("is-loading");
      try {
        const data = await postForm(form);
        setCount("[data-cart-count]", data.count);
        if (data.message) toast(data.message);
        await refreshSwap(zone);
      } catch (err) {
        form.submit();
      }
      return;
    }

    /* ———— Qayta qo‘ng‘iroq so‘rovi ———— */
    if (form.matches("[data-callback-form]")) {
      e.preventDefault();
      const btn = $("button[type=submit]", form);
      btn?.classList.add("is-loading");
      try {
        const data = await postForm(form);
        toast(data.message, data.ok ? "success" : "error");
        if (data.ok) form.reset();
      } catch (err) {
        form.submit();
      } finally {
        btn?.classList.remove("is-loading");
      }
    }
  });

  // Son o‘zgartiruvchi tugmalar: − / +
  document.addEventListener("click", (e) => {
    const step = e.target.closest("[data-step]");
    if (!step) return;
    const box = step.closest("[data-qty]");
    const input = $("input", box);
    const max = Number(input.max) || 99;
    const min = Number(input.min) || 0;
    const v = Math.max(min, Math.min(max, (Number(input.value) || 0) + Number(step.dataset.step)));
    if (v === Number(input.value)) return;
    input.value = v;
    const form = input.form;
    if (form && form.matches("[data-swap-form]")) form.requestSubmit();
  });
  document.addEventListener("change", (e) => {
    const input = e.target;
    if (input.matches("[data-qty] input") && input.form?.matches("[data-swap-form]")) input.form.requestSubmit();
  });

  async function refreshSwap(zone) {
    if (!zone) return;
    if (zone.closest("[data-cart-body]")) return loadCart(true);
    const res = await fetch(location.href, { headers: AJAX, credentials: "same-origin" });
    const fresh = $(`[data-swap="${zone.dataset.swap}"]`, parse(await res.text()));
    if (fresh) zone.replaceWith(fresh); else location.reload();
  }

  /* ———— Yon paneldagi savatcha ———— */
  const cartBody = $("[data-cart-body]");
  async function loadCart() {
    if (!cartBody) return;
    try {
      const res = await fetch(cartBody.dataset.url, { headers: AJAX, credentials: "same-origin" });
      cartBody.innerHTML = await res.text();
    } catch (err) {
      cartBody.innerHTML = `<p class="drawer__loading">${esc(T.cartError || "")} <a href="${esc(U.cart || "/savat/")}">${esc(T.cartPage || "")}</a></p>`;
    }
  }

  /* ———— Qidiruv ———— */
  const sInput = $("[data-search-input]");
  const sResults = $("[data-search-results]");
  if (sInput && sResults) {
    const hints = sResults.innerHTML;
    let active = -1;
    let seq = 0;
    const run = debounce(async () => {
      const q = sInput.value.trim();
      active = -1;
      if (q.length < 2) { sResults.innerHTML = hints; return; }
      const my = ++seq;
      try {
        const res = await fetch(`${sInput.dataset.url}?q=${encodeURIComponent(q)}`, { headers: AJAX });
        const data = await res.json();
        if (my !== seq) return;
        if (!data.items.length) {
          sResults.innerHTML = `<p class="suggest__none">${esc(tpl(T.notFound, { q }))}</p>` + hints;
          return;
        }
        sResults.innerHTML = '<div class="suggest">' + data.items.map((it) => `
          <a class="suggest__item" href="${esc(it.url)}">
            <img src="${esc(it.img)}" alt="" width="64" height="64">
            <span><small>${esc(it.brand)}</small><b>${esc(it.title)}</b>
            ${it.old_price ? `<s>${esc(it.old_price)}</s><span class="is-sale">${esc(it.price)}</span>` : `<span>${esc(it.price)}</span>`}</span>
          </a>`).join("") + "</div>" +
          '<div class="suggest__all">' +
          (data.total ? `<a class="link-arrow" href="${esc(U.catalog || "/katalog/")}?q=${encodeURIComponent(q)}">${esc(tpl(T.allResults, { n: data.total }))} <svg class="i"><use href="#i-arrow"/></svg></a>` : "") +
          (data.straps_total ? `<a class="link-arrow" href="${esc(data.straps_url)}">${esc(tpl(T.strapResults, { n: data.straps_total }))} <svg class="i"><use href="#i-arrow"/></svg></a>` : "") +
          "</div>";
      } catch (err) { /* tarmoq xatosi — Enter bilan katalogga o‘tish ishlayveradi */ }
    }, 220);
    sInput.addEventListener("input", run);
    sInput.addEventListener("keydown", (e) => {
      const items = $$(".suggest__item", sResults);
      if (!items.length || !["ArrowDown", "ArrowUp", "Enter"].includes(e.key)) return;
      if (e.key === "Enter") {
        if (active >= 0) { e.preventDefault(); location.href = items[active].href; }
        return;
      }
      e.preventDefault();
      active = (active + (e.key === "ArrowDown" ? 1 : -1) + items.length) % items.length;
      items.forEach((it, i) => it.classList.toggle("is-active", i === active));
      items[active].scrollIntoView({ block: "nearest" });
    });
  }

  /* ———— Katalog filtri ———— */
  const catalog = $("[data-catalog]");
  if (catalog) initCatalog();

  function initCatalog() {
    const panel = $(".filters", catalog);
    const toggle = () => $("[data-filter-toggle]", catalog);

    function syncToggle() {
      const btn = toggle();
      if (btn) btn.setAttribute("aria-expanded", desktop.matches ? String(!html.classList.contains("filters-off")) : "false");
    }
    syncToggle();

    catalog.addEventListener("click", (e) => {
      if (!e.target.closest("[data-filter-toggle]")) return;
      if (desktop.matches) {
        const off = html.classList.toggle("filters-off");
        store.set("oclock.filters", off ? "0" : "1");
        syncToggle();
      } else {
        open("filters");
      }
    });
    desktop.addEventListener?.("change", () => { if (desktop.matches && openDrawer === panel) close(); syncToggle(); });

    const getForm = () => $("[data-filter-form]", catalog);

    function urlFromForm() {
      const fd = new FormData(getForm());
      const params = new URLSearchParams();
      for (const [k, v] of fd) if (String(v).trim() !== "") params.append(k, v);
      params.delete("sahifa");
      const qs = params.toString();
      return location.pathname + (qs ? `?${qs}` : "");
    }

    let seq = 0;
    async function load(url, { push = true, replaceForm = false, scroll = false } = {}) {
      const my = ++seq;
      const results = $("[data-results]", catalog);
      results.classList.add("is-loading");
      panel.classList.add("is-loading");
      try {
        const res = await fetch(url, { headers: AJAX, credentials: "same-origin" });
        const doc = parse(await res.text());
        if (my !== seq) return;
        const freshResults = $("[data-results]", doc);
        const freshForm = $("[data-filter-form]", doc);
        if (!freshResults || !freshForm) { location.href = url; return; }
        results.replaceWith(freshResults);
        if (replaceForm) {
          const openKeys = new Set($$("details[open]", getForm()).map((d) => d.dataset.facet).filter(Boolean));
          getForm().replaceWith(freshForm);
          $$("details[data-facet]", freshForm).forEach((d) => { if (openKeys.has(d.dataset.facet)) d.open = true; });
          initForm();
        } else {
          updateCounts(freshForm);
        }
        const title = $("title", doc)?.textContent;
        if (title) document.title = title;
        const h1 = $(".page-title"), freshH1 = $(".page-title", doc);
        if (h1 && freshH1) h1.textContent = freshH1.textContent;
        if (push) history.pushState({ catalog: true }, "", url);
        else history.replaceState({ catalog: true }, "", url);
        syncToggle();
        if (scroll) {
          const top = catalog.getBoundingClientRect().top + window.scrollY - (header?.offsetHeight || 0) - 12;
          if (window.scrollY > top) window.scrollTo({ top, behavior: "smooth" });
        }
      } catch (err) {
        location.href = url;
      } finally {
        if (my === seq) {
          $("[data-results]", catalog)?.classList.remove("is-loading");
          panel.classList.remove("is-loading");
        }
      }
    }

    // Formadagi variantlar soni va «ko‘rsatish» tugmasidagi raqamni yangilaydi
    function updateCounts(freshForm) {
      const form = getForm();
      $$("[data-count]", freshForm).forEach((n) => {
        const cur = $(`[data-count="${CSS.escape(n.dataset.count)}"]`, form);
        if (!cur) return;
        cur.textContent = n.textContent;
        const opt = cur.closest(".opt");
        const freshOpt = n.closest(".opt");
        if (opt && freshOpt) opt.classList.toggle("is-empty", freshOpt.classList.contains("is-empty"));
      });
      $$("[data-facet]", form).forEach((d) => {
        const n = $$("input:checked", d).length;
        const sel = $("[data-sel]", d);
        if (sel) sel.textContent = n || "";
      });
      const total = $("[data-result-count]", freshForm)?.textContent;
      if (total != null) $$("[data-result-count]", form).forEach((el) => { el.textContent = total; });
    }

    const apply = debounce(() => load(urlFromForm(), { push: false }), 280);

    function initForm() {
      const form = getForm();
      initRange(form, apply);
      // «Yana N ta» tugmasi
      $$("[data-more]", form).forEach((btn) => {
        btn.addEventListener("click", () => {
          const opts = btn.previousElementSibling;
          const expanded = opts.classList.toggle("is-expanded");
          btn.dataset.label = btn.dataset.label || btn.textContent;
          btn.textContent = expanded ? (T.collapse || "Yig‘ish") : btn.dataset.label;
        });
      });
      // Brendlar ro‘yxatida qidirish
      $$("[data-facet-search]", form).forEach((inp) => {
        inp.addEventListener("input", () => {
          const q = inp.value.trim().toLowerCase();
          const opts = inp.nextElementSibling;
          opts.classList.toggle("is-searching", !!q);
          $$(".opt", opts).forEach((o) => o.classList.toggle("is-filtered", !!q && !o.textContent.toLowerCase().includes(q)));
        });
      });
    }
    initForm();

    catalog.addEventListener("change", (e) => {
      const el = e.target;
      if (el.matches("[data-no-auto]")) return;
      if (el.form && el.form === getForm()) apply();
    });
    catalog.addEventListener("submit", (e) => {
      if (!e.target.matches("[data-filter-form]")) return;
      e.preventDefault();
      load(urlFromForm(), { push: true });
      if (!desktop.matches) close();
    });
    // Chiplar, sahifalar va «tozalash» havolalari — sahifani yangilamasdan
    catalog.addEventListener("click", (e) => {
      const a = e.target.closest(".chip, .pagination a, .filters__foot a, .empty a");
      if (!a || e.metaKey || e.ctrlKey || e.shiftKey) return;
      e.preventDefault();
      const url = new URL(a.getAttribute("href"), location.href);
      load(url.pathname + url.search, { push: true, replaceForm: true, scroll: !!a.closest(".pagination") });
    });
    window.addEventListener("popstate", () => load(location.pathname + location.search, { push: false, replaceForm: true }));
  }

  /* ———— Narx oralig‘i (ikki tutqichli slayder) ———— */
  function initRange(root, onCommit) {
    $$("[data-range]", root).forEach((box) => {
      const lo = Number(box.dataset.lo) || 0;
      const hi = Number(box.dataset.hi) || 0;
      if (hi <= lo) { $(".range__track", box).hidden = true; return; }
      const [minInp, maxInp] = $$('input[type="number"]', box);
      const sMin = $("[data-range-min]", box);
      const sMax = $("[data-range-max]", box);
      const fill = $("[data-range-fill]", box);
      // Narxlar keng oraliqda, shuning uchun slayder logarifmik
      const toVal = (p) => {
        const v = Math.exp(Math.log(lo || 1) + (Math.log(hi) - Math.log(lo || 1)) * (p / 1000));
        const step = v > 5e6 ? 100000 : v > 1e6 ? 50000 : 10000;
        return Math.round(v / step) * step;
      };
      const toPos = (v) => {
        if (!v) return null;
        const p = ((Math.log(Math.max(v, lo || 1)) - Math.log(lo || 1)) / (Math.log(hi) - Math.log(lo || 1))) * 1000;
        return Math.max(0, Math.min(1000, p));
      };
      const paint = () => {
        fill.style.left = `${sMin.value / 10}%`;
        fill.style.right = `${100 - sMax.value / 10}%`;
      };
      const fromInputs = () => {
        sMin.value = toPos(Number(minInp.value)) ?? 0;
        sMax.value = toPos(Number(maxInp.value)) ?? 1000;
        paint();
      };
      fromInputs();
      const onSlide = (which) => {
        if (Number(sMin.value) > Number(sMax.value) - 20) {
          if (which === "min") sMin.value = Number(sMax.value) - 20; else sMax.value = Number(sMin.value) + 20;
        }
        minInp.value = Number(sMin.value) <= 0 ? "" : toVal(sMin.value);
        maxInp.value = Number(sMax.value) >= 1000 ? "" : toVal(sMax.value);
        paint();
      };
      sMin.addEventListener("input", () => onSlide("min"));
      sMax.addEventListener("input", () => onSlide("max"));
      sMin.addEventListener("change", onCommit);
      sMax.addEventListener("change", onCommit);
      minInp.addEventListener("input", fromInputs);
      maxInp.addEventListener("input", fromInputs);
    });
  }

  /* ———— Soat sahifasi: kattalashtirish va bo‘limlar ———— */
  $$("[data-zoom]").forEach((box) => {
    const img = $("img", box);
    box.addEventListener("mousemove", (e) => {
      const r = box.getBoundingClientRect();
      img.style.setProperty("--zx", `${((e.clientX - r.left) / r.width) * 100}%`);
      img.style.setProperty("--zy", `${((e.clientY - r.top) / r.height) * 100}%`);
    });
    box.addEventListener("mouseenter", () => { if (window.matchMedia("(hover: hover)").matches) box.classList.add("is-zoom"); });
    box.addEventListener("mouseleave", () => box.classList.remove("is-zoom"));
  });

  $$("[data-tabs]").forEach((wrap) => {
    const tabs = $$('[role="tab"]', wrap);
    const select = (tab) => {
      tabs.forEach((t) => {
        const on = t === tab;
        t.setAttribute("aria-selected", String(on));
        t.tabIndex = on ? 0 : -1;
        $(`#${t.getAttribute("aria-controls")}`).hidden = !on;
      });
    };
    tabs.forEach((t, i) => {
      t.addEventListener("click", () => select(t));
      t.addEventListener("keydown", (e) => {
        if (e.key !== "ArrowRight" && e.key !== "ArrowLeft") return;
        const next = tabs[(i + (e.key === "ArrowRight" ? 1 : -1) + tabs.length) % tabs.length];
        select(next); next.focus();
      });
    });
  });

  // Yetkazib berish muddati viloyatga qarab
  $$("[data-region-days]").forEach((sel) => {
    const out = $(sel.dataset.regionDays);
    let days = {};
    try { days = JSON.parse($("#region-days")?.textContent || "{}"); } catch (e) { /* bo‘sh */ }
    const show = () => {
      if (!out) return;
      const d = days[sel.value];
      out.hidden = !d;
      if (d) $("[data-days]", out).textContent = d;
    };
    sel.addEventListener("change", show);
    show();
  });

  /* ———— Telefon raqami: +998 90 123 45 67 ———— */
  $$('input[inputmode="tel"]').forEach((inp) => {
    inp.addEventListener("focus", () => { if (!inp.value) inp.value = "+998 "; });
    inp.addEventListener("blur", () => { if (inp.value.trim() === "+998") inp.value = ""; });
    inp.addEventListener("input", () => {
      let d = inp.value.replace(/\D/g, "");
      if (!d.startsWith("998")) d = "998" + d.replace(/^998/, "");
      d = d.slice(0, 12);
      const parts = [d.slice(0, 3), d.slice(3, 5), d.slice(5, 8), d.slice(8, 10), d.slice(10, 12)].filter(Boolean);
      inp.value = "+" + parts.join(" ");
    });
  });
})();
