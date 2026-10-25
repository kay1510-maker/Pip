from pathlib import Path
import re
import shutil

BASE = Path("pip-src/app/src/main/java/de/pip/companion")
main_path = BASE / "MainActivity.kt"
db_path = BASE / "PipMemoryDb.java"
worker_path = BASE / "PipReminderWorker.kt"
manifest_path = Path("pip-src/app/src/main/AndroidManifest.xml")
gradle_path = Path("pip-src/app/build.gradle")

def replace_once(text, old, new, label):
    count = text.count(old)
    if count != 1:
        raise SystemExit(f"{label}: expected exactly one match, found {count}; refusing unsafe patch")
    return text.replace(old, new, 1)

# Bound and separate the two context sources so important saved memories are not displaced by chat logs.
old_context = r"""    public String context(int limit){
        StringBuilder s=new StringBuilder();
        Cursor c=getReadableDatabase().rawQuery("SELECT category,content FROM memories ORDER BY importance DESC,created DESC LIMIT ?",
          new String[]{String.valueOf(limit)});
        while(c.moveToNext()) s.append("- ").append(c.getString(0)).append(": ").append(c.getString(1)).append("\n");
        c.close();
        return s.toString();
    }"""
new_context = r"""    public String context(int limit){
        StringBuilder result = new StringBuilder();
        Cursor memories = getReadableDatabase().rawQuery(
          "SELECT category,content FROM memories WHERE category!='Gespräch' ORDER BY importance DESC,created DESC LIMIT 5", null);
        int memoryCount = 0;
        while(memories.moveToNext() && memoryCount < 5){
            String category = memories.getString(0) == null ? "Erinnerung" : memories.getString(0);
            String content = memories.getString(1) == null ? "" : memories.getString(1).trim().replace("\n"," ");
            if(content.length() > 100) content = content.substring(0,100) + "…";
            if(memoryCount == 0) result.append("Wichtige Erinnerungen:\n");
            result.append("- ").append(category).append(": ").append(content).append("\n");
            memoryCount++;
        }
        memories.close();
        ArrayList<String> recent = new ArrayList<>();
        Cursor conversations = getReadableDatabase().rawQuery(
          "SELECT content FROM memories WHERE category='Gespräch' ORDER BY created DESC LIMIT ?",
          new String[]{String.valueOf(Math.max(3, Math.min(6, limit)))});
        while(conversations.moveToNext()){
            String content = conversations.getString(0);
            if(content != null && !content.trim().isEmpty()) recent.add(content.trim());
        }
        conversations.close();
        ArrayList<String> selected = new ArrayList<>();
        int remaining = Math.max(0, 1800 - result.length() - 24);
        for(String row : recent){
            String line = row.replace("\n"," ").trim();
            if(line.length() > 170) line = line.substring(0,170) + "…";
            if(line.length() + 3 > remaining) break;
            selected.add(line);
            remaining -= line.length() + 3;
        }
        Collections.reverse(selected);
        if(!selected.isEmpty()) result.append("Letzte Gespräche:\n");
        for(String line : selected) result.append("- ").append(line).append("\n");
        return result.toString();
    }"""
db = db_path.read_text(encoding="utf-8")
db = replace_once(db, old_context, new_context, "separate long-term memories from recent conversation")
db_path.write_text(db, encoding="utf-8")

# Keep the prompt within a predictable budget while retaining the combined context.
main = main_path.read_text(encoding="utf-8")
old_prompt = "Gesprächsverlauf: " + "$" + "{context.takeLast(1200)}"
new_prompt = "Gedächtnis und letzte Gespräche: " + "$" + "{context.take(1800)}"
if main.count(old_prompt) != 1:
    raise SystemExit("Prompt context insertion point not unique")
main = main.replace(old_prompt, new_prompt, 1)

main, n = re.subn(
    r"    override fun onResume\(\) \{\s*super\.onResume\(\)\s*// Voice input is started only by the microphone button; this prevents it stealing text input focus\.\s*stopService\(Intent\(this, PipListeningService::class\.java\)\)\s*\}\s*",
    "",
    main,
    count=1,
    flags=re.S,
)
if n == 0 and "PipListeningService" in main:
    raise SystemExit("Could not safely remove the unused wakeword-service reference")
