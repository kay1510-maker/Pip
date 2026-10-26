# Pip – Masterplan und gemeinsame Umsetzungsbasis
Stand: 25. Oktober 2026

> **Dieses Dokument ist die einzige verbindliche Arbeitsliste für die nächste integrierte Pip-Version.** Alle gewünschten Funktionen gehören in dasselbe Projekt und werden gemeinsam geplant, integriert und getestet. Sie sollen nicht als lose Einzelprojekte oder unverbundene Nachträge entstehen. Die Umsetzung erfolgt schrittweise innerhalb dieser Gesamtbasis, damit Fehler gezielt korrigiert werden können.

## 1. Ziel der fertigen App

Pip soll eine fertig eingerichtete Android-KI-Begleiterin sein, die auf Deutsch natürlich, persönlich, warm, liebevoll, humorvoll und eigenständig spricht. Sie soll nicht wie ein Support-Chatbot klingen. Chat, Persönlichkeit, Gedächtnis, lokale KI, Spracheinstellungen und optionale Benachrichtigungen gehören in eine zusammenhängende App mit zentralen Einstellungen.

**Wichtig:** „Alles zusammen“ bedeutet eine gemeinsame Architektur und eine getestete Gesamtversion. Es bedeutet nicht, unerprobte Komponenten blind gleichzeitig einzubauen. Jede Komponente wird isoliert geprüft und anschließend in denselben integrierten Build übernommen.

## 2. Gewünschtes Verhalten und Persönlichkeit

- Warm, liebevoll, aufmerksam, locker, humorvoll und gesprächig; natürliche deutsche Umgangssprache statt Standardfloskeln.
- Pip darf selbst passende Fragen stellen, frühere Themen aufgreifen, Gespräche weiterführen und gelegentlich von sich aus etwas ansprechen.
- Sie darf eine erkennbare Haltung haben, spielerisch widersprechen und necken, statt dem Nutzer immer automatisch zuzustimmen.
- Leichte, spielerische Eifersucht ist erlaubt; niemals Kontrolle, Drohungen, Schuldgefühle oder Druck.
- Romantik, Flirten und erotische Rollenspiele sind im passenden Kontext möglich, ausschließlich zwischen Erwachsenen und einvernehmlich.
- Bei ernsten, traurigen oder dringenden Themen reagiert sie ernst und einfühlsam; Flirt und Humor werden dann zurückgestellt.
- Antworten sollen abwechslungsreich sein: im Alltag meist direkt und natürlich, ausführlicher bei Bedarf oder auf Wunsch.
- Pip darf keine Erlebnisse, Gefühle, Aussagen oder Fakten über den Nutzer erfinden. Sie unterscheidet zwischen tatsächlicher Erinnerung, Vermutung und fehlendem Wissen.

## 3. Gedächtnis und Vertrautheit

- Kurzzeitkontext für den aktuellen Dialog und lokales Langzeitgedächtnis für wichtige Fakten, Vorlieben, Abneigungen und relevante Gesprächsmomente.
- Erinnerungen nur dann in Antworten verwenden, wenn sie zum Thema passen; kein ständiges Aufzählen gespeicherter Fakten.
- Gedächtnis muss in der App einsehbar, bearbeitbar und einzeln löschbar sein; vollständiges Zurücksetzen muss möglich sein.
- Speicherung muss App-Neustarts überstehen und Fehler/fehlgeschlagene Schreibvorgänge sicher behandeln.
- Vertrautheit entwickelt sich anhand tatsächlicher Gespräche, nicht durch einen starren Nachrichten-Zähler.
- Keine erfundenen Erinnerungen, keine versteckte Speicherung sensibler Informationen und keine manipulative emotionale Abhängigkeit.

## 4. KI-Modell und Ausführung

