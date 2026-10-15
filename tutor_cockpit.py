#!/usr/bin/env python3
"""Moli-Tutor Phase 1–2 — サーバー無しコックピット（pywebview + ローカルファイル）。

- ローカルファイルを file:// で開く（HTTP サーバー・待受ポート無し）。
- 教材 HTML と bridge は Python が読み、js_api 経由で shell に渡す（shell は fetch しない）。
- 状態は tutor_state.json を監視し evaluate_js で反映（live 更新）。
"""
from __future__ import annotations

import argparse
import json
import os
import re
import threading
import time
from pathlib import Path
from urllib.parse import unquote

import webview

import subprocess
import hashlib
import html

ROOT = Path(__file__).resolve().parent
STATIC = ROOT / "static"
DEFAULT_STATE = ROOT / "tutor_state.json"
SHELL_HTML = STATIC / "shell.html"
BRIDGE_JS = STATIC / "material_bridge.js"
SHELL_BUILD = "18"

# 教材のルート（この下に <material_id>/ が並ぶ）
MATERIAL_ROOTS = [
    ROOT / "materials",
    ROOT / "demo-material",
    Path(r"G:\マイドライブ\Projects\Teaching-materials"),
]
DEFAULT_MATERIAL_ID = "tropical-math"

D2_EXE = ROOT.parent / "d2" / "d2.exe"

_D2_CACHE: dict[str, str] = {}


def _render_d2_to_svg(d2_text: str) -> str:
    """Compile D2 text to SVG using Tools/d2/d2.exe in ~0.04s."""
    if not d2_text or not d2_text.strip():
        return ""
    code_hash = hashlib.sha256(d2_text.encode("utf-8")).hexdigest()
    if code_hash in _D2_CACHE:
        return _D2_CACHE[code_hash]

    if not D2_EXE.is_file():
        return f'<div style="color:#ef4444;padding:8px;border:1px solid #dc2626;border-radius:4px;">D2 binary not found: {html.escape(str(D2_EXE))}</div>'

    try:
        proc = subprocess.run(
            [str(D2_EXE), "-", "-"],
            input=d2_text.encode("utf-8"),
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
            timeout=5.0,
        )
        if proc.returncode == 0:
            svg = proc.stdout.decode("utf-8", errors="replace")
            _D2_CACHE[code_hash] = svg
            return svg
        else:
            err = proc.stderr.decode("utf-8", errors="replace")
            return f'<div style="color:#ef4444;background:#1e1e2e;padding:12px;border:1px solid #ef4444;border-radius:6px;font-family:monospace;white-space:pre-wrap;">D2 Compile Error:\n{html.escape(err)}</div>'
    except Exception as e:
        return f'<div style="color:#ef4444;padding:8px;">D2 Execution Error: {html.escape(str(e))}</div>'


def _preprocess_state(state: dict) -> dict:
    """Preprocess state to convert D2 code into SVG while preserving d2_source."""
    processed = json.loads(json.dumps(state))

    if "sections" in processed and isinstance(processed["sections"], list):
        for sec in processed["sections"]:
            if isinstance(sec, dict) and sec.get("type") == "d2":
                raw_d2 = sec.get("content", "")
                sec["d2_source"] = raw_d2
                sec["content"] = _render_d2_to_svg(raw_d2)

    if "d2" in processed and isinstance(processed["d2"], str):
        raw_d2 = processed["d2"]
        processed["d2_source"] = raw_d2
        d2_svg = _render_d2_to_svg(raw_d2)
        processed["d2_svg"] = d2_svg
        if not processed.get("svg"):
            processed["svg"] = d2_svg

    return processed


def _load_state(path: Path) -> dict:
    text = path.read_text(encoding="utf-8-sig")
    return _preprocess_state(json.loads(text))


def read_text(path: Path) -> str:
    data = path.read_bytes()
    for enc in ("utf-8-sig", "utf-8", "cp932"):
        try:
            return data.decode(enc)
        except Exception:
            pass
    return data.decode("utf-8", "replace")


def to_file_url(path: Path) -> str:
    return "file:///" + path.resolve().as_posix()


def parse_material_url(url: str) -> tuple[str | None, str]:
    """URL/パスから (material_id, file) を取り出す。"""
    u = (url or "").replace("\\", "/")
    m = re.search(r"/material/([^/]+)/(.+)$", u)
    if m:
        return unquote(m.group(1)), unquote(m.group(2))
    m = re.search(r"/materials/([^/]+)/(.+)$", u)
    if m:
        return unquote(m.group(1)), unquote(m.group(2))
    p = Path(u)
    if p.is_file():
        return p.parent.name, p.name
    return None, "index.html"


class Api:
    def __init__(self, state_path: Path, roots: list[Path]):
        self.state_path = state_path
        self.roots = [r for r in roots if r]
        self._result: dict | None = None
        self.done = threading.Event()

    # --- shell へ渡す読み取り API ---
    def get_bridge(self) -> str:
        return read_text(BRIDGE_JS)

    def get_state(self) -> dict:
        try:
            return _load_state(self.state_path)
        except Exception:
            return {}

    def get_material(self, material_id: str | None = None, file: str = "index.html") -> dict:
        state = self.get_state()
        mid = material_id or state.get("material_id") or DEFAULT_MATERIAL_ID
        fname = file or "index.html"
        for root in self.roots:
            p = root / mid / fname
            if p.is_file():
                return {
                    "ok": True,
                    "material_id": mid,
                    "file": fname,
                    "html": read_text(p),
                    "base": to_file_url(p.parent) + "/",
                    "path": str(p),
                    "url": f"/material/{mid}/{fname}",
                }
        return {"ok": False, "material_id": mid, "file": fname, "error": "material_not_found"}

    def open_material_url(self, url: str) -> dict:
        mid, fname = parse_material_url(url)
        return self.get_material(mid, fname)

    # --- 自己テスト用 ---
    def report(self, data) -> bool:
        self._result = data
        self.done.set()
        return True


