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
from html.parser import HTMLParser
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
            headings.append({"index": len(headings), "level": len(m.group(1)), "text": m.group(2).strip()})
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
                headings.append({"index": len(headings), "level": len(m.group(1)), "text": m.group(2).strip()})
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


_VOID_TAGS = {
    "area", "base", "br", "col", "embed", "hr", "img", "input",
    "link", "meta", "param", "source", "track", "wbr",
}

DAG_SKIP_DEFAULT = r"^(目次|内容|contents|table of contents|索引|index|参考文献|references)\s*$"
DAG_PREREQ_DEFAULT = r"(前提|基礎|はじめに|概要|導入|introduction|prerequisite|background|overview)"


_SKIP_TAGS = {"script", "style", "noscript", "template"}


class _DocParser(HTMLParser):
    """見出し（h1-h6 と role='heading'）と本文テキストを DOM 順に抽出する。

    見出しの集合・順序は material_bridge.js の collectHeadings() と一致させる
    （querySelectorAll('h1,...,h6,[role=heading]') は文書順で重複なし）。
    ("h", {...}) / ("t", text) のイベント列を返し、後段で節ごとの本文に組み立てる。
    """

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.events: list[tuple[str, object]] = []
        self._cap: dict | None = None
        self._depth = 0
        self._stack: list[str] = []

    @staticmethod
    def _level_of(tag: str, attrs: list[tuple[str, str | None]]) -> int | None:
        a = dict(attrs)
        if re.fullmatch(r"h[1-6]", tag):
            return int(tag[1])
        if (a.get("role") or "").lower() == "heading":
            try:
                return int(a.get("aria-level") or "2")
            except ValueError:
                return 2
        return None

    def _in_skip(self) -> bool:
        return any(t in _SKIP_TAGS for t in self._stack)

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        level = self._level_of(tag, attrs)
        if level is not None:
            if self._cap is not None:
                self._finish()
            self._stack.append(tag)
            self._depth = len(self._stack)
            self._cap = {"level": level, "id": dict(attrs).get("id") or "", "parts": []}
            return
        if tag not in _VOID_TAGS:
            self._stack.append(tag)

    def handle_data(self, data: str) -> None:
        if self._cap is not None:
            self._cap["parts"].append(data)
        elif data.strip() and not self._in_skip():
            self.events.append(("t", data))

    def handle_endtag(self, tag: str) -> None:
        if (
            self._cap is not None
            and self._stack
            and len(self._stack) == self._depth
            and self._stack[-1] == tag
        ):
            self._finish()
        if self._stack:
            for i in range(len(self._stack) - 1, -1, -1):
                if self._stack[i] == tag:
                    del self._stack[i:]
                    break

    def _finish(self) -> None:
        cap = self._cap
        self._cap = None
        if cap is None:
            return
        text = re.sub(r"\s+", " ", "".join(cap["parts"])).strip()
        self.events.append(("h", {"level": cap["level"], "text": text, "id": cap["id"]}))


def _extract_doc(text: str) -> list[tuple[str, object]]:
    parser = _DocParser()
    parser.feed(text)
    parser.close()
    return parser.events


def _headings_and_sections(events: list[tuple[str, object]]) -> tuple[list[dict], list[str]]:
    """各見出しの本文を組み立てる。

    body は「その見出しの直後から、同レベル以上（level <= 自身）の次の見出しまで」の
    テキスト。章見出しなら節の本文も含むので、要約を章単位で作れる。
    """
    headings: list[dict] = []
    bodies: list[str] = []
    for i, (kind, val) in enumerate(events):
        if kind != "h":
            continue
        h = val  # type: ignore[assignment]
        level = h["level"]
        parts: list[str] = []
        j = i + 1
        while j < len(events):
            k, v = events[j]
            if k == "h":
                if v["level"] <= level:
                    break
                j += 1
                continue
            parts.append(str(v))
            j += 1
        headings.append(h)
        bodies.append(re.sub(r"\s+", " ", " ".join(parts)).strip())
    return headings, bodies


def _extract_headings_from_html(text: str) -> list[dict]:
    return _headings_and_sections(_extract_doc(text))[0]


