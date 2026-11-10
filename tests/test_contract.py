"""One subprocess/HTTP contract suite runs against both native launchers.

Only synthetic loopback endpoints are contacted. No product tool is executed.
CHANS_NODE_COMMAND/CHANS_PYTHON_COMMAND can point at installed release artifacts.
"""

import contextlib
import json
import os
import queue
import shlex
import signal
import subprocess
import sys
import threading
import time
import unittest
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

CF_ENV = {
    "CF_ACCESS_CLIENT_ID": "fixture-access-id.access",
    "CF_ACCESS_CLIENT_SECRET": "fixture-access-secret",
}
CF_HEADERS = {
    "CF-Access-Client-Id": CF_ENV["CF_ACCESS_CLIENT_ID"],
    "CF-Access-Client-Secret": CF_ENV["CF_ACCESS_CLIENT_SECRET"],
}


def clean_environment():
    return {name: value for name, value in os.environ.items() if name not in CF_ENV}


ROOT = Path(__file__).resolve().parents[1]
TOOL = json.loads((ROOT / "contracts/tool.json").read_text())
COMMANDS = {
    "node": shlex.split(os.environ.get("CHANS_NODE_COMMAND", "node packages/node/src/cli.js")),
    "python": shlex.split(os.environ["CHANS_PYTHON_COMMAND"])
    if os.environ.get("CHANS_PYTHON_COMMAND")
    else [
        sys.executable,
        "-c",
        "from chans_mcp.cli import main; raise SystemExit(main())",
    ],
}


class Endpoint(ThreadingHTTPServer):
    daemon_threads = True

    def __init__(self):
        super().__init__(("127.0.0.1", 0), Handler)
        self.messages = []
        self.http_requests = []
        self.access_headers = {}
        self.received = threading.Event()
        self.cancelled = threading.Event()
        self.blocked = threading.Event()
        self.redirect_target = None
        self.sse = False
        self.disconnect = False
        self.stateful = False


class Handler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"

    def log_message(self, *_):
        pass

    def handle(self):
        with contextlib.suppress(ConnectionResetError):
            super().handle()

    def reply(self, status, body=None, extra=None, sse=False):
        raw = b"" if body is None else json.dumps(body).encode()
        if sse:
            raw = b"event: message\ndata: " + raw + b"\n\n"
        self.send_response(status)
        self.send_header("Content-Type", "text/event-stream" if sse else "application/json")
        self.send_header("Content-Length", str(len(raw)))
        for key, value in (extra or {}).items():
            self.send_header(key, value)
        self.end_headers()
        with contextlib.suppress(BrokenPipeError, ConnectionResetError):
            self.wfile.write(raw)

    def check_access(self):
        self.server.http_requests.append((self.command, dict(self.headers)))
        if any(
            self.headers.get(name) != value for name, value in self.server.access_headers.items()
        ):
            self.reply(403, {"detail": "Access denied"})
            return False
        return True

    def do_GET(self):
        if self.check_access():
            self.reply(405)

    def do_DELETE(self):
        if self.check_access():
            self.reply(204)

    def do_POST(self):
        message = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
        self.server.messages.append((message, dict(self.headers)))
        self.server.received.set()
        if not self.check_access():
            return
        if self.server.redirect_target:
            self.reply(307, extra={"Location": self.server.redirect_target})
            return
        if self.headers.get("Authorization") != "Bearer fixture-key":
            self.reply(401, {"detail": "Invalid key"})
            return
        method = message.get("method")
        if method == "notifications/cancelled":
            self.server.cancelled.set()
        if "id" not in message:
            self.reply(202)
            return
        params = message.get("params", {})
        if method == "initialize":
            result = {
                "protocolVersion": "2025-11-25",
                "capabilities": {"tools": {"listChanged": True}},
                "serverInfo": {"name": "Chans fixture", "version": "1.0.0"},
                "instructions": "Keep hosted instructions unchanged.",
            }
        elif method == "tools/list":
            result = (
                {"tools": [TOOL]}
                if params.get("cursor")
                else {"tools": [], "nextCursor": "page-two"}
            )
        elif method == "tools/call":
            if self.server.disconnect:
                self.close_connection = True
                self.connection.shutdown(2)
                return
            if params.get("name") == "block":
                self.server.blocked.set()
                self.server.cancelled.wait(5)
            result = {
                "content": [{"type": "text", "text": "fixture result"}],
                "structuredContent": {"ok": True},
                "isError": params.get("name") == "error",
                "_meta": {"opaque": [1, "preserved"]},
            }
        elif method == "ping":
            result = {}
        else:
            self.reply(
                200,
                {
                    "jsonrpc": "2.0",
                    "id": message["id"],
                    "error": {"code": -32601, "message": "Unsupported fixture method"},
                },
            )
            return
        response = {"jsonrpc": "2.0", "id": message["id"], "result": result}
        if self.server.sse and method == "tools/call":
            # One SSE response contains a progress notification, a capability
            # change notification and the correlated result.
            frames = [
                {
                    "jsonrpc": "2.0",
                    "method": "notifications/progress",
                    "params": {"progressToken": "progress-1", "progress": 1},
                },
                {"jsonrpc": "2.0", "method": "notifications/tools/list_changed"},
                response,
            ]
            raw = "".join(
                "event: message\ndata: " + json.dumps(frame) + "\n\n" for frame in frames
            ).encode()
            self.send_response(200)
            self.send_header("Content-Type", "text/event-stream")
            self.send_header("Content-Length", str(len(raw)))
            self.end_headers()
            self.wfile.write(raw)
        else:
            headers = (
                {"Mcp-Session-Id": "isolated-fixture-session"} if self.server.stateful else None
            )
            self.reply(200, response, extra=headers)


