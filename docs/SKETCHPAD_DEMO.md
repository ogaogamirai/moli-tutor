# Interactive Sketchpad 試読デモ

論文: [arXiv:2503.16434](https://arxiv.org/html/2503.16434)（CHI EA 2025）

## なぜ要約 HTML か

arXiv 全文を左 iframe に直接載せると **クロスオリジン** のため `scroll_to` ハイライトが効きません。  
`demo-material/sketchpad/index.html` を同一オリジン配信し、**伴走用の要約＋原文引用**として読みます。全文はリンクから arXiv HTML へ。

## 手順

1. 既存コックピットを止める場合: `stop_cockpit.bat`
2. `start_sketchpad_demo.bat`（`--material-dir demo-material`）
3. 右ペインが **b8** であることを確認
4. 別ターミナル:

```bat
cd /d G:\マイドライブ\Tools\moli-tutor
python -X utf8 tutor_demo_sketchpad.py
```

10 ステップで左ハイライト → 右 `focus_board` を交互に進みます。

## エージェント向け

- 本文抽出: `tutor_cli.py fetch https://arxiv.org/html/2503.16434 --format markdown`
- 見出し: `tutor_cli.py headings https://arxiv.org/html/2503.16434`
- 右ボード定義: `demo_sketchpad_board.py`
