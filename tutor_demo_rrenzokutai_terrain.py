#!/usr/bin/env python3
"""R連続体 記事② 地形図 — 左ペイン本文・冒頭から。"""
from __future__ import annotations

import json
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent
STATE = ROOT / "tutor_state.json"
MATERIAL_URL = (
    "http://127.0.0.1:8777/material/rrenzokutai-terrain/index.html"
    f"?r={int(time.time())}"
)

state = {
    "status": "active",
    "tutor": "Jarvis Turing (JT-01)",
    "material_id": "rrenzokutai-terrain",
    "session_mode": "explain_ja",
    "page_url": MATERIAL_URL,
    "url": MATERIAL_URL,
    "dag": [],
    "sections": [
        {
            "id": "bridge",
            "title": "①→②",
            "type": "mermaid",
            "content": "flowchart TB\n  A[① 頻度=深さ<br/>内部/外部] --> B[② 地形<br/>球と窪み]\n  I[内部=深い谷+周辺] --> B\n  E[外部=浅い窪み<br/>スキル] --> B\n",
        },
        {
            "id": "now",
            "title": "いま読むところ",
            "type": "text",
            "content": "記事② 冒頭 — 球・核・浅いくぼみ・軽く強く。\n次は「周辺構造があると」（ドリフト抑制）。",
        },
    ],
    "board_focus": "bridge",
    "latest_message": {
        "id": 4503,
        "text": "記事② — 左ペインを地形図に戻しました（冒頭）。",
    },
    "action_request": {
        "id": 4503,
        "type": "scroll_to",
        "target_text": "冒頭",
        "match": "first",
        "behavior": "smooth",
    },
}

STATE.write_text(json.dumps(state, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
print(f"Wrote {STATE}\n{MATERIAL_URL}")