main = main.replace("tts.speak(answer, TextToSpeech.QUEUE_FLUSH, null, \"pip\")",
                    "tts.speak(displayAnswer, TextToSpeech.QUEUE_FLUSH, null, \"pip\")")
main = replace_once(
    main,
    '        val q = text.trim()\n        if (q.isEmpty()) return\n        appendHistory("Kay", q)',
    '        val q = text.trim()\n        if (q.isEmpty()) return\n        input.setText("")\n        appendHistory("Kay", q)',
    "clear submitted chat input",
)


# Prevent accidental double-submits and reject obvious stale/model-loop replies.
main = replace_once(
    main,
    "    private var model: Any? = null",
    "    private var model: Any? = null\n    private var lastSubmittedText: String = \"\"\n    private var lastSubmittedAt: Long = 0L",
    "add duplicate-submit guard state",
)
main = replace_once(
    main,
    '        val q = text.trim()\n        if (q.isEmpty()) return\n        input.setText("")',
    '''        val q = text.trim()
        if (q.isEmpty()) return
        val now = android.os.SystemClock.elapsedRealtime()
        if (q.equals(lastSubmittedText, ignoreCase = true) && now - lastSubmittedAt < 2500L) {
            status.text = "Nachricht wurde bereits gesendet."
            return
        }
        lastSubmittedText = q
        lastSubmittedAt = now
        input.setText("")''',
    "ignore duplicate taps or repeated recognizer result",
)
main = replace_once(
    main,
    '            val answer = result.text.trim().ifEmpty { "Hmm … mir fällt gerade nichts ein. ❤️" }',
    '''            var answer = result.text.trim().ifEmpty { "Hmm … mir fällt gerade nichts ein. ❤️" }
            val normalizedAnswer = answer.lowercase(Locale.ROOT).replace(Regex("\\\\s+"), " ").trim()
            val isKnownBadTemplate = normalizedAnswer.contains("du wärst ganz schön eingesprungen") ||
                normalizedAnswer.contains("als wäre ich ein kind")
            val repeatsRecentAnswer = db.context(8).lowercase(Locale.ROOT)
                .contains("pip: " + normalizedAnswer.take(100)) && normalizedAnswer.length > 35
            if (isKnownBadTemplate || repeatsRecentAnswer) {
                answer = when {
                    q.matches(Regex("(?i)\\\\s*(hallo|hi|hey|na du)[!.? ]*")) ->
                        "Hey Kay 😊 Na, da bist du ja. Wie geht's dir?"
                    q.contains("vermisst", ignoreCase = true) ->
                        "Ein bisschen schon, du 😉 Was hast du so getrieben?"
                    q.equals("okay", ignoreCase = true) || q.equals("ok", ignoreCase = true) ->
                        "Na gut 😄"
                    else ->
                        "Uff, das war gerade keine passende Antwort von mir. Versuch's bitte nochmal – ich will auf das eingehen, was du wirklich gesagt hast."
                }
            }''',
    "reject stale repeated answers and nonsensical known template",
)



