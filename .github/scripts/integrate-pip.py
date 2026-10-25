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

print("Pip integration patches applied: larger context/replies, editable personality controls, memory list/delete/reset, bounded transcript storage.")
