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

`type`: `math` | `mermaid` | `svg` | `text` | `d2`（D2テキスト直接入力 ➔ 0.04秒自動SVGコンパイル ＆ 画面からSVG保存・D2コピー対応）。`section_id` の代わりに `section_index`（0 始まり）も可。細部だけ見せたいときは `scroll_viewport` + `pane: "right"` も併用可。

### 左右ペイン折りたたみ（AIチャット並列表示対応）
AIチャット画面と横並びで表示する際、視認性を高めるためワンクリックおよびショートカットでペインを切り替えられます：
- **`◀ 教材のみ` (Alt+1)**: 生教材を全幅表示（解説ボードを一時隠す）
- **`50:50` (Alt+2)**: 通常の2分割表示
- **`解説のみ ▶` (Alt+3)**: 解説ボード（D2・数式・図解）を全幅表示（教材を一時隠す）
※教材のみモードでも右上の「解説を開く」ボタンで即座に復帰できます。モードはブラウザに記憶されます。

デモ: `python -X utf8 tutor_demo_focus.py`（コックピット起動中に `tutor_state.json` を更新）。

### 学習マップ（DAG）

`dag` を入れると、ボード上部に **学習マップ**（学ぶ順番と現在地）が出ます。ノードをクリックすると、教材の該当箇所へスクロール＆ハイライトします。

```json
"dag": [
  { "id": "KC_01", "name": "1. 半環", "type": "concept", "status": "active", "heading_index": 5 }
]
```

- `type`: `prerequisite`（前提） | `concept`（概念）
- `status`: `pending`（⚪） | `active`（🎯） | `completed`（✅）
- 進捗は自動表示（`n/m 完了`）

**アンカー（教材のどこへ飛ぶか）** — 次のいずれか:

| 指定 | 挙動 |
|------|------|
| `heading_index` | 教材の見出し（h1–h6）の **N番目（0始まり）** へ厳密にジャンプ。最も安定 |
| `heading` | 見出しテキストで探す（見出しのみ対象） |
| `target_text` | まず見出しを探し、無ければ本文テキスト。空白は正規化して照合 |

`heading_index` は `tutor_cli.py headings`（`ingest` も）が **index 付き** で出力します。

```bat
python -X utf8 tutor_cli.py headings "G:\path\to\textbook.html"
```

### DAG 雛形の自動生成（`tutor_cli.py dag`）

教材の見出しから **学習マップの雛形**を作ります。ツールは**構造だけ**（見出し→ノード＋`heading_index`）を作り、`prerequisite` / `concept` の意味づけは**下書き**です。意味は **AIが直してください**。

```bat
python -X utf8 tutor_cli.py dag "G:\path\to\textbook.html" --max-level 3
python -X utf8 tutor_cli.py dag "https://..." --max-level 2 --out dag.json
python -X utf8 tutor_cli.py dag "G:\...\index.html" --max-level 2 --state tutor_state.json --material-id tropical-math
```

- 見出しは **`h1`–`h6` と `role="heading"`** を **DOM順**に取得（bridge と同じ集合・順序）→ `heading_index` が一致します
- 各ノードに **節の要約**（`summary`）と本文長（`chars`）を付与。**章見出しは節の本文も含めて要約** → 教材全文を読まずに**全体像**を掴めます
- `--outline PATH` で **読みやすいアウトライン（Markdown）** を書き出し（AIの低負荷な全体把握用）
- `--max-level`（既定 3）／ `--include-h1` ／ `--skip-re` ／ `--no-skip` ／ `--prereq-re` ／ `--include-re` ／ `--exclude-re` ／ `--limit`
- `--no-summary` ／ `--summary-chars`（既定 160）／ `--summary-sentences`（既定 2）
- 既定の除外: 目次・内容・索引・参考文献など／ 既定の prerequisite 判定: はじめに・概要・前提・基礎・導入・Introduction…
- `--state PATH` で `tutor_state.json` の `dag` を置換（`--out` は配列だけ書き出し）

> 要約は**決定的な抽出**（先頭文ベース。LLM不使用）です。足りない所は AI が補います。学習マップでは各ノードにマウスを重ねると要約が見えます。

### 状態の確認と再開（`status` / `load` / pack）

AI は `status` で「いまの状態（教材・進捗・現在ノード）」を低負荷で読めます。

```bat
python -X utf8 tutor_cli.py status --state tutor_state.json
python -X utf8 tutor_cli.py status --json          REM 機械可読
python -X utf8 tutor_cli.py status --outline       REM 各ノードの要約も表示
```

教材ごとの DAG を **`packs/<material_id>/dag.json`** に保存し、後で読み戻せます。

```bat
REM 生成 → pack に保存 → live state にも反映
python -X utf8 tutor_cli.py dag "G:\...\index.html" --material-id tropical-math --pack packs --state tutor_state.json
REM 再開: pack から state に読み戻す
python -X utf8 tutor_cli.py load --material-id tropical-math --state tutor_state.json --pack packs
```


### AI 操作の CLI（`tutor_cli.py act`）

エージェントは `tutor_state.json` を手書きせず、`act` で1操作ずつ追記できます（`id` は自動で +1）。

**どのシェルからでも（推奨）:**

```bat
act.bat --scroll-to "半環"
act.bat --heading-index 26
act.bat --clear-highlight
```

> `act.bat` は内部でリポジトリへ移動し、`tutor_state.json` を対象にします。
> 直接叩く場合のディレクトリ移動は **cmd.exe: `cd /d G:\...\moli-tutor`** ／ **PowerShell: `cd "G:\...\moli-tutor"`**（PowerShell では `/d` は使えません）。

