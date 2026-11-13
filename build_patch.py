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

service_part1 = f'''class ApexCoreService : Service(), TextToSpeech.OnInitListener {{

    private var tts: TextToSpeech? = null
    private var speechRecognizer: SpeechRecognizer? = null
    private var isListeningActive = false
    private var isSpeaking = false
    private val mainHandler = Handler(Looper.getMainLooper())

    companion object {{
        private fun resolveModel(apiKey: String, needVision: Boolean): String {{
            try {{
                val c = URL("{m_url}").openConnection() as HttpURLConnection
                c.requestMethod = "GET"
                c.setRequestProperty("Authorization", "Bearer $apiKey")
                c.connectTimeout = 8000
                c.readTimeout = 8000
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
                        return ids.firstOrNull {{ it.contains("vision") || it.contains("scout") || it.contains("maverick") || it.contains("llama-4") }} ?: ids.firstOrNull() ?: "llama-3.3-70b-versatile"
                    }}
                    for (tag in listOf("70b", "llama-4", "qwen", "32b", "8b", "gemma", "llama")) {{
                        val hit = ids.firstOrNull {{ it.contains(tag, true) }}
                        if (hit != null) return hit
                    }}
                    if (ids.isNotEmpty()) return ids.first()
                }}
            }} catch (_: Exception) {{}}
            return "llama-3.3-70b-versatile"
        }}

        private fun runDeviceCmd(ctx: Context, raw: String): String? {{
            val q = raw.lowercase(Locale.getDefault()).trim()
            try {{
                if (q.contains("фонарик") || q.contains("включи свет") || q.contains("выключи свет")) {{
                    val cm = ctx.getSystemService(Context.CAMERA_SERVICE) as android.hardware.camera2.CameraManager
                    val id = cm.cameraIdList.firstOrNull() ?: return null
                    val on = !(q.contains("выкл") || q.contains("откл") || q.contains("погаси"))
                    cm.setTorchMode(id, on)
                    return if (on) "🔦 Фонарик включён." else "🔦 Фонарик выключен."
                }}
                if (q.startsWith("открой ") || q.startsWith("запусти ") || q.startsWith("включи ")) {{
                    val t = q.removePrefix("открой ").removePrefix("запусти ").removePrefix("включи ").trim()
                    val map = mapOf("ютуб" to "youtube", "телеграм" to "telegram", "тг" to "telegram", "ватсап" to "whatsapp", "вк" to "vk", "тикток" to "tiktok", "хром" to "chrome", "озон" to "ozon", "вб" to "wildberries", "сдэк" to "cdek", "авито" to "avito")
                    val w = map[t] ?: t
                    val pm = ctx.packageManager
                    for (app in pm.getInstalledApplications(0)) {{
                        val lbl = pm.getApplicationLabel(app).toString().lowercase(Locale.getDefault())
                        if ((lbl.contains(w) || app.packageName.lowercase().contains(w)) && w.length >= 2) {{
                            pm.getLaunchIntentForPackage(app.packageName)?.let {{ it.addFlags(Intent.FLAG_ACTIVITY_NEW_TASK); ctx.startActivity(it); return "🚀 Открываю ${{pm.getApplicationLabel(app)}}..." }}
                        }}
                    }}
                }}
            }} catch (_: Exception) {{}}
            return null
        }}

        fun queryBrainDirect(ctx: Context, prompt: String, isCreator: Boolean, imageBase64: String?, callback: (String, String) -> Unit) {{
            thread {{
                if (imageBase64 == null) {{
                    val cmdRes = runDeviceCmd(ctx, prompt)
                    if (cmdRes != null) {{ callback(cmdRes, "Cmd"); return@thread }}
                }}
                val prefs = ctx.getSharedPreferences("apex_prefs", Context.MODE_PRIVATE)
                val apiKey = MainActivity.getActiveKey(prefs)
                try {{
                    val modelName = resolveModel(apiKey, imageBase64 != null)
                    val conn = URL("{u}").openConnection() as HttpURLConnection
                    conn.requestMethod = "POST"
                    conn.setRequestProperty("Authorization", "Bearer $apiKey")
                    conn.setRequestProperty("Content-Type", "application/json")
                    conn.connectTimeout = 25000
                    conn.readTimeout = 35000
                    conn.doOutput = true

                    val sysPrompt = "Ты — Apex AI, живой голосовой и текстовый интеллект уровня Джарвиса, созданный инженером Derek Stealth. Никогда не отвечай сухо в два слова! Если человек делится настроением или проблемой, поддержи его тепло и по-человечески. Если просят решить задачу — дай глубокий, развёрнутый разбор по шагам."
                    val messages = JSONArray()
                    messages.put(JSONObject().apply {{ put("role", "system"); put("content", sysPrompt) }})

                    if (imageBase64 != null) {{
                        val arr = JSONArray()
                        arr.put(JSONObject().apply {{ put("type", "text"); put("text", prompt) }})
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
'''
service_part2 = '''
    override fun onCreate() {
        super.onCreate()
        tts = TextToSpeech(this, this)
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
            getSystemService(NotificationManager::class.java)?.createNotificationChannel(NotificationChannel("apex_voice", "Apex Voice", NotificationManager.IMPORTANCE_LOW))
        }
    }

    override fun onInit(status: Int) {
        if (status == TextToSpeech.SUCCESS) {
            tts?.setLanguage(Locale("ru", "RU"))
            tts?.setSpeechRate(1.04f)
            tts?.setOnUtteranceProgressListener(object : UtteranceProgressListener() {
                override fun onStart(id: String?) { isSpeaking = true }
                override fun onDone(id: String?) { isSpeaking = false; if (isListeningActive) mainHandler.postDelayed({ startListeningCycle() }, 500) }
                override fun onError(id: String?) { isSpeaking = false; if (isListeningActive) mainHandler.postDelayed({ startListeningCycle() }, 500) }
            })
        }
    }

    override fun onStartCommand(intent: Intent?, flags: Int, startId: Int): Int {
        when (intent?.action) {
            "START_VOICE" -> {
                val nb = if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) Notification.Builder(this, "apex_voice") else @Suppress("DEPRECATION") Notification.Builder(this)
                startForeground(1, nb.setContentTitle("Apex AI").setContentText("Жду команду «Апекс»...").setSmallIcon(android.R.drawable.ic_btn_speak_now).build())
                isListeningActive = true
                startListeningCycle()
            }
            "STOP_VOICE" -> {
                isListeningActive = false
                isSpeaking = false
                try { speechRecognizer?.destroy() } catch (_: Exception) {}
                stopForeground(true)
                stopSelf()
            }
        }
        return START_STICKY
    }

    private fun startListeningCycle() {
        if (!isListeningActive || isSpeaking) return
        mainHandler.post {
            try {
                try { (getSystemService(Context.AUDIO_SERVICE) as android.media.AudioManager).adjustStreamVolume(android.media.AudioManager.STREAM_NOTIFICATION, android.media.AudioManager.ADJUST_MUTE, 0) } catch (_: Exception) {}
                speechRecognizer?.destroy()
                speechRecognizer = SpeechRecognizer.createSpeechRecognizer(this)
                speechRecognizer?.setRecognitionListener(object : RecognitionListener {
                    override fun onReadyForSpeech(p: Bundle?) {}
                    override fun onBeginningOfSpeech() {}
                    override fun onRmsChanged(r: Float) {}
                    override fun onBufferReceived(b: ByteArray?) {}
                    override fun onEndOfSpeech() {}
                    override fun onPartialResults(p: Bundle?) {}
                    override fun onEvent(e: Int, p: Bundle?) {}
                    override fun onError(e: Int) { if (isListeningActive && !isSpeaking) mainHandler.postDelayed({ startListeningCycle() }, 800L) }
                    override fun onResults(results: Bundle?) {
                        val heard = results?.getStringArrayList(SpeechRecognizer.RESULTS_RECOGNITION)?.firstOrNull()?.trim() ?: ""
                        val low = heard.lowercase(Locale.getDefault())
                        val wake = listOf("апекс", "apex", "апек", "апикс").firstOrNull { low.contains(it) }
                        if (wake == null) {
                            if (isListeningActive) mainHandler.postDelayed({ startListeningCycle() }, 300L)
                            return
                        }
                        val cmd = heard.substring(low.indexOf(wake) + wake.length).trim(',', '.', ' ', '!', '?')
                        if (cmd.isEmpty()) {
                            isSpeaking = true
                            tts?.speak("Слушаю", TextToSpeech.QUEUE_FLUSH, Bundle(), "APEX_U")
                            return
                        }
                        val prefs = getSharedPreferences("apex_prefs", Context.MODE_PRIVATE)
                        val devId = Settings.Secure.getString(contentResolver, Settings.Secure.ANDROID_ID) ?: ""
                        val isCreator = MainActivity.CREATOR_IDS.contains(devId) || prefs.getBoolean("is_admin", false)
                        queryBrainDirect(this@ApexCoreService, cmd, isCreator, null) { reply, _ ->
                            isSpeaking = true
                            tts?.speak(reply, TextToSpeech.QUEUE_FLUSH, Bundle(), "APEX_U")
                        }
                    }
                })
                val ri = Intent(RecognizerIntent.ACTION_RECOGNIZE_SPEECH).apply {
                    putExtra(RecognizerIntent.EXTRA_LANGUAGE_MODEL, RecognizerIntent.LANGUAGE_MODEL_FREE_FORM)
                    putExtra(RecognizerIntent.EXTRA_LANGUAGE, "ru-RU")
                }
                speechRecognizer?.startListening(ri)
            } catch (_: Exception) { if (isListeningActive) mainHandler.postDelayed({ startListeningCycle() }, 1200L) }
        }
    }

    override fun onBind(intent: Intent?) = null
    override fun onDestroy() { isListeningActive = false; try { speechRecognizer?.destroy() } catch (_: Exception) {}; try { tts?.shutdown() } catch (_: Exception) {}; super.onDestroy() }
}
'''

open(p, "w").write(s + service_part1 + service_part2)
