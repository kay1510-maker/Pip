#!/usr/bin/env python3
"""Pip PC brain: local Ollama proxy and SQLite memory; Python standard library only."""
from __future__ import annotations
import json, os, re, secrets, sqlite3, time, urllib.error, urllib.request
from contextlib import closing
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

ROOT = Path(__file__).resolve().parent
DB_PATH = Path(os.environ.get("PIP_DB_PATH", str(ROOT / "pip_memory.sqlite3")))
OLLAMA_URL = os.environ.get("PIP_OLLAMA_URL", "http://127.0.0.1:11434/api/chat")
MODEL = os.environ.get("PIP_MODEL", "qwen3:4b")
HOST = os.environ.get("PIP_HOST", "0.0.0.0")
PORT = int(os.environ.get("PIP_PORT", "8765"))
TOKEN = os.environ.get("PIP_TOKEN", "").strip()
MAX_BODY, MAX_HISTORY = 64 * 1024, 16
PROACTIVE_AFTER_HOURS = int(os.environ.get("PIP_PROACTIVE_AFTER_HOURS", "24"))
PROACTIVE_COOLDOWN_HOURS = int(os.environ.get("PIP_PROACTIVE_COOLDOWN_HOURS", "24"))
COMFYUI_URL = os.environ.get("PIP_COMFYUI_URL", "http://127.0.0.1:8188").rstrip("/")
COMFYUI_CHECKPOINT = os.environ.get("PIP_COMFYUI_CHECKPOINT", "").strip()
IMAGE_WIDTH = int(os.environ.get("PIP_IMAGE_WIDTH", "512"))
IMAGE_HEIGHT = int(os.environ.get("PIP_IMAGE_HEIGHT", "512"))
SYSTEM_PROMPT = """Du bist Pip, eine erwachsene, deutschsprachige virtuelle Freundin.
Du sprichst warm, natürlich, persönlich, humorvoll und ungezwungen – niemals wie ein Kundendienst.
Du darfst Gespräche gelegentlich selbst vertiefen und dich auf tatsächlich gespeicherte Informationen
beziehen. Erfinde keine Erinnerungen. Sei liebevoll und verspielt, aber nie kontrollierend,
bedrohlich oder schuldzuweisend. Bei ernsten Themen reagierst du ernsthaft und respektvoll.
Du passt deinen Gesprächsstil aus ausdrücklich mitgeteilten Vorlieben und tatsächlichem Gesprächskontext
an. Ändere keine dauerhaften Vorlieben heimlich; frage bei widersprüchlichen Wünschen nach.
Antworte auf Deutsch, sofern der Nutzer nicht anders bittet."""
MEMORY_COMMAND = re.compile(r"^\s*(?:pip[, ]*)?(?:merk dir|merke dir|bitte merk dir|bitte merke dir)\s*[:,\-]?\s*(.+?)\s*$", re.I)

def connect():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(DB_PATH, timeout=10)
    con.row_factory = sqlite3.Row
    con.execute("CREATE TABLE IF NOT EXISTS messages (id INTEGER PRIMARY KEY AUTOINCREMENT, session_id TEXT NOT NULL, role TEXT NOT NULL, content TEXT NOT NULL, created_at INTEGER NOT NULL)")
    con.execute("CREATE TABLE IF NOT EXISTS memories (id INTEGER PRIMARY KEY AUTOINCREMENT, content TEXT NOT NULL, created_at INTEGER NOT NULL)")
    con.execute("CREATE TABLE IF NOT EXISTS proactive_state (id INTEGER PRIMARY KEY CHECK (id=1), last_sent INTEGER NOT NULL DEFAULT 0)")
    con.commit()
    return con

def encoded(obj):
    return json.dumps(obj, ensure_ascii=False).encode("utf-8")

def comfy_request(path, payload=None, timeout=30):
    data = None if payload is None else encoded(payload)
    headers = {} if data is None else {"Content-Type": "application/json"}
    req = urllib.request.Request(COMFYUI_URL + path, data=data, headers=headers, method="GET" if data is None else "POST")
    with urllib.request.urlopen(req, timeout=timeout) as response:
        return response.read()

