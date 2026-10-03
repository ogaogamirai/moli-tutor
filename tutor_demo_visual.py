#!/usr/bin/env python3
"""Mermaid + 右ペインスクロール + 左ハイライトの統合デモ。"""
from __future__ import annotations

import argparse
import json
import time
from copy import deepcopy
from pathlib import Path

ROOT = Path(__file__).resolve().parent
STATE = ROOT / "tutor_state.json"

MERMAID = """flowchart TB
  subgraph semi["トロピカル半環（max-plus）"]
    A["a ⊕ b = min(a,b)"]
    B["a ⊗ b = a + b"]
  end
  subgraph path["路線コスト"]
    S["駅 S"]
    T["駅 T"]
    U["駅 U"]
    S -->|"c(S,T)"| T -->|"c(T,U)"| U
  end
  A --> C["最短路 = ⊗ を繰り返し"]
  B --> C
  C --> D["フロンティア法で状態を圧縮"]
  D --> E["ZDD で組合せを共有"]
  E --> F["4駅デモ → 87駅へ"]
"""

SVG = (
    '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 420 140" width="100%" height="140">'
    '<rect x="10" y="10" width="400" height="120" rx="14" fill="#0f172a" stroke="#38bdf8" stroke-width="2"/>'
    '<text x="28" y="48" fill="#e2e8f0" font-size="17">4駅 · トロピカル最短路</text>'
    '<circle cx="70" cy="95" r="9" fill="#38bdf8"/><circle cx="170" cy="95" r="9" fill="#38bdf8"/>'
    '<circle cx="270" cy="95" r="9" fill="#38bdf8"/><circle cx="370" cy="95" r="9" fill="#f472b6"/>'
    '<line x1="79" y1="95" x2="161" y2="95" stroke="#94a3b8" stroke-width="3"/>'
    '<line x1="179" y1="95" x2="261" y2="95" stroke="#94a3b8" stroke-width="3"/>'
    '<line x1="279" y1="95" x2="361" y2="95" stroke="#94a3b8" stroke-width="3"/>'
    "</svg>"
)

STEPS = [
    (3001, "right", 0.0, None, None, "▶ 1/5 右ペイン先頭（SVG・式・Mermaid 図）"),
    (3002, "left", None, "scroll_to", "発想の転換", "▶ 2/5 左: 第2章をハイライト"),
    (3003, "right", 0.55, None, None, "▶ 3/5 右ペイン中段へスクロール（Mermaid 下部）"),
    (3004, "left", None, "scroll_to", "ZDD", "▶ 4/5 左: ZDD を複数ハイライト"),
    (3005, "right", 0.95, None, None, "▶ 5/5 右ペイン末尾へスクロール"),
]


def base_state() -> dict:
    return {
        "status": "active",
        "tutor": "Jarvis Turing (JT-01)",
        "material_id": "tropical-math",
        "page_url": "http://127.0.0.1:8777/material/index.html",
        "url": "http://127.0.0.1:8777/material/index.html",
        "svg": SVG,
        "math": "a \\oplus b = \\min(a,b),\\quad a \\otimes b = a + b",
        "mermaid": MERMAID,
        "dag": [],
    }


def save_state(path: Path, state: dict) -> None:
    path.write_text(json.dumps(state, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description="Moli-Tutor 視覚デモ")
    parser.add_argument("--pause", type=float, default=7.0)
    parser.add_argument("--state", type=Path, default=STATE)
    args = parser.parse_args()
    path = args.state.resolve()
    print("[moli-tutor visual demo] コックピットを前面に。", flush=True)
    for step_id, pane, y_ratio, kind, text, msg in STEPS:
        state = deepcopy(base_state())
        state["latest_message"] = {"id": step_id, "text": msg}
        if pane == "right":
            state["action_request"] = {
                "id": step_id,
                "type": "scroll_viewport",
                "pane": "right",
                "y_ratio": y_ratio,
                "behavior": "smooth",
            }
        else:
            state["action_request"] = {
                "id": step_id,
                "type": kind,
                "target_text": text,
                "match": "all" if text == "ZDD" else None,
            }
            if state["action_request"]["match"] is None:
                del state["action_request"]["match"]
        save_state(path, state)
        print(f"  {msg}", flush=True)
        time.sleep(args.pause)
    print("[moli-tutor visual demo] 完了", flush=True)


if __name__ == "__main__":
    main()
