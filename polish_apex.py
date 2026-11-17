import os, glob, shutil, re

# 1. ИКОНКА НА РАБОЧИЙ СТОЛ (ПРИНУДИТЕЛЬНО ЧЕРЕЗ ANDROIDMANIFEST.XML + ВСЕ MIPMAP/DRAWABLE)
logo_src = next(iter(glob.glob("fbe20faddd*")), None)
if logo_src:
    os.makedirs("app/src/main/res/drawable", exist_ok=True)
    shutil.copyfile(logo_src, "app/src/main/res/drawable/apex_custom_logo.png")
    for root, _, files in os.walk("app/src/main/res"):
        for f in files:
            if "ic_launcher" in f and f.endswith((".png", ".webp")):
                shutil.copyfile(logo_src, os.path.join(root, f))
    for xml_f in glob.glob("app/src/main/res/mipmap-anydpi-v26/*.xml"):
        os.remove(xml_f)
    m_path = "app/src/main/AndroidManifest.xml"
    if os.path.exists(m_path):
        mt = open(m_path, "r", encoding="utf-8").read()
        mt = re.sub(r'android:icon="[^"]+"', 'android:icon="@drawable/apex_custom_logo"', mt)
        mt = re.sub(r'android:roundIcon="[^"]+"', 'android:roundIcon="@drawable/apex_custom_logo"', mt)
        open(m_path, "w", encoding="utf-8").write(mt)

# 2. MAINACTIVITY.KT: ЛОГОТИП ПО ЦЕНТРУ + ПУШИ ВСЕМ БЕЗ ТОКЕНОВ ЧЕРЕЗ NTFY.SH
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
        'ApexCoreService.publishFreePush(pTitle, pBody) { ok -> runOnUiThread { android.widget.Toast.makeText(this@MainActivity, if (ok) "Push отправлен всем в шторку!" else "Ошибка сети при отправке Push", android.widget.Toast.LENGTH_LONG).show() } }'
    )
    open(main_path, "w", encoding="utf-8").write(mc)

