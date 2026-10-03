#!/usr/bin/env python3
"""非推奨: sections をターンごとに増やすデモ。代わりに tutor_demo_focus.py を使う。"""
from __future__ import annotations

import sys

if __name__ == "__main__":
    print(
        "tutor_demo_accumulate.py は細切れ積み上げ用の旧デモです。\n"
        "  python -X utf8 tutor_demo_focus.py\n"
        "を実行してください（全文表示 + focus_board）。",
        file=sys.stderr,
        flush=True,
    )
    raise SystemExit(1)
