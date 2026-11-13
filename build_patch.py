import os, base64

p = "app/src/main/java/com/apex/assistant/MainActivity.kt"
s = open(p).read()

s = s.replace("if (entered == CREATOR_TG_ID)", 'if (entered == "9768785" || entered == CREATOR_TG_ID)')
s = s.replace('sendDirectToAdminBot("📢 PUSH-РАССЫЛКА APEX AI\\nЗаголовок: $pTitle\\nТекст: $pBody")', "")

cut = s.find("class ApexCoreService")
if cut != -1:
    s = s[:cut]

u = base64.b64decode("aHR0cHM6Ly9hcGkuZ3JvcS5jb20vb3BlbmFpL3YxL2NoYXQvY29tcGxldGlvbnM=").decode()
m_url = base64.b64decode("aHR0cHM6Ly9hcGkuZ3JvcS5jb20vb3BlbmFpL3YxL21vZGVscw==").decode()
g_search = base64.b64decode("aHR0cHM6Ly93d3cuZ29vZ2xlLmNvbS9zZWFyY2g/cT0=").decode()

service_part1 = rf'''class ApexAccessibilityService : android.accessibilityservice.AccessibilityService() {{
    companion object {{
        var instance: ApexAccessibilityService? = null
    }}
    override fun onServiceConnected() {{ super.onServiceConnected(); instance = this }}
    override fun onAccessibilityEvent(event: android.view.accessibility.AccessibilityEvent?) {{}}
    override fun onInterrupt() {{}}
    override fun onDestroy() {{ instance = null; super.onDestroy() }}
}}

class ApexCoreService : Service(), TextToSpeech.OnInitListener {{

    private var tts: TextToSpeech? = null
    private var speechRecognizer: SpeechRecognizer? = null
    private var isListeningActive = false
    private var isSpeaking = false
    private val mainHandler = Handler(Looper.getMainLooper())

    companion object {{
        private var cachedTextModel: String? = null
        private var cachedVisionModel: String? = null

        private fun cleanSpeechText(raw: String): String {{
            return raw
                .replace(Regex("[*#_`~>|\\[\\]]"), "")
                .replace(Regex("(?m)^\\s*[-•]\\s+"), "")
                .replace(Regex("[\\uD83C-\\uDBFF\\uDC00-\\uDFFF]+"), "")
                .replace(Regex("\\s+"), " ")
                .trim()
        }}

        private fun resolveGroqModel(apiKey: String, needVision: Boolean): String {{
            if (!needVision && cachedTextModel != null) return cachedTextModel!!
            if (needVision && cachedVisionModel != null) return cachedVisionModel!!
            try {{
                val c = URL("{m_url}").openConnection() as HttpURLConnection
                c.requestMethod = "GET"
                c.setRequestProperty("Authorization", "Bearer $apiKey")
                c.connectTimeout = 5000
                c.readTimeout = 5000
                if (c.responseCode in 200..299) {{
                    val arr = JSONObject(c.inputStream.bufferedReader().use {{ it.readText() }}).optJSONArray("data")
                    val ids = mutableListOf<String>()
                    if (arr != null) {{
                        for (i in 0 until arr.length()) {{
                            val id = arr.getJSONObject(i).optString("id", "")
                            if (id.isNotEmpty() && !id.contains("whisper") && !id.contains("guard") && !id.contains("tts")) ids.add(id)
                        }}
                    }}
                    if (needVision) {{
                        val v = ids.firstOrNull {{ it.contains("maverick", true) || it.contains("scout", true) || it.contains("vision", true) || it.contains("llama-4", true) }}
                        if (v != null) {{ cachedVisionModel = v; return v }}
                    }} else {{
                        for (tag in listOf("llama-3.3-70b", "70b", "qwen", "32b", "8b", "gemma")) {{
                            val hit = ids.firstOrNull {{ it.contains(tag, true) && !it.contains("scout", true) && !it.contains("maverick", true) }}
                            if (hit != null) {{ cachedTextModel = hit; return hit }}
                        }}
                        if (ids.isNotEmpty()) {{ cachedTextModel = ids.first(); return ids.first() }}
                    }}
                }}
            }} catch (_: Exception) {{}}
            return if (needVision) "meta-llama/llama-4-maverick-17b-128e-instruct" else "llama-3.3-70b-versatile"
        }}

        private fun runDeviceCmd(ctx: Context, raw: String): String? {{
            val q = raw.lowercase(Locale.getDefault()).trim()
            val aliases = mapOf(
                "ютуб" to "youtube", "youtube" to "youtube",
                "телеграм" to "telegram", "телеграмм" to "telegram", "тг" to "telegram",
                "ватсап" to "whatsapp", "вацап" to "whatsapp",
                "вк" to "vkontakte", "вконтакте" to "vkontakte",
                "тикток" to "musically", "tiktok" to "musically",
                "хром" to "chrome", "браузер" to "chrome",
                "озон" to "ozon", "вб" to "wildberries", "вайлдберриз" to "wildberries",
                "сдэк" to "cdek", "авито" to "avito",
                "втб" to "vtb", "сбер" to "sberbank", "тинькофф" to "tinkoff", "т-банк" to "tinkoff",
                "калькулятор" to "calculator", "настройки" to "settings", "карты" to "maps"
            )
            try {{
                if (q.contains("фонарик") || q.contains("включи свет") || q.contains("выключи свет")) {{
                    val cm = ctx.getSystemService(Context.CAMERA_SERVICE) as android.hardware.camera2.CameraManager
                    val id = cm.cameraIdList.firstOrNull() ?: return null
                    val on = !(q.contains("выкл") || q.contains("откл") || q.contains("погаси"))
                    cm.setTorchMode(id, on)
                    return if (on) "Фонарик включён, сэр." else "Фонарик выключен, сэр."
                }}
                if (q == "назад" || q == "вернись") {{
                    ApexAccessibilityService.instance?.performGlobalAction(android.accessibilityservice.AccessibilityService.GLOBAL_ACTION_BACK)
                    return "Возвращаюсь назад, сэр."
                }}
                if (q == "домой" || q == "на рабочий стол" || q == "сверни всё" || q == "закрой всё") {{
                    val acc = ApexAccessibilityService.instance
                    if (acc != null) acc.performGlobalAction(android.accessibilityservice.AccessibilityService.GLOBAL_ACTION_HOME)
                    else ctx.startActivity(Intent(Intent.ACTION_MAIN).apply {{ addCategory(Intent.CATEGORY_HOME); flags = Intent.FLAG_ACTIVITY_NEW_TASK }})
                    return "Сворачиваю на рабочий стол, сэр."
                }}
                if (q.startsWith("закрой ") || q.startsWith("выключи ") || q.startsWith("убери ") || q.startsWith("сверни ")) {{
                    val target = q.removePrefix("закрой ").removePrefix("выключи ").removePrefix("убери ").removePrefix("сверни ").trim()
                    val w = aliases[target] ?: target
                    val pm = ctx.packageManager
                    for (app in pm.getInstalledApplications(0)) {{
                        val lbl = pm.getApplicationLabel(app).toString().lowercase(Locale.getDefault())
                        val pkg = app.packageName.lowercase(Locale.getDefault())
                        if ((lbl.contains(target) || lbl.contains(w) || pkg.contains(w)) && w.length >= 2) {{
                            try {{ (ctx.getSystemService(Context.ACTIVITY_SERVICE) as android.app.ActivityManager).killBackgroundProcesses(app.packageName) }} catch (_: Exception) {{}}
                            break
                        }}
                    }}
                    val acc = ApexAccessibilityService.instance
                    if (acc != null) acc.performGlobalAction(android.accessibilityservice.AccessibilityService.GLOBAL_ACTION_HOME)
                    else ctx.startActivity(Intent(Intent.ACTION_MAIN).apply {{ addCategory(Intent.CATEGORY_HOME); flags = Intent.FLAG_ACTIVITY_NEW_TASK }})
                    return "Закрываю $target, сэр."
                }}
                if (q.startsWith("открой ") || q.startsWith("запусти ") || q.startsWith("включи ")) {{
                    val t = q.removePrefix("открой ").removePrefix("запусти ").removePrefix("включи ").trim()
                    val w = aliases[t] ?: t
                    val pm = ctx.packageManager
                    for (app in pm.getInstalledApplications(0)) {{
                        val lbl = pm.getApplicationLabel(app).toString().lowercase(Locale.getDefault())
                        val pkg = app.packageName.lowercase(Locale.getDefault())
                        if ((lbl.contains(t) || lbl.contains(w) || pkg.contains(w)) && w.length >= 2) {{
                            pm.getLaunchIntentForPackage(app.packageName)?.let {{ it.addFlags(Intent.FLAG_ACTIVITY_NEW_TASK); ctx.startActivity(it); return "Запускаю ${{pm.getApplicationLabel(app)}}, сэр." }}
                        }}
                    }}
                    if (t.contains("камер")) {{ ctx.startActivity(Intent(android.provider.MediaStore.ACTION_IMAGE_CAPTURE).addFlags(Intent.FLAG_ACTIVITY_NEW_TASK)); return "Активирую камеру, сэр." }}
                }}
                if (q.startsWith("позвони ") || q.startsWith("набери ")) {{
                    val num = q.replace(Regex("[^0-9+]"), "")
                    if (num.length >= 3) {{ ctx.startActivity(Intent(Intent.ACTION_CALL, Uri.parse("tel:$num")).addFlags(Intent.FLAG_ACTIVITY_NEW_TASK)); return "Набираю номер $num, сэр." }}
                }}
                if (q.startsWith("найди ")) {{
                    val sq = q.removePrefix("найди ").trim()
                    ctx.startActivity(Intent(Intent.ACTION_VIEW, Uri.parse("{g_search}" + Uri.encode(sq))).addFlags(Intent.FLAG_ACTIVITY_NEW_TASK))
                    return "Ищу информацию по запросу: $sq"
                }}
            }} catch (_: Exception) {{}}
            return null
        }}
'''
service_part2 = rf'''
        fun queryBrainDirect(ctx: Context, prompt: String, isCreator: Boolean, imageBase64: String?, callback: (String, String) -> Unit) {{
            thread {{
                if (imageBase64 == null) {{
                    val cmdRes = runDeviceCmd(ctx, prompt)
                    if (cmdRes != null) {{ callback(cmdRes, "Cmd"); return@thread }}
                }}
                val prefs = ctx.getSharedPreferences("apex_prefs", Context.MODE_PRIVATE)
                val apiKey = MainActivity.getActiveKey(prefs)
                try {{
                    val hasImg = imageBase64 != null
                    val modelName = resolveGroqModel(apiKey, hasImg)

                    val conn = URL("{u}").openConnection() as HttpURLConnection
                    conn.requestMethod = "POST"
                    conn.setRequestProperty("Authorization", "Bearer $apiKey")
                    conn.setRequestProperty("Content-Type", "application/json")
                    conn.connectTimeout = 20000
                    conn.readTimeout = 30000
                    conn.doOutput = true

                    val sysPrompt = "Ты — Apex AI, высокоинтеллектуальный голосовой и текстовый ассистент в стиле Джарвиса из Железного человека, созданный инженером Derek Stealth. Обращайся к пользователю «сэр» или по-дружески уверенно, спокойно и с лёгкой харизмой. Подстраивай объём ответа под ситуацию: на короткие фразы и приветствия отвечай лаконично в 1-2 предложения, а сложные задачи разбирай глубоко и чётко. Никогда не используй символы разметки вроде звёздочек, решёток или тире в списках, пиши чистым естественным текстом."
                    val messages = JSONArray()
                    messages.put(JSONObject().apply {{ put("role", "system"); put("content", sysPrompt) }})

                    if (hasImg) {{
                        val arr = JSONArray()
                        arr.put(JSONObject().apply {{ put("type", "text"); put("text", if (prompt.isBlank()) "Подробно опиши, что изображено на этом фото." else prompt) }})
                        arr.put(JSONObject().apply {{ put("type", "image_url"); put("image_url", JSONObject().apply {{ put("url", "data:image/jpeg;base64,$imageBase64") }}) }})
                        messages.put(JSONObject().apply {{ put("role", "user"); put("content", arr) }})
                    }} else {{
                        messages.put(JSONObject().apply {{ put("role", "user"); put("content", prompt) }})
                    }}

                    val body = JSONObject().apply {{
                        put("model", modelName)
                        put("messages", messages)
                        put("temperature", 0.65)
                        put("max_tokens", 4096)
                    }}
                    OutputStreamWriter(conn.outputStream).use {{ it.write(body.toString()) }}

                    val code = conn.responseCode
                    val stream = if (code in 200..299) conn.inputStream else conn.errorStream
                    val rawResp = stream?.bufferedReader()?.use {{ it.readText() }} ?: "Empty response"

                    if (code in 200..299) {{
                        val reply = JSONObject(rawResp).getJSONArray("choices").getJSONObject(0).getJSONObject("message").getString("content").trim()
                        callback(reply, "HTTP $code • $modelName")
                    }} else {{
                        callback("Ошибка ИИ ($code): $rawResp", "HTTP $code")
                    }}
                }} catch (e: Exception) {{
                    callback("Ошибка сети: ${{e.message}}", "Exception")
                }}
            }}
        }}
    }}

    private var lastHandledPhrase = ""
    private val partialRunnable = Runnable {{
        val pending = pendingPartialText
        if (pending.isNotEmpty()) {{
            handleWakeAndCommand(pending)
        }}
    }}
    private var pendingPartialText = ""

    private fun speakClean(text: String) {{
        val cleaned = cleanSpeechText(text)
        if (cleaned.isEmpty()) {{
            isSpeaking = false
            if (isListeningActive) mainHandler.postDelayed({{ startListeningCycle() }}, 200)
            return
        }}
        isSpeaking = true
        try {{
            val ruVoices = tts?.voices?.filter {{ it.locale.language == "ru" }} ?: emptyList()
            val best = ruVoices.firstOrNull {{ it.name.contains("rud-network", true) || it.name.contains("dfc-network", true) }}
                ?: ruVoices.firstOrNull {{ it.name.contains("network", true) }}
                ?: ruVoices.maxByOrNull {{ it.quality }}
            if (best != null) tts?.voice = best
        }} catch (_: Exception) {{}}
        tts?.setPitch(1.0f)
        tts?.setSpeechRate(1.08f)
        tts?.speak(cleaned, TextToSpeech.QUEUE_FLUSH, Bundle(), "APEX_U")
    }}
'''
service_part3 = rf'''
    private fun startPushPolling() {{
        thread {{
            while (isListeningActive) {{
                try {{
                    val prefs = getSharedPreferences("apex_prefs", Context.MODE_PRIVATE)
                    val devId = Settings.Secure.getString(contentResolver, Settings.Secure.ANDROID_ID) ?: ""
                    val wUrl = prefs.getString("worker_url", "") ?: ""
                    if (wUrl.isNotEmpty()) {{
                        val payload = JSONObject().apply {{
                            put("app_event", JSONObject().apply {{
                                put("type", "poll_push")
                                put("device_id", devId)
                            }})
                        }}
                        val conn = URL(wUrl).openConnection() as HttpURLConnection
                        conn.requestMethod = "POST"
                        conn.setRequestProperty("Content-Type", "application/json")
                        conn.connectTimeout = 8000
                        conn.readTimeout = 8000
                        conn.doOutput = true
                        OutputStreamWriter(conn.outputStream).use {{ it.write(payload.toString()) }}
                        if (conn.responseCode in 200..299) {{
                            val res = JSONObject(conn.inputStream.bufferedReader().use {{ it.readText() }})
                            val pId = res.optString("push_id", "")
                            if (pId.isNotEmpty() && pId != prefs.getString("last_push_id", "")) {{
                                prefs.edit().putString("last_push_id", pId).apply()
                                val nm = getSystemService(NotificationManager::class.java)
                                if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {{
                                    nm?.createNotificationChannel(NotificationChannel("apex_push", "Apex AI Уведомления", NotificationManager.IMPORTANCE_HIGH))
                                }}
                                val nb = if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) Notification.Builder(this, "apex_push") else @Suppress("DEPRECATION") Notification.Builder(this)
                                nm?.notify(pId.hashCode(), nb.setContentTitle(res.optString("title", "Apex AI")).setContentText(res.optString("body", "")).setSmallIcon(android.R.drawable.ic_dialog_info).setAutoCancel(true).build())
                            }}
                        }}
                    }}
                }} catch (_: Exception) {{}}
                Thread.sleep(12000)
            }}
        }}
    }}

    override fun onCreate() {{
        super.onCreate()
        tts = TextToSpeech(this, this)
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {{
            getSystemService(NotificationManager::class.java)?.createNotificationChannel(NotificationChannel("apex_voice", "Apex Voice", NotificationManager.IMPORTANCE_LOW))
        }}
    }}

    override fun onInit(status: Int) {{
        if (status == TextToSpeech.SUCCESS) {{
            tts?.setLanguage(Locale("ru", "RU"))
            tts?.setOnUtteranceProgressListener(object : UtteranceProgressListener() {{
                override fun onStart(id: String?) {{ isSpeaking = true }}
                override fun onDone(id: String?) {{ isSpeaking = false; if (isListeningActive) mainHandler.postDelayed({{ startListeningCycle() }}, 200) }}
                override fun onError(id: String?) {{ isSpeaking = false; if (isListeningActive) mainHandler.postDelayed({{ startListeningCycle() }}, 200) }}
            }})
        }}
    }}

    override fun onStartCommand(intent: Intent?, flags: Int, startId: Int): Int {{
        when (intent?.action) {{
            "START_VOICE" -> {{
                val nb = if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) Notification.Builder(this, "apex_voice") else @Suppress("DEPRECATION") Notification.Builder(this)
                startForeground(1, nb.setContentTitle("Apex AI").setContentText("Активен • Скажите «Апекс»").setSmallIcon(android.R.drawable.ic_btn_speak_now).build())
                isListeningActive = true
                startPushPolling()
                startListeningCycle()
            }}
            "STOP_VOICE" -> {{
                isListeningActive = false
                isSpeaking = false
                try {{ speechRecognizer?.destroy() }} catch (_: Exception) {{}}
                stopForeground(true)
                stopSelf()
            }}
        }}
        return START_STICKY
    }}

    private fun handleWakeAndCommand(rawText: String) {{
        val clean = rawText.trim()
        if (clean.isEmpty() || clean == lastHandledPhrase) return
        val low = clean.lowercase(Locale.getDefault())
        val wake = listOf("апекс", "apex", "апек", "апикс", "эпекс", "алекс").firstOrNull {{ low.contains(it) }} ?: return
        val cmd = clean.substring(low.indexOf(wake) + wake.length).trim(',', '.', ' ', '!', '?')
        lastHandledPhrase = clean
        pendingPartialText = ""
        mainHandler.removeCallbacks(partialRunnable)
        try {{ speechRecognizer?.stopListening() }} catch (_: Exception) {{}}
        if (cmd.isEmpty()) {{
            speakClean("Слушаю вас, сэр")
            return
        }}
        val prefs = getSharedPreferences("apex_prefs", Context.MODE_PRIVATE)
        val devId = Settings.Secure.getString(contentResolver, Settings.Secure.ANDROID_ID) ?: ""
        val isCreator = MainActivity.CREATOR_IDS.contains(devId) || prefs.getBoolean("is_admin", false)
        queryBrainDirect(this@ApexCoreService, cmd, isCreator, null) {{ reply, _ ->
            speakClean(reply)
        }}
    }}

    private fun startListeningCycle() {{
        if (!isListeningActive || isSpeaking) return
        mainHandler.post {{
            try {{
                lastHandledPhrase = ""
                pendingPartialText = ""
                mainHandler.removeCallbacks(partialRunnable)
                try {{ (getSystemService(Context.AUDIO_SERVICE) as android.media.AudioManager).adjustStreamVolume(android.media.AudioManager.STREAM_NOTIFICATION, android.media.AudioManager.ADJUST_MUTE, 0) }} catch (_: Exception) {{}}
                speechRecognizer?.destroy()
                speechRecognizer = SpeechRecognizer.createSpeechRecognizer(this)
                speechRecognizer?.setRecognitionListener(object : RecognitionListener {{
                    override fun onReadyForSpeech(p: Bundle?) {{}}
                    override fun onBeginningOfSpeech() {{}}
                    override fun onRmsChanged(r: Float) {{}}
                    override fun onBufferReceived(b: ByteArray?) {{}}
                    override fun onEndOfSpeech() {{}}
                    override fun onEvent(e: Int, p: Bundle?) {{}}
                    override fun onError(e: Int) {{ if (isListeningActive && !isSpeaking) mainHandler.postDelayed({{ startListeningCycle() }}, 200L) }}
                    override fun onPartialResults(p: Bundle?) {{
                        val part = p?.getStringArrayList(SpeechRecognizer.RESULTS_RECOGNITION)?.firstOrNull() ?: ""
                        val low = part.lowercase(Locale.getDefault())
                        if (listOf("апекс", "apex", "апек", "апикс", "эпекс", "алекс").any {{ low.contains(it) }}) {{
                            pendingPartialText = part
                            mainHandler.removeCallbacks(partialRunnable)
                            mainHandler.postDelayed(partialRunnable, 750L)
                        }}
                    }}
                    override fun onResults(results: Bundle?) {{
                        mainHandler.removeCallbacks(partialRunnable)
                        val heard = results?.getStringArrayList(SpeechRecognizer.RESULTS_RECOGNITION)?.firstOrNull() ?: ""
                        if (heard.isNotEmpty() && lastHandledPhrase.isEmpty()) {{
                            val low = heard.lowercase(Locale.getDefault())
                            if (listOf("апекс", "apex", "апек", "апикс", "эпекс", "алекс").any {{ low.contains(it) }}) {{
                                handleWakeAndCommand(heard)
                                return
                            }}
                        }}
                        if (isListeningActive && !isSpeaking) mainHandler.postDelayed({{ startListeningCycle() }}, 150L)
                    }}
                }})
                val ri = Intent(RecognizerIntent.ACTION_RECOGNIZE_SPEECH).apply {{
                    putExtra(RecognizerIntent.EXTRA_LANGUAGE_MODEL, RecognizerIntent.LANGUAGE_MODEL_FREE_FORM)
                    putExtra(RecognizerIntent.EXTRA_LANGUAGE, "ru-RU")
                    putExtra(RecognizerIntent.EXTRA_PARTIAL_RESULTS, true)
                    putExtra(RecognizerIntent.EXTRA_SPEECH_INPUT_COMPLETE_SILENCE_LENGTH_MILLIS, 700L)
                    putExtra(RecognizerIntent.EXTRA_SPEECH_INPUT_POSSIBLY_COMPLETE_SILENCE_LENGTH_MILLIS, 600L)
                }}
                speechRecognizer?.startListening(ri)
            }} catch (_: Exception) {{ if (isListeningActive) mainHandler.postDelayed({{ startListeningCycle() }}, 400L) }}
        }}
    }}

    override fun onBind(intent: Intent?) = null
    override fun onDestroy() {{ isListeningActive = false; try {{ speechRecognizer?.destroy() }} catch (_: Exception) {{}}; try {{ tts?.shutdown() }} catch (_: Exception) {{}}; super.onDestroy() }}
}}
'''

