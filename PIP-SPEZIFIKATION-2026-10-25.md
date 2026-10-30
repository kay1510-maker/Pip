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
- Das aktuelle Projekt nennt das Quellarchiv `Pip-v4.9-Qwen-1.5B-Supertonic.zip`. `681cc3594d89b1e0e76b73c06a2f9aa7ff43791b` („Use smaller Qwen 0.5B model to prevent response-time crashes“, 18.10.2026) ist die Basis des Arbeitsbranches; der aktuelle `main`-HEAD am 28.10.2026 ist `34293546e87e9f56d3edc2525ea3d6eae845d5f5` („Make Pip APK builds manual only“). Der Workflow patcht Teile des Archivs beim Build. Diese Patch-Kette muss geprüft werden, bevor man sie weiter verändert.
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


### CI-Nachtrag 2026-10-27

- Der korrigierte Buildlauf 207 (`270c1a26`) bestand die PC-Server-Tests (6 Tests), die statischen Quellverträge, den APK-Build und die APK-Validierung. Die Android-Instrumentierung lief tatsächlich: drei der vier Tests bestanden, darunter alle drei SQLite-Gedächtnistests. Der UI-Test scheiterte vor seiner ersten Interaktion mit `RootViewWithoutFocusException`; das Protokoll zeigt, dass die Einstellungenprüfung unnötig über `GrantPermissionRule` eine Mikrofonberechtigung anforderte, während Pip diese Berechtigung zusätzlich beim App-Start anfragte.
- In diesem Schritt wird die Mikrofonberechtigung erst nach einem ausdrücklichen Tipp auf **🎤 Sprechen** angefordert. Das beseitigt den früher vermuteten Berechtigungsdialog als Ursache, reichte aber noch nicht aus.
- Buildlauf 208 (Commit `d876d0d`) bestand APK-Build und APK-Validierung, scheiterte jedoch vor den Tests beim Emulatorstart: `sys.boot_completed` blieb leer. Deshalb wurden für den nächsten Versuch Boot-Zeitlimit und Arbeitsspeicher erhöht.
- Buildlauf 209 (Commit `ae878218`) bestätigte: Emulatorstart, APK-Build/-Validierung und die sechs PC-Server-Unit-Tests waren erfolgreich; auch die drei SQLite-Gedächtnis-Instrumentierungstests bestanden. Der vierte Test `settingsControlSpeechAndExposeOptInReminderOptions` scheiterte weiterhin beim allerersten Espresso-Klick (Zeile 30) mit `RootViewWithoutFocusException`. Im Log ist `MainActivity` zwar `RESUMED`, aber das Fenster hat keinen Fokus; der Test erreicht keine UI-Assertion. Der UI-Funktionstest ist somit weiterhin **nicht bestanden**.
- Nächster konkreter Versuch: den headless Emulator vor den Instrumentierungstests mit `KEYCODE_WAKEUP`, `wm dismiss-keyguard` und `KEYCODE_MENU` aufwecken/entsperren. Der Emulator-Schritt erhält außerdem ein 20-Minuten-Limit, damit ein hängender Testlauf nicht den gesamten Job blockiert. Nach diesem Fix müssen die vollständigen Instrumentierungstests erneut ausgewertet werden.
- `main` bleibt unverändert. Vor dem Fokus-Fix wurde `backup/pip-spec-2026-10-27-before-focus-fix` auf Commit `ae878218` angelegt; frühere Stände bleiben durch `backup/pip-spec-2026-10-27-before-emulator-shell-fix` und `backup/pip-spec-2026-10-27-before-mic-permission-fix` gesichert.

### CI-Nachtrag 2026-10-27 – Instrumentierungsdiagnose