```bat
python -X utf8 tutor_cli.py act --scroll-to "半環"
python -X utf8 tutor_cli.py act --heading "第2章" --behavior smooth
python -X utf8 tutor_cli.py act --heading-index 26
python -X utf8 tutor_cli.py act --clear-highlight
python -X utf8 tutor_cli.py act --focus-board semiring --no-dim
python -X utf8 tutor_cli.py act --scroll-viewport --y-ratio 0.35
python -X utf8 tutor_cli.py act --navigate-to "http://127.0.0.1:8777/material/index.html" --then-scroll-to "半環"
python -X utf8 tutor_cli.py act --latest-message "では、ここを見てみましょう"
python -X utf8 tutor_cli.py act --url "http://..." --board-visible true
```

- `--state PATH` で対象を指定（既定 `tutor_state.json`）／ `--dry-run` で書き込まず確認
- ハイライト解除は `--clear-highlight`（shell 側も `clear_highlight` に対応）
- 「いま指している場所」は画面下の status に **🎯** で表示
- `tutor_state.json` は BOM 付きでも読めます（`utf-8-sig`）

### ボードの開閉

既定は **教材のみ**（ボードは隠れています）。開くには右上の「解説を開く」または **Alt+2**。`tutor_state.json` の `board_visible` でも制御できます（`true`=開く / `false`=隠す）。`focus_board` や右ペインへの `scroll_viewport` を送ると自動で開きます。

### 教材の入口（`add-material` / `open`）

リンクや PDF を**教材化して左ペインに出す**までを1コマンドに寄せます。教材は **`materials/<material_id>/`** に置かれ、`/material/<material_id>/` として配信されます（**複数ルート対応**）。

```bat
REM Web → Moli で HTML 化 ／ PDF → Docling ／ HTML → コピー
python -X utf8 tutor_cli.py add-material "https://example.com/article" --material-id article1
python -X utf8 tutor_cli.py add-material "G:\path\book.pdf" --material-id book1
python -X utf8 tutor_cli.py add-material "G:\path\page.html" --material-id page1

REM 左ペインに出す（+ pack があれば DAG も読み込む）
python -X utf8 tutor_cli.py open --material-id article1 --pack packs
```

- `add-material` の出力に `url`（`/material/<id>/index.html`）と次の一手が出ます
- `open` は `tutor_state.json` の `url` と `material_id` を設定（`--pack` で DAG も）
- 教材は `materials/`（git 除外）。`--materials DIR` で変更可

> **外部URLの直接 iframe は操作できません**（cross-origin で bridge が入らない）。だから `add-material` で**同一オリジンに教材化**してから `open` します。

### 教材が出ないとき（404）

左ペインが404のときは、**起動時の `--material-dir` と `tutor_state.json` の `url` が不一致**です。両者を同じ教材に合わせてください（左ペインにも案内が出ます）。

### アクセスログ（デバッグ）

環境変数 `MOLI_TUTOR_ACCESS_LOG=1` を付けて起動すると、HTTPリクエストを stderr に出力します。

```bat
set MOLI_TUTOR_ACCESS_LOG=1
python -X utf8 tutor_cockpit.py --state tutor_state.json --material-dir "G:\...\tropical-math"
```

### テスト

```bat
python -X utf8 tests/smoke.py
```

D2変換・state素通し・`/api/state`・パストラバーサル・shellのフックを確認し、`node` があれば学習マップの描画も検証します。



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
- **学習プロトコル（15分/1トピック）**: [`docs/LEARNING_PROTOCOL_v01.md`](docs/LEARNING_PROTOCOL_v01.md)
- **R連続体 note 伴走**: [`docs/RRENZOKUTAI_DEMO.md`](docs/RRENZOKUTAI_DEMO.md)
- **状態ファイルのひな形**: `tutor_state.example.json` → ローカルで `tutor_state.json`（Git 除外）

## Phase 1 スコープ外（次フェーズ候補）

- 章ジャンプ API（左ペインへの JS 注入）
- D2 / Mermaid 枠
- `tutor_state.json` のスキーマ版管理・複数プロファイル

## Docling（任意・PDF/複雑な HTML の取り込み）

PDF や複雑な HTML を **構造化 Markdown** に変換して教材化する任意機能です（`tutor_cli.py ingest`）。
Web ページは従来どおり Moli（`fetch`）を使い、**PDF は Docling** が担います。**図・表も抽出**します。

### セットアップ（初回のみ）

```bat
setup_docling.bat
```

- 既定のインストール先: `%LOCALAPPDATA%\moli-tutor\docling`（**クラウド同期フォルダは避ける**）
- 変更する場合は引数で指定: `setup_docling.bat "D:\tools\docling"`
- Mac/Linux: `./setup_docling.sh`
- インストール先は `docling.path`（git 除外）に記録され、`tutor_cli.py` が自動で解決します
- ディスク約 1.9GB（venv 約1.1GB ＋ モデル 約0.8GB）。**モデルは公式から取得**（再配布しません）

### 使い方

```bat
python -X utf8 tutor_cli.py ingest "G:\path\to\book.pdf"
python -X utf8 tutor_cli.py ingest https://arxiv.org/pdf/1706.03762 --out .\materials\transformer
```

出力: `<name>.md`（Markdown）／`<name>.json`（DoclingDocument）／`<name>_artifacts/`（図PNG）／`headings.json`（見出し）。
画像参照は相対パスに正規化され、HTTP 配信の左ペインで表示できます。

### 注意（実測）

- **横書き和文**: 読み順・見出し・表・図とも良好
- **縦書き和文**: 読み順が逆転（要前処理）
- **スキャン PDF**: OCR は使えるが促音・句読点・誤字あり（校閲必須）
- 環境変数 `DOCLING_EXE` で docling 実行ファイルを上書きできます