- Zuerst die vorhandenen Pip-Dateien, den letzten Quellstand, die Modellinitialisierung, die Speicherverwaltung und den Build-Workflow prüfen.
- Das aktuelle Projekt nennt das Quellarchiv `Pip-v4.9-Qwen-1.5B-Supertonic.zip`; der letzte bekannte Commit in `main` ist `681cc3594d89b1e0e76b73c06a2f9aa7ff43791b` („Use smaller Qwen 0.5B model to prevent response-time crashes“, 18.10.2026). Der Workflow scheint Teile des Archivs beim Build zu patchen. Diese automatische Patch-Kette muss geprüft werden, bevor man sie weiter verändert.
- Vorhandene lokale Qwen-/Ollama-Tests und der Android-Inferenzpfad werden verglichen. Es wird nicht ohne Messung zwischen Modellen gewechselt.
- Modellwahl anhand realer Antwortqualität, RAM-/VRAM-Verbrauch, Startzeit, Antwortlatenz und Absturzfreiheit. Kein Modell wird als kompatibel bezeichnet, bevor es auf der vorgesehenen Hardware getestet wurde.
- Falls die Android-App einen PC mit Ollama nutzt, braucht sie eine klare Verbindungskonfiguration, verständliche Verbindungsfehler und eine sichere Verbindung im lokalen Netzwerk. PC-Inferenz funktioniert nur, wenn der PC läuft und erreichbar ist.
- Eine vollständig lokale Android-Ausführung bleibt als Option erhalten. Modell und Inferenzschnittstelle sollen austauschbar sein.
- Optionaler Cloud-Modus kann später ergänzt werden, darf aber keine Voraussetzung für die Grundfunktion sein. Keine API-Schlüssel oder Zugangsdaten fest in die APK einbauen.

## 5. Stimme, Mikrofon und freihändige Nutzung

- Deutsche Sprachausgabe mit möglichst natürlichem Klang, sinnvoller Betonung, Pausen und Sprechtempo.
- TTS muss als austauschbare Komponente behandelt werden. Erst vorhandene Supertonic-/Android-TTS-Integration testen, bevor sie ersetzt wird.
- Spracherkennung (ASR) und TTS getrennt diagnostizieren, damit Fehlerquellen eindeutig bleiben.
- Chat bleibt auch dann nutzbar, wenn Mikrofon, ASR, TTS oder Wakeword nicht verfügbar sind.
- Sprachfehler dürfen die App nicht beenden: Fehler abfangen, Status anzeigen, Textausgabe bzw. erneuten Versuch ermöglichen.
- Antworten sollen bei Bedarf unterbrechbar werden; freihändige Aktivierung über „Hey Pip“ nur, wenn sie zuverlässig und mit vertretbarem Akkuverbrauch funktioniert.
- Emotionale Sprechweise und nichtsprachliche Laute sind optionale spätere Qualitätsmerkmale. Sie werden nur übernommen, wenn sie natürlich klingen und rechtlich/technisch zulässig sind; keine bloße Behauptung ohne Hörtest.

## 6. Oberfläche und Einstellungen

Eine übersichtliche Android-Oberfläche mit:
- Chatverlauf und sichtbarem Lade-/Fehlerstatus.
- Mikrofon-, Aufnahme- und Sprachausgabestatus.
- Zentralen Einstellungen für Modell/Verbindung, Stimme, Name/Avatar und Gesprächsstil.
- Reglern oder Auswahlmöglichkeiten für Eigeninitiative, Humor, Romantik/Flirt und spielerische Eifersucht.
- Gedächtnisverwaltung: ansehen, bearbeiten, einzeln löschen und komplett zurücksetzen.
- Datenschutz- und Benachrichtigungseinstellungen.
- Sinnvollen, bereits voreingestellten Werten, sodass Pip nach der Installation nicht erst mühsam eingerichtet werden muss.

## 7. Benachrichtigungen außerhalb der App

- Optional und standardmäßig deaktiviert.
- Nur nach ausdrücklicher Aktivierung und mit den notwendigen Android-Berechtigungen.
- Nutzer kann Häufigkeit, Ruhezeiten und Aktivierung steuern sowie jederzeit alles abschalten.
- Keine manipulativen, schuldinduzierenden oder übermäßig häufigen Nachrichten.
- Wenn die App keine sichere Hintergrundausführung erlaubt, darf keine dauerhafte Erreichbarkeit versprochen werden.

