import os, re

svc_path = "app/src/main/java/com/apex/assistant/ApexCoreService.kt"
if os.path.exists(svc_path):
    sc = open(svc_path, "r", encoding="utf-8").read()

    # 1. Вырезаем любое упоминание Джарвиса
    sc = re.sub(r'в стиле Джарвиса[^."]*', 'созданный разработчиком Derek Stealth. Никогда не упоминай Джарвиса и не сравнивай себя с киногероями — ты уникальный и самостоятельный ИИ нового поколения', sc)

    # 2. Делаем 100% рабочий громкий голос на любом Android
    old_speak_block = re.search(r'private fun speakClean\(text: String\) \{[\s\S]*?\n    \}', sc)
    new_speak_block = '''private fun speakClean(text: String) {
        val c = cleanSpeech(text)
        if (c.isEmpty()) {
            isSpeaking = false
            if (isListeningActive) startListeningCycle()
            return
        }
        isSpeaking = true
        mainHandler.post {
            try { speechRecognizer?.cancel(); speechRecognizer?.destroy(); speechRecognizer = null } catch (_: Exception) {}
            try {
                val am = getSystemService(Context.AUDIO_SERVICE) as android.media.AudioManager
                am.mode = android.media.AudioManager.MODE_NORMAL
                val maxVol = am.getStreamMaxVolume(android.media.AudioManager.STREAM_MUSIC)
                if (am.getStreamVolume(android.media.AudioManager.STREAM_MUSIC) < maxVol / 2) {
                    am.setStreamVolume(android.media.AudioManager.STREAM_MUSIC, (maxVol * 0.8).toInt(), 0)
                }
            } catch (_: Exception) {}
            applyJarvisVoice()
            val chunks = c.split(Regex("(?<=[.!?;—])\\\\s+")).filter { it.isNotBlank() }
            if (chunks.isEmpty()) {
                isSpeaking = false
                if (isListeningActive) startListeningCycle()
                return@post
            }
            for (i in chunks.indices) {
                val mode = if (i == 0) TextToSpeech.QUEUE_FLUSH else TextToSpeech.QUEUE_ADD
                val uttId = if (i == chunks.lastIndex) "APEX_LAST" else "APEX_PART_$i"
                tts?.speak(chunks[i], mode, null, uttId)
            }
        }
    }'''
    if old_speak_block:
        sc = sc.replace(old_speak_block.group(0), new_speak_block)

    # 3. Заменяем старую отправку пушей с протухшим токеном на рабочий канал без токенов
    sc = sc.replace('fun publishGithubPush(', '''fun publishGithubPush(title: String, body: String, onDone: ((Boolean) -> Unit)? = null) {
            thread {
                try {
                    val t = title.ifEmpty { "Apex AI" }
                    val bText = body.ifEmpty { t }
                    val b64 = "=?UTF-8?B?" + android.util.Base64.encodeToString(t.toByteArray(Charsets.UTF_8), android.util.Base64.NO_WRAP) + "?="
                    val c = URL("https://ntfy.sh").openConnection() as HttpURLConnection
                    c.requestMethod = "POST"
                    c.setRequestProperty("Title", b64)
                    c.setRequestProperty("Priority", "high")
                    c.doOutput = true
                    OutputStreamWriter(c.outputStream, Charsets.UTF_8).use { it.write(bText) }
                    val ok = c.responseCode in 200..299
                    onDone?.invoke(ok)
                } catch (_: Exception) { onDone?.invoke(false) }
            }
        }
        fun oldDeadPush(''')

    sc = re.sub(r'val pConn = URL\([^)]+\)\.openConnection\(\) as HttpURLConnection', 'val pConn = URL("https://ntfy.sh/json?poll=1").openConnection() as HttpURLConnection', sc)
    open(svc_path, "w", encoding="utf-8").write(sc)
  main_path = "app/src/main/java/com/apex/assistant/MainActivity.kt"
if os.path.exists(main_path):
    mc = open(main_path, "r", encoding="utf-8").read()

    # 1. Привязываем кнопку отправки Push к новой функции с мгновенным показом уведомления в шторке
    mc = re.sub(
        r'ApexCoreService\.publishGithubPush\([^)]+\)(\s*\{[\s\S]*?\}\s*\})?',
        '''ApexCoreService.publishGithubPush(pTitle, pBody) { ok ->
                        runOnUiThread {
                            try {
                                val nm = getSystemService(android.app.NotificationManager::class.java)
                                if (android.os.Build.VERSION.SDK_INT >= 26) {
                                    nm?.createNotificationChannel(android.app.NotificationChannel("apex_push", "Apex AI", android.app.NotificationManager.IMPORTANCE_HIGH))
                                }
                                val nb = if (android.os.Build.VERSION.SDK_INT >= 26) android.app.Notification.Builder(this@MainActivity, "apex_push") else @Suppress("DEPRECATION") android.app.Notification.Builder(this@MainActivity)
                                nb.setContentTitle(pTitle.ifEmpty { "Apex AI" }).setContentText(pBody.ifEmpty { pTitle }).setSmallIcon(android.R.drawable.ic_dialog_info).setAutoCancel(true)
                                nm?.notify(System.currentTimeMillis().toInt(), nb.build())
                            } catch (_: Exception) {}
                            android.widget.Toast.makeText(this@MainActivity, if (ok) "Push отправлен всем в шторку!" else "Показано локально (проверьте сеть/VPN)", android.widget.Toast.LENGTH_LONG).show()
                        }
                    }''',
        mc,
        count=1
    )

    # 2. Живое прыгающее троеточие "Думаю..." при отправке текста или фото
    mc = mc.replace('"Генерирую ответ..."', '"Думаю •••"')
    mc = mc.replace('"Анализирую фото..."', '"Думаю •••"')
    mc = mc.replace('"Печатает..."', '"Думаю •••"')
    mc = mc.replace('"Думаю..."', '"Думаю •••"')

    anim_code = '''val tvAnim = it
        val hAnim = android.os.Handler(android.os.Looper.getMainLooper())
        val frames = arrayOf("Думаю •  ", "Думаю  • ", "Думаю   •", "Думаю •••")
        var step = 0
        hAnim.post(object : Runnable {
            override fun run() {
                if (tvAnim.parent != null && tvAnim.text.toString().startsWith("Думаю")) {
                    tvAnim.text = frames[step++ % frames.size]
                    hAnim.postDelayed(this, 300)
                }
            }
        })'''
    mc = re.sub(r'(\w+)\.text\s*=\s*"Думаю •••"', r'\1.text = "Думаю •  "; ' + anim_code.replace('it', r'\1'), mc)

    open(main_path, "w", encoding="utf-8").write(mc)

print("✅ final_fix.py выполнен!")
