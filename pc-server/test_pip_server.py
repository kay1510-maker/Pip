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

    def request(self, path, method="GET", payload=None, token="test-secret-token-for-unit-tests", raw=None, authorization=None):
        data = raw
        if data is None and payload is not None:
            data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        headers = {}
        if authorization is not None:
            headers["Authorization"] = authorization
        elif token is not None:
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

    def test_bearer_authorization_requires_scheme_and_accepts_case_insensitive_scheme(self):
        invalid_headers = (
            "test-secret-token-for-unit-tests",
            "Basic test-secret-token-for-unit-tests",
            "Bearer",
            "Bearer test-secret-token-for-unit-tests extra",
        )
        for header in invalid_headers:
            with self.subTest(authorization=header):
                status, _ = self.request("/memories", authorization=header)
                self.assertEqual(status, 401)

        status, body = self.request(
            "/memories",
            authorization="bearer test-secret-token-for-unit-tests",
        )
        self.assertEqual(status, 200)
        self.assertEqual(body["memories"], [])

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

    def test_pc_and_android_share_canonical_personality_source(self):
        prompt_path = Path(pip_server.__file__).with_name("pip-personality.txt")
        self.assertEqual(
            pip_server.SYSTEM_PROMPT,
            prompt_path.read_text(encoding="utf-8").strip(),
        )
        for required in (
            "NATÜRLICHKEIT IST WICHTIGER ALS PERFEKTE FORMULIERUNGEN",
            "Keine Standard-Anfänge",
            "Erfinde keine Erinnerungen",
            "Bei ernsten Problemen",
            "Flirte nur, wenn es zum Gespräch passt; ungefragt nicht explizit.",
            "Erzeuge niemals Druck, Kontrolle, Drohungen, Schuldgefühle",
            "Unterscheide zwischen tatsächlicher Erinnerung, Vermutung und fehlendem Wissen.",
            "Romantik und einvernehmliches Flirten zwischen Erwachsenen",
        ):
            self.assertIn(required, pip_server.SYSTEM_PROMPT)

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
        self.assertIn("NATÜRLICHKEIT IST WICHTIGER ALS PERFEKTE FORMULIERUNGEN", system_prompt)
        self.assertIn("Vermeide Standard-Anfänge", system_prompt)
        self.assertIn("ein bis drei natürliche Sätze", system_prompt)
        self.assertIn("Erfinde keine Erinnerungen", system_prompt)
        self.assertIn("Bei ernsten, traurigen oder dringenden Themen", system_prompt)
        self.assertIn("Für Sprachausgabe", system_prompt)

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

    def test_chat_rejects_non_object_json_payloads(self):
        for raw in (b"[]", b"null", b'"Hallo"'):
            with self.subTest(raw=raw):
                status, body = self.request("/chat", method="POST", raw=raw)
                self.assertEqual(status, 400)
                self.assertIn("JSON-Objekt", body["error"])
        self.assertEqual(self.calls, [])

    def test_ollama_chat_sends_configured_cpu_safe_options_and_disables_thinking(self):
        captured = {}

        class FakeResponse:
            def __enter__(self):
                return self

            def __exit__(self, exc_type, exc, tb):
                return False

            def read(self):
                return b'{"message":{"content":"Hallo Pip"}}'

        def fake_urlopen(request, timeout):
            captured["url"] = request.full_url
            captured["timeout"] = timeout
            captured["payload"] = json.loads(request.data.decode("utf-8"))
            return FakeResponse()

        messages = [{"role": "user", "content": "Sag Hallo"}]
        # setUp patches ollama_chat for the HTTP endpoint tests; restore the real
        # function here so this test verifies the actual outgoing Ollama request.
        self.chat_patch.stop()
        try:
            with patch.object(pip_server, "OLLAMA_URL", "http://127.0.0.1:11434/api/chat"), \
                 patch.object(pip_server, "NUM_GPU", 0), \
                 patch.object(pip_server, "NUM_CTX", 4096), \
                 patch.object(pip_server, "NUM_PREDICT", 256), \
                 patch("pip_server.urllib.request.urlopen", side_effect=fake_urlopen):
                reply = pip_server.ollama_chat(messages)
        finally:
            self.chat_patch.start()

        self.assertEqual(reply, "Hallo Pip")
        self.assertEqual(captured["url"], "http://127.0.0.1:11434/api/chat")
        self.assertEqual(captured["timeout"], 240)
        payload = captured["payload"]
        self.assertEqual(payload["model"], "test-qwen-model")
        self.assertEqual(payload["messages"], messages)
        self.assertFalse(payload["stream"])
        self.assertEqual(payload["keep_alive"], "5m")
        self.assertIs(payload["think"], False)
        self.assertEqual(payload["options"]["num_gpu"], 0)
        self.assertEqual(payload["options"]["num_ctx"], 4096)
        self.assertEqual(payload["options"]["num_predict"], 256)

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

    def test_proactive_uses_android_local_activity_when_pc_has_no_chat_history(self):
        now = 2_000_000
        payload = {
            "personality": {"name": "Pipchen", "initiative": 84},
            "memories": [],
            "last_user_at": now - 25 * 3600,
            "recent_context": "Nutzer: Ich habe Pip am PC weitergebaut. | Pip: Ich helfe dir gern.",
        }
        with patch.object(pip_server.time, "time", return_value=now):
            status, body = self.request("/proactive", method="POST", payload=payload)
        self.assertEqual(status, 200)
        self.assertTrue(body["ready"])
        self.assertEqual(body["message"], "Testantwort 1")
        self.assertIn("Ich habe Pip am PC weitergebaut.", self.calls[0][0]["content"])
        self.assertEqual(len(self.calls), 1)

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

    def test_concurrent_proactive_requests_do_not_generate_duplicate_messages(self):
        now = 2_000_000
        self.seed_user_message(now - 25 * 3600)
        generation_started = threading.Event()
        allow_generation_to_finish = threading.Event()
        responses = []

        def slow_chat(messages):
            self.calls.append(messages)
            generation_started.set()
            if not allow_generation_to_finish.wait(timeout=4):
                raise RuntimeError("Testfreigabe für die Modellantwort kam nicht rechtzeitig.")
            return "Nur eine proaktive Nachricht"

        payload = {"personality": {"name": "Pip"}, "memories": []}
        with patch.object(pip_server.time, "time", return_value=now), \
             patch.object(pip_server, "ollama_chat", side_effect=slow_chat):
            first = threading.Thread(
                target=lambda: responses.append(
                    self.request("/proactive", method="POST", payload=payload)
                ),
                daemon=True,
            )
            first.start()
            self.assertTrue(generation_started.wait(timeout=2))

            second_status, second_body = self.request(
                "/proactive", method="POST", payload=payload
            )
            self.assertEqual(second_status, 200)
            self.assertFalse(second_body["ready"])
            self.assertEqual(second_body["reason"], "generation_in_progress")

            allow_generation_to_finish.set()
            first.join(timeout=5)

        self.assertFalse(first.is_alive(), "Die erste proaktive Anfrage muss beendet sein.")
        self.assertEqual(len(responses), 1)
        self.assertEqual(responses[0][0], 200)
        self.assertTrue(responses[0][1]["ready"])
        self.assertEqual(responses[0][1]["message"], "Nur eine proaktive Nachricht")
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
