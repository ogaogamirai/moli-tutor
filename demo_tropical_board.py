"""トロピカル数学デモ用 — 右ペイン全文（一度に載せ、解説は focus で移す）。"""
from __future__ import annotations

SVG = (
    '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 400 100" width="100%">'
    '<rect x="8" y="8" width="384" height="84" rx="10" fill="#0f172a" stroke="#38bdf8"/>'
    '<text x="20" y="58" fill="#e2e8f0" font-size="16">S — T — U — V（4駅）</text></svg>'
)

MMD_PATH = """flowchart LR
  S((S)) -->|c| T((T)) -->|c| U((U)) -->|c| V((V))
"""

MMD_ZDD = """flowchart TB
  F["フロンティア状態"] --> M["同型部分をマージ"]
  M --> Z["ZDD ノード共有"]
"""

SECTIONS = [
    {
        "id": "semiring",
        "title": "1. 半環の定義",
        "type": "math",
        "content": r"a \oplus b = \min(a,b),\quad a \otimes b = a + b",
    },
    {
        "id": "stations",
        "title": "2. 4駅のイメージ",
        "type": "svg",
        "content": SVG,
    },
    {
        "id": "path",
        "title": "3. 路線コスト",
        "type": "mermaid",
        "content": MMD_PATH,
    },
    {
        "id": "analogy",
        "title": "4. たとえ話",
        "type": "text",
        "content": (
            "⊕ は「より小さいコストを選ぶ」（駅で乗り換え候補を比べる）。\n"
            "⊗ は「コストを足す」（区間をつなげる）。\n"
            "だから最短路は ⊗ の繰り返しで、全体は ⊕ で枝を刈る。"
        ),
    },
    {
        "id": "zdd",
        "title": "5. フロンティア → ZDD",
        "type": "mermaid",
        "content": MMD_ZDD,
    },
    {
        "id": "boundary",
        "title": "6. 境界の問い",
        "type": "text",
        "content": (
            "通常の足し算では引き算で戻せますが、min には逆元がない。\n"
            "だから「最短」は得意だが「最長一筆書き」は別問題になる——\n"
            "教材第4章以降の入口です。"
        ),
    },
]
