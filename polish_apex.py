import os, glob, shutil, re

logo_src = next(iter(glob.glob("fbe20faddd*")), None)
if logo_src:
    os.makedirs("app/src/main/res/drawable", exist_ok=True)
    shutil.copyfile(logo_src, "app/src/main/res/drawable/apex_custom_logo.png")
    try:
        from PIL import Image, ImageChops
        im = Image.open(logo_src).convert("RGBA")
        bg = Image.new("RGBA", im.size, (255, 255, 255, 255))
        bbox = ImageChops.difference(im.convert("RGB"), bg.convert("RGB")).getbbox()
        if bbox:
            cropped = im.crop(bbox)
            side = int(max(cropped.size) * 1.65)
            canvas = Image.new("RGBA", (side, side), (255, 255, 255, 255))
            canvas.paste(cropped, ((side - cropped.width) // 2, (side - cropped.height) // 2), cropped)
            canvas.resize((256, 256), Image.LANCZOS).save("app/src/main/res/drawable/apex_launcher_icon.png")
        else:
            shutil.copyfile(logo_src, "app/src/main/res/drawable/apex_launcher_icon.png")
    except Exception:
        shutil.copyfile(logo_src, "app/src/main/res/drawable/apex_launcher_icon.png")

    for root, _, files in os.walk("app/src/main/res"):
        for f in files:
            if "ic_launcher" in f and f.endswith((".png", ".webp")):
                shutil.copyfile("app/src/main/res/drawable/apex_launcher_icon.png", os.path.join(root, f))
    for xml_f in glob.glob("app/src/main/res/mipmap-anydpi-v26/*.xml"):
        os.remove(xml_f)
    m_path = "app/src/main/AndroidManifest.xml"
    if os.path.exists(m_path):
        mt = open(m_path, "r", encoding="utf-8").read()
        mt = re.sub(r'android:icon="[^"]+"', 'android:icon="@drawable/apex_launcher_icon"', mt)
        mt = re.sub(r'android:roundIcon="[^"]+"', 'android:roundIcon="@drawable/apex_launcher_icon"', mt)
        open(m_path, "w", encoding="utf-8").write(mt)
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
        'ApexCoreService.checkAppUpdateDialog(this)',
        'ApexCoreService.checkAppUpdateDialog(this); ApexCoreService.startPushPoller(applicationContext)'
    )
    mc = mc.replace(
        'ApexCoreService.publishGithubPush(pTitle, pBody)',
        'ApexCoreService.publishFreePush(applicationContext, pTitle, pBody) { ok -> runOnUiThread { android.widget.Toast.makeText(this@MainActivity, if (ok) "Push отправлен в шторку всем!" else "Ошибка сети при отправке Push", android.widget.Toast.LENGTH_LONG).show() } }'
    )
    open(main_path, "w", encoding="utf-8").write(mc)
    svc_path = "app/src/main/java/com/apex/assistant/ApexCoreService.kt"
if os.path.exists(svc_path):
    sc = open(svc_path, "r", encoding="utf-8").read()

    old_speak = '''        isSpeaking = true
        mainHandler.post {
            applyJarvisVoice()'''
    new_speak = '''        isSpeaking = true
        mainHandler.post {
            try { speechRecognizer?.cancel(); speechRecognizer?.destroy(); speechRecognizer = null } catch (_: Exception) {}
            try {
                val am = getSystemService(Context.AUDIO_SERVICE) as android.media.AudioManager
                if (am.getStreamVolume(android.media.AudioManager.STREAM_MUSIC) == 0) {
                    am.setStreamVolume(android.media.AudioManager.STREAM_MUSIC, am.getStreamMaxVolume(android.media.AudioManager.STREAM_MUSIC) / 2, 0)
                }
            } catch (_: Exception) {}
            applyJarvisVoice()'''
    sc = sc.replace(old_speak, new_speak)

    sc = sc.replace('mainHandler.postDelayed({ startStopListener() }, 200)', '')
    sc = sc.replace('mainHandler.postDelayed({ startListeningCycle() }, 70)', 'mainHandler.postDelayed({ startListeningCycle() }, 1200)')
    sc = sc.replace('if (isListeningActive && !isSpeaking) startListeningCycle()', 'if (isListeningActive && !isSpeaking) mainHandler.postDelayed({ startListeningCycle() }, 1000)')
    sc = sc.replace(
        'tts?.speak(chunks[i], mode, Bundle(), uttId)',
        'val b = Bundle().apply { putInt(TextToSpeech.Engine.KEY_PARAM_STREAM, android.media.AudioManager.STREAM_MUSIC); putFloat(TextToSpeech.Engine.KEY_PARAM_VOLUME, 1.0f) }; tts?.speak(chunks[i], mode, b, uttId)'
    )

    push_block = '''
        private var pushPollerStarted = false
        fun showNotifyStatic(ctx: Context, id: Int, title: String, body: String) {
            try {
                val nm = ctx.getSystemService(NotificationManager::class.java)
                if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
                    nm?.createNotificationChannel(NotificationChannel("apex_push", "Apex AI Уведомления", NotificationManager.IMPORTANCE_HIGH))
                }
                val nb = if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) Notification.Builder(ctx, "apex_push") else @Suppress("DEPRECATION") Notification.Builder(ctx)
                nb.setContentTitle(title).setContentText(body).setSmallIcon(android.R.drawable.ic_dialog_info).setAutoCancel(true)
                nm?.notify(id, nb.build())
            } catch (_: Exception) {}
        }

        fun startPushPoller(ctx: Context) {
            if (pushPollerStarted) return
            pushPollerStarted = true
            thread {
                while (true) {
                    try {
                        val prefs = ctx.getSharedPreferences("apex_prefs", Context.MODE_PRIVATE)
                        val pConn = URL("https://ntfy.sh").openConnection() as HttpURLConnection
                        pConn.connectTimeout = 8000; pConn.readTimeout = 8000
                        if (pConn.responseCode in 200..299) {
                            val lines = pConn.inputStream.bufferedReader().use { it.readLines() }.filter { it.isNotBlank() }
                            if (lines.isNotEmpty()) {
                                val res = JSONObject(lines.last())
                                val pId = res.optString("id", "")
                                if (pId.isNotEmpty() && res.optString("event") == "message" && pId != prefs.getString("gh_last_push_id", "")) {
                                    prefs.edit().putString("gh_last_push_id", pId).apply()
                                    showNotifyStatic(ctx, pId.hashCode(), res.optString("title", "Apex AI"), res.optString("message", ""))
                                }
                            }
                        }
                    } catch (_: Exception) {}
                    Thread.sleep(8000)
                }
            }
        }

        fun publishFreePush(ctx: Context, title: String, body: String, onDone: ((Boolean) -> Unit)? = null) {
            thread {
                try {
                    val t = title.ifEmpty { "Apex AI" }
                    val c = URL("https://ntfy.sh").openConnection() as HttpURLConnection
                    c.requestMethod = "POST"
                    c.setRequestProperty("Title", t)
                    c.setRequestProperty("Priority", "high")
                    c.doOutput = true
                    OutputStreamWriter(c.outputStream).use { it.write(body) }
                    val ok = c.responseCode in 200..299
                    if (ok) showNotifyStatic(ctx, System.currentTimeMillis().toInt(), t, body)
                    onDone?.invoke(ok)
                } catch (_: Exception) { onDone?.invoke(false) }
            }
        }
'''
    sc = sc.replace('fun publishGithubPush(', push_block + '\n        fun publishGithubPush(')
    sc = sc.replace('c.connectTimeout = 7000; c.readTimeout = 18000', 'c.connectTimeout = 12000; c.readTimeout = 45000')
    sc = sc.replace('r = r.replace(Regex("[\\\\u2600-\\\\u27BF\\\\u1F300-\\\\u1F9FF\\\\u1FA00-\\\\u1FAFF]"), "")', 'r = r.replace(Regex("[\\\\p{So}\\\\p{Cn}]"), "")')
    sc = sc.replace('r = r.replace(Regex("[ \\\\t]+"), " ")', 'r = r.replace("ъ", "ь").replace("Ъ", "Ь").replace(" - ", " — ").replace(Regex("[ \\\\t]+"), " ")')
    sc = sc.replace('val sys = "Ты — Apex AI, интеллектуальный ассистент от Derek Stealth в стиле Джарвиса: спокойный, вежливый, собранный и остроумный. $ctxInfo $noGreetRule Пиши грамотно с правильной пунктуацией (точки, запятые, тире), чтобы речь при озвучке звучала с естественными паузами и интонацией. Не используй символы разметки (*, #, _)."', 'val sys = "Ты — Apex AI, живой, душевный и умный ассистент в стиле Джарвиса (создатель — Derek Stealth). $ctxInfo $noGreetRule Общайся тепло, по-человечески, с харизмой и уместными эмодзи (😊, 🔥, 👍, 💡, ❤️), без сухого робото-канцелярита. Адаптируй длину ответа: на простые вопросы отвечай живо и ёмко; если пользователю грустно или плохо — искренне поддержи, спроси что случилось и предложи реальные решения; если просят код, объяснение, стих, конспект или разбор фото — пиши максимально подробно, глубоко и развёрнуто. Ставь правильную пунктуацию (точки, запятые, тире) для красивой интонации. Не используй символы разметки (*, #, _)."')
    sc = sc.replace('"max_tokens", 700', '"max_tokens", 2800')
    open(svc_path, "w", encoding="utf-8").write(sc)
    
