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

print("Pip-Qualitätsintegration angewendet: Kontexttrennung, ASR-Fehlerbehandlung, konfigurierbare Opt-in-Erinnerungen; Wakeword bleibt bis zum Gerätetest deaktiviert.")