# SpeechRecognizer creation/startup can throw on devices without a usable offline German service.
pattern = r"    private fun startListening\(\) \{.*?\n    \}\n\n    override fun onInit\(statusCode: Int\) \{"
replacement = r"""    private fun startListening() {
        if (!SpeechRecognizer.isRecognitionAvailable(this)) {
            output.text = "Spracherkennung ist auf diesem Gerät nicht verfügbar."
            status.text = "Du kannst Pip weiterhin schreiben."
            return
        }
        try {
            recognizer?.destroy()
            recognizer = SpeechRecognizer.createOnDeviceSpeechRecognizer(this)
            recognizer?.setRecognitionListener(object : RecognitionListener {
                override fun onReadyForSpeech(p: Bundle?) { output.text = "🎤 Ich höre …" }
                override fun onResults(b: Bundle?) {
                    val heard = b?.getStringArrayList(SpeechRecognizer.RESULTS_RECOGNITION)?.firstOrNull()?.trim().orEmpty()
                    if (heard.isBlank()) {
                        status.text = "Nichts erkannt – tippe auf 🎤 und versuche es nochmal"
                        scheduleListenAgain()
                        return
                    }
                    input.setText(heard)
                    status.text = "Nachricht erkannt – Pip antwortet …"
                    ask(heard)
                }
                override fun onError(e: Int) {
                    status.text = "Spracheingabe fehlgeschlagen. Du kannst weiter schreiben oder es erneut versuchen."
                    scheduleListenAgain()
                }
                override fun onBeginningOfSpeech() {}
                override fun onBufferReceived(b: ByteArray?) {}
                override fun onEndOfSpeech() {}
                override fun onEvent(t: Int, b: Bundle?) {}
                override fun onPartialResults(b: Bundle?) {}
                override fun onRmsChanged(v: Float) {}
            })
            recognizer?.startListening(Intent(RecognizerIntent.ACTION_RECOGNIZE_SPEECH).apply {
                putExtra(RecognizerIntent.EXTRA_LANGUAGE, "de-DE")
                putExtra(RecognizerIntent.EXTRA_LANGUAGE_PREFERENCE, "de-DE")
                putExtra(RecognizerIntent.EXTRA_PARTIAL_RESULTS, false)
            })
        } catch (e: Throwable) {
            try { recognizer?.cancel(); recognizer?.destroy() } catch (_: Throwable) {}
            recognizer = null
            status.text = "Spracherkennung konnte nicht gestartet werden."
            output.text = "Die Spracheingabe ist gerade nicht verfügbar. Prüfe die Mikrofonberechtigung oder installiere ein deutsches Offline-Sprachpaket."
        }
    }

    override fun onInit(statusCode: Int) {"""
main, n = re.subn(pattern, replacement, main, count=1, flags=re.S)
if n != 1:
    raise SystemExit("Could not safely harden the startListening method")
