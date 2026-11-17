import os, glob, shutil, re
from PIL import Image

logo_src = next(iter(glob.glob("fbe20faddd*")), None)
if logo_src:
    os.makedirs("app/src/main/res/drawable", exist_ok=True)
    shutil.copyfile(logo_src, "app/src/main/res/drawable/apex_custom_logo.png")
    im = Image.open(logo_src).convert("RGBA")
    bbox = im.convert("L").point(lambda p: 255 if p < 120 else 0).getbbox()
    if bbox:
        cropped = im.crop(bbox)
        side = int(max(cropped.size) * 1.75)
        canvas = Image.new("RGBA", (side, side), (255, 255, 255, 255))
        canvas.paste(cropped, ((side - cropped.width) // 2, (side - cropped.height) // 2), cropped)
        canvas.resize((256, 256), Image.LANCZOS).save("app/src/main/res/drawable/apex_launcher_icon.png")
    else:
        shutil.copyfile(logo_src, "app/src/main/res/drawable/apex_launcher_icon.png")
    for r, _, fs in os.walk("app/src/main/res"):
        for f in fs:
            if "ic_launcher" in f and f.endswith((".png", ".webp")):
                shutil.copyfile("app/src/main/res/drawable/apex_launcher_icon.png", os.path.join(r, f))
    for xf in glob.glob("app/src/main/res/mipmap-anydpi-v26/*.xml"):
        os.remove(xf)
    mp = "app/src/main/AndroidManifest.xml"
    if os.path.exists(mp):
        mt = open(mp, "r", encoding="utf-8").read()
        mt = re.sub(r'android:icon="[^"]+"', 'android:icon="@drawable/apex_launcher_icon"', mt)
        mt = re.sub(r'android:roundIcon="[^"]+"', 'android:roundIcon="@drawable/apex_launcher_icon"', mt)
        open(mp, "w", encoding="utf-8").write(mt)

main_path = "app/src/main/java/com/apex/assistant/MainActivity.kt"
mc = open(main_path, "r", encoding="utf-8").read()
mc = mc.replace('val CREATOR_IDS = setOf("97def6cd87afc85f", "212239d20d74e965")', 'val CREATOR_IDS = setOf("97def6cd87afc85f", "212239d20d74e965", "16b6f7987517a519")')
mc = mc.replace('if (prefs.getBoolean("dev_unlocked", false)) {', 'if (isCreator || prefs.getBoolean("dev_unlocked", false)) {')
old_logo_view = '''        val logoBadge = object : View(this) {
            val fillPaint = Paint(Paint.ANTI_ALIAS_FLAG).apply {
                color = textMainColor
                style = Paint.Style.FILL
            }
            override fun onDraw(canvas: Canvas) {
                super.onDraw(canvas)
                val s = minOf(width, height) / 108f
                canvas.save()
                canvas.scale(s, s)
                val path = Path().apply {
                    moveTo(50f, 30f)
                    lineTo(58f, 30f)
                    lineTo(75f, 78f)
                    lineTo(66.5f, 78f)
                    lineTo(62.2f, 65.5f)
                    lineTo(46.2f, 65.5f)
                    lineTo(48.5f, 58.8f)
                    lineTo(60f, 58.8f)
                    lineTo(54f, 40.5f)
                    lineTo(41.5f, 78f)
                    lineTo(33f, 78f)
                    close()
                }
                canvas.drawPath(path, fillPaint)
                canvas.restore()
            }
        }'''
new_logo_view = '''        val logoBadge = android.widget.ImageView(this).apply {
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
mc = mc.replace(old_logo_view, new_logo_view)

old_send = '''                addChatBubble((if (imgB64 != null) "📷 [Фото прикреплено]\\n" else "") + promptToSend, true)
                ApexCoreService.queryBrainDirect(this@MainActivity, promptToSend, isCreator, imgB64) { reply, diag ->
                    prefs.edit().putString("last_diag", diag).apply()
                    runOnUiThread { addChatBubble(reply, false) }
                }'''
new_send = '''                addChatBubble((if (imgB64 != null) "📷 [Фото прикреплено]\\n" else "") + promptToSend, true)
                addChatBubble("Думаю •  ", false)
                val thinkRow = messagesContainer.getChildAt(messagesContainer.childCount - 1) as? LinearLayout
                val thinkTv = ((thinkRow?.getChildAt(0) as? LinearLayout)?.getChildAt(0) as? LinearLayout)?.getChildAt(1) as? TextView
                var animAlive = true
                val hAnim = Handler(Looper.getMainLooper())
                val frames = arrayOf("Думаю •  ", "Думаю  • ", "Думаю   •", "Думаю •••")
                var step = 0
                hAnim.post(object : Runnable {
                    override fun run() {
                        if (animAlive && thinkTv != null) {
                            thinkTv.text = frames[step++ % frames.size]
                            hAnim.postDelayed(this, 300)
                        }
                    }
                })
                ApexCoreService.queryBrainDirect(this@MainActivity, promptToSend, isCreator, imgB64) { reply, diag ->
                    prefs.edit().putString("last_diag", diag).apply()
                    runOnUiThread {
                        animAlive = false
                        if (thinkRow != null) messagesContainer.removeView(thinkRow)
                        addChatBubble(reply, false)
                    }
                }'''
mc = mc.replace(old_send, new_send)

old_push_btn = '''                    Toast.makeText(this@MainActivity, "✅ Push-уведомление отправлено!", Toast.LENGTH_LONG).show()'''
new_push_btn = '''                    try {
                        val nm = getSystemService(Context.NOTIFICATION_SERVICE) as NotificationManager
                        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
                            nm.createNotificationChannel(NotificationChannel("apex_push", "Apex Updates", NotificationManager.IMPORTANCE_HIGH))
                        }
                        val nb = if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) Notification.Builder(this@MainActivity, "apex_push") else @Suppress("DEPRECATION") Notification.Builder(this@MainActivity)
                        nm.notify(System.currentTimeMillis().toInt(), nb.setContentTitle(pTitle).setContentText(pBody).setSmallIcon(android.R.drawable.ic_dialog_info).setAutoCancel(true).build())
                    } catch (_: Exception) {}
                    Toast.makeText(this@MainActivity, "✅ Push-уведомление отправлено!", Toast.LENGTH_LONG).show()'''
mc = mc.replace(old_push_btn, new_push_btn)

open(main_path, "w", encoding="utf-8").write(mc)
svc_path = "app/src/main/java/com/apex/assistant/ApexCoreService.kt"
if os.path.exists(svc_path):
    sc = open(svc_path, "r", encoding="utf-8").read()
    sc = re.sub(r'в стиле Джарвиса[^."]*', 'созданный разработчиком Derek Stealth. Никогда не упоминай Джарвиса и не сравнивай себя с киногероями — ты уникальный и самостоятельный ИИ нового поколения', sc)

    fallback_player = '''
    private var onlinePlayer: android.media.MediaPlayer? = null
    private fun speakOnlineFallback(text: String) {
        thread {
            try {
                val shortTxt = text.take(280)
                val enc = java.net.URLEncoder.encode(shortTxt, "UTF-8")
                val urlStr = "https://google.com"
                mainHandler.post {
                    try {
                        onlinePlayer?.release()
                        onlinePlayer = android.media.MediaPlayer().apply {
                            setAudioAttributes(android.media.AudioAttributes.Builder().setContentType(android.media.AudioAttributes.CONTENT_TYPE_SPEECH).setUsage(android.media.AudioAttributes.USAGE_MEDIA).build())
                            setDataSource(urlStr)
                            setOnCompletionListener {
                                isSpeaking = false
                                if (isListeningActive) mainHandler.postDelayed({ startListeningCycle() }, 700)
                            }
                            setOnErrorListener { _, _, _ ->
                                isSpeaking = false
                                if (isListeningActive) mainHandler.postDelayed({ startListeningCycle() }, 700)
                                true
                            }
                            prepareAsync()
                            setOnPreparedListener { start() }
                        }
                    } catch (_: Exception) {
                        isSpeaking = false
                        if (isListeningActive) mainHandler.postDelayed({ startListeningCycle() }, 700)
                    }
                }
            } catch (_: Exception) {
                isSpeaking = false
                if (isListeningActive) mainHandler.postDelayed({ startListeningCycle() }, 700)
            }
        }
    }
