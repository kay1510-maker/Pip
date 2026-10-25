# Pip: lokale Bildgenerierung (PC)

Diese Funktion ist absichtlich optional. Pip läuft weiter, wenn kein Bildmodell installiert ist. Es wird kein Cloud-Bilddienst verwendet.

## Zielaufbau

- **Qwen3/Ollama** erstellt aus echten Erinnerungen und den letzten Gesprächen einen neuen Bildprompt.
- **ComfyUI lokal** rendert das Bild auf dem PC.
- Die Android-App fragt später den authentifizierten Pip-Server über die private Tailscale-Verbindung ab und zeigt das Ergebnis als Benachrichtigung an.
- Das Referenzbild kann später hinzugefügt werden; es ist für den ersten Test nicht erforderlich.

## Hardware-Hinweis

Die GTX 1070 Ti hat typischerweise 8 GB VRAM. Starte mit einem SD 1.5-kompatiblen Modell und 512×512 Bildern. SDXL und größere Modelle können auf dieser Karte sehr langsam sein oder nicht zuverlässig passen. Bildgenerierung ist lokal, aber nicht kostenlos im Stromverbrauch.

## Sicherheitsregeln

- ComfyUI nur an `127.0.0.1` binden und seinen Port nicht ins Internet oder Heimnetz freigeben.
- Nur der Pip-PC-Server soll lokal mit ComfyUI sprechen.
- Android greift später ausschließlich über Tailscale auf Pip zu; niemals Ollama oder ComfyUI direkt freigeben.
- Bildgenerierung und Benachrichtigungen müssen in Pip abschaltbar sein.

## Integrationsstatus

Dies ist eine Planungs-/Setup-Datei, keine Behauptung, dass Bildgenerierung schon aktiv ist. Vor der ersten Bildbenachrichtigung müssen ComfyUI installiert, ein kompatibles Modell ausgewählt und der authentifizierte Bild-Endpunkt samt Android-Download/Benachrichtigung getestet werden.