def _push_material(window, api: Api, material_id: str | None) -> None:
    m = api.get_material(material_id)
    if m.get("ok"):
        payload = json.dumps(m, ensure_ascii=False)
        window.evaluate_js(f"window.__applyMaterial({payload})")


def _state_watcher(window, api: Api, state_path: Path, interval: float) -> None:
    last_mtime: float | None = None
    last_payload: str | None = None
    last_material: str | None = None
    while True:
        try:
            if not state_path.is_file():
                time.sleep(interval)
                continue
            mtime = state_path.stat().st_mtime
            if last_mtime is not None and mtime == last_mtime:
                time.sleep(interval)
                continue
            last_mtime = mtime
            state = _load_state(state_path)
            payload = json.dumps(state, ensure_ascii=False)
            if payload != last_payload:
                last_payload = payload
                window.evaluate_js(f"window.applyState({payload})")
            mid = state.get("material_id")
            if mid and mid != last_material:
                last_material = mid
                _push_material(window, api, mid)
        except (json.JSONDecodeError, OSError):
            pass
        time.sleep(interval)


def run(state_path: Path, poll_ms: int, selftest: bool) -> int:
    api = Api(state_path, MATERIAL_ROOTS)

    window = webview.create_window(
        "Moli-Tutor",
        url=str(SHELL_HTML),
        js_api=api,
        width=1400,
        height=900,
        resizable=True,
    )

    def on_loaded() -> None:
        time.sleep(1.0)
        try:
            state = _load_state(state_path)
            window.evaluate_js(f"window.applyState({json.dumps(state, ensure_ascii=False)})")
            _push_material(window, api, state.get("material_id"))
        except (json.JSONDecodeError, OSError):
            pass
        threading.Thread(
            target=_state_watcher,
            args=(window, api, state_path, poll_ms / 1000.0),
            daemon=True,
        ).start()
        if selftest:
            threading.Thread(target=_selftest, args=(window, api), daemon=True).start()

    window.events.loaded += on_loaded
    webview.start(gui="edgechromium")
    return 0


SELFTEST_JS = r"""
(function(){
  var out={};
  try{
    var f = document.getElementById('material');
    var doc = f.contentDocument, win = f.contentWindow;
    out.sameOrigin = !!(doc && doc.body);
    out.materialUrl = f.getAttribute('src') ? f.getAttribute('src') : '(srcdoc)';
    out.usedSrcdoc = !!f.srcdoc;
    var api = win && win.moliTutor;
    out.hasApi = !!api;
    if (api) {
      out.headings = api.collectHeadings().length;
      out.highlight = api.highlightAndScroll('', { heading_index: 5, behavior: 'auto' });
      out.scroll = api.scrollViewport({ y_ratio: 0.5, behavior: 'auto' });
      out.image = api.highlightImage(1, { behavior: 'auto' });
      var imgs = doc.querySelectorAll('img');
      out.imgCount = imgs.length;
      out.lightbox = (function(){ var i=doc.querySelector('img'); if(!i) return null; i.click(); var lb=!!doc.querySelector('.moli-tutor-lightbox'); var c=doc.querySelector('.moli-tutor-lightbox-close'); if(c) c.click(); return {opened:lb, closed: !doc.querySelector('.moli-tutor-lightbox')}; })();
    }
    out.dag = (window.__lastDagCount || 0);
    out.ok = out.sameOrigin && out.hasApi;
  }catch(e){ out.error = String(e); out.ok = false; }
  window.pywebview.api.report(out);
  return true;
})()
"""


def _selftest(window, api: Api) -> None:
    time.sleep(3.0)
    try:
        window.evaluate_js(SELFTEST_JS)
    except Exception as exc:
        window.evaluate_js("window.pywebview.api.report({ok:false,error:%r})" % ("selftest_failed:" + str(exc),))
    api.done.wait(timeout=10)
    out = os.path.join(str(ROOT), "_spike", "serverless_selftest.json")
    os.makedirs(os.path.dirname(out), exist_ok=True)
    with open(out, "w", encoding="utf-8") as fh:
        json.dump(api._result or {"ok": False, "error": "no_result"}, fh, ensure_ascii=False, indent=2)
    try:
        window.destroy()
    except Exception:
        pass
    os._exit(0)


def main() -> int:
    parser = argparse.ArgumentParser(description="Moli-Tutor コックピット（サーバー無し）")
    parser.add_argument("--state", type=Path, default=DEFAULT_STATE, help="監視する tutor_state.json")
    parser.add_argument("--poll-ms", type=int, default=250, help="状態ファイルのポーリング間隔")
    parser.add_argument("--selftest", action="store_true", help="読み込み後に DOM 自己テストして終了")
    args = parser.parse_args()
    if not SHELL_HTML.is_file():
        raise SystemExit(f"shell が見つかりません: {SHELL_HTML}")
    return run(args.state.resolve(), args.poll_ms, args.selftest)


if __name__ == "__main__":
    raise SystemExit(main())
