// Headless check that shell.html's DAG map renders from a state.dag payload.
// Run:  node tests/shell_render_check.mjs [path/to/shell.html]
// Needs no browser and no npm deps: it evaluates the inline script with a tiny DOM shim.
import fs from "node:fs";
import { fileURLToPath } from "node:url";
import path from "node:path";

const here = path.dirname(fileURLToPath(import.meta.url));
const htmlPath = process.argv[2] || path.join(here, "..", "static", "shell.html");
const html = fs.readFileSync(htmlPath, "utf8");

const re = /<script(?![^>]*\bsrc=)[^>]*>([\s\S]*?)<\/script>/gi;
const scripts = [];
let m;
while ((m = re.exec(html))) scripts.push(m[1]);
if (!scripts.length) {
  console.log("FAIL no inline script found");
  process.exit(1);
}
const code = scripts.join("\n;\n");

function makeEl(tag) {
  return {
    tag,
    id: "",
    hidden: false,
    className: "",
    textContent: "",
    style: {},
    children: [],
    classList: { add() {}, remove() {}, toggle() {}, contains() { return false; } },
    setAttribute() {},
    getAttribute() { return null; },
    removeAttribute() {},
    appendChild(c) { this.children.push(c); return c; },
    append(...c) { this.children.push(...c); },
    insertBefore(c) { this.children.push(c); return c; },
    replaceChildren() { this.children = []; },
    addEventListener() {},
    removeEventListener() {},
    querySelector() { return null; },
    querySelectorAll() { return []; },
    getBoundingClientRect() { return { top: 0, height: 0 }; },
    scrollTo() {},
    scrollIntoView() {},
    contentWindow: null,
    contentDocument: null,
  };
}

const registry = new Map();
const document = {
  getElementById(id) {
    if (!registry.has(id)) registry.set(id, makeEl("#" + id));
    return registry.get(id);
  },
  createElement(tag) { return makeEl(tag); },
  querySelector() { return null; },
  querySelectorAll() { return []; },
  body: makeEl("body"),
  documentElement: makeEl("html"),
  head: makeEl("head"),
};
const window = { addEventListener() {}, location: { href: "http://x/", origin: "http://x" } };
const localStorage = { getItem() { return null; }, setItem() {}, removeItem() {} };

let api;
try {
  const fn = new Function(
    "window", "document", "localStorage", "setInterval",
    code + "\n;return { renderDagMap, jumpToDagNode, setLayout };"
  );
  api = fn(window, document, localStorage, () => 0);
} catch (e) {
  console.log("FAIL inline script threw: " + e.message);
  process.exit(1);
}

let ok = true;
function assert(name, cond) {
  console.log((cond ? "PASS " : "FAIL ") + name);
  if (!cond) ok = false;
}

const dag = [
  { id: "PRE_01", name: "前提: 用語", type: "prerequisite", status: "completed", target_text: "a" },
  { id: "KC_01", name: "1. 核心", type: "concept", status: "active", target_text: "b" },
  { id: "KC_02", name: "2. 境界", type: "concept", status: "pending", target_text: "c" },
];
api.renderDagMap(dag);

const list = registry.get("dag-list");
const wrap = registry.get("dag-map");
const prog = registry.get("dag-progress");
assert("dag-list rendered 3 nodes", !!list && list.children.length === 3);
assert("dag-map is visible when dag present", !!wrap && wrap.hidden === false);
assert("progress shows 1/3 完了", !!prog && prog.textContent === "1/3 完了");
assert("first node is completed", list && list.children[0].className.includes("completed"));
assert("second node is active", list && list.children[1].className.includes("active"));

api.renderDagMap([]);
assert("empty dag hides the map", registry.get("dag-map").hidden === true);

process.exit(ok ? 0 : 1);