- Sicherungsbranch `backup/pip-spec-2026-10-27-before-instrumentation-diagnostics` bewahrt den vorherigen Arbeitsstand `f1f632a6dfe86a2c7550c0ca5a5b2761a2250797`.
- Buildlauf 40470778291 (Commit `f1f632a6`) bestand Quellintegration, statische Vertragstests, APK-Build und APK-Validierung sowie die PC-Server-Tests. Die Android-Instrumentierung startete, meldete dann jedoch `Process crashed` und **0 ausgeführte Tests**; damit ist der Funktionstest nicht bestanden. Das Testartefakt enthielt keine Ursache im Logcat, weil das Shellskript beim fehlgeschlagenen Gradle-Befehl sofort abbrach.
- Der Workflow sichert nun bei Instrumentierungsfehlern den tatsächlichen Gradle-Exitcode, das vollständige Gradle-Testprotokoll, Logcat und `dumpsys activity` als Artefakte. Das ist Diagnoseinstrumentierung, keine Behebung des App-/Emulatorfehlers.
- Nächster Schritt: den durch den PR-Branch-Update ausgelösten Lauf auswerten, Ursache aus Logcat bestimmen und erst dann die kleinste begründete Code-/Emulatoränderung vornehmen. Der integrierte APK-Kandidat bleibt bis zu einem erfolgreichen vollständigen Testlauf gesperrt; echte Geräte-, Sprach- und PC-Ollama-Tests sind weiterhin offen. `main` bleibt unverändert.



### CI-Nachtrag 2026-10-27 – Buildlauf 213 / Emulator-Startabbruch

- Buildlauf 213 (Commit `a01a32df`) bestand weiterhin die statischen Quellvertragstests, den arm64-APK-Build und die APK-Validierung. Der PC-Server-Workflow war erfolgreich.
- Die Android-Instrumentierung scheiterte erneut **vor dem ersten Test**: Das XML-Testprotokoll meldet `tests="0"` und `Process crashed`. Das gesicherte Logcat zeigt, dass `de.pip.companion` beim Prozessstart in einen ANR lief (`failed to complete startup`); gleichzeitig scheiterten auch mehrere Android-Systemprozesse beim Start. Es gab keine fehlgeschlagene Test-Assertion, daher ist dies zunächst als Emulator-/Startstabilitätsproblem zu behandeln, nicht als bestandener App-Funktionstest und auch nicht als nachgewiesener Fehler einer bestimmten UI-Assertion.
- Die Diagnoseartefakte `Pip-Android-Testberichte` wurden aus Lauf 213 gesichert und geprüft. Der vorangehende Buildlauf 212 hatte bereits gezeigt, dass Build und APK-Prüfung vor der Instrumentierung erfolgreich sind.
- Vor der nächsten Änderung wurde der aktuelle Stand auf `backup/pip-spec-2026-10-27-before-emulator-resource-fix` bei Commit `a01a32df` gesichert.
- Nächster begründeter Versuch: die Instrumentierung auf ein API-34-Emulator-Image umstellen, den Kaltstart-Zeitpuffer auf 900 Sekunden erhöhen und dem Headless-Emulator 3072 MiB RAM sowie 4 virtuelle CPU-Kerne geben. Danach die Instrumentierungsergebnisse und Logcat erneut prüfen. Der Test bleibt verpflichtend; ein grüner APK-Build allein reicht nicht für die Abnahme. `main` bleibt unverändert.


### CI-Nachtrag 2026-10-27 – API-34-Instrumentierung

- Buildlauf 215 (Commit `de61c7ad`) bestand die statischen Quellvertragstests, den APK-Build und die APK-Validierung. Der PC-Server-Workflow bestand erneut alle sechs Unit-Tests (API, Tokenprüfung, SQLite-Erinnerungen und Fehlerpfade).
- Der API-34-Emulator startete diesmal und führte tatsächlich alle vier Android-Instrumentierungstests aus. Die drei Gedächtnistests bestanden. Der UI-Test scheiterte jedoch beim allerersten Espresso-Klick mit `RootViewWithoutFocusException` (`has-window-focus=false`), bevor eine fachliche UI-Assertion ausgeführt wurde. Damit ist die Gesamt-Instrumentierung weiterhin fehlgeschlagen; das ist kein Nachweis für bestandene Einstellungen-/Benachrichtigungsfunktionen.
- Der Quellstand wurde vor dem nächsten Testumbau auf `backup/pip-spec-2026-10-27-before-uiautomator-fix` bei Commit `de61c7ad` gesichert.
- Nächster begründeter Versuch: den Fokus-abhängigen Espresso-UI-Test durch UIAutomator zu ersetzen, der die sichtbaren Bedienelemente über die Accessibility-Hierarchie bedient, und zugleich statisch zu prüfen, dass dieser Testpfad tatsächlich erzeugt wird. Die Gedächtnistests bleiben unverändert. Nach dem nächsten Lauf sind die Testberichte zu prüfen; keine Abnahme allein aufgrund eines erfolgreichen APK-Builds.
- Weiter offen: realer Ollama-PC-/LAN-Test, Chat mit echtem lokalem Modell auf dem Zielgerät, Hörtest der deutschen Stimme, Offline-ASR auf einem physischen Telefon sowie Neustart-/Einstellungs-/Benachrichtigungs-Gesamttest. `main` bleibt unverändert.


