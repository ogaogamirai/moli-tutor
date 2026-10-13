#!/usr/bin/env python3
"""Moli-Tutor smoke test (dependency-free).

Run:  python -X utf8 tests/smoke.py

Covers the paths that do not need a browser:
  1. D2 sections are compiled to SVG (or a graceful error box) in _preprocess_state.
  2. State passthrough (dag / text sections) is untouched.
  3. The mini HTTP server serves /shell.html and /api/state.
  4. shell.html contains the learning-map (DAG) and collapsible-board hooks.
  5. tutor_state.example.json is valid and carries the expected keys.
"""
from __future__ import annotations

import json
import shutil
import subprocess
import sys
import tempfile
import types
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

# tutor_cockpit imports pywebview at module load; stub it so the test runs headless.
sys.modules.setdefault("webview", types.ModuleType("webview"))

import tutor_cockpit  # noqa: E402
import tutor_http  # noqa: E402
import tutor_cli  # noqa: E402

FAILURES: list[str] = []


def check(name: str, cond: bool) -> None:
    print(("PASS " if cond else "FAIL ") + name)
    if not cond:
        FAILURES.append(name)


def test_d2_preprocess() -> None:
    state = {"sections": [{"id": "d", "type": "d2", "content": "a -> b"}]}
    out = tutor_cockpit._preprocess_state(state)
    sec = out["sections"][0]
    check("d2: d2_source preserved", sec.get("d2_source") == "a -> b")
    if (ROOT.parent / "d2" / "d2.exe").is_file():
        content = str(sec.get("content", "")).lower()
        check("d2: content compiled to svg", "<svg" in content)
    else:
        print("SKIP d2: compile (d2.exe not found)")


def test_passthrough() -> None:
    state = {
        "dag": [{"id": "n", "name": "N", "type": "concept", "status": "active"}],
        "sections": [{"id": "t", "type": "text", "content": "x"}],
        "board_visible": True,
    }
    out = tutor_cockpit._preprocess_state(state)
    check("passthrough: dag preserved", out["dag"][0]["id"] == "n")
    check("passthrough: text section untouched", out["sections"][0]["content"] == "x")
    check("passthrough: board_visible preserved", out.get("board_visible") is True)


def test_http() -> None:
    sample = {
        "board_visible": True,
        "dag": [{"id": "n1", "name": "N1", "type": "concept", "status": "active", "target_text": "x"}],
        "sections": [{"id": "s", "type": "text", "content": "hello"}],
    }
    server = tutor_http.serve(
        ROOT / "static", None, "127.0.0.1", 0, state_callback=lambda: sample
    )
    try:
        port = server.server_address[1]
        with urllib.request.urlopen(f"http://127.0.0.1:{port}/api/state", timeout=5) as r:
            data = json.loads(r.read().decode("utf-8"))
        check("http: /api/state returns dag", data["dag"][0]["id"] == "n1")
        with urllib.request.urlopen(f"http://127.0.0.1:{port}/shell.html", timeout=5) as r:
            html = r.read().decode("utf-8")
        check("http: /shell.html served", "Moli-Tutor" in html)
        try:
            urllib.request.urlopen(f"http://127.0.0.1:{port}/material/nope.html", timeout=5)
            blocked = False
        except urllib.error.HTTPError as e:
            blocked = e.code == 404
        check("http: unknown path is 404", blocked)
    finally:
        server.shutdown()


def test_http_nul_path() -> None:
    """A path with an embedded NUL must be rejected (404), not crash the handler."""
    server = tutor_http.serve(ROOT / "static", None, "127.0.0.1", 0, state_callback=lambda: {})
    try:
        port = server.server_address[1]
        try:
            urllib.request.urlopen(f"http://127.0.0.1:{port}/material/a%00b", timeout=5)
            code: object = 200
        except urllib.error.HTTPError as e:
            code = e.code
        except Exception as e:  # noqa: BLE001
            code = "EXC:" + type(e).__name__
        check("http: NUL path -> 404 (no crash)", code == 404)
    finally:
        server.shutdown()


def test_shell_hooks() -> None:
    html = (ROOT / "static" / "shell.html").read_text(encoding="utf-8")
    for needle in (
        'id="dag-map"',
        'id="dag-list"',
        'id="material-error"',
        "function renderDagMap",
        "function jumpToDagNode",
        "function dagNodeToAction",
        "function checkMaterialError",
        "function describeAction",
        "function refreshStatus",
        "clear_highlight",
        "heading_index",
        "board_visible",
        'setLayout(savedLayout || "left-only")',
        'setLayout("split", false);',
    ):
        check("shell: " + needle, needle in html)


