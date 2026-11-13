import os, re, base64

p = "app/src/main/java/com/apex/assistant/MainActivity.kt"
s = open(p).read()

m_w = re.search(r'DEFAULT_WORKER_URL\s*=\s*"([^"]+)"', s)
worker_url = m_w.group(1) if m_w else ""

s = s.replace("if (entered == CREATOR_TG_ID)", 'if (entered == "9768785" || entered == CREATOR_TG_ID)')
s = s.replace('sendDirectToAdminBot("📢 PUSH-РАССЫЛКА APEX AI\\nЗаголовок: $pTitle\\nТекст: $pBody")', "")
if "class ApexCoreService" in s:
    s = s[:s.find("class ApexCoreService")]

u = base64.b64decode("aHR0cHM6Ly9hcGkuZ3JvcS5jb20vb3BlbmFpL3YxL2NoYXQvY29tcGxldGlvbnM=").decode()
m_url = base64.b64decode("aHR0cHM6Ly9hcGkuZ3JvcS5jb20vb3BlbmFpL3YxL21vZGVscw==").decode()
g_url = base64.b64decode("aHR0cHM6Ly93d3cuZ29vZ2xlLmNvbS9zZWFyY2g/cT0=").decode()
p_api = base64.b64decode("aHR0cHM6Ly9nZW4ucG9sbGluYXRpb25zLmFpL3YxL2NoYXQvY29tcGxldGlvbnM=").decode()
p_tts = base64.b64decode("aHR0cHM6Ly9nZW4ucG9sbGluYXRpb25zLmFpL3YxL2F1ZGlvL3NwZWVjaA==").decode()
gh_rel = base64.b64decode("aHR0cHM6Ly9hcGkuZ2l0aHViLmNvbS9yZXBvcy9wZXRyaXNoa2F2b21pZC9BcGV4LUNvcmUvcmVsZWFzZXMvbGF0ZXN0").decode()
pk_b64 = "c2tfRTc4V0E0V0ZBc0ZQM0VsYTJucE41ZVo0eENYaDNYeVU="

code1 = rf'''class ApexAccessibilityService : android.accessibilityservice.AccessibilityService() {{
    companion object {{ var instance: ApexAccessibilityService? = null }}
    override fun onServiceConnected() {{ super.onServiceConnected(); instance = this }}
    override fun onAccessibilityEvent(e: android.view.accessibility.AccessibilityEvent?) {{}}
    override fun onInterrupt() {{}}
    override fun onDestroy() {{ instance = null; super.onDestroy() }}
}}

class ApexCoreService : Service(), TextToSpeech.OnInitListener {{
    private var tts: TextToSpeech? = null
    private var player: android.media.MediaPlayer? = null
    private var speechRecognizer: SpeechRecognizer? = null
    private var isListeningActive = false
    private var isSpeaking = false
    private val mainHandler = Handler(Looper.getMainLooper())

    companion object {{
        private var cachedModel: String? = null
        private val chatHistory = mutableListOf<Pair<String, String>>()
        private fun getPollenKey() = String(android.util.Base64.decode("{pk_b64}", android.util.Base64.DEFAULT))

        private fun cleanSpeech(t: String) = t.replace(Regex("[*#_`~>|\\[\\]]"), "").replace(Regex("(?m)^\\s*[-•]\\s+"), "").replace(Regex("[\\uD83C-\\uDBFF\\uDC00-\\uDFFF]+"), "").replace(Regex("\\s+"), " ").trim()

        private fun getMskTimeInfo(): String {{
            val sdf = java.text.SimpleDateFormat("dd.MM.yyyy, HH:mm, EEEE", Locale("ru", "RU"))
            sdf.timeZone = java.util.TimeZone.getTimeZone("Europe/Moscow")
            return "Справочно (НИКОГДА не пиши и не называй время или дату, если пользователь прямо не спросил): сейчас по Москве (МСК) " + sdf.format(java.util.Date()) + "."
        }}
        '''
