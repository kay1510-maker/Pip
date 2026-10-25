from pathlib import Path

BASE = Path("pip-src/app/src/main/java/de/pip/companion")
main_path = BASE / "MainActivity.kt"
db_path = BASE / "PipMemoryDb.java"

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
            AlertDialog.Builder(this).setTitle("Gedächtnis").setMessage("Pip hat noch keine gespeicherten Gesprächserinnerungen.")
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

s = replace_once(s, "implementation 'androidx.lifecycle:lifecycle-runtime-ktx:2.9.3'\n", "implementation 'androidx.lifecycle:lifecycle-runtime-ktx:2.9.3'\n    implementation 'androidx.work:work-runtime-ktx:2.10.1'\n", "add notification scheduling dependency")
s = replace_once(s, 'val options = arrayOf("Gesprächsstil anpassen", "Gespeicherte Erinnerungen ansehen / löschen", "Alle Erinnerungen zurücksetzen")', 'val options = arrayOf("Gesprächsstil anpassen", "Gespeicherte Erinnerungen ansehen / löschen", "Alle Erinnerungen zurücksetzen", "Benachrichtigungen außerhalb der App")', "add notification settings")
s = replace_once(s, '                    2 -> AlertDialog.Builder(this)\n                        .setTitle("Gedächtnis zurücksetzen?")\n                        .setMessage("Alle lokal gespeicherten Gesprächserinnerungen werden gelöscht. Das kann nicht rückgängig gemacht werden.")\n                        .setNegativeButton("Abbrechen", null)\n                        .setPositiveButton("Alles löschen") { _, _ ->\n                            db.clearMemories()\n                            status.text = "Gedächtnis zurückgesetzt."\n                        }\n                        .show()\n                }', '                    2 -> AlertDialog.Builder(this)\n                        .setTitle("Gedächtnis zurücksetzen?")\n                        .setMessage("Alle lokal gespeicherten Gesprächserinnerungen werden gelöscht. Das kann nicht rückgängig gemacht werden.")\n                        .setNegativeButton("Abbrechen", null)\n                        .setPositiveButton("Alles löschen") { _, _ ->\n                            db.clearMemories()\n                            status.text = "Gedächtnis zurückgesetzt."\n                        }\n                        .show()\n                    3 -> showNotificationSettings()\n                }', "wire notification settings")
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
        val request = androidx.work.PeriodicWorkRequestBuilder<PipReminderWorker>(24, java.util.concurrent.TimeUnit.HOURS).build()
        androidx.work.WorkManager.getInstance(this).enqueueUniquePeriodicWork(
            "pip_daily_ping", androidx.work.ExistingPeriodicWorkPolicy.UPDATE, request)
    }

    private fun showPersonalitySettings() {""", "add opt-in daily notifications")
""
main_path.write_text(s, encoding="utf-8")

d = db_path.read_text(encoding="utf-8")
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

print("Pip integration patches applied: larger context/replies, editable personality controls, memory management, bounded history, opt-in daily notifications.")
