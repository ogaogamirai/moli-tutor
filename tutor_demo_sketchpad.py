#!/usr/bin/env python3
"""Interactive Sketchpad 試読デモ — 左（要約 HTML）と右（解説ボード）を順に誘導。"""
from __future__ import annotations

import argparse
import json
import time
from copy import deepcopy
from pathlib import Path

from demo_sketchpad_board import SECTIONS

ROOT = Path(__file__).resolve().parent
STATE = ROOT / "tutor_state.json"
MATERIAL_URL = "http://127.0.0.1:8777/material/sketchpad/index.html"

BASE = {
    "status": "active",
    "tutor": "Jarvis Turing (JT-01)",
    "material_id": "sketchpad-paper",
    "page_url": MATERIAL_URL,
    "url": MATERIAL_URL,
    "dag": [],
    "sections": SECTIONS,
}

# (action_id, pane, action_type, target, board_section, message)
STEPS = [
    (
        4301,
        "material",
        "scroll_to",
        "text-based",
        None,
        "試読 1/10 — 左: Abstract 付近。「text-based」がハイライトされます",
    ),
    (
        4302,
        "right",
        "focus_board",
        None,
        "motlab",
        "試読 2/10 — 右: 論文が何を問題にしているか",
    ),
    (
        4303,
        "material",
        "scroll_to",
        "Interactive Sketchpad",
        None,
        "試読 3/10 — 左: システムの説明へ",
    ),
    (
        4304,
        "right",
        "focus_board",
        None,
        "arch",
        "試読 4/10 — 右: ループ構造の図",
    ),
    (
        4305,
        "material",
        "scroll_to",
        "code execution",
        None,
        "試読 5/10 — 左: コード実行で図を作る設計",
    ),
    (
        4306,
        "right",
        "focus_board",
        None,
        "codeviz",
        "試読 6/10 — 右: Moli の視覚レイヤーとの対応",
    ),
    (
        4307,
        "material",
        "scroll_to",
        "User Studies",
        None,
        "試読 7/10 — 左: 実験・ユーザースタディ",
    ),
    (
        4308,
        "right",
        "focus_board",
        None,
        "results",
        "試読 8/10 — 右: 結果の要約（1問: 何が改善したと言っている？）",
    ),
    (
        4309,
        "material",
        "scroll_to",
        "Limitations",
        None,
        "試読 9/10 — 左: 限界",
    ),
    (
        4310,
        "right",
        "focus_board",
        None,
        "moli",
        "試読 10/10 — 右: Moli-Tutor への写像。全文は arXiv HTML へ",
    ),
]


def save(path: Path, state: dict) -> None:
    path.write_text(json.dumps(state, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def build_action(step_id: int, pane: str, action_type: str, target: str | None, section: str | None) -> dict:
    action: dict = {"id": step_id, "behavior": "smooth"}
    if action_type == "scroll_to":
        action["type"] = "scroll_to"
        action["target_text"] = target
        action["match"] = "first"
    elif action_type == "focus_board":
        action["type"] = "focus_board"
        action["section_id"] = section
        action["dim"] = True
    else:
        raise ValueError(action_type)
    if pane == "right" and action_type == "scroll_viewport":
        action["pane"] = "right"
    return action


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--pause", type=float, default=9.0)
    parser.add_argument("--state", type=Path, default=STATE)
    args = parser.parse_args()
    path = args.state.resolve()
    print("[sketchpad demo] demo-material を --material-dir にしたコックピットで実行してください。", flush=True)
    print(f"  URL: {MATERIAL_URL}", flush=True)
    for step_id, pane, action_type, target, section, msg in STEPS:
        state = deepcopy(BASE)
        if section:
            state["board_focus"] = section
        state["latest_message"] = {"id": step_id, "text": msg}
        state["action_request"] = build_action(step_id, pane, action_type, target, section)
        save(path, state)
        print(f"  {msg}", flush=True)
        time.sleep(args.pause)
    print("[sketchpad demo] 完了", flush=True)


if __name__ == "__main__":
    main()
