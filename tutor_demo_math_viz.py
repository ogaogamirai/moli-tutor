#!/usr/bin/env python3
"""数学可視化ギャラリー — 右ペインでテーマ A〜D を順にフォーカス。"""
from __future__ import annotations

import argparse
import json
import time
from copy import deepcopy
from pathlib import Path

from demo_math_viz_board import SECTIONS

ROOT = Path(__file__).resolve().parent
STATE = ROOT / "tutor_state.json"
MATERIAL_URL = "http://127.0.0.1:8777/material/math-viz-gallery/index.html"

BASE = {
    "status": "active",
    "tutor": "Jarvis Turing (JT-01)",
    "material_id": "math-viz-gallery",
    "session_mode": "math_viz_gallery",
    "page_url": MATERIAL_URL,
    "url": MATERIAL_URL,
    "dag": [],
    "sections": SECTIONS,
}

STEPS = [
    (4401, "katex", "例 1/4 — 数式（KaTeX）"),
    (4402, "mermaid", "例 2/4 — 手順・関係（Mermaid）"),
    (4403, "svg", "例 3/4 — 固定概念図（SVG）"),
    (4404, "jsxgraph", "例 4/4 — 操作付き（JSXGraph・スライダーと接線）"),
]


def save(path: Path, state: dict) -> None:
    path.write_text(json.dumps(state, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--pause", type=float, default=10.0)
    parser.add_argument("--state", type=Path, default=STATE)
    parser.add_argument("--once", action="store_true", help="最初の1枚だけ表示")
    args = parser.parse_args()
    path = args.state.resolve()
    steps = STEPS[:1] if args.once else STEPS
    print("[math viz] material: demo-material/math-viz-gallery/", flush=True)
    print("[math viz] shell b9+ で iframe 型を表示", flush=True)
    for step_id, sec_id, msg in steps:
        state = deepcopy(BASE)
        state["board_focus"] = sec_id
        state["latest_message"] = {"id": step_id, "text": msg}
        state["action_request"] = {
            "id": step_id,
            "type": "focus_board",
            "section_id": sec_id,
            "dim": True,
            "behavior": "smooth",
        }
        save(path, state)
        print(f"  {msg}", flush=True)
        if not args.once:
            time.sleep(args.pause)
    print("[math viz] 完了", flush=True)


if __name__ == "__main__":
    main()
