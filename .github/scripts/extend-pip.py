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
            addView(historyView, ScrollView.LayoutParams(-1, -2))
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
s = replace_once(
    s,
    """        appendHistory("Kay", q)
        if (model == null) {""",
    """        appendHistory("Kay", q)
        val memoryMatch = Regex("""(?i)^(?:pip[, ]*)?(?:merk dir|merke dir|bitte merk dir|bitte merke dir)\s*[:,\-]?\s*(.+)$""").find(q)
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
        if (model == null) {""",
    "add explicit long-term memory command"
)
main_path.write_text(s, encoding="utf-8")
print("Expliziter Merker-Befehl integriert.")

