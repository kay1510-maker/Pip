from pathlib import Path

ROOT = Path("pip-src/app/src/main")
JAVA = ROOT / "java/de/pip/companion"
main = (JAVA / "MainActivity.kt").read_text(encoding="utf-8")
db = (JAVA / "PipMemoryDb.java").read_text(encoding="utf-8")
worker = (JAVA / "PipReminderWorker.kt").read_text(encoding="utf-8")
manifest = (ROOT / "AndroidManifest.xml").read_text(encoding="utf-8")
gradle = Path("pip-src/app/build.gradle").read_text(encoding="utf-8")
patch_script = Path(".github/scripts/patch-pip-quality.py").read_text(encoding="utf-8")
use_in_process_settings_test = "getLastSettingsDialogForTest" in patch_script

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
ui_test_source = (test_root / "PipUiInstrumentedTest.java").read_text(encoding="utf-8") if (test_root / "PipUiInstrumentedTest.java").exists() else ""
checks.update({
    "memory instrumentation tests generated": (test_root / "PipMemoryDbInstrumentedTest.java").exists(),
    "UI instrumentation tests generated": (test_root / "PipUiInstrumentedTest.java").exists(),
    "Android instrumentation runner configured": "androidx.test.runner.AndroidJUnitRunner" in gradle,
    "voice interaction stub is not shipped": "PipVoiceInteractionService" not in manifest and not (JAVA / "PipVoiceInteractionService.java").exists(),
    "settings UI test does not invoke the runtime permission controller": "GrantPermissionRule" not in ui_test_source,
    "settings UI test uses the active focus-safe strategy": (
        (
            "scenario.onActivity" in ui_test_source
            and "performClick()" in ui_test_source
            and "UiDevice" not in ui_test_source
        )
        if use_in_process_settings_test
        else (
            "UiDevice.getInstance" in ui_test_source
            and "Until.findObject" in ui_test_source
            and "androidx.test.espresso.Espresso" not in ui_test_source
        )
    ),
    "settings dialog test seam is present when in-process mode is enabled": (
        not use_in_process_settings_test
        or ("getLastSettingsDialogForTest" in main and "getLastSettingsDialogForTest" in ui_test_source)
    ),
    "settings dialog accessor avoids a Kotlin/JVM property getter collision": (
        not use_in_process_settings_test
        or (
            "fun getLastSettingsDialogForTest(): AlertDialog? = lastSettingsDialogForTestRef" in main
            and main.count("lastSettingsDialogForTestRef = it") >= 3
        )
    ),
    "speech setting is exercised through the settings dialog": (
        "Antworten laut vorlesen" in ui_test_source
        and "speech_enabled" in ui_test_source
        and "AlertDialog.BUTTON_POSITIVE" in ui_test_source
    ) if use_in_process_settings_test else "speech_enabled" in ui_test_source,
    "notification options remain opt-in": (
        "Benachrichtigungen außerhalb der App" in ui_test_source
        and "notifications_enabled" in ui_test_source
        and "assertFalse" in ui_test_source
    ),
    "UIAutomator dependency matches the current test mode": (
        "androidx.test.uiautomator:uiautomator:2.3.0" not in gradle
        if use_in_process_settings_test
        else "androidx.test.uiautomator:uiautomator:2.3.0" in gradle
    ),
})


ask_start = main.index("private fun ask(text: String)")
ask_end = main.index("private suspend fun askLoaded(q: String)", ask_start)
ask_source = main[ask_start:ask_end]
on_create_start = main.index("override fun onCreate(")
on_create_end = main.index("private fun showPreviousCrashReason()", on_create_start)
on_create_source = main[on_create_start:on_create_end]

pc_route = 'if (getSharedPreferences("pip_settings", MODE_PRIVATE).getBoolean("pc_backend_enabled", false)) {'
pc_route_positions = []
search_from = 0
while True:
    position = ask_source.find(pc_route, search_from)
    if position < 0:
        break
    pc_route_positions.append(position)
    search_from = position + len(pc_route)
normal_pc_route = pc_route_positions[-1] if len(pc_route_positions) >= 2 else -1
local_model_branch = ask_source.find("if (model == null)", normal_pc_route) if normal_pc_route >= 0 else -1
normal_pc_block = ask_source[normal_pc_route:local_model_branch] if local_model_branch > normal_pc_route else ""
local_model_block = ask_source[local_model_branch:] if local_model_branch >= 0 else ""