# Replace only the notification settings + scheduler, leaving profile and voice settings intact.
notification_pattern = r"    private fun showNotificationSettings\(\) \{.*?\n    private fun showProfileSettings\(\) \{"
notification_replacement = r"""    private fun showNotificationSettings() {
        val prefs = getSharedPreferences("pip_settings", MODE_PRIVATE)
        val enabled = prefs.getBoolean("notifications_enabled", false)
        val panel = LinearLayout(this).apply {
            orientation = LinearLayout.VERTICAL
            setPadding(32, 8, 32, 0)
        }
        panel.addView(TextView(this).apply {
            text = "Freiwillig und standardmäßig aus. Wenn ein geplanter Zeitpunkt in die Ruhezeit fällt, wird die Erinnerung ausgelassen."
        })
        val intervalDays = intArrayOf(1, 2, 7)
        val intervalLabels = arrayOf("Täglich", "Alle 2 Tage", "Wöchentlich")
        val intervalSpinner = Spinner(this).apply {
            adapter = ArrayAdapter(this@MainActivity, android.R.layout.simple_spinner_dropdown_item, intervalLabels)
            setSelection(intervalDays.indexOf(prefs.getInt("notification_interval_days", 1)).coerceAtLeast(0))
        }
        val hours = (0..23).map { String.format(Locale.GERMANY, "%02d:00", it) }.toTypedArray()
        val quietStart = Spinner(this).apply {
            adapter = ArrayAdapter(this@MainActivity, android.R.layout.simple_spinner_dropdown_item, hours)
            setSelection(prefs.getInt("quiet_start_hour", 22).coerceIn(0, 23))
        }
        val quietEnd = Spinner(this).apply {
            adapter = ArrayAdapter(this@MainActivity, android.R.layout.simple_spinner_dropdown_item, hours)
            setSelection(prefs.getInt("quiet_end_hour", 8).coerceIn(0, 23))
        }
        panel.addView(TextView(this).apply { text = "Häufigkeit" })
        panel.addView(intervalSpinner)
        panel.addView(TextView(this).apply { text = "Ruhezeit beginnt" })
        panel.addView(quietStart)
        panel.addView(TextView(this).apply { text = "Ruhezeit endet" })
        panel.addView(quietEnd)
        val saveSettings = {
            prefs.edit()
                .putInt("notification_interval_days", intervalDays[intervalSpinner.selectedItemPosition.coerceIn(0, intervalDays.lastIndex)])
                .putInt("quiet_start_hour", quietStart.selectedItemPosition.coerceIn(0, 23))
                .putInt("quiet_end_hour", quietEnd.selectedItemPosition.coerceIn(0, 23))
                .apply()
        }
        AlertDialog.Builder(this)
            .setTitle("Pip-Benachrichtigungen")
            .setView(panel)
            .setNegativeButton("Schließen", null)
            .setPositiveButton("Speichern") { _, _ ->
                saveSettings()
                if (enabled) scheduleDailyNotification()
                status.text = if (enabled) "Benachrichtigungseinstellungen gespeichert." else "Einstellungen gespeichert; Benachrichtigungen bleiben aus."
            }
            .setNeutralButton(if (enabled) "Ausschalten" else "Aktivieren") { _, _ ->
                saveSettings()
                if (enabled) {
                    prefs.edit().putBoolean("notifications_enabled", false).putBoolean("notifications_pending", false).apply()
                    androidx.work.WorkManager.getInstance(this).cancelUniqueWork("pip_daily_ping")
                    status.text = "Pip-Benachrichtigungen ausgeschaltet."
                } else if (android.os.Build.VERSION.SDK_INT >= 33 &&
                    ContextCompat.checkSelfPermission(this, Manifest.permission.POST_NOTIFICATIONS) != PackageManager.PERMISSION_GRANTED) {
                    prefs.edit().putBoolean("notifications_pending", true).apply()
                    ActivityCompat.requestPermissions(this, arrayOf(Manifest.permission.POST_NOTIFICATIONS), 11)
                } else {
                    prefs.edit().putBoolean("notifications_enabled", true).putBoolean("notifications_pending", false).apply()
                    scheduleDailyNotification()
                    status.text = "Pip-Erinnerung aktiviert."
                }
            }
            .show()
    }

    private fun scheduleDailyNotification() {
        val prefs = getSharedPreferences("pip_settings", MODE_PRIVATE)
        val days = prefs.getInt("notification_interval_days", 1).coerceIn(1, 7).toLong()
        val request = androidx.work.PeriodicWorkRequestBuilder<PipReminderWorker>(days, java.util.concurrent.TimeUnit.DAYS)
            .setInitialDelay(days, java.util.concurrent.TimeUnit.DAYS).build()
        androidx.work.WorkManager.getInstance(this).enqueueUniquePeriodicWork(
            "pip_daily_ping", androidx.work.ExistingPeriodicWorkPolicy.UPDATE, request)
    }

    private fun showProfileSettings() {"""
main, n = re.subn(notification_pattern, notification_replacement, main, count=1, flags=re.S)
if n != 1:
    raise SystemExit("Could not safely replace notification settings/scheduler")
main = main.replace("Tägliche Pip-Erinnerung aktiviert.", "Pip-Erinnerung aktiviert.")

# PC replies follow the same safe Android-TTS path as local replies; Supertonic stays disabled.
pc_old = r"""            val answer = json.optString("reply", "").trim()
            if (answer.isBlank()) throw IllegalStateException("Der PC hat eine leere Antwort geliefert.")
            db.remember("Gespräch", "Nutzer: $q | Pip: $answer", 1)
            db.pruneConversationLog(500)
            withContext(Dispatchers.Main) {
                output.text = answer
                appendHistory("Pip", answer)
                status.text = "PC verbunden · " + json.optString("model", "Ollama")
            }
            if (prefs.getBoolean("speech_enabled", true)) speakWithSupertonic(answer)"""
