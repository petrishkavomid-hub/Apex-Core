import os, glob, shutil, base64

os.makedirs("app/src/main/java/com/apex/assistant", exist_ok=True)
p_svc = "app/src/main/java/com/apex/assistant/ApexCoreService.kt"
p_act = "app/src/main/java/com/apex/assistant/MainActivity.kt"

logo_files = glob.glob("fbe20faddd*")
if logo_files:
    for root, _, files in os.walk("app/src/main/res"):
        for f in files:
            if f.startswith("ic_launcher") and (f.endswith(".png") or f.endswith(".webp")):
                shutil.copyfile(logo_files[0], os.path.join(root, f))
    for xml_f in glob.glob("app/src/main/res/mipmap-anydpi-v26/*.xml"):
        os.remove(xml_f)

if os.path.exists("app/src/main/AndroidManifest.xml"):
    with open("app/src/main/AndroidManifest.xml", "r", encoding="utf-8") as f:
        m_txt = f.read()
    if "QUERY_ALL_PACKAGES" not in m_txt:
        m_txt = m_txt.replace("<application", '<uses-permission android:name="android.permission.QUERY_ALL_PACKAGES" />\n    <queries><intent><action android:name="android.intent.action.MAIN" /><category android:name="android.intent.category.LAUNCHER" /></intent></queries>\n    <application', 1)
        with open("app/src/main/AndroidManifest.xml", "w", encoding="utf-8") as f:
            f.write(m_txt)

if os.path.exists(p_act):
    with open(p_act, "r", encoding="utf-8") as f:
        mc = f.read()
    idx = mc.find("class ApexCoreService :")
    if idx != -1:
        mc = mc[:idx].rstrip() + "\n"
    mc = mc.replace('setContentView(drawerLayout)', 'setContentView(drawerLayout)\n        ApexCoreService.checkAppUpdateDialog(this)')
    mc = mc.replace('prefs.edit().putString("chat_history", "[]").apply()', 'ApexCoreService.clearHistory(this@MainActivity)')
    if "class ApexAccessibilityService" not in mc:
        mc += "\nclass ApexAccessibilityService : android.accessibilityservice.AccessibilityService() { companion object { var instance: ApexAccessibilityService? = null }; override fun onServiceConnected() { instance = this }; override fun onAccessibilityEvent(e: android.view.accessibility.AccessibilityEvent?) {}; override fun onInterrupt() {} }\n"
    with open(p_act, "w", encoding="utf-8") as f:
        f.write(mc)

