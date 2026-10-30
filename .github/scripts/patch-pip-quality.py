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



# Request microphone access only after the user explicitly taps the microphone button.
main = replace_once(
    main,
    """        if (ContextCompat.checkSelfPermission(this, Manifest.permission.RECORD_AUDIO)
            != PackageManager.PERMISSION_GRANTED) {
            ActivityCompat.requestPermissions(this, arrayOf(Manifest.permission.RECORD_AUDIO), 10)
        } else {
            status.text = "Mikrofon bereit – tippe auf 🎤 Sprechen"
        }
""",
    """        status.text = "Textchat bereit. Mikrofonzugriff wird erst beim Tippen auf 🎤 Sprechen angefragt."
""",
    "defer microphone permission request until explicit action",
)

# SpeechRecognizer creation/startup can throw on devices without a usable offline German service.
pattern = r"    private fun startListening\(\) \{.*?\n    \}\n\n    override fun onInit\(statusCode: Int\) \{"
replacement = r"""    private fun startListening() {
        if (ContextCompat.checkSelfPermission(this, Manifest.permission.RECORD_AUDIO) != PackageManager.PERMISSION_GRANTED) {
            status.text = "Mikrofonzugriff erforderlich. Erlaube ihn und tippe erneut auf 🎤 Sprechen."
            ActivityCompat.requestPermissions(this, arrayOf(Manifest.permission.RECORD_AUDIO), 10)
            return
        }
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
            text = "Freiwillig und standardmäßig aus. Mit PC-Gehirn erstellt Pip die Nachricht live nach mindestens 24 Stunden Gesprächspause; ohne PC-Gehirn erscheint eine lokale Erinnerung ebenfalls erst nach mindestens 24 Stunden ohne Gespräch. Ruhezeiten werden beachtet."
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

# Keep the PC-hosted model optional; local on-device inference remains the default.
pc_flag = '        if (getSharedPreferences("pip_settings", MODE_PRIVATE).getBoolean("pc_backend_enabled", false)) {'
ask_start = main.index("    private fun ask(text: String) {")
ask_end = main.index("    private suspend fun askLoaded(q: String) {", ask_start)
ask_body = main[ask_start:ask_end]
pc_positions = []
search_from = 0
while True:
    position = ask_body.find(pc_flag, search_from)
    if position < 0:
        break
    pc_positions.append(position)
    search_from = position + len(pc_flag)
if len(pc_positions) < 2:
    raise SystemExit("Expected explicit-memory and normal-chat PC opt-in branches; refusing to ship PC-only routing")
normal_pc_route = pc_positions[-1]
local_model_branch = ask_body.find("        if (model == null)", normal_pc_route)
if local_model_branch < 0 or "askWithPc(q)" not in ask_body[normal_pc_route:local_model_branch]:
    raise SystemExit("PC routing must be opt-in and precede the local-model branch")
print("Optional PC brain verified; local on-device inference remains the default.")

# Keep first launch responsive; load the on-device model only when a message is sent.
preload = '        lifecycleScope.launch(Dispatchers.IO) { prepareModel() }'
if preload in main:
    main = main.replace(preload, '        // Load the on-device model lazily when the first message is sent.', 1)

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
            val hostText = endpoint.host.lowercase(Locale.ROOT)
            val isTailscaleIPv4 = hostText.matches(Regex("^100[.](6[4-9]|[7-9][0-9]|1[01][0-9]|12[0-7])[.][0-9]{1,3}[.][0-9]{1,3}$"))
            if (!address.isLoopbackAddress && !address.isSiteLocalAddress && !address.isLinkLocalAddress && !isTailscaleIPv4) {
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


# Keep the optional PC brain in sync with Android conversation settings and local memories.
# The phone remains the source of truth; snapshots also propagate edits and deletions.
pc_payload_marker = """            val body = org.json.JSONObject()
                .put("message", q)
                .put("session_id", "handy-1")
                .toString().toByteArray(Charsets.UTF_8)"""
pc_payload_replacement = """            val memorySnapshot = org.json.JSONArray()
            val memoryCursor = db.listMemories()
            try {
                while (memoryCursor.moveToNext() && memorySnapshot.length() < 50) {
                    memorySnapshot.put(org.json.JSONObject()
                        .put("category", memoryCursor.getString(1) ?: "Erinnerung")
                        .put("content", memoryCursor.getString(2) ?: ""))
                }
            } finally {
                memoryCursor.close()
            }
            val personality = org.json.JSONObject()
                .put("name", prefs.getString("pip_name", "Pip") ?: "Pip")
                .put("initiative", prefs.getInt("initiative", 70).coerceIn(0, 100))
                .put("humor", prefs.getInt("humor", 65).coerceIn(0, 100))
                .put("romance", prefs.getInt("romance", 60).coerceIn(0, 100))
                .put("jealousy", prefs.getInt("jealousy", 20).coerceIn(0, 100))
            val body = org.json.JSONObject()
                .put("message", q)
                .put("session_id", "handy-1")
                .put("personality", personality)
                .put("memories", memorySnapshot)
                .toString().toByteArray(Charsets.UTF_8)"""
main = replace_once(main, pc_payload_marker, pc_payload_replacement, "sync Android personality and memories with PC backend")

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

    @Test public void lastConversationTimestampIgnoresOrdinaryMemoriesAndResets() {
        long before = System.currentTimeMillis();
        db.remember("Vorliebe", "Tee", 3);
        assertEquals(0L, db.lastConversationAt());

        db.remember("Gespräch", "Nutzer: Hallo | Pip: Hi", 1);
        long last = db.lastConversationAt();
        assertTrue(last >= before);
        assertTrue(System.currentTimeMillis() - last < 5000L);

        db.clearMemories();
        assertEquals(0L, db.lastConversationAt());
    }
}
"""
(test_dir / "PipMemoryDbInstrumentedTest.java").write_text(db_test, encoding="utf-8")
ui_test = r"""package de.pip.companion;

import android.app.AlertDialog;
import android.content.Context;
import android.view.View;
import android.view.ViewGroup;
import android.widget.Button;
import android.widget.ListView;
import android.widget.SeekBar;
import android.widget.Switch;
import android.widget.TextView;
import androidx.test.core.app.ActivityScenario;
import androidx.test.ext.junit.runners.AndroidJUnit4;
import androidx.test.platform.app.InstrumentationRegistry;
import org.junit.Before;
import org.junit.Test;
import org.junit.runner.RunWith;
import static org.junit.Assert.*;

@RunWith(AndroidJUnit4.class)
public class PipUiInstrumentedTest {
    private Context context;

    @Before public void resetPreferences() {
        context = InstrumentationRegistry.getInstrumentation().getTargetContext();
        context.getSharedPreferences("pip_settings", Context.MODE_PRIVATE).edit().clear().commit();
        context.deleteDatabase("pip_memory.db");
    }

    private static Button findButtonContaining(View root, String text) {
        if (root instanceof Button) {
            CharSequence label = ((Button) root).getText();
            if (label != null && label.toString().contains(text)) return (Button) root;
        }
        if (root instanceof ViewGroup) {
            ViewGroup group = (ViewGroup) root;
            for (int i = 0; i < group.getChildCount(); i++) {
                Button found = findButtonContaining(group.getChildAt(i), text);
                if (found != null) return found;
            }
        }
        return null;
    }

    private static Switch findSwitchContaining(View root, String text) {
        if (root instanceof Switch) {
            CharSequence label = ((Switch) root).getText();
            if (label != null && label.toString().contains(text)) return (Switch) root;
        }
        if (root instanceof ViewGroup) {
            ViewGroup group = (ViewGroup) root;
            for (int i = 0; i < group.getChildCount(); i++) {
                Switch found = findSwitchContaining(group.getChildAt(i), text);
                if (found != null) return found;
            }
        }
        return null;
    }

    private static SeekBar findFirstSeekBar(View root) {
        if (root instanceof SeekBar) return (SeekBar) root;
        if (root instanceof ViewGroup) {
            ViewGroup group = (ViewGroup) root;
            for (int i = 0; i < group.getChildCount(); i++) {
                SeekBar found = findFirstSeekBar(group.getChildAt(i));
                if (found != null) return found;
            }
        }
        return null;
    }

    private static boolean containsText(View root, String text) {
        if (root instanceof TextView) {
            CharSequence value = ((TextView) root).getText();
            if (value != null && value.toString().contains(text)) return true;
        }
        if (root instanceof ViewGroup) {
            ViewGroup group = (ViewGroup) root;
            for (int i = 0; i < group.getChildCount(); i++) {
                if (containsText(group.getChildAt(i), text)) return true;
            }
        }
        return false;
    }

    private static void selectItem(AlertDialog dialog, int position) {
        assertNotNull(dialog);
        ListView list = dialog.getListView();
        assertNotNull(list);
        assertNotNull(list.getAdapter());
        assertTrue(position >= 0 && position < list.getAdapter().getCount());
        assertTrue(list.performItemClick(null, position, list.getAdapter().getItemId(position)));
    }

    @Test public void settingsControlSpeechAndExposeOptInReminderOptions() {
        try (ActivityScenario<MainActivity> scenario = ActivityScenario.launch(MainActivity.class)) {
            scenario.onActivity(activity -> {
                Button settingsButton = findButtonContaining(
                    activity.getWindow().getDecorView(), "Einstellungen & Gedächtnis");
                assertNotNull("Settings entry must be present in the actual activity view tree", settingsButton);
                assertTrue(settingsButton.performClick());

                AlertDialog menu = activity.getLastSettingsDialogForTest();
                assertNotNull(menu);
                assertEquals("Pip-Einstellungen", menu.getTitle().toString());
                assertEquals("Gesprächsstil anpassen", menu.getListView().getAdapter().getItem(0).toString());
                selectItem(menu, 0);

                AlertDialog style = activity.getLastSettingsDialogForTest();
                assertNotNull(style);
                Switch speech = findSwitchContaining(style.getWindow().getDecorView(), "Antworten laut vorlesen");
                assertNotNull("Speech toggle must be present in the real settings dialog", speech);
                speech.setChecked(false);
                SeekBar initiative = findFirstSeekBar(style.getWindow().getDecorView());
                assertNotNull("Personality sliders must be present", initiative);
                initiative.setProgress(82);
                style.getButton(AlertDialog.BUTTON_POSITIVE).performClick();

                assertFalse(context.getSharedPreferences("pip_settings", Context.MODE_PRIVATE)
                    .getBoolean("speech_enabled", true));
                assertEquals(82, context.getSharedPreferences("pip_settings", Context.MODE_PRIVATE)
                    .getInt("initiative", 70));

                assertTrue(settingsButton.performClick());
                menu = activity.getLastSettingsDialogForTest();
                assertNotNull(menu);
                assertEquals("Benachrichtigungen außerhalb der App",
                    menu.getListView().getAdapter().getItem(3).toString());
                selectItem(menu, 3);

                AlertDialog notifications = activity.getLastSettingsDialogForTest();
                assertNotNull(notifications);
                View dialogRoot = notifications.getWindow().getDecorView();
                assertTrue(containsText(dialogRoot, "Häufigkeit"));
                assertTrue(containsText(dialogRoot, "Ruhezeit beginnt"));
                assertTrue(containsText(dialogRoot, "Ruhezeit endet"));
                assertFalse(context.getSharedPreferences("pip_settings", Context.MODE_PRIVATE)
                    .getBoolean("notifications_enabled", false));
                notifications.getButton(AlertDialog.BUTTON_POSITIVE).performClick();
                assertFalse(context.getSharedPreferences("pip_settings", Context.MODE_PRIVATE)
                    .getBoolean("notifications_enabled", false));
            });
        }
    }
}"""
(test_dir / "PipUiInstrumentedTest.java").write_text(ui_test, encoding="utf-8")

