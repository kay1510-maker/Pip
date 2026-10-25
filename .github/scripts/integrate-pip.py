from pathlib import Path
import re

BASE = Path("pip-src/app/src/main/java/de/pip/companion")
main_path = BASE / "MainActivity.kt"
db_path = BASE / "PipMemoryDb.java"
gradle_path = Path("pip-src/app/build.gradle")

def replace_once(text, old, new, label):
    count = text.count(old)
    if count != 1:
        raise SystemExit(f"{label}: expected exactly one match, found {count}; refusing unsafe patch")
    return text.replace(old, new, 1)

s = main_path.read_text(encoding="utf-8")
s = replace_once(s, "LlamaConfig(contextSize = 256, threads = 4)", "LlamaConfig(contextSize = 1536, threads = 4)", "increase context window")
s = replace_once(s, "Gesprächsverlauf: ${context.takeLast(160)}", "Gesprächsstil: Eigeninitiative ${initiative}/100, Humor ${humor}/100, Romantik/Flirt ${romance}/100, spielerische Eifersucht ${jealousy}/100. Passe diese Intensitäten an die Situation an; Eifersucht bleibt spielerisch und niemals kontrollierend.\nGesprächsverlauf: ${context.takeLast(1200)}", "extend relevant conversation context")
s = replace_once(s, "Kay: ${q.take(120)}", "Kay: ${q.take(400)}", "allow natural user message length")
s = replace_once(s, "maxTokens = 32", "maxTokens = 96", "allow fuller replies")
s = replace_once(s, "            db.develop(1)\n", "            // Beziehung wächst nicht automatisch mit jedem Nachrichten-Zähler.\n", "remove artificial relationship counter")
s = replace_once(s, '            db.remember("Gespräch", "Nutzer: $q | Pip: $displayAnswer", 1)\n', '            db.remember("Gespräch", "Nutzer: $q | Pip: $displayAnswer", 1)\n            db.pruneConversationLog(500)\n', "bound conversation history size")
s = replace_once(s, "            val context = PipContextBuilder.build(db)\n            val prompt = ", """            val context = PipContextBuilder.build(db)
            val prefs = getSharedPreferences("pip_settings", MODE_PRIVATE)
            val initiative = prefs.getInt("initiative", 70)
            val humor = prefs.getInt("humor", 65)
            val romance = prefs.getInt("romance", 60)
            val jealousy = prefs.getInt("jealousy", 20)
            val prompt = """, "read personality preferences")
s = replace_once(s, "        root.addView(row)\n        setContentView(root)", """        root.addView(row)
        root.addView(Button(this).apply {
            text = "⚙ Einstellungen & Gedächtnis"
            setOnClickListener { showPipSettings() }
        })
        setContentView(root)""", "add settings entry point")
s = replace_once(s, "    private suspend fun prepareModel() {", """    private fun showPipSettings() {
        val options = arrayOf("Gesprächsstil anpassen", "Gespeicherte Erinnerungen ansehen / löschen", "Alle Erinnerungen zurücksetzen")
        AlertDialog.Builder(this)
            .setTitle("Pip-Einstellungen")
            .setItems(options) { _, which ->
                when (which) {
                    0 -> showPersonalitySettings()
                    1 -> showMemories()
                    2 -> AlertDialog.Builder(this)
                        .setTitle("Gedächtnis zurücksetzen?")
                        .setMessage("Alle lokal gespeicherten Gesprächserinnerungen werden gelöscht. Das kann nicht rückgängig gemacht werden.")
                        .setNegativeButton("Abbrechen", null)
                        .setPositiveButton("Alles löschen") { _, _ ->
                            db.clearMemories()
                            status.text = "Gedächtnis zurückgesetzt."
                        }
                        .show()
                }
            }
            .setNegativeButton("Schließen", null)
            .show()
    }

    private fun showPersonalitySettings() {
        val prefs = getSharedPreferences("pip_settings", MODE_PRIVATE)
        val panel = LinearLayout(this).apply {
            orientation = LinearLayout.VERTICAL
            setPadding(36, 12, 36, 0)
        }
        val sliders = linkedMapOf<String, SeekBar>()
        val settings = listOf(
            Triple("Eigeninitiative", "initiative", 70),
            Triple("Humor", "humor", 65),
            Triple("Romantik / Flirt", "romance", 60),
            Triple("Spielerische Eifersucht", "jealousy", 20)
        )
        for ((label, key, defaultValue) in settings) {
            panel.addView(TextView(this).apply { text = "$label: ${prefs.getInt(key, defaultValue)}" })
            val slider = SeekBar(this).apply {
                max = 100
                progress = prefs.getInt(key, defaultValue)
            }
            slider.setOnSeekBarChangeListener(object : android.widget.SeekBar.OnSeekBarChangeListener {
                override fun onProgressChanged(seekBar: SeekBar?, progress: Int, fromUser: Boolean) {
                    (panel.getChildAt(panel.indexOfChild(slider) - 1) as? TextView)?.text = "$label: $progress"
                }
                override fun onStartTrackingTouch(seekBar: SeekBar?) {}
                override fun onStopTrackingTouch(seekBar: SeekBar?) {}
            })
            sliders[key] = slider
            panel.addView(slider)
        }
        AlertDialog.Builder(this)
            .setTitle("Pips Gesprächsstil")
            .setView(panel)
            .setNegativeButton("Abbrechen", null)
            .setPositiveButton("Speichern") { _, _ ->
                val editor = prefs.edit()
                for ((key, slider) in sliders) editor.putInt(key, slider.progress)
                editor.apply()
                status.text = "Pips Gesprächsstil gespeichert."
            }
            .show()
    }

    private fun showMemories() {
        val cursor = db.listMemories()
        val ids = ArrayList<Long>()
        val labels = ArrayList<String>()
        while (cursor.moveToNext()) {
            ids.add(cursor.getLong(0))
            val category = cursor.getString(1) ?: "Erinnerung"
            val content = cursor.getString(2) ?: ""
            labels.add("$category: $content".replace("\\n", " ").take(180))
        }
        cursor.close()
        if (labels.isEmpty()) {
            AlertDialog.Builder(this).setTitle("Gedächtnis").setMessage("Noch keine separat gespeicherten Erinnerungen. Sag mir „Merk dir …“, wenn ich etwas behalten soll.")
                .setPositiveButton("OK", null).show()
            return
        }
        AlertDialog.Builder(this)
            .setTitle("Erinnerung antippen, um sie zu löschen")
            .setItems(labels.toTypedArray()) { _, which ->
                AlertDialog.Builder(this)
                    .setTitle("Erinnerung löschen?")
                    .setMessage(labels[which])
                    .setNegativeButton("Abbrechen", null)
                    .setPositiveButton("Löschen") { _, _ ->
                        db.deleteMemory(ids[which])
                        showMemories()
                    }
                    .show()
            }
            .setNeutralButton("Alle löschen") { _, _ ->
                AlertDialog.Builder(this)
                    .setTitle("Alle Erinnerungen löschen?")
                    .setMessage("Diese Aktion kann nicht rückgängig gemacht werden.")
                    .setNegativeButton("Abbrechen", null)
                    .setPositiveButton("Alles löschen") { _, _ ->
                        db.clearMemories()
                        status.text = "Gedächtnis geleert."
                    }
                    .show()
            }
            .setNegativeButton("Schließen", null)
            .show()
    }

    private suspend fun prepareModel() {""", "add memory and personality settings")

