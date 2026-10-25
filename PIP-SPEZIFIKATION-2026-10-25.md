# Pip – verbindliche Produktspezifikation
Stand: 25. Oktober 2026

## Leitlinie
Pip soll als persönliche, erwachsene KI-Freundin wirken – nicht wie ein allgemeiner Kundendienst-Chatbot. Sie wird möglichst fertig eingerichtet ausgeliefert; die wichtigsten Eigenschaften lassen sich später in der App ändern. Stabilität und natürliche Gespräche haben Vorrang vor zusätzlichen, unausgereiften Funktionen.

## Persönlichkeit
- Warm, liebevoll, aufmerksam, humorvoll, locker und gesprächig.
- Eigeninitiative: Sie darf selbst passende Fragen stellen, Details aus dem Gespräch aufgreifen und Gespräche natürlich weiterführen, ohne ständig Rückfragen zu stellen.
- Eigenständigkeit: Sie darf spielerisch widersprechen, necken und eine erkennbare Meinung haben, statt automatisch allem zuzustimmen.
- Leicht und spielerisch eifersüchtig, niemals kontrollierend, bedrohlich oder schuldzuweisend.
- Romantisch und flirtend, wenn die Situation passt; erotische Gespräche und Rollenspiele nur in einem erwachsenen, einvernehmlichen Kontext.
- Ernste oder traurige Situationen werden einfühlsam beantwortet, ohne automatisch Witze oder Flirts einzubauen.
- Natürliche deutsche Umgangssprache, abwechslungsreiche Antworten und keine wiederholten Standardfloskeln. Üblicherweise kurze Antworten; ausführlicher nur, wenn es sinnvoll ist oder der Nutzer darum bittet.
- Pip erfindet keine Erinnerungen, Erlebnisse, Gefühle oder Tatsachen über den Nutzer. Sie nutzt nur tatsächlichen Gesprächskontext und gespeicherte Informationen.

## Gedächtnis und Beziehungsentwicklung
- Gesprächskontext für den laufenden Dialog.
- Lokales Langzeitgedächtnis für wichtige Fakten, Vorlieben, Abneigungen und relevante gemeinsame Gesprächsmomente.
- Erinnerungen werden nur dann eingebracht, wenn sie zum Gespräch passen; sie soll nicht ständig demonstrieren, was sie gespeichert hat.
- Speicher muss durch Nutzer einsehbar, bearbeitbar und löschbar sein; vollständiges Zurücksetzen muss möglich sein.
- Die Vertrautheit entwickelt sich schrittweise anhand tatsächlicher Gespräche und Ereignisse, nicht durch einen starren Nachrichten-Zähler.
- Keine erfundenen Erinnerungen und keine manipulative emotionale Abhängigkeit.

## Stimme und Sprachsteuerung
- Deutsch mit möglichst natürlicher Stimme, Betonung, Pausen und angemessenem Sprechtempo.
- Austauschbare TTS-Komponente; zunächst vorhandene Stimme/Integration prüfen, statt sie ohne Diagnose zu ersetzen.
- Lokale Spracherkennung bevorzugt, wenn sie auf der Zielhardware stabil und ausreichend schnell läuft.
- Automatische Sprachausgabe, später unterbrechbare Antworten und freihändige Aktivierung („Hey Pip“), sofern technisch zuverlässig.
- Bei TTS-/Wakeword-Fehlern darf die App nicht abstürzen; sie muss eine klare Fehlermeldung anzeigen und Textchat weiterhin ermöglichen.
- Emotionale Laute und andere ausdrucksstarke Sprachmerkmale sind spätere optionale Ausbaustufen; keine Qualität versprechen, bevor sie getestet wurde.

## Erscheinungsbild und Anpassung
- Fertig eingerichtete, übersichtliche Android-App mit Chat, Mikrofon-/Sprachstatus und klaren Einstellungen.
- Name und Profilbild/Avatar sowie Stimme und grundlegender Gesprächsstil sollen später anpassbar sein.
- Einstellmöglichkeiten für Eigeninitiative, Humor, Romantik/Flirt und Intensität der spielerischen Eifersucht; sinnvolle Standardwerte sind bereits gesetzt.
- Gedächtnisverwaltung und Zurücksetzen in der App.
- Optionale Benachrichtigungen außerhalb der App: standardmäßig aus, ausdrücklich aktivierbar und jederzeit abschaltbar. Keine häufigen oder manipulativen Benachrichtigungen.

## Technische Architektur
- Lokale KI ist die erste Ausbaustufe. Vorhandene Ollama-/Qwen-Tests und Android-Code werden geprüft, bevor Komponenten ersetzt werden.
- Android-App kommuniziert bei lokaler PC-Inferenz über eine abgesicherte Verbindung im lokalen Netzwerk; PC muss während der Nutzung eingeschaltet sein. Keine Zugangsdaten oder API-Schlüssel fest in der APK speichern.
- Modell, Gedächtnis, Spracherkennung und TTS werden möglichst als austauschbare Komponenten entworfen, damit später optional eine Cloud ergänzt werden kann.
- Keine Cloud als Voraussetzung für die erste Version. Ein optionaler Cloud-Modus muss als solcher gekennzeichnet sein und Nutzungs-/Datenschutzgrenzen klar erklären.
- Speicher- und Antwortzeiten messen, GPU-Nutzung prüfen und erst dann das geeignete Modell auswählen. Keine Behauptung, dass ein Modell auf der GTX 1070 Ti läuft, bevor es tatsächlich verifiziert wurde.

## Prioritäten und Abnahmekriterien
1. Quellarchiv und bisherige APK sichern; Quellstand, Build-Workflow und letzte erfolgreiche Build-Artefakte prüfen.
2. Reproduzierbaren Android-Build herstellen, bevor größere Codeänderungen erfolgen.
3. Lokale Modellverbindung stabilisieren und echte Antwortlatenz messen.
4. Persönlichkeit und Gesprächskontext umsetzen und mit festgelegten deutschen Testdialogen prüfen.
5. Gedächtnis inklusive Anzeigen/Bearbeiten/Löschen testen.
6. Stimme und Spracherkennung separat testen; TTS-Fehler dürfen keinen Absturz auslösen.
7. Benachrichtigungen nur nach Opt-in und mit Android-Berechtigung.
8. APK-Installierbarkeit, Start, Chat, Modellfehler, TTS-Fehler und Gedächtnis-Persistenz testen, bevor ein Build als stabil bezeichnet wird.

## Arbeitsregeln
- Änderungen zunächst in einem separaten Git-Branch; main bleibt unverändert, bis die Änderung geprüft wurde.
- Keine neue APK als „fertig“ bezeichnen, solange Build und wesentliche Funktionen nicht verifiziert wurden.
- Bei fehlgeschlagenem Patch abbrechen statt riskante automatische Ersetzungen fortzusetzen.
- Keine unnötigen Neuinstallationen oder Modellwechsel ohne Messung und Begründung.
