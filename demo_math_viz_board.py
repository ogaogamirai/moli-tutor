"""数学可視化テーマ例 — 右ペイン sections（ギャラリー用）。"""
from __future__ import annotations

MMD_ALG = """flowchart LR
  IN[入力グラフ] --> D[Dijkstra / 最短路]
  D --> OUT[距離ラベル]
  IN --> T["トロピカル半環 (min, +)"]
"""

SVG_STATIONS = (
    '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 400 90" width="100%">'
    '<rect x="6" y="6" width="388" height="78" rx="8" fill="#0f172a" stroke="#38bdf8"/>'
    '<text x="16" y="52" fill="#e2e8f0" font-size="15">S — T — U — V（区間コスト）</text></svg>'
)

SECTIONS = [
    {
        "id": "katex",
        "title": "テーマ A — 数式（KaTeX）",
        "type": "math",
        "content": r"\int_0^1 x^2 \, dx = \frac{1}{3}, \quad a \oplus b = \min(a,b)",
    },
    {
        "id": "mermaid",
        "title": "テーマ B — 関係・手順（Mermaid）",
        "type": "mermaid",
        "content": MMD_ALG,
    },
    {
        "id": "svg",
        "title": "テーマ C — 概念図（SVG）",
        "type": "svg",
        "content": SVG_STATIONS,
    },
    {
        "id": "jsxgraph",
        "title": "テーマ D — 操作付きグラフ（JSXGraph iframe）",
        "type": "iframe",
        "content": "/visuals/jsxgraph-parabola.html",
    },
    {
        "id": "note",
        "title": "運用メモ",
        "type": "text",
        "content": (
            "教材テーマごとに sections テンプレを差し替え。\n"
            "GeoGebra / Desmos / mathly などは visual_html または別 material_id で足す。\n"
            "コアの shell は型だけ増やし、機能は詰め込まない。"
        ),
    },
]