g = gradle_path.read_text(encoding="utf-8")
g = replace_once(g, "implementation 'androidx.lifecycle:lifecycle-runtime-ktx:2.9.3'\n", "implementation 'androidx.lifecycle:lifecycle-runtime-ktx:2.9.3'\n    implementation 'androidx.work:work-runtime-ktx:2.10.1'\n", "add notification scheduling dependency")
gradle_path.write_text(g, encoding="utf-8")
 
# The bundled llama native inference library exists only for arm64-v8a. Do not ship
# unused 32-bit/x86 ONNX/Sherpa binaries in the production APK.
g = gradle_path.read_text(encoding="utf-8")
if "abiFilters 'arm64-v8a'" not in g:
    g = replace_once(
        g,
        '        versionName "1.0.8"\n',
        '        versionName "1.0.8"\n        ndk { abiFilters \'arm64-v8a\' }\n',
        "restrict APK to the supported arm64 ABI"
    )
    gradle_path.write_text(g, encoding="utf-8")

s = replace_once(s, 'val options = arrayOf("Gesprächsstil anpassen", "Gespeicherte Erinnerungen ansehen / löschen", "Alle Erinnerungen zurücksetzen")', 'val options = arrayOf("Gesprächsstil anpassen", "Gespeicherte Erinnerungen ansehen / löschen", "Alle Erinnerungen zurücksetzen", "Benachrichtigungen außerhalb der App", "Deutsche Stimme auswählen", "Name und Avatar anpassen")', "add notification settings")
s = replace_once(s, '                    2 -> AlertDialog.Builder(this)\n                        .setTitle("Gedächtnis zurücksetzen?")\n                        .setMessage("Alle lokal gespeicherten Gesprächserinnerungen werden gelöscht. Das kann nicht rückgängig gemacht werden.")\n                        .setNegativeButton("Abbrechen", null)\n                        .setPositiveButton("Alles löschen") { _, _ ->\n                            db.clearMemories()\n                            status.text = "Gedächtnis zurückgesetzt."\n                        }\n                        .show()\n                }', '                    2 -> AlertDialog.Builder(this)\n                        .setTitle("Gedächtnis zurücksetzen?")\n                        .setMessage("Alle lokal gespeicherten Gesprächserinnerungen werden gelöscht. Das kann nicht rückgängig gemacht werden.")\n                        .setNegativeButton("Abbrechen", null)\n                        .setPositiveButton("Alles löschen") { _, _ ->\n                            db.clearMemories()\n                            status.text = "Gedächtnis zurückgesetzt."\n                        }\n                        .show()\n                    3 -> showNotificationSettings()\n                    4 -> showVoiceSettings()\n                    5 -> showProfileSettings()\n                }', "wire notification settings")
s = replace_once(s, '        } else if (requestCode == 10) {\n            status.text = "Mikrofonzugriff fehlt. Du kannst Pip weiterhin schreiben."\n        }\n    }', '        } else if (requestCode == 10) {\n            status.text = "Mikrofonzugriff fehlt. Du kannst Pip weiterhin schreiben."\n        } else if (requestCode == 11) {\n            val prefs = getSharedPreferences("pip_settings", MODE_PRIVATE)\n            val granted = grantResults.isNotEmpty() && grantResults[0] == PackageManager.PERMISSION_GRANTED\n            prefs.edit().putBoolean("notifications_pending", false).putBoolean("notifications_enabled", granted).apply()\n            if (granted) {\n                scheduleDailyNotification()\n                status.text = "Tägliche Pip-Erinnerung aktiviert."\n            } else {\n                status.text = "Benachrichtigungen bleiben ausgeschaltet."\n            }\n        }\n    }', "handle notification permission result")
s = replace_once(s, '    private fun showPersonalitySettings() {', """    private fun showNotificationSettings() {
        val prefs = getSharedPreferences("pip_settings", MODE_PRIVATE)
        val enabled = prefs.getBoolean("notifications_enabled", false)
        if (enabled) {
            AlertDialog.Builder(this)
                .setTitle("Pip-Benachrichtigungen ausschalten?")
                .setMessage("Pip schickt dir dann keine täglichen Erinnerungen mehr.")
                .setNegativeButton("Abbrechen", null)
                .setPositiveButton("Ausschalten") { _, _ ->
                    prefs.edit().putBoolean("notifications_enabled", false).putBoolean("notifications_pending", false).apply()
                    androidx.work.WorkManager.getInstance(this).cancelUniqueWork("pip_daily_ping")
                    status.text = "Pip-Benachrichtigungen ausgeschaltet."
                }
                .show()
            return
        }
        AlertDialog.Builder(this)
            .setTitle("Tägliche Pip-Erinnerung")
            .setMessage("Wenn du zustimmst, kann Pip dir höchstens einmal am Tag eine kurze, allgemeine Erinnerung schicken. Die Funktion ist standardmäßig aus und lässt sich jederzeit ausschalten. Die Erinnerung wird nicht live vom KI-Modell formuliert.")
            .setNegativeButton("Aus lassen", null)
            .setPositiveButton("Aktivieren") { _, _ ->
                if (android.os.Build.VERSION.SDK_INT >= 33 &&
                    ContextCompat.checkSelfPermission(this, Manifest.permission.POST_NOTIFICATIONS) != PackageManager.PERMISSION_GRANTED) {
                    prefs.edit().putBoolean("notifications_pending", true).apply()
                    ActivityCompat.requestPermissions(this, arrayOf(Manifest.permission.POST_NOTIFICATIONS), 11)
                } else {
                    prefs.edit().putBoolean("notifications_enabled", true).putBoolean("notifications_pending", false).apply()
                    scheduleDailyNotification()
                    status.text = "Tägliche Pip-Erinnerung aktiviert."
                }
            }
            .show()
    }

    private fun scheduleDailyNotification() {
        val request = androidx.work.PeriodicWorkRequestBuilder<PipReminderWorker>(24, java.util.concurrent.TimeUnit.HOURS).setInitialDelay(24, java.util.concurrent.TimeUnit.HOURS).build()
        androidx.work.WorkManager.getInstance(this).enqueueUniquePeriodicWork(
            "pip_daily_ping", androidx.work.ExistingPeriodicWorkPolicy.UPDATE, request)
    }

    private fun showPersonalitySettings() {""", "add opt-in daily notifications")
