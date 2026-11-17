import os, glob, shutil

# 1. Создаём push.json в корне репозитория, если его ещё нет
if not os.path.exists("push.json"):
    with open("push.json", "w", encoding="utf-8") as f:
        f.write('{"push_id":"","title":"Apex AI","body":""}')

# 2. Ставим твой оригинальный логотип на рабочий стол и в центр экрана
logo_src = glob.glob("fbe20faddd*")
if logo_src:
    os.makedirs("app/src/main/res/drawable", exist_ok=True)
    shutil.copyfile(logo_src, "app/src/main/res/drawable/apex_custom_logo.png")
    for root, _, files in os.walk("app/src/main/res"):
        for f in files:
            if f.startswith("ic_launcher") and (f.endswith(".png") or f.endswith(".webp")):
                shutil.copyfile(logo_src, os.path.join(root, f))
    for xml_f in glob.glob("app/src/main/res/mipmap-anydpi-v26/*.xml"):
        os.remove(xml_f)

# 3. Обновляем MainActivity.kt (твой логотип по центру + отправка пуша всем в 1 клик)
main_path = "app/src/main/java/com/apex/assistant/MainActivity.kt"
if os.path.exists(main_path):
    mc = open(main_path, "r", encoding="utf-8").read()
    old_badge = '''        val logoBadge = TextView(this).apply {
            text = "A"
            textSize = 44f
            typeface = Typeface.create("sans-serif-black", Typeface.BOLD)
            setTextColor(Color.BLACK)
            gravity = Gravity.CENTER
            background = GradientDrawable().apply {
                setColor(Color.WHITE)
                cornerRadius = 36f
            }
            elevation = 8f
        }'''
    new_badge = '''        val logoBadge = android.widget.ImageView(this).apply {
            setImageResource(R.drawable.apex_custom_logo)
            scaleType = android.widget.ImageView.ScaleType.FIT_CENTER
            setPadding(16, 16, 16, 16)
            background = GradientDrawable().apply {
                setColor(Color.WHITE)
                cornerRadius = 36f
            }
            clipToOutline = true
            elevation = 8f
        }'''
    mc = mc.replace(old_badge, new_badge)
    mc = mc.replace(
        'ApexCoreService.publishGithubPush(pTitle, pBody)',
        'ApexCoreService.publishGithubPush(pTitle, pBody) { ok -> runOnUiThread { android.widget.Toast.makeText(this@MainActivity, if (ok) "Push отправлен всем пользователям!" else "Ошибка отправки: проверь токен в коде", android.widget.Toast.LENGTH_LONG).show() } }'
    )
    open(main_path, "w", encoding="utf-8").write(mc)

# 4. Чиним бульканье микрофона, дикцию, живой характер с эмодзи и глубокие ответы
svc_path = "app/src/main/java/com/apex/assistant/ApexCoreService.kt"
if os.path.exists(svc_path):
    sc = open(svc_path, "r", encoding="utf-8").read()
    sc = sc.replace('speechRecognizer?.startListening(ri)', 'try { (getSystemService(Context.AUDIO_SERVICE) as android.media.AudioManager).adjustStreamVolume(android.media.AudioManager.STREAM_NOTIFICATION, android.media.AudioManager.ADJUST_MUTE, 0) } catch (_: Exception) {}\n                speechRecognizer?.startListening(ri)')
    sc = sc.replace('mainHandler.postDelayed({ startListeningCycle() }, 70)', 'mainHandler.postDelayed({ startListeningCycle() }, if (e == SpeechRecognizer.ERROR_RECOGNIZER_BUSY || e == SpeechRecognizer.ERROR_CLIENT) 1500 else 850)')
    sc = sc.replace('if (isListeningActive && !isSpeaking) startListeningCycle()', 'if (isListeningActive && !isSpeaking) mainHandler.postDelayed({ startListeningCycle() }, 650)')
    sc = sc.replace('r = r.replace(Regex("[\\\\u2600-\\\\u27BF\\\\u1F300-\\\\u1F9FF\\\\u1FA00-\\\\u1FAFF]"), "")', 'r = r.replace(Regex("[\\\\p{So}\\\\p{Cn}]"), "")')
    sc = sc.replace('r = r.replace(Regex("[ \\\\t]+"), " ")', 'r = r.replace("ъ", "ь").replace("Ъ", "Ь").replace(" - ", " — ").replace(Regex("[ \\\\t]+"), " ")')
    sc = sc.replace('val sys = "Ты — Apex AI, интеллектуальный ассистент от Derek Stealth в стиле Джарвиса: спокойный, вежливый, собранный и остроумный. $ctxInfo $noGreetRule Пиши грамотно с правильной пунктуацией (точки, запятые, тире), чтобы речь при озвучке звучала с естественными паузами и интонацией. Не используй символы разметки (*, #, _)."', 'val sys = "Ты — Apex AI, живой, душевный и умный ассистент в стиле Джарвиса (создатель — Derek Stealth). $ctxInfo $noGreetRule Общайся тепло, по-человечески, с харизмой и уместными эмодзи (😊, 🔥, 👍, 💡, ❤️), без сухого робото-канцелярита. Адаптируй длину ответа: на простые вопросы отвечай живо и ёмко; если пользователю грустно или плохо — искренне поддержи, спроси что случилось и предложи реальные решения; если просят код, объяснение, стих, конспект или разбор фото — пиши максимально подробно, глубоко и развёрнуто. Ставь правильную пунктуацию (точки, запятые, тире) для красивой интонации. Не используй символы разметки (*, #, _)."')
    sc = sc.replace('"max_tokens", 700', '"max_tokens", 3500')
    sc = sc.replace('"Подробно разбери это фото."', '"Максимально подробно и детально опиши всё, что изображено на этом фото, включая мелкие детали, текст и контекст."')
    open(svc_path, "w", encoding="utf-8").write(sc)
  