print("Pip-Qualitätsintegration angewendet: Gedächtnis, Sprache, Opt-in-Erinnerungen; Wakeword bleibt bis zum Gerätetest deaktiviert.")



# Expose the actual settings dialogs to in-process instrumentation tests.
main = main_path.read_text(encoding="utf-8")
field_anchor = "    private var model: Any? = null"
if "lastSettingsDialogForTestRef" not in main:
    if main.count(field_anchor) != 1:
        raise SystemExit("Could not safely add the settings-dialog test reference")
    main = main.replace(
        field_anchor,
        field_anchor + "\n    private var lastSettingsDialogForTestRef: AlertDialog? = null",
        1,
    )

getter_anchor = "    private fun showPipSettings() {"
if "fun getLastSettingsDialogForTest()" not in main:
    if main.count(getter_anchor) != 1:
        raise SystemExit("Could not safely add the settings-dialog test accessor")
    main = main.replace(
        getter_anchor,
        "    fun getLastSettingsDialogForTest(): AlertDialog? = lastSettingsDialogForTestRef\n\n" + getter_anchor,
        1,
    )

def capture_settings_dialog(start_marker, end_marker, label):
    global main
    start = main.index(start_marker)
    end = main.index(end_marker, start)
    block = main[start:end]
    if "lastSettingsDialogForTestRef = it" in block:
        return
    show_at = block.rfind(".show()")
    if show_at < 0:
        raise SystemExit(label + ": dialog show call not found")
    block = block[:show_at] + ".show().also { lastSettingsDialogForTestRef = it }" + block[show_at + len(".show()"):]
    main = main[:start] + block + main[end:]