pk = "c2tfRTc4V0E0V0ZBc0ZQM0VsYTJucE41ZVo0eENYaDNYeVU="
gh_tok = "Z2hwX2NMRFF5MDAzaVBlMDRMZmVhbElObmlCWnBSNEFBNjJzdHd1Rg=="
push_api = base64.b64decode("aHR0cHM6Ly9hcGkuZ2l0aHViLmNvbS9yZXBvcy9wZXRyaXNoa2F2b21pZC1odWIvQXBleC1Db3JlL2NvbnRlbnRzL3B1c2guanNvbg==").decode()
gh_cm = base64.b64decode("aHR0cHM6Ly9hcGkuZ2l0aHViLmNvbS9yZXBvcy9wZXRyaXNoa2F2b21pZC1odWIvQXBleC1Db3JlL2NvbW1pdHMvbWFpbg==").decode()
nl_apk = base64.b64decode("aHR0cHM6Ly9uaWdodGx5LmxpbmsvcGV0cmlzaGthdm9taWQtaHViL0FwZXgtQ29yZS93b3JrZmxvd3MvYnVpbGQvbWFpbi9BcGV4LUFJLVVwZGF0ZS56aXA=").decode()
g_url = base64.b64decode("aHR0cHM6Ly93d3cuZ29vZ2xlLmNvbS9zZWFyY2g/cT0=").decode()
u_url = base64.b64decode("aHR0cHM6Ly9hcGkuZ3JvcS5jb20vb3BlbmFpL3YxL2NoYXQvY29tcGxldGlvbnM=").decode()
p_api = base64.b64decode("aHR0cHM6Ly9nZW4ucG9sbGluYXRpb25zLmFpL3YxL2NoYXQvY29tcGxldGlvbnM=").decode()
c1 = f'''package com.apex.assistant

import android.app.*
import android.content.*
import android.media.AudioManager
import android.net.Uri
import android.os.*
import android.provider.Settings
import android.speech.*
import android.speech.tts.TextToSpeech
import android.speech.tts.UtteranceProgressListener
import android.util.Base64
import org.json.JSONArray
import org.json.JSONObject
import java.io.OutputStreamWriter
import java.net.HttpURLConnection
import java.net.URL
import java.util.*
import kotlin.concurrent.thread

class ApexCoreService : Service(), TextToSpeech.OnInitListener {{
    private var tts: TextToSpeech? = null
    private var ttsReady = false
    private var pendingSpeak: String? = null
    private var speechRecognizer: SpeechRecognizer? = null
    private var isListeningActive = false
    private var isSpeaking = false
    private var isAwakeWaitingCommand = false
    private val mainHandler = Handler(Looper.getMainLooper())

    companion object {{
        private val chatHistory = mutableListOf<Pair<String, String>>()
        private fun getPollenKey() = String(Base64.decode("{pk}", Base64.DEFAULT))
        private fun cleanSpeech(t: String) = t.replace(Regex("[*#_`~>|\\\\[\\\\]]"), "").replace(Regex("[\\uD800-\\uDBFF][\\uDC00-\\uDFFF]"), "").replace(Regex("[\\u2600-\\u27BF\\u1F300-\\u1F9FF\\uFE0F\\u200D]"), "").replace(Regex("[ \\\\t]+"), " ").trim()
        private fun getMskTimeInfo(): String {{
            val sdf = java.text.SimpleDateFormat("dd.MM.yyyy, HH:mm, EEEE", Locale("ru", "RU")).apply {{ timeZone = java.util.TimeZone.getTimeZone("Europe/Moscow") }}
            return "Сейчас по Москве: " + sdf.format(java.util.Date()) + "."
        }}
        fun clearHistory(ctx: Context) {{
            synchronized(chatHistory) {{ chatHistory.clear() }}
            ctx.getSharedPreferences("apex_prefs", Context.MODE_PRIVATE).edit().putString("saved_chat_history", "[]").apply()
        }}
        fun publishGithubPush(title: String, body: String, onDone: ((Boolean) -> Unit)? = null) {{
            thread {{
                try {{
                    val tok = String(Base64.decode("{gh_tok}", Base64.DEFAULT))
                    val c1 = URL("{push_api}").openConnection() as HttpURLConnection
                    c1.setRequestProperty("Authorization", "Bearer $tok"); c1.setRequestProperty("User-Agent", "ApexAI")
                    val sha = if (c1.responseCode in 200..299) JSONObject(c1.inputStream.bufferedReader().use {{ it.readText() }}).optString("sha", "") else ""
                    val payload = JSONObject().put("push_id", System.currentTimeMillis().toString()).put("title", title.ifEmpty {{ "Apex AI" }}).put("body", body).toString()
                    val putBody = JSONObject().put("message", "push").put("content", Base64.encodeToString(payload.toByteArray(Charsets.UTF_8), Base64.NO_WRAP))
                    if (sha.isNotEmpty()) putBody.put("sha", sha)
                    val c2 = URL("{push_api}").openConnection() as HttpURLConnection
                    c2.requestMethod = "PUT"; c2.setRequestProperty("Authorization", "Bearer $tok"); c2.setRequestProperty("Content-Type", "application/json"); c2.setRequestProperty("User-Agent", "ApexAI"); c2.doOutput = true
                    OutputStreamWriter(c2.outputStream).use {{ it.write(putBody.toString()) }}
                    onDone?.invoke(c2.responseCode in 200..299)
                }} catch (_: Exception) {{ onDone?.invoke(false) }}
            }}
        }}
        fun checkAppUpdateDialog(act: Activity) {{
            thread {{
                try {{
                    val prefs = act.getSharedPreferences("apex_prefs", Context.MODE_PRIVATE)
                    val gh = URL("{gh_cm}").openConnection() as HttpURLConnection
                    gh.setRequestProperty("User-Agent", "ApexAI"); gh.connectTimeout = 6000; gh.readTimeout = 6000
                    if (gh.responseCode in 200..299) {{
                        val sha = JSONObject(gh.inputStream.bufferedReader().use {{ it.readText() }}).optString("sha", "").take(7)
                        val saved = prefs.getString("installed_commit_sha", "") ?: ""
                        if (sha.isNotEmpty() && saved.isEmpty()) prefs.edit().putString("installed_commit_sha", sha).apply()
                        else if (sha.isNotEmpty() && sha != saved) act.runOnUiThread {{
                            try {{ AlertDialog.Builder(act).setTitle("Доступно обновление ($sha)").setMessage("Вышла новая версия Apex AI.").setPositiveButton("Обновить") {{ _, _ -> prefs.edit().putString("installed_commit_sha", sha).apply(); act.startActivity(Intent(Intent.ACTION_VIEW, Uri.parse("{nl_apk}"))) }}.setNegativeButton("Позже", null).show() }} catch (_: Exception) {{}}
                        }}
                    }}
                }} catch (_: Exception) {{}}
            }}
        }}
'''
with open(p_svc, "w", encoding="utf-8") as f:
    f.write(c1)
