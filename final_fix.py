import os, re

# 1. ПРАВИМ MANIFEST (ЧТОБЫ ANDROID НЕ БЛОКИРОВАЛ ФОНОВЫЙ МИКРОФОН, ГОЛОС И ПУШИ)
m_path = "app/src/main/AndroidManifest.xml"
if os.path.exists(m_path):
    mt = open(m_path, "r", encoding="utf-8").read()
    if "FOREGROUND_SERVICE_MICROPHONE" not in mt:
        mt = mt.replace("<application", '<uses-permission android:name="android.permission.FOREGROUND_SERVICE_MICROPHONE"/>\n    <uses-permission android:name="android.permission.POST_NOTIFICATIONS"/>\n    <application')

    open(m_path, "w", encoding="utf-8").write(mt)
    print("OK: Manifest updated")

# 2. ПРАВИМ ГОЛОС И ХАРАКТЕР В ApexCoreService.kt
svc_path = "app/src/main/java/com/apex/assistant/ApexCoreService.kt"
if os.path.exists(svc_path):
    sc = open(svc_path, "r", encoding="utf-8").read()
    sc = re.sub(r'в стиле Джарвиса[^."]*', 'созданный разработчиком Derek Stealth. Никогда не упоминай Джарвиса и не сравнивай себя с киногероями — ты уникальный и самостоятельный ИИ нового поколения', sc)
    sc = sc.replace('tts?.speak(chunks[i], mode, Bundle(), uttId)', 'tts?.speak(chunks[i], mode, null, uttId)')
    sc = sc.replace('val b = Bundle().apply { putInt(TextToSpeech.Engine.KEY_PARAM_STREAM, android.media.AudioManager.STREAM_MUSIC); putFloat(TextToSpeech.Engine.KEY_PARAM_VOLUME, 1.0f) }; tts?.speak(chunks[i], mode, b, uttId)', 'tts?.speak(chunks[i], mode, null, uttId)')
    # Принудительно включаем первый доступный голосовой движок в системе, если основной молчит
    sc = sc.replace(
        'override fun onInit(status: Int) {',
        '''override fun onInit(status: Int) {
        if (status != TextToSpeech.SUCCESS) {
            val engs = tts?.engines
            if (!engs.isNullOrEmpty()) {
                tts = TextToSpeech(this, this, engs[0].name)
                return
            }
        }'''
    )
    open(svc_path, "w", encoding="utf-8").write(sc)
    print("OK: ApexCoreService updated")

# 3. ПРАВИМ ПУШ И АНИМАЦИЮ "ДУМАЮ..." В MainActivity.kt
main_path = "app/src/main/java/com/apex/assistant/MainActivity.kt"
if os.path.exists(main_path):
    mc = open(main_path, "r", encoding="utf-8").read()
    # Мгновенный Push в шторку при нажатии кнопки в админке
    mc = mc.replace(
        'val pTitle =',
        '''try {
            val nm = getSystemService(android.app.NotificationManager::class.java)
            if (android.os.Build.VERSION.SDK_INT >= 26) nm?.createNotificationChannel(android.app.NotificationChannel("apex_push", "Apex AI", android.app.NotificationManager.IMPORTANCE_HIGH))
            val nb = if (android.os.Build.VERSION.SDK_INT >= 26) android.app.Notification.Builder(this, "apex_push") else @Suppress("DEPRECATION") android.app.Notification.Builder(this)
            nb.setContentTitle("Apex AI").setContentText("Тестовое Push-уведомление доставлено!").setSmallIcon(android.R.drawable.ic_dialog_info).setAutoCancel(true)
            nm?.notify(9991, nb.build())
        } catch (_: Exception) {}
        val pTitle ='''
    )
    # Анимация "Думаю •••" на любой пузырь загрузки
    mc = re.sub(r'("Печатает\.\.\."|"Генерирую\.\.\."|"Анализирую\.\.\."|"Думаю\.\.\."|"\.\.\.")', '"Думаю •  "', mc)
    mc = mc.replace(
        '"Думаю •  "',
        '''"Думаю •  ".also {
            android.os.Handler(android.os.Looper.getMainLooper()).postDelayed({
                val root = window.decorView.findViewById<android.view.ViewGroup>(android.R.id.content)
                fun findAndAnimate(v: android.view.View) {
                    if (v is android.widget.TextView && v.text.toString().startsWith("Думаю")) {
                        val frames = arrayOf("Думаю •  ", "Думаю  • ", "Думаю   •", "Думаю •••")
                        var st = 0
                        val h = android.os.Handler(android.os.Looper.getMainLooper())
                        h.post(object : Runnable {
                            override fun run() {
                                if (v.parent != null && v.text.toString().startsWith("Думаю")) {
                                    v.text = frames[st++ % frames.size]
                                    h.postDelayed(this, 300)
                                }
                            }
                        })
                    } else if (v is android.view.ViewGroup) {
                        for (i in 0 until v.childCount) findAndAnimate(v.getChildAt(i))
                    }
                }
                findAndAnimate(root)
            }, 80)
        }'''
    )
    open(main_path, "w", encoding="utf-8").write(mc)
    print("OK: MainActivity updated")
    import re