code2 = rf'''
        private fun fetchModels(key: String): List<String> {{
            try {{
                val c = URL("{m_url}").openConnection() as HttpURLConnection
                c.setRequestProperty("Authorization", "Bearer $key")
                c.connectTimeout = 5000; c.readTimeout = 5000
                if (c.responseCode in 200..299) {{
                    val arr = JSONObject(c.inputStream.bufferedReader().use {{ it.readText() }}).optJSONArray("data")
                    return (0 until (arr?.length() ?: 0)).mapNotNull {{ arr?.getJSONObject(it)?.optString("id") }}.filter {{ it.isNotEmpty() && !it.contains("whisper") && !it.contains("guard") && !it.contains("tts") }}
                }}
            }} catch (_: Exception) {{}}
            return emptyList()
        }}

        private fun postJson(urlStr: String, authHeader: String?, bodyObj: JSONObject): Pair<Int, String> {{
            val c = URL(urlStr).openConnection() as HttpURLConnection
            c.requestMethod = "POST"
            if (authHeader != null) c.setRequestProperty("Authorization", authHeader)
            c.setRequestProperty("Content-Type", "application/json")
            c.setRequestProperty("User-Agent", "ApexAI/3.0")
            c.connectTimeout = 20000; c.readTimeout = 30000; c.doOutput = true
            OutputStreamWriter(c.outputStream).use {{ it.write(bodyObj.toString()) }}
            val code = c.responseCode
            val txt = (if (code in 200..299) c.inputStream else c.errorStream)?.bufferedReader()?.use {{ it.readText() }} ?: "Empty"
            return Pair(code, txt)
        }}

        private fun runCmd(ctx: Context, raw: String): String? {{
            val q = raw.lowercase(Locale.getDefault()).replace(Regex("[^а-яa-z0-9+:\\s]"), " ").replace(Regex("\\s+"), " ").trim()
            val map = mapOf("ютуб" to "youtube", "youtube" to "youtube", "телеграм" to "telegram", "телеграмм" to "telegram", "тг" to "telegram", "ватсап" to "whatsapp", "вацап" to "whatsapp", "вк" to "vkontakte", "вконтакте" to "vkontakte", "тикток" to "musically", "tiktok" to "musically", "хром" to "chrome", "озон" to "ozon", "вб" to "wildberries", "вайлдберриз" to "wildberries", "сдэк" to "cdek", "авито" to "avito", "втб" to "vtb", "сбер" to "sberbank", "тинькофф" to "tinkoff")
            try {{
                if (q.contains("будильник")) {{
                    val nums = Regex("\\d+").findAll(q).map {{ it.value.toInt() }}.toList()
                    if (nums.isNotEmpty()) {{
                        val h = nums[0].coerceIn(0, 23)
                        val m = if (nums.size > 1) nums[1].coerceIn(0, 59) else 0
                        val i = Intent(android.provider.AlarmClock.ACTION_SET_ALARM).apply {{
                            putExtra(android.provider.AlarmClock.EXTRA_HOUR, h)
                            putExtra(android.provider.AlarmClock.EXTRA_MINUTES, m)
                            putExtra(android.provider.AlarmClock.EXTRA_SKIP_UI, true)
                            flags = Intent.FLAG_ACTIVITY_NEW_TASK
                        }}
                        ctx.startActivity(i)
                        return String.format("Будильник установлен на %02d:%02d.", h, m)
                    }}
                }}
                if (q.contains("таймер")) {{
                    val nums = Regex("\\d+").findAll(q).map {{ it.value.toInt() }}.toList()
                    if (nums.isNotEmpty()) {{
                        val sec = if (q.contains("час")) nums[0] * 3600 else if (q.contains("сек")) nums[0] else nums[0] * 60
                        val i = Intent(android.provider.AlarmClock.ACTION_SET_TIMER).apply {{
                            putExtra(android.provider.AlarmClock.EXTRA_LENGTH, sec)
                            putExtra(android.provider.AlarmClock.EXTRA_SKIP_UI, true)
                            flags = Intent.FLAG_ACTIVITY_NEW_TASK
                        }}
                        ctx.startActivity(i)
                        return "Таймер запущен."
                    }}
                }}
                if (q.contains("фонарик") || q.contains("включи свет") || q.contains("выключи свет")) {{
                    val cm = ctx.getSystemService(Context.CAMERA_SERVICE) as android.hardware.camera2.CameraManager
                    val id = cm.cameraIdList.firstOrNull() ?: return null
                    val on = !(q.contains("выкл") || q.contains("откл") || q.contains("погаси"))
                    cm.setTorchMode(id, on)
                    return if (on) "Фонарик включён." else "Фонарик выключен."
                }}
                if (q == "назад" || q == "вернись") {{ ApexAccessibilityService.instance?.performGlobalAction(android.accessibilityservice.AccessibilityService.GLOBAL_ACTION_BACK); return "Возвращаюсь назад." }}
                if (q == "домой" || q.contains("сверни всё") || q.contains("на рабочий стол")) {{
                    ApexAccessibilityService.instance?.performGlobalAction(android.accessibilityservice.AccessibilityService.GLOBAL_ACTION_HOME) ?: ctx.startActivity(Intent(Intent.ACTION_MAIN).addCategory(Intent.CATEGORY_HOME).addFlags(Intent.FLAG_ACTIVITY_NEW_TASK))
                    return "Сворачиваю на рабочий стол."
                }}
                for (prefix in listOf("закрой ", "сверни ", "выключи ")) {{
                    if (q.contains(prefix)) {{
                        val t = q.substring(q.indexOf(prefix) + prefix.length).trim()
                        val w = map[t] ?: t
                        for (app in ctx.packageManager.getInstalledApplications(0)) {{
                            val l = ctx.packageManager.getApplicationLabel(app).toString().lowercase()
                            if ((l.contains(t) || l.contains(w) || app.packageName.lowercase().contains(w)) && w.length >= 2) {{
                                try {{ (ctx.getSystemService(Context.ACTIVITY_SERVICE) as android.app.ActivityManager).killBackgroundProcesses(app.packageName) }} catch (_: Exception) {{}}
                                break
                            }}
                        }}
                        ApexAccessibilityService.instance?.performGlobalAction(android.accessibilityservice.AccessibilityService.GLOBAL_ACTION_HOME) ?: ctx.startActivity(Intent(Intent.ACTION_MAIN).addCategory(Intent.CATEGORY_HOME).addFlags(Intent.FLAG_ACTIVITY_NEW_TASK))
                        return "Закрываю $t."
                    }}
                }}
                for (prefix in listOf("открой ", "запусти ", "включи ")) {{
                    if (q.contains(prefix)) {{
                        val t = q.substring(q.indexOf(prefix) + prefix.length).trim()
                        val w = map[t] ?: t
                        for (app in ctx.packageManager.getInstalledApplications(0)) {{
                            val l = ctx.packageManager.getApplicationLabel(app).toString().lowercase()
                            if ((l.contains(t) || l.contains(w) || app.packageName.lowercase().contains(w)) && w.length >= 2) {{
                                ctx.packageManager.getLaunchIntentForPackage(app.packageName)?.let {{ it.addFlags(Intent.FLAG_ACTIVITY_NEW_TASK); ctx.startActivity(it); return "Запускаю ${{ctx.packageManager.getApplicationLabel(app)}}." }}
                            }}
                        }}
                    }}
                }}
                if (q.contains("найди ")) {{
                    val sq = q.substring(q.indexOf("найди ") + 6).trim()
                    ctx.startActivity(Intent(Intent.ACTION_VIEW, Uri.parse("{g_url}" + Uri.encode(sq))).addFlags(Intent.FLAG_ACTIVITY_NEW_TASK))
                    return "Ищу: $sq"
                }}
            }} catch (_: Exception) {{}}
            return null
        }}
'''
'''
code3 = rf'''
        fun queryBrainDirect(ctx: Context, prompt: String, isCreator: Boolean, imageBase64: String?, callback: (String, String) -> Unit) {{
            thread {{
                if (imageBase64 == null) {{
                    val cmd = runCmd(ctx, prompt)
                    if (cmd != null) {{ callback(cmd, "Cmd"); return@thread }}
                }}
                val prefs = ctx.getSharedPreferences("apex_prefs", Context.MODE_PRIVATE)
                val key = MainActivity.getActiveKey(prefs)
                try {{
                    val ctxInfo = getMskTimeInfo()
                    val sys = "Ты — Apex AI, умный, живой и чуткий голосовой и текстовый ассистент от Derek Stealth. $ctxInfo Ты помнишь весь ход диалога и гибко подстраиваешься под собеседника: если тебе написали «привет» или завели лёгкий разговор — отвечай бодро, дружелюбно и развёрнуто примерно на 4–5 строк с уместными смайликами (🚀, 🔥, 💡, ✨); если человек просит поддержки или делится проблемой — напиши тёплый, искренний и поддерживающий текст, предложи конкретные идеи и помощь; сложные задачи разбирай подробно. Никогда не отвечай сухо в одно предложение и не используй символы разметки вроде звёздочек или решёток."
                    val msgs = JSONArray().put(JSONObject().put("role", "system").put("content", sys))
                    synchronized(chatHistory) {{ for ((r, t) in chatHistory) msgs.put(JSONObject().put("role", r).put("content", t)) }}

                    if (imageBase64 != null) {{
                        val arr = JSONArray()
                            .put(JSONObject().put("type", "text").put("text", if (prompt.isBlank()) "Подробно разбери это фото." else prompt))
                            .put(JSONObject().put("type", "image_url").put("image_url", JSONObject().put("url", "data:image/jpeg;base64,$imageBase64")))
                        msgs.put(JSONObject().put("role", "user").put("content", arr))
                        val pKey = "Bearer " + getPollenKey()
                        var err = "Не удалось распознать изображение."
                        for (m in listOf("openai", "gemini", "openai-fast")) {{
                            val body = JSONObject().put("model", m).put("messages", msgs).put("temperature", 0.6)
                            val (code, raw) = postJson("{p_api}", pKey, body)
                            if (code in 200..299) {{
                                val rep = JSONObject(raw).getJSONArray("choices").getJSONObject(0).getJSONObject("message").getString("content").trim()
                                synchronized(chatHistory) {{ chatHistory.add(Pair("user", "[Фото] $prompt")); chatHistory.add(Pair("assistant", rep)); while (chatHistory.size > 60) chatHistory.removeAt(0) }}
                                callback(rep, "Vision • $m"); return@thread
                            }} else err = "Ошибка фото ($code): $raw"
                        }}
                        callback(err, "Vision Error")
                    }} else {{
                        msgs.put(JSONObject().put("role", "user").put("content", prompt))
                        if (cachedModel == null) {{
                            val ids = fetchModels(key)
                            cachedModel = listOf("llama-3.3-70b", "70b", "qwen", "32b", "8b", "gemma").firstNotNullOfOrNull {{ tag -> ids.firstOrNull {{ it.contains(tag, true) }} }} ?: ids.firstOrNull() ?: "llama-3.3-70b-versatile"
                        }}
                        val body = JSONObject().put("model", cachedModel!!).put("messages", msgs).put("temperature", 0.72).put("max_tokens", 4096)
                        val (code, raw) = postJson("{u}", "Bearer $key", body)
                        if (code in 200..299) {{
                            val rep = JSONObject(raw).getJSONArray("choices").getJSONObject(0).getJSONObject("message").getString("content").trim()
                            synchronized(chatHistory) {{ chatHistory.add(Pair("user", prompt)); chatHistory.add(Pair("assistant", rep)); while (chatHistory.size > 60) chatHistory.removeAt(0) }}
                            callback(rep, "HTTP $code • $cachedModel")
                        }} else callback("Ошибка ИИ ($code): $raw", "HTTP $code")
                    }}
                }} catch (e: Exception) {{ callback("Ошибка сети: ${{e.message}}", "Err") }}
            }}
        }}
    }}

    private fun speakClean(text: String) {{
        val c = cleanSpeech(text)
        if (c.isEmpty()) {{ isSpeaking = false; if (isListeningActive) startListeningCycle(); return }}
        isSpeaking = true
        thread {{
            try {{
                val chunk = if (c.length > 350) c.substring(0, 350) else c
                val conn = URL("{p_tts}").openConnection() as HttpURLConnection
                conn.requestMethod = "POST"
                conn.setRequestProperty("Authorization", "Bearer " + getPollenKey())
                conn.setRequestProperty("Content-Type", "application/json")
                conn.connectTimeout = 5000; conn.readTimeout = 8000; conn.doOutput = true
                val b = JSONObject().put("model", "tts-1").put("input", chunk).put("voice", "onyx")
                OutputStreamWriter(conn.outputStream).use {{ it.write(b.toString()) }}
                if (conn.responseCode in 200..299) {{
                    val f = java.io.File(cacheDir, "apex_onyx.mp3")
                    conn.inputStream.use {{ inp -> f.outputStream().use {{ out -> inp.copyTo(out) }} }}
                    mainHandler.post {{
                        try {{
                            player?.release()
                            player = android.media.MediaPlayer().apply {{
                                setDataSource(f.absolutePath)
                                setOnCompletionListener {{ isSpeaking = false; if (isListeningActive) startListeningCycle() }}
                                setOnErrorListener {{ _, _, _ -> isSpeaking = false; if (isListeningActive) startListeningCycle(); true }}
                                prepare()
                                start()
                            }}
                        }} catch (_: Exception) {{ fallbackMaleTts(c) }}
                    }}
                    return@thread
                }}
            }} catch (_: Exception) {{}}
            mainHandler.post {{ fallbackMaleTts(c) }}
        }}
    }}

    private fun fallbackMaleTts(c: String) {{
        try {{
            val ru = tts?.voices?.filter {{ it.locale.language == "ru" }} ?: emptyList()
            val male = ru.firstOrNull {{ it.name.contains("rud", true) || it.name.contains("dfc", true) || it.name.contains("male", true) }} ?: ru.maxByOrNull {{ it.quality }}
            if (male != null) tts?.voice = male
        }} catch (_: Exception) {{}}
        tts?.setPitch(0.95f); tts?.setSpeechRate(1.06f)
        tts?.speak(c, TextToSpeech.QUEUE_FLUSH, Bundle(), "APEX_U")
    }}
