"""Interactive Sketchpad 試読 — 右ペイン sections（全文固定 + focus 誘導）。"""
from __future__ import annotations

MMD_LOOP = """flowchart TB
  P[問題] --> LMM[LMM チューター]
  LMM --> T[テキストヒント]
  LMM --> C[図生成コード]
  C --> R[実行]
  R --> D[ダイアグラム]
  T --> SP[スケッチパッド]
  D --> SP
  SP --> S[学習者の落書き・追問]
  S --> LMM
"""

MMD_MOLI = """flowchart LR
  L[左: 論文・教材] --> JT[JT / Cursor]
  JT --> ST[tutor_state.json]
  ST --> R[右: sections + focus]
  JT --> V["/visualize 試案"]
  V --> R
"""

SECTIONS = [
    {
        "id": "motlab",
        "title": "1. 論文の問い",
        "type": "text",
        "content": (
            "多くのチューターはテキストだけ。\n"
            "人間は図・スケッチで考えるのに、フィードバックが自然言語だけだと負荷が偏る。\n"
            "Sketchpad は「言葉＋見える図」を同じキャンバスに載せる。"
        ),
    },
    {
        "id": "arch",
        "title": "2. システムの流れ",
        "type": "mermaid",
        "content": MMD_LOOP,
    },
    {
        "id": "codeviz",
        "title": "3. コード実行で図を安定化",
        "type": "text",
        "content": (
            "LMM が画像を直接ばらまくより、\n"
            "Python 等で描画プログラムを書いて実行 → 図を得る。\n"
            "Moli-Tutor の右ペインは SVG / Mermaid で「定着した図」を載せる層（VISUAL_LAYER）に相当。"
        ),
    },
    {
        "id": "results",
        "title": "4. ユーザースタディ（要約）",
        "type": "text",
        "content": (
            "几何・微積・三角の問題で評価。\n"
            "テキストのみより、理解度・正答・エンゲージメントが改善（論文の主張）。\n"
            "左の「User Studies」付近を読みながら、何が測られたか自分の言葉で言える？"
        ),
    },
    {
        "id": "limits",
        "title": "5. 限界",
        "type": "text",
        "content": (
            "数学ドリル中心。論文読解や長文 PDF はスコープ外。\n"
            "コード実行は遅延・安全性の課題。\n"
            "→ 軽いコックピット + 外側の JT という Moli の割り切りの根拠にもなる。"
        ),
    },
    {
        "id": "moli",
        "title": "6. Moli-Tutor への写像",
        "type": "mermaid",
        "content": MMD_MOLI,
    },
]
