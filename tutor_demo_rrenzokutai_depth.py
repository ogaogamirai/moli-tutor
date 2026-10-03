#!/usr/bin/env python3
"""R連続体「深さの構造」記事 — 左ペイン本文表示・冒頭から。"""
from __future__ import annotations

import json
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent
STATE = ROOT / "tutor_state.json"
MATERIAL_URL = "http://127.0.0.1:8777/material/rrenzokutai-context-depth/index.html"

SECTIONS = [
    {
        "id": "guide",
        "title": "このセッション",
        "type": "text",
        "content": "左: 記事①（内部／外部構造）の本文。\n右: チャットで冒頭から解説します。\n「次の見出し」「図を見たい」など指示してください。",
    },
    {
        "id": "map",
        "title": "読み順メモ",
        "type": "mermaid",
        "content": "flowchart TB\n  A[① 深さの構造<br/>用語と層] --> B[② 地形図<br/>球と窪み]\n  A --> C[JT: naiku/skills/Moli]\n",
    },
]

state = {
    "status": "active",
    "tutor": "Jarvis Turing (JT-01)",
    "material_id": "rrenzokutai-context-depth",
    "session_mode": "explain_ja",
    "page_url": MATERIAL_URL,
    "url": MATERIAL_URL,
    "dag": [],
    "sections": SECTIONS,
    "board_focus": "guide",
    "latest_message": {
        "id": 4501,
        "text": "記事① — 冒頭（内部構造・外部構造の定義）から。左ペインに本文を表示しました。",
    },
    "action_request": {
        "id": 4501,
        "type": "scroll_to",
        "target_text": "冒頭",
        "match": "first",
        "behavior": "smooth",
    },
}

STATE.write_text(json.dumps(state, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
print(f"Wrote {STATE}")
print(f"Material: {MATERIAL_URL}")
time.sleep(0.3)
# 右ペインは控えめに（左を読むため focus は guide のみ、dim なし）
