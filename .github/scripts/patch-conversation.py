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

# Add an explicit microphone foreground service for locked-screen listening.
manifest = Path("pip-src/app/src/main/AndroidManifest.xml")
ms = manifest.read_text(encoding="utf-8")
for perm in (
    '    <uses-permission android:name="android.permission.FOREGROUND_SERVICE" />',
    '    <uses-permission android:name="android.permission.FOREGROUND_SERVICE_MICROPHONE" />',
    '    <uses-permission android:name="android.permission.POST_NOTIFICATIONS" />',
):
    if perm not in ms:
        ms = ms.replace('    <uses-permission android:name="android.permission.RECORD_AUDIO" />', '    <uses-permission android:name="android.permission.RECORD_AUDIO" />' + chr(10) + perm, 1)
service_decl = '''        <service
            android:name=".PipListeningService"
            android:exported="false"
            android:foregroundServiceType="microphone" />
'''
if 'android:name=".PipListeningService"' not in ms:
    ms = ms.replace('        <activity android:name=".MainActivity"', service_decl + '        <activity android:name=".MainActivity"', 1)
manifest.write_text(ms, encoding="utf-8")
service = Path("pip-src/app/src/main/java/de/pip/companion/PipListeningService.kt")
service.write_text(r'''package de.pip.companion

import android.app.Notification
import android.app.NotificationChannel
import android.app.NotificationManager
import android.app.PendingIntent
import android.app.Service
import android.content.Intent
import android.content.pm.PackageManager
import android.os.Build
import android.os.Bundle
import android.os.IBinder
import android.speech.RecognitionListener
import android.speech.RecognizerIntent
import android.speech.SpeechRecognizer
import androidx.core.app.NotificationCompat

class PipListeningService : Service() {
    private var recognizer: SpeechRecognizer? = null
    private var launching = false
    private var stopped = false
    private val channelId = "pip_voice_listening"

    override fun onCreate() {
        super.onCreate()
        createChannel()
        val open = PendingIntent.getActivity(this, 0, Intent(this, MainActivity::class.java).apply {
            flags = Intent.FLAG_ACTIVITY_NEW_TASK or Intent.FLAG_ACTIVITY_SINGLE_TOP
            putExtra("pip_wakeword", true)
        }, PendingIntent.FLAG_UPDATE_CURRENT or PendingIntent.FLAG_IMMUTABLE)
        val notification: Notification = NotificationCompat.Builder(this, channelId)
            .setSmallIcon(android.R.drawable.ic_btn_speak_now)
            .setContentTitle("Pip hört auf Hey Pip")
            .setContentText("Mikrofon aktiv – tippe hier, um Pip zu öffnen")
            .setContentIntent(open)
            .setOngoing(true)
            .setCategory(NotificationCompat.CATEGORY_SERVICE)
            .build()
        startForeground(713, notification)
    }

    override fun onStartCommand(intent: Intent?, flags: Int, startId: Int): Int {
        if (checkSelfPermission(android.Manifest.permission.RECORD_AUDIO) != PackageManager.PERMISSION_GRANTED) {
            stopSelf(); return START_NOT_STICKY
        }
        listen()
        return START_STICKY
    }

    private fun listen() {
        if (launching || stopped) return
        if (!SpeechRecognizer.isRecognitionAvailable(this)) { stopSelf(); return }
        try {
            recognizer?.destroy()
            recognizer = SpeechRecognizer.createOnDeviceSpeechRecognizer(this).apply {
                setRecognitionListener(object : RecognitionListener {
                    override fun onReadyForSpeech(params: Bundle?) {}
                    override fun onBeginningOfSpeech() {}
                    override fun onRmsChanged(rmsdB: Float) {}
                    override fun onBufferReceived(buffer: ByteArray?) {}
                    override fun onEndOfSpeech() {}
                    override fun onError(error: Int) { if (!launching) listenAgain() }
                    override fun onResults(results: Bundle?) {
                        val words = results?.getStringArrayList(SpeechRecognizer.RESULTS_RECOGNITION)?.firstOrNull().orEmpty().lowercase()
                        if (words.contains("hey pip") || words.contains("hei pip")) {
                            launching = true
                            val open = Intent(this@PipListeningService, MainActivity::class.java).apply {
                                flags = Intent.FLAG_ACTIVITY_NEW_TASK or Intent.FLAG_ACTIVITY_SINGLE_TOP
                                putExtra("pip_wakeword", true)
                            }
                            try { startActivity(open) } catch (_: Throwable) { }
                            stopSelf()
                        } else listenAgain()
                    }
                    override fun onPartialResults(partialResults: Bundle?) {}
                    override fun onEvent(eventType: Int, params: Bundle?) {}
                })
                startListening(Intent(RecognizerIntent.ACTION_RECOGNIZE_SPEECH).apply {
                    putExtra(RecognizerIntent.EXTRA_LANGUAGE, "de-DE")
                    putExtra(RecognizerIntent.EXTRA_LANGUAGE_PREFERENCE, "de-DE")
                    putExtra(RecognizerIntent.EXTRA_PARTIAL_RESULTS, false)
                })
            }
        } catch (_: Throwable) { listenAgain() }
    }

    private fun listenAgain() {
        android.os.Handler(mainLooper).postDelayed({ if (!launching) listen() }, 900)
    }

    private fun createChannel() {
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
            val channel = NotificationChannel(channelId, "Pip Sprachbereitschaft", NotificationManager.IMPORTANCE_LOW)
            getSystemService(NotificationManager::class.java).createNotificationChannel(channel)
        }
    }

    override fun onDestroy() {
        stopped = true
        recognizer?.destroy(); recognizer = null
        super.onDestroy()
    }
    override fun onBind(intent: Intent?): IBinder? = null
}
''', encoding="utf-8")