@contextlib.contextmanager
def endpoint():
    server = Endpoint()
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield server, f"http://127.0.0.1:{server.server_port}/mcp/"
    finally:
        server.cancelled.set()
        server.shutdown()
        server.server_close()
        thread.join(timeout=2)


class Peer:
    def __init__(self, command, url, key="fixture-key", extra_env=None):
        env = {**clean_environment(), "CHANS_API_KEY": key, "CHANS_MCP_URL": url}
        env.update(extra_env or {})
        self.process = subprocess.Popen(
            command,
            cwd=ROOT,
            env=env,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        self.received = queue.Queue()
        self.output = []
        self.errors = []

        def read(stream, target, wire=False):
            for line in stream:
                target.append(line)
                if wire:
                    try:
                        self.received.put(json.loads(line))
                    except ValueError:
                        self.received.put({"invalid_stdout": line})

        self.readers = [
            threading.Thread(
                target=read, args=(self.process.stdout, self.output, True), daemon=True
            ),
            threading.Thread(target=read, args=(self.process.stderr, self.errors), daemon=True),
        ]
        for thread in self.readers:
            thread.start()

    def send(self, message):
        self.process.stdin.write(json.dumps({"jsonrpc": "2.0", **message}) + "\n")
        self.process.stdin.flush()

    def receive(self):
        try:
            return self.received.get(timeout=8)
        except queue.Empty:
            raise AssertionError(
                f"No protocol response; exit={self.process.poll()}, stderr={self.errors}"
            ) from None

    def initialize(self):
        self.send(
            {
                "id": "init",
                "method": "initialize",
                "params": {
                    "protocolVersion": "2025-11-25",
                    "capabilities": {},
                    "clientInfo": {"name": "contract-test", "version": "1"},
                },
            }
        )
        response = self.receive()
        assert response["result"]["instructions"] == "Keep hosted instructions unchanged.", response
        self.send({"method": "notifications/initialized"})

    def stop(self):
        if not self.process.stdin.closed:
            with contextlib.suppress(BrokenPipeError):
                self.process.stdin.close()
        try:
            self.process.wait(timeout=6)
        except subprocess.TimeoutExpired:
            self.process.kill()
            self.process.wait()
            raise AssertionError("Bridge failed to shut down on stdin EOF") from None
        finally:
            for thread in self.readers:
                thread.join(timeout=2)
            self.process.stdout.close()
            self.process.stderr.close()


class Contract(unittest.TestCase):
    def each(self, fn, extra_env=None):
        for name, command in COMMANDS.items():
            with self.subTest(implementation=name), endpoint() as (server, url):
                peer = Peer(command, url, extra_env=extra_env)
                try:
                    fn(peer, server)
                finally:
                    peer.stop()
                self.assertNotIn("fixture-key", "".join(peer.output + peer.errors))
                for value in CF_ENV.values():
                    self.assertNotIn(value, "".join(peer.output + peer.errors))

    def test_discovery_call_fidelity_and_protocol_headers(self):
        def check(peer, server):
            server.stateful = True
            peer.initialize()
            peer.send({"id": 2, "method": "tools/list", "params": {"cursor": "page-two"}})
            self.assertEqual(
                peer.receive(), {"jsonrpc": "2.0", "id": 2, "result": {"tools": [TOOL]}}
            )
            peer.send(
                {
                    "id": "call",
                    "method": "tools/call",
                    "params": {
                        "name": "contract_probe",
                        "arguments": {"value": "héllo"},
                        "_meta": {"trace": "opaque"},
                    },
                }
            )
            result = peer.receive()["result"]
            self.assertEqual(result["structuredContent"], {"ok": True})
            self.assertEqual(result["_meta"], {"opaque": [1, "preserved"]})
            self.assertFalse(result["isError"])
            message, headers = server.messages[-1]
            self.assertEqual(message["params"]["_meta"], {"trace": "opaque"})
            headers = {k.lower(): v for k, v in headers.items()}
            self.assertEqual(headers.get("mcp-protocol-version"), "2025-11-25")
            self.assertEqual(headers.get("mcp-session-id"), "isolated-fixture-session")

        self.each(check)

    def test_sse_notifications_and_tool_errors(self):
        def check(peer, server):
            server.sse = True
            peer.initialize()
            peer.send(
                {
                    "id": 3,
                    "method": "tools/call",
                    "params": {"name": "error", "arguments": {}},
                }
            )
            self.assertEqual(peer.receive()["method"], "notifications/progress")
            self.assertEqual(peer.receive()["method"], "notifications/tools/list_changed")
            self.assertTrue(peer.receive()["result"]["isError"])

        self.each(check)

    def test_cancellation_during_request(self):
        def check(peer, server):
            peer.initialize()
            peer.send({"id": "blocked", "method": "tools/call", "params": {"name": "block"}})
            self.assertTrue(server.blocked.wait(5))
            peer.send(
                {
                    "method": "notifications/cancelled",
                    "params": {"requestId": "blocked", "reason": "fixture"},
                }
            )
            self.assertTrue(server.cancelled.wait(5))
            self.assertEqual(peer.receive()["id"], "blocked")

        self.each(check)

    def test_no_replay_after_disconnect(self):
        def check(peer, server):
            peer.initialize()
            server.disconnect = True
            peer.send({"id": 4, "method": "tools/call", "params": {"name": "contract_probe"}})
            time.sleep(0.4)
            peer.stop()
            self.assertEqual(sum(m.get("method") == "tools/call" for m, _ in server.messages), 1)

        self.each(check)

    def test_cross_origin_redirect_does_not_receive_key(self):
        def check(peer, server):
            with endpoint() as (target, target_url):
                server.access_headers = CF_HEADERS
                server.redirect_target = target_url
                peer.send(
                    {
                        "id": "init",
                        "method": "initialize",
                        "params": {
                            "protocolVersion": "2025-11-25",
                            "capabilities": {},
                            "clientInfo": {"name": "test", "version": "1"},
                        },
                    }
                )
                self.assertTrue(server.received.wait(5))
                time.sleep(0.4)
                peer.stop()
                self.assertEqual(target.messages, [])
                for header, value in CF_HEADERS.items():
                    self.assertEqual(server.http_requests[0][1].get(header), value)

        self.each(check, extra_env=CF_ENV)

    def test_cloudflare_headers_on_bridge_and_doctor(self):
        def check(peer, server):
            server.access_headers = CF_HEADERS
            server.stateful = True
            peer.initialize()
            peer.send(
                {"id": "access-list", "method": "tools/list", "params": {"cursor": "page-two"}}
            )
            self.assertEqual(peer.receive()["result"]["tools"], [TOOL])
            peer.send(
                {"id": "access-call", "method": "tools/call", "params": {"name": "contract_probe"}}
            )
            self.assertTrue(peer.receive()["result"]["structuredContent"]["ok"])
            for _, headers in server.http_requests:
                for name, value in CF_HEADERS.items():
                    self.assertEqual(headers.get(name), value)

        self.each(check, extra_env=CF_ENV)
        for name, command in COMMANDS.items():
            with self.subTest(implementation=name, command="doctor"), endpoint() as (server, url):
                server.access_headers = CF_HEADERS
                result = subprocess.run(
                    command + ["doctor"],
                    cwd=ROOT,
                    capture_output=True,
                    text=True,
                    env={
                        **clean_environment(),
                        **CF_ENV,
                        "CHANS_API_KEY": "fixture-key",
                        "CHANS_MCP_URL": url,
                    },
                    timeout=10,
                )
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertEqual(result.stdout, "")
                self.assertIn("1 authorized tools", result.stderr)
                for _, headers in server.http_requests:
                    for header, value in CF_HEADERS.items():
                        self.assertEqual(headers.get(header), value)
                for value in CF_ENV.values():
                    self.assertNotIn(value, result.stdout + result.stderr)

    def test_cloudflare_rejects_partial_and_invalid_credentials(self):
        cases = [
            {"CF_ACCESS_CLIENT_ID": CF_ENV["CF_ACCESS_CLIENT_ID"]},
            {"CF_ACCESS_CLIENT_SECRET": CF_ENV["CF_ACCESS_CLIENT_SECRET"]},
            {**CF_ENV, "CF_ACCESS_CLIENT_SECRET": "secret\r\nInjected: value"},
            {**CF_ENV, "CF_ACCESS_CLIENT_ID": "invalid id"},
            {**CF_ENV, "CF_ACCESS_CLIENT_SECRET": "invalid-é"},
        ]
        for name, command in COMMANDS.items():
            for index, values in enumerate(cases):
                with self.subTest(implementation=name, case=index):
                    result = subprocess.run(
                        command,
                        cwd=ROOT,
                        capture_output=True,
                        text=True,
                        env={**clean_environment(), "CHANS_API_KEY": "fixture-key", **values},
                        timeout=5,
                    )
                    self.assertNotEqual(result.returncode, 0)
                    self.assertEqual(result.stdout, "")
                    self.assertIn("CF_ACCESS_CLIENT_", result.stderr)
                    for value in values.values():
                        self.assertNotIn(value, result.stderr)

    def test_unknown_method_returns_remote_protocol_error(self):
        def check(peer, _):
            peer.initialize()
            peer.send({"id": 9, "method": "fixture/unknown"})
            self.assertEqual(peer.receive()["error"]["code"], -32601)

        self.each(check)

    @unittest.skipIf(sys.platform == "win32", "Windows terminates processes directly on SIGTERM")
    def test_sigterm_closes_idle_bridge(self):
        def check(peer, _):
            peer.initialize()
            peer.process.send_signal(signal.SIGTERM)
            self.assertEqual(peer.process.wait(timeout=5), 0)

        self.each(check)

    def test_doctor_only_discovers_and_counts_all_pages(self):
        for name, command in COMMANDS.items():
            with self.subTest(implementation=name), endpoint() as (server, url):
                result = subprocess.run(
                    command + ["doctor"],
                    cwd=ROOT,
                    capture_output=True,
                    text=True,
                    env={
                        **clean_environment(),
                        "CHANS_API_KEY": "fixture-key",
                        "CHANS_MCP_URL": url,
                    },
                    timeout=10,
                )
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertEqual(result.stdout, "")
                self.assertIn("1 authorized tools", result.stderr)
                self.assertFalse(any(m.get("method") == "tools/call" for m, _ in server.messages))

    def test_cli_configuration_and_auth_errors(self):
        for name, command in COMMANDS.items():
            for url, key in [
                ("http://remote.example/mcp", "fixture-key"),
                ("https://user:secret@example.test/mcp", "fixture-key"),
                ("https://example.test/mcp?secret=1", "fixture-key"),
                ("https://example.test/mcp", ""),
            ]:
                with self.subTest(implementation=name, url=url):
                    result = subprocess.run(
                        command,
                        cwd=ROOT,
                        capture_output=True,
                        text=True,
                        env={**clean_environment(), "CHANS_API_KEY": key, "CHANS_MCP_URL": url},
                        timeout=5,
                    )
                    self.assertNotEqual(result.returncode, 0)
                    self.assertEqual(result.stdout, "")
                    self.assertNotIn("fixture-key", result.stderr)
                    self.assertNotIn("user:secret", result.stderr)
            with (
                self.subTest(implementation=name, authentication="invalid"),
                endpoint() as (_, url),
            ):
                result = subprocess.run(
                    command + ["doctor"],
                    cwd=ROOT,
                    capture_output=True,
                    text=True,
                    env={
                        **clean_environment(),
                        "CHANS_API_KEY": "secret-invalid-key",
                        "CHANS_MCP_URL": url,
                    },
                    timeout=10,
                )
                self.assertNotEqual(result.returncode, 0)
                self.assertEqual(result.stdout, "")
                self.assertNotIn("secret-invalid-key", result.stderr)

    def test_help_and_version_without_credentials(self):
        for name, command in COMMANDS.items():
            for flag in ["--help", "--version"]:
                with self.subTest(implementation=name, flag=flag):
                    result = subprocess.run(
                        command + [flag],
                        cwd=ROOT,
                        capture_output=True,
                        text=True,
                        env={**clean_environment(), "CHANS_API_KEY": ""},
                        timeout=5,
                    )
                    self.assertEqual(result.returncode, 0, result.stderr)
                    self.assertTrue(result.stdout)


if __name__ == "__main__":
    unittest.main()