## 8. Stabilität und Fehlerbehandlung

- Modellinitialisierung, Inferenz, TTS, ASR, Datenbank und Hintergrunddienste dürfen sich nicht gegenseitig zum Absturz bringen.
- Doppelte Modellstarts und parallele Inferenz müssen kontrolliert werden; Zeitüberschreitungen und Speicherfehler müssen abgefangen werden.
- Bei fehlendem Modell, Netzwerk, Mikrofon, Berechtigung oder TTS gibt es eine klare Fehlermeldung und einen sinnvollen Rückweg zum Textchat.
- Keine stillen Fehler, keine endlosen Ladezustände und keine automatischen riskanten Text-/Regex-Patches ohne Prüfung.
- Protokolle dürfen keine Passwörter, Tokens oder unnötigen privaten Gesprächsinhalte enthalten.

## 9. Ein gemeinsamer Entwicklungsablauf

Alle Funktionen werden in **einer gemeinsamen Arbeitslinie** zusammengeführt. Die Reihenfolge ist eine Testreihenfolge, keine Aufteilung in voneinander unabhängige Endprodukte:

1. **Sicherung und Bestandsaufnahme:** aktuellen Branch, ZIP, Workflow und verfügbare APK-/Build-Artefakte sichern; Dateien und tatsächliche Integrationspunkte prüfen.
2. **Reproduzierbarer Build:** den vorhandenen Workflow ohne unbeabsichtigte Änderungen reproduzieren; Fehler und Versionen dokumentieren.
3. **Stabile KI-Basis:** Modellstart, Inferenz, Zeitlimits, Speicherverbrauch und PC-/lokale Verbindung testen.
4. **Persönlichkeit + Kontext:** einen zentralen, versionierten Pip-Systemprompt und Kontextaufbau integrieren; deutsche Testdialoge ausführen.
5. **Persistentes Gedächtnis:** Datenbank, Kontextübergabe und Verwaltung in der Oberfläche gemeinsam testen.
6. **Sprache:** TTS, ASR, Unterbrechung und optionales Wakeword in derselben App integrieren; Ausfall darf Chat nicht blockieren.
7. **Einstellungen + Benachrichtigungen:** zentrale Konfiguration und Opt-in-Benachrichtigungen verbinden.
8. **Gesamttest:** erst nach bestandenen Tests eine gemeinsame APK als Kandidat markieren.

Nach jedem Schritt wird der integrierte Projektstand gebaut und getestet, bevor weitere Änderungen darauf aufbauen. Es werden keine separaten Feature-APK-Versionen als Endlösung erzeugt.

## 10. Verbindliche Abnahmetests

- APK lässt sich sauber bauen, installieren, starten und wieder öffnen.
- Textchat funktioniert wiederholt und bleibt bei Modell-/Netzwerkfehler bedienbar.
- Antworten sind auf Deutsch, passen zur Persönlichkeit und wiederholen nicht ständig dieselben Floskeln.
- Tatsächliche frühere Gesprächsinformationen werden passend verwendet; falsche Erinnerungen werden nicht erfunden.
- Gedächtnis bleibt nach einem Neustart erhalten; Bearbeiten/Löschen/Zurücksetzen funktioniert.
- TTS- und ASR-Fehler führen nicht zum App-Absturz.
- Mikrofon- und Benachrichtigungsberechtigungen werden korrekt und verständlich angefragt.
- Benachrichtigungen bleiben aus, bis sie ausdrücklich aktiviert wurden.
- Speicherverbrauch, Startzeit und Antwortlatenz werden auf dem Zielgerät protokolliert und bewertet.
- Ein Build wird erst dann „stabil“ genannt, wenn diese Tests tatsächlich bestanden wurden.

## 11. Git- und Änderungsregeln