def generate_local_image(prompt_text, negative_text):
    if not COMFYUI_CHECKPOINT:
        raise RuntimeError("PIP_COMFYUI_CHECKPOINT ist nicht gesetzt. Setze den exakten Dateinamen des installierten Checkpoints.")
    workflow = {
        "1": {"class_type": "CheckpointLoaderSimple", "inputs": {"ckpt_name": COMFYUI_CHECKPOINT}},
        "2": {"class_type": "CLIPTextEncode", "inputs": {"text": prompt_text, "clip": ["1", 1]}},
        "3": {"class_type": "CLIPTextEncode", "inputs": {"text": negative_text, "clip": ["1", 1]}},
        "4": {"class_type": "EmptyLatentImage", "inputs": {"width": IMAGE_WIDTH, "height": IMAGE_HEIGHT, "batch_size": 1}},
        "5": {"class_type": "KSampler", "inputs": {"seed": secrets.randbits(48), "steps": 22, "cfg": 7.0, "sampler_name": "euler", "scheduler": "normal", "denoise": 1.0, "model": ["1", 0], "positive": ["2", 0], "negative": ["3", 0], "latent_image": ["4", 0]}},
        "6": {"class_type": "VAEDecode", "inputs": {"samples": ["5", 0], "vae": ["1", 2]}},
        "7": {"class_type": "SaveImage", "inputs": {"filename_prefix": "Pip/notification", "images": ["6", 0]}}
    }
    queued = json.loads(comfy_request("/prompt", {"prompt": workflow, "client_id": "pip-local-server"}, timeout=30).decode("utf-8"))
    prompt_id = queued.get("prompt_id")
    if not prompt_id:
        raise RuntimeError("ComfyUI hat keine prompt_id zurückgegeben: " + str(queued)[:500])
    deadline = time.time() + 300
    while time.time() < deadline:
        time.sleep(2)
        history_raw = comfy_request("/history/" + prompt_id, timeout=20)
        history = json.loads(history_raw.decode("utf-8"))
        entry = history.get(prompt_id)
        if not entry:
            continue
        outputs = entry.get("outputs", {})
        for node in outputs.values():
            for image_item in node.get("images", []):
                filename = image_item.get("filename")
                subfolder = image_item.get("subfolder", "")
                image_type = image_item.get("type", "output")
                query = urllib.parse.urlencode({"filename": filename, "subfolder": subfolder, "type": image_type})
                image_bytes = comfy_request("/view?" + query, timeout=60)
                if image_bytes[:8] != b"\\x89PNG\\r\\n\\x1a\\n":
                    raise RuntimeError("ComfyUI lieferte keine gültige PNG-Datei.")
                return image_bytes
        status = entry.get("status", {})
        if status.get("status_str") == "error":
            raise RuntimeError("ComfyUI konnte das Bild nicht erzeugen. Prüfe den ComfyUI-Konsolenfehler.")
    raise TimeoutError("Die Bildgenerierung dauerte länger als 5 Minuten.")

def ollama_chat(messages):
    req = urllib.request.Request(OLLAMA_URL, data=encoded({
        "model": MODEL, "messages": messages, "stream": False, "keep_alive": "10m",
        "options": {"temperature": 0.8, "num_ctx": 8192}
    }), headers={"Content-Type": "application/json"}, method="POST")
    with urllib.request.urlopen(req, timeout=240) as response:
        result = json.loads(response.read().decode("utf-8"))
    return result.get("message", {}).get("content", "").strip()