### CI-Nachtrag 2026-10-28 – UIAutomator-Testdiagnose und nächster Fix

- Der zuletzt verfügbare Android-Buildlauf 216 (Commit `517ed805`, 27.10.2026) bestand Quellintegration, statische Quellverträge, arm64-APK-Build und APK-Validierung. Die Emulator-Instrumentierung führte alle vier Tests aus: drei Gedächtnistests bestanden; der UI-Test scheiterte vor der ersten fachlichen Assertion, weil UIAutomator den Einstellungsbutton nicht innerhalb von zehn Sekunden fand. Das Testprotokoll zeigt, dass `MainActivity` kurz `RESUMED` war und danach `PAUSED/STOPPED`; der Emulator-Bericht meldete später `mSleeping=true`. Es wurde kein App-Absturz als Ursache nachgewiesen.
- Der Testgenerator `.github/scripts/patch-pip-quality.py` wird angepasst: Der Emulator-Bildschirm bleibt für zehn Minuten aktiv, die App wird nach dem Start erneut aufgeweckt und entsperrt, der Einstellungsbutton wird ohne exakte Emoji-Zeichenfolge gesucht, und bei erneut fehlendem UI-Element wird die Accessibility-Hierarchie im Fehlertext gesichert. `.github/scripts/test-pip-source.py` prüft diese Schutzmaßnahmen statisch.
- Vor dieser Änderung wurde `backup/pip-spec-2026-10-28-before-ui-test-fix` auf dem vorherigen Branch-Stand `1b1566b0bf86cd44127a7546a312314a699b41fd` angelegt. `main` wurde nicht verändert.
- **Build-Blockade für diesen Lauf:** Seit Commit `1b1566b` ist `.github/workflows/build-apk.yml` absichtlich nur noch über `workflow_dispatch` startbar, damit APK-Builds nicht bei jeder Branch-/PR-Änderung automatisch anlaufen. Die verfügbaren GitHub-Aktionen erlauben das Lesen von Workflows und das erneute Ausführen alter Jobs, stellen hier aber keine Aktion zum manuellen Auslösen von `workflow_dispatch` bereit. Einen alten fehlgeschlagenen Job erneut auszuführen würde den neuen Quellstand nicht testen; daher wird das nicht als Verifikation ausgegeben. Nach dem Commit kann der PC-Server-Testworkflow automatisch laufen, aber der Android-Build samt Emulator-Instrumentierung bleibt bis zu einem manuellen Dispatch unbestätigt.
- Noch offen: vollständiger neuer Android-Instrumentierungslauf, reales Gerät mit deutscher TTS und Offline-ASR, echte Verbindung zu Ollama im privaten LAN, Laufzeit-/Speichermessungen sowie der durchgehende Neustart-/Einstellungs-/Benachrichtigungsablauf. Die gemeinsame Version bleibt bis zu diesen Nachweisen nicht abgenommen.


### CI-Nachtrag 2026-10-28 – Lokale Ollama-Konfiguration und Skriptprüfung