capture_settings_dialog("    private fun showPipSettings() {", "    private fun showNotificationSettings() {", "main settings dialog")
capture_settings_dialog("    private fun showNotificationSettings() {", "    private fun scheduleDailyNotification() {", "notification settings dialog")
capture_settings_dialog("    private fun showPersonalitySettings() {", "    private fun showMemories() {", "personality settings dialog")
main_path.write_text(main, encoding="utf-8")

print("Settings instrumentation now drives the real activity view and AlertDialogs in-process; external window focus is not required.")


# Make optional reminders use the same PC personality and memory when the PC brain is enabled.
db_path = Path("pip-src/app/src/main/java/de/pip/companion/PipMemoryDb.java")
db_source = db_path.read_text(encoding="utf-8")
db_anchor = "    public String conversationHistory(int limit){"
if "lastConversationAt()" not in db_source:
    if db_source.count(db_anchor) != 1:
        raise SystemExit("Could not safely add local conversation timestamp query")
    db_method = """    public long lastConversationAt(){
        Cursor c = getReadableDatabase().rawQuery(
            "SELECT MAX(created) FROM memories WHERE category='Gespräch'", null);
        long last = 0L;
        try {
            if (c.moveToFirst() && !c.isNull(0)) last = c.getLong(0);
        } finally {
            c.close();
        }
        return last;
    }

"""
    db_source = db_source.replace(db_anchor, db_method + db_anchor, 1)
    db_path.write_text(db_source, encoding="utf-8")