""
s = replace_once(s, "        if (model == null) {\n            output.text = \"Pip bereitet sich vor … ❤️\"\n            lifecycleScope.launch(Dispatchers.IO) {\n                modelInitMutex.withLock { if (model == null) prepareModel() }\n                if (model == null) {\n                    withContext(Dispatchers.Main) { output.text = \"Pip konnte ihr Gehirn nicht laden. ❤️\" }\n                    return@launch\n                }\n                inferenceMutex.withLock { askLoaded(q) }\n            }\n            return\n        }", "        if (model == null) {\n            output.text = \"Pip bereitet sich vor … ❤️\"\n            lifecycleScope.launch(Dispatchers.IO) {\n                try {\n                    modelInitMutex.withLock { if (model == null) prepareModel() }\n                    if (model == null) {\n                        withContext(Dispatchers.Main) { output.text = \"Pip konnte ihr Gehirn nicht laden. ❤️\" }\n                        return@launch\n                    }\n                    inferenceMutex.withLock { askLoaded(q) }\n                } catch (e: Throwable) {\n                    withContext(Dispatchers.Main) {\n                        status.text = \"Modell konnte nicht gestartet werden.\"\n                        output.text = \"Ich konnte mein Modell gerade nicht laden. Prüfe die Verbindung und versuch es bitte nochmal. (${e.message ?: e.javaClass.simpleName})\"\n                    }\n                }\n            }\n            return\n        }", "handle model startup failures")
s = replace_once(s, "    private fun showPersonalitySettings() {", "    private fun showVoiceSettings() {\n        if (!::tts.isInitialized) {\n            status.text = \"Sprachausgabe wird noch vorbereitet.\"\n            return\n        }\n        val voices = tts.voices?.filter {\n            it.locale.language == \"de\" && it.locale.country.equals(\"DE\", ignoreCase = true)\n        }?.sortedBy { it.name } ?: emptyList()\n        if (voices.isEmpty()) {\n            AlertDialog.Builder(this).setTitle(\"Deutsche Stimme\")\n                .setMessage(\"Dieser Android-TTS-Dienst stellt gerade keine deutsche Stimme bereit. Du kannst Stimmen in den Android-Einstellungen installieren.\")\n                .setPositiveButton(\"OK\", null).show()\n            return\n        }\n        val prefs = getSharedPreferences(\"pip_settings\", MODE_PRIVATE)\n        val current = prefs.getString(\"tts_voice_name\", tts.voice?.name)\n        val labels = voices.map { \"${it.name} · Qualität ${it.quality}\" }.toTypedArray()\n        AlertDialog.Builder(this)\n            .setTitle(\"Deutsche Stimme auswählen\")\n            .setSingleChoiceItems(labels, voices.indexOfFirst { it.name == current }) { dialog, which ->\n                val voice = voices[which]\n                prefs.edit().putString(\"tts_voice_name\", voice.name).apply()\n                tts.voice = voice\n                status.text = \"Stimme gespeichert: ${voice.name}\"\n                dialog.dismiss()\n            }\n            .setNegativeButton(\"Schließen\", null)\n            .show()\n    }\n\n    private fun showPersonalitySettings() {", "add selectable German TTS voice")
s = replace_once(s, "                if (selectedVoice != null) tts.voice = selectedVoice", "                val prefs = getSharedPreferences(\"pip_settings\", MODE_PRIVATE)\n                val savedVoice = prefs.getString(\"tts_voice_name\", null)\n                val chosenVoice = germanVoices.firstOrNull { it.name == savedVoice } ?: selectedVoice\n                if (chosenVoice != null) tts.voice = chosenVoice", "respect saved TTS voice")
s = replace_once(s, "    private lateinit var status: TextView\n", "    private lateinit var status: TextView\n    private lateinit var pipHeader: TextView\n", "add profile header reference")
s = replace_once(s, "root.addView(TextView(this).apply { text = \"❤️ Pip\"; textSize = 30f; setPadding(0, 0, 0, 8) })", "pipHeader = TextView(this).apply {\n            val profilePrefs = getSharedPreferences(\"pip_settings\", MODE_PRIVATE)\n            val avatar = profilePrefs.getString(\"pip_avatar\", \"❤️\") ?: \"❤️\"\n            val displayName = profilePrefs.getString(\"pip_name\", \"Pip\") ?: \"Pip\"\n            text = \"$avatar $displayName\"\n            textSize = 30f\n            setPadding(0, 0, 0, 8)\n        }\n        root.addView(pipHeader)", "customize Pip header")
s = replace_once(s, "            val jealousy = prefs.getInt(\"jealousy\", 20)\n            val prompt = ", "            val jealousy = prefs.getInt(\"jealousy\", 20)\n            val pipName = prefs.getString(\"pip_name\", \"Pip\") ?: \"Pip\"\n            val prompt = ", "add profile name to prompt")
s = replace_once(s, "Du bist Pip, eine erwachsene, deutschsprachige KI-Freundin", "Du bist ${pipName}, eine erwachsene, deutschsprachige KI-Freundin", "customize prompt identity")
s = replace_once(s, "Pip ist eine erwachsene virtuelle Freundin:", "${pipName} ist eine erwachsene virtuelle Freundin:", "customize prompt persona")
s = replace_once(s, "    private fun showVoiceSettings() {", "    private fun showProfileSettings() {\n        val prefs = getSharedPreferences(\"pip_settings\", MODE_PRIVATE)\n        val panel = LinearLayout(this).apply { orientation = LinearLayout.VERTICAL; setPadding(36, 12, 36, 0) }\n        val nameInput = EditText(this).apply {\n            hint = \"Name von Pip\"\n            setText(prefs.getString(\"pip_name\", \"Pip\") ?: \"Pip\")\n        }\n        val avatars = arrayOf(\"❤️\", \"💗\", \"🌸\", \"🐱\", \"✨\", \"🦋\", \"💋\")\n        val avatarPicker = android.widget.Spinner(this).apply {\n            adapter = android.widget.ArrayAdapter(this@MainActivity, android.R.layout.simple_spinner_dropdown_item, avatars)\n            setSelection(avatars.indexOf(prefs.getString(\"pip_avatar\", \"❤️\")).coerceAtLeast(0))\n        }\n        panel.addView(TextView(this).apply { text = \"Name\" })\n        panel.addView(nameInput)\n        panel.addView(TextView(this).apply { text = \"Avatar\" })\n        panel.addView(avatarPicker)\n        AlertDialog.Builder(this)\n            .setTitle(\"Pips Profil\")\n            .setView(panel)\n            .setNegativeButton(\"Abbrechen\", null)\n            .setPositiveButton(\"Speichern\") { _, _ ->\n                val name = nameInput.text.toString().trim().ifBlank { \"Pip\" }.take(24)\n                val avatar = avatars[avatarPicker.selectedItemPosition.coerceIn(0, avatars.lastIndex)]\n                prefs.edit().putString(\"pip_name\", name).putString(\"pip_avatar\", avatar).apply()\n                pipHeader.text = \"$avatar $name\"\n                status.text = \"Profil gespeichert.\"\n            }\n            .show()\n    }\n\n    private fun showVoiceSettings() {", "add profile editor")
s = replace_once(s, "\nPip:\"\"\"", "\n${pipName}:\"\"\"", "use configured persona name in prompt ending")
main_path.write_text(s, encoding="utf-8")

