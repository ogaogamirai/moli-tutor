// 教材 iframe 内 — スクロール・ハイライト（単一 / 複数 / 自由スクロール）
(function () {
  "use strict";

  const HL_CLASS = "ai-tutor-highlight";

  function normalizeText(s) {
    return String(s == null ? "" : s).replace(/\s+/g, " ").trim();
  }

  function collectHeadings() {
    return Array.from(document.querySelectorAll("h1, h2, h3, h4, h5, h6, [role='heading']"));
  }

  function applyHighlightEl(el, heading) {
    el.classList.add(HL_CLASS);
    el.style.backgroundColor = "#fde047";
    el.style.color = "#713f12";
    el.style.padding = heading ? "6px 10px" : "3px 6px";
    el.style.borderRadius = "6px";
    el.style.boxShadow = "0 0 0 4px #facc15, 0 0 24px rgba(250, 204, 21, 0.85)";
    el.style.outline = "2px solid #ea580c";
    el.style.animation = "moli-tutor-pulse 1.2s ease-in-out 4";
  }

  (function injectPulseStyle() {
    if (document.getElementById("moli-tutor-pulse-style")) return;
    const st = document.createElement("style");
    st.id = "moli-tutor-pulse-style";
    st.textContent =
      "@keyframes moli-tutor-pulse { 0%,100%{filter:brightness(1)} 50%{filter:brightness(1.35)} }";
    (document.head || document.documentElement).appendChild(st);
  })();

  function clearAllHighlights() {
    document.querySelectorAll("." + HL_CLASS).forEach((el) => {
      if (el.tagName === "SPAN") {
        const parent = el.parentElement;
        if (parent) {
          parent.replaceChild(document.createTextNode(el.textContent || ""), el);
          parent.normalize();
        }
      } else {
        el.classList.remove(HL_CLASS);
        el.style.backgroundColor = "";
        el.style.color = "";
        el.style.padding = "";
        el.style.borderRadius = "";
        el.style.boxShadow = "";
        el.style.outline = "";
      }
    });
    const legacy = document.getElementById("ai-tutor-highlight-target");
    if (legacy) legacy.removeAttribute("id");
  }

  function isSkippableNode(node) {
    const parent = node.parentElement;
    if (!parent) return true;
    if (["SCRIPT", "STYLE", "NOSCRIPT"].includes(parent.tagName)) return true;
    if (parent.closest("." + HL_CLASS)) return true;
    return false;
  }

  function highlightNextTextMatch(targetText) {
    const walker = document.createTreeWalker(document.body, NodeFilter.SHOW_TEXT, null, false);
    let node;
    while ((node = walker.nextNode())) {
      if (!node.nodeValue || !node.nodeValue.includes(targetText)) continue;
      if (isSkippableNode(node)) continue;

      const span = document.createElement("span");
      applyHighlightEl(span, false);
      const parts = node.nodeValue.split(targetText);
      const before = document.createTextNode(parts[0]);
      const match = document.createTextNode(targetText);
      const after = document.createTextNode(parts.slice(1).join(targetText));
      span.appendChild(match);
      const parent = node.parentElement;
      parent.replaceChild(after, node);
      parent.insertBefore(span, after);
      parent.insertBefore(before, span);
      return { success: true, element: span, method: "text" };
    }
    return { success: false };
  }

  function highlightAllHeadings(targetText) {
    const needle = normalizeText(targetText);
    if (!needle) return [];
    const hits = [];
    collectHeadings().forEach((h) => {
      const text = normalizeText(h.innerText || h.textContent || "");
      if (!text || !text.includes(needle)) return;
      if (h.classList.contains(HL_CLASS)) return;
      applyHighlightEl(h, true);
      hits.push(h);
    });
    return hits;
  }

  function scrollToHeadingIndex(index, options) {
    const headings = collectHeadings();
    const el = headings[index];
    if (!el) return { success: false, reason: "heading_index_oob", count: headings.length };
    clearAllHighlights();
    applyHighlightEl(el, true);
    el.scrollIntoView({ behavior: behaviorOf(options), block: "start" });
    return { success: true, method: "heading_index", index, count: headings.length };
  }

  function highlightAndScroll(targetText, options) {
    if (options && options.heading_index != null) {
      return scrollToHeadingIndex(Number(options.heading_index), options);
    }
    const match = (options && options.match) || "first";
    const occurrence = options && options.occurrence != null ? options.occurrence : 0;
    if (!targetText) return { success: false, reason: "empty" };

    clearAllHighlights();

    if (match === "all") {
      const headings = highlightAllHeadings(targetText);
      let textCount = 0;
      let firstEl = headings[0] || null;
      while (true) {
        const r = highlightNextTextMatch(targetText);
        if (!r.success) break;
        textCount += 1;
        if (!firstEl) firstEl = r.element;
      }
      const total = headings.length + textCount;
      if (total === 0) return { success: false, reason: "not_found", count: 0 };
      const focusList = [...headings, ...document.querySelectorAll("span." + HL_CLASS)];
      const focus = focusList[occurrence] || firstEl || focusList[0];
      if (focus) focus.scrollIntoView({ behavior: behaviorOf(options), block: "center" });
      return { success: true, method: "all", count: total };
    }

    if (match === "heading") {
      const headingHits = highlightAllHeadings(targetText);
      if (!headingHits.length) return { success: false, reason: "heading_not_found", count: 0 };
      const focus = headingHits[occurrence] || headingHits[0];
      focus.scrollIntoView({ behavior: behaviorOf(options), block: "center" });
      return { success: true, method: "heading", count: headingHits.length };
    }

    const headings = highlightAllHeadings(targetText);
    if (headings.length) {
      const focus = headings[occurrence] || headings[0];
      focus.scrollIntoView({ behavior: behaviorOf(options), block: "center" });
      return { success: true, method: "heading", count: headings.length };
    }

    function unwrapSpan(span) {
      const parent = span.parentElement;
      if (!parent) return;
      parent.replaceChild(document.createTextNode(span.textContent || ""), span);
      parent.normalize();
    }

    let lastEl = null;
    for (let i = 0; i <= occurrence; i += 1) {
      const r = highlightNextTextMatch(targetText);
      if (!r.success) {
        return i === 0 ? { success: false, reason: "not_found" } : { success: false, reason: "occurrence_oob" };
      }
      if (i < occurrence) {
        unwrapSpan(r.element);
        continue;
      }
      lastEl = r.element;
    }
    if (lastEl) lastEl.scrollIntoView({ behavior: behaviorOf(options), block: "center" });
    return { success: true, method: "text", count: 1, occurrence };
  }

  function behaviorOf(options) {
    return (options && options.behavior) || "smooth";
  }

  function scrollViewport(options) {
    const behavior = behaviorOf(options);
    const root = document.scrollingElement || document.documentElement;
    const max = Math.max(0, root.scrollHeight - root.clientHeight);
    let top = root.scrollTop;
    if (options && options.y_ratio != null) {
      top = max * Math.max(0, Math.min(1, Number(options.y_ratio)));
    } else if (options && options.y_px != null) {
      top = Math.max(0, Math.min(max, Number(options.y_px)));
    } else if (options && options.dy != null) {
      top = Math.max(0, Math.min(max, root.scrollTop + Number(options.dy)));
    } else {
      return { success: false, reason: "no_scroll_target" };
    }
    window.scrollTo({ top, behavior });
    return { success: true, method: "viewport", scrollTop: top };
  }

  function scrollToHash(hash, options) {
    if (!hash) return { success: false };
    const id = hash.replace(/^#/, "");
    const el = document.getElementById(id);
    if (el) {
      el.scrollIntoView({ behavior: behaviorOf(options), block: "start" });
      return { success: true, method: "hash" };
    }
    return { success: false, reason: "no_id" };
  }

  function highlightImage(index, options) {
    const imgs = document.querySelectorAll("img");
    const el = imgs[index];
    if (!el) return { success: false, reason: "image_index_oob", count: imgs.length };
    clearAllHighlights();
    el.classList.add(HL_CLASS);
    el.style.outline = "3px solid #ea580c";
    el.style.boxShadow = "0 0 0 6px #facc15, 0 0 28px rgba(250, 204, 21, 0.9)";
    el.style.borderRadius = "6px";
    el.scrollIntoView({ behavior: behaviorOf(options), block: "center" });
    return { success: true, method: "image", index, count: imgs.length };
  }

  // --- 画像ライトボックス（クリックで拡大・Esc/×/背景クリックで戻る）---
  let lightbox = null;

  function closeLightbox() {
    if (!lightbox) return;
    lightbox.remove();
    lightbox = null;
    document.removeEventListener("keydown", onLightboxKey);
  }

  function onLightboxKey(e) {
    if (e.key === "Escape") closeLightbox();
  }

  function openLightbox(src, alt) {
    if (!src) return { success: false, reason: "no_src" };
    closeLightbox();
    lightbox = document.createElement("div");
    lightbox.className = "moli-tutor-lightbox";
    const img = document.createElement("img");
    img.src = src;
    img.alt = alt || "";
    const close = document.createElement("button");
    close.className = "moli-tutor-lightbox-close";
    close.textContent = "✕ 閉じる (Esc)";
    lightbox.append(img, close);
    lightbox.addEventListener("click", (e) => {
      if (e.target === lightbox) closeLightbox();
    });
    close.addEventListener("click", closeLightbox);
    (document.body || document.documentElement).appendChild(lightbox);
    document.addEventListener("keydown", onLightboxKey);
    return { success: true, src };
  }

  (function injectLightboxStyle() {
    if (document.getElementById("moli-tutor-lb-style")) return;
    const st = document.createElement("style");
    st.id = "moli-tutor-lb-style";
    st.textContent =
      ".moli-tutor-lightbox{position:fixed;inset:0;z-index:2147483000;" +
      "background:rgba(15,23,42,.93);display:flex;align-items:center;justify-content:center;" +
      "padding:24px;cursor:zoom-out}" +
      ".moli-tutor-lightbox img{max-width:96%;max-height:92%;background:#fff;" +
      "box-shadow:0 10px 40px rgba(0,0,0,.6)}" +
      ".moli-tutor-lightbox-close{position:fixed;top:14px;right:18px;cursor:pointer;" +
      "background:#1e293b;color:#e2e8f0;border:1px solid #334155;border-radius:8px;" +
      "padding:8px 12px;font-size:14px;z-index:2147483001}";
    (document.head || document.documentElement).appendChild(st);
  })();

  // 画像（または画像を包むリンク）クリックを横取りして拡大表示。ナビゲーションで教材を失わない。
  if (typeof document.addEventListener === "function") {
    document.addEventListener(
      "click",
      (e) => {
        const t = e.target;
        if (!t || !t.tagName) return;
        let img = null;
        if (t.tagName === "IMG") img = t;
        else if (t.tagName === "A") img = t.querySelector("img");
        if (!img) return;
        e.preventDefault();
        e.stopPropagation();
        openLightbox(img.currentSrc || img.src, img.alt);
      },
      true
    );
  }

  const api = {
    highlightAndScroll,
    scrollViewport,
    scrollToHash,
    scrollToHeadingIndex,
    collectHeadings,
    clearAllHighlights,
    highlightImage,
    openImage: openLightbox,
    closeLightbox
  };
  window.moliTutor = api;

  window.addEventListener("message", (event) => {
    const data = event.data;
    if (!data || data.source !== "moli-tutor-shell") return;
    let result = { success: false };

    if (data.type === "scroll_to" && (data.target_text || data.heading_index != null)) {
      result = highlightAndScroll(data.target_text, {
        match: data.match,
        occurrence: data.occurrence,
        behavior: data.behavior,
        heading_index: data.heading_index
      });
    } else if (data.type === "scroll_viewport") {
      result = scrollViewport(data);
    } else if (data.type === "scroll_hash" && data.hash) {
      result = scrollToHash(data.hash, data);
    } else if (data.type === "clear_highlight") {
      clearAllHighlights();
      result = { success: true };
    } else if (data.type === "highlight_image" && data.index != null) {
      result = highlightImage(Number(data.index), data);
    }

    if (event.source && event.source.postMessage) {
      event.source.postMessage(
        { source: "moli-tutor-material", actionId: data.actionId, result },
        event.origin
      );
    }
  });
})();