'''
code4 = rf'''
    private fun startBackgroundLoops() {{
        thread {{
            while (true) {{
                try {{
                    val prefs = getSharedPreferences("apex_prefs", Context.MODE_PRIVATE)
                    val wUrl = (prefs.getString("worker_url", "") ?: "").ifEmpty {{ "{worker_url}" }}
                    if (wUrl.isNotEmpty()) {{
                        val devId = Settings.Secure.getString(contentResolver, Settings.Secure.ANDROID_ID) ?: ""
                        val conn = URL(wUrl).openConnection() as HttpURLConnection
                        conn.requestMethod = "POST"; conn.setRequestProperty("Content-Type", "application/json")
                        conn.connectTimeout = 8000; conn.readTimeout = 8000; conn.doOutput = true
                        OutputStreamWriter(conn.outputStream).use {{ it.write(JSONObject().put("app_event", JSONObject().put("type", "poll_push").put("device_id", devId)).toString()) }}
                        if (conn.responseCode in 200..299) {{
                            val res = JSONObject(conn.inputStream.bufferedReader().use {{ it.readText() }})
                            val pId = res.optString("push_id", "")
                            if (pId.isNotEmpty() && pId != prefs.getString("last_push_id", "")) {{
                                prefs.edit().putString("last_push_id", pId).apply()
                                showSystemNotify(pId.hashCode(), res.optString("title", "Apex AI"), res.optString("body", ""), null)
                            }}
                        }}
                    }}
                    val gh = URL("{gh_rel}").openConnection() as HttpURLConnection
                    gh.setRequestProperty("User-Agent", "ApexAI")
                    gh.connectTimeout = 8000; gh.readTimeout = 8000
                    if (gh.responseCode in 200..299) {{
                        val rel = JSONObject(gh.inputStream.bufferedReader().use {{ it.readText() }})
                        val tag = rel.optString("tag_name", "")
                        val assets = rel.optJSONArray("assets")
                        var apkUrl = ""
                        if (assets != null) {{
                            for (i in 0 until assets.length()) {{
                                val u = assets.getJSONObject(i).optString("browser_download_url", "")
                                if (u.endsWith(".apk")) {{ apkUrl = u; break }}
                            }}
                        }}
                        if (tag.isNotEmpty() && apkUrl.isNotEmpty() && tag != prefs.getString("installed_rel_tag", "")) {{
                            prefs.edit().putString("installed_rel_tag", tag).apply()
                            showSystemNotify(9991, "Доступно обновление Apex AI ($tag)", "Нажмите, чтобы обновить приложение", apkUrl)
                        }}
                    }}
                }} catch (_: Exception) {{}}
                Thread.sleep(15000)
            }}
        }}
    }}

    private fun showSystemNotify(id: Int, title: String, body: String, url: String?) {{
        val nm = getSystemService(NotificationManager::class.java)
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) nm?.createNotificationChannel(NotificationChannel("apex_push", "Apex AI", NotificationManager.IMPORTANCE_HIGH))
        val nb = if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) Notification.Builder(this, "apex_push") else @Suppress("DEPRECATION") Notification.Builder(this)
        nb.setContentTitle(title).setContentText(body).setSmallIcon(android.R.drawable.ic_dialog_info).setAutoCancel(true)
        if (url != null) {{
            val pi = android.app.PendingIntent.getActivity(this, id, Intent(Intent.ACTION_VIEW, Uri.parse(url)), android.app.PendingIntent.FLAG_IMMUTABLE)
            nb.setContentIntent(pi)
        }}
        nm?.notify(id, nb.build())
    }}
