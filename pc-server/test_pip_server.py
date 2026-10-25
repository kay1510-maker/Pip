import json
import tempfile
import threading
import unittest
import urllib.error
import urllib.request
from pathlib import Path
from unittest.mock import patch

import pip_server


class PipServerTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.old_db_path = pip_server.DB_PATH
        self.old_token = pip_server.TOKEN
        self.old_model = pip_server.MODEL
        pip_server.DB_PATH = Path(self.temp.name) / "test.sqlite3"
        pip_server.TOKEN = "test-secret-token-for-unit-tests"
        pip_server.MODEL = "test-qwen-model"
        self.calls = []
        self.chat_patch = patch.object(pip_server, "ollama_chat", side_effect=self.fake_chat)
        self.chat_patch.start()
        self.httpd = pip_server.ThreadingHTTPServer(("127.0.0.1", 0), pip_server.Handler)
        self.thread = threading.Thread(target=self.httpd.serve_forever, daemon=True)
        self.thread.start()
        self.base = f"http://127.0.0.1:{self.httpd.server_address[1]}"

    def tearDown(self):
        self.httpd.shutdown()
        self.httpd.server_close()
        self.thread.join(timeout=2)
        self.chat_patch.stop()
        pip_server.DB_PATH = self.old_db_path
        pip_server.TOKEN = self.old_token
        pip_server.MODEL = self.old_model
        self.temp.cleanup()

    def fake_chat(self, messages):
        self.calls.append(messages)
        return f"Testantwort {len(self.calls)}"

    def request(self, path, method="GET", payload=None, token="test-secret-token-for-unit-tests", raw=None):
        data = raw
        if data is None and payload is not None:
            data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        headers = {}
        if token is not None:
            headers["Authorization"] = "Bearer " + token
        if data is not None:
            headers["Content-Type"] = "application/json"
        req = urllib.request.Request(self.base + path, data=data, headers=headers, method=method)
        try:
            with urllib.request.urlopen(req, timeout=3) as response:
                body = response.read()
                return response.status, json.loads(body.decode("utf-8")) if body else {}
        except urllib.error.HTTPError as exc:
            body = exc.read()
            return exc.code, json.loads(body.decode("utf-8")) if body else {}

    def test_health_is_available_without_authentication(self):
        status, body = self.request("/health", token=None)
        self.assertEqual(status, 200)
        self.assertTrue(body["ok"])
        self.assertEqual(body["model"], "test-qwen-model")

    def test_chat_and_memory_endpoints_require_bearer_token(self):
        status, _ = self.request("/chat", method="POST", payload={"message": "Hallo"}, token=None)
        self.assertEqual(status, 401)
        status, _ = self.request("/memories", token="wrong-token")
        self.assertEqual(status, 401)

    def test_explicit_memory_is_saved_and_can_be_deleted(self):
        status, body = self.request(
            "/chat", method="POST",
            payload={"message": "Merk dir: Ich mag Kaffee.", "session_id": "phone-1"},
        )
        self.assertEqual(status, 200)
        self.assertTrue(body["memory_saved"])
        status, body = self.request("/memories")
        self.assertEqual(status, 200)
        self.assertEqual(body["memories"][0]["content"], "Ich mag Kaffee.")
        memory_id = body["memories"][0]["id"]
        status, body = self.request(f"/memories/{memory_id}", method="DELETE")
        self.assertEqual(status, 200)
        self.assertTrue(body["deleted"])
        status, body = self.request("/memories")
        self.assertEqual(status, 200)
        self.assertEqual(body["memories"], [])

    def test_saved_memory_and_previous_turn_reach_local_model_client(self):
        status, _ = self.request(
            "/chat", method="POST",
            payload={"message": "Merk dir: Ich mag Kaffee.", "session_id": "phone-2"},
        )
        self.assertEqual(status, 200)
        status, body = self.request(
            "/chat", method="POST",
            payload={"message": "Was mag ich?", "session_id": "phone-2"},
        )
        self.assertEqual(status, 200)
        self.assertEqual(body["reply"], "Testantwort 1")
        messages = self.calls[0]
        self.assertIn("Ich mag Kaffee.", messages[0]["content"])
        self.assertEqual(messages[-1]["content"], "Was mag ich?")
        self.assertTrue(any(m["content"] == "Merk dir: Ich mag Kaffee." for m in messages))

    def test_invalid_json_and_empty_message_are_rejected(self):
        status, _ = self.request("/chat", method="POST", raw=b"{bad")
        self.assertEqual(status, 400)
        status, _ = self.request("/chat", method="POST", payload={"message": "   "})
        self.assertEqual(status, 400)

    def test_ollama_failure_returns_service_unavailable(self):
        with patch.object(pip_server, "ollama_chat", side_effect=urllib.error.URLError("offline")):
            status, body = self.request(
                "/chat", method="POST",
                payload={"message": "Hallo", "session_id": "phone-3"},
            )
        self.assertEqual(status, 503)
        self.assertIn("Ollama ist nicht erreichbar", body["error"])


if __name__ == "__main__":
    unittest.main()