pc_new = r"""            val answer = json.optString("reply", "").trim()
            if (answer.isBlank()) throw IllegalStateException("Der PC hat eine leere Antwort geliefert.")
            val displayAnswer = answer.replace(Regex("<\\/?[a-zA-Z]+>"), "")
                .replace(Regex("\\s{2,}"), " ").trim()
            db.remember("Gespräch", "Nutzer: $q | Pip: $displayAnswer", 1)
            db.pruneConversationLog(500)
            withContext(Dispatchers.Main) {
                output.text = displayAnswer
                appendHistory("Pip", displayAnswer)
                status.text = "PC verbunden · " + json.optString("model", "Ollama")
                if (prefs.getBoolean("speech_enabled", true)) {
                    try { tts.speak(displayAnswer, TextToSpeech.QUEUE_FLUSH, null, "pip") } catch (_: Throwable) {
                        status.text = "Sprachausgabe nicht verfügbar; Textchat funktioniert weiter."
                    }
                }
            }"""
main = replace_once(main, pc_old, pc_new, "use Android TTS for PC replies")

# Explicit "remember this" requests are saved locally first, then mirrored to the PC only when that backend is enabled.
memory_start = main.index("        val memoryMatch = Regex(")
route_marker = '        if (getSharedPreferences("pip_settings", MODE_PRIVATE).getBoolean("pc_backend_enabled", false)) {'
memory_end = main.index(route_marker, memory_start)
if memory_start < 0 or memory_end < 0:
    raise SystemExit("Could not locate the explicit-memory branch before PC routing")
memory_block = r"""        val memoryMatch = Regex("(?i)^(?:pip[, ]*)?(?:merk dir|merke dir|bitte merk dir|bitte merke dir)\\s*[:,\\-]?\\s*(.+)$").find(q)
        val explicitMemory = memoryMatch?.groupValues?.getOrNull(1)?.trim()?.takeIf { it.isNotBlank() }?.take(500)
        if (explicitMemory != null) {
            db.remember("Von dir gemerkt", explicitMemory, 3)
            if (getSharedPreferences("pip_settings", MODE_PRIVATE).getBoolean("pc_backend_enabled", false)) {
                output.text = "Ich speichere mir das auch auf dem PC …"
                status.text = "Erinnerung lokal gespeichert; PC-Synchronisierung läuft …"
                lifecycleScope.launch(Dispatchers.IO) { askWithPc(q) }
                return
            }
            val reply = "Mach ich. Ich merk mir: " + explicitMemory
            db.remember("Gespräch", "Nutzer: " + q + " | Pip: " + reply, 1)
            db.pruneConversationLog(500)
            output.text = reply
            status.text = "Erinnerung gespeichert."
            appendHistory("Pip", reply)
            if (getSharedPreferences("pip_settings", MODE_PRIVATE).getBoolean("speech_enabled", true)) {
                try { tts.speak(reply, TextToSpeech.QUEUE_FLUSH, null, "pip") } catch (_: Throwable) { }
            }
            return
        }
"""
main = main[:memory_start] + memory_block + main[memory_end:]

# PC-only mode: no local Qwen inference, including on connection failure.
# Route all normal messages to the PC and preserve the settings screen for configuring it.
route_start = main.index('        if (getSharedPreferences("pip_settings", MODE_PRIVATE).getBoolean("pc_backend_enabled", false)) {', main.index('        val memoryMatch = Regex(') + 1)
# The first match is inside the explicit-memory handler; locate the next normal-chat branch.
route_start = main.index('        if (getSharedPreferences("pip_settings", MODE_PRIVATE).getBoolean("pc_backend_enabled", false)) {', route_start + 1)
route_end = main.index('\n        if (model == null)', route_start)
main = main[:route_start] + '''        output.text = "Verbinde mit Pips PC-Gehirn …"
        status.text = "PC-Modus · Qwen3 4B"
        lifecycleScope.launch(Dispatchers.IO) { askWithPc(q) }
        return
''' + main[route_end:]
# Prevent the app from automatically downloading/loading the unused mobile model.
main = main.replace('        lifecycleScope.launch(Dispatchers.IO) { prepareModel() }', '        // PC-only: no mobile model preload.')