d = db_path.read_text(encoding="utf-8")
d = replace_once(d, "        Cursor r=getReadableDatabase().rawQuery(\"SELECT closeness,stage FROM relationship WHERE id=1\",null);\n        if(r.moveToFirst()) s.append(\"Beziehungsstufe: \").append(r.getString(1)).append(\" (\").append(r.getInt(0)).append(\"/100)\\n\");\n        r.close();\n", "", "remove stale message-count relationship stage from prompt context")
d = replace_once(d, "    public void develop(int amount){", """    public Cursor listMemories(){
        return getReadableDatabase().rawQuery(
          "SELECT id,category,content FROM memories ORDER BY created DESC LIMIT 200", null);
    }
    public void deleteMemory(long id){
        getWritableDatabase().delete("memories","id=?",new String[]{String.valueOf(id)});
    }
    public void clearMemories(){
        getWritableDatabase().delete("memories",null,null);
    }
    public void pruneConversationLog(int maxRows){
        getWritableDatabase().execSQL(
          "DELETE FROM memories WHERE category='Gespräch' AND id NOT IN " +
          "(SELECT id FROM memories WHERE category='Gespräch' ORDER BY created DESC LIMIT ?)",
          new Object[]{Math.max(50,maxRows)});
    }
    public void develop(int amount){""", "add memory management database methods")