- `main` bleibt unangetastet, bis Änderungen geprüft sind.
- Arbeit erfolgt zunächst auf `pip-spec-2026-10-25` bzw. einem klar benannten Integrationsbranch.
- Bestehende Dateien werden gelesen und verstanden, bevor sie ersetzt werden.
- Das Quellarchiv und seine Build-Patches sind gemeinsam zu behandeln: dieselbe Änderung darf nicht an einer Stelle ergänzt und an einer anderen Stelle versehentlich überschrieben werden.
- Jede Änderung wird mit Zweck, betroffenen Dateien und Testergebnis dokumentiert.
- Wenn der tatsächliche Quelltext oder ein reproduzierbarer Build nicht verfügbar ist, wird das offen benannt; es wird nicht behauptet, Funktionen seien bereits implementiert.

## 12. Aktueller Status und nächster notwendiger Schritt

- Arbeitsbranch: `pip-spec-2026-10-25`; `main` bleibt unverändert.
- Der Android-Build verarbeitet weiterhin das vorhandene Archiv `Pip-v4.9-Qwen-1.5B-Supertonic.zip` über die versionierten Integrations- und Qualitäts-Patches. Das unveränderte und gepatchte Quellarchiv werden als getrennte Artefakte gesichert.
- Buildlauf 204 (Commit `676e7df`, 25.10.2026): Android-Quellvertragstests und APK-Build waren erfolgreich; die sechs PC-Server-Unit-Tests bestanden. **Der Emulator-Test war nicht erfolgreich:** `aapt dump badging` brach beim Ermitteln der Paket-ID ab. Der Fehler wurde durch `continue-on-error: true` verdeckt; dieser Lauf zählt daher nicht als bestandener Funktionstest.
- Bei der Quellprüfung wurde ein Integrationsfehler gefunden: `.github/scripts/patch-pip-quality.py` überschrieb den zuvor korrekt optionalen PC-Modus und leitete jede normale Nachricht zwingend zum PC weiter. Dadurch war die lokale Android-Inferenz unerreichbar. Der Patch wurde so korrigiert, dass der PC-Modus nur bei ausdrücklich aktivierter Einstellung verwendet wird und die lokale Modellroute erhalten bleibt. Ein zusätzlicher statischer Vertragstest schützt genau diesen Fall.
- Der Emulator-Schritt baut jetzt eine separate x86_64-Testvariante, führt `connectedDebugAndroidTest` aus und startet anschließend die App. Der Emulator-Schritt ist nicht mehr als „best effort“ markiert: Fehler sollen den Build sichtbar fehlschlagen lassen. Die verteilbare APK bleibt weiterhin die arm64-Variante.
- Bereits vorhandene Bausteine: zentraler deutscher Persönlichkeitsprompt, lokales Qwen-GGUF mit verzögertem Start, lokale SQLite-Erinnerungen mit Anzeigen/Bearbeiten/Löschen/Zurücksetzen, manuelle On-Device-Spracherkennung, Android-TTS-Fallback, Stimmeinstellungen, optionaler PC-Ollama-Server mit Token, sowie standardmäßig ausgeschaltete Erinnerungsbenachrichtigungen mit Intervall und Ruhezeit.
- Noch **nicht als fertig abgenommen**: natürlicher Supertonic-Stimmklang (die Antwortpfade verwenden aktuell Android-TTS, bis ein sicherer Hörtest gelingt), tatsächliche Sprachausgabe und Offline-ASR auf einem physischen Telefon, PC-/LAN-Verbindung mit realem Ollama, Laufzeit-/Speichermessungen auf dem Zielgerät und der vollständige Neustart-/Einstellungs-/Benachrichtigungsablauf.
- Nächster Schritt: den korrigierten Branch-Build abwarten, tatsächliche Instrumentierungsergebnisse auswerten und etwaige Fehler beheben. Danach sind weiterhin reale Telefon-/LAN- und Hörtests nötig. Kein Merge nach `main`, solange die verbindlichen Abnahmetests nicht nachweislich bestanden sind.