def _summarize(body: str, max_chars: int, max_sentences: int) -> str:
    body = body.strip()
    if not body:
        return ""
    # 文境界で分割するが、区切り後の空白は保持する（英語の略語 e.g. 等でも崩れない）
    pieces = [p for p in re.split(r"(?<=[。．！？!?])|(?<=\.)(?=\s)", body) if p]
    if not pieces:
        return body[:max_chars]
    out = pieces[0]
    count = 1
    for p in pieces[1:]:
        if count >= max_sentences or len(out) + len(p) > max_chars:
            break
        out += p
        count += 1
    if len(out) > max_chars:
        out = out[:max_chars].rstrip() + "…"
    return out


def _decode_bytes(data: bytes) -> str:
    for enc in ("utf-8-sig", "cp932"):
        try:
            return data.decode(enc)
        except UnicodeDecodeError:
            continue
    return data.decode("utf-8", errors="replace")


def _load_material(target: str) -> tuple[str, str]:
    p = Path(target).expanduser()
    if p.is_file():
        return str(p.resolve()), _decode_bytes(p.read_bytes())
    if target.startswith(("http://", "https://")):
        from urllib.request import urlopen

        with urlopen(target, timeout=30) as resp:
            return target, _decode_bytes(resp.read())
    raise SystemExit(f"パスまたは URL が見つかりません: {target}")


def _headings_to_dag(headings: list[dict], bodies: list[str], args: argparse.Namespace) -> list[dict]:
    skip_re = None if args.no_skip else re.compile(args.skip_re or DAG_SKIP_DEFAULT, re.I)
    prereq_re = re.compile(args.prereq_re or DAG_PREREQ_DEFAULT, re.I)
    include_re = re.compile(args.include_re, re.I) if args.include_re else None
    exclude_re = re.compile(args.exclude_re, re.I) if args.exclude_re else None

    nodes: list[dict] = []
    for index, h in enumerate(headings):
        text = h["text"]
        level = h["level"]
        if not text:
            continue
        if level > args.max_level:
            continue
        if level == 1 and not args.include_h1:
            continue
        if skip_re and skip_re.search(text):
            continue
        if include_re and not include_re.search(text):
            continue
        if exclude_re and exclude_re.search(text):
            continue
        node = {
            "id": f"H{index}",
            "name": text,
            "type": "prerequisite" if prereq_re.search(text) else "concept",
            "status": "pending",
            "heading_index": index,
            "heading": text,
            "level": level,
        }
        if args.summary:
            body = bodies[index] if index < len(bodies) else ""
            summary = _summarize(body, args.summary_chars, args.summary_sentences)
            if summary:
                node["summary"] = summary
            node["chars"] = len(body)
        nodes.append(node)
        if args.limit and len(nodes) >= args.limit:
            break
    return nodes


def _render_outline(source: str, nodes: list[dict]) -> str:
    lines = [f"# 教材アウトライン: {source}", ""]
    for n in nodes:
        indent = "  " * max(0, int(n.get("level", 2)) - 2)
        lines.append(f"{indent}- [{n['heading_index']}] {n['name']}")
        if n.get("summary"):
            lines.append(f"{indent}  {n['summary']}")
    return "\n".join(lines)


