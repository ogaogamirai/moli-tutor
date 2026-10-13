#!/usr/bin/env python3
"""Moli-Tutor Phase 1–2 — Aether型コックピット + AI Tutor 状態連動。"""
from __future__ import annotations

import argparse
import json
import threading
import time
from pathlib import Path

import webview

from tutor_http import serve

import subprocess
import hashlib
import html

ROOT = Path(__file__).resolve().parent
STATIC = ROOT / "static"
DEFAULT_STATE = ROOT / "tutor_state.json"
SHELL_BUILD = "17"
DEFAULT_MATERIAL = Path(r"G:\マイドライブ\Projects\Teaching-materials\tropical-math")
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
    raw_state = json.loads(text)
    return _preprocess_state(raw_state)


def _state_watcher(window: webview.Window, state_path: Path, interval: float) -> None:
    last_mtime: float | None = None
    last_payload: str | None = None
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
        except (json.JSONDecodeError, OSError):
            pass
        time.sleep(interval)


def main() -> None:
    parser = argparse.ArgumentParser(description="Moli-Tutor コックピット")
    parser.add_argument(
        "--state",
        type=Path,
        default=DEFAULT_STATE,
        help="監視する tutor_state.json",
    )
    parser.add_argument("--poll-ms", type=int, default=250, help="状態ファイルのポーリング間隔")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8777, help="shell + 教材の同一オリジン HTTP ポート")
    parser.add_argument(
        "--material-dir",
        type=Path,
        action="append",
        default=None,
        help="教材を /material/ 以下で配信（複数指定可。既定: リポジトリの materials/ と tropical-math）",
    )
    parser.add_argument(
        "--browser",
        action="store_true",
        help="pywebview GUI ではなく通常ブラウザで開く",
    )
    args = parser.parse_args()
    state_path = args.state.resolve()

    if not (STATIC / "shell.html").is_file():
        raise SystemExit(f"shell が見つかりません: {STATIC / 'shell.html'}")

    material_roots: list[Path] = []
    library = ROOT / "materials"
    if library.is_dir():
        material_roots.append(library)
    for d in args.material_dir or [DEFAULT_MATERIAL]:
        if d and d.is_dir():
            material_roots.append(d)
    serve(STATIC, material_roots, args.host, args.port, state_callback=lambda: _load_state(state_path))
    shell_url = f"http://{args.host}:{args.port}/shell.html?b={SHELL_BUILD}&t={int(time.time())}"

    if args.browser:
        import webbrowser
        print(f"[moli-tutor] Opening in browser: {shell_url}", flush=True)
        webbrowser.open(shell_url)
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            return

    try:
        window = webview.create_window(
            "Moli-Tutor",
            url=shell_url,
            width=1400,
            height=900,
            resizable=True,
        )

        def on_loaded() -> None:
            time.sleep(1.2)
            try:
                state = _load_state(state_path)
                payload = json.dumps(state, ensure_ascii=False)
                window.evaluate_js(f"window.applyState({payload})")
            except (json.JSONDecodeError, OSError):
                pass
            t = threading.Thread(
                target=_state_watcher,
                args=(window, state_path, args.poll_ms / 1000.0),
                daemon=True,
            )
            t.start()

        window.events.loaded += on_loaded
        webview.start(gui="edgechromium")
    except Exception as e:
        import webbrowser
        print(f"[moli-tutor] GUI launch failed ({e}), falling back to browser...", flush=True)
        webbrowser.open(shell_url)
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            return


if __name__ == "__main__":
    main()