worker_path.write_text(r"""package de.pip.companion

import android.app.NotificationChannel
import android.app.NotificationManager
import android.app.PendingIntent
import android.content.Context
import android.content.Intent
import android.content.SharedPreferences
import android.os.Build
import android.util.Log
import androidx.core.app.NotificationCompat
import androidx.core.app.NotificationManagerCompat
import androidx.work.Worker
import androidx.work.WorkerParameters
import org.json.JSONArray
import org.json.JSONObject
import java.net.HttpURLConnection
import java.net.InetAddress
import java.net.URL
import java.util.Locale

class PipReminderWorker(context: Context, params: WorkerParameters) : Worker(context, params) {
    override fun doWork(): Result {
        val context = applicationContext
        val prefs = context.getSharedPreferences("pip_settings", Context.MODE_PRIVATE)
        if (!prefs.getBoolean("notifications_enabled", false)) return Result.success()

        val hour = java.time.LocalTime.now().hour
        val quietStart = prefs.getInt("quiet_start_hour", 22).coerceIn(0, 23)
        val quietEnd = prefs.getInt("quiet_end_hour", 8).coerceIn(0, 23)
        val inQuietHours = when {
            quietStart == quietEnd -> false
            quietStart < quietEnd -> hour >= quietStart && hour < quietEnd
            else -> hour >= quietStart || hour < quietEnd
        }
        if (inQuietHours) return Result.success()

        val message = (if (prefs.getBoolean("pc_backend_enabled", false)) {
            createPcMessage(context, prefs)
        } else {
            if (!localConversationIsIdle(context)) return Result.success()
            fallbackMessage()
        }) ?: return Result.success()

        return try {
            val channelId = "pip_daily_ping"
            if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
                val channel = NotificationChannel(
                    channelId, "Pip-Erinnerungen", NotificationManager.IMPORTANCE_DEFAULT
                )
                context.getSystemService(NotificationManager::class.java).createNotificationChannel(channel)
            }
            val open = PendingIntent.getActivity(
                context, 714, Intent(context, MainActivity::class.java).apply {
                    flags = Intent.FLAG_ACTIVITY_NEW_TASK or Intent.FLAG_ACTIVITY_SINGLE_TOP
                }, PendingIntent.FLAG_UPDATE_CURRENT or PendingIntent.FLAG_IMMUTABLE
            )
            val notification = NotificationCompat.Builder(context, channelId)
                .setSmallIcon(android.R.drawable.ic_dialog_info)
                .setContentTitle(prefs.getString("pip_name", "Pip") ?: "Pip")
                .setContentText(message)
                .setContentIntent(open)
                .setAutoCancel(true)
                .setPriority(NotificationCompat.PRIORITY_DEFAULT)
                .build()
            NotificationManagerCompat.from(context).notify(714, notification)
            Result.success()
        } catch (_: SecurityException) {
            Result.success()
        } catch (e: Throwable) {
            Log.w(TAG, "Pip-Erinnerung konnte nicht angezeigt werden.", e)
            Result.retry()
        }
    }

    private fun createPcMessage(context: Context, prefs: SharedPreferences): String? {
        val base = (prefs.getString("pc_backend_url", "") ?: "").trim().trimEnd('/')
        val token = (prefs.getString("pc_backend_token", "") ?: "").trim()
        if (base.isBlank() || token.length < 24) return null

        var connection: HttpURLConnection? = null
        return try {
            val endpoint = URL(base)
            if ((endpoint.protocol != "http" && endpoint.protocol != "https") || endpoint.host.isBlank()) return null
            val host = endpoint.host.lowercase(Locale.ROOT)
            val address = InetAddress.getByName(endpoint.host)
            val isTailscaleIPv4 = host.matches(
                Regex("^100[.](6[4-9]|[7-9][0-9]|1[01][0-9]|12[0-7])[.][0-9]{1,3}[.][0-9]{1,3}$")
            )
            if (!address.isLoopbackAddress && !address.isSiteLocalAddress &&
                !address.isLinkLocalAddress && !isTailscaleIPv4) return null

            val payload = JSONObject()
            val personality = JSONObject()
                .put("name", prefs.getString("pip_name", "Pip") ?: "Pip")
                .put("initiative", prefs.getInt("initiative", 70))
                .put("humor", prefs.getInt("humor", 65))
                .put("romance", prefs.getInt("romance", 60))
                .put("jealousy", prefs.getInt("jealousy", 20))
            payload.put("personality", personality)

            // Send a complete snapshot when the local DB can be read. An empty list is
            // meaningful (the user may have deleted every memory); a read error omits it.
            try {
                val memoryDb = PipMemoryDb(context)
                try {
                    val lastConversationAt = memoryDb.lastConversationAt()
                    if (lastConversationAt > 0L) payload.put("last_user_at", lastConversationAt / 1000L)
                    val localRecentContext = memoryDb.conversationHistory(8)
                    if (localRecentContext.isNotBlank()) payload.put("recent_context", localRecentContext.take(6000))
                    val cursor = memoryDb.listMemories()
                    try {
                        val memories = JSONArray()
                        while (cursor.moveToNext() && memories.length() < 50) {
                            memories.put(
                                JSONObject()
                                    .put("category", cursor.getString(1) ?: "Erinnerung")
                                    .put("content", cursor.getString(2) ?: "")
                            )
                        }
                        payload.put("memories", memories)
                    } finally {
                        cursor.close()
                    }
                } finally {
                    memoryDb.close()
                }
            } catch (e: Exception) {
                Log.w(TAG, "Lokales Gedächtnis konnte nicht synchronisiert werden; PC-Snapshot bleibt bestehen.", e)
            }

            connection = URL("$base/proactive").openConnection() as HttpURLConnection
            connection!!.apply {
                requestMethod = "POST"
                connectTimeout = 15000
                readTimeout = 240000
                doOutput = true
                setRequestProperty("Content-Type", "application/json; charset=utf-8")
                setRequestProperty("Accept", "application/json")
                setRequestProperty("Authorization", "Bearer $token")
                outputStream.use { it.write(payload.toString().toByteArray(Charsets.UTF_8)) }
            }
            if (connection!!.responseCode !in 200..299) {
                Log.w(TAG, "PC-Proaktivnachricht nicht verfügbar (HTTP \${connection!!.responseCode}).")
                return null
            }
            val response = connection!!.inputStream.bufferedReader(Charsets.UTF_8).use { it.readText() }
            val result = JSONObject(response)
            if (!result.optBoolean("ready", false)) return null
            result.optString("message", "").trim().take(500).takeIf { it.isNotBlank() }
        } catch (e: Exception) {
            Log.w(TAG, "PC-Proaktivnachricht konnte nicht abgerufen werden.", e)
            null
        } finally {
            connection?.disconnect()
        }
    }

    private fun fallbackMessage(): String {
        val messages = arrayOf(
            "Na, hast du kurz Lust zu quatschen? ❤️",
            "Ich bin da, wenn du ein bisschen reden magst. 😌",
            "Wie läuft dein Tag bisher? Erzähl mir, wenn du magst. 💗"
        )
        return messages[(System.currentTimeMillis() / 86_400_000L % messages.size).toInt()]
    }

    companion object {
        private const val TAG = "PipReminderWorker"
    }
}
""", encoding="utf-8")
