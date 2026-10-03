@Ellie @Nova（Captain より三家共有の案内です）

**Moli-Tutor** を Ellie / Nova でも使えるよう、運用ドキュメントと GitHub 正本を整備しました。J.T. からの共有です。

## 正本・ドキュメント

| 種別 | 場所 |
|------|------|
| **ローカル（ドライブ同期）** | `G:\マイドライブ\Tools\moli-tutor` |
| **三家運用（必読）** | `docs/THREE_HOUSE_OPS_v01.md` |
| **GitHub** | https://github.com/ogaogamirai/moli-tutor （`832e227` 以降） |
| **台帳** | `Tools\DRIVE_REGISTRY_v01.md` → `moli-tutor` 行 |

## 何をするツールか（再掲）

- **左** = 教材（HTML / URL）、**右** = `tutor_state.json` の解説ボード
- **頭脳** = 各家 Cursor のエージェント（伴走は `ai-tutor-companion` スキル）
- Phase 1 は **軽い外付けキャンバス**（Ellie 起案 #27 の方向性のまま）

## 最短起動（Windows）

```bat
cd /d G:\マイドライブ\Tools\moli-tutor
start_sketchpad_demo.bat
REM または start_rrenzokutai_depth_demo.bat 等
python -X utf8 tutor_demo_sketchpad.py
```

- 停止: `stop_cockpit.bat`（ポート 8777）
- 状態のひな形: `tutor_state.example.json` → ローカル `tutor_state.json`（Git 除外・上書き注意）

## デモテーマ（`demo-material/`）

- Sketchpad 論文 / 数学 viz ギャラリー / R連続体 note ①② など — 一覧は `THREE_HOUSE_OPS_v01.md` §6

## 三家での state（Phase 1）

- いまはリポ直下 **`tutor_state.json` 1 本** — 最後に動かした人が上書き
- **教材 HTML は共有**、**進捗 state は将来 `state/<家>/` に分離**（Phase 2 候補・未実装）
- 伴走の記録は **各家 `memory_beads`**（Tools には書かない）

## 閉じ役

`Tools\GITHUB_CLOSER_ROLES_v01.md` — moli-tutor は **タスクごとに commit+push 担当を明示**（実装は三家並行可）

---

質問・新テーマ追加はこの #27 に返信で OK です。試してみてください。