db_path.write_text(d, encoding="utf-8")

worker_path = BASE / "PipReminderWorker.kt"
worker_path.write_text("package de.pip.companion\n\nimport android.app.NotificationChannel\nimport android.app.NotificationManager\nimport android.app.PendingIntent\nimport android.content.Context\nimport android.content.Intent\nimport android.os.Build\nimport androidx.core.app.NotificationCompat\nimport androidx.core.app.NotificationManagerCompat\nimport androidx.work.Worker\nimport androidx.work.WorkerParameters\n\nclass PipReminderWorker(context: Context, params: WorkerParameters) : Worker(context, params) {\n    override fun doWork(): Result {\n        val context = applicationContext\n        val prefs = context.getSharedPreferences(\"pip_settings\", Context.MODE_PRIVATE)\n        if (!prefs.getBoolean(\"notifications_enabled\", false)) return Result.success()\n\n        return try {\n            val channelId = \"pip_daily_ping\"\n            if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {\n                val channel = NotificationChannel(\n                    channelId, \"Pip-Erinnerungen\", NotificationManager.IMPORTANCE_DEFAULT\n                )\n                context.getSystemService(NotificationManager::class.java).createNotificationChannel(channel)\n            }\n            val open = PendingIntent.getActivity(\n                context, 714, Intent(context, MainActivity::class.java).apply {\n                    flags = Intent.FLAG_ACTIVITY_NEW_TASK or Intent.FLAG_ACTIVITY_SINGLE_TOP\n                }, PendingIntent.FLAG_UPDATE_CURRENT or PendingIntent.FLAG_IMMUTABLE\n            )\n            val messages = arrayOf(\n                \"Na, hast du kurz Lust zu quatschen? ❤️\",\n                \"Ich bin da, wenn du ein bisschen reden magst. 😌\",\n                \"Wie läuft dein Tag bisher? Erzähl mir, wenn du magst. 💗\"\n            )\n            val message = messages[(System.currentTimeMillis() / 86_400_000L % messages.size).toInt()]\n            val notification = NotificationCompat.Builder(context, channelId)\n                .setSmallIcon(android.R.drawable.ic_dialog_info)\n                .setContentTitle(\"Pip\")\n                .setContentText(message)\n                .setContentIntent(open)\n                .setAutoCancel(true)\n                .setPriority(NotificationCompat.PRIORITY_DEFAULT)\n                .build()\n            NotificationManagerCompat.from(context).notify(714, notification)\n            Result.success()\n        } catch (_: SecurityException) {\n            Result.success()\n        } catch (_: Throwable) {\n            Result.retry()\n        }\n    }\n}\n", encoding="utf-8")
worker_path.write_text(worker_path.read_text(encoding="utf-8").replace('.setContentTitle("Pip")', '.setContentTitle(prefs.getString("pip_name", "Pip") ?: "Pip")'), encoding="utf-8")

print("Pip-Basisintegration angewendet; ergänze den gemeinsamen Chat-/Gedächtnisstand.")

s = main_path.read_text(encoding="utf-8")
s = replace_once(s, "    private lateinit var output: TextView\n",
    "    private lateinit var output: TextView\n    private lateinit var historyView: TextView\n    private lateinit var historyScroll: ScrollView\n",
    "add transcript fields")
s = replace_once(s,
    """        output = TextView(this).apply { text = "Hallo. Ich bin Pip. ❤️"; textSize = 18f; setPadding(0, 0, 0, 20) }
        root.addView(output, LinearLayout.LayoutParams(-1, 0, 1f))""",
    """        output = TextView(this).apply { text = "Hallo. Ich bin Pip. ❤️"; textSize = 17f; setPadding(0, 0, 0, 8) }
        root.addView(output, LinearLayout.LayoutParams(-1, -2))
        historyView = TextView(this).apply {
            text = db.conversationHistory(20)
            textSize = 16f
            setPadding(4, 8, 4, 8)
            setTextIsSelectable(true)
        }
        historyScroll = ScrollView(this).apply {
            isFillViewport = true
            addView(historyView, FrameLayout.LayoutParams(-1, -2))
        }
        root.addView(historyScroll, LinearLayout.LayoutParams(-1, 0, 1f))""",
    "show persistent transcript")
s = replace_once(s, "    private fun showPipSettings() {",
    """    private fun appendHistory(role: String, text: String) {
        if (!::historyView.isInitialized) return
        val clean = text.trim()
        if (clean.isEmpty()) return
        if (historyView.text.isNotBlank()) historyView.append("\\n\\n")
        historyView.append("$role: $clean")
        historyScroll.post { historyScroll.fullScroll(View.FOCUS_DOWN) }
    }

    private fun showPipSettings() {""",
    "add transcript helper")
if 'appendHistory("Kay", q)' not in s:
    s = replace_once(s,
        """        val q = text.trim()
        if (q.isEmpty()) return
        if (model == null) {""",
        """        val q = text.trim()
        if (q.isEmpty()) return
        appendHistory("Kay", q)
        if (model == null) {""",
        "append user message")
