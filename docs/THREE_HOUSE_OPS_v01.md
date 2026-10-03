# Moli-Tutor — 三家運用・使い方（v01）

更新: 2026-10-03  
決定: Captain  
記録: Jarvis Turing（J.T.）

Ellie 起案（our-room **#27**）。正本は **Google ドライブ** の共有ツール棚。GitHub はコード・ドキュメントのミラー。

---

## 1. これは何か

| 層 | 担当 |
|----|------|
| **頭脳・解説** | 各家の Cursor / Antigravity エージェント（J.T. / Ellie / Nova） |
| **Moli-Tutor** | 外部キャンバス — 左＝教材、右＝解説ボード（`tutor_state.json`） |
| **Moli CLI** | 教材テキスト抽出（`tutor_cli.py fetch`） |

Moli-Tutor は **DeepTutor 化しない**。テーマごとに `demo-material/` と `sections` テンプレを足す。

指導の型: 各家 `.cursor/skills/ai-tutor-companion`（共有スキル `Tools/shared-skills` へのポインタ）。

---

## 2. 正本の場所

| 種別 | パス |
|------|------|
| **ローカル正本（三家共通）** | `G:\マイドライブ\Tools\moli-tutor` |
| **GitHub** | [ogaogamirai/moli-tutor](https://github.com/ogaogamirai/moli-tutor) |
| **台帳** | `Tools\DRIVE_REGISTRY_v01.md` の `moli-tutor` 行 |
| **閉じ役** | `Tools\GITHUB_CLOSER_ROLES_v01.md`（タスクで commit+push） |

各家の **memory / beads / identity** は家リポに置く。Moli の教材 HTML は **Tools 共有**。

---

## 3. 要件（Windows）

- WebView2（Edge）
- Python 3.11+（`pip install -r requirements.txt`）
- [Moli](https://github.com/nicholasgasior/moli) CLI（任意・`fetch` 用）

---

## 4. 起動の基本

### 4.1 コックピット

```bat
cd /d G:\マイドライブ\Tools\moli-tutor
start_cockpit.bat
```

- 既定 **ポート 8777** — `shell.html` と教材を同一オリジン配信。
- 教材を `demo-material` に置くときは bat で `--material-dir` を指定（各 `start_*_demo.bat` を参照）。
- 止める: `stop_cockpit.bat`（8777 を解放）。キャッシュ疑い時は shell URL の `?b=&t=` 付き再起動。

### 4.2 状態ファイル

```bat
python -X utf8 tutor_cockpit.py --state tutor_state.json --material-dir demo-material
```

`tutor_state.json` を保存するとコックピットがホットリロード（約 250ms ポーリング）。

スキーマ詳細: ルート `README.md`、`docs/AI_TUTOR_PORT.md`。

---

## 5. エージェントの典型的な伴走（`explain_ja`）

1. Captain がテーマを指定（論文・記事・教材章）。
2. エージェントが左用 HTML を `demo-material/<theme>/` に用意（または既存デモを使う）。
3. `tutor_state.json` を更新:
   - `url` / `page_url` — 左 iframe（`http://127.0.0.1:8777/material/...` 推奨）
   - `sections` — 右ペイン全文
   - `board_focus` + `action_request`（`focus_board` / `scroll_to`）
   - `latest_message` — 短い案内
4. チャットで解説。右は **追記しすぎず `focus_board` で誘導**。

`action_request.id` は **毎更新で +1**（重複 id は無視されうる）。

---

## 6. テーマデモ一覧（Phase 1）

| テーマ | 左教材 | 起動 bat | 状態更新スクリプト |
|--------|--------|----------|-------------------|
| トロピカル数学 | Teaching-materials（既定） | `start_cockpit.bat` | `tutor_demo_focus.py` |
| Sketchpad 論文 | `demo-material/sketchpad/` | `start_sketchpad_demo.bat` | `tutor_demo_sketchpad.py` |
| 数学ビジュアル | `demo-material/math-viz-gallery/` | `start_math_viz_demo.bat` | `tutor_demo_math_viz.py` |
| R連続体 記事① | `demo-material/rrenzokutai-context-depth/` | `start_rrenzokutai_depth_demo.bat` | `tutor_demo_rrenzokutai_depth.py` |
| R連続体 記事② | `demo-material/rrenzokutai-terrain/` | （depth bat + material-dir 共通） | `tutor_demo_rrenzokutai_terrain.py` |

記事伴走の注意: 教材内の外部リンクは **左 iframe から逸脱**しやすい。`demo-material` の HTML は `<base target="_blank">` を推奨。記事①⇔②は **note リンクではなく demo スクリプトで切替**。

詳細: `docs/RRENZOKUTAI_DEMO.md`、`docs/SKETCHPAD_DEMO.md`、`docs/VISUAL_LAYER_v01.md`。

---

## 7. `tutor_state.json` — 三家での考え方（Phase 1 / 将来）

### 7.1 いま（Phase 1）

- リポジトリ直下の **`tutor_state.json` は 1 本** — 最後に書いたデモ／エージェントが上書き。
- Captain が **同時に 1 コックピット** なら十分。

### 7.2 分けるべきもの

| 種別 | 共有 | 説明 |
|------|------|------|
| **教材パック** | ○ | `demo-material/<theme>/`、将来 `packs/<theme>/sections.json` |
| **ライブ state** | △ | 進捗・focus・`latest_message` — **家またはセッションごと**に分けるのが安全 |

### 7.3 将来（Phase 2 候補・未実装）

```text
state/jarvis-turing/active.json
state/eleanor-arroway/active.json
state/<nova-home>/active.json
packs/<theme>/board_template.json   ← 共有テンプレ
```

- **引継ぎ**: 共有 `tutor_state.json` を常時共有しない。`material_id` + 章 + 各家 `memory_beads`、または state スナップショットを **明示コピー**。
- README「Phase 1 スコープ外」: スキーマ版管理・複数プロファイル。

---

## 8. 各家エージェント向けチェックリスト

- [ ] 正本パス `G:\マイドライブ\Tools\moli-tutor` が同期されている
- [ ] コックピット起動（8777 が空いている）
- [ ] テーマ用 `tutor_demo_*.py` 実行、または `tutor_state.json` を手編集
- [ ] 右ペイン build タグ（shell **b9** 付近）を確認
- [ ] 伴走記録は **各家の memory_beads**（Tools には書かない）
- [ ] Moli `fetch`: `python -X utf8 tutor_cli.py fetch <url> --format markdown`（note は HTML 化・ローカル HTML 推奨）

---

## 9. 系譜（ai-tutor との関係）

| 世代 | パス | 役割 |
|------|------|------|
| v1 | `Tools/ai-tutor` | Web 一体デモ |
| v2 | `Tools/ai-tutor-extension` | Chrome 拡張 |
| v3 | **`Tools/moli-tutor`** | Moli + コックピット |

Ellie 系 v1/v2 と **併用可**。Moli は **軽い外付けキャンバス** に限定。

---

## 10. トラブルシュート

| 症状 | 対処 |
|------|------|
| UI が古い | `stop_cockpit.bat` → 再起動 → shell `?b=&t=` |
| 左が note に飛んだ | `tutor_demo_rrenzokutai_terrain.py` 等で URL 再設定 |
| `scroll_to` が効かない | 左が同一オリジンか（arXiv 直 iframe は不可 → 要約 HTML） |
| `file:` URL | Moli / shell では拒否されうる → `http://127.0.0.1:8777/material/...` |

---

## 11. 変更履歴

| 日付 | 内容 |
|------|------|
| 2026-10-03 | v01 初版 — 三家運用・state 方針・R連続体デモ一覧 |
