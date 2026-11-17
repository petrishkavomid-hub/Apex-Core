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