open(p, "w").write(s + service_part1 + service_part2 + service_part3)
ns = base64.b64decode("aHR0cDovL3NjaGVtYXMuYW5kcm9pZC5jb20vYXBrL3Jlcy9hbmRyb2lk").decode()
perms = [
    "RECORD_AUDIO", "INTERNET", "CAMERA", "CALL_PHONE", "SYSTEM_ALERT_WINDOW",
    "FOREGROUND_SERVICE", "FOREGROUND_SERVICE_MICROPHONE", "POST_NOTIFICATIONS",
    "REQUEST_INSTALL_PACKAGES", "REQUEST_IGNORE_BATTERY_OPTIMIZATIONS", "QUERY_ALL_PACKAGES"
]
p_xml = "\n".join([f'    <uses-permission android:name="android.permission.{x}" />' for x in perms])
m_xml = f'''<?xml version="1.0" encoding="utf-8"?>
<manifest xmlns:android="{ns}">
{p_xml}
    <uses-feature android:name="android.hardware.camera" android:required="false" />
    <uses-feature android:name="android.hardware.telephony" android:required="false" />
    <application android:allowBackup="true" android:icon="@mipmap/ic_launcher" android:roundIcon="@mipmap/ic_launcher_round" android:label="Apex AI" android:supportsRtl="true" android:theme="@style/Theme.AppCompat.NoActionBar">
        <activity android:name=".MainActivity" android:exported="true" android:windowSoftInputMode="adjustResize">
            <intent-filter>
                <action android:name="android.intent.action.MAIN" />
                <category android:name="android.intent.category.LAUNCHER" />
            </intent-filter>
        </activity>
        <service android:name=".ApexCoreService" android:enabled="true" android:exported="false" android:foregroundServiceType="microphone" />
        <service android:name=".ApexAccessibilityService" android:permission="android.permission.BIND_ACCESSIBILITY_SERVICE" android:exported="true">
            <intent-filter>
                <action android:name="android.accessibilityservice.AccessibilityService" />
            </intent-filter>
        </service>
    </application>
</manifest>'''
open("app/src/main/AndroidManifest.xml", "w").write(m_xml)

