# Pip PC Brain – erste Backend-Stufe

Dieses Backend verbindet Pip mit Ollama auf dem Windows-PC. Es nutzt nur Python-Standardbibliotheken; keine API-Abos oder Cloud-KI sind nötig.

## Voraussetzungen
- Windows 11 und Python 3.10+
- Ollama läuft auf dem PC
- Das Modell qwen3:4b ist installiert (oder PIP_MODEL passend setzen)

## Start in PowerShell
Im Ordner pc-server:

    $env:PIP_TOKEN = [guid]::NewGuid().ToString() + [guid]::NewGuid().ToString()
    $env:PIP_MODEL = "qwen3:4b"
    python .\pip_server.py

Den Token sicher aufbewahren; er ist das Passwort zwischen Handy und PC.

- Status: http://127.0.0.1:8765/health
- Chat: POST http://PC-IP:8765/chat
- Erinnerungen ansehen: GET http://PC-IP:8765/memories
- Erinnerung löschen: DELETE http://PC-IP:8765/memories/ID

Alle Endpunkte außer /health benötigen Authorization: Bearer DEIN_TOKEN. Chat-JSON: {"message":"Hallo Pip","session_id":"handy-1"}.

## Sicherheit und Status
- Die aktuelle Android-APK ist noch nicht mit diesem Backend verbunden.
- Der Server lauscht standardmäßig auf 0.0.0.0:8765, damit das Handy im Heimnetz zugreifen kann. Windows-Firewall nur für das private Heimnetz erlauben.
- Niemals Port 8765 oder Ollamas Port 11434 direkt ins Internet weiterleiten.
- /health liefert ohne Token nur Dienst- und Modellstatus.
- Erinnerungen liegen lokal in pip_memory.sqlite3. Der Befehl "Merk dir ..." speichert ausdrücklich einen Fakt.
- Chatantworten nutzen Ollamas lokale /api/chat-Schnittstelle mit stream=false.
- Dies ist der Backend-Grundstein, noch nicht die vollständige Verbindung mit der Handy-App. Bildgenerierung, Avatar-Anzeige und proaktive Bildzustellung kommen in späteren Schritten.
