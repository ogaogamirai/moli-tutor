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
    media_path = Path(args.pack).expanduser() / args.material_id / "media.json"
    media_n = 0
    if media_path.is_file():
        state["media"] = json.loads(media_path.read_text(encoding="utf-8-sig"))
        media_n = len(state["media"])
    sp.write_text(json.dumps(state, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    done = sum(1 for n in dag if n.get("status") == "completed")
    sys.stdout.write(
        json.dumps(
            {
                "state": str(sp),
                "material_id": args.material_id,
                "source": str(dag_path),
                "dag": len(dag),
                "media": media_n,
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


def _fetch_html(url: str) -> bytes:
    """URL を HTML として取得する（既定はブラウザレス urllib、失敗時のみ Moli）。"""
    from urllib.request import Request, urlopen

    try:
        req = Request(url, headers={"User-Agent": _BROWSER_UA})
        with urlopen(req, timeout=30) as resp:
            data = resp.read()
        if data.strip():
            return data
    except Exception:  # noqa: BLE001 - ブラウザレスで取れなければ Moli を試す
        pass
    try:
        moli = _resolve_moli()
    except SystemExit:
        moli = None
    if moli:
        proc = subprocess.run([moli, "fetch", url, "--dump", "html"], capture_output=True)
        if proc.returncode == 0 and proc.stdout.strip():
            return proc.stdout
    raise SystemExit(f"HTML を取得できませんでした: {url}")


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
        (lib / "index.html").write_bytes(_fetch_html(source))
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
        pd = Path(args.pack).expanduser() / args.material_id
        dag_path = pd / "dag.json"
        if dag_path.is_file():
            state["dag"] = json.loads(dag_path.read_text(encoding="utf-8-sig"))
            out["pack"] = str(dag_path)
        media_path = pd / "media.json"
        if media_path.is_file():
            state["media"] = json.loads(media_path.read_text(encoding="utf-8-sig"))
            out["media"] = str(media_path)
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
    elif args.highlight_image is not None:
        action = {"id": new_id, "type": "highlight_image", "index": args.highlight_image}
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


# ---------------------------------------------------------------------------
# normalize: 取得した Markdown を「自前の軽量 HTML 1枚」へ正規化する。
# 表示(iframe)と解析(dag)の双方の正本を、外部サイト非依存の1枚に揃える。
# 生の外部ページ(SPA)をそのまま配信しないことで、重さ・脆さ・chrome 混入を断つ。
# ---------------------------------------------------------------------------

# 末尾のページ chrome（タグ・パンくず・おすすめ）以降を落とす。
NORMALIZE_TAIL_CUT = re.compile(
    r"^(#{1,6}\s*)?(あなたへのおすすめ|関連記事|おすすめの記事|この記事が気に入ったら)\b"
    r"|^-\s*\[#"
    r"|^\d+\.\s*\[トップ\]",
    re.M,
)

# タイトル直後の著者行（アバター画像リンク・著者リンク・日付）を判定
NORMALIZE_BYLINE_RE = re.compile(
    r"^\[!\[[^\]]*\]\([^)]*\)\]\([^)]*\)$"
    r"|^\[[^\]]+\]\(https?://[^)]+\)$"
    r"|^\d{4}年\d{1,2}月\d{1,2}日"
)

NORMALIZE_TEMPLATE = """<!DOCTYPE html>
<html lang="ja">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{title}</title>
<style>
:root {{ color-scheme: light; }}
* {{ box-sizing: border-box; }}
body {{ margin: 0; padding: 32px 20px 64px; background: #fff; color: #1f2937;
  font-family: "Yu Gothic", "Hiragino Kaku Gothic ProN", Meiryo, system-ui, sans-serif;
  line-height: 1.9; font-size: 17px; }}
main {{ max-width: 760px; margin: 0 auto; }}
h1 {{ font-size: 1.7em; line-height: 1.5; border-bottom: 2px solid #e5e7eb; padding-bottom: .4em; }}
h2 {{ font-size: 1.35em; margin-top: 2.2em; padding-left: .5em; border-left: 5px solid #2563eb; line-height: 1.5; }}
h3 {{ font-size: 1.12em; margin-top: 1.8em; }}
p {{ margin: .8em 0; }}
ul, ol {{ padding-left: 1.6em; }}
li {{ margin: .3em 0; }}
blockquote {{ margin: 1em 0; padding: .4em 1em; border-left: 4px solid #cbd5e1;
  background: #f8fafc; color: #334155; }}
code {{ background: #f1f5f9; padding: .1em .35em; border-radius: 4px; font-size: .9em; }}
pre {{ background: #0f172a; color: #e2e8f0; padding: 14px 16px; border-radius: 8px; overflow: auto; }}
pre code {{ background: none; color: inherit; padding: 0; }}
img {{ max-width: 100%; height: auto; }}
table {{ border-collapse: collapse; width: 100%; margin: 1em 0; }}
th, td {{ border: 1px solid #cbd5e1; padding: 6px 10px; }}
th {{ background: #f1f5f9; }}
hr {{ border: 0; border-top: 1px solid #e5e7eb; margin: 2em 0; }}
.source {{ margin-top: 3em; padding-top: 1em; border-top: 1px solid #e5e7eb;
  color: #64748b; font-size: .82em; }}
</style>
</head>
<body>
<main>
{body}
<p class="source">出典: <a href="{source}">{source}</a></p>
</main>
</body>
</html>
"""


def _html_escape(text: str) -> str:
    return (
        text.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
    )


def _clean_markdown(md: str) -> str:
    """先頭のページ chrome（タイトル前）と末尾の chrome（タグ/パンくず/おすすめ）を落とす。"""
    lines = md.replace("\r\n", "\n").replace("\r", "\n").split("\n")
    start = 0
    for i, ln in enumerate(lines):
        if re.match(r"^#\s+\S", ln):
            start = i
            break
    # タイトル直後の著者行（アバター画像リンク・著者リンク・日付）を飛ばす
    content_start = start + 1
    while content_start < len(lines):
        s = lines[content_start].strip()
        if s == "":
            content_start += 1
            continue
        if re.match(r"^#{1,6}\s", s):
            break
        if NORMALIZE_BYLINE_RE.match(s):
            content_start += 1
            continue
        break
    end = len(lines)
    for i in range(content_start, len(lines)):
        if NORMALIZE_TAIL_CUT.search(lines[i].strip()):
            end = i
            break
    body_lines = lines[content_start:end]
    text = lines[start] + "\n\n" + "\n".join(body_lines)
    text = re.sub(r"\n{3,}", "\n\n", text).strip() + "\n"
    return text


def _md_to_html(md: str) -> str:
    try:
        import markdown  # type: ignore
    except ImportError:
        raise SystemExit("markdown が見つかりません。`pip install markdown` を実行してください。")
    return markdown.markdown(md, extensions=["extra", "sane_lists"], output_format="html5")


def _fetch_markdown(target: str) -> str:
    p = Path(target).expanduser()
    if p.is_file():
        if p.suffix.lower() in (".md", ".markdown"):
            return p.read_text(encoding="utf-8-sig", errors="replace")
        raise SystemExit(
            "HTML/PDF からは直接正規化できません。URL を渡すか、Moli の markdown ダンプ(.md) を渡してください。"
        )
    if target.startswith(("http://", "https://")):
        moli = _resolve_moli()
        proc = subprocess.run([moli, "fetch", target, "--dump", "markdown"], capture_output=True)
        if proc.returncode != 0:
            sys.stderr.write(proc.stderr.decode("utf-8", errors="replace"))
            raise SystemExit(proc.returncode or 1)
        return proc.stdout.decode("utf-8", errors="replace")
    raise SystemExit(f"パスまたは URL が見つかりません: {target}")


def _fetch_url_html(url: str) -> str:
    """ブラウザを使わず urllib で HTML を取得（ブラウザ相当の UA）。"""
    from urllib.request import Request, urlopen

    req = Request(url, headers={"User-Agent": _BROWSER_UA})
    with urlopen(req, timeout=30) as resp:
        return _decode_bytes(resp.read())


_BROWSER_UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/124.0 Safari/537.36"
)

_HTML_SKIP_TAGS = {
    "script", "style", "noscript", "svg", "iframe", "form", "nav", "header",
    "footer", "aside", "button", "select", "option", "textarea", "template",
}
_VOID_TAGS = {
    "area", "base", "br", "col", "embed", "hr", "img", "input", "link", "meta",
    "param", "source", "track", "wbr",
}
_CHROME_RE = re.compile(
    r"(nav|menu|header|footer|sidebar|side-bar|breadcrumb|related|recommend|share|"
    r"social|comment|advert|ad-|banner|cookie|pagination|\btoc\b|おすすめ|目次|関連|"
    r"広告|シェア|コメント|フッター|ヘッダー)",
    re.I,
)

# 本文コンテナの候補（id/class）。見つかれば、その中だけを本文として採用する。
_MAIN_RE = re.compile(r"(article|content|main|body|post|entry|markdown|prose)", re.I)
# 「本文らしさ」が強いコンテナ（これらを優先して選ぶ）
_BODY_STRONG_RE = re.compile(
    r"(note-body|markdown|prose|article-?body|post-?body|entry-?content|content-?body|"
    r"main-?content|article-?content|textnote-body)",
    re.I,
)


class _HtmlClean(HTMLParser):
    """本文抽出つき HTML→ブロック列。

    chrome（nav/header/footer/aside 等のタグ、および nav 系の id/class・role）を除外し、
    見出し / 段落 / リスト / 表題 / コード / 画像を DOM 順に拾う。
    """

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.blocks: list[dict] = []
        self.title = ""
        self._title_buf: list[str] = []
        self._skip = 0
        self._cur: dict | None = None
        self._in_title = False
        self._cid = 0
        self._container_stack: list[dict] = []
        self._container_meta: dict[int, str] = {}

    def _is_chrome(self, a: dict) -> bool:
        if a.get("role") in ("navigation", "banner", "contentinfo", "complementary", "search"):
            return True
        idc = (a.get("id", "") + " " + a.get("class", "")).strip()
        return bool(idc) and bool(_CHROME_RE.search(idc))

    def _container_kind(self, tag: str, a: dict) -> str | None:
        idc = a.get("id", "") + " " + a.get("class", "")
        if idc.strip() and _BODY_STRONG_RE.search(idc):
            return "strong"
        if tag in ("article", "main"):
            return "weak"
        if idc.strip() and _MAIN_RE.search(idc):
            return "weak"
        return None

    def _is_chrome_image(self, a: dict) -> bool:
        """見出し画像・アバター・小アイコンなど本文でない画像を判定。"""
        alt = (a.get("alt") or "").strip()
        if alt in ("見出し画像", "ヘッダー画像", "ヘッダ画像", "header", "avatar"):
            return True
        src = a.get("src", "") or a.get("data-src", "") or ""
        if re.search(r"(profile|avatar|default_profile|/icon|/emoji)", src, re.I):
            return True
        try:
            w = int(a.get("width", "0") or 0)
            h = int(a.get("height", "0") or 0)
            if 0 < w <= 80 and 0 < h <= 80:
                return True
        except ValueError:
            pass
        return False

    def handle_starttag(self, tag: str, attrs: list) -> None:
        a = {k: (v or "") for k, v in attrs}
        if tag == "title":
            self._in_title = True
            return
        if self._skip > 0:
            if tag not in _VOID_TAGS:
                self._skip += 1
            return
        if tag in _HTML_SKIP_TAGS or self._is_chrome(a):
            if tag not in _VOID_TAGS:
                self._skip = 1
            return
        kind = self._container_kind(tag, a)
        if self._container_stack:
            if kind:
                if tag not in _VOID_TAGS:
                    self._cid += 1
                    self._container_meta[self._cid] = kind
                    self._container_stack.append({"tag": tag, "cid": self._cid, "depth": 0})
                return
            if tag not in _VOID_TAGS:
                self._container_stack[-1]["depth"] += 1
        elif kind:
            if tag not in _VOID_TAGS:
                self._cid += 1
                self._container_meta[self._cid] = kind
                self._container_stack.append({"tag": tag, "cid": self._cid, "depth": 0})
            return
        cids = tuple(c["cid"] for c in self._container_stack)
        if tag in ("h1", "h2", "h3", "h4", "h5", "h6"):
            self._flush()
            self._cur = {"type": "h", "level": int(tag[1]), "buf": [], "cids": cids}
        elif tag == "p":
            self._flush()
            self._cur = {"type": "p", "buf": [], "cids": cids}
        elif tag == "li":
            self._flush()
            self._cur = {"type": "li", "buf": [], "cids": cids}
        elif tag == "pre":
            self._flush()
            self._cur = {"type": "pre", "buf": [], "cids": cids}
        elif tag == "blockquote":
            self._flush()
            self._cur = {"type": "quote", "buf": [], "cids": cids}
        elif tag == "img":
            self._flush()
            src = a.get("src", "") or a.get("data-src", "") or a.get("data-original", "")
            if src and not self._is_chrome_image(a):
                self.blocks.append({"type": "img", "src": src, "alt": a.get("alt", ""), "cids": cids})
        elif tag == "br" and self._cur is not None:
            self._cur["buf"].append("\n")

    def handle_startendtag(self, tag: str, attrs: list) -> None:
        self.handle_starttag(tag, attrs)
        self.handle_endtag(tag)

    def handle_endtag(self, tag: str) -> None:
        if tag == "title":
            self._in_title = False
            self.title = re.sub(r"\s+", " ", "".join(self._title_buf)).strip()
            return
        if self._skip > 0:
            if tag not in _VOID_TAGS:
                self._skip -= 1
            return
        if self._container_stack and tag not in _VOID_TAGS:
            top = self._container_stack[-1]
            if top["depth"] > 0:
                top["depth"] -= 1
            else:
                self._container_stack.pop()
        if tag in ("h1", "h2", "h3", "h4", "h5", "h6", "p", "li", "pre", "blockquote"):
            self._flush()

    def handle_data(self, data: str) -> None:
        if self._in_title:
            self._title_buf.append(data)
            return
        if self._skip > 0 or self._cur is None:
            return
        self._cur["buf"].append(data)

    def best_blocks(self) -> list[dict]:
        """本文コンテナを1つ選び、その（子孫を含む）ブロックだけを返す。

        「本文らしい強いコンテナ（note-body 等）」を優先。無ければテキスト量が最大のもの。
        """
        totals: dict = {}
        for b in self.blocks:
            for cid in b.get("cids", ()):
                totals[cid] = totals.get(cid, 0) + len(b.get("text", ""))
        if not totals:
            return self.blocks
        strong = [c for c in totals if self._container_meta.get(c) == "strong"]
        cands = strong or list(totals)
        best = max(cands, key=lambda c: totals[c])
        return [b for b in self.blocks if best in b.get("cids", ())]

    def _flush(self) -> None:
        if self._cur is None:
            return
        text = re.sub(r"[ \t\u00a0]+", " ", "".join(self._cur["buf"]))
        text = re.sub(r"\n{2,}", "\n", text).strip()
        if text:
            blk = {k: v for k, v in self._cur.items() if k != "buf"}
            blk["text"] = text
            self.blocks.append(blk)
        self._cur = None


def _blocks_to_html(blocks: list[dict]) -> str:
    out: list[str] = []
    list_open = False
    for b in blocks:
        t = b["type"]
        if t != "li" and list_open:
            out.append("</ul>")
            list_open = False
        if t == "h":
            lvl = min(max(b["level"], 1), 3)
            if lvl == 1:
                continue  # タイトルはテンプレ側で扱う
            out.append(f'<h{lvl}>{_html_escape(b["text"])}</h{lvl}>')
        elif t == "p":
            out.append(f'<p>{_html_escape(b["text"])}</p>')
        elif t == "li":
            if not list_open:
                out.append("<ul>")
                list_open = True
            out.append(f'<li>{_html_escape(b["text"])}</li>')
        elif t == "pre":
            out.append(f'<pre><code>{_html_escape(b["text"])}</code></pre>')
        elif t == "quote":
            out.append(f'<blockquote>{_html_escape(b["text"])}</blockquote>')
        elif t == "img":
            out.append(f'<img src="{_html_escape(b["src"])}" alt="{_html_escape(b.get("alt", ""))}">')
    if list_open:
        out.append("</ul>")
    return "\n".join(out)


def cmd_normalize(args: argparse.Namespace) -> int:
    """教材を軽量 HTML に正規化し materials/<id>/index.html に置く。

    既定（--mode auto）: まずブラウザレス（urllib / ローカル HTML の本文抽出）。
    抽出テキストが --min-chars 未満なら Markdown 経路（URL は Moli、.md はそのまま）へフォールバック。
    """
    target = args.target
    p = Path(target).expanduser()
    is_url = (not p.is_file()) and target.startswith(("http://", "https://"))
    is_local_html = p.is_file() and p.suffix.lower() in (".html", ".htm")
    is_md = p.is_file() and p.suffix.lower() in (".md", ".markdown")

    def _write(body: str, title: str, used_mode: str, md_cleaned: str | None = None) -> int:
        html_doc = NORMALIZE_TEMPLATE.format(
            title=_html_escape(title), body=body, source=_html_escape(target)
        )
        lib = Path(args.materials).expanduser() / args.material_id
        lib.mkdir(parents=True, exist_ok=True)
        out = lib / "index.html"
        out.write_text(html_doc, encoding="utf-8")
        result: dict = {
            "material_id": args.material_id,
            "dir": str(lib),
            "file": str(out),
            "bytes": len(html_doc.encode("utf-8")),
            "url": f"/material/{args.material_id}/index.html",
            "title": title,
            "mode": used_mode,
            "next": (
                f'python -X utf8 tutor_cli.py dag "{out}" --material-id {args.material_id} '
                f"--pack packs --outline packs/{args.material_id}/outline.md"
            ),
        }
        if args.save_markdown and md_cleaned is not None:
            mp = lib / "source.md"
            mp.write_text(md_cleaned, encoding="utf-8")
            result["markdown"] = str(mp)
        sys.stdout.write(json.dumps(result, ensure_ascii=False, indent=2))
        sys.stdout.write("\n")
        return 0

    # --- 1) ブラウザレス経路（urllib / ローカル HTML）---
    if args.mode in ("auto", "urllib") and (is_url or is_local_html):
        html_text: str | None = None
        try:
            html_text = _fetch_url_html(target) if is_url else _decode_bytes(p.read_bytes())
        except Exception as exc:  # noqa: BLE001
            if args.mode == "urllib":
                raise SystemExit(f"取得に失敗しました（urllib）: {exc}")
        if html_text is not None:
            clean = _HtmlClean()
            clean.feed(html_text)
            blocks = clean.best_blocks()
            text_len = sum(len(b.get("text", "")) for b in blocks if b.get("text"))
            if text_len >= args.min_chars or args.mode == "urllib":
                title = args.title or clean.title or args.material_id
                title = title.split("｜")[0].strip() or title
                body = f"<h1>{_html_escape(title)}</h1>\n" + _blocks_to_html(blocks)
                return _write(body, title, "urllib" if is_url else "local-html")
            if is_local_html:
                raise SystemExit(
                    f"本文を抽出できませんでした（抽出 {text_len} 字）。--min-chars を下げてください。"
                )

    # --- 2) Markdown 経路 ---
    if is_md:
        md = p.read_text(encoding="utf-8-sig", errors="replace")
        used_mode = "md"
    elif is_url:
        md = _fetch_markdown(target)
        used_mode = "moli"
    else:
        raise SystemExit("HTML/Markdown のパス、または http(s) URL を指定してください")

    cleaned = _clean_markdown(md)
    body = _md_to_html(cleaned)
    # 画像を包む <a> を外す（クリックで外部へ飛んで教材を失うのを防ぐ。拡大は bridge が担当）
    body = re.sub(r"<a\b[^>]*>\s*(<img\b[^>]*>)\s*</a>", r"\1", body, flags=re.I)
    title = args.title
    if not title:
        m = re.search(r"^#\s+(.+)$", cleaned, re.M)
        title = m.group(1).strip() if m else args.material_id
    return _write(body, title, used_mode, md_cleaned=cleaned)


class _ImageCollector(HTMLParser):
    """教材 HTML から img を DOM 順に集め、直前の見出し index を付ける。

    見出し index は bridge の collectHeadings()（h1–h6 と role=heading を DOM 順）と一致させる。
    """

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.heading_count = 0
        self.current_heading = -1
        self.images: list[dict] = []

    def handle_starttag(self, tag: str, attrs: list) -> None:
        a = {k: (v or "") for k, v in attrs}
        if tag in ("h1", "h2", "h3", "h4", "h5", "h6") or a.get("role") == "heading":
            self.heading_count += 1
            self.current_heading = self.heading_count - 1
        elif tag == "img":
            self.images.append(
                {
                    "index": len(self.images),
                    "src": a.get("src", ""),
                    "alt": a.get("alt", ""),
                    "after_heading_index": self.current_heading,
                }
            )

    def handle_startendtag(self, tag: str, attrs: list) -> None:
        self.handle_starttag(tag, attrs)


def _ext_from_url(url: str) -> str:
    path = url.split("?")[0]
    ext = Path(path).suffix.lower()
    return ext if ext in (".png", ".jpg", ".jpeg", ".gif", ".webp", ".svg", ".bmp") else ".png"


def cmd_images(args: argparse.Namespace) -> int:
    """教材 HTML の画像を列挙（＋任意でローカル取得）。AIが直接読める local パスを返す。"""
    from urllib.request import Request, urlopen

    source, html_text = _load_material(args.target)
    parser = _ImageCollector()
    parser.feed(html_text)
    skip_re = re.compile(args.skip_re, re.I) if args.skip_re else None

    images: list[dict] = []
    media_dir = None
    if args.download_dir:
        media_dir = Path(args.download_dir).expanduser()
        media_dir.mkdir(parents=True, exist_ok=True)

    for img in parser.images:
        if skip_re and skip_re.search(img["src"] + " " + img["alt"]):
            continue
        entry = dict(img)
        if media_dir and img["src"].startswith(("http://", "https://")):
            dest = media_dir / f"img_{img['index']}{_ext_from_url(img['src'])}"
            try:
                req = Request(img["src"], headers={"User-Agent": "moli-tutor/0.1"})
                with urlopen(req, timeout=30) as resp:
                    dest.write_bytes(resp.read())
                entry["local"] = str(dest)
            except Exception as exc:  # noqa: BLE001 - 取得失敗は記録して続行
                entry["error"] = f"download_failed: {exc}"
        elif img["src"] and not img["src"].startswith(("http://", "https://", "data:")):
            p = Path(img["src"])
            entry["local"] = str((Path(source).parent / p).resolve()) if p.is_absolute() is False else str(p)
        images.append(entry)

    result: dict = {
        "source": source,
        "count": len(images),
        "images": images,
    }
    if args.pack and args.material_id:
        pd = Path(args.pack).expanduser() / args.material_id
        pd.mkdir(parents=True, exist_ok=True)
        mp = pd / "media.json"
        mp.write_text(json.dumps(images, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        result["media"] = str(mp)
    if args.out:
        op = Path(args.out).expanduser()
        op.write_text(json.dumps(images, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        result["out"] = str(op)

    sys.stdout.write(json.dumps(result, ensure_ascii=False, indent=2))
    sys.stdout.write("\n")
    return 0


class _DiagramCollector(HTMLParser):
    """教材 HTML から Mermaid / D2 のソース（テキスト）を抽出する。"""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.heading_count = 0
        self.current_heading = -1
        self.diagrams: list[dict] = []
        self._cap: dict | None = None

    def _kind_of(self, tag: str, a: dict) -> str | None:
        if tag not in ("div", "pre", "code", "script"):
            return None
        cls = a.get("class", "")
        tokens = cls.split()
        if "mermaid" in tokens or "mermaid" in cls:
            return "mermaid"
        if "d2" in tokens or "language-d2" in cls or a.get("type") in ("text/d2", "text/d2lang"):
            return "d2"
        return None

    def handle_starttag(self, tag: str, attrs: list) -> None:
        a = {k: (v or "") for k, v in attrs}
        if self._cap is None and (tag in ("h1", "h2", "h3", "h4", "h5", "h6") or a.get("role") == "heading"):
            self.heading_count += 1
            self.current_heading = self.heading_count - 1
            return
        if self._cap is not None:
            self._cap["depth"] += 1
            return
        kind = self._kind_of(tag, a)
        if kind:
            self._cap = {"kind": kind, "tag": tag, "depth": 0, "buf": []}

    def handle_startendtag(self, tag: str, attrs: list) -> None:
        self.handle_starttag(tag, attrs)

    def handle_endtag(self, tag: str) -> None:
        if self._cap is None:
            return
        if self._cap["depth"] == 0 and tag == self._cap["tag"]:
            src = "".join(self._cap["buf"]).strip()
            if src:
                self.diagrams.append(
                    {
                        "index": len(self.diagrams),
                        "kind": self._cap["kind"],
                        "source": src,
                        "after_heading_index": self.current_heading,
                    }
                )
            self._cap = None
        else:
            self._cap["depth"] -= 1

    def handle_data(self, data: str) -> None:
        if self._cap is not None:
            self._cap["buf"].append(data)


def _extract_fenced_diagrams(md: str) -> list[dict]:
    """Markdown の ```mermaid / ```d2 フェンスを抽出。"""
    out: list[dict] = []
    lines = md.replace("\r\n", "\n").split("\n")
    hcount = 0
    heading_idx = -1
    i = 0
    while i < len(lines):
        line = lines[i]
        if re.match(r"^#{1,6}\s+", line):
            hcount += 1
            heading_idx = hcount - 1
            i += 1
            continue
        fm = re.match(r"^\s*```\s*(mermaid|d2)\s*$", line, re.I)
        if fm:
            kind = fm.group(1).lower()
            buf: list[str] = []
            i += 1
            while i < len(lines) and not lines[i].strip().startswith("```"):
                buf.append(lines[i])
                i += 1
            i += 1
            src = "\n".join(buf).strip()
            if src:
                out.append({"index": len(out), "kind": kind, "source": src, "after_heading_index": heading_idx})
            continue
        i += 1
    return out


def cmd_diagrams(args: argparse.Namespace) -> int:
    """教材の Mermaid / D2 のソースを抽出し diagrams.json に保存（AIがテキストで読める）。"""
    source, text = _load_material(args.target)
    if source.lower().endswith((".md", ".markdown")):
        diagrams = _extract_fenced_diagrams(text)
    else:
        parser = _DiagramCollector()
        parser.feed(text)
        diagrams = parser.diagrams

    result: dict = {"source": source, "count": len(diagrams), "diagrams": diagrams}
    if args.pack and args.material_id:
        pd = Path(args.pack).expanduser() / args.material_id
        pd.mkdir(parents=True, exist_ok=True)
        dp = pd / "diagrams.json"
        dp.write_text(json.dumps(diagrams, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        result["diagrams_file"] = str(dp)
    if args.out:
        op = Path(args.out).expanduser()
        op.write_text(json.dumps(diagrams, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        result["out"] = str(op)

    sys.stdout.write(json.dumps(result, ensure_ascii=False, indent=2))
    sys.stdout.write("\n")
    return 0


def cmd_section(args: argparse.Namespace) -> int:
    """特定の箇所の詳細を低負荷で取得（DAG に無い本文・図・画像）。

    - --heading-index N : DAG ノード番号で指定（bridge/DAG と同じ 0 始まり）
    - --heading TEXT     : 見出しテキストの部分一致で指定
    - --query TEXT       : 全節から語を検索し、該当節の一覧＋snippet を返す（本文は取らない）
    既定では本文を --max-chars で切る（--full で全文）。
    """
    source, html_text = _load_material(args.target)
    headings, bodies = _headings_and_sections(_extract_doc(html_text))

    def snip(text: str) -> str:
        t = text or ""
        n = args.snippet_chars
        return t if len(t) <= n else t[:n] + "…"

    if args.query and args.heading_index is None and args.heading is None:
        q = args.query.lower()
        matches = []
        for i, h in enumerate(headings):
            body = bodies[i] if i < len(bodies) else ""
            if q in (h["text"] + " " + body).lower():
                matches.append(
                    {"heading_index": i, "heading": h["text"], "level": h["level"], "snippet": snip(body)}
                )
        sys.stdout.write(
            json.dumps(
                {"source": source, "query": args.query, "count": len(matches), "matches": matches[: args.limit or 20]},
                ensure_ascii=False,
                indent=2,
            )
            + "\n"
        )
        return 0

    idx = args.heading_index
    if idx is None and args.heading is not None:
        for i, h in enumerate(headings):
            if args.heading in h["text"]:
                idx = i
                break
    if idx is None:
        raise SystemExit("--heading-index / --heading / --query のいずれかを指定してください")
    if idx < 0 or idx >= len(headings):
        raise SystemExit(f"heading_index {idx} は範囲外です（0..{len(headings) - 1}）")

    body = bodies[idx] if idx < len(bodies) else ""
    maxc = 0 if args.full else (args.max_chars or 2000)
    shown = body if maxc <= 0 or len(body) <= maxc else body[:maxc] + "…"

    imgs = _ImageCollector()
    imgs.feed(html_text)
    dias = _DiagramCollector()
    dias.feed(html_text)
    section_images = [im for im in imgs.images if im.get("after_heading_index") == idx]
    section_diagrams = [d for d in dias.diagrams if d.get("after_heading_index") == idx]

    subs = []
    for j in range(idx + 1, len(headings)):
        if headings[j]["level"] <= headings[idx]["level"]:
            break
        subs.append({"heading_index": j, "level": headings[j]["level"], "heading": headings[j]["text"]})

    out = {
        "source": source,
        "heading_index": idx,
        "heading": headings[idx]["text"],
        "level": headings[idx]["level"],
        "chars": len(body),
        "truncated": len(shown) < len(body),
        "body": shown,
        "subheadings": subs,
        "images": section_images,
        "diagrams": section_diagrams,
    }
    sys.stdout.write(json.dumps(out, ensure_ascii=False, indent=2) + "\n")
    return 0


def _short_name(name: str) -> str:
    return re.sub(r"^[0-9０-９\.\s\u3000]+", "", name or "").strip() or (name or "")


def _build_spine(nodes: list[dict], material_id: str) -> list[dict]:
    """DAG ノードから会話の基本線（dialogue spine）を機械的に下書きする（LLM不使用・型v0.2）。

    型v0.2: 説明の種（goal）1 + 山場の問い（ask）1 + on_fail + on_pass（+ preempt）。
    想起の確認（check_light）や汎用質問バンクは持たない。ask / preempt / shallow は AI が節ごとに推敲する。
    """
    out: list[dict] = []
    for i, n in enumerate(nodes):
        idx = n.get("heading_index")
        name = n.get("name", "")
        summary = (n.get("summary") or "").strip()
        goal = summary or name
        if len(goal) > 120:
            goal = goal[:120] + "…"
        nid = f"KC_{material_id}_{idx}"
        nxt = f"KC_{material_id}_{nodes[i + 1]['heading_index']}" if i + 1 < len(nodes) else "END"
        spine = [
            {"beat": "act", "heading_index": idx},
            {"beat": "ask", "text": "この節のキモ（なぜ・どう）を、あなたの言葉で言うと？"},
            {"beat": "on_fail", "text": "浅化: 具体例・身近な例に1段下げる（shallow_example 参照）"},
            {"beat": "on_pass", "text": f"次へ: {nxt}"},
        ]
        out.append(
            {
                "node_id": nid,
                "heading_index": idx,
                "name": name,
                "type": n.get("type"),
                "depth_start": 0,
                "goal": goal,
                "spine": spine,
                "preempt": "",
                "fallbacks": {"fragile": n.get("type") == "prerequisite", "shallow_example": ""},
            }
        )
    return out


def _spine_to_markdown(material_id: str, source: str, nodes: list[dict]) -> str:
    lines = [
        f"# dialogue spine（基本線）— {material_id}",
        "",
        f"> 生成: `tutor_cli.py spine`（DAG から機械的下書き・型v0.2）。教材: `{source}`",
        "> 目的: 短ターンで速く回す会話のレール。**説明1＋山場の問い1**に絞る。**AI がノードごとに推敲**して使う。",
        "",
        "## テンポ規律（v0.2）",
        "- 1ターン = 説明 2〜3文 + **山場の問い1問だけ**（想起の確認はしない）。8割で次へ。",
        "- **予測→答え合わせ**: 「どうなると思う？」を先に。外れても1往復で理解が動く。",
        "- 詰まり=`on_fail`（具体へ浅化）。通過=`on_pass`（次節へ）。",
        "- 指す操作: `act --heading-index N`（beat に埋め込み済み）。",
        "- **先回り**（preempt）: 予測される摩擦は最初の説明で触れる（浅化の往復を消す）。",
        "",
        "---",
        "",
    ]
    for s in nodes:
        lines.append(f"## node idx{s['heading_index']} — {s['name']}（{s.get('type')}）")
        lines.append(f"- goal: {s['goal']}")
        lines.append("- spine:")
        for b in s["spine"]:
            if b["beat"] == "act":
                lines.append(f"  - `act` — heading_index {b['heading_index']}")
            else:
                lines.append(f"  - `{b['beat']}` — {b.get('text', '')}")
        lines.append(f"- preempt: {s.get('preempt') or '—'}")
        lines.append(f"- shallow_example: {s['fallbacks'].get('shallow_example', '') or '（未記入）'}")
        lines.append("")
    return "\n".join(lines)


def cmd_spine(args: argparse.Namespace) -> int:
    """DAG から会話の基本線（dialogue spine）を下書きし packs/<id>/ に保存する（汎用）。"""
    source, html_text = _load_material(args.target)
    headings, bodies = _headings_and_sections(_extract_doc(html_text))
    dag_args = argparse.Namespace(
        no_skip=False, skip_re=None, prereq_re=None, max_level=args.max_level, include_h1=False,
        include_re=None, exclude_re=args.exclude_re, summary=True,
        summary_chars=160, summary_sentences=2, limit=args.limit,
    )
    nodes = _headings_to_dag(headings, bodies, dag_args)
    spines = _build_spine(nodes, args.material_id or "material")

    result: dict = {"source": source, "material_id": args.material_id, "count": len(spines), "nodes": spines}
    if args.pack and args.material_id:
        pd = Path(args.pack).expanduser() / args.material_id
        pd.mkdir(parents=True, exist_ok=True)
        jp = pd / "dialogue_spine.json"
        jp.write_text(json.dumps(spines, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        result["json"] = str(jp)
        md = _spine_to_markdown(args.material_id, source, spines)
        mp = pd / "dialogue_spine.md"
        mp.write_text(md, encoding="utf-8")
        result["markdown"] = str(mp)
    if args.out:
        op = Path(args.out).expanduser()
        op.write_text(json.dumps(spines, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        result["out"] = str(op)

    sys.stdout.write(json.dumps(result, ensure_ascii=False, indent=2))
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
    p_act.add_argument("--highlight-image", dest="highlight_image", type=int, help="画像 index（DOM順・media.json と一致）をハイライト＋スクロール")
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

    p_norm = sub.add_parser("normalize", help="URL/Markdown を軽量 HTML に正規化して materials/<id>/ に置く")
    p_norm.add_argument("target", help="URL または Markdown(.md) パス")
    p_norm.add_argument("--material-id", dest="material_id", required=True)
    p_norm.add_argument("--materials", default="materials", help="教材ライブラリのディレクトリ（既定 materials）")
    p_norm.add_argument("--title", default=None, help="タイトル上書き（既定: Markdown の H1）")
    p_norm.add_argument("--save-markdown", dest="save_markdown", action="store_true", help="正規化後の Markdown も保存")
    p_norm.add_argument("--mode", choices=("auto", "urllib", "moli"), default="auto", help="取り込み経路（既定 auto: ブラウザレス優先）")
    p_norm.add_argument("--min-chars", dest="min_chars", type=int, default=300, help="ブラウザレス抽出の最低本文文字数（既定 300。下回ると Moli へフォールバック）")
    p_norm.set_defaults(func=cmd_normalize)

    p_img = sub.add_parser("images", help="教材 HTML の画像を列挙（＋任意でローカル取得）し media.json に保存")
    p_img.add_argument("target", help="HTML のパスまたは URL")
    p_img.add_argument("--material-id", dest="material_id", default=None, help="--pack と併用で media.json を置く")
    p_img.add_argument("--pack", default=None, help="<pack>/<id>/media.json に保存（要 --material-id）")
    p_img.add_argument("--download-dir", dest="download_dir", default=None, help="リモート画像の保存先（AIが読む用）")
    p_img.add_argument("--out", default=None, help="画像配列の書き出し先ファイル")
    p_img.add_argument("--skip-re", dest="skip_re", default=None, help="src/alt が一致する画像を除外（アイコン等）")
    p_img.set_defaults(func=cmd_images)

    p_dia = sub.add_parser("diagrams", help="教材の Mermaid / D2 ソースを抽出し diagrams.json に保存")
    p_dia.add_argument("target", help="HTML / Markdown のパスまたは URL")
    p_dia.add_argument("--material-id", dest="material_id", default=None, help="--pack と併用で diagrams.json を置く")
    p_dia.add_argument("--pack", default=None, help="<pack>/<id>/diagrams.json に保存（要 --material-id）")
    p_dia.add_argument("--out", default=None, help="図配列の書き出し先ファイル")
    p_dia.set_defaults(func=cmd_diagrams)

    p_sec = sub.add_parser("section", help="特定の箇所の詳細を低負荷で取得（本文・図・画像）")
    p_sec.add_argument("target", help="HTML のパスまたは URL")
    p_sec.add_argument("--heading-index", dest="heading_index", type=int, default=None, help="DAG/bridge と同じ 0 始まりの見出し番号")
    p_sec.add_argument("--heading", default=None, help="見出しテキストの部分一致")
    p_sec.add_argument("--query", default=None, help="全節から語を検索（本文は取らず該当節の一覧を返す）")
    p_sec.add_argument("--full", action="store_true", help="本文を切らずに全文返す")
    p_sec.add_argument("--max-chars", dest="max_chars", type=int, default=2000, help="本文の最大文字数（既定 2000）")
    p_sec.add_argument("--snippet-chars", dest="snippet_chars", type=int, default=160, help="--query の1件あたり冒頭字数（既定 160）")
    p_sec.add_argument("--limit", type=int, default=20, help="--query の最大件数（既定 20）")
    p_sec.set_defaults(func=cmd_section)

    p_sp = sub.add_parser("spine", help="DAG から会話の基本線（dialogue spine）を下書きして packs/<id>/ に保存")
    p_sp.add_argument("target", help="HTML のパスまたは URL")
    p_sp.add_argument("--material-id", dest="material_id", required=True)
    p_sp.add_argument("--pack", default="packs", help="保存先のベース（既定 packs）")
    p_sp.add_argument("--max-level", dest="max_level", type=int, default=3, help="含める見出しの最大レベル（既定 3）")
    p_sp.add_argument("--exclude-re", dest="exclude_re", default=None, help="除外する見出しの正規表現")
    p_sp.add_argument("--limit", type=int, default=0, help="ノード数の上限（0=無制限）")
    p_sp.add_argument("--out", default=None, help="JSON の書き出し先（任意）")
    p_sp.set_defaults(func=cmd_spine)

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
