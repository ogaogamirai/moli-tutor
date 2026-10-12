#!/usr/bin/env python3
"""Moli-Tutor CLI — 教材取り込み CLI。

- fetch / headings: Moli（ヘッドレスブラウザ）で Web/HTML のテキストを取得
- ingest: Docling で PDF/複雑な HTML を構造化取り込み（Markdown + JSON + 画像）
  ※ docling 本体は外部ツール。PATH か環境変数 DOCLING_EXE で解決する。
"""
from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path
from urllib.request import pathname2url


def _resolve_moli() -> str:
    exe = shutil.which("moli") or shutil.which("moli.exe")
    if exe:
        return exe
    local = Path(os.environ.get("LOCALAPPDATA", "")) / "Moli" / "bin" / "moli.exe"
    if local.is_file():
        return str(local)
    raise SystemExit("moli が見つかりません。PATH または %LOCALAPPDATA%\\Moli\\bin を確認してください。")


def _resolve_docling() -> str:
    env = os.environ.get("DOCLING_EXE")
    if env and Path(env).expanduser().is_file():
        return str(Path(env).expanduser())
    # repo-local の記録ファイル（setup_docling が書き込む。Drive 外のローカル実体を指す）
    pointer = Path(__file__).resolve().parent / "docling.path"
    if pointer.is_file():
        cand = pointer.read_text(encoding="utf-8-sig").strip()
        if cand and Path(cand).is_file():
            return cand
    exe = shutil.which("docling") or shutil.which("docling.exe")
    if exe:
        return exe
    raise SystemExit(
        "docling が見つかりません。setup_docling を実行するか、PATH を通すか、"
        "環境変数 DOCLING_EXE に実行ファイルのパスを設定してください。"
    )


def _to_fetch_url(target: str) -> str:
    p = Path(target).expanduser()
    if p.exists():
        resolved = p.resolve()
        if resolved.is_dir():
            raise SystemExit(f"ディレクトリは指定できません: {resolved}")
        # pathname2url は Windows で drive 付きパスを file:///G:/... 形式にする
        return "file:" + pathname2url(str(resolved))
    if target.startswith(("http://", "https://", "file:")):
        return target
    raise SystemExit(f"パスまたは URL が見つかりません: {target}")


def cmd_headings(args: argparse.Namespace) -> int:
    """Moli markdown から # 見出しを抽出（拡張のページ解析の軽量代替）。"""
    import re

    url = _to_fetch_url(args.target)
    moli = _resolve_moli()
    proc = subprocess.run(
        [moli, "fetch", url, "--dump", "markdown", "--timeout", str(args.timeout_ms or 60000)],
        capture_output=True,
    )
    if proc.returncode != 0:
        sys.stderr.write(proc.stderr.decode("utf-8", errors="replace"))
        return proc.returncode or 1
    text = proc.stdout.decode("utf-8", errors="replace")
    headings = []
    for line in text.splitlines():
        m = re.match(r"^(#{1,6})\s+(.+)$", line.strip())
        if m:
            headings.append({"level": len(m.group(1)), "text": m.group(2).strip()})
    import json as _json

    sys.stdout.write(_json.dumps({"url": url, "headings": headings[: args.limit]}, ensure_ascii=False, indent=2))
    sys.stdout.write("\n")
    return 0


def cmd_fetch(args: argparse.Namespace) -> int:
    url = _to_fetch_url(args.target)
    moli = _resolve_moli()
    cmd = [moli, "fetch", url, "--dump", args.format]
    if args.timeout_ms is not None:
        cmd.extend(["--timeout", str(args.timeout_ms)])
    proc = subprocess.run(cmd, capture_output=True)
    if proc.returncode != 0:
        err = proc.stderr.decode("utf-8", errors="replace") or proc.stdout.decode("utf-8", errors="replace")
        sys.stderr.write(err)
        return proc.returncode or 1
    sys.stdout.buffer.write(proc.stdout)
    return 0


def _default_out(source: str) -> Path:
    p = Path(source).expanduser()
    if p.exists():
        return p.resolve().parent / (p.stem + "_docling")
    return Path.cwd() / "docling_out"


