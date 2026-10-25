from pathlib import Path

ROOT = Path("pip-src/app/src/main")
JAVA = ROOT / "java/de/pip/companion"
main = (JAVA / "MainActivity.kt").read_text(encoding="utf-8")
db = (JAVA / "PipMemoryDb.java").read_text(encoding="utf-8")
worker = (JAVA / "PipReminderWorker.kt").read_text(encoding="utf-8")
manifest = (ROOT / "AndroidManifest.xml").read_text(encoding="utf-8")
gradle = Path("pip-src/app/build.gradle").read_text(encoding="utf-8")

asr = main[main.index("private fun startListening()"):main.index("override fun onInit(statusCode: Int)")]
checks = {
    "local Qwen GGUF path": "qwen2.5-0.5b-instruct-q4_k_m.gguf" in main.lower() and "Llama.complete" in main,
    "serial model initialization and inference": "modelInitMutex.withLock" in main and "inferenceMutex.withLock" in main,
    "persistent long-term memories": "WHERE category!='Gespräch'" in db and "ORDER BY importance DESC,created DESC LIMIT 5" in db,
    "recent conversation context separated": "WHERE category='Gespräch' ORDER BY created DESC LIMIT ?" in db and "Letzte Gespräche:" in db,
    "memory edit/delete/reset APIs": all(x in db for x in ("updateMemory(", "deleteMemory(", "clearMemories(")),
    "chat exposes memory management": all(x in main for x in ("showMemories()", "showEditMemory(", "db.clearMemories()")),
    "ASR startup failure is caught": "catch (e: Throwable)" in asr and "createOnDeviceSpeechRecognizer" in asr,
    "text chat clears sent input": 'input.setText("")' in main and 'appendHistory("Kay", q)' in main,
    "speech preference is present": 'speech_enabled' in main and "speechSwitch.isChecked" in main,
    "assistant text is spoken through the configured TTS path": any(token in main for token in ('tts.speak(displayAnswer', 'tts.speak(answer', 'tts.speak(reply')),
    "voice selection persists": 'putString("tts_voice_name", voice.name)' in main and 'getString("tts_voice_name", null)' in main,
    "notification feature defaults off": 'getBoolean("notifications_enabled", false)' in main and 'getBoolean("notifications_enabled", false)' in worker,
    "notification frequency is configurable": "notification_interval_days" in main and "PeriodicWorkRequestBuilder<PipReminderWorker>(days" in main,
    "quiet hours are enforced": all(x in worker for x in ("quiet_start_hour", "quiet_end_hour", "LocalTime.now()", "if (inQuietHours) return Result.success()")),
    "wakeword service reference removed from chat": "PipListeningService" not in main,
    "wakeword service declaration removed from manifest": "PipListeningService" not in manifest,
    "wakeword service source deleted": not (JAVA / "PipListeningService.kt").exists(),
    "unused ONNX wakeword dependency removed": "com.microsoft.onnxruntime" not in gradle and not (ROOT / "assets/hey_pip/wake.int8.onnx").exists(),
    "notification permission declared": 'android.permission.POST_NOTIFICATIONS' in manifest,
}


test_root = Path("pip-src/app/src/androidTest/java/de/pip/companion")
checks.update({
    "memory instrumentation tests generated": (test_root / "PipMemoryDbInstrumentedTest.java").exists(),
    "UI instrumentation tests generated": (test_root / "PipUiInstrumentedTest.java").exists(),
    "Android instrumentation runner configured": "androidx.test.runner.AndroidJUnitRunner" in gradle,
    "voice interaction stub is not shipped": "PipVoiceInteractionService" not in manifest and not (JAVA / "PipVoiceInteractionService.java").exists(),
})


ask_start = main.index("private fun ask(text: String)")
ask_end = main.index("private suspend fun askLoaded(q: String)", ask_start)
ask_source = main[ask_start:ask_end]
checks.update({
    "PC brain is opt-in after explicit memory commands": (
        'getBoolean("pc_backend_enabled", false)' in ask_source
        and "val memoryMatch" in ask_source
        and ask_source.index("val memoryMatch") < ask_source.index('getBoolean("pc_backend_enabled", false)')
    ),
    "PC replies use Android TTS rather than disabled Supertonic": (
        'tts.speak(displayAnswer' in main and "speakWithSupertonic(answer)" not in main
    ),

    "PC endpoint restricted to private/local addresses": all(x in main for x in ("isLoopbackAddress", "isSiteLocalAddress", "isLinkLocalAddress")),
    "PC memory sync is opt-in and follows local save": (
        'db.remember("Von dir gemerkt", explicitMemory, 3)' in ask_source
        and ask_source.index('db.remember("Von dir gemerkt", explicitMemory, 3)') < ask_source.index("askWithPc(q)")
        and 'getBoolean("pc_backend_enabled", false)' in ask_source
    ),
    "activity cleans up TTS and database": all(x in main for x in ("override fun onDestroy()", "tts.shutdown()", "db.close()")),
})

failed = [name for name, passed in checks.items() if not passed]
for name, passed in checks.items():
    print(f'{"PASS" if passed else "FAIL"}: {name}')
if failed:
    raise SystemExit("Pip source contract checks failed: " + ", ".join(failed))
print(f"Passed {len(checks)} static source-contract checks. Device behavior is not tested by this script.")
