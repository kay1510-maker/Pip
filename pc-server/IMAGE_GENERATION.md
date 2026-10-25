# Pip: lokale Bildgenerierung (PC)

Diese Funktion ist optional. Pip läuft weiter, wenn kein Bildmodell installiert ist. Der geplante Ablauf verwendet keine Cloud-Bild-API.

## Was jetzt vorbereitet ist

- `setup-comfyui.ps1`: richtet ComfyUI und eine separate Python-Umgebung unter `%LOCALAPPDATA%\Pip\ComfyUI` ein.
- `start-comfyui.ps1`: startet ComfyUI ausschließlich auf `127.0.0.1:8188` mit Low-VRAM-Modus.
- Es wird **kein Bildmodell automatisch heruntergeladen**. Dadurch werden keine fremden Modell-Lizenzen oder ungeprüften Downloads stillschweigend akzeptiert.

## Windows-Einrichtung

1. Installiere Git for Windows und Python 3.11 (64-bit), falls sie noch fehlen.
2. Öffne PowerShell im geklonten Pip-Projektordner.
3. Führe aus:
   ```powershell
   Set-ExecutionPolicy -Scope Process Bypass
   .\pc-server\setup-comfyui.ps1
   ```
4. Besorge ein SD 1.5-kompatibles Checkpoint-Modell aus einer vertrauenswürdigen Quelle, prüfe die Lizenz und lege die Datei mit der Endung `.safetensors` unter `%LOCALAPPDATA%\Pip\ComfyUI\models\checkpoints\` ab.
5. Starte es mit:
   ```powershell
   .\pc-server\start-comfyui.ps1
   ```
6. Prüfe lokal im Browser `http://127.0.0.1:8188`. ComfyUI sollte nicht von anderen Geräten aus erreichbar sein.

Wenn PyTorch CUDA oder die Treiberprüfung fehlschlägt, brich ab und melde die genaue Fehlermeldung, statt beliebige CUDA-Versionen zu installieren. Die GTX 1070 Ti (Pascal, typischerweise 8 GB VRAM) braucht ein kompatibles Modell und eher 512×512 statt SDXL.

## Zielaufbau

- **Qwen3/Ollama** erstellt aus tatsächlich gespeicherten Erinnerungen und dem letzten Gespräch eine neue Bildidee.
- **ComfyUI lokal** rendert das Bild auf dem PC.
- Die Android-App soll später über den authentifizierten Pip-Server und Tailscale ein fertiges Bild abrufen und als Benachrichtigung anzeigen.
- Ein Referenzbild für Pips Aussehen kann später ergänzt werden.

## Sicherheit

- ComfyUI bleibt an `127.0.0.1` gebunden; Port 8188 nicht im Router freigeben und nicht über Tailscale veröffentlichen.
- Ollama-Port 11434 und Pip-Port 8765 niemals direkt ins öffentliche Internet freigeben.
- Bildgenerierung und Benachrichtigungen sollen abschaltbar sein.

## Noch nicht implementiert

Die beiden PowerShell-Skripte bereiten die lokale ComfyUI-Installation vor, aber sie erzeugen noch keine Pip-Bilder. Noch fehlen der authentifizierte Pip-Server-Endpunkt, der ComfyUI-Workflow mit dem gewählten Checkpoint, Bilddatei-Download sowie Android-Benachrichtigung. Diese Schritte müssen separat entwickelt und getestet werden.
