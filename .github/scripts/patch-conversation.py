from pathlib import Path

p = Path("pip-src/app/src/main/java/de/pip/companion/MainActivity.kt")
s = p.read_text(encoding="utf-8")

def replace_once(old, new, label):
    global s
    if old not in s:
        raise SystemExit(f"Patch fehlgeschlagen: {label}")
    s = s.replace(old, new, 1)

# Remove the manual microphone button: voice starts through "Hey Pip".
replace_once(
    '        row.addView(Button(this).apply { text = "🎤 Sprechen"; setOnClickListener { startListening() } }, LinearLayout.LayoutParams(0, -2, 1f))\n',
    "",
    "Manuellen Mikrofonknopf entfernen",
)

# Session state.
replace_once(
    "    private var recognizer: SpeechRecognizer? = null\n",
    "    private var recognizer: SpeechRecognizer? = null\n    private var conversationMode = false\n",
    "Recognizer-Feld",
)

# Auto-start listening if microphone permission already exists.
replace_once(
    """        if (ContextCompat.checkSelfPermission(this, Manifest.permission.RECORD_AUDIO)
            != PackageManager.PERMISSION_GRANTED) {
            ActivityCompat.requestPermissions(this, arrayOf(Manifest.permission.RECORD_AUDIO), 10)
        }
""",
    """        if (ContextCompat.checkSelfPermission(this, Manifest.permission.RECORD_AUDIO)
            != PackageManager.PERMISSION_GRANTED) {
            ActivityCompat.requestPermissions(this, arrayOf(Manifest.permission.RECORD_AUDIO), 10)
        } else {
            Handler(Looper.getMainLooper()).postDelayed({ startListening() }, 700)
        }
""",
    "Mikrofonberechtigung",
)

replace_once(
    "    private fun buildUi() {",
    """    override fun onRequestPermissionsResult(requestCode: Int, permissions: Array<String>, grantResults: IntArray) {
        super.onRequestPermissionsResult(requestCode, permissions, grantResults)
        if (requestCode == 10 && grantResults.isNotEmpty() && grantResults[0] == PackageManager.PERMISSION_GRANTED) {
            Handler(Looper.getMainLooper()).postDelayed({ startListening() }, 700)
        } else if (requestCode == 10) {
            status.text = "Mikrofonzugriff fehlt. Du kannst Pip weiterhin schreiben."
        }
    }

    private fun buildUi() {""",
    "Permission-Callback",
)

replace_once(
    "    private fun startListening() {",
    """    private fun scheduleListenAgain() {
        Handler(Looper.getMainLooper()).postDelayed({
            if (!isFinishing && !isDestroyed &&
                ContextCompat.checkSelfPermission(this, Manifest.permission.RECORD_AUDIO) == PackageManager.PERMISSION_GRANTED) {
                startListening()
            }
        }, 900)
    }

    private fun startListening() {""",
    "Listen-Wiederholung",
)

replace_once(
    '            override fun onResults(b: Bundle?) { b?.getStringArrayList(SpeechRecognizer.RESULTS_RECOGNITION)?.firstOrNull()?.let { input.setText(it); ask(it) } }',
    """            override fun onResults(b: Bundle?) {
                val heard = b?.getStringArrayList(SpeechRecognizer.RESULTS_RECOGNITION)?.firstOrNull()?.trim().orEmpty()
                if (heard.isBlank()) { scheduleListenAgain(); return }
                val normalized = heard.lowercase(Locale.GERMAN).replace(",", "").replace(".", "")
                if (normalized.contains("pip ende") || normalized.contains("gespräch beenden") || normalized.contains("gespraech beenden")) {
                    conversationMode = false
                    output.text = "Alles klar, ich bin wieder im Bereitschaftsmodus. Sag Hey Pip, wenn du mich brauchst. ❤️"
                    status.text = "💤 Sag Hey Pip zum Starten"
                    scheduleListenAgain()
                    return
                }
                if (!conversationMode) {
                    if (normalized.contains("hey pip") || normalized.contains("hei pip")) {
                        conversationMode = true
                        status.text = "💗 Gespräch aktiv – du kannst einfach weiterreden"
                        val remainder = heard.replace(Regex("(?i)hey[, ]+pip|hei[, ]+pip"), "").trim()
                        if (remainder.isNotBlank()) { input.setText(remainder); ask(remainder) } else scheduleListenAgain()
                    } else {
                        scheduleListenAgain()
                    }
                } else {
                    input.setText(heard)
                    ask(heard)
                }
            }""",
    "Wakeword- und Gesprächslogik",
)

replace_once(
    '            override fun onError(e: Int) { output.text = "Ich konnte dich nicht verstehen. Versuch es nochmal. ❤️" }',
    """            override fun onError(e: Int) {
                if (conversationMode) output.text = "Ich höre dir weiter zu … ❤️"
                scheduleListenAgain()
            }""",
    "Erkennungsfehler",
)

replace_once(
    "    override fun onInit(statusCode: Int) { if (statusCode == TextToSpeech.SUCCESS) tts.language = Locale.GERMAN }",
    """    override fun onInit(statusCode: Int) {
        if (statusCode == TextToSpeech.SUCCESS) {
            tts.language = Locale.GERMAN
            tts.setOnUtteranceProgressListener(object : android.speech.tts.UtteranceProgressListener() {
                override fun onStart(utteranceId: String?) {}
                override fun onDone(utteranceId: String?) { scheduleListenAgain() }
                @Deprecated("Deprecated in Java")
                override fun onError(utteranceId: String?) { scheduleListenAgain() }
            })
        }
    }""",
    "TTS-Rückkehr",
)

replace_once(
    "            playPcm(audio.samples, audio.sampleRate)",
    """            playPcm(audio.samples, audio.sampleRate)
            kotlinx.coroutines.delay((audio.samples.size * 1000L / audio.sampleRate) + 500L)
            scheduleListenAgain()""",
    "Supertonic-Rückkehr",
)

p.write_text(s, encoding="utf-8")
print("Wakeword-Gate und fortlaufender Gesprächsmodus wurden in MainActivity integriert.")