'''
    sc = sc.replace('private var tts: TextToSpeech? = null', 'private var tts: TextToSpeech? = null\n    private var ttsReady = false\n' + fallback_player)
    sc = sc.replace('tts?.setSpeechRate(1.05f)', 'ttsReady = true; tts?.setSpeechRate(1.02f); tts?.setPitch(0.95f)')

    sc = sc.replace('tts?.speak(chunks[i], mode, Bundle(), uttId)', 'if (ttsReady) { tts?.speak(chunks[i], mode, null, uttId) } else { if (i == 0) speakOnlineFallback(c); break }')
    sc = sc.replace(
        'tts?.speak(reply, TextToSpeech.QUEUE_FLUSH, Bundle(), "APEX_UTTERANCE")',
        'try { speechRecognizer?.cancel(); speechRecognizer?.destroy(); speechRecognizer = null } catch (_: Exception) {}; if (ttsReady) tts?.speak(reply, TextToSpeech.QUEUE_FLUSH, null, "APEX_UTTERANCE") else speakOnlineFallback(reply)'
    )
    sc = sc.replace(
        'override fun onInit(status: Int) {',
        '''override fun onInit(status: Int) {
        if (status != TextToSpeech.SUCCESS) {
            val engs = tts?.engines
            if (!engs.isNullOrEmpty()) {
                tts = TextToSpeech(this, this, engs.first().name)
                return
            }
        }'''
    )
    open(svc_path, "w", encoding="utf-8").write(sc)

print("✅ update_code.py успешно применён!")