def cmd_dag(args: argparse.Namespace) -> int:
    """教材の見出しから DAG 雛形を生成する（意味づけは AI が直す）。"""
    source, html_text = _load_material(args.target)
    headings, bodies = _headings_and_sections(_extract_doc(html_text))
    nodes = _headings_to_dag(headings, bodies, args)

    result: dict = {
        "source": source,
        "headings": len(headings),
        "count": len(nodes),
        "dag": nodes,
    }

    if args.state:
        sp = Path(args.state).expanduser()
        state = json.loads(sp.read_text(encoding="utf-8-sig")) if sp.is_file() else {}
        state["dag"] = nodes
        if args.material_id:
            state["material_id"] = args.material_id
        sp.write_text(json.dumps(state, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        result["state"] = str(sp)
    if args.out:
        op = Path(args.out).expanduser()
        op.write_text(json.dumps(nodes, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        result["out"] = str(op)
    if args.outline:
        op = Path(args.outline).expanduser()
        op.write_text(_render_outline(source, nodes) + "\n", encoding="utf-8")
        result["outline"] = str(op)
    if args.pack and args.material_id:
        pd = Path(args.pack).expanduser() / args.material_id
        pd.mkdir(parents=True, exist_ok=True)
        (pd / "dag.json").write_text(json.dumps(nodes, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        result["pack"] = str(pd / "dag.json")

    sys.stdout.write(json.dumps(result, ensure_ascii=False, indent=2))
    sys.stdout.write("\n")
    return 0


def _read_state(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8-sig")) if path.is_file() else {}


def cmd_status(args: argparse.Namespace) -> int:
    """現在の tutor_state.json を読み、AI が再開しやすい形で要約する。"""
    sp = Path(args.state).expanduser()
    state = _read_state(sp)
    dag = state.get("dag") or []
    done = sum(1 for n in dag if n.get("status") == "completed")
    current = next((n for n in dag if n.get("status") == "active"), None)
    latest = state.get("latest_message")
    latest_text = latest.get("text") if isinstance(latest, dict) else latest

    if args.json:
        out = {
            "state": str(sp),
            "material_id": state.get("material_id"),
            "url": state.get("url") or state.get("page_url"),
            "board_visible": state.get("board_visible"),
            "board_focus": state.get("board_focus"),
            "latest_message": latest_text,
            "progress": {"done": done, "total": len(dag)},
            "current": current,
            "dag": dag,
        }
        sys.stdout.write(json.dumps(out, ensure_ascii=False, indent=2) + "\n")
        return 0

    lines = [
        "# Moli-Tutor status",
        f"state: {sp}",
        f"material: {state.get('material_id')}",
        f"url: {state.get('url') or state.get('page_url')}",
        f"board_visible: {state.get('board_visible')}",
        f"progress: {done}/{len(dag)}",
    ]
    if current:
        lines.append(f"current: {current.get('name')}  (heading_index {current.get('heading_index')})")
    if state.get("board_focus"):
        lines.append(f"board_focus: {state.get('board_focus')}")
    if latest_text:
        lines.append(f"latest: {latest_text}")
    if dag:
        lines.append("dag:")
        for n in dag:
            icon = {"completed": "✅", "active": "🎯"}.get(n.get("status"), "⚪")
            lines.append(f"  [{n.get('heading_index')}] {icon} {n.get('name')}")
            if args.outline and n.get("summary"):
                lines.append(f"      {n['summary']}")
    sys.stdout.write("\n".join(lines) + "\n")
    return 0


def cmd_load(args: argparse.Namespace) -> int:
    """packs/<material_id>/dag.json を tutor_state.json に読み戻す（再開用）。"""
    sp = Path(args.state).expanduser()
    state = _read_state(sp)
    dag_path = Path(args.pack).expanduser() / args.material_id / "dag.json"
    if not dag_path.is_file():
        raise SystemExit(f"pack が見つかりません: {dag_path}")
    dag = json.loads(dag_path.read_text(encoding="utf-8-sig"))
    state["dag"] = dag
    state["material_id"] = args.material_id
    sp.write_text(json.dumps(state, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    done = sum(1 for n in dag if n.get("status") == "completed")
    sys.stdout.write(
        json.dumps(
            {
                "state": str(sp),
                "material_id": args.material_id,
                "source": str(dag_path),
                "dag": len(dag),
                "progress": f"{done}/{len(dag)}",
            },
            ensure_ascii=False,
            indent=2,
        )
        + "\n"
    )
    return 0


_IMAGE_EXTS = {".png", ".jpg", ".jpeg", ".gif", ".svg", ".webp"}


def _relativize_assets(out_dir: Path, text_path: Path) -> None:
    text = text_path.read_text(encoding="utf-8", errors="replace")
    for img in out_dir.rglob("*"):
        if img.is_file() and img.suffix.lower() in _IMAGE_EXTS:
            rel = img.relative_to(out_dir).as_posix()
            abs_posix = img.resolve().as_posix()
            for uri in ("file:///" + abs_posix, "file://" + abs_posix):
                text = text.replace(uri, rel)
    text_path.write_text(text, encoding="utf-8")


def _moli_fetch_html(url: str) -> bytes:
    moli = _resolve_moli()
    proc = subprocess.run([moli, "fetch", url, "--dump", "html"], capture_output=True)
    if proc.returncode != 0:
        err = proc.stderr.decode("utf-8", "replace") or proc.stdout.decode("utf-8", "replace")
        raise SystemExit("Moli fetch に失敗しました:\n" + err)
    return proc.stdout


def _docling_to_html(lib: Path, source: str) -> None:
    docling = _resolve_docling()
    before = {p.name for p in lib.glob("*.html")}
    cmd = [
        docling, "convert", source,
        "--output", str(lib),
        "--to", "html", "--to", "md",
        "--image-export-mode", "referenced",
    ]
    models_dir = Path(docling).resolve().parent.parent.parent / "models"
    if models_dir.is_dir():
        cmd.extend(["--artifacts-path", str(models_dir)])
    proc = subprocess.run(cmd, capture_output=True)
    if proc.returncode != 0:
        err = proc.stderr.decode("utf-8", "replace") or proc.stdout.decode("utf-8", "replace")
        raise SystemExit("Docling に失敗しました:\n" + err)
    new = [p for p in sorted(lib.glob("*.html")) if p.name not in before]
    produced = new[0] if new else (sorted(lib.glob("*.html")) or [None])[0]
    if produced is None:
        raise SystemExit("Docling が HTML を出力しませんでした（--to html 非対応の版かもしれません）")
    if produced.name != "index.html":
        produced.replace(lib / "index.html")
    _relativize_assets(lib, lib / "index.html")


def cmd_add_material(args: argparse.Namespace) -> int:
    """URL / PDF / HTML を教材化し、materials/<material-id>/index.html に置く。"""
    mid = args.material_id
    lib = Path(args.materials).expanduser() / mid
    lib.mkdir(parents=True, exist_ok=True)
    source = args.source
    p = Path(source).expanduser()
    result: dict = {"material_id": mid, "dir": str(lib)}

    if p.is_file() and p.suffix.lower() in (".html", ".htm"):
        shutil.copyfile(p, lib / "index.html")
        result["kind"] = "html"
    elif p.is_file() and p.suffix.lower() == ".pdf":
        _docling_to_html(lib, str(p.resolve()))
        result["kind"] = "pdf"
    elif source.startswith(("http://", "https://")) and source.lower().endswith(".pdf"):
        _docling_to_html(lib, source)
        result["kind"] = "pdf"
    elif source.startswith(("http://", "https://")):
        (lib / "index.html").write_bytes(_moli_fetch_html(source))
        result["kind"] = "web"
    else:
        raise SystemExit(f"未対応の source です（.html / .pdf / http(s) のURL）: {source}")

    result["file"] = str(lib / "index.html")
    result["url"] = f"/material/{mid}/index.html"
    result["next"] = f"python -X utf8 tutor_cli.py open --material-id {mid}"
    sys.stdout.write(json.dumps(result, ensure_ascii=False, indent=2))
    sys.stdout.write("\n")
    return 0


def cmd_open(args: argparse.Namespace) -> int:
    """教材を左ペインに設定する（materials/<id>/<file> を開く）。"""
    sp = Path(args.state).expanduser()
    state = _read_state(sp)
    url = f"http://127.0.0.1:{args.port}/material/{args.material_id}/{args.file}"
    state["url"] = url
    state["page_url"] = url
    state["material_id"] = args.material_id
    out = {"state": str(sp), "material_id": args.material_id, "url": url}
    if args.pack:
        dag_path = Path(args.pack).expanduser() / args.material_id / "dag.json"
        if dag_path.is_file():
            state["dag"] = json.loads(dag_path.read_text(encoding="utf-8-sig"))
            out["pack"] = str(dag_path)
    sp.write_text(json.dumps(state, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    sys.stdout.write(json.dumps(out, ensure_ascii=False, indent=2))
    sys.stdout.write("\n")
    return 0


def cmd_act(args: argparse.Namespace) -> int:
    """tutor_state.json に action_request を1つ追記する（id は既存 +1）。

    エージェントが JSON を手書きせずに教材を操作するための薄い CLI。
    """
    state_path = Path(args.state).expanduser()
    state: dict = {}
    if state_path.is_file():
        state = json.loads(state_path.read_text(encoding="utf-8-sig"))

    prev_id = 0
    ar = state.get("action_request")
    if isinstance(ar, dict) and isinstance(ar.get("id"), int):
        prev_id = ar["id"]
    new_id = prev_id + 1

    if args.url:
        state["url"] = args.url
        state["page_url"] = args.url
    if args.board_visible is not None:
        state["board_visible"] = args.board_visible == "true"
    if args.board_focus is not None:
        state["board_focus"] = args.board_focus
    if args.latest_message is not None:
        state["latest_message"] = {"id": new_id, "text": args.latest_message}

    if args.clear_highlight:
        action: dict = {"id": new_id, "type": "clear_highlight"}
    elif args.navigate_to:
        action = {"id": new_id, "type": "navigate_to", "url": args.navigate_to}
        if args.then_scroll_to:
            action["then_scroll_to"] = args.then_scroll_to
    elif args.focus_board is not None:
        action = {"id": new_id, "type": "focus_board", "section_id": args.focus_board}
        if args.no_dim:
            action["dim"] = False
    elif args.heading_index is not None:
        action = {"id": new_id, "type": "scroll_to", "heading_index": args.heading_index, "match": "heading"}
    elif args.heading is not None:
        action = {"id": new_id, "type": "scroll_to", "target_text": args.heading, "match": "heading"}
    elif args.scroll_to is not None:
        action = {"id": new_id, "type": "scroll_to", "target_text": args.scroll_to}
        if args.match:
            action["match"] = args.match
        if args.occurrence is not None:
            action["occurrence"] = args.occurrence
    elif args.scroll_hash:
        action = {"id": new_id, "type": "scroll_hash", "hash": args.scroll_hash}
    elif args.scroll_viewport:
        action = {"id": new_id, "type": "scroll_viewport"}
        if args.pane:
            action["pane"] = args.pane
        if args.y_ratio is not None:
            action["y_ratio"] = args.y_ratio
        if args.y_px is not None:
            action["y_px"] = args.y_px
        if args.dy is not None:
            action["dy"] = args.dy
    else:
        raise SystemExit(
            "action を1つ指定してください "
            "(--scroll-to / --heading / --heading-index / --scroll-hash / --scroll-viewport / "
            "--focus-board / --navigate-to / --clear-highlight)"
        )

    if args.behavior and action.get("type") in ("scroll_to", "scroll_hash", "scroll_viewport"):
        action["behavior"] = args.behavior

    state["action_request"] = action
    out = {"state": str(state_path), "action_request": action}

    if not args.dry_run:
        state_path.write_text(json.dumps(state, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    else:
        out["dry_run"] = True

    sys.stdout.write(json.dumps(out, ensure_ascii=False, indent=2))
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

    p_act = sub.add_parser("act", help="tutor_state.json に action_request を1つ追記（id 自動+1）")
    p_act.add_argument("--state", default="tutor_state.json", help="対象の tutor_state.json")
    p_act.add_argument("--scroll-to", dest="scroll_to", help="語へスクロール＋ハイライト（見出し優先→本文）")
    p_act.add_argument("--heading", help="見出しテキストへ（見出しのみ対象）")
    p_act.add_argument("--heading-index", dest="heading_index", type=int, help="見出しの N番目（0始まり）へ")
    p_act.add_argument("--scroll-hash", dest="scroll_hash", help="要素 id へ（# は付けない）")
    p_act.add_argument("--scroll-viewport", dest="scroll_viewport", action="store_true", help="割合/px/差分スクロール")
    p_act.add_argument("--pane", choices=("material", "right"), help="scroll_viewport の対象ペイン")
    p_act.add_argument("--y-ratio", dest="y_ratio", type=float)
    p_act.add_argument("--y-px", dest="y_px", type=float)
    p_act.add_argument("--dy", type=float)
    p_act.add_argument("--match", choices=("first", "all", "heading"))
    p_act.add_argument("--occurrence", type=int)
    p_act.add_argument("--behavior", choices=("smooth", "auto"))
    p_act.add_argument("--clear-highlight", dest="clear_highlight", action="store_true", help="ハイライトを解除")
    p_act.add_argument("--focus-board", dest="focus_board", help="解説ブロックへフォーカス")
    p_act.add_argument("--no-dim", dest="no_dim", action="store_true", help="focus_board で他を薄くしない")
    p_act.add_argument("--navigate-to", dest="navigate_to", help="教材ページを切替")
    p_act.add_argument("--then-scroll-to", dest="then_scroll_to", help="navigate_to 後にスクロールする語")
    p_act.add_argument("--url", help="state の url / page_url を更新")
    p_act.add_argument("--board-visible", dest="board_visible", choices=("true", "false"), help="ボードの開閉")
    p_act.add_argument("--board-focus", dest="board_focus", help="state の board_focus を更新")
    p_act.add_argument("--latest-message", dest="latest_message", help="latest_message を更新")
    p_act.add_argument("--dry-run", dest="dry_run", action="store_true", help="書き込まずに結果だけ表示")
    p_act.set_defaults(func=cmd_act)

    p_dag = sub.add_parser("dag", help="教材の見出しから DAG 雛形を生成（heading_index 付き）")
    p_dag.add_argument("target", help="HTML のパスまたは URL")
    p_dag.add_argument("--max-level", dest="max_level", type=int, default=3, help="含める見出しの最大レベル（既定 3）")
    p_dag.add_argument("--include-h1", dest="include_h1", action="store_true", help="h1（通常はタイトル）も含める")
    p_dag.add_argument("--skip-re", dest="skip_re", default=None, help="除外する見出しの正規表現（目次など）")
    p_dag.add_argument("--no-skip", dest="no_skip", action="store_true", help="既定のノイズ除外を無効化")
    p_dag.add_argument("--prereq-re", dest="prereq_re", default=None, help="prerequisite とみなす正規表現")
    p_dag.add_argument("--include-re", dest="include_re", default=None, help="一致する見出しだけ含める")
    p_dag.add_argument("--exclude-re", dest="exclude_re", default=None, help="一致する見出しを除外")
    p_dag.add_argument("--limit", type=int, default=0, help="ノード数の上限（0=無制限）")
    p_dag.add_argument("--no-summary", dest="summary", action="store_false", help="節の要約を付けない")
    p_dag.add_argument("--summary-chars", dest="summary_chars", type=int, default=160, help="要約の最大文字数（既定 160）")
    p_dag.add_argument("--summary-sentences", dest="summary_sentences", type=int, default=2, help="要約に含める文の数（既定 2）")
    p_dag.add_argument("--out", default=None, help="DAG 配列の書き出し先ファイル")
    p_dag.add_argument("--outline", default=None, help="読みやすいアウトライン(Markdown)の書き出し先")
    p_dag.add_argument("--state", default=None, help="この tutor_state.json の dag を置き換える")
    p_dag.add_argument("--material-id", dest="material_id", default=None, help="--state と併用で material_id を設定")
    p_dag.add_argument("--pack", default=None, help="<pack>/<material-id>/dag.json に保存（要 --material-id）")
    p_dag.set_defaults(func=cmd_dag)

    p_status = sub.add_parser("status", help="現在の state を読み、進捗・現在ノードを要約表示")
    p_status.add_argument("--state", default="tutor_state.json", help="対象の tutor_state.json")
    p_status.add_argument("--json", action="store_true", help="JSON で出力")
    p_status.add_argument("--outline", action="store_true", help="DAG に要約も表示")
    p_status.set_defaults(func=cmd_status)

    p_load = sub.add_parser("load", help="packs/<material-id>/dag.json を state に読み戻す")
    p_load.add_argument("--material-id", dest="material_id", required=True)
    p_load.add_argument("--state", default="tutor_state.json", help="対象の tutor_state.json")
    p_load.add_argument("--pack", default="packs", help="pack のベースディレクトリ（既定 packs）")
    p_load.set_defaults(func=cmd_load)

    p_add = sub.add_parser("add-material", help="URL/PDF/HTML を教材化して materials/<id>/ に置く")
    p_add.add_argument("source", help="HTML/PDF のパス、または http(s) URL")
    p_add.add_argument("--material-id", dest="material_id", required=True)
    p_add.add_argument("--materials", default="materials", help="教材ライブラリのディレクトリ（既定 materials）")
    p_add.set_defaults(func=cmd_add_material)

    p_open = sub.add_parser("open", help="教材を左ペインに設定（materials/<id>/index.html）")
    p_open.add_argument("--material-id", dest="material_id", required=True)
    p_open.add_argument("--state", default="tutor_state.json", help="対象の tutor_state.json")
    p_open.add_argument("--file", default="index.html", help="materials/<id>/ 内のファイル（既定 index.html）")
    p_open.add_argument("--port", type=int, default=8777)
    p_open.add_argument("--pack", default=None, help="指定時は packs/<id>/dag.json も読み込む")
    p_open.set_defaults(func=cmd_open)

    args = parser.parse_args()
    return int(args.func(args))


if __name__ == "__main__":
    raise SystemExit(main())