def test_shell_render() -> None:
    """Render the DAG map headlessly (node + a tiny DOM shim). Skips if node is absent."""
    node = shutil.which("node")
    if not node:
        print("SKIP shell: DAG map render (node not found)")
        return
    proc = subprocess.run(
        [node, str(ROOT / "tests" / "shell_render_check.mjs")],
        capture_output=True,
        text=True,
    )
    for line in proc.stdout.splitlines():
        print("  " + line)
    check("shell: DAG map renders from state.dag (node)", proc.returncode == 0)


def test_bridge_anchor() -> None:
    """Heading anchoring (by index / normalized text). Skips if node is absent."""
    node = shutil.which("node")
    if not node:
        print("SKIP bridge: heading anchor (node not found)")
        return
    proc = subprocess.run(
        [node, str(ROOT / "tests" / "bridge_anchor_check.mjs")],
        capture_output=True,
        text=True,
    )
    for line in proc.stdout.splitlines():
        print("  " + line)
    check("bridge: heading anchors by index and normalized text (node)", proc.returncode == 0)


def test_load_state_bom() -> None:
    with tempfile.TemporaryDirectory() as d:
        p = Path(d) / "state.json"
        p.write_bytes(b"\xef\xbb\xbf" + json.dumps({"action_request": {"id": 5}}).encode("utf-8"))
        st = tutor_cockpit._load_state(p)
        check("load_state: tolerates UTF-8 BOM", st["action_request"]["id"] == 5)


def test_act_cli() -> None:
    with tempfile.TemporaryDirectory() as d:
        p = Path(d) / "state.json"
        p.write_text(json.dumps({"action_request": {"id": 10}}), encoding="utf-8")

        def run(*extra: str) -> subprocess.CompletedProcess:
            return subprocess.run(
                [sys.executable, "-X", "utf8", str(ROOT / "tutor_cli.py"), "act", "--state", str(p), *extra],
                capture_output=True,
                text=True,
            )

        run("--scroll-to", "半環")
        st1 = json.loads(p.read_text(encoding="utf-8"))
        check(
            "act: id -> 11, scroll_to target_text",
            st1["action_request"]["id"] == 11 and st1["action_request"]["target_text"] == "半環",
        )
        run("--heading-index", "26")
        st2 = json.loads(p.read_text(encoding="utf-8"))
        check(
            "act: id -> 12, heading_index",
            st2["action_request"]["id"] == 12 and st2["action_request"]["heading_index"] == 26,
        )
        run("--clear-highlight")
        st3 = json.loads(p.read_text(encoding="utf-8"))
        check("act: clear_highlight", st3["action_request"]["type"] == "clear_highlight")
        check("act: no action -> non-zero exit", run().returncode != 0)


FIXTURE = ROOT / "tests" / "fixtures" / "sample_material.html"


def test_heading_parser() -> None:
    hs = tutor_cli._extract_headings_from_html(FIXTURE.read_text(encoding="utf-8"))
    check("parser: 8 headings in DOM order", len(hs) == 8)
    check("parser: h2 text + id", hs[1]["text"] == "はじめに" and hs[1]["id"] == "intro")
    check("parser: nested tag text joined", hs[4]["text"] == "1.1 min の話" and hs[4]["level"] == 3)
    check("parser: role=heading + aria-level", hs[5]["text"] == "1.2 ロール見出し" and hs[5]["level"] == 3)
    check("parser: whitespace normalized", hs[7]["text"] == "余白 つき 見出し")
    check("parser: ignores tags inside <script>", all("見出しではない" not in h["text"] for h in hs))


def test_dag_cli() -> None:
    def run(*extra: str) -> dict:
        proc = subprocess.run(
            [sys.executable, "-X", "utf8", str(ROOT / "tutor_cli.py"), "dag", str(FIXTURE), *extra],
            capture_output=True,
            text=True,
        )
        return json.loads(proc.stdout)

    default = run()
    idx = [n["heading_index"] for n in default["dag"]]
    check("dag: default keeps 5 (skips h1/目次/h4)", idx == [1, 3, 4, 5, 7])
    check("dag: はじめに -> prerequisite", default["dag"][0]["type"] == "prerequisite")
    check("dag: heading text carried for anchor", default["dag"][0]["heading"] == "はじめに")
    check("dag: node carries summary from section body", default["dag"][0].get("summary", "").startswith("導入の本文"))
    check("dag: node carries chars", default["dag"][0].get("chars") == 6)

    full = run("--include-h1", "--no-skip", "--max-level", "4")
    check("dag: include-h1/no-skip/max4 -> 8", full["count"] == 8)

    with tempfile.TemporaryDirectory() as d:
        outline = Path(d) / "outline.md"
        run("--outline", str(outline))
        txt = outline.read_text(encoding="utf-8")
        check("dag: outline written", "# 教材アウトライン" in txt and "[1] はじめに" in txt)


