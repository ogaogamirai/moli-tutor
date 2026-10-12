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
        "function checkMaterialError",
        "board_visible",
        'setLayout(savedLayout || "left-only")',
        'setLayout("split");',
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
    test_example_state()
    print()
    if FAILURES:
        print(f"SMOKE FAILED: {len(FAILURES)} check(s): {', '.join(FAILURES)}")
        return 1
    print("SMOKE OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