# 3. APEXCORESERVICE.KT: ВОЗВРАЩАЕМ ГРОМКИЙ ГОЛОС БЕЗ БУЛЬКАНЬЯ, ЧИНИМ ФОТО (45 СЕК + GROQ VISION) И ПУШИ
svc_path = "app/src/main/java/com/apex/assistant/ApexCoreService.kt"
if os.path.exists(svc_path):
    sc = open(svc_path, "r", encoding="utf-8").read()

    # Убираем глушение системной громкости и ставим плавный перезапуск слушателя
    sc = sc.replace('mainHandler.postDelayed({ startListeningCycle() }, 70)', 'mainHandler.postDelayed({ startListeningCycle() }, 1100)')
    sc = sc.replace('if (isListeningActive && !isSpeaking) startListeningCycle()', 'if (isListeningActive && !isSpeaking) mainHandler.postDelayed({ startListeningCycle() }, 900)')

    # Гарантируем громкий аудио-поток для голоса Джарвиса
    sc = sc.replace(
        'tts?.speak(chunks[i], mode, Bundle(), uttId)',
        'val b = Bundle().apply { putInt(TextToSpeech.Engine.KEY_PARAM_STREAM, android.media.AudioManager.STREAM_MUSIC) }; tts?.speak(chunks[i], mode, b, uttId)'
    )

    # Увеличиваем таймаут сети до 45 секунд для длинных разборов фото и добавляем резерв Groq Vision
    sc = sc.replace('c.connectTimeout = 7000; c.readTimeout = 18000', 'c.connectTimeout = 12000; c.readTimeout = 45000')
    sc = sc.replace(
        'for (m in listOf("openai", "gemini", "openai-fast", "gpt-4o-mini")) {',
        'for (gm in listOf("meta-llama/llama-4-scout-17b-16e-instruct", "llama-3.2-11b-vision-preview")) { val gBody = JSONObject().put("model", gm).put("messages", msgs).put("temperature", 0.6).put("max_tokens", 1800); val (gc, gr) = postJson("https://groq.com", "Bearer $key", gBody); if (gc in 200..299) { val rep = JSONObject(gr).getJSONArray("choices").getJSONObject(0).getJSONObject("message").getString("content").trim(); synchronized(chatHistory) { chatHistory.add(Pair("user", "[Фото] $prompt")); chatHistory.add(Pair("assistant", rep)); while (chatHistory.size > 40) chatHistory.removeAt(0) }; saveHistory(ctx); callback(rep, "Groq Vision"); return@thread } }\n                        for (m in listOf("openai", "gemini", "openai-fast")) {'
    )

    # Добавляем бесплатную отправку и приём Push через ntfy.sh без токенов
    push_funcs = '''
        fun publishFreePush(title: String, body: String, onDone: ((Boolean) -> Unit)? = null) {
            thread {
                try {
                    val c = URL("https://ntfy.sh").openConnection() as HttpURLConnection
                    c.requestMethod = "POST"
                    c.setRequestProperty("Title", title.ifEmpty { "Apex AI" })
                    c.setRequestProperty("Priority", "high")
                    c.doOutput = true
                    OutputStreamWriter(c.outputStream).use { it.write(body) }
                    onDone?.invoke(c.responseCode in 200..299)
                } catch (_: Exception) { onDone?.invoke(false) }
            }
        }
'''
    sc = sc.replace('fun publishGithubPush(', push_funcs + '\n        fun publishGithubPush(')
    sc = sc.replace(
        'val pConn = URL("{push_raw}?t=" + System.currentTimeMillis()).openConnection() as HttpURLConnection',
        'val pConn = URL("https://ntfy.sh/json?poll=1").openConnection() as HttpURLConnection'
    )
    old_poll = '''val res = JSONObject(pConn.inputStream.bufferedReader().use { it.readText() })
                        val pId = res.optString("push_id", "")
                        if (pId.isNotEmpty() && pId != prefs.getString("gh_last_push_id", "")) {
                            prefs.edit().putString("gh_last_push_id", pId).apply()
                            showSystemNotify(pId.hashCode(), res.optString("title", "Apex AI"), res.optString("body", ""), null)
                        }'''
    new_poll = '''val lines = pConn.inputStream.bufferedReader().use { it.readLines() }.filter { it.isNotBlank() }
                        if (lines.isNotEmpty()) {
                            val res = JSONObject(lines.last())
                            val pId = res.optString("id", "")
                            if (pId.isNotEmpty() && res.optString("event") == "message" && pId != prefs.getString("gh_last_push_id", "")) {
                                prefs.edit().putString("gh_last_push_id", pId).apply()
                                showSystemNotify(pId.hashCode(), res.optString("title", "Apex AI"), res.optString("message", ""), null)
                            }
                        }'''
    sc = sc.replace(old_poll, new_poll)

    # Характер, глубина ответов и очистка эмодзи для голоса
    sc = sc.replace('r = r.replace(Regex("[\\\\u2600-\\\\u27BF\\\\u1F300-\\\\u1F9FF\\\\u1FA00-\\\\u1FAFF]"), "")', 'r = r.replace(Regex("[\\\\p{So}\\\\p{Cn}]"), "")')
    sc = sc.replace('r = r.replace(Regex("[ \\\\t]+"), " ")', 'r = r.replace("ъ", "ь").replace("Ъ", "Ь").replace(" - ", " — ").replace(Regex("[ \\\\t]+"), " ")')
    sc = sc.replace('val sys = "Ты — Apex AI, интеллектуальный ассистент от Derek Stealth в стиле Джарвиса: спокойный, вежливый, собранный и остроумный. $ctxInfo $noGreetRule Пиши грамотно с правильной пунктуацией (точки, запятые, тире), чтобы речь при озвучке звучала с естественными паузами и интонацией. Не используй символы разметки (*, #, _)."', 'val sys = "Ты — Apex AI, живой, душевный и умный ассистент в стиле Джарвиса (создатель — Derek Stealth). $ctxInfo $noGreetRule Общайся тепло, по-человечески, с харизмой и уместными эмодзи (😊, 🔥, 👍, 💡, ❤️), без сухого робото-канцелярита. Адаптируй длину ответа: на простые вопросы отвечай живо и ёмко; если пользователю грустно или плохо — искренне поддержи, спроси что случилось и предложи реальные решения; если просят код, объяснение, стих, конспект или разбор фото — пиши максимально подробно, глубоко и развёрнуто. Ставь правильную пунктуацию (точки, запятые, тире) для красивой интонации. Не используй символы разметки (*, #, _)."')
    sc = sc.replace('"max_tokens", 700', '"max_tokens", 2800')
    sc = sc.replace('"Подробно разбери это фото."', '"Подробно и понятно опиши всё, что изображено на этом фото, включая детали, текст и смысл."')

    open(svc_path, "w", encoding="utf-8").write(sc)
        