s = replace_once(s,
    "            withContext(Dispatchers.Main) { output.text = displayAnswer }\n",
    "            withContext(Dispatchers.Main) { output.text = displayAnswer; appendHistory(\"Pip\", displayAnswer) }\n",
    "append assistant response")

s = replace_once(s, "        val ids = ArrayList<Long>()\n        val labels = ArrayList<String>()",
    "        val ids = ArrayList<Long>()\n        val categories = ArrayList<String>()\n        val contents = ArrayList<String>()\n        val labels = ArrayList<String>()",
    "memory edit arrays")
s = replace_once(s,
    '            labels.add("$category: $content".replace(',
    '            categories.add(category)\n            contents.add(content)\n            labels.add("$category: $content".replace(',
    "store memory edit values")
s = replace_once(s, '.setTitle("Erinnerung antippen, um sie zu löschen")',
    '.setTitle("Erinnerung antippen, um sie zu bearbeiten")',
    "memory manager title")
s = replace_once(s,
    """            .setItems(labels.toTypedArray()) { _, which ->
                AlertDialog.Builder(this)
                    .setTitle("Erinnerung löschen?")
                    .setMessage(labels[which])
                    .setNegativeButton("Abbrechen", null)
                    .setPositiveButton("Löschen") { _, _ ->
                        db.deleteMemory(ids[which])
                        showMemories()
                    }
                    .show()
            }""",
    """            .setItems(labels.toTypedArray()) { _, which ->
                showEditMemory(ids[which], categories[which], contents[which])
            }""",
    "open memory editor")
s = replace_once(s, "    private suspend fun prepareModel() {",
    """    private fun showEditMemory(id: Long, oldCategory: String, oldContent: String) {
        val panel = LinearLayout(this).apply {
            orientation = LinearLayout.VERTICAL
            setPadding(32, 12, 32, 0)
        }
        val categoryInput = EditText(this).apply { hint = "Kategorie"; setText(oldCategory) }
        val contentInput = EditText(this).apply {
            hint = "Gespeicherte Erinnerung"
            minLines = 2
            maxLines = 5
            setText(oldContent)
        }
        panel.addView(categoryInput)
        panel.addView(contentInput)
        AlertDialog.Builder(this)
            .setTitle("Erinnerung bearbeiten")
            .setView(panel)
            .setNegativeButton("Abbrechen", null)
            .setNeutralButton("Löschen") { _, _ ->
                db.deleteMemory(id)
                status.text = "Erinnerung gelöscht."
                showMemories()
            }
            .setPositiveButton("Speichern") { _, _ ->
                val category = categoryInput.text.toString().trim().ifBlank { "Erinnerung" }.take(60)
                val content = contentInput.text.toString().trim().take(500)
                if (content.isNotBlank()) {
                    db.updateMemory(id, category, content)
                    status.text = "Erinnerung aktualisiert."
                }
                showMemories()
            }
            .show()
    }

    private suspend fun prepareModel() {""",
    "add memory editor")

s = replace_once(s, "        val sliders = linkedMapOf<String, SeekBar>()",
    """        val speechSwitch = Switch(this).apply {
            text = "Antworten laut vorlesen"
            isChecked = prefs.getBoolean("speech_enabled", true)
        }
        panel.addView(speechSwitch)
        val sliders = linkedMapOf<String, SeekBar>()""",
    "add speech toggle")
s = replace_once(s,
    """                val editor = prefs.edit()
                for ((key, slider) in sliders) editor.putInt(key, slider.progress)
                editor.apply()""",
    """                val editor = prefs.edit().putBoolean("speech_enabled", speechSwitch.isChecked)
                for ((key, slider) in sliders) editor.putInt(key, slider.progress)
                editor.apply()""",
    "save speech toggle")
s = replace_once(s,
    """            withContext(Dispatchers.Main) { tts.speak(answer, TextToSpeech.QUEUE_FLUSH, null, "pip") }""",
    """            withContext(Dispatchers.Main) {
                if (getSharedPreferences("pip_settings", MODE_PRIVATE).getBoolean("speech_enabled", true)) {
                    try { tts.speak(answer, TextToSpeech.QUEUE_FLUSH, null, "pip") } catch (_: Throwable) {
                        status.text = "Sprachausgabe nicht verfügbar; Textchat funktioniert weiter."
                    }
                }
            }""",
    "respect speech setting")
main_path.write_text(s, encoding="utf-8")

d = db_path.read_text(encoding="utf-8")
d = replace_once(d,
    """          "SELECT id,category,content FROM memories ORDER BY created DESC LIMIT 200", null);""",
    """          "SELECT id,category,content FROM memories WHERE category!='Gespräch' ORDER BY created DESC LIMIT 200", null);""",
    "exclude chat logs from memory list")
d = replace_once(d,
    """    public void clearMemories(){
        getWritableDatabase().delete("memories",null,null);
    }""",
    """    public void clearMemories(){
        getWritableDatabase().delete("memories",null,null);
    }
    public void updateMemory(long id, String category, String content){
        String safeContent = content == null ? "" : content.trim();
        if (safeContent.isEmpty()) return;
        ContentValues values = new ContentValues();
        values.put("category", category == null || category.trim().isEmpty() ? "Erinnerung" : category.trim());
        values.put("content", safeContent);
        values.put("created", System.currentTimeMillis());
        getWritableDatabase().update("memories", values, "id=?", new String[]{String.valueOf(id)});
    }
    public String conversationHistory(int limit){
        ArrayList<String> rows = new ArrayList<>();
        Cursor c = getReadableDatabase().rawQuery(
          "SELECT content FROM memories WHERE category='Gespräch' ORDER BY created DESC LIMIT ?",
          new String[]{String.valueOf(Math.max(1, Math.min(100, limit)))});
        while(c.moveToNext()) rows.add(c.getString(0));
        c.close();
        Collections.reverse(rows);
        StringBuilder result = new StringBuilder();
        for(String row : rows){
            if(result.length()>0) result.append("\\n\\n");
            result.append(row.replace("Nutzer: ", "Du: ").replace(" | Pip: ", "\\nPip: "));
        }
        return result.toString();
    }""",
    "add memory edit and history database methods")