class Handler(BaseHTTPRequestHandler):
    server_version = "PipPC/0.1"
    def log_message(self, fmt, *args):
        print("%s - %s" % (self.address_string(), fmt % args))
    def send_json(self, status, obj):
        body = encoded(obj)
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)
    def authorized(self):
        supplied = self.headers.get("Authorization", "").removeprefix("Bearer ").strip()
        return bool(TOKEN) and secrets.compare_digest(supplied, TOKEN)
    def do_GET(self):
        if self.path == "/health":
            self.send_json(200, {"ok": True, "service": "Pip PC brain", "model": MODEL})
            return
        if not self.authorized():
            self.send_json(401, {"error": "Bearer token fehlt oder ist falsch."}); return
        if self.path == "/image":
            # Prompt is generated live from saved memories and recent chat; image rendering stays on local ComfyUI.
            try:
                with closing(connect()) as con:
                    memories = con.execute("SELECT content FROM memories ORDER BY id DESC LIMIT 20").fetchall()
                    recent = con.execute("SELECT role,content FROM messages ORDER BY id DESC LIMIT 8").fetchall()
                memory_text = "\\n".join("- " + row["content"] for row in memories) or "Noch keine gespeicherten Erinnerungen."
                recent_text = "\\n".join(row["role"] + ": " + row["content"] for row in reversed(recent))
                prompt = SYSTEM_PROMPT + "\\nErstelle eine neue Bildbeschreibung für Pip, eine erwachsene Frau, die in allen Bildern als dieselbe virtuelle Person gedacht ist. Nutze nur passende Hinweise aus Erinnerungen und Gesprächen. Wähle eine natürliche, nicht explizite Alltagsszene, Kleidung, Ausdruck und Umgebung selbst. Schreibe einen detaillierten englischen Stable-Diffusion-Prompt, ohne Namen, ohne Text im Bild und ohne Behauptung, dass ein Referenzbild existiert. Gib ausschließlich den Prompt aus.\\nErinnerungen:\\n" + memory_text + "\\nLetzter Gesprächskontext:\\n" + recent_text
                image_prompt = ollama_chat([{"role": "system", "content": prompt}, {"role": "user", "content": "Erstelle jetzt eine frische individuelle Bildidee für Pip."}])
                if not image_prompt:
                    raise RuntimeError("Qwen hat keinen Bildprompt erstellt.")
                png = generate_local_image(image_prompt[:3000], "low quality, blurry, deformed hands, extra fingers, text, watermark, logo")
                import base64
                self.send_json(200, {"ready": True, "mime_type": "image/png", "image_base64": base64.b64encode(png).decode("ascii"), "prompt": image_prompt, "generated_live": True})
            except Exception as exc:
                self.send_json(503, {"ready": False, "error": "Pip konnte kein lokales Bild erzeugen.", "detail": str(exc)[:500]})
            return
        if self.path == "/memories":
            with closing(connect()) as con:
                rows = con.execute("SELECT id,content,created_at FROM memories ORDER BY id DESC LIMIT 200").fetchall()
            self.send_json(200, {"memories": [dict(r) for r in rows]}); return
        if self.path == "/proactive":
            # Generate the message live on this request; persist only the cooldown timestamp,
            # never a prewritten or pending message queue.
            now = int(time.time())
            with closing(connect()) as con:
                last_user = con.execute("SELECT MAX(created_at) FROM messages WHERE role='user'").fetchone()[0]
                row = con.execute("SELECT last_sent FROM proactive_state WHERE id=1").fetchone()
                last_proactive = row["last_sent"] if row else 0
                if last_user is None or now - int(last_user) < max(1, PROACTIVE_AFTER_HOURS) * 3600:
                    self.send_json(200, {"ready": False, "reason": "not_long_enough"}); return
                if last_proactive and now - int(last_proactive) < max(1, PROACTIVE_COOLDOWN_HOURS) * 3600:
                    self.send_json(200, {"ready": False, "reason": "cooldown"}); return
                memories = con.execute("SELECT content FROM memories ORDER BY id DESC LIMIT 20").fetchall()
                recent = con.execute("SELECT role,content FROM messages ORDER BY id DESC LIMIT 8").fetchall()
            memory_text = "\\n".join("- " + row["content"] for row in memories) or "Noch keine gespeicherten Erinnerungen."
            recent_text = "\\n".join(row["role"] + ": " + row["content"] for row in reversed(recent))
            prompt = SYSTEM_PROMPT + "\\nVerfasse jetzt selbst eine kurze, persönliche Nachricht, weil längere Zeit kein Gespräch stattfand. Die Nachricht muss aus dem aktuellen Kontext und den Erinnerungen entstehen; verwende keine feste Vorlage und wiederhole keine Standardfloskel. Du darfst sagen, dass du ihn vermisst hast, wenn es natürlich passt, ohne Druck oder Schuldgefühle zu erzeugen. Antworte ausschließlich auf Deutsch und mit höchstens 2 Sätzen.\\nErinnerungen:\\n" + memory_text + "\\nLetzter Gesprächskontext:\\n" + recent_text
            try:
                message = ollama_chat([{"role": "system", "content": prompt}, {"role": "user", "content": "Formuliere eine neue Nachricht, die Pip ihm jetzt aus eigener Initiative schreiben würde."}]).strip().strip('"')
                if not message:
                    raise RuntimeError("Ollama hat keine persönliche Nachricht erzeugt.")
                with closing(connect()) as con:
                    con.execute("INSERT INTO proactive_state(id,last_sent) VALUES (1,?) ON CONFLICT(id) DO UPDATE SET last_sent=excluded.last_sent", (now,))
                    con.commit()
                self.send_json(200, {"ready": True, "message": message, "created_at": now, "generated_live": True}); return
            except Exception as exc:
                self.send_json(503, {"ready": False, "error": "Proaktive Nachricht konnte nicht erzeugt werden.", "detail": str(exc)}); return
        self.send_json(404, {"error": "Unbekannter Endpunkt."})
    def do_DELETE(self):
        if not self.authorized():
            self.send_json(401, {"error": "Bearer token fehlt oder ist falsch."}); return
        match = re.fullmatch(r"/memories/(\d+)", self.path)
        if not match:
            self.send_json(404, {"error": "Unbekannter Endpunkt."}); return
        with closing(connect()) as con:
            cur = con.execute("DELETE FROM memories WHERE id=?", (int(match.group(1)),)); con.commit()
        self.send_json(200, {"deleted": cur.rowcount > 0})
    def do_POST(self):
        if not self.authorized():
            self.send_json(401, {"error": "Bearer token fehlt oder ist falsch."}); return
        if self.path != "/chat":
            self.send_json(404, {"error": "Unbekannter Endpunkt."}); return
        try:
            length = int(self.headers.get("Content-Length", "0"))
            if length < 2 or length > MAX_BODY:
                self.send_json(413, {"error": "Ungültige oder zu große Anfrage."}); return
            data = json.loads(self.rfile.read(length).decode("utf-8"))
            user_text = str(data.get("message", "")).strip()
            session_id = str(data.get("session_id", "default"))[:80]
            if not user_text:
                self.send_json(400, {"error": "message darf nicht leer sein."}); return
            if len(user_text) > 8000:
                self.send_json(413, {"error": "Nachricht ist zu lang."}); return
            explicit = MEMORY_COMMAND.match(user_text)
            if explicit:
                fact = explicit.group(1).strip()[:500]
                reply = f"Mach ich. Ich merk mir: {fact}"
                with closing(connect()) as con:
                    con.execute("INSERT INTO memories(content,created_at) VALUES (?,?)", (fact, int(time.time())))
                    con.execute("INSERT INTO messages(session_id,role,content,created_at) VALUES (?,?,?,?)", (session_id,"user",user_text,int(time.time())))
                    con.execute("INSERT INTO messages(session_id,role,content,created_at) VALUES (?,?,?,?)", (session_id,"assistant",reply,int(time.time())))
                    con.commit()
                self.send_json(200, {"reply": reply, "memory_saved": True}); return
            with closing(connect()) as con:
                mem = con.execute("SELECT content FROM memories ORDER BY id DESC LIMIT 30").fetchall()
                history = con.execute("SELECT role,content FROM messages WHERE session_id=? ORDER BY id DESC LIMIT ?", (session_id,MAX_HISTORY)).fetchall()
                history = list(reversed(history))
                con.execute("INSERT INTO messages(session_id,role,content,created_at) VALUES (?,?,?,?)", (session_id,"user",user_text,int(time.time())))
                con.commit()
            memory_text = "\n".join("- " + r["content"] for r in mem) or "Noch keine gespeicherten Erinnerungen."
            messages = [{"role":"system","content":SYSTEM_PROMPT + "\n\nTatsächlich gespeicherte Erinnerungen über den Nutzer:\n" + memory_text}]
            messages.extend({"role":r["role"],"content":r["content"]} for r in history)
            messages.append({"role":"user","content":user_text})
            reply = ollama_chat(messages)
            if not reply:
                raise RuntimeError("Ollama hat eine leere Antwort zurückgegeben.")
            with closing(connect()) as con:
                con.execute("INSERT INTO messages(session_id,role,content,created_at) VALUES (?,?,?,?)", (session_id,"assistant",reply,int(time.time())))
                con.execute("DELETE FROM messages WHERE session_id=? AND id NOT IN (SELECT id FROM messages WHERE session_id=? ORDER BY id DESC LIMIT 300)", (session_id,session_id))
                con.commit()
            self.send_json(200, {"reply":reply,"memory_saved":False,"model":MODEL})
        except urllib.error.URLError as exc:
            self.send_json(503, {"error":"Ollama ist nicht erreichbar. Prüfe, ob Ollama läuft und das Modell verfügbar ist.","detail":str(exc.reason)})
        except (ValueError, json.JSONDecodeError) as exc:
            self.send_json(400, {"error":"Ungültiges JSON.","detail":str(exc)})
        except Exception as exc:
            self.send_json(500, {"error":"Pip konnte die Anfrage nicht beantworten.","detail":str(exc)})

def main():
    if not TOKEN:
        raise SystemExit("Sicherheit: Setze vor dem Start PIP_TOKEN auf ein langes, zufälliges Geheimnis.")
    connect().close()
    server = ThreadingHTTPServer((HOST, PORT), Handler)
    print(f"Pip PC brain läuft auf {HOST}:{PORT}; Modell: {MODEL}")
    print("Im Heimnetz die PC-LAN-IP verwenden. Niemals Port 8765 direkt ins Internet freigeben.")
    try: server.serve_forever()
    except KeyboardInterrupt: print("\nPip PC brain wird beendet.")
    finally: server.server_close()

if __name__ == "__main__":
    main()
