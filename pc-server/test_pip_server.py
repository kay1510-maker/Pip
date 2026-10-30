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

    def seed_user_message(self, created_at):
        con = pip_server.connect()
        try:
            con.execute(
                "INSERT INTO messages(session_id,role,content,created_at) VALUES (?,?,?,?)",
                ("phone-proactive", "user", "Letzter Gesprächsbeitrag", created_at),
            )
            con.commit()
        finally:
            con.close()

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

    def test_android_personality_settings_are_applied_to_pc_prompt(self):
        status, body = self.request(
            "/chat", method="POST",
            payload={
                "message": "Hallo",
                "session_id": "personality-1",
                "personality": {
                    "name": "Pipchen",
                    "initiative": 91,
                    "humor": 42,
                    "romance": 73,
                    "jealousy": 8,
                },
            },
        )
        self.assertEqual(status, 200)
        system_prompt = self.calls[0][0]["content"]
        self.assertIn("Dein Name ist Pipchen", system_prompt)
        self.assertIn("Eigeninitiative 91/100", system_prompt)
        self.assertIn("Humor 42/100", system_prompt)
        self.assertIn("Romantik/Flirt 73/100", system_prompt)
        self.assertIn("spielerische Eifersucht 8/100", system_prompt)

    def test_android_memory_snapshot_replaces_pc_memory_and_propagates_deletion(self):
        status, body = self.request(
            "/chat", method="POST",
            payload={"message": "Merk dir: Alter PC-Fakt", "session_id": "memory-sync"},
        )
        self.assertEqual(status, 200)
        status, body = self.request(
            "/chat", method="POST",
            payload={
                "message": "Was weißt du?",
                "session_id": "memory-sync",
                "memories": [{"category": "Vorliebe", "content": "Ich mag Tee."}],
            },
        )
        self.assertEqual(status, 200)
        self.assertIn("Ich mag Tee.", self.calls[-1][0]["content"])
        status, body = self.request("/memories")
        self.assertEqual(status, 200)
        self.assertEqual(len(body["memories"]), 1)
        self.assertEqual(body["memories"][0]["category"], "Vorliebe")
        self.assertEqual(body["memories"][0]["content"], "Ich mag Tee.")

        status, body = self.request(
            "/chat", method="POST",
            payload={"message": "Noch eine Nachricht", "session_id": "memory-sync", "memories": []},
        )
        self.assertEqual(status, 200)
        status, body = self.request("/memories")
        self.assertEqual(status, 200)
        self.assertEqual(body["memories"], [])

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


    def test_proactive_endpoint_requires_bearer_token_for_get_and_post(self):
        status, _ = self.request("/proactive", token=None)
        self.assertEqual(status, 401)
        status, _ = self.request(
            "/proactive", method="POST",
            payload={"personality": {}, "memories": []}, token=None,
        )
        self.assertEqual(status, 401)

    def test_proactive_waits_for_idle_threshold_without_calling_ollama(self):
        now = 2_000_000
        self.seed_user_message(now - 3600)
        with patch.object(pip_server.time, "time", return_value=now):
            status, body = self.request(
                "/proactive", method="POST",
                payload={"personality": {"name": "Pipchen"}, "memories": []},
            )
        self.assertEqual(status, 200)
        self.assertFalse(body["ready"])
        self.assertEqual(body["reason"], "not_long_enough")
        self.assertEqual(self.calls, [])

    def test_proactive_uses_android_personality_and_memory_snapshot_then_respects_cooldown(self):
        now = 2_000_000
        self.seed_user_message(now - 25 * 3600)
        payload = {
            "personality": {
                "name": "Pipchen",
                "initiative": 91,
                "humor": 42,
                "romance": 73,
                "jealousy": 8,
            },
            "memories": [{"category": "Vorliebe", "content": "Ich mag Tee."}],
        }
        with patch.object(pip_server.time, "time", return_value=now):
            status, body = self.request("/proactive", method="POST", payload=payload)
            self.assertEqual(status, 200)
            self.assertTrue(body["ready"])
            self.assertTrue(body["generated_live"])
            self.assertEqual(body["message"], "Testantwort 1")
            system_prompt = self.calls[0][0]["content"]
            self.assertIn("Dein Name ist Pipchen", system_prompt)
            self.assertIn("Eigeninitiative 91/100", system_prompt)
            self.assertIn("Humor 42/100", system_prompt)
            self.assertIn("Romantik/Flirt 73/100", system_prompt)
            self.assertIn("spielerische Eifersucht 8/100", system_prompt)
            self.assertIn("Vorliebe: Ich mag Tee.", system_prompt)

            status, body = self.request("/proactive", method="POST", payload=payload)
        self.assertEqual(status, 200)
        self.assertFalse(body["ready"])
        self.assertEqual(body["reason"], "cooldown")
        self.assertEqual(len(self.calls), 1)

    def test_proactive_ollama_failure_does_not_start_cooldown(self):
        now = 2_000_000
        self.seed_user_message(now - 25 * 3600)
        payload = {"personality": {"name": "Pip"}, "memories": []}
        with patch.object(pip_server.time, "time", return_value=now):
            with patch.object(pip_server, "ollama_chat", side_effect=urllib.error.URLError("offline")):
                status, body = self.request("/proactive", method="POST", payload=payload)
            self.assertEqual(status, 503)
            self.assertFalse(body["ready"])

            status, body = self.request("/proactive", method="POST", payload=payload)
        self.assertEqual(status, 200)
        self.assertTrue(body["ready"])
        self.assertEqual(body["message"], "Testantwort 1")
        self.assertEqual(len(self.calls), 1)


if __name__ == "__main__":
    unittest.main()
