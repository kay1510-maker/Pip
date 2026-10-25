from pathlib import Path
import re

BASE = Path("pip-src/app/src/main/java/de/pip/companion")
main_path = BASE / "MainActivity.kt"
db_path = BASE / "PipMemoryDb.java"

def replace_once(text, old, new, label):
    count = text.count(old)
    if count != 1:
        raise SystemExit(label + ": expected one match, found " + str(count))
    return text.replace(old, new, 1)

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

# Finish the same integrated settings flow: configurable display name, reliable model-load
# errors, and no stale history shown after a full local reset.
s = main_path.read_text(encoding="utf-8")
s = replace_once(
    s,
    "    private lateinit var historyScroll: ScrollView\n",
    "    private lateinit var historyScroll: ScrollView\n    private lateinit var titleView: TextView\n",
    "add editable Pip display name"
)
s = replace_once(
    s,
    """        root.addView(TextView(this).apply { text = "❤️ Pip"; textSize = 30f; setPadding(0, 0, 0, 8) })""",
    """        titleView = TextView(this).apply {
            text = "❤️ " + (getSharedPreferences("pip_settings", MODE_PRIVATE).getString("pip_name", "Pip") ?: "Pip")
            textSize = 30f
            setPadding(0, 0, 0, 8)
        }
        root.addView(titleView)""",
    "use configurable title"
)
s = replace_once(
    s,
    """        val speechSwitch = Switch(this).apply {
            text = "Antworten laut vorlesen"
            isChecked = prefs.getBoolean("speech_enabled", true)
        }""",
    """        val nameInput = EditText(this).apply {
            hint = "Name der Begleiterin"
            setText(prefs.getString("pip_name", "Pip") ?: "Pip")
        }
        panel.addView(TextView(this).apply { text = "Name der Begleiterin" })
        panel.addView(nameInput)
        val speechSwitch = Switch(this).apply {
            text = "Antworten laut vorlesen"
            isChecked = prefs.getBoolean("speech_enabled", true)
        }""",
    "add name field to settings"
)
s = replace_once(
    s,
    """                val editor = prefs.edit().putBoolean("speech_enabled", speechSwitch.isChecked)""",
    """                val editor = prefs.edit()
                    .putString("pip_name", nameInput.text.toString().trim().ifBlank { "Pip" }.take(30))
                    .putBoolean("speech_enabled", speechSwitch.isChecked)""",
    "save custom name"
)
s = replace_once(
    s,
    """                editor.apply()
                status.text = "Pips Gesprächsstil gespeichert." """.rstrip(),
    """                editor.apply()
                titleView.text = "❤️ " + (prefs.getString("pip_name", "Pip") ?: "Pip")
                status.text = "Pips Gesprächsstil gespeichert." """.rstrip(),
    "refresh custom title"
)
s = replace_once(
    s,
    """            val jealousy = prefs.getInt("jealousy", 20)
            val prompt = """,
    """            val jealousy = prefs.getInt("jealousy", 20)
            val pipName = prefs.getString("pip_name", "Pip") ?: "Pip"
            val prompt = """,
    "read configurable persona name"
)
s = replace_once(s, "Du bist Pip, eine erwachsene, deutschsprachige KI-Freundin", "Du bist $pipName, eine erwachsene, deutschsprachige KI-Freundin", "use configured persona name")
s = replace_once(s, "\nPip:\"\"\"", "\n$pipName:\"\"\"", "use configured persona name in prompt ending")

s = replace_once(
    s,
    """            lifecycleScope.launch(Dispatchers.IO) {
                modelInitMutex.withLock { if (model == null) prepareModel() }
                if (model == null) {""",
    """            lifecycleScope.launch(Dispatchers.IO) {
                try {
                    modelInitMutex.withLock { if (model == null) prepareModel() }
                } catch (e: Throwable) {
                    val message = "Pip konnte die lokale KI nicht laden: " + (e.message ?: e.javaClass.simpleName)
                    withContext(Dispatchers.Main) {
                        status.text = "Modell konnte nicht geladen werden."
                        output.text = message
                        appendHistory("Pip", message)
                    }
                    return@launch
                }
                if (model == null) {""",
    "catch model download and initialization failures"
)
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
s = replace_once(
    s,
    "Pip hat noch keine gespeicherten Gesprächserinnerungen.",
    "Noch keine eigenen Erinnerungen. Schreibe im Chat „Merk dir …“, damit Pip einen Fakt speichert.",
    "explain explicit memory command"
)
main_path.write_text(s, encoding="utf-8")

d = db_path.read_text(encoding="utf-8")
old_relation = """        Cursor r=getReadableDatabase().rawQuery("SELECT closeness,stage FROM relationship WHERE id=1",null);
        if(r.moveToFirst()) s.append("Beziehungsstufe: ").append(r.getString(1)).append(" (").append(r.getInt(0)).append("/100)\\n");
        r.close();
"""
if old_relation in d:
    d = d.replace(old_relation, "", 1)
db_path.write_text(d, encoding="utf-8")
print("Pip-Integration ergänzt: Name einstellbar, Modellfehler abgefangen, Reset-Anzeige konsistent.")