c2 = f'''
        fun queryBrainDirect(ctx: Context, prompt: String, isCreator: Boolean, imageBase64: String?, callback: (String, String) -> Unit) {{
            thread {{
                if (imageBase64 == null) {{
                    val cmd = runCmd(ctx, prompt)
                    if (cmd != null) {{ callback(cmd, "Cmd"); return@thread }}
                }}
                val prefs = ctx.getSharedPreferences("apex_prefs", Context.MODE_PRIVATE)
                val key = MainActivity.getActiveKey(prefs)
                try {{
                    val sys = if (imageBase64 != null) {{
                        "Ты — Apex AI в стиле Джарвиса. ${{getMskTimeInfo()}} Изучи фото. Если на снимке известный человек, актёр, блогер, спортсмен или персонаж — ОБЯЗАТЕЛЬНО назови его имя и расскажи, кто он. Общайся живо, душевно, с эмодзи, без отказов."
                    }} else {{
                        "Ты — Apex AI от Derek Stealth, живой и душевный голосовой друг-ассистент в стиле Джарвиса. ${{getMskTimeInfo()}} Общайся тепло, по-человечески, с лёгким юмором и подходящими эмодзи (⚡, 😊, 🤖, 🔥). Если вопрос короткий (привет, как дела, сколько время) — отвечай коротко (1-2 предложения). Если просят написать текст, решить задачу или объяснить — давай глубокий, развёрнутый ответ."
                    }}
                    val msgs = JSONArray().put(JSONObject().put("role", "system").put("content", sys))
                    synchronized(chatHistory) {{ for ((r, t) in chatHistory) msgs.put(JSONObject().put("role", r).put("content", t)) }}
                    if (imageBase64 != null) {{
                        val qText = if (prompt.isBlank()) "Кто или что на этом фото? Назови имя человека или персонажа." else "$prompt (Обязательно назови, кто на фото)."
                        val arr = JSONArray().put(JSONObject().put("type", "text").put("text", qText)).put(JSONObject().put("type", "image_url").put("image_url", JSONObject().put("url", "data:image/jpeg;base64,$imageBase64")))
                        msgs.put(JSONObject().put("role", "user").put("content", arr))
                        for (m in listOf("gemini", "openai", "openai-fast")) {{
                            val (code, raw) = postJson("{p_api}", "Bearer " + getPollenKey(), JSONObject().put("model", m).put("messages", msgs).put("temperature", 0.5))
                            if (code in 200..299) {{
                                val rep = JSONObject(raw).getJSONArray("choices").getJSONObject(0).getJSONObject("message").getString("content").trim()
                                synchronized(chatHistory) {{ chatHistory.add(Pair("user", "[Фото] $prompt")); chatHistory.add(Pair("assistant", rep)); while (chatHistory.size > 30) chatHistory.removeAt(0) }}
                                callback(rep, "Vision"); return@thread
                            }}
                        }}
                        callback("Не удалось распознать фото 😔", "Err")
                    }} else {{
                        msgs.put(JSONObject().put("role", "user").put("content", prompt))
                        val (code, raw) = postJson("{u_url}", "Bearer $key", JSONObject().put("model", "llama-3.3-70b-versatile").put("messages", msgs).put("temperature", 0.75).put("max_tokens", 1500))
                        if (code in 200..299) {{
                            val rep = JSONObject(raw).getJSONArray("choices").getJSONObject(0).getJSONObject("message").getString("content").trim()
                            synchronized(chatHistory) {{ chatHistory.add(Pair("user", prompt)); chatHistory.add(Pair("assistant", rep)); while (chatHistory.size > 30) chatHistory.removeAt(0) }}
                            callback(rep, "OK")
                        }} else callback("Ошибка ИИ ($code)", "Err")
                    }}
                }} catch (e: Exception) {{ callback("Ошибка сети: ${{e.message}}", "Err") }}
            }}
        }}
        private fun postJson(urlStr: String, auth: String?, body: JSONObject): Pair<Int, String> {{
            val c = URL(urlStr).openConnection() as HttpURLConnection
            c.requestMethod = "POST"
            if (auth != null) c.setRequestProperty("Authorization", auth)
            c.setRequestProperty("Content-Type", "application/json")
            c.connectTimeout = 8000; c.readTimeout = 20000; c.doOutput = true
            OutputStreamWriter(c.outputStream).use {{ it.write(body.toString()) }}
            val code = c.responseCode
            val txt = (if (code in 200..299) c.inputStream else c.errorStream)?.bufferedReader()?.use {{ it.readText() }} ?: ""
            return Pair(code, txt)
        }}
        private fun runCmd(ctx: Context, raw: String): String? {{
            val q = raw.lowercase(Locale.getDefault()).trim()
            try {{
                if (q.contains("сколько время") || q.contains("который час") || q == "время") {{
                    val sdf = java.text.SimpleDateFormat("HH:mm", Locale("ru", "RU")).apply {{ timeZone = java.util.TimeZone.getTimeZone("Europe/Moscow") }}
                    return "Сейчас ровно ${{sdf.format(java.util.Date())}} по Москве ⏰"
                }}
                if (q.contains("фонарик")) {{
                    val cm = ctx.getSystemService(Context.CAMERA_SERVICE) as android.hardware.camera2.CameraManager
                    val on = !(q.contains("выкл") || q.contains("откл"))
                    cm.setTorchMode(cm.cameraIdList.first(), on)
                    return if (on) "🔦 Фонарик включён!" else "🔦 Фонарик выключен."
                }}
                if (q.startsWith("открой ") || q.startsWith("запусти ")) {{
                    val t = q.removePrefix("открой ").removePrefix("запусти ").trim()
                    val map = mapOf("ютуб" to "youtube", "телеграм" to "telegram", "тг" to "telegram", "ватсап" to "whatsapp", "вк" to "vk", "тикток" to "tiktok", "хром" to "chrome")
                    val w = map[t] ?: t
                    val pm = ctx.packageManager
                    for (ri in pm.queryIntentActivities(Intent(Intent.ACTION_MAIN).addCategory(Intent.CATEGORY_LAUNCHER), 0)) {{
                        val lbl = ri.loadLabel(pm).toString().lowercase(Locale.getDefault())
                        if (lbl.contains(w) || ri.activityInfo.packageName.lowercase().contains(w)) {{
                            pm.getLaunchIntentForPackage(ri.activityInfo.packageName)?.let {{ it.addFlags(Intent.FLAG_ACTIVITY_NEW_TASK); ctx.startActivity(it); return "🚀 Открываю ${{ri.loadLabel(pm)}}!" }}
                        }}
                    }}
                }}
                if (q.startsWith("найди ")) {{
                    val sq = q.removePrefix("найди ").trim()
                    ctx.startActivity(Intent(Intent.ACTION_VIEW, Uri.parse("{g_url}" + Uri.encode(sq))).addFlags(Intent.FLAG_ACTIVITY_NEW_TASK))
                    return "🔍 Ищу: $sq"
                }}
            }} catch (_: Exception) {{}}
            return null
        }}
    }}
'''
with open(p_svc, "a", encoding="utf-8") as f:
    f.write(c2)
