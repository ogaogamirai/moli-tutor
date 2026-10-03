# Moli-Tutor 視覚レイヤー設計 v0.1（検討用）

更新: 2026-10-03  
ステータス: **設計のみ**（学習記録 `turn_pipeline` は後回し）

## 問い

Cursor の **`/visualize`** と、Moli-Tutor の **右ペイン（外部キャンバス）** を、解説の流れでどう組み合わせるか。

## 三つの「画面」（住み分け）

| 層 | 何か | 強み | 弱み |
|----|------|------|------|
| **A. チャット内** (`/visualize`) | 会話中の表・Mermaid・HTML 断片 | 試行が速い、説明と同じ場所 | 教材と並べて常時見えない、セッション外は消える |
| **B. Moli-Tutor 右ペイン** (`tutor_state.json`) | 教材の横に固定の図・式 | **指し示し（左）と図（右）が同時**、AI が JSON で操作 | 表現力は今は `svg` / `math` が中心 |
| **C. Canvas**（Cursor） | 会話外の durable アプリ | 共有・反復編集 | コックピットとは別ウィンドウ |

**提案:** 伴走中の「教科書＋図」は **B を正**、チャットの `/visualize` は **ラフ・比較・試案**（A）。定着した図だけ B に昇格。

## いま動いているもの（Tier 0）

```json
{
  "svg": "<svg>...</svg>",
  "math": "a \\oplus b = \\min(a,b),\\quad a \\otimes b = a + b"
}
```

- AI は **文字列を書いて保存**するだけで右ペインが更新される。
- 左は `action_request` で教材ハイライト（済）。

## `/visualize` の制約（接続時に重要）

正本: `.cursor/skills-cursor/visualize/SKILL.md`

- HTML は **エージェント store** の `visualizations/<slug>.html`（断片、ネットワーク禁止サンドボックス）。
- チャットには `<cursor-content kind="visualization" src="visualizations/...">` で埋め込み。
- Moli-Tutor の WebView2 右ペインは **別ランタイム**（KaTeX CDN 可、iframe 教材は同一オリジン）。

→ **visualize の HTML をそのままコピペしない**方が安全。昇格時は **SVG / 簡略 HTML / Mermaid ソース** に落とす。

## Tier 1 — `mermaid`（実装済 2026-10-03）

```json
{
  "mermaid": "flowchart TB\n  A[\"⊕ = min\"] --> B[\"⊗ = +\"]"
}
```

- 右ペインは **`sections[]` を一体の解説ボード**として縦に並べる（細切れにターンごと追記しない）。
- 解説の「今ここ」は **`focus_board`**（`section_id`）で中央スクロール＋他ブロックを薄く表示（`dim: true`）。
- レンダは shell 同梱 CDN（将来 `static/vendor/mermaid` へ移行可）。

### 右ペインの誘導（推奨: focus、補助: scroll）

```json
{
  "sections": [
    { "id": "main", "type": "math", "content": "a \\oplus b = \\min(a,b)" }
  ],
  "action_request": {
    "id": 1020,
    "type": "focus_board",
    "section_id": "main",
    "behavior": "smooth",
    "dim": true
  }
}
```

比率スクロールのみ必要なとき:

```json
{ "id": 1021, "type": "scroll_viewport", "pane": "right", "y_ratio": 0.55 }
```

左（教材）と同じ `y_ratio` / `y_px` / `dy`。`pane` 省略時は **material**。

## 拡張案（Tier 2〜3）

### 動きのある図（visualize 相当）— Tier 2 以降

`/visualize` の HTML は **チャット用サンドボックス**（ネットワーク不可）。Moli-Tutor 右ペインでは **`static/visuals/*.html` を iframe 表示**（同一オリジン・スクリプト可）が現実路線。visualize で試した断片を **簡略化してコピー** → `visual_html` フィールドで参照。

### Tier 2 — `visual_html`（同一オリジン）

```json
{ "visual_html": "/visuals/demo-42.html" }
```

- 正本: `Tools/moli-tutor/static/visuals/*.html`（J.T. が生成・コミット or セッション用）。
- 右ペインは **下段 iframe** または `div` + `srcdoc`（ネットワーク不要の断片）。
- `/visualize` で作った断片を **人手 or スクリプトで簡略化してコピー**する運用から始める。

### Tier 3 — 半自動ブリッジ（将来）

- `tutor_cli.py visual-publish <store-path>` → `static/visuals/` にコピー + `tutor_state` 用パスを stdout。
- visualize の D3 チャートは **データ＋SVG 抽出**が難しい場合は Tier 1 Mermaid へ落とすルール。

## 1ターンの推奨フロー（トロピカル例）

1. **左:** `action_request` → 「第2章 発想の転換」へスクロール＋ハイライト。
2. **右:** `math` でトロピカル半環、`svg` で 4駅の概念図（済）。
3. **チャット（任意）:** `/visualize` で「max-plus と通常加算の違い」比較表 → 納得したら右の `mermaid` に固定。
4. **latest_message:** 1問だけ（AI Tutor 規律は維持）。

## AI  operability 原則

- 操作面は **`tutor_state.json` 1ファイル**に集約（id 増分は `action_request` のみでも可）。
- 視覚は **型を増やしすぎない**: `svg` | `math` | `mermaid` | `visual_html` の4種で足りる想定。
- 複雑なインタラクションは **教材側シミュレータ URL**（左を `simulator.html` に切替）も選択肢。

## 未決（Captain と決める）

1. 右ペイン **タブ**化の要否（現行: 一体ボード + focus で十分か）。
2. Mermaid・visual HTML は **CDN 禁止**で全部同梱するか（推奨: 同梱）。
3. `/visualize` を **必須**にするか、J.T. が SVG を直接書くか（初期は直接 SVG + たまに visualize 試案でよいか）。

## 次の実装スパイク候補

- **Spike A:** `mermaid` フィールド + `shell.html` レンダ（1ファイル変更中心）。
- **Spike B:** `tutor_demo_tour.py` に「右ペインだけ差し替え」ステップを追加し、デモ可能に。

学習記録（`turn_pipeline`）は **Tier 1 視覚が一段落してから**でよい（合意済み）。