svc_path = "app/src/main/java/com/apex/assistant/ApexCoreService.kt"
sc = open(svc_path, "r", encoding="utf-8").read()

# 1. Точность по фото (не путать Тони Старка со Стивом Роджерсом)
sc = sc.replace(
    'prompt',
    '(if (imageBase64 != null) "Внимательно изучи лица, детали одежды и фон на фото, точно определяй людей и персонажей, не путай их. " + prompt else prompt)',
    1
)

# 2. Мгновенный "Стоп" в реальном времени (в onPartialResults за 0.1 сек)
sc = sc.replace(
    'override fun onPartialResults(partialResults: Bundle?) {}',
    '''override fun onPartialResults(partialResults: Bundle?) {
                        val part = partialResults?.getStringArrayList(SpeechRecognizer.RESULTS_RECOGNITION)?.firstOrNull()?.lowercase()?.trim() ?: ""
                        if (part.contains("стоп") || part.contains("хватит") || part.contains("замолчи") || part.contains("тихо")) {
                            try { tts?.stop() } catch (_: Exception) {}
                            isSpeaking = false
                            if (isListeningActive) startListeningCycle()
                        }
                    }'''
)

# 3. Мгновенный громкий голос при ответе + убираем лишние задержки
old_res = 'tts?.speak(reply, TextToSpeech.QUEUE_FLUSH, Bundle(), "APEX_UTTERANCE")'
new_res = '''try { speechRecognizer?.cancel(); speechRecognizer?.destroy(); speechRecognizer = null } catch (_: Exception) {}
                                isSpeaking = true
                                tts?.setPitch(0.86f)
                                tts?.setSpeechRate(1.04f)
                                tts?.speak(reply, TextToSpeech.QUEUE_FLUSH, null, "APEX_UTTERANCE")'''
sc = sc.replace(old_res, new_res)
sc = sc.replace('mainHandler.postDelayed({ startListeningCycle() }, 1200L)', 'mainHandler.postDelayed({ startListeningCycle() }, 250L)')
sc = sc.replace('mainHandler.postDelayed({ startListeningCycle() }, 900L)', 'mainHandler.postDelayed({ startListeningCycle() }, 200L)')
sc = sc.replace('mainHandler.postDelayed({ startListeningCycle() }, 700)', 'mainHandler.postDelayed({ startListeningCycle() }, 150)')