def test_summarize() -> None:
    s = tutor_cli._summarize
    check("summarize: english keeps sentence space", s("First point. Second point.", 160, 2) == "First point. Second point.")
    check("summarize: english abbreviation intact", s("See e.g. papers for details.", 160, 2) == "See e.g. papers for details.")
    check("summarize: japanese no added space", s("これは一つ目。次は二つ目。", 160, 2) == "これは一つ目。次は二つ目。")
    check("summarize: max_chars truncates with ellipsis", s("A" * 50 + ". " + "B" * 50, 20, 2).endswith("…"))
    check("summarize: empty -> empty", s("   ", 160, 2) == "")


def test_status_load() -> None:
    with tempfile.TemporaryDirectory() as d:
        base = Path(d)
        state = base / "state.json"
        packs = base / "packs"

        def cli(*a: str) -> subprocess.CompletedProcess:
            return subprocess.run(
                [sys.executable, "-X", "utf8", str(ROOT / "tutor_cli.py"), *a],
                capture_output=True,
                text=True,
            )

        cli("dag", str(FIXTURE), "--material-id", "sample", "--pack", str(packs), "--state", str(state))
        check("dag --pack: dag.json written", (packs / "sample" / "dag.json").is_file())

        s = cli("status", "--state", str(state))
        check("status: material + progress shown", "material: sample" in s.stdout and "progress: 0/" in s.stdout)

        st = json.loads(state.read_text(encoding="utf-8"))
        st["dag"] = []
        state.write_text(json.dumps(st, ensure_ascii=False), encoding="utf-8")
        cli("load", "--material-id", "sample", "--state", str(state), "--pack", str(packs))
        st2 = json.loads(state.read_text(encoding="utf-8"))
        check("load: dag restored from pack", len(st2["dag"]) == 5 and st2["material_id"] == "sample")

        sj = cli("status", "--state", str(state), "--json")
        check("status --json: progress total", json.loads(sj.stdout)["progress"]["total"] == 5)


def test_multi_root() -> None:
    with tempfile.TemporaryDirectory() as d:
        base = Path(d)
        r1 = base / "r1"
        r2 = base / "r2"
        r1.mkdir()
        r2.mkdir()
        (r1 / "a.html").write_text("A", encoding="utf-8")
        (r2 / "b.html").write_text("B", encoding="utf-8")
        server = tutor_http.serve(ROOT / "static", [r1, r2], "127.0.0.1", 0, state_callback=lambda: {})
        try:
            port = server.server_address[1]

            def get(path: str) -> str:
                with urllib.request.urlopen(f"http://127.0.0.1:{port}{path}", timeout=5) as r:
                    return r.read().decode()

            check("multi-root: file served from root 1", get("/material/a.html") == "A")
            check("multi-root: file served from root 2", get("/material/b.html") == "B")
        finally:
            server.shutdown()


def test_add_open() -> None:
    with tempfile.TemporaryDirectory() as d:
        base = Path(d)
        mats = base / "materials"
        state = base / "state.json"

        def cli(*a: str) -> subprocess.CompletedProcess:
            return subprocess.run(
                [sys.executable, "-X", "utf8", str(ROOT / "tutor_cli.py"), *a],
                capture_output=True,
                text=True,
            )

        cli("add-material", str(FIXTURE), "--material-id", "demo", "--materials", str(mats))
        check("add-material: html copied to index.html", (mats / "demo" / "index.html").is_file())

        cli("open", "--material-id", "demo", "--state", str(state))
        st = json.loads(state.read_text(encoding="utf-8"))
        check(
            "open: url points at the material",
            st["url"].endswith("/material/demo/index.html") and st["material_id"] == "demo",
        )


def test_example_state() -> None:
    ex = json.loads((ROOT / "tutor_state.example.json").read_text(encoding="utf-8"))
    check("example: valid json with dag", isinstance(ex.get("dag"), list) and len(ex["dag"]) > 0)
    check("example: has board_visible", "board_visible" in ex)


def main() -> int:
    test_d2_preprocess()
    test_passthrough()
    test_http()
    test_http_nul_path()
    test_shell_hooks()
    test_shell_render()
    test_bridge_anchor()
    test_load_state_bom()
    test_act_cli()
    test_heading_parser()
    test_dag_cli()
    test_summarize()
    test_status_load()
    test_multi_root()
    test_add_open()
    test_example_state()
    print()
    if FAILURES:
        print(f"SMOKE FAILED: {len(FAILURES)} check(s): {', '.join(FAILURES)}")
        return 1
    print("SMOKE OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