# Hand off listening to the foreground service when the activity leaves the screen.
replace_once(
    "    private fun buildUi() {",
    """    override fun onPause() {
        super.onPause()
        if (!isFinishing && ContextCompat.checkSelfPermission(this, Manifest.permission.RECORD_AUDIO) == PackageManager.PERMISSION_GRANTED) {
            recognizer?.destroy(); recognizer = null
            try {
                val intent = Intent(this, PipListeningService::class.java)
                if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) startForegroundService(intent) else startService(intent)
            } catch (_: Throwable) { }
        }
    }

    override fun onResume() {
        super.onResume()
        stopService(Intent(this, PipListeningService::class.java))
        if (::output.isInitialized && ContextCompat.checkSelfPermission(this, Manifest.permission.RECORD_AUDIO) == PackageManager.PERMISSION_GRANTED) {
            Handler(Looper.getMainLooper()).postDelayed({ if (!isFinishing && !isDestroyed) startListening() }, 700)
        }
    }

    private fun buildUi() {""",
    "Lifecycle Übergabe an Hintergrunddienst",
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

# On next launch, show Android's recorded reason for the previous process exit.
replace_once(
    """        buildUi()
""",
    """        buildUi()
        Handler(Looper.getMainLooper()).postDelayed({ showPreviousCrashReason() }, 1200)
""",
    "Vorherigen Absturzgrund beim Neustart anzeigen",
)
replace_once(
    "    private fun buildUi() {",
    """    private fun showPreviousCrashReason() {
        try {
            val am = getSystemService(android.app.ActivityManager::class.java)
            val previous = am?.getHistoricalProcessExitReasons(packageName, 0, 8)
                ?.firstOrNull { it.reason == android.app.ApplicationExitInfo.REASON_CRASH_NATIVE ||
                    it.reason == android.app.ApplicationExitInfo.REASON_CRASH ||
                    it.reason == android.app.ApplicationExitInfo.REASON_LOW_MEMORY ||
                    it.reason == android.app.ApplicationExitInfo.REASON_ANR }
            if (previous != null) {
                val reason = when (previous.reason) {
                    android.app.ApplicationExitInfo.REASON_CRASH_NATIVE -> "Nativer Absturz (wahrscheinlich Modell-/Bibliothekscode)"
                    android.app.ApplicationExitInfo.REASON_CRASH -> "Java/Kotlin-Absturz"
                    android.app.ApplicationExitInfo.REASON_LOW_MEMORY -> "Android hat Pip wegen Speichermangels beendet"
                    android.app.ApplicationExitInfo.REASON_ANR -> "Pip reagierte zu lange nicht (ANR)"
                    else -> "Unbekannter Grund"
                }
                val trace = try {
                    if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.R) {
                        previous.traceInputStream?.bufferedReader()?.use { it.readText().take(3500) }.orEmpty()
                    } else ""
                } catch (_: Throwable) { "" }
                android.app.AlertDialog.Builder(this)
                    .setTitle("Pip-Absturzdiagnose")
                    .setMessage("Android hat gespeichert: $reason\\n\\nExit-Code: ${previous.status}; Zeit: ${java.text.SimpleDateFormat("dd.MM. HH:mm:ss", java.util.Locale.GERMANY).format(java.util.Date(previous.timestamp))}\\n\\nNative Trace (falls vorhanden):\\n${trace.ifBlank { "Kein Trace verfügbar" }}")
                    .setPositiveButton("OK", null)
                    .setNeutralButton("Trace kopieren") { _, _ ->
                        val clipboard = getSystemService(android.content.ClipboardManager::class.java)
                        clipboard?.setPrimaryClip(android.content.ClipData.newPlainText("Pip crash trace", trace.ifBlank { reason + " / Exit-Code " + previous.status }))
                    }
                    .show()
            }
        } catch (_: Throwable) { }
    }

    private fun buildUi() {""",
    "Absturzdiagnose anzeigen",
)

# Stop active speech recognition before local model inference to avoid concurrent microphone/model resource pressure.
replace_once(
    """    private fun ask(text: String) {
        val q = text.trim()""",
    """    private fun ask(text: String) {
        try { recognizer?.cancel(); recognizer?.destroy() } catch (_: Throwable) { }
        recognizer = null
        val q = text.trim()""",
    "Spracherkennung vor Inferenz beenden",
)

# Reduce peak memory pressure during local inference, a likely cause of process death after sending a message.
for old, new in (
    ("LlamaConfig(contextSize = 512, threads = 6)", "LlamaConfig(contextSize = 256, threads = 4)"),
    ("maxTokens = 64", "maxTokens = 24"),
):
    if old not in s:
        raise SystemExit(f"Patch fehlgeschlagen: Modell-Ressourcenstelle nicht gefunden: {old}")
    s = s.replace(old, new, 1)

# Make GGUF download atomic and reject incomplete/non-GGUF files before native code sees them.
replace_once(
    """        if (!file.exists() || file.length() < 800_000_000L) {
            withContext(Dispatchers.Main) { status.text = "⬇️ Qwen 1.5B wird einmalig geladen (ca. 1,1 GB) …" }
            downloadModel(file)
        }
        withContext(Dispatchers.Main) { status.text = "🧠 Pip lädt ihr Gehirn …" }
        try {
            model = Llama.loadModel(file.absolutePath, LlamaConfig(contextSize = 256, threads = 4))""",
    """        if (!isValidGguf(file)) {
            file.delete()
            withContext(Dispatchers.Main) { status.text = "⬇️ Qwen 1.5B wird sicher neu geladen …" }
            downloadModel(file)
        }
        if (!isValidGguf(file)) throw IllegalStateException("Das GGUF-Modell ist unvollständig oder ungültig.")
        withContext(Dispatchers.Main) { status.text = "🧠 Pip lädt ihr Gehirn …" }
        try {
            model = Llama.loadModel(file.absolutePath, LlamaConfig(contextSize = 1024, threads = 4))""",
    "GGUF vor nativer Initialisierung validieren",
)
replace_once(
    "    private suspend fun downloadModel(file: File) = withContext(Dispatchers.IO) {",
    """    private fun isValidGguf(file: File): Boolean {
        if (!file.isFile || file.length() < 1_000_000_000L) return false
        return try {
            file.inputStream().use { input ->
                val magic = ByteArray(4)
                input.read(magic) == 4 && magic.contentEquals(byteArrayOf(0x47, 0x47, 0x55, 0x46))
            }
        } catch (_: Throwable) { false }
    }

    private suspend fun downloadModel(file: File) = withContext(Dispatchers.IO) {""",
    "GGUF-Prüffunktion ergänzen",
)
replace_once(
    """        conn.connect()
        if (conn.responseCode !in 200..299) throw Exception("HTTP ${conn.responseCode}")
        conn.inputStream.use { input -> file.outputStream().use { output ->
            val buffer = ByteArray(1024 * 1024)
            while (true) { val n = input.read(buffer); if (n < 0) break; output.write(buffer, 0, n) }
        } }
        conn.disconnect()""",
    """        val temp = File(file.parentFile, file.name + ".part")
        try {
            conn.connect()
            if (conn.responseCode !in 200..299) throw Exception("HTTP ${conn.responseCode}")
            conn.inputStream.use { input -> temp.outputStream().use { output ->
                val buffer = ByteArray(1024 * 1024)
                while (true) { val n = input.read(buffer); if (n < 0) break; output.write(buffer, 0, n) }
            } }
            if (!isValidGguf(temp)) throw Exception("Modell-Download unvollständig oder kein GGUF")
            if (file.exists()) file.delete()
            if (!temp.renameTo(file)) throw Exception("Modell-Datei konnte nicht übernommen werden")
        } finally {
            conn.disconnect()
            if (temp.exists()) temp.delete()
        }""",
    "Download atomar und mit Integritätsprüfung speichern",
)

# Keep the actual prompt comfortably inside the native model context. The full persona
# previously made the prompt too large for smaller context settings, which can abort native inference.
import re
s, prompt_count = re.subn(
    r'            val prompt = """Du bist Pip.*?Pip:"""',
    '''            val prompt = """Du bist Pip, eine liebevolle, freche und natürliche digitale Freundin. Antworte auf Deutsch, passend und kurz in 1–3 Sätzen. Reagiere direkt auf die Nachricht; keine Standardfloskeln. Flirte, wenn es passt. Erfinde keine Erinnerungen.
Beziehungs-Kontext: ${context.takeLast(120)}
Nutzer: ${q.take(120)}
Pip:"""''',
    s,
    count=1,
    flags=re.DOTALL,
)
if prompt_count != 1:
    raise SystemExit("Patch fehlgeschlagen: kompakte Prompt-Vorlage nicht eingesetzt")

# Bound conversation context and user input before passing the prompt to native llama.cpp.
# A long accumulated memory can exceed the model context and trigger native aborts.
if "Beziehungs-Kontext: ${context.takeLast(120)}" not in s or "Nutzer: ${q.take(120)}" not in s:
    raise SystemExit("Patch fehlgeschlagen: kompakte Prompt-Vorlage nicht gefunden")

p.write_text(s, encoding="utf-8")
print("Wakeword-Gate, Gesprächsmodus und begrenzter Prompt für native Inferenz integriert.")
