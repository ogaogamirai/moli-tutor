# Moli-Tutor × AI Tutor Companion 移植マップ

正本: `Tools/ai-tutor-extension/SYSTEM_OVERVIEW.md`  
状態スキーマ: 拡張 `data/tutor_state.json` と **同一フィールドを段階移植**。

## Phase 1（済）— コックピット

- 左右2分割、`url` / `svg` / `math`
- Moli `fetch` CLI
- 内蔵 HTTP（`8777`）で shell + 教材を **同一オリジン**

## Phase 2（済）— ブラウザ連動（拡張の手足）

| 拡張機能 | Moli-Tutor |
|----------|------------|
| `action_request` `scroll_to` + `target_text` | `material_bridge.js` + `tutor_state.json` |
| `scroll_to` + `match: "all"` | 同一語の **複数箇所** を黄色ハイライト（先頭 or `occurrence` へスクロール） |
| `scroll_to` + `occurrence: N` | N 番目の一致（0 始まり）だけ強調してスクロール |
| `scroll_viewport` | AI の自由スクロール（`y_ratio` 0–1 / `y_px` / `dy`） |
| `navigate_to` + `then_scroll_to` | `shell.html` `runActionRequest` |
| `latest_message` | 右ペイン青枠（チューター1問用テキスト） |
| `sections` + `focus_board` | 右ペイン **一体表示**（`id` 付きブロック）＋解説ターンでスクロール＆強調 |
| `board_focus` | フォーカスだけ維持（`action_request` なし時の表示用） |
| `page_url` | 左ペイン URL（`url` と同義、拡張互換） |

**注意:** `action_request.id` はターンごとに **必ず増やす**（同じ id は再実行しない）。  
再起動直後は教材 iframe の読込完了まで最大数秒リトライする（bridge 未準備で失敗しないよう shell 側で再送）。

### 試し方（トロピカル）

1. `start_cockpit.bat` 起動（`8777`、教材は `/material/index.html`）
2. `tutor_state.json` の `action_request.id` を +1 し、`target_text` を章見出しの一部に変更して保存
3. 左ペインがスクロール＆黄色ハイライト

## Phase 3（未）— 伴走パイプライン

| 拡張 | 移植案 |
|------|--------|
| `current_page.json`（ページ解析） | `tutor_cli.py headings`（Moli markdown → 見出し一覧） |
| `turn_pipeline.py` | `--state` で `moli-tutor/tutor_state.json` を指定するラッパー |
| `dag` サイドバー | 右ペイン下部または別ウィンドウ（v3.1） |
| `log_turn` / セッション終了パック | `data/sessions/` を moli-tutor 配下に共有 |
| Chrome 拡張のみ | ブックマーク inbox → 手動 or 将来 Moli URL 登録 |

## Phase 4（未）— 魂

- `TUTORING_METHODOLOGY.md` / `misconception_registry` — **Cursor スキル側**（変更なし）
- 対話は引き続き **Cursor / Antigravity**（コックピットにチャット欄は作らない）

## データ置き場（推奨）

```
Tools/moli-tutor/
  tutor_state.json          ← active（拡張の data/tutor_state.json と同型に育てる）
  data/materials/<id>/      ← 将来: material_registry 互換
```

拡張と並行運用する場合は、**どちらか一方を active** にし、パスをスキル／プロンプトで明示する。
