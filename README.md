# Moli-Tutor（Phase 1: Aether型コックピット）

Ellie 起案・our-room **#27**。教材は Moli でテキスト抽出、表示は **pywebview（WebView2）** の左右2分割。会話は Cursor / Antigravity 側。本ツールは **外部キャンバス + 状態ファイル** のみ。

## 要件

- Windows + WebView2（Edge）
- Python 3.11+（開発環境: Python 3.14 + `pip install -r requirements.txt`）
- [Moli](https://github.com/nicholasgasior/moli) CLI（例: `%LOCALAPPDATA%\Moli\bin\moli.exe`）

## 起動

```bat
start_cockpit.bat
```

既定で **ポート 8777** に shell とトロピカル数学（`/material/index.html`）を同一オリジン配信します。  
AI Tutor 拡張と同型の `action_request` / `latest_message` に対応（詳細 `docs/AI_TUTOR_PORT.md`）。

（黒い **コマンドプロンプト** は起動用です。旧版ではここを閉じるとアプリも終了していました。**現行 bat は `pythonw` + `start` で GUI だけ残します。** コンソールも出したくない場合は `start_cockpit.vbs` を使う。）

または:

```bat
python -X utf8 tutor_cockpit.py --state tutor_state.json
```

## 状態同期（Aether型）

`tutor_state.json` を編集・保存すると、コックピットがホットリロードします。

```json
{
  "url": "https://example.com/ または file:///G:/path/to/textbook.html",
  "svg": "<svg>...</svg>",
  "math": "E = mc^2"
}
```

- **左**: `url`（HTTP(S) または `file:`）
- **右**: `svg`（インライン SVG）、`math`（KaTeX 用 LaTeX 本体。`$` / `$$` は付けない）

### AI 操作（`action_request` — id は毎回 +1）

```json
{ "id": 1010, "type": "scroll_to", "target_text": "半環", "match": "all" }
```

```json
{ "id": 1011, "type": "scroll_to", "target_text": "トロピカル", "occurrence": 2 }
```

```json
{ "id": 1012, "type": "scroll_viewport", "y_ratio": 0.35 }
```

```json
{ "id": 1013, "type": "scroll_viewport", "dy": 400 }
```

```json
{ "id": 1020, "type": "scroll_viewport", "pane": "right", "y_ratio": 0.6 }
```

```json
"mermaid": "flowchart LR\n  A[min] --> B[+]"
```

**解説ボード（推奨）** — 右ペインは **一度に全文**（`sections`）。解説の流れはブロックを増やさず **`focus_board` で誘導**:

```json
"sections": [
  { "id": "semiring", "title": "1. 半環", "type": "math", "content": "a \\oplus b = \\min(a,b)" },
  { "id": "path", "title": "2. 経路", "type": "mermaid", "content": "flowchart LR\n  A --> B" }
],
"board_focus": "semiring",
"action_request": {
  "id": 4102,
  "type": "focus_board",
  "section_id": "path",
  "behavior": "smooth",
  "dim": true
}
```

`type`: `math` | `mermaid` | `svg` | `text`。`section_id` の代わりに `section_index`（0 始まり）も可。細部だけ見せたいときは `scroll_viewport` + `pane: "right"` も併用可。

デモ: `python -X utf8 tutor_demo_focus.py`（コックピット起動中に `tutor_state.json` を更新）。

**論文試読（Interactive Sketchpad）:** `start_sketchpad_demo.bat` → `tutor_demo_sketchpad.py` — 手順は `docs/SKETCHPAD_DEMO.md`。

`y_ratio` はページ全体の 0（先頭）〜1（末尾）。`behavior`: `"smooth"` | `"auto"`（省略時 smooth）。

## Moli 連携（教材テキスト取得）

```bat
python -X utf8 tutor_cli.py fetch "G:\path\to\textbook.html"
python -X utf8 tutor_cli.py fetch https://example.com --format markdown
```

Agent は stdout の Markdown をそのまま読めます。

**ローカル HTML:** Moli は `file:` URL を既定で拒否します。手元正本を使うときは教材ディレクトリで `python -m http.server 8765` を立て、`http://127.0.0.1:8765/index.html` を指定する（`tutor_state.json` も同じ URL）。

## 系譜

| 世代 | パス | 役割 |
|------|------|------|
| v1 | `Tools/ai-tutor` | Web一体型デモ |
| v2 | `Tools/ai-tutor-extension` | Chrome 拡張（将来普及） |
| v3 | **`Tools/moli-tutor`** | Moli + コックピット（本リポ） |

指導コア: `.cursor/skills/ai-tutor-companion` / `skills/ai-tutor-pack`（各家）

## 三家運用（J.T. / Ellie / Nova）

- **正本**: `G:\マイドライブ\Tools\moli-tutor`（ドライブ同期）
- **手順・運用・state の考え方**: [`docs/THREE_HOUSE_OPS_v01.md`](docs/THREE_HOUSE_OPS_v01.md)
- **R連続体 note 伴走**: [`docs/RRENZOKUTAI_DEMO.md`](docs/RRENZOKUTAI_DEMO.md)
- **状態ファイルのひな形**: `tutor_state.example.json` → ローカルで `tutor_state.json`（Git 除外）

## Phase 1 スコープ外（次フェーズ候補）

- 章ジャンプ API（左ペインへの JS 注入）
- D2 / Mermaid 枠
- `tutor_state.json` のスキーマ版管理・複数プロファイル