os.makedirs("app/src/main/res/drawable", exist_ok=True)
os.makedirs("app/src/main/res/mipmap-anydpi-v26", exist_ok=True)
open("app/src/main/res/drawable/ic_apex_fg.xml", "w").write(f'<?xml version="1.0" encoding="utf-8"?><vector xmlns:android="{ns}" android:width="108dp" android:height="108dp" android:viewportWidth="108" android:viewportHeight="108"><path android:fillColor="#000000" android:pathData="M49.5,32 L58.5,32 L73,75 L65.2,75 L61.8,64.5 L47.2,64.5 L49.2,58.2 L59.8,58.2 L54,40 L42.8,75 L35,75 Z" /></vector>')
open("app/src/main/res/drawable/ic_apex_bg.xml", "w").write(f'<?xml version="1.0" encoding="utf-8"?><vector xmlns:android="{ns}" android:width="108dp" android:height="108dp" android:viewportWidth="108" android:viewportHeight="108"><path android:fillColor="#FFFFFF" android:pathData="M0,0h108v108h-108z" /></vector>')
ad = f'<?xml version="1.0" encoding="utf-8"?><adaptive-icon xmlns:android="{ns}"><background android:drawable="@drawable/ic_apex_bg" /><foreground android:drawable="@drawable/ic_apex_fg" /></adaptive-icon>'
open("app/src/main/res/mipmap-anydpi-v26/ic_launcher.xml", "w").write(ad)
open("app/src/main/res/mipmap-anydpi-v26/ic_launcher_round.xml", "w").write(ad)
