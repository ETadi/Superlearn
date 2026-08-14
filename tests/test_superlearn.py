"""Superlearn test suite — stdlib only, no network, no browser.

Covers the validator's contract (examples pass, bad boards fail), the
exporter's script-context neutralization, the server's API round-trip with
its security guards, and — when node is available — the app's JS syntax.

Run:  python3 -m unittest discover -s tests -v
"""

from __future__ import annotations

import http.client
import json
import pathlib
import shutil
import socket
import subprocess
import sys
import tempfile
import time
import unittest

ROOT = pathlib.Path(__file__).resolve().parent.parent
SCRIPTS = ROOT / "scripts"
sys.path.insert(0, str(SCRIPTS))

from export_html import build_standalone_html  # noqa: E402


def run_validator(board: dict) -> subprocess.CompletedProcess:
    """The validator's contract is its CLI: exit 0 clean, 1 on errors."""
    with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False) as f:
        json.dump(board, f)
        path = f.name
    try:
        return subprocess.run(
            [sys.executable, str(SCRIPTS / "validate_board.py"), path],
            capture_output=True, text=True,
        )
    finally:
        pathlib.Path(path).unlink(missing_ok=True)


def minimal_board(**over) -> dict:
    board = {
        "id": "test-board",
        "topic": "testing",
        "title": "A test board",
        "emoji": "🧪",
        "layout": "board",
        "depth": "standard",
        "theme": {"preset": "midnight"},
        "blocks": [{"type": "summary", "title": "Overview", "markdown": "Hello."}],
        "sources": [],
    }
    board.update(over)
    return board


class ValidatorTests(unittest.TestCase):
    def test_shipped_examples_validate_clean(self):
        for example in sorted((ROOT / "examples").glob("*.json")):
            with self.subTest(example=example.name):
                r = subprocess.run(
                    [sys.executable, str(SCRIPTS / "validate_board.py"), str(example)],
                    capture_output=True, text=True,
                )
                self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
                self.assertIn("0 warning(s)", r.stdout)

    def test_minimal_board_passes(self):
        self.assertEqual(run_validator(minimal_board()).returncode, 0)

    def test_quiz_blocks_are_rejected(self):
        board = minimal_board()
        board["blocks"].append({"type": "quiz", "title": "Nope", "questions": []})
        r = run_validator(board)
        self.assertEqual(r.returncode, 1)
        self.assertIn("quiz", r.stdout)

    def test_bad_video_id_is_rejected(self):
        board = minimal_board()
        board["blocks"].append({"type": "video", "title": "V", "videoId": "not-a-real-id!"})
        self.assertEqual(run_validator(board).returncode, 1)

    def test_bar_chart_length_mismatch_is_rejected(self):
        board = minimal_board()
        board["blocks"].append({
            "type": "chart", "title": "C", "chart": "bar", "yLabel": "y",
            "categories": ["a", "b", "c"],
            "series": [{"name": "s", "values": [1, 2]}],
        })
        r = run_validator(board)
        self.assertEqual(r.returncode, 1)
        self.assertIn("must line up", r.stdout)

    def test_image_requires_alt_and_http_url(self):
        board = minimal_board()
        board["blocks"].append({"type": "image", "title": "I", "url": "javascript:alert(1)", "alt": "x"})
        self.assertEqual(run_validator(board).returncode, 1)
        board = minimal_board()
        board["blocks"].append({"type": "image", "title": "I", "url": "https://example.com/a.png"})
        self.assertEqual(run_validator(board).returncode, 1)

    def test_partial_sections_warn_but_pass(self):
        board = minimal_board()
        board["blocks"][0]["section"] = "Start"
        board["blocks"].append({"type": "note", "title": "N", "markdown": "hi"})
        r = run_validator(board)
        self.assertEqual(r.returncode, 0)
        self.assertIn("More", r.stdout)

    def test_canvas_positions_shape_is_enforced(self):
        board = minimal_board(canvas={"Start": {"x": "left", "y": 2}})
        self.assertEqual(run_validator(board).returncode, 1)
        board = minimal_board(canvas={"Start": {"x": 10, "y": 20}})
        self.assertEqual(run_validator(board).returncode, 0)


class ExporterTests(unittest.TestCase):
    APP = (ROOT / "app" / "index.html").read_text(encoding="utf-8")

    def test_script_context_is_neutralized(self):
        board = minimal_board()
        board["blocks"][0]["markdown"] = "evil </script><script>alert(1)</script>" + chr(0x2028) + "end"
        html = build_standalone_html(self.APP, board)
        payload_start = html.index("SUPERLEARN_EMBEDDED_BOARD")
        payload = html[payload_start:html.index("</script>", payload_start)]
        self.assertNotIn("</script", payload)      # breakout is impossible
        self.assertNotIn(chr(0x2028), payload)   # legal JSON, illegal JS literal
        self.assertIn("\\u003c", payload)
        # And it round-trips: the escapes decode back to the original text.
        raw = payload.split("=", 1)[1].strip().rstrip(";")
        self.assertIn("</script>", json.loads(raw)["blocks"][0]["markdown"])

    def test_embedded_marker_precedes_app_script(self):
        html = build_standalone_html(self.APP, minimal_board())
        self.assertLess(html.index("SUPERLEARN_EMBEDDED_BOARD"), html.index('"use strict"'))


