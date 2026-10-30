# Pip PC Brain – optionales lokales Ollama-Backend

Dieses Backend verbindet die Android-App Pip optional mit Ollama auf dem Windows-PC. Es verwendet lokale Modelle und Python-Standardbibliotheken; ein Cloud-Abo ist nicht erforderlich.

## Voraussetzungen

- Windows 10/11 und Python 3.10+
- Ollama läuft auf dem PC
- Das Modell `qwen3:4b` ist installiert (oder `PIP_MODEL` passend setzen)
- Handy und PC sind im selben vertrauenswürdigen privaten WLAN

## Start in PowerShell

Im Ordner `pc-server`:

```powershell
.\start-pip-server.ps1
```

Der Starter erzeugt bei Bedarf einen langen `PIP_TOKEN`, prüft, ob Ollama erreichbar ist, und verwendet standardmäßig CPU-Inferenz (`PIP_NUM_GPU=0`). Das ist eine konservative Einstellung für Systeme, auf denen der CUDA-Pfad nicht kompatibel ist; die Antworten können dadurch deutlich langsamer sein. Ein anderer Wert ist nur sinnvoll, wenn GPU-Inferenz auf dem betreffenden PC tatsächlich getestet wurde.

Den angezeigten Token sicher aufbewahren. Er ist das Passwort zwischen Handy und PC und wird beim Schließen des PowerShell-Fensters nicht automatisch dauerhaft gespeichert.

- Status: `http://127.0.0.1:8765/health`
- Chat: `POST http://PC-IP:8765/chat`
- Erinnerungen ansehen: `GET http://PC-IP:8765/memories`
- Erinnerung löschen: `DELETE http://PC-IP:8765/memories/ID`

Alle Endpunkte außer `/health` benötigen `Authorization: Bearer DEIN_TOKEN`. Chat-JSON: `{"message":"Hallo Pip","session_id":"handy-1"}`.

## Android-Verbindung

Im integrierten Arbeitsbranch ist das PC-Gehirn eine optionale Einstellung. Standardmäßig bleibt das lokale Android-Modell ausgewählt. In Pip unter **Einstellungen → PC-Gehirn verbinden** die PC-Adresse (zum Beispiel `http://192.168.1.20:8765`) und den Token eintragen und den Schalter ausdrücklich aktivieren. Die PC-Adresse muss eine private/lokale Adresse sein.

Wenn der PC ausgeschaltet oder nicht erreichbar ist, zeigt Pip einen Verbindungsfehler. Der PC-Modus schaltet sich nicht automatisch ein und verspricht keine Erreichbarkeit, wenn der PC nicht läuft.

## Sicherheit und Grenzen

- Der Server lauscht standardmäßig auf `0.0.0.0:8765`, damit das Handy im Heimnetz zugreifen kann. Beschränke die Windows-Firewall auf das private Heimnetz.
- HTTP im Heimnetz ist unverschlüsselt: Ein Token kann im selben Netzwerk mitgeschnitten werden. Nur in einem vertrauenswürdigen privaten Netz verwenden.
- Port 8765 und Ollamas Port 11434 niemals direkt ins Internet weiterleiten.
- `/health` liefert ohne Token nur Dienst- und Modellstatus.
- Erinnerungen liegen lokal in `pip_memory.sqlite3`. Der ausdrückliche Befehl „Merk dir …“ speichert einen Fakt. Die Android-App speichert Erinnerungen lokal zuerst und spiegelt explizite Merkvorgänge nur im aktivierten PC-Modus.
- Chatantworten nutzen Ollamas lokale `/api/chat`-Schnittstelle. Standardmäßig werden `num_gpu=0`, begrenzter Kontext und ein Antwortlimit verwendet.
- Die CI-Tests prüfen API, Authentifizierung, SQLite-Gedächtnis und Fehlerpfade mit einem simulierten Modellclient. Ein erfolgreicher CI-Test ersetzt keinen Test mit echtem Ollama, dem eigenen WLAN oder einem physischen Android-Gerät.
- Die optionale Bildgenerierung über ComfyUI ist separat dokumentiert und wird nicht als Voraussetzung für den Textchat benötigt.


## Proaktive Benachrichtigungen

Wenn Benachrichtigungen in Pip ausdrücklich aktiviert sind und zugleich das PC-Gehirn eingeschaltet ist, sendet Android einen authentifizierten `POST /proactive`. Der Request überträgt die aktuellen Gesprächsstil-Regler und – wenn die lokale Datenbank lesbar ist – einen vollständigen Snapshot von bis zu 50 lokalen Erinnerungen. So verwendet eine selbst initiierte Nachricht dieselbe Persönlichkeit und denselben Gedächtnisstand wie der Chat. Ein leerer Snapshot ist ausdrücklich gültig und synchronisiert auch das Löschen aller Erinnerungen.

Der Server erzeugt die Nachricht erst live über Ollama, wenn seit der letzten Nutzernachricht mindestens `PIP_PROACTIVE_AFTER_HOURS` vergangen sind (Standard: 24 Stunden) und der Cooldown `PIP_PROACTIVE_COOLDOWN_HOURS` abgelaufen ist (Standard: 24 Stunden). Bei `ready: false`, nicht erreichbarem PC oder Modellfehler sendet Android keine Benachrichtigung; es wird keine Nachricht vorgeneriert oder in eine Warteschlange gelegt. Die bestehende GET-Variante von `/proactive` bleibt für Diagnose-/Kompatibilitätszwecke erhalten.

Ist das PC-Gehirn ausgeschaltet, verwendet der Worker weiterhin kurze lokale Erinnerungsformulierungen. Ruhezeiten und der standardmäßig ausgeschaltete Benachrichtigungs-Opt-in gelten in beiden Modi.
