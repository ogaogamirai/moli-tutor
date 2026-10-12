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

  const api = {
    highlightAndScroll,
    scrollViewport,
    scrollToHash,
    scrollToHeadingIndex,
    collectHeadings,
    clearAllHighlights
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
    }

    if (event.source && event.source.postMessage) {
      event.source.postMessage(
        { source: "moli-tutor-material", actionId: data.actionId, result },
        event.origin
      );
    }
  });
})();
