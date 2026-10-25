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
    con.execute("CREATE TABLE IF NOT EXISTS proactive_notifications (id INTEGER PRIMARY KEY AUTOINCREMENT, content TEXT NOT NULL, created_at INTEGER NOT NULL, delivered INTEGER NOT NULL DEFAULT 0)")
    con.commit()
    return con

def encoded(obj):
    return json.dumps(obj, ensure_ascii=False).encode("utf-8")

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
        if self.path == "/memories":
            with closing(connect()) as con:
                rows = con.execute("SELECT id,content,created_at FROM memories ORDER BY id DESC LIMIT 200").fetchall()
            self.send_json(200, {"memories": [dict(r) for r in rows]}); return
        if self.path == "/proactive":
            now = int(time.time())
            with closing(connect()) as con:
                pending = con.execute("SELECT id,content,created_at FROM proactive_notifications WHERE delivered=0 ORDER BY id LIMIT 1").fetchone()
                if pending:
                    self.send_json(200, {"ready": True, "id": pending["id"], "message": pending["content"], "created_at": pending["created_at"]}); return
                last_user = con.execute("SELECT MAX(created_at) FROM messages WHERE role='user'").fetchone()[0]
                last_proactive = con.execute("SELECT MAX(created_at) FROM proactive_notifications").fetchone()[0]
                if last_user is None or now - int(last_user) < max(1, PROACTIVE_AFTER_HOURS) * 3600:
                    self.send_json(200, {"ready": False, "reason": "not_long_enough"}); return
                if last_proactive is not None and now - int(last_proactive) < max(1, PROACTIVE_COOLDOWN_HOURS) * 3600:
                    self.send_json(200, {"ready": False, "reason": "cooldown"}); return
                memories = con.execute("SELECT content FROM memories ORDER BY id DESC LIMIT 20").fetchall()
                recent = con.execute("SELECT role,content FROM messages ORDER BY id DESC LIMIT 8").fetchall()
            memory_text = "\n".join("- " + row["content"] for row in memories) or "Noch keine gespeicherten Erinnerungen."
            recent_text = "\n".join(row["role"] + ": " + row["content"] for row in reversed(recent))
            prompt = SYSTEM_PROMPT + "\nDu darfst eine kurze, liebevolle Nachricht aus eigener Initiative verfassen, weil längere Zeit kein Gespräch stattfand. Dränge nicht, mache keine Schuldgefühle und behaupte keine echten menschlichen Gefühle als Tatsache. Nutze Erinnerungen nur, wenn sie passen. Antworte ausschließlich mit der Nachricht, auf Deutsch, maximal 2 Sätze.\nErinnerungen:\n" + memory_text + "\nLetzter Gesprächskontext:\n" + recent_text
            try:
                message = ollama_chat([{"role": "system", "content": prompt}, {"role": "user", "content": "Schreibe jetzt eine persönliche Nachricht, mit der Pip sich nach längerer Funkstille von sich aus meldet."}])
                message = message.strip().strip('"')
                if not message:
                    raise RuntimeError("Ollama hat keine proaktive Nachricht erzeugt.")
                with closing(connect()) as con:
                    cur = con.execute("INSERT INTO proactive_notifications(content,created_at,delivered) VALUES (?,?,0)", (message, now))
                    con.commit()
                    item_id = cur.lastrowid
                self.send_json(200, {"ready": True, "id": item_id, "message": message, "created_at": now}); return
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
        if self.path == "/proactive/ack":
            try:
                length = int(self.headers.get("Content-Length", "0"))
                if length < 2 or length > 1024:
                    self.send_json(400, {"error": "Ungültige Bestätigung."}); return
                data = json.loads(self.rfile.read(length).decode("utf-8"))
                item_id = int(data.get("id", 0))
                with closing(connect()) as con:
                    cur = con.execute("UPDATE proactive_notifications SET delivered=1 WHERE id=?", (item_id,))
                    con.commit()
                self.send_json(200, {"acknowledged": cur.rowcount > 0}); return
            except (ValueError, json.JSONDecodeError):
                self.send_json(400, {"error": "Ungültige Bestätigung."}); return
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
