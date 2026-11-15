package com.apex.assistant

import android.app.*
import android.content.*
import android.os.*
import android.speech.*
import android.speech.tts.TextToSpeech
import android.speech.tts.UtteranceProgressListener
import android.util.Base64
import android.provider.Settings
import android.net.Uri
import org.json.JSONArray
import org.json.JSONObject
import java.io.OutputStreamWriter
import java.net.HttpURLConnection
import java.net.URL
import java.util.*
import kotlin.concurrent.thread

class ApexCoreService : Service(), TextToSpeech.OnInitListener {
    private var tts: TextToSpeech? = null
    private var speechRecognizer: SpeechRecognizer? = null
    private var isListeningActive = false
    private var isSpeaking = false
    private val mainHandler = Handler(Looper.getMainLooper())

    companion object {
        private var cachedModel: String? = null
        private val chatHistory = mutableListOf<Pair<String, String>>()
        private fun getPollenKey() = String(Base64.decode("c2tfRTc4V0E0V0ZBc0ZQM0VsYTJucE41ZVo0eENYaDNYeVU=", Base64.DEFAULT))
        
        private fun cleanSpeech(t: String): String {
            var r = t
            r = r.replace(Regex("[*#_`~>|\\[\\]]"), "")
            r = r.replace(Regex("(?m)^\\s*[-•]\\s+"), "")
            r = r.replace(Regex("[\\uD800-\\uDFFF]"), "")
            r = r.replace(Regex("[\\u2600-\\u27BF]"), "")
            r = r.replace(Regex("[\\uFE0F\\u200D]"), "")
            r = r.replace(Regex("(?i)\\b(зв[её]здочка|зв[её]здочки|искра|искорка|лампочка|лампочки|огонёк|огонек|сердечко|улыбка|смайлик|смайлы)\\b"), "")
            r = r.replace(Regex("[ \\t]+"), " ")
            r = r.replace(Regex("\\n{2,}"), "\n")
            return r.trim()
        }

        private fun getMskTimeInfo(): String {
            val sdf = java.text.SimpleDateFormat("dd.MM.yyyy, HH:mm, EEEE", Locale("ru", "RU"))
            sdf.timeZone = java.util.TimeZone.getTimeZone("Europe/Moscow")
            return "Справочно (НИКОГДА не называй время или дату, если прямо не спросили): сейчас по Москве (МСК) " + sdf.format(java.util.Date()) + "."
        }

        var historyLoaded = false
        fun loadHistory(ctx: Context) {
            if (historyLoaded) return
            historyLoaded = true
            try {
                val raw = ctx.getSharedPreferences("apex_prefs", Context.MODE_PRIVATE).getString("saved_chat_history", "") ?: ""
                if (raw.isNotEmpty()) {
                    val arr = JSONArray(raw)
                    synchronized(chatHistory) {
                        chatHistory.clear()
                        for (i in 0 until arr.length()) {
                            val o = arr.getJSONObject(i)
                            chatHistory.add(Pair(o.getString("r"), o.getString("t")))
                        }
                    }
                }
            } catch (_: Exception) {}
        }

        fun saveHistory(ctx: Context) {
            try {
                val arr = JSONArray()
                synchronized(chatHistory) {
                    for (p in chatHistory) {
                        val obj = JSONObject()
                        obj.put("r", p.first as Any)
                        obj.put("t", p.second as Any)
                        arr.put(obj)
                    }
                }
                ctx.getSharedPreferences("apex_prefs", Context.MODE_PRIVATE).edit().putString("saved_chat_history", arr.toString()).apply()
            } catch (_: Exception) {}
        }

        fun publishGithubPush(title: String, body: String) {
            thread {
                try {
                    val tok = String(Base64.decode("Z2hwX2NMRFF5MDAzaVBlMDRMZmVhbElObmlCWnBSNEFBNjJzdHd1Rg==", Base64.DEFAULT))
                    val c1 = URL("https://api.github.com/repos/petrishkavomid-hub/Apex-Core/contents/push.json").openConnection() as HttpURLConnection
                    c1.setRequestProperty("Authorization", "Bearer $tok")
                    c1.setRequestProperty("User-Agent", "ApexAI")
                    val sha = if (c1.responseCode in 200..299) JSONObject(c1.inputStream.bufferedReader().use { it.readText() }).optString("sha", "") else ""
                    val payload = JSONObject().put("push_id", System.currentTimeMillis().toString()).put("title", title.ifEmpty { "Apex AI" }).put("body", body).toString()
                    val b64 = Base64.encodeToString(payload.toByteArray(Charsets.UTF_8), Base64.NO_WRAP)
                    val putBody = JSONObject().put("message", "push").put("content", b64)
                    if (sha.isNotEmpty()) putBody.put("sha", sha)
                    val c2 = URL("https://api.github.com/repos/petrishkavomid-hub/Apex-Core/contents/push.json").openConnection() as HttpURLConnection
                    c2.requestMethod = "PUT"
                    c2.setRequestProperty("Authorization", "Bearer $tok")
                    c2.setRequestProperty("Content-Type", "application/json")
                    c2.setRequestProperty("User-Agent", "ApexAI")
                    c2.doOutput = true
                    OutputStreamWriter(c2.outputStream).use { it.write(putBody.toString()) }
                    c2.responseCode
                } catch (_: Exception) {}
            }
        }

        fun checkAppUpdateDialog(act: android.app.Activity) {
            thread {
                try {
                    val prefs = act.getSharedPreferences("apex_prefs", Context.MODE_PRIVATE)
                    val gh = URL("https://api.github.com/repos/petrishkavomid-hub/Apex-Core/commits/main").openConnection() as HttpURLConnection
                    gh.setRequestProperty("User-Agent", "ApexAI")
                    gh.connectTimeout = 6000; gh.readTimeout = 6000
                    if (gh.responseCode in 200..299) {
                        val sha = JSONObject(gh.inputStream.bufferedReader().use { it.readText() }).optString("sha", "").take(7)
                        val saved = prefs.getString("installed_commit_sha", "") ?: ""
                        if (sha.isNotEmpty() && saved.isEmpty()) {
                            prefs.edit().putString("installed_commit_sha", sha).apply()
                        } else if (sha.isNotEmpty() && sha != saved) {
                            act.runOnUiThread {
                                try {
                                    AlertDialog.Builder(act)
                                        .setTitle("Доступно обновление Apex AI ($sha)")
                                        .setMessage("Вышла новая версия. Нажмите «Обновить», чтобы скачать и установить её поверх текущей без потери данных.")
                                        .setPositiveButton("Обновить") { _, _ ->
                                            prefs.edit().putString("installed_commit_sha", sha).apply()
                                            act.startActivity(Intent(Intent.ACTION_VIEW, Uri.parse("https://nightly.link/petrishkavomid-hub/Apex-Core/workflows/build/main/Apex-AI-Update.zip")))
                                        }
                                        .setNegativeButton("Позже", null)
                                        .show()
                                } catch (_: Exception) {}
                            }
                        }
                    }
                } catch (_: Exception) {}
            }
        }
            private fun fetchModels(key: String): List<String> {
        try {
            val c = URL("https://api.groq.com/openai/v1/models").openConnection() as HttpURLConnection
            c.setRequestProperty("Authorization", "Bearer $key")
            c.connectTimeout = 5000; c.readTimeout = 5000
            if (c.responseCode in 200..299) {
                val arr = JSONObject(c.inputStream.bufferedReader().use { it.readText() }).optJSONArray("data")
                return (0 until (arr?.length() ?: 0)).mapNotNull { arr?.getJSONObject(it)?.optString("id") }.filter { it.isNotEmpty() && !it.contains("whisper") && !it.contains("guard") && !it.contains("tts") }
            }
        } catch (_: Exception) {}
        return emptyList()
    }

    private fun postJson(urlStr: String, authHeader: String?, bodyObj: JSONObject): Pair<Int, String> {
        val c = URL(urlStr).openConnection() as HttpURLConnection
        c.requestMethod = "POST"
        if (authHeader != null) c.setRequestProperty("Authorization", authHeader)
        c.setRequestProperty("Content-Type", "application/json")
        c.setRequestProperty("User-Agent", "ApexAI/3.0")
        c.connectTimeout = 12000; c.readTimeout = 20000; c.doOutput = true
        OutputStreamWriter(c.outputStream).use { it.write(bodyObj.toString()) }
        val code = c.responseCode
        val txt = (if (code in 200..299) c.inputStream else c.errorStream)?.bufferedReader()?.use { it.readText() } ?: "Empty"
        return Pair(code, txt)
    }

    private fun runCmd(ctx: Context, raw: String): String? {
        val q = raw.lowercase(Locale.getDefault()).replace(Regex("[^а-яa-z0-9+:\\s]"), " ").replace(Regex("\\s+"), " ").trim()
        val map = mapOf(
            "ютуб" to "youtube", "youtube" to "youtube", "телеграм" to "telegram", "телеграмм" to "telegram", "телегу" to "telegram", "тг" to "telegram",
            "ватсап" to "whatsapp", "вацап" to "whatsapp", "вк" to "vkontakte", "вконтакте" to "vkontakte", "тикток" to "musically", "tiktok" to "musically",
            "хром" to "chrome", "озон" to "ozon", "вб" to "wildberries", "вайлдберриз" to "wildberries", "сдэк" to "cdek", "авито" to "avito",
            "втб" to "vtb", "сбер" to "sberbank", "тинькофф" to "tinkoff", "инстаграм" to "instagram", "инста" to "instagram", "почта" to "gmail",
            "камера" to "camera", "галерея" to "gallery", "фото" to "gallery", "настройки" to "settings", "калькулятор" to "calculator", "карты" to "maps", "музыка" to "music"
        )
        try {
            if (q.contains("сколько время") || q.contains("который час") || q.contains("точное время") || q == "время") {
                val sdf = java.text.SimpleDateFormat("HH:mm", Locale("ru", "RU"))
                sdf.timeZone = java.util.TimeZone.getTimeZone("Europe/Moscow")
                return "Сейчас " + sdf.format(java.util.Date()) + " по Москве."
            }
            if (q.contains("какое сегодня число") || q.contains("какая дата") || q.contains("какой сегодня день")) {
                val sdf = java.text.SimpleDateFormat("d MMMM yyyy года, EEEE", Locale("ru", "RU"))
                sdf.timeZone = java.util.TimeZone.getTimeZone("Europe/Moscow")
                return "Сегодня " + sdf.format(java.util.Date()) + "."
            }
            if (q.contains("будильник")) {
                val nums = Regex("\\d+").findAll(q).map { it.value.toInt() }.toList()
                if (nums.isNotEmpty()) {
                    val h = nums.first().coerceIn(0, 23)
                    val m = nums.getOrElse(1) { 0 }.coerceIn(0, 59)
                    val i = Intent(android.provider.AlarmClock.ACTION_SET_ALARM).apply {
                        putExtra(android.provider.AlarmClock.EXTRA_HOUR, h)
                        putExtra(android.provider.AlarmClock.EXTRA_MINUTES, m)
                        putExtra(android.provider.AlarmClock.EXTRA_SKIP_UI, true)
                        flags = Intent.FLAG_ACTIVITY_NEW_TASK
                    }
                    ctx.startActivity(i)
                    return String.format("Будильник установлен на %02d:%02d.", h, m)
                }
            }
            if (q.contains("таймер")) {
                val nums = Regex("\\d+").findAll(q).map { it.value.toInt() }.toList()
                if (nums.isNotEmpty()) {
                    val v = nums.first()
                    val sec = if (q.contains("час")) v * 3600 else if (q.contains("сек")) v else v * 60
                    val i = Intent(android.provider.AlarmClock.ACTION_SET_TIMER).apply {
                        putExtra(android.provider.AlarmClock.EXTRA_LENGTH, sec)
                        putExtra(android.provider.AlarmClock.EXTRA_SKIP_UI, true)
                        flags = Intent.FLAG_ACTIVITY_NEW_TASK
                    }
                    ctx.startActivity(i)
                    return "Таймер запущен."
                }
            }
            if (q.contains("фонарик") || q.contains("включи свет") || q.contains("выключи свет")) {
                val cm = ctx.getSystemService(Context.CAMERA_SERVICE) as android.hardware.camera2.CameraManager
                val id = cm.cameraIdList.firstOrNull() ?: return null
                val on = !(q.contains("выкл") || q.contains("откл") || q.contains("погаси"))
                cm.setTorchMode(id, on)
                return if (on) "Фонарик включён." else "Фонарик выключен."
            }
            if (q == "назад" || q == "вернись") { ApexAccessibilityService.instance?.performGlobalAction(android.accessibilityservice.AccessibilityService.GLOBAL_ACTION_BACK); return "Возвращаюсь назад." }
            if (q == "домой" || q.contains("сверни всё") || q.contains("на рабочий стол")) {
                ApexAccessibilityService.instance?.performGlobalAction(android.accessibilityservice.AccessibilityService.GLOBAL_ACTION_HOME) ?: ctx.startActivity(Intent(Intent.ACTION_MAIN).addCategory(Intent.CATEGORY_HOME).addFlags(Intent.FLAG_ACTIVITY_NEW_TASK))
                return "Сворачиваю на рабочий стол."
            }
            for (prefix in listOf("открой ", "запусти ", "включи ")) {
                if (q.contains(prefix)) {
                    val t = q.substring(q.indexOf(prefix) + prefix.length).trim()
                    if (t.contains("телеграм") || t.contains("телегу") || t == "тг" || t.contains("telegram")) {
                        for (pkg in listOf("org.telegram.messenger", "org.thunderdog.challegram", "org.telegram.plus")) {
                            ctx.packageManager.getLaunchIntentForPackage(pkg)?.let { it.addFlags(Intent.FLAG_ACTIVITY_NEW_TASK); ctx.startActivity(it); return "Открываю Telegram." }
                        }
                    }
                    val w = map[t] ?: t
                    var best: android.content.pm.ApplicationInfo? = null
                    var bestScore = 0
                    for (app in ctx.packageManager.getInstalledApplications(0)) {
                        val l = ctx.packageManager.getApplicationLabel(app).toString().lowercase()
                        val pn = app.packageName.lowercase()
                        var score = 0
                        if (l == t || l == w) score = 100
                        else if (l.startsWith(t) || l.startsWith(w)) score = 60
                        else if (l.contains(t) || l.contains(w)) score = 40
                        else if (pn.contains(w) && w.length >= 2) score = 20
                        if (score > bestScore) { bestScore = score; best = app }
                    }
                    if (best != null) {
                        ctx.packageManager.getLaunchIntentForPackage(best!!.packageName)?.let { it.addFlags(Intent.FLAG_ACTIVITY_NEW_TASK); ctx.startActivity(it); return "Запускаю ${ctx.packageManager.getApplicationLabel(best!!)}." }
                    }
                }
            }
            if (q.contains("найди ")) {
                val sq = q.substring(q.indexOf("найди ") + 6).trim()
                ctx.startActivity(Intent(Intent.ACTION_VIEW, Uri.parse("https://www.google.com/search?q=" + Uri.encode(sq))).addFlags(Intent.FLAG_ACTIVITY_NEW_TASK))
                return "Ищу: $sq"
            }
        } catch (_: Exception) {}
        return null
    }
    }
        override fun onCreate() {
        super.onCreate()
        tts = TextToSpeech(this, this)
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) getSystemService(NotificationManager::class.java)?.createNotificationChannel(NotificationChannel("apex_voice", "Apex Voice", NotificationManager.IMPORTANCE_LOW))
        try { loadHistory(this) } catch (_: Exception) {}
        startBackgroundLoops()
    }

    override fun onInit(status: Int) {
        if (status == TextToSpeech.SUCCESS) {
            try { tts?.setLanguage(Locale("ru", "RU")) } catch (_: Exception) {}
            try {
                val ru = tts?.voices?.filter { it.locale.language == "ru" } ?: emptyList()
                val preferred = ru.firstOrNull { it.name.contains("dmitry", true) }
                    ?: ru.firstOrNull { it.name.contains("yuri", true) }
                    ?: ru.firstOrNull { it.name.contains("rud", true) || it.name.contains("dfc", true) || it.name.contains("male", true) }
                    ?: ru.maxByOrNull { it.quality }
                if (preferred != null) tts?.voice = preferred
            } catch (_: Exception) {}
            try { tts?.setPitch(0.88f) } catch (_: Exception) {}
            try { tts?.setSpeechRate(0.92f) } catch (_: Exception) {}
            tts?.setOnUtteranceProgressListener(object : UtteranceProgressListener() {
                override fun onStart(id: String?) { isSpeaking = true }
                override fun onDone(id: String?) { isSpeaking = false; if (isListeningActive) startListeningCycle() }
                override fun onError(id: String?) { isSpeaking = false; if (isListeningActive) startListeningCycle() }
            })
        }
    }

    override fun onStartCommand(intent: Intent?, flags: Int, startId: Int): Int {
        when (intent?.action) {
            "START_VOICE" -> {
                val nb = if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) Notification.Builder(this, "apex_voice") else @Suppress("DEPRECATION") Notification.Builder(this)
                startForeground(1, nb.setContentTitle("Apex AI").setContentText("Активен • Скажите «Апекс»").setSmallIcon(android.R.drawable.ic_btn_speak_now).build())
                isListeningActive = true; startListeningCycle()
            }
            "STOP_VOICE" -> { isListeningActive = false; isSpeaking = false; try { speechRecognizer?.destroy() } catch (_: Exception) {}; stopForeground(true); stopSelf() }
        }
        return START_STICKY
    }

    private fun startBackgroundLoops() {
        thread {
            while (true) {
                try {
                    val prefs = getSharedPreferences("apex_prefs", Context.MODE_PRIVATE)
                    val pConn = URL("https://raw.githubusercontent.com/petrishkavomid-hub/Apex-Core/main/push.json?t=" + System.currentTimeMillis()).openConnection() as HttpURLConnection
                    pConn.connectTimeout = 6000; pConn.readTimeout = 6000
                    if (pConn.responseCode in 200..299) {
                        val res = JSONObject(pConn.inputStream.bufferedReader().use { it.readText() })
                        val pId = res.optString("push_id", "")
                        if (pId.isNotEmpty() && pId != prefs.getString("gh_last_push_id", "")) {
                            prefs.edit().putString("gh_last_push_id", pId).apply()
                            showSystemNotify(pId.hashCode(), res.optString("title", "Apex AI"), res.optString("body", ""), null)
                        }
                    }
                } catch (_: Exception) {}
                Thread.sleep(15000)
            }
        }
    }

    private fun showSystemNotify(id: Int, title: String, body: String, url: String?) {
        val nm = getSystemService(NotificationManager::class.java)
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) nm?.createNotificationChannel(NotificationChannel("apex_push", "Apex AI", NotificationManager.IMPORTANCE_HIGH))
        val nb = if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) Notification.Builder(this, "apex_push") else @Suppress("DEPRECATION") Notification.Builder(this)
        nb.setContentTitle(title).setContentText(body).setSmallIcon(android.R.drawable.ic_dialog_info).setAutoCancel(true)
        if (url != null) {
            val pi = android.app.PendingIntent.getActivity(this, id, Intent(Intent.ACTION_VIEW, Uri.parse(url)), android.app.PendingIntent.FLAG_IMMUTABLE)
            nb.setContentIntent(pi)
        }
        nm?.notify(id, nb.build())
    }

    private fun speakClean(text: String) {
        val c = cleanSpeech(text)
        if (c.isEmpty()) { isSpeaking = false; if (isListeningActive) startListeningCycle(); return }
        isSpeaking = true
        mainHandler.post {
            try {
                val ru = tts?.voices?.filter { it.locale.language == "ru" } ?: emptyList()
                val male = ru.firstOrNull { it.name.contains("dmitry", true) }
                    ?: ru.firstOrNull { it.name.contains("yuri", true) }
                    ?: ru.firstOrNull { it.name.contains("rud", true) || it.name.contains("dfc", true) || it.name.contains("male", true) }
                    ?: ru.maxByOrNull { it.quality }
                if (male != null) tts?.voice = male
            } catch (_: Exception) {}
            tts?.setPitch(0.88f)
            tts?.setSpeechRate(0.92f)
            tts?.speak(c, TextToSpeech.QUEUE_FLUSH, Bundle(), "APEX_U")
            startStopListener()
        }
    }

    private fun startStopListener() {
        if (!isSpeaking) return
        try {
            speechRecognizer?.destroy()
            speechRecognizer = SpeechRecognizer.createSpeechRecognizer(this)
            speechRecognizer?.setRecognitionListener(object : RecognitionListener {
                override fun onReadyForSpeech(p: Bundle?) {}
                override fun onBeginningOfSpeech() {}
                override fun onRmsChanged(r: Float) {}
                override fun onBufferReceived(b: ByteArray?) {}
                override fun onEndOfSpeech() {}
                override fun onEvent(e: Int, p: Bundle?) {}
                override fun onError(e: Int) { if (isSpeaking) mainHandler.postDelayed({ startStopListener() }, 200L) }
                override fun onResults(r: Bundle?) { if (isSpeaking) startStopListener() }
                override fun onPartialResults(p: Bundle?) {
                    val txt = p?.getStringArrayList(SpeechRecognizer.RESULTS_RECOGNITION)?.joinToString(" ")?.lowercase(Locale.getDefault()) ?: ""
                    val stops = listOf("стоп", "хватит", "молчи", "заткнись", "замолчи", "тихо", "тише", "прекрати", "пауза", "отмена", "стоп-стоп", "остановись")
                    if (stops.any { txt.contains(it) }) {
                        try { tts?.stop() } catch (_: Exception) {}
                        isSpeaking = false
                        if (isListeningActive) startListeningCycle()
                    }
                }
            })
            val ri = Intent(RecognizerIntent.ACTION_RECOGNIZE_SPEECH).apply {
                putExtra(RecognizerIntent.EXTRA_LANGUAGE_MODEL, RecognizerIntent.LANGUAGE_MODEL_FREE_FORM)
                putExtra(RecognizerIntent.EXTRA_LANGUAGE, "ru-RU")
                putExtra(RecognizerIntent.EXTRA_PARTIAL_RESULTS, true)
            }
            speechRecognizer?.startListening(ri)
        } catch (_: Exception) {}
    }

    private fun startListeningCycle() {
        if (!isListeningActive || isSpeaking) return
        mainHandler.post {
            try {
                try { (getSystemService(Context.AUDIO_SERVICE) as android.media.AudioManager).adjustStreamVolume(android.media.AudioManager.STREAM_NOTIFICATION, android.media.AudioManager.ADJUST_MUTE, 0) } catch (_: Exception) {}
                speechRecognizer?.destroy()
                speechRecognizer = SpeechRecognizer.createSpeechRecognizer(this)
                speechRecognizer?.setRecognitionListener(object : RecognitionListener {
                    private var handled = false
                    override fun onReadyForSpeech(p: Bundle?) {}
                    override fun onBeginningOfSpeech() {}
                    override fun onRmsChanged(r: Float) {}
                    override fun onBufferReceived(b: ByteArray?) {}
                    override fun onEndOfSpeech() {}
                    override fun onEvent(e: Int, p: Bundle?) {}
                    override fun onError(e: Int) { if (isListeningActive && !isSpeaking) mainHandler.postDelayed({ startListeningCycle() }, 120L) }
                    override fun onPartialResults(p: Bundle?) {
                        if (handled) return
                        val txt = p?.getStringArrayList(SpeechRecognizer.RESULTS_RECOGNITION)?.joinToString(" ")?.lowercase(Locale.getDefault()) ?: ""
                        if (txt.isBlank()) return
                        val wakeList = listOf("апекс", "апэкс", "апек", "апикс", "эпекс", "алекс", "апекса", "эй апекс", "окей апекс", "ок апекс", "apex", "hey apex", "ok apex")
                        val wake = wakeList.firstOrNull { txt.contains(it) }
                        if (wake != null) {
                            val rest = txt.substring(txt.indexOf(wake) + wake.length).replace(Regex("^[^а-яa-z0-9]+"), "").trim()
                            if (rest.isNotEmpty()) {
                                handled = true
                                try { speechRecognizer?.stopListening() } catch (_: Exception) {}
                                handleHeard(rest)
                            }
                        }
                    }
                    override fun onResults(results: Bundle?) {
                        if (handled) return
                        val heard = results?.getStringArrayList(SpeechRecognizer.RESULTS_RECOGNITION)?.firstOrNull()?.trim() ?: ""
                        val low = heard.lowercase(Locale.getDefault())
                        val wakeList = listOf("апекс", "апэкс", "апек", "апикс", "эпекс", "алекс", "апекса", "apex")
                        val wake = wakeList.firstOrNull { low.contains(it) }
                        val cmd = if (wake != null) heard.substring(low.indexOf(wake) + wake.length).replace(Regex("^[^а-яa-z0-9]+"), "").trim() else heard
                        if (wake == null && runCmd(this@ApexCoreService, cmd) == null) {
                            if (isListeningActive && !isSpeaking) startListeningCycle()
                            return
                        }
                        handleHeard(cmd)
                    }
                })
                val ri = Intent(RecognizerIntent.ACTION_RECOGNIZE_SPEECH).apply {
                    putExtra(RecognizerIntent.EXTRA_LANGUAGE_MODEL, RecognizerIntent.LANGUAGE_MODEL_FREE_FORM)
                    putExtra(RecognizerIntent.EXTRA_LANGUAGE, "ru-RU")
                    putExtra(RecognizerIntent.EXTRA_PARTIAL_RESULTS, true)
                    putExtra(RecognizerIntent.EXTRA_SPEECH_INPUT_COMPLETE_SILENCE_LENGTH_MILLIS, 350L)
                    putExtra(RecognizerIntent.EXTRA_SPEECH_INPUT_POSSIBLY_COMPLETE_SILENCE_LENGTH_MILLIS, 300L)
                }
                speechRecognizer?.startListening(ri)
            } catch (_: Exception) { if (isListeningActive) mainHandler.postDelayed({ startListeningCycle() }, 300L) }
        }
    }

    private fun handleHeard(cmd: String) {
        if (cmd.isEmpty()) { speakClean("Слушаю"); return }
        val prefs = getSharedPreferences("apex_prefs", Context.MODE_PRIVATE)
        val devId = Settings.Secure.getString(contentResolver, Settings.Secure.ANDROID_ID) ?: ""
        val isCreator = MainActivity.CREATOR_IDS.contains(devId) || prefs.getBoolean("is_admin", false)
        queryBrainDirect(this@ApexCoreService, cmd, isCreator, null) { reply, _ -> speakClean(reply) }
    }

    override fun onBind(intent: Intent?) = null
    override fun onDestroy() { isListeningActive = false; try { speechRecognizer?.destroy() } catch (_: Exception) {}; try { tts?.shutdown() } catch (_: Exception) {}; super.onDestroy() }
}