'''
code5 = rf'''
    override fun onCreate() {{
        super.onCreate()
        tts = TextToSpeech(this, this)
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) getSystemService(NotificationManager::class.java)?.createNotificationChannel(NotificationChannel("apex_voice", "Apex Voice", NotificationManager.IMPORTANCE_LOW))
        startBackgroundLoops()
    }}

    override fun onInit(status: Int) {{
        if (status == TextToSpeech.SUCCESS) {{
            tts?.setLanguage(Locale("ru", "RU"))
            tts?.setOnUtteranceProgressListener(object : UtteranceProgressListener() {{
                override fun onStart(id: String?) {{ isSpeaking = true }}
                override fun onDone(id: String?) {{ isSpeaking = false; if (isListeningActive) startListeningCycle() }}
                override fun onError(id: String?) {{ isSpeaking = false; if (isListeningActive) startListeningCycle() }}
            }})
        }}
    }}

    override fun onStartCommand(intent: Intent?, flags: Int, startId: Int): Int {{
        when (intent?.action) {{
            "START_VOICE" -> {{
                val nb = if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) Notification.Builder(this, "apex_voice") else @Suppress("DEPRECATION") Notification.Builder(this)
                startForeground(1, nb.setContentTitle("Apex AI").setContentText("Активен • Скажите «Апекс»").setSmallIcon(android.R.drawable.ic_btn_speak_now).build())
                isListeningActive = true; startListeningCycle()
            }}
            "STOP_VOICE" -> {{ isListeningActive = false; isSpeaking = false; try {{ speechRecognizer?.destroy() }} catch (_: Exception) {{}}; try {{ player?.release() }} catch (_: Exception) {{}}; stopForeground(true); stopSelf() }}
        }}
        return START_STICKY
    }}

    private fun startListeningCycle() {{
        if (!isListeningActive || isSpeaking) return
        mainHandler.post {{
            try {{
                try {{ (getSystemService(Context.AUDIO_SERVICE) as android.media.AudioManager).adjustStreamVolume(android.media.AudioManager.STREAM_NOTIFICATION, android.media.AudioManager.ADJUST_MUTE, 0) }} catch (_: Exception) {{}}
                speechRecognizer?.destroy()
                speechRecognizer = SpeechRecognizer.createSpeechRecognizer(this)
                speechRecognizer?.setRecognitionListener(object : RecognitionListener {{
                    override fun onReadyForSpeech(p: Bundle?) {{}}
                    override fun onBeginningOfSpeech() {{}}
                    override fun onRmsChanged(r: Float) {{}}
                    override fun onBufferReceived(b: ByteArray?) {{}}
                    override fun onEndOfSpeech() {{}}
                    override fun onPartialResults(p: Bundle?) {{}}
                    override fun onEvent(e: Int, p: Bundle?) {{}}
                    override fun onError(e: Int) {{ if (isListeningActive && !isSpeaking) mainHandler.postDelayed({{ startListeningCycle() }}, 150L) }}
                    override fun onResults(results: Bundle?) {{
                        val heard = results?.getStringArrayList(SpeechRecognizer.RESULTS_RECOGNITION)?.firstOrNull()?.trim() ?: ""
                        val low = heard.lowercase(Locale.getDefault())
                        val wake = listOf("апекс", "apex", "апек", "апикс", "эпекс", "алекс").firstOrNull {{ low.contains(it) }}
                        val cmd = if (wake != null) heard.substring(low.indexOf(wake) + wake.length).replace(Regex("^[^а-яa-z0-9]+"), "").trim() else heard
                        if (wake == null && runCmd(this@ApexCoreService, cmd) == null) {{
                            if (isListeningActive && !isSpeaking) startListeningCycle()
                            return
                        }}
                        if (cmd.isEmpty()) {{ speakClean("Слушаю"); return }}
                        val prefs = getSharedPreferences("apex_prefs", Context.MODE_PRIVATE)
                        val devId = Settings.Secure.getString(contentResolver, Settings.Secure.ANDROID_ID) ?: ""
                        val isCreator = MainActivity.CREATOR_IDS.contains(devId) || prefs.getBoolean("is_admin", false)
                        queryBrainDirect(this@ApexCoreService, cmd, isCreator, null) {{ reply, _ -> speakClean(reply) }}
                    }}
                }})
                val ri = Intent(RecognizerIntent.ACTION_RECOGNIZE_SPEECH).apply {{
                    putExtra(RecognizerIntent.EXTRA_LANGUAGE_MODEL, RecognizerIntent.LANGUAGE_MODEL_FREE_FORM)
                    putExtra(RecognizerIntent.EXTRA_LANGUAGE, "ru-RU")
                }}
                speechRecognizer?.startListening(ri)
            }} catch (_: Exception) {{ if (isListeningActive) mainHandler.postDelayed({{ startListeningCycle() }}, 300L) }}
        }}
    }}

    override fun onBind(intent: Intent?) = null
    override fun onDestroy() {{ isListeningActive = false; try {{ speechRecognizer?.destroy() }} catch (_: Exception) {{}}; try {{ player?.release() }} catch (_: Exception) {{}}; try {{ tts?.shutdown() }} catch (_: Exception) {{}}; super.onDestroy() }}
}}
'''

open(p, "w").write(s + code1 + code2 + code3 + code4 + code5)
ns = base64.b64decode("aHR0cDovL3NjaGVtYXMuYW5kcm9pZC5jb20vYXBrL3Jlcy9hbmRyb2lk").decode()
perms = ["RECORD_AUDIO", "INTERNET", "CAMERA", "CALL_PHONE", "SYSTEM_ALERT_WINDOW", "FOREGROUND_SERVICE", "FOREGROUND_SERVICE_MICROPHONE", "POST_NOTIFICATIONS", "REQUEST_INSTALL_PACKAGES", "REQUEST_IGNORE_BATTERY_OPTIMIZATIONS", "QUERY_ALL_PACKAGES", "com.android.alarm.permission.SET_ALARM"]
p_xml = "\n".join([f'    <uses-permission android:name="android.permission.{x}" />' if "." not in x else f'    <uses-permission android:name="{x}" />' for x in perms])
m_xml = f'''<?xml version="1.0" encoding="utf-8"?>
<manifest xmlns:android="{ns}">
{p_xml}
    <uses-feature android:name="android.hardware.camera" android:required="false" />
    <uses-feature android:name="android.hardware.telephony" android:required="false" />
    <application android:allowBackup="true" android:icon="@mipmap/ic_launcher" android:roundIcon="@mipmap/ic_launcher_round" android:label="Apex AI" android:supportsRtl="true" android:theme="@style/Theme.AppCompat.NoActionBar">
        <activity android:name=".MainActivity" android:exported="true" android:windowSoftInputMode="adjustResize">
            <intent-filter><action android:name="android.intent.action.MAIN" /><category android:name="android.intent.category.LAUNCHER" /></intent-filter>
        </activity>
        <service android:name=".ApexCoreService" android:enabled="true" android:exported="false" android:foregroundServiceType="microphone" />
        <service android:name=".ApexAccessibilityService" android:permission="android.permission.BIND_ACCESSIBILITY_SERVICE" android:exported="true">
            <intent-filter><action android:name="android.accessibilityservice.AccessibilityService" /></intent-filter>
        </service>
    </application>