- Der vorhandene PC-Server setzt `PIP_NUM_GPU=0` als Standard und sendet `think: false` an Ollama. Das ist eine bewusste CPU-Voreinstellung für Systeme, auf denen der CUDA-/PTX-Pfad nicht kompatibel ist. GPU-Auslagerung bleibt konfigurierbar, sollte aber erst nach einem echten GPU-Test aktiviert werden.
- Der manuelle PC-Smoke-Test vom 25.10.2026 verwendete `qwen3:4b` mit `num_gpu=0` und erhielt `Hallo!`; Ollama meldete etwa 33,3 Sekunden Gesamtdauer und gab zusätzlich ein langes `thinking`-Feld zurück. Das belegt nur, dass dieser einzelne CPU-API-Aufruf antwortete. Es ist **kein** Test des PC-Servers, der Android-App oder der vollständigen Pip-Verbindung; die Laufzeit bleibt zu prüfen.
- Ergänzend wurde `.github/workflows/test-pip-integration.yml` erstellt. Diese leichte Prüfung baut **keine APK**; sie soll Python-Syntax und die UI-Testgenerator-Schutzverträge prüfen, während `.github/workflows/build-apk.yml` weiterhin nur manuell startet. Ein Lauf dieser neuen Prüfung wurde für die per GitHub-API erstellten Commits nicht beobachtet, deshalb wird kein Testergebnis behauptet.
- Die UI-Testgenerator- und Workflow-Änderungen liegen auf `pip-spec-2026-10-25`; Sicherung vor der UI-Teständerung: `backup/pip-spec-2026-10-28-before-ui-test-fix` auf `1b1566b0bf86cd44127a7546a312314a699b41fd`. Der aktuelle `main`-Stand bleibt `34293546e87e9f56d3edc2525ea3d6eae845d5f5`; kein Merge und keine Änderung an `main`.
- Weiterhin zwingend offen: neuer Android-Build-/Emulatorlauf nach dem UI-Testfix, physischer Telefon-/Sprachtest, reale PC-/LAN-Verbindung zu Ollama sowie Messungen von Antwortlatenz und Speicherverbrauch. Die integrierte Version ist nicht abgenommen.


### CI-Nachtrag 2026-10-29 – PR-Testtrigger und verifizierbare Blockade

- Vor der Änderung der Testauslöser wurde der Branch-Stand `9922f03516a75d667ca01200c3579172f8e0fa73` auf `backup/pip-spec-2026-10-29-before-ci-triggers` gesichert.
- `.github/workflows/test-pip-integration.yml` und `.github/workflows/test-pc-server.yml` sind nun so konfiguriert, dass sie bei Pull-Request-Aktualisierungen gegen `main` laufen; der APK-/Emulator-Workflow `.github/workflows/build-apk.yml` bleibt bewusst ausschließlich über `workflow_dispatch` startbar. Damit werden die schnellen Python-/Quellvertragstests von einem vollständigen Android-Build getrennt.
- Die GitHub-Aktionen in dieser Ausführungsumgebung stellen keinen manuellen `workflow_dispatch`-Aufruf bereit. Nach den Workflow-Änderungen lieferte `fetch_commit_workflow_runs` für den Branch-HEAD `2a615dcc21be3343de8c82aa75da76c364d292a7` keine PR-Workflow-Läufe; der kombinierte Commit-Status enthielt ebenfalls keine Checks. Deshalb wird weder für die neuen Workflow-Änderungen noch für die Android-App ein Testergebnis behauptet.
- Lokale Ausführung des Builds ist hier ebenfalls nicht möglich: `gradle`, `adb` und `ANDROID_HOME` fehlen. Ein Versuch, das Repository für lokale Tests zu klonen, scheiterte an nicht auflösbarem `github.com` (`Could not resolve host`). Die Quelltexte konnten über die GitHub-API gelesen werden, aber die tatsächlichen Android-Instrumentierungstests und der APK-Build wurden in diesem Lauf nicht ausgeführt.
- Der Branch enthält jetzt zwei zusätzliche Workflow-Änderungscommits; der aktuelle Branch-HEAD ist `2a615dcc21be3343de8c82aa75da76c364d292a7`. `main` blieb unangetastet; der zuletzt über die Commit-Vergleichs-API bestätigte `main`-HEAD ist `19875fd31a67fc6b0cb464c8e4a3628aa995f1da`. Der Branch ist weiterhin gegenüber `main` divergiert (111 Commits voraus, 2 zurück); kein Merge wurde ausgeführt.
- Nächster notwendiger Schritt bleibt ein tatsächlicher PR-CI-Lauf für die beiden leichten Prüfungen sowie ein manuell ausgelöster APK-/Emulator-Lauf durch eine Umgebung mit Actions-Dispatch-Berechtigung. Danach sind weiterhin ein physisches Android-Gerät, ein echter Ollama-PC-/LAN-Test, Hörtest der deutschen TTS und Offline-ASR sowie Laufzeit-/Speichermessungen erforderlich. Pip ist nicht abgenommen.