open(svc_path, "w", encoding="utf-8").write(sc)
# 4. ФИНАЛЬНЫЙ ПАТЧ: МГНОВЕННЫЙ ОТКЛИК, СТОП-СЛОВО, ДЖАРВИС И ТОЧНОЕ ЗРЕНИЕ
svc_path = "app/src/main/java/com/apex/assistant/ApexCoreService.kt"
if os.path.exists(svc_path):
    sc = open(svc_path, "r", encoding="utf-8").read()

    # Убираем обязательное слово "Апекс" — реагируем сразу на любую команду или вопрос
    sc = sc.replace(
        'if (matchedWake != null) {',
        'if (true) {'
    )
    sc = sc.replace(
        'val cmd = matchedPhrase.substring(low.indexOf(matchedWake) + matchedWake.length).replace(Regex("^[^а-яa-z0-9А-ЯA-Z]+"), "").trim()',
        'val cmd = if (matchedWake != null) matchedPhrase.substring(low.indexOf(matchedWake) + matchedWake.length).replace(Regex("^[^а-яa-z0-9А-ЯA-Z]+"), "").trim() else heard.trim()'
    )
    # Если сказали просто "Апекс" без команды — не тратим время на "Слушаю вас", сразу ждём команду
    sc = sc.replace(
        'if (cmd.isEmpty()) { speakClean("Слушаю вас."); return }',
        'if (cmd.isEmpty()) { if (isListeningActive && !isSpeaking) startListeningCycle(); return }'
    )

    # Ускоряем реакцию микрофона до 450 мс и настраиваем голос Джарвиса
    sc = sc.replace('tts?.setPitch(0.83f)', 'tts?.setPitch(0.80f)')
    sc = sc.replace('tts?.setSpeechRate(0.86f)', 'tts?.setSpeechRate(0.96f)')
    sc = sc.replace('EXTRA_SPEECH_INPUT_COMPLETE_SILENCE_LENGTH_MILLIS, 500', 'EXTRA_SPEECH_INPUT_COMPLETE_SILENCE_LENGTH_MILLIS, 450')

    # Переключаем распознавание фото на Groq Vision вместо слабого Pollinations
    old_vision = 'for (m in listOf("openai", "gemini", "openai-fast", "gpt-4o-mini")) {'
    new_vision = '''val visionOnlyMsgs = JSONArray().put(JSONObject().put("role", "user").put("content", arr))
                        for (vMod in listOf("meta-llama/llama-4-scout-17b-16e-instruct", "llama-3.2-90b-vision-preview")) {
                            val vBody = JSONObject().put("model", vMod).put("messages", visionOnlyMsgs).put("temperature", 0.25).put("max_tokens", 800)
                            val (vCode, vRaw) = postJson("https://groq.com", "Bearer $key", vBody)
                            if (vCode in 200..299) {
                                val rep = JSONObject(vRaw).getJSONArray("choices").getJSONObject(0).getJSONObject("message").getString("content").trim()
                                synchronized(chatHistory) {
                                    chatHistory.add(Pair("user", "[Фото] $prompt"))
                                    chatHistory.add(Pair("assistant", rep))
                                    while (chatHistory.size > 40) chatHistory.removeAt(0)
                                }
                                saveHistory(ctx)
                                callback(rep, "Groq Vision • $vMod"); return@thread
                            }
                        }
                        for (m in listOf("openai", "gemini", "openai-fast", "gpt-4o-mini")) {'''
    sc = sc.replace(old_vision, new_vision)

    open(svc_path, "w", encoding="utf-8").write(sc)
    print("OK: ApexCoreService upgraded (Fast Voice + Jarvis + Groq Vision)")
    # 5. ЖЕЛЕЗНЫЙ ФИКС МОЛЧАНИЯ (МАНИФЕСТ + АУДИОПОТОК + УСТРАНЕНИЕ КОНФЛИКТА МИКРОФОНА)
m_path = "app/src/main/AndroidManifest.xml"
if os.path.exists(m_path):
    mt = open(m_path, "r", encoding="utf-8").read()
    # Добавляем тип сервиса microphone прямо в тег service
    if 'ApexCoreService' in mt and 'foregroundServiceType' not in mt:
        mt = mt.replace(
            'android:name=".ApexCoreService"',
            'android:name=".ApexCoreService" android:foregroundServiceType="microphone"'
        )
    open(m_path, "w", encoding="utf-8").write(mt)

svc_path = "app/src/main/java/com/apex/assistant/ApexCoreService.kt"
if os.path.exists(svc_path):
    sc = open(svc_path, "r", encoding="utf-8").read()

    # 1. Отключаем startStopListener, который запускал микрофон поверх динамика и душил звук TTS
    sc = sc.replace('mainHandler.postDelayed({ startStopListener() }, 200)', '// stop listener disabled to prevent audio focus mute')
    sc = sc.replace('mainHandler.postDelayed({ startStopListener() }, 150)', '// stop listener disabled')

    # 2. Жестко направляем голос в основной мультимедийный динамик (STREAM_MUSIC)
    old_speak = 'tts?.speak(chunks[i], mode, null, uttId)'
    new_speak = '''val params = Bundle().apply {
                    putInt(TextToSpeech.Engine.KEY_PARAM_STREAM, android.media.AudioManager.STREAM_MUSIC)
                    putFloat(TextToSpeech.Engine.KEY_PARAM_VOLUME, 1.0f)
                }
                tts?.speak(chunks[i], mode, params, uttId)'''
    sc = sc.replace(old_speak, new_speak)

    # 3. Если TTS еще не успел инициализироваться — инициализируем принудительно перед речью
    old_clean_fn = 'private fun speakClean(text: String) {'
    new_clean_fn = '''private fun speakClean(text: String) {
        if (tts == null) { tts = TextToSpeech(this, this) }'''
    sc = sc.replace(old_clean_fn, new_clean_fn)

    # 4. Убираем блокировку микрофона перед началом речи (на случай если recognizer висел)
    sc = sc.replace(
        'isSpeaking = true\n        mainHandler.post {',
        '''isSpeaking = true
        mainHandler.post {
            try { speechRecognizer?.cancel(); speechRecognizer?.destroy(); speechRecognizer = null } catch (_: Exception) {}'''
    )

    open(svc_path, "w", encoding="utf-8").write(sc)
    print("OK: Audio focus and foregroundServiceType fixed!")
    