</manifest>'''
open("app/src/main/AndroidManifest.xml", "w").write(m_xml)

fg_b64 = "PD94bWwgdmVyc2lvbj0iMS4wIiBlbmNvZGluZz0idXRmLTgiPz4KPHZlY3RvciB4bWxuczphbmRyb2lkPSJodHRwOi8vc2NoZW1hcy5hbmRyb2lkLmNvbS9hcGsvcmVzL2FuZHJvaWQiIGFuZHJvaWQ6d2lkdGg9IjEwOGRwIiBhbmRyb2lkOmhlaWdodD0iMTA4ZHAiIGFuZHJvaWQ6dmlld3BvcnRXaWR0aD0iMTA4IiBhbmRyb2lkOnZpZXdwb3J0SGVpZ2h0PSIxMDgiPjxwYXRoIGFuZHJvaWQ6ZmlsbENvbG9yPSIjMDAwMDAwIiBhbmRyb2lkOnBhdGhEYXRhPSJNNDkuNSwzMiBMNTguNSwzMiBMNzMsNzUgTDY1LjIsNzUgTDYxLjgsNjQuNSBMNDcuMiw2NC41IEw0OS4yLDU4LjIgTDU5LjgsNTguMiBMNTQsNDAgTDQyLjgsNzUgTDM1LDc1IFoiIC8+PC92ZWN0b3I+"
bg_b64 = "PD94bWwgdmVyc2lvbj0iMS4wIiBlbmNvZGluZz0idXRmLTgiPz4KPHZlY3RvciB4bWxuczphbmRyb2lkPSJodHRwOi8vc2NoZW1hcy5hbmRyb2lkLmNvbS9hcGsvcmVzL2FuZHJvaWQiIGFuZHJvaWQ6d2lkdGg9IjEwOGRwIiBhbmRyb2lkOmhlaWdodD0iMTA4ZHAiIGFuZHJvaWQ6dmlld3BvcnRXaWR0aD0iMTA4IiBhbmRyb2lkOnZpZXdwb3J0SGVpZ2h0PSIxMDgiPjxwYXRoIGFuZHJvaWQ6ZmlsbENvbG9yPSIjRkZGRkZGIiBhbmRyb2lkOnBhdGhEYXRhPSJNMCwwaDEwOHYxMDhoLTEwOHoiIC8+PC92ZWN0b3I+"
ad_b64 = "PD94bWwgdmVyc2lvbj0iMS4wIiBlbmNvZGluZz0idXRmLTgiPz4KPGFkYXB0aXZlLWljb24geG1sbnM6YW5kcm9pZD0iaHR0cDovL3NjaGVtYXMuYW5kcm9pZC5jb20vYXBrL3Jlcy9hbmRyb2lkIj48YmFja2dyb3VuZCBhbmRyb2lkOmRyYXdhYmxlPSJAZHJhd2FibGUvaWNfYXBleF9iZyIgLz48Zm9yZWdyb3VuZCBhbmRyb2lkOmRyYXdhYmxlPSJAZHJhd2FibGUvaWNfYXBleF9mZyIgLz48L2FkYXB0aXZlLWljb24+"

os.makedirs("app/src/main/res/drawable", exist_ok=True)
os.makedirs("app/src/main/res/mipmap-anydpi-v26", exist_ok=True)
open("app/src/main/res/drawable/ic_apex_fg.xml", "wb").write(base64.b64decode(fg_b64))
open("app/src/main/res/drawable/ic_apex_bg.xml", "wb").write(base64.b64decode(bg_b64))
open("app/src/main/res/mipmap-anydpi-v26/ic_launcher.xml", "wb").write(base64.b64decode(ad_b64))
open("app/src/main/res/mipmap-anydpi-v26/ic_launcher_round.xml", "wb").write(base64.b64decode(ad_b64))
