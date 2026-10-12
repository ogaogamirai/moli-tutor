// Headless check that material_bridge.js anchors to headings by index and by
// whitespace-normalized text. Needs no browser and no npm deps.
// Run:  node tests/bridge_anchor_check.mjs
import fs from "node:fs";
import { fileURLToPath } from "node:url";
import path from "node:path";

const here = path.dirname(fileURLToPath(import.meta.url));
const code = fs.readFileSync(path.join(here, "..", "static", "material_bridge.js"), "utf8");

const HL = "ai-tutor-highlight";

function makeEl(tag, text) {
  const classes = new Set();
  return {
    tagName: String(tag).toUpperCase(),
    textContent: text || "",
    innerText: text || "",
    style: {},
    scrolled: false,
    classList: {
      add(c) { classes.add(c); },
      remove(c) { classes.delete(c); },
      contains(c) { return classes.has(c); },
      toggle() {},
    },
    scrollIntoView() { this.scrolled = true; },
    appendChild() {},
    replaceChild() {},
    insertBefore() {},
    normalize() {},
    parentElement: null,
    getAttribute() { return null; },
    setAttribute() {},
  };
}

const headings = [
  makeEl("h1", "はじめに"),
  makeEl("h2", "第 2 章   発想の転換"),
  makeEl("h3", "2.1 トロピカル半環"),
];

const document = {
  getElementById() { return null; },
  createElement(tag) { return makeEl(tag, ""); },
  querySelectorAll(sel) {
    if (/h1/.test(sel)) return headings;
    if (sel === "." + HL) return headings.filter((h) => h.classList.contains(HL));
    return [];
  },
  head: makeEl("head"),
  documentElement: makeEl("html"),
  body: makeEl("body"),
};
const window = { addEventListener() {} };
const NodeFilter = { SHOW_TEXT: 4 };

let api;
try {
  new Function("window", "document", "NodeFilter", code)(window, document, NodeFilter);
  api = window.moliTutor;
} catch (e) {
  console.log("FAIL bridge threw: " + e.message);
  process.exit(1);
}

let ok = true;
function assert(name, cond) {
  console.log((cond ? "PASS " : "FAIL ") + name);
  if (!cond) ok = false;
}

assert("api exposed", !!api && typeof api.highlightAndScroll === "function");
assert("collectHeadings returns 3", api.collectHeadings().length === 3);

const r1 = api.scrollToHeadingIndex(1, {});
assert(
  "scrollToHeadingIndex(1) -> heading_index",
  r1.success && r1.method === "heading_index" && r1.index === 1
);
assert("heading[1] scrolled", headings[1].scrolled === true);

const r2 = api.highlightAndScroll(null, { heading_index: 0 });
assert("highlightAndScroll heading_index 0 succeeds", r2.success && r2.method === "heading_index");

const r3 = api.highlightAndScroll("x", { heading_index: 99 });
assert("heading_index out-of-bounds fails", r3.success === false && r3.reason === "heading_index_oob");

const r4 = api.highlightAndScroll("第 2 章 発想の転換", { match: "heading" });
assert("whitespace-normalized heading match", r4.success && r4.method === "heading");

const r5 = api.highlightAndScroll("存在しない見出し", { match: "heading" });
assert("match:heading not found fails", r5.success === false && r5.reason === "heading_not_found");

process.exit(ok ? 0 : 1);