def cmd_ingest(args: argparse.Namespace) -> int:
    """Docling で PDF/HTML を構造化取り込み（md + json + 画像 + headings.json）。

    既存の fetch/headings と同じ『Markdown + 見出し』契約を返すので、Agent 側は
    Moli 経路と同じ読み方で扱える。図・表は Docling が抽出する。
    """
    source = args.target
    p = Path(source).expanduser()
    if p.exists():
        source = str(p.resolve())
    elif not source.startswith(("http://", "https://")):
        raise SystemExit(f"パスまたは URL が見つかりません: {source}")

    out = Path(args.out).expanduser().resolve() if args.out else _default_out(source)
    out.mkdir(parents=True, exist_ok=True)

    docling = _resolve_docling()
    to_formats = list(args.to) if args.to else ["md", "json"]
    cmd = [docling, "convert", source, "--output", str(out), "--image-export-mode", args.image_export_mode]
    # オフライン/可搬: setup_docling が置いた models/ があれば使う（無ければ通常の HF キャッシュ）
    models_dir = Path(docling).resolve().parent.parent.parent / "models"
    if models_dir.is_dir():
        cmd.extend(["--artifacts-path", str(models_dir)])
    for fmt in to_formats:
        cmd.extend(["--to", fmt])
    if args.ocr:
        cmd.append("--ocr")

    proc = subprocess.run(cmd, capture_output=True)
    if proc.returncode != 0:
        err = proc.stderr.decode("utf-8", errors="replace") or proc.stdout.decode("utf-8", errors="replace")
        sys.stderr.write(err)
        return proc.returncode or 1

    mds = sorted(out.glob("*.md"))
    headings: list[dict] = []
    md_path = mds[0] if mds else None
    if md_path is not None:
        text = md_path.read_text(encoding="utf-8", errors="replace")
        # Docling は画像を file:/// 絶対URLで参照する。HTTP配信の左ペインで表示できるよう相対化する。
        for img in out.glob("**/*.png"):
            rel = img.relative_to(out).as_posix()
            abs_posix = img.resolve().as_posix()
            for uri in ("file:///" + abs_posix, "file://" + abs_posix):
                text = text.replace(uri, rel)
        md_path.write_text(text, encoding="utf-8")
        for line in text.splitlines():
            m = re.match(r"^(#{1,6})\s+(.+)$", line.strip())
            if m:
                headings.append({"level": len(m.group(1)), "text": m.group(2).strip()})
        (out / "headings.json").write_text(
            json.dumps({"source": source, "headings": headings[: args.limit]}, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    images = [str(x) for x in out.glob("**/*.png")]
    summary = {
        "ok": True,
        "source": source,
        "out": str(out),
        "markdown": str(md_path) if md_path else None,
        "headings": len(headings),
        "images": len(images),
        "formats": to_formats,
    }
    sys.stdout.write(json.dumps(summary, ensure_ascii=False, indent=2))
    sys.stdout.write("\n")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Moli-Tutor agent CLI")
    sub = parser.add_subparsers(dest="command", required=True)

    p_fetch = sub.add_parser("fetch", help="Moli で教材テキストを取得（既定: markdown）")
    p_fetch.add_argument("target", help="URL またはローカル HTML/PDF パス")
    p_fetch.add_argument(
        "--format",
        default="markdown",
        choices=("markdown", "html", "json", "semantic_tree", "semantic_tree_text"),
        help="moli fetch --dump の形式",
    )
    p_fetch.add_argument("--timeout-ms", type=int, default=None, help="moli --timeout（ミリ秒）")
    p_fetch.set_defaults(func=cmd_fetch)

    p_head = sub.add_parser("headings", help="Moli markdown から見出し一覧 JSON")
    p_head.add_argument("target", help="URL またはローカルパス（file は不可 → http.server 推奨）")
    p_head.add_argument("--limit", type=int, default=40)
    p_head.add_argument("--timeout-ms", type=int, default=60000)
    p_head.set_defaults(func=cmd_headings)

    p_ingest = sub.add_parser("ingest", help="Docling で PDF/HTML を構造化取り込み（md + json + 画像）")
    p_ingest.add_argument("target", help="PDF/HTML のパスまたは URL")
    p_ingest.add_argument("--out", default=None, help="出力ディレクトリ（既定: 元ファイルの隣 <stem>_docling/）")
    p_ingest.add_argument("--to", nargs="*", default=["md", "json"], help="出力形式（既定: md json）")
    p_ingest.add_argument(
        "--image-export-mode",
        choices=("placeholder", "embedded", "referenced"),
        default="referenced",
        help="画像の出し方（既定: referenced = 別ファイルに書き出し）",
    )
    p_ingest.add_argument("--ocr", action="store_true", help="OCR を有効化（スキャン PDF 向け）")
    p_ingest.add_argument("--limit", type=int, default=200, help="headings.json に載せる見出しの上限")
    p_ingest.set_defaults(func=cmd_ingest)

    args = parser.parse_args()
    return int(args.func(args))


if __name__ == "__main__":
    raise SystemExit(main())
