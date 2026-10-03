#!/usr/bin/env python3
"""教材を順にスクロール＋ハイライトするデモ（tutor_state.json を段階更新）。"""
from __future__ import annotations

import argparse
import json
import time
from copy import deepcopy
from pathlib import Path

ROOT = Path(__file__).resolve().parent
STATE = ROOT / "tutor_state.json"

TOUR = [
    (2001, "scroll_to", "発想の転換", None, "▶ 1/6 第2章見出し「発想の転換」を照準"),
    (2002, "scroll_viewport", None, 0.22, "▶ 2/6 ページ上部（約22%）へスクロール"),
    (2003, "scroll_to", "フロンティア", None, "▶ 3/6 「フロンティア」付近をハイライト"),
    (2004, "scroll_viewport", None, 0.48, "▶ 4/6 ページ中央（約48%）へスクロール"),
    (2005, "scroll_to", "ZDD", "all", "▶ 5/6 「ZDD」が出る箇所をまとめてハイライト"),
    (2006, "scroll_viewport", None, 0.72, "▶ 6/6 ページ後半（約72%）へスクロール"),
]


def load_state(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def save_state(path: Path, state: dict) -> None:
    path.write_text(json.dumps(state, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description="Moli-Tutor スクロール見学デモ")
    parser.add_argument("--pause", type=float, default=5.0, help="各ステップの秒数")
    parser.add_argument("--state", type=Path, default=STATE)
    args = parser.parse_args()
    state_path = args.state.resolve()

    base = load_state(state_path)
    print("[moli-tutor demo] コックピットが起動していることを確認してください。", flush=True)
    for step_id, kind, text, match, msg in TOUR:
        state = deepcopy(base)
        state["latest_message"] = {"id": step_id, "text": msg}
        if kind == "scroll_to":
            state["action_request"] = {
                "id": step_id,
                "type": "scroll_to",
                "target_text": text,
            }
            if match == "all":
                state["action_request"]["match"] = "all"
        else:
            state["action_request"] = {
                "id": step_id,
                "type": "scroll_viewport",
                "y_ratio": match,
                "behavior": "smooth",
            }
        save_state(state_path, state)
        print(f"  {msg}", flush=True)
        time.sleep(args.pause)
    print("[moli-tutor demo] 完了", flush=True)


if __name__ == "__main__":
    main()