# Never send the PC bearer token to a public host or an unsupported URL scheme.
pc_connection_marker = '            conn = (URL("$base/chat").openConnection() as HttpURLConnection).apply {'
main = replace_once(
    main,
    pc_connection_marker,
    """            val endpoint = URL(base)
            if (endpoint.protocol != "http" && endpoint.protocol != "https") {
                throw IllegalArgumentException("Die PC-Adresse muss mit http:// oder https:// beginnen.")
            }
            val address = java.net.InetAddress.getByName(endpoint.host)
            if (!address.isLoopbackAddress && !address.isSiteLocalAddress && !address.isLinkLocalAddress) {
                throw IllegalArgumentException("Nur private oder lokale PC-Adressen sind erlaubt.")
            }
""" + pc_connection_marker,
    "restrict PC backend to private addresses",
)
main = main.replace(
    "Ich erreiche mein PC-Gehirn gerade nicht. Prüfe, ob der Server läuft und die Adresse stimmt. ($e)",
    "Ich erreiche das PC-Gehirn gerade nicht. Prüfe Server, Token und private Netzwerkadresse. Lokale Erinnerungen bleiben auf dem Handy gespeichert."
)

# Extend the existing onDestroy implementation rather than creating a duplicate.
on_destroy_pattern = r"    override fun onDestroy\(\) \{.*?\n    \}"
def ensure_on_destroy_cleanup(match):
    block = match.group(0)
    if "db.close()" not in block:
        block = block.replace("        super.onDestroy()", "        try { db.close() } catch (_: Throwable) { }\n        super.onDestroy()")
    if "tts.stop()" not in block:
        block = block.replace(
            "        if (::tts.isInitialized) tts.shutdown()",
            "        if (::tts.isInitialized) { try { tts.stop(); tts.shutdown() } catch (_: Throwable) { } }",
        )
    return block
main, n = re.subn(on_destroy_pattern, ensure_on_destroy_cleanup, main, count=1, flags=re.S)
if n != 1:
    raise SystemExit("Could not safely extend existing onDestroy cleanup")

main_path.write_text(main, encoding="utf-8")

# Quiet hours are evaluated in the device's local time; if the periodic job lands in the quiet window, skip it.
worker = worker_path.read_text(encoding="utf-8")
worker = replace_once(
    worker,
    """        if (!prefs.getBoolean("notifications_enabled", false)) return Result.success()

        return try {""",
    """        if (!prefs.getBoolean("notifications_enabled", false)) return Result.success()
        val hour = java.time.LocalTime.now().hour
        val quietStart = prefs.getInt("quiet_start_hour", 22).coerceIn(0, 23)
        val quietEnd = prefs.getInt("quiet_end_hour", 8).coerceIn(0, 23)
        val inQuietHours = when {
            quietStart == quietEnd -> false
            quietStart < quietEnd -> hour >= quietStart && hour < quietEnd
            else -> hour >= quietStart || hour < quietEnd
        }
        if (inQuietHours) return Result.success()

        return try {""",
    "respect notification quiet hours",
)
worker_path.write_text(worker, encoding="utf-8")

# Remove the unused, unconnected wakeword service, model files and ONNX dependency from the generated app.
manifest = manifest_path.read_text(encoding="utf-8")
manifest, _ = re.subn(r"\s*<service\s+android:name=\"\.PipListeningService\".*?/>", "", manifest, count=1, flags=re.S)
for permission in (
    '    <uses-permission android:name="android.permission.FOREGROUND_SERVICE" />\n',
    '    <uses-permission android:name="android.permission.FOREGROUND_SERVICE_MICROPHONE" />\n',
):
    manifest = manifest.replace(permission, "")
manifest_path.write_text(manifest, encoding="utf-8")
service_path = BASE / "PipListeningService.kt"
if service_path.exists():
    service_path.unlink()
assets = Path("pip-src/app/src/main/assets/hey_pip")
if assets.exists():
    shutil.rmtree(assets)
