#!/usr/bin/env python3
"""Moli-Tutor CLI — Moli fetch wrapper for agents."""
from __future__ import annotations

import argparse
import os
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

    args = parser.parse_args()
    return int(args.func(args))


if __name__ == "__main__":
    raise SystemExit(main())
