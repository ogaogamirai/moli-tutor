#!/usr/bin/env python3
"""右ペインは全文を一度に表示し、解説ターンは focus_board で誘導するデモ。"""
from __future__ import annotations

import argparse
import json
import time
from copy import deepcopy
from pathlib import Path

from demo_tropical_board import SECTIONS

ROOT = Path(__file__).resolve().parent
STATE = ROOT / "tutor_state.json"

BASE = {
    "status": "active",
    "tutor": "Jarvis Turing (JT-01)",
    "material_id": "tropical-math",
    "page_url": "http://127.0.0.1:8777/material/index.html",
    "url": "http://127.0.0.1:8777/material/index.html",
    "dag": [],
    "sections": SECTIONS,
}

STEPS = [
    (4101, "semiring", "解説 1/6 — まず半環の式に注目（下の図はこのあとつながります）"),
    (4102, "stations", "解説 2/6 — 4駅のイメージ。左の教材と並べて眺めてください"),
    (4103, "path", "解説 3/6 — 路線コストは ⊗ の積み上げ"),
    (4104, "analogy", "解説 4/6 — ⊕ と ⊗ のたとえ話"),
    (4105, "zdd", "解説 5/6 — フロンティアから ZDD への流れ"),
    (4106, "boundary", "解説 6/6 — min 半環の境界（最短と一筆書きは別問題）"),
]


def save(path: Path, state: dict) -> None:
    path.write_text(json.dumps(state, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--pause", type=float, default=8.0)
    parser.add_argument("--state", type=Path, default=STATE)
    args = parser.parse_args()
    path = args.state.resolve()
    print("[focus demo] 右ペインは全文固定。ターンごとに focus_board で誘導します。", flush=True)
    for step_id, section_id, msg in STEPS:
        state = deepcopy(BASE)
        state["board_focus"] = section_id
        state["latest_message"] = {"id": step_id, "text": msg}
        state["action_request"] = {
            "id": step_id,
            "type": "focus_board",
            "section_id": section_id,
            "behavior": "smooth",
            "dim": True,
        }
        save(path, state)
        print(f"  {msg} → focus {section_id}", flush=True)
        time.sleep(args.pause)
    print("[focus demo] 完了", flush=True)


if __name__ == "__main__":
    main()