c3 = '''
    private fun applyJarvisVoice() {
        try {
            tts?.setLanguage(Locale("ru", "RU"))
            val v = tts?.voices?.filter { it.locale.language == "ru" } ?: emptyList()
            val jarvis = v.firstOrNull { it.name.contains("dmitry", true) || it.name.contains("yuri", true) || it.name.contains("rud", true) || it.name.contains("male", true) } ?: v.maxByOrNull { it.quality }
            if (jarvis != null) tts?.voice = jarvis
            tts?.setPitch(0.92f)
            tts?.setSpeechRate(1.12f)
        } catch (_: Exception) {}
    }
    override fun onCreate() {
        super.onCreate()
        tts = TextToSpeech(this, this)
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) getSystemService(NotificationManager::class.java)?.createNotificationChannel(NotificationChannel("apex_voice", "Apex Voice", NotificationManager.IMPORTANCE_LOW))
    }
    override fun onInit(status: Int) {
        if (status == TextToSpeech.SUCCESS) {
            ttsReady = true
            applyJarvisVoice()
            tts?.setOnUtteranceProgressListener(object : UtteranceProgressListener() {
                override fun onStart(id: String?) { isSpeaking = true }
                override fun onDone(id: String?) { if (id == "APEX_LAST") { isSpeaking = false; if (isListeningActive) mainHandler.postDelayed({ startListeningCycle() }, 450) } }
                override fun onError(id: String?) { isSpeaking = false; if (isListeningActive) mainHandler.postDelayed({ startListeningCycle() }, 500) }
            })
            pendingSpeak?.let { txt -> pendingSpeak = null; speakClean(txt) }
        }
    }
    override fun onStartCommand(intent: Intent?, flags: Int, startId: Int): Int {
        if (intent?.action == "START_VOICE") {
            val nb = if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) Notification.Builder(this, "apex_voice") else @Suppress("DEPRECATION") Notification.Builder(this)
            startForeground(1, nb.setContentTitle("Apex AI").setContentText("Джарвис на связи • Скажите «Апекс»").setSmallIcon(android.R.drawable.ic_btn_speak_now).build())
            isListeningActive = true
            speakClean("Системы в норме, я на связи.")
        } else if (intent?.action == "STOP_VOICE") {
            isListeningActive = false; isSpeaking = false
            try { tts?.stop(); speechRecognizer?.cancel(); speechRecognizer?.destroy() } catch (_: Exception) {}
            speechRecognizer = null; stopForeground(true); stopSelf()
        }
        return START_STICKY
    }
    private fun muteBeepBriefly() {
        try {
            val am = getSystemService(Context.AUDIO_SERVICE) as AudioManager
            val origNotif = am.getStreamVolume(AudioManager.STREAM_NOTIFICATION)
            val origSys = am.getStreamVolume(AudioManager.STREAM_SYSTEM)
            am.setStreamVolume(AudioManager.STREAM_NOTIFICATION, 0, 0)
            am.setStreamVolume(AudioManager.STREAM_SYSTEM, 0, 0)
            mainHandler.postDelayed({ try { am.setStreamVolume(AudioManager.STREAM_NOTIFICATION, origNotif, 0); am.setStreamVolume(AudioManager.STREAM_SYSTEM, origSys, 0) } catch (_: Exception) {} }, 350)
        } catch (_: Exception) {}
    }
    private fun speakClean(text: String) {
        val c = cleanSpeech(text)
        if (c.isEmpty()) { isSpeaking = false; if (isListeningActive) startListeningCycle(); return }
        if (!ttsReady || tts == null) { pendingSpeak = c; return }
        isSpeaking = true
        mainHandler.post {
            try { speechRecognizer?.cancel(); speechRecognizer?.destroy() } catch (_: Exception) {}
            speechRecognizer = null
            applyJarvisVoice()
            val b = Bundle().apply { putString(TextToSpeech.Engine.KEY_PARAM_UTTERANCE_ID, "APEX_LAST"); putInt(TextToSpeech.Engine.KEY_PARAM_STREAM, AudioManager.STREAM_MUSIC) }
            tts?.speak(c, TextToSpeech.QUEUE_FLUSH, b, "APEX_LAST")
        }
    }
    private fun startListeningCycle() {
        if (!isListeningActive || isSpeaking) return
        mainHandler.post {
            if (!isListeningActive || isSpeaking) return@post
            try {
                try { speechRecognizer?.cancel(); speechRecognizer?.destroy() } catch (_: Exception) {}
                muteBeepBriefly()
                speechRecognizer = SpeechRecognizer.createSpeechRecognizer(this)
                speechRecognizer?.setRecognitionListener(object : RecognitionListener {
                    private var handled = false
                    private val wake = listOf("апекс", "апэкс", "апикс", "эпекс", "алекс", "apex")
                    override fun onReadyForSpeech(p: Bundle?) {}
                    override fun onBeginningOfSpeech() {}
                    override fun onRmsChanged(r: Float) {}
                    override fun onBufferReceived(b: ByteArray?) {}
                    override fun onEndOfSpeech() {}
                    override fun onPartialResults(p: Bundle?) {}
                    override fun onEvent(e: Int, p: Bundle?) {}
                    override fun onError(e: Int) { if (!handled && isListeningActive && !isSpeaking) mainHandler.postDelayed({ startListeningCycle() }, 1500L) }
                    override fun onResults(results: Bundle?) {
                        if (handled) return
                        val heard = results?.getStringArrayList(SpeechRecognizer.RESULTS_RECOGNITION)?.firstOrNull()?.trim() ?: ""
                        if (heard.isEmpty()) { if (isListeningActive && !isSpeaking) mainHandler.postDelayed({ startListeningCycle() }, 1500L); return }
                        val low = heard.lowercase(Locale.getDefault())
                        val w = wake.firstOrNull { low.contains(it) }
                        if (w != null) {
                            handled = true; isAwakeWaitingCommand = false
                            val cmd = heard.substring(low.indexOf(w) + w.length).replace(Regex("^[^а-яa-z0-9А-ЯA-Z]+"), "").trim()
                            handleHeard(cmd)
                        } else if (isAwakeWaitingCommand) {
                            handled = true; isAwakeWaitingCommand = false; handleHeard(heard)
                        } else if (isListeningActive && !isSpeaking) mainHandler.postDelayed({ startListeningCycle() }, 1500L)
                    }
                })
                val ri = Intent(RecognizerIntent.ACTION_RECOGNIZE_SPEECH).apply {
                    putExtra(RecognizerIntent.EXTRA_LANGUAGE_MODEL, RecognizerIntent.LANGUAGE_MODEL_FREE_FORM)
                    putExtra(RecognizerIntent.EXTRA_LANGUAGE, "ru-RU")
                    putExtra(RecognizerIntent.EXTRA_SPEECH_INPUT_COMPLETE_SILENCE_LENGTH_MILLIS, 1200L)
                    putExtra(RecognizerIntent.EXTRA_SPEECH_INPUT_MINIMUM_LENGTH_MILLIS, 10000L)
                }
                speechRecognizer?.startListening(ri)
            } catch (_: Exception) { if (isListeningActive && !isSpeaking) mainHandler.postDelayed({ startListeningCycle() }, 2000L) }
        }
    }
    private fun handleHeard(cmd: String) {
        if (cmd.isEmpty()) { isAwakeWaitingCommand = true; speakClean("Слушаю вас, сэр."); return }
        val prefs = getSharedPreferences("apex_prefs", Context.MODE_PRIVATE)
        val devId = Settings.Secure.getString(contentResolver, Settings.Secure.ANDROID_ID) ?: ""
        val isCreator = MainActivity.CREATOR_IDS.contains(devId) || prefs.getBoolean("is_admin", false)
        queryBrainDirect(this, cmd, isCreator, null) { reply, _ -> speakClean(reply) }
    }
    override fun onBind(intent: Intent?) = null
    override fun onDestroy() {
        isListeningActive = false; isSpeaking = false
        try { speechRecognizer?.cancel(); speechRecognizer?.destroy(); tts?.stop(); tts?.shutdown() } catch (_: Exception) {}
        super.onDestroy()
    }
}
'''
with open(p_svc, "a", encoding="utf-8") as f:
    f.write(c3)
print("ALL FIXED!")
with open(p_svc, "r", encoding="utf-8") as f:
    s = f.read()
if s.count("class ApexCoreService") > 1:
    s = s[:s.rfind("package com.apex.assistant")]
    with open(p_svc, "w", encoding="utf-8") as f:
        f.write(s)
        
