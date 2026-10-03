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

ROOT = Path(__file__).resolve().parent
STATIC = ROOT / "static"
DEFAULT_STATE = ROOT / "tutor_state.json"
SHELL_BUILD = "9"
DEFAULT_MATERIAL = Path(r"G:\マイドライブ\Projects\Teaching-materials\tropical-math")


def _load_state(path: Path) -> dict:
    text = path.read_text(encoding="utf-8")
    return json.loads(text)


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
        default=DEFAULT_MATERIAL,
        help="教材を /material/ 以下で配信（スクロール連動に必須）",
    )
    args = parser.parse_args()
    state_path = args.state.resolve()

    if not (STATIC / "shell.html").is_file():
        raise SystemExit(f"shell が見つかりません: {STATIC / 'shell.html'}")

    material_dir = args.material_dir.resolve() if args.material_dir and args.material_dir.is_dir() else None
    serve(STATIC, material_dir, args.host, args.port)
    shell_url = f"http://{args.host}:{args.port}/shell.html?b={SHELL_BUILD}&t={int(time.time())}"

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


if __name__ == "__main__":
    main()