### Integrationsnachtrag 2026-10-30 – PC-Gehirn, Gedächtnis und CI-Ausführung

- Vor Änderungen wurden der aktuelle Branch-HEAD f338cc349f20e5262ccdaaaf56869a11c5a250e7, der Masterplan, die drei Actions-Workflows, die Integrations-/Qualitätsskripte, der PC-Server und seine Tests geprüft. Der unveränderte Stand wurde auf backup/pip-spec-2026-10-30-before-push-ci-trigger gesichert. main blieb bei 19875fd31a67fc6b0cb464c8e4a3628aa995f1da.
- Das gepatchte Quellartefakt aus Buildlauf 216 wurde tatsächlich heruntergeladen und untersucht. Dabei zeigte sich eine Integrationslücke: Die Android-App übergab dem PC nur Nachricht und Sitzungs-ID. Die lokal gespeicherten Gesprächsstil-Regler erreichten den PC-Prompt nicht; Änderungen oder Löschungen lokaler Erinnerungen wurden nicht in den PC-Erinnerungsspiegel übernommen.
- Der Build-Patch sendet im optionalen PC-Modus jetzt den Pip-Namen, die vier Gesprächsstil-Regler und einen begrenzten Snapshot von bis zu 50 lokalen Erinnerungen inklusive Kategorie. Das Handy bleibt Quelle der Wahrheit; der PC ersetzt seinen Erinnerungsspiegel vor jeder Chat-Inferenz mit diesem Snapshot. Explizite Merkvorgänge werden dadurch nicht doppelt gespeichert.
- Der PC-Server erhält eine rückwärtskompatible SQLite-Schemamigration für Erinnerungskategorien, wendet die Gesprächsstil-Regler auf den Systemprompt an und unterstützt das Ersetzen/Löschen des synchronisierten Erinnerungssnapshots. Neue Unit-Tests prüfen Persönlichkeit und Synchronisierung einschließlich Löschungen. Der statische Android-Quellvertrag prüft, dass beide Payload-Felder tatsächlich in den generierten App-Quelltext gelangen.
- Die beiden leichten Prüfworkflows und der APK-/Emulator-Workflow erhalten einen push-Auslöser, der ausschließlich auf pip-spec-2026-10-25 reagiert. Grund: Die vorherigen PR-Workflows waren nur auf dem Arbeitsbranch vorhanden; es wurden für HEAD f338cc3 weder PR-Workflow-Läufe noch Statuschecks beobachtet. Ein branch-lokaler Push-Trigger ermöglicht die Verifikation, ohne main zu verändern. Der vollständige APK-/Emulator-Workflow bleibt zusätzlich manuell auslösbar.
- Testergebnis nach dieser Änderung: noch ausstehend. Erst der tatsächlich ausgelöste GitHub-Actions-Lauf darf die neuen Python-, Quellvertrag-, APK- und Emulatorprüfungen als bestanden oder fehlgeschlagen bewerten. Physische Geräte-, Hör-, Offline-ASR- und echte PC-/WLAN-/Ollama-Tests bleiben zusätzlich offen.


### CI-Nachtrag 2026-10-30 – erste Ergebnisse des neuen Push-Laufs

- PC-Server-Workflow 41023354739: erfolgreich. Python-Syntaxprüfung und alle 8 Unit-Tests bestanden, darunter neue Tests für die Android-Persönlichkeitseinstellungen sowie die Synchronisierung und Löschung lokaler Erinnerungen.
- APK-Workflow 41023354734: Quellintegration und statische Pip-Verträge erfolgreich; APK-Build und APK-Validierung erfolgreich. Der Android-Emulator-Instrumentierungsschritt lief zum Zeitpunkt dieses Nachtrags noch; sein Ergebnis ist ausdrücklich offen.
- Der leichte Integrationsworkflow 41023354740 scheiterte nicht an Python-Syntax oder den Quellschutzprüfungen, sondern ausschließlich an einer veralteten Guard-Bedingung, die den APK-Workflow weiterhin als rein manuell erwartete. Die Bedingung wird an den branch-lokalen Push-Auslöser angepasst. Der APK-Workflow erhält zusätzlich einen Pfadfilter, damit reine Masterplan-/CI-Teständerungen keinen unnötigen vollständigen Emulator-Build starten.