gradle = gradle_path.read_text(encoding="utf-8")
gradle = re.sub(r"^\s*implementation ['\"]com\.microsoft\.onnxruntime:onnxruntime-android:[^'\"]+['\"]\s*\n", "", gradle, flags=re.M)
gradle_path.write_text(gradle, encoding="utf-8")


# Remove the unused Android VoiceInteractionService stub as well; no wakeword feature is advertised.
manifest = manifest_path.read_text(encoding="utf-8")
manifest, _ = re.subn(
    r"\s*<service\s+android:name=\"\.PipVoiceInteractionService\".*?</service>",
    "",
    manifest,
    count=1,
    flags=re.S,
)
manifest_path.write_text(manifest, encoding="utf-8")
voice_java = BASE / "PipVoiceInteractionService.java"
if voice_java.exists():
    voice_java.unlink()
voice_xml = Path("pip-src/app/src/main/res/xml/voice_interaction_service.xml")
if voice_xml.exists():
    voice_xml.unlink()

# Add real Android instrumentation tests. The emulator test property adds x86_64 only for CI tests.
gradle = gradle_path.read_text(encoding="utf-8")
gradle = replace_once(
    gradle,
    "        applicationId 'de.pip.companion'\n",
    "        applicationId 'de.pip.companion'\n        testInstrumentationRunner 'androidx.test.runner.AndroidJUnitRunner'\n",
    "configure Android instrumentation runner",
)
gradle = replace_once(
    gradle,
    "        ndk { abiFilters 'arm64-v8a' }",
    """        ndk {
            if (project.hasProperty("pipEmulatorTests")) {
                abiFilters 'arm64-v8a', 'x86_64'
            } else {
                abiFilters 'arm64-v8a'
            }
        }""",
    "allow x86_64 only during emulator tests",
)
if "androidTestImplementation 'androidx.test:runner:1.6.2'" not in gradle:
    gradle = replace_once(
        gradle,
        "dependencies {\n",
        """dependencies {
    androidTestImplementation 'androidx.test:runner:1.6.2'
    androidTestImplementation 'androidx.test:rules:1.6.1'
    androidTestImplementation 'androidx.test:core:1.6.1'
    androidTestImplementation 'androidx.test.ext:junit:1.2.1'
    androidTestImplementation 'androidx.test.espresso:espresso-core:3.6.1'
""",
        "add Android instrumentation test dependencies",
    )
gradle_path.write_text(gradle, encoding="utf-8")