class ServerTests(unittest.TestCase):
    """Round-trips the real server on a loopback port."""

    @classmethod
    def setUpClass(cls):
        cls.dir = tempfile.mkdtemp(prefix="superlearn-test-")
        boards = pathlib.Path(cls.dir) / "boards"
        boards.mkdir()
        research = pathlib.Path(cls.dir) / "research"
        research.mkdir()
        (research / "note.md").write_text("# a note", encoding="utf-8")
        (boards / "test-board.json").write_text(json.dumps(minimal_board()), encoding="utf-8")
        with socket.socket() as s:
            s.bind(("127.0.0.1", 0))
            cls.port = s.getsockname()[1]
        cls.proc = subprocess.Popen(
            [sys.executable, str(SCRIPTS / "serve.py"),
             "--boards-dir", str(boards), "--research-dir", str(research),
             "--port", str(cls.port)],
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
        )
        for _ in range(50):
            try:
                if cls.get("/api/health")[0] == 200:
                    break
            except OSError:
                time.sleep(0.1)
        else:
            raise RuntimeError("server never came up")

    @classmethod
    def tearDownClass(cls):
        cls.proc.terminate()
        cls.proc.wait(timeout=5)
        shutil.rmtree(cls.dir, ignore_errors=True)

    @classmethod
    def get(cls, path, host=None):
        conn = http.client.HTTPConnection("127.0.0.1", cls.port, timeout=5)
        headers = {"Host": host} if host else {}
        conn.request("GET", path, headers=headers)
        r = conn.getresponse()
        body = r.read()
        conn.close()
        return r.status, body

    def test_health_and_listing(self):
        status, body = self.get("/api/health")
        self.assertEqual(status, 200)
        self.assertTrue(json.loads(body)["ok"])
        status, body = self.get("/api/boards")
        self.assertEqual(status, 200)
        self.assertEqual(json.loads(body)[0]["id"], "test-board")

    def test_put_round_trip(self):
        board = minimal_board()
        board["blocks"][0]["annotation"] = "my note"
        conn = http.client.HTTPConnection("127.0.0.1", self.port, timeout=5)
        conn.request("PUT", "/api/boards/test-board", body=json.dumps(board),
                     headers={"Content-Type": "application/json"})
        self.assertEqual(conn.getresponse().status, 200)
        conn.close()
        status, body = self.get("/api/boards/test-board")
        self.assertEqual(json.loads(body)["blocks"][0]["annotation"], "my note")

    def test_put_rejects_bad_ids_and_bodies(self):
        conn = http.client.HTTPConnection("127.0.0.1", self.port, timeout=5)
        conn.request("PUT", "/api/boards/test-board", body='{"not": "a board"}',
                     headers={"Content-Type": "application/json"})
        self.assertEqual(conn.getresponse().status, 400)
        conn.close()

    def test_path_traversal_is_blocked(self):
        status, _ = self.get("/api/research/file?path=../../../../etc/passwd")
        self.assertEqual(status, 404)
        status, body = self.get("/api/research/file?path=note.md")
        self.assertEqual(status, 200)
        self.assertIn(b"a note", body)

    def test_dns_rebinding_host_is_refused(self):
        status, _ = self.get("/api/boards", host="evil.example.com")
        self.assertEqual(status, 403)
        status, _ = self.get("/api/boards", host=f"localhost:{self.port}")
        self.assertEqual(status, 200)


class AppTests(unittest.TestCase):
    def test_manifests_are_valid(self):
        plugin = json.loads((ROOT / ".claude-plugin" / "plugin.json").read_text())
        self.assertEqual(plugin["name"], "superlearn")
        market = json.loads((ROOT / ".claude-plugin" / "marketplace.json").read_text())
        self.assertEqual(market["plugins"][0]["name"], "superlearn")

    @unittest.skipUnless(shutil.which("node"), "node not installed")
    def test_app_javascript_parses(self):
        html = (ROOT / "app" / "index.html").read_text(encoding="utf-8")
        start = html.index('<script>\n"use strict"') + len("<script>")
        js = html[start:html.rindex("</script>")]
        with tempfile.NamedTemporaryFile("w", suffix=".js", delete=False, encoding="utf-8") as f:
            f.write(js)
            path = f.name
        try:
            r = subprocess.run(["node", "--check", path], capture_output=True, text=True)
            self.assertEqual(r.returncode, 0, r.stderr)
        finally:
            pathlib.Path(path).unlink(missing_ok=True)


if __name__ == "__main__":
    unittest.main()