pc_route = 'if (getSharedPreferences("pip_settings", MODE_PRIVATE).getBoolean("pc_backend_enabled", false)) {'
pc_route_positions = []
search_from = 0
while True:
    position = ask_source.find(pc_route, search_from)
    if position < 0:
        break
    pc_route_positions.append(position)
    search_from = position + len(pc_route)
normal_pc_route = pc_route_positions[-1] if len(pc_route_positions) >= 2 else -1
local_model_branch = ask_source.find("if (model == null)", normal_pc_route) if normal_pc_route >= 0 else -1
normal_pc_block = ask_source[normal_pc_route:local_model_branch] if local_model_branch > normal_pc_route else ""
local_model_block = ask_source[local_model_branch:] if local_model_branch >= 0 else ""
checks.update({
    "on-device model is loaded lazily rather than during app startup": "prepareModel()" not in on_create_source,
    "microphone permission is requested only after explicit tap": (
        "requestPermissions(this, arrayOf(Manifest.permission.RECORD_AUDIO), 10)" not in on_create_source
        and "checkSelfPermission(this, Manifest.permission.RECORD_AUDIO)" in asr
        and "requestPermissions(this, arrayOf(Manifest.permission.RECORD_AUDIO), 10)" in asr
    ),
    "PC backend is opt-in and local inference remains reachable": (
        len(pc_route_positions) >= 2
        and local_model_branch > normal_pc_route
        and "askWithPc(q)" in normal_pc_block
        and "return" in normal_pc_block
        and "modelInitMutex.withLock" in local_model_block
        and "askLoaded(q)" in local_model_block
    ),
    "PC brain is opt-in after explicit memory commands": (
        'getBoolean("pc_backend_enabled", false)' in ask_source
        and "val memoryMatch" in ask_source
        and ask_source.index("val memoryMatch") < ask_source.index('getBoolean("pc_backend_enabled", false)')
    ),
    "PC replies use Android TTS rather than disabled Supertonic": (
        'tts.speak(displayAnswer' in main and "speakWithSupertonic(answer)" not in main
    ),
    "PC proactive reminders use the authenticated live endpoint": all(
        item in worker for item in (
            'getBoolean("pc_backend_enabled", false)',
            'URL("$base/proactive")',
            'requestMethod = "POST"',
            'setRequestProperty("Authorization", "Bearer $token")',
            'optBoolean("ready", false)',
        )
    ),
    "PC proactive messages receive current Android personality": all(
        item in worker for item in (
            'payload.put("personality", personality)',
            '.put("initiative", prefs.getInt("initiative", 70))',
            '.put("humor", prefs.getInt("humor", 65))',
            '.put("romance", prefs.getInt("romance", 60))',
            '.put("jealousy", prefs.getInt("jealousy", 20))',
        )
    ),
    "PC proactive messages receive a bounded local memory snapshot": all(
        item in worker for item in (
            'PipMemoryDb(context)',
            'cursor.getString(1)',
            'cursor.getString(2)',
            'memories.length() < 50',
            'payload.put("memories", memories)',
        )
    ),
    "PC proactive reminders respect idle gate and local-network boundary": (
        'if (!result.optBoolean("ready", false)) return null' in worker
        and all(item in worker for item in (
            "isLoopbackAddress", "isSiteLocalAddress", "isLinkLocalAddress"
        ))
    ),
    "static reminder text is used only when the PC brain is disabled": (
        'if (prefs.getBoolean("pc_backend_enabled", false))' in worker
        and "fallbackMessage()" in worker
    ),
    "PC proactive requests run only when notifications are enabled and outside quiet hours": (
        worker.index('if (!prefs.getBoolean("notifications_enabled", false))')
        < worker.index("if (inQuietHours) return Result.success()")
        < worker.index("createPcMessage(context, prefs)")
    ),

    "PC endpoint restricted to private/local addresses": all(x in main for x in ("isLoopbackAddress", "isSiteLocalAddress", "isLinkLocalAddress")),
    "PC backend receives Android personality and local memory snapshot": all(x in main for x in ('.put("personality", personality)', '.put("memories", memorySnapshot)')),
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