test_dir = Path("pip-src/app/src/androidTest/java/de/pip/companion")
test_dir.mkdir(parents=True, exist_ok=True)
db_test = r"""package de.pip.companion;

import android.content.Context;
import android.database.Cursor;
import androidx.test.ext.junit.runners.AndroidJUnit4;
import androidx.test.platform.app.InstrumentationRegistry;
import org.junit.After;
import org.junit.Before;
import org.junit.Test;
import org.junit.runner.RunWith;
import static org.junit.Assert.*;

@RunWith(AndroidJUnit4.class)
public class PipMemoryDbInstrumentedTest {
    private Context context;
    private PipMemoryDb db;

    @Before public void setUp() {
        context = InstrumentationRegistry.getInstrumentation().getTargetContext();
        context.deleteDatabase("pip_memory.db");
        db = new PipMemoryDb(context);
    }

    @After public void tearDown() {
        if (db != null) db.close();
        if (context != null) context.deleteDatabase("pip_memory.db");
    }

    @Test public void longTermMemoryAndRecentDialogueBothEnterContext() {
        db.remember("Vorliebe", "Kaffee", 3);
        db.remember("Gespräch", "Nutzer: Magst du Kaffee? | Pip: Klar.", 1);
        String contextText = db.context(12);
        assertTrue(contextText.contains("Wichtige Erinnerungen:"));
        assertTrue(contextText.contains("Vorliebe: Kaffee"));
        assertTrue(contextText.contains("Letzte Gespräche:"));
        assertTrue(contextText.contains("Magst du Kaffee?"));
    }

    @Test public void memoryCanBeEditedDeletedAndReset() {
        db.remember("Vorliebe", "Tee", 3);
        Cursor cursor = db.listMemories();
        assertTrue(cursor.moveToFirst());
        long id = cursor.getLong(0);
        cursor.close();

        db.updateMemory(id, "Vorliebe", "Kaffee");
        assertTrue(db.context(12).contains("Vorliebe: Kaffee"));
        db.deleteMemory(id);
        assertFalse(db.context(12).contains("Vorliebe: Kaffee"));

        db.remember("Hinweis", "Zum Zurücksetzen", 3);
        db.clearMemories();
        assertFalse(db.context(12).contains("Zum Zurücksetzen"));
    }

    @Test public void memoriesSurviveHelperRecreation() {
        db.remember("Hinweis", "Persistenz", 3);
        db.close();
        db = new PipMemoryDb(context);
        assertTrue(db.context(12).contains("Hinweis: Persistenz"));
    }
}
"""
(test_dir / "PipMemoryDbInstrumentedTest.java").write_text(db_test, encoding="utf-8")
ui_test = r"""package de.pip.companion;

import android.Manifest;
import android.content.Context;
import androidx.test.core.app.ActivityScenario;
import androidx.test.ext.junit.runners.AndroidJUnit4;
import androidx.test.platform.app.InstrumentationRegistry;
import androidx.test.rule.GrantPermissionRule;
import org.junit.Before;
import org.junit.Rule;
import org.junit.Test;
import org.junit.runner.RunWith;
import static androidx.test.espresso.Espresso.onView;
import static androidx.test.espresso.action.ViewActions.click;
import static androidx.test.espresso.assertion.ViewAssertions.matches;
import static androidx.test.espresso.matcher.ViewMatchers.isDisplayed;
import static androidx.test.espresso.matcher.ViewMatchers.withText;
import static org.junit.Assert.assertFalse;

@RunWith(AndroidJUnit4.class)
public class PipUiInstrumentedTest {
    private Context context;

    @Rule
    public final GrantPermissionRule microphonePermission =
        GrantPermissionRule.grant(Manifest.permission.RECORD_AUDIO);

    @Before public void resetPreferences() {
        context = InstrumentationRegistry.getInstrumentation().getTargetContext();
        context.getSharedPreferences("pip_settings", Context.MODE_PRIVATE).edit().clear().commit();
        context.deleteDatabase("pip_memory.db");
    }

    @Test public void settingsControlSpeechAndExposeOptInReminderOptions() {
        try (ActivityScenario<MainActivity> scenario = ActivityScenario.launch(MainActivity.class)) {
            onView(withText("⚙ Einstellungen & Gedächtnis")).perform(click());
            onView(withText("Gesprächsstil anpassen")).perform(click());
            onView(withText("Antworten laut vorlesen")).check(matches(isDisplayed())).perform(click());
            onView(withText("Speichern")).perform(click());
            assertFalse(context.getSharedPreferences("pip_settings", Context.MODE_PRIVATE)
                .getBoolean("speech_enabled", true));

            onView(withText("⚙ Einstellungen & Gedächtnis")).perform(click());
            onView(withText("Benachrichtigungen außerhalb der App")).perform(click());
            onView(withText("Pip-Benachrichtigungen")).check(matches(isDisplayed()));
            onView(withText("Häufigkeit")).check(matches(isDisplayed()));
            onView(withText("Ruhezeit beginnt")).check(matches(isDisplayed()));
            onView(withText("Ruhezeit endet")).check(matches(isDisplayed()));
            onView(withText("Aktivieren")).check(matches(isDisplayed()));
            assertFalse(context.getSharedPreferences("pip_settings", Context.MODE_PRIVATE)
                .getBoolean("notifications_enabled", false));
        }
    }
}
"""
(test_dir / "PipUiInstrumentedTest.java").write_text(ui_test, encoding="utf-8")

print("Pip-Qualitätsintegration angewendet: Gedächtnis, Sprache, Opt-in-Erinnerungen; Wakeword bleibt bis zum Gerätetest deaktiviert.")