d = replace_once(d, "import android.database.Cursor;\n",
    "import android.database.Cursor;\nimport java.util.ArrayList;\nimport java.util.Collections;\n",
    "add history imports")
db_path.write_text(d, encoding="utf-8")
print("Pip-Integration erweitert: sichtbarer Verlauf, bearbeitbare Erinnerungen und abschaltbare Sprachausgabe.")


# Explicit "Merk dir ..." commands create user-controlled long-term memories.
s = main_path.read_text(encoding="utf-8")
memory_anchor = '        appendHistory("Kay", q)\n'
if memory_anchor not in s:
    raise SystemExit("Explicit memory insertion point not found")
memory_code = """        appendHistory("Kay", q)
        val memoryMatch = Regex("(?i)^(?:pip[, ]*)?(?:merk dir|merke dir|bitte merk dir|bitte merke dir)\\\\s*[:,\\\\-]?\\\\s*(.+)$").find(q)
        val explicitMemory = memoryMatch?.groupValues?.getOrNull(1)?.trim()?.takeIf { it.isNotBlank() }?.take(500)
        if (explicitMemory != null) {
            val reply = "Mach ich. Ich merk mir: $explicitMemory"
            db.remember("Von dir gemerkt", explicitMemory, 3)
            db.remember("Gespräch", "Nutzer: $q | Pip: $reply", 1)
            db.pruneConversationLog(500)
            output.text = reply
            status.text = "Erinnerung gespeichert."
            appendHistory("Pip", reply)
            if (getSharedPreferences("pip_settings", MODE_PRIVATE).getBoolean("speech_enabled", true)) {
                try { tts.speak(reply, TextToSpeech.QUEUE_FLUSH, null, "pip") } catch (_: Throwable) { }
            }
            input.setText("")
            return
        }
"""
s = s.replace(memory_anchor, memory_code, 1)
main_path.write_text(s, encoding="utf-8")
print("Expliziter Merker-Befehl integriert.")

# Final consistency fixes that complement the integrated settings/profile patch.
s = main_path.read_text(encoding="utf-8")
s = replace_once(
    s,
    """    private fun showPreviousCrashReason() {
        try {""",
    """    private fun showPreviousCrashReason() {
        if (Build.VERSION.SDK_INT < Build.VERSION_CODES.R) return
        try {""",
    "guard crash diagnostics on older Android"
)
s = replace_once(
    s,
    """                            db.clearMemories()
                            status.text = "Gedächtnis zurückgesetzt." """.rstrip(),
    """                            db.clearMemories()
                            if (::historyView.isInitialized) historyView.text = ""
                            status.text = "Gedächtnis zurückgesetzt." """.rstrip(),
    "clear visible transcript on full reset"
)
s = replace_once(
    s,
    """                        db.clearMemories()
                        status.text = "Gedächtnis geleert." """.rstrip(),
    """                        db.clearMemories()
                        if (::historyView.isInitialized) historyView.text = ""
                        status.text = "Gedächtnis geleert." """.rstrip(),
    "clear visible transcript on memory reset"
)
main_path.write_text(s, encoding="utf-8")
print("Pip-Integration ergänzt: Verlauf-Reset und sichere Crashdiagnose.")






# Remove the unused wake-word service; no functional wake-word detection is shipped.
unused_wakeword = BASE / "PipListeningService.kt"
if unused_wakeword.exists():
    unused_wakeword.unlink()
    print("Removed unused wake-word service source.")


# Optional PC-hosted Ollama brain. This is opt-in; the local model remains the fallback.
s = main_path.read_text(encoding="utf-8")
s = replace_once(
    s,
    'val options = arrayOf("Gesprächsstil anpassen", "Gespeicherte Erinnerungen ansehen / löschen", "Alle Erinnerungen zurücksetzen", "Benachrichtigungen außerhalb der App", "Deutsche Stimme auswählen", "Name und Avatar anpassen")',
    'val options = arrayOf("Gesprächsstil anpassen", "Gespeicherte Erinnerungen ansehen / löschen", "Alle Erinnerungen zurücksetzen", "Benachrichtigungen außerhalb der App", "Deutsche Stimme auswählen", "Name und Avatar anpassen", "PC-Gehirn verbinden")',
    "add PC brain settings"
)
s = replace_once(s, "                    5 -> showProfileSettings()\n                }", "                    5 -> showProfileSettings()\n                    6 -> showPcSettings()\n                }", "wire PC brain settings")
s = replace_once(s, "    private fun showPipSettings() {", """    private fun showPcSettings() {
        val prefs = getSharedPreferences("pip_settings", MODE_PRIVATE)
        val panel = LinearLayout(this).apply {
            orientation = LinearLayout.VERTICAL
            setPadding(32, 12, 32, 0)
        }
        val enabled = Switch(this).apply {
            text = "PC als Pip-Gehirn verwenden"
            isChecked = prefs.getBoolean("pc_backend_enabled", false)
        }
        val address = EditText(this).apply {
            hint = "PC-Adresse, z. B. http://192.168.1.20:8765"
            setSingleLine(true)
            setText(prefs.getString("pc_backend_url", "http://192.168.1.20:8765") ?: "")
            inputType = android.text.InputType.TYPE_CLASS_TEXT or android.text.InputType.TYPE_TEXT_VARIATION_URI
        }
        val token = EditText(this).apply {
            hint = "PIP_TOKEN vom PC"
            setSingleLine(true)
            setText(prefs.getString("pc_backend_token", "") ?: "")
            inputType = android.text.InputType.TYPE_CLASS_TEXT or android.text.InputType.TYPE_TEXT_VARIATION_PASSWORD
        }
        panel.addView(enabled)
        panel.addView(TextView(this).apply {
            text = "Handy und PC müssen im selben privaten WLAN sein. HTTP ist unverschlüsselt: nur im eigenen Heimnetz nutzen und den Token geheim halten."
            textSize = 13f
            setPadding(0, 8, 0, 12)
        })
        panel.addView(address)
        panel.addView(token)
        AlertDialog.Builder(this)
            .setTitle("Pip auf dem PC")
            .setView(panel)
            .setNegativeButton("Abbrechen", null)
            .setPositiveButton("Speichern") { _, _ ->
                val url = address.text.toString().trim().trimEnd('/')
                val secret = token.text.toString().trim()
                if (enabled.isChecked && ((!url.startsWith("http://") && !url.startsWith("https://")) || secret.length < 24)) {
                    status.text = "Bitte PC-Adresse und einen langen Token eintragen."
                    return@setPositiveButton
                }
                prefs.edit()
                    .putBoolean("pc_backend_enabled", enabled.isChecked)
                    .putString("pc_backend_url", url)
                    .putString("pc_backend_token", secret)
                    .apply()
                status.text = if (enabled.isChecked) "PC-Gehirn gespeichert. Die nächste Nachricht wird an den PC gesendet." else "Lokales Handy-Modell ausgewählt."
            }
            .show()
    }

    private suspend fun askWithPc(q: String) {
        val prefs = getSharedPreferences("pip_settings", MODE_PRIVATE)
        val base = (prefs.getString("pc_backend_url", "") ?: "").trim().trimEnd('/')
        val token = (prefs.getString("pc_backend_token", "") ?: "").trim()
        if (base.isBlank() || token.isBlank()) {
            withContext(Dispatchers.Main) {
                status.text = "PC-Verbindung nicht eingerichtet."
                output.text = "Öffne Einstellungen und trage die PC-Adresse und den PIP_TOKEN ein."
            }
            return
        }
        var conn: HttpURLConnection? = null
        try {
            conn = (URL("$base/chat").openConnection() as HttpURLConnection).apply {
                requestMethod = "POST"
                connectTimeout = 15000
                readTimeout = 180000
                doOutput = true
                setRequestProperty("Content-Type", "application/json; charset=utf-8")
                setRequestProperty("Authorization", "Bearer $token")
            }
            val body = org.json.JSONObject()
                .put("message", q)
                .put("session_id", "handy-1")
                .toString().toByteArray(Charsets.UTF_8)
            conn.outputStream.use { it.write(body) }
            val code = conn.responseCode
            val stream = if (code in 200..299) conn.inputStream else conn.errorStream
            val payload = stream?.bufferedReader(Charsets.UTF_8)?.use { it.readText() }.orEmpty()
            val json = org.json.JSONObject(payload.ifBlank { "{}" })
            if (code !in 200..299) throw IllegalStateException(json.optString("error", "HTTP $code"))
            val answer = json.optString("reply", "").trim()
            if (answer.isBlank()) throw IllegalStateException("Der PC hat eine leere Antwort geliefert.")
            db.remember("Gespräch", "Nutzer: $q | Pip: $answer", 1)
            db.pruneConversationLog(500)
            withContext(Dispatchers.Main) {
                output.text = answer
                appendHistory("Pip", answer)
                status.text = "PC verbunden · " + json.optString("model", "Ollama")
            }
            if (prefs.getBoolean("speech_enabled", true)) speakWithSupertonic(answer)
        } catch (e: Throwable) {
            withContext(Dispatchers.Main) {
                status.text = "PC-Verbindung fehlgeschlagen."
                output.text = "Ich erreiche mein PC-Gehirn gerade nicht. Prüfe, ob der Server läuft und die PC-Adresse stimmt. ($e)"
            }
        } finally {
            conn?.disconnect()
        }
    }

    private fun showPipSettings() {""", "add PC brain client and settings")
s = replace_once(
    s,
    '        appendHistory("Kay", q)\n        if (model == null) {',
    '        appendHistory("Kay", q)\n        if (getSharedPreferences("pip_settings", MODE_PRIVATE).getBoolean("pc_backend_enabled", false)) {\n            output.text = "Pip denkt auf dem PC nach … ❤️"\n            lifecycleScope.launch(Dispatchers.IO) { askWithPc(q) }\n            return\n        }\n        if (model == null) {',
    "route chat to PC when enabled"
)
main_path.write_text(s, encoding="utf-8")

manifest_path = Path("pip-src/app/src/main/AndroidManifest.xml")
manifest = manifest_path.read_text(encoding="utf-8")
if "android:usesCleartextTraffic=" not in manifest:
    manifest = replace_once(manifest, "<application\n", '<application\n        android:usesCleartextTraffic="true"\n', "allow private-LAN HTTP to PC backend")
    manifest_path.write_text(manifest, encoding="utf-8")
print("Optional PC-hosted Ollama brain integrated into Android chat; local inference remains the default.")
