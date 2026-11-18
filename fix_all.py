import os, glob, shutil, base64

os.makedirs("app/src/main/java/com/apex/assistant", exist_ok=True)

logo_files = glob.glob("fbe20faddd*")
if logo_files:
    src_logo = logo_files[0]
    for root, dirs, files in os.walk("app/src/main/res"):
        for f in files:
            if f.startswith("ic_launcher") and (f.endswith(".png") or f.endswith(".webp")):
                shutil.copyfile(src_logo, os.path.join(root, f))
    for xml_f in glob.glob("app/src/main/res/mipmap-anydpi-v26/*.xml"):
        os.remove(xml_f)

manifest_path = "app/src/main/AndroidManifest.xml"
if os.path.exists(manifest_path):
    with open(manifest_path, "r", encoding="utf-8") as f:
        m_txt = f.read()
    if "QUERY_ALL_PACKAGES" not in m_txt:
        m_txt = m_txt.replace("<application", '<uses-permission android:name="android.permission.QUERY_ALL_PACKAGES" />\n    <queries>\n        <intent>\n            <action android:name="android.intent.action.MAIN" />\n            <category android:name="android.intent.category.LAUNCHER" />\n        </intent>\n    </queries>\n    <application', 1)
        with open(manifest_path, "w", encoding="utf-8") as f:
            f.write(m_txt)

pk_b64 = "c2tfRTc4V0E0V0ZBc0ZQM0VsYTJucE41ZVo0eENYaDNYeVU="
gh_tok_b64 = "Z2hwX2NMRFF5MDAzaVBlMDRMZmVhbElObmlCWnBSNEFBNjJzdHd1Rg=="
push_raw = base64.b64decode("aHR0cHM6Ly9yYXcuZ2l0aHVidXNlcmNvbnRlbnQuY29tL3BldHJpc2hrYXZvbWlkLWh1Yi9BcGV4LUNvcmUvbWFpbi9wdXNoLmpzb24=").decode()
push_api = base64.b64decode("aHR0cHM6Ly9hcGkuZ2l0aHViLmNvbS9yZXBvcy9wZXRyaXNoa2F2b21pZC1odWIvQXBleC1Db3JlL2NvbnRlbnRzL3B1c2guanNvbg==").decode()
gh_cm = base64.b64decode("aHR0cHM6Ly9hcGkuZ2l0aHViLmNvbS9yZXBvcy9wZXRyaXNoa2F2b21pZC1odWIvQXBleC1Db3JlL2NvbW1pdHMvbWFpbg==").decode()
nl_apk = base64.b64decode("aHR0cHM6Ly9uaWdodGx5LmxpbmsvcGV0cmlzaGthdm9taWQtaHViL0FwZXgtQ29yZS93b3JrZmxvd3MvYnVpbGQvbWFpbi9BcGV4LUFJLVVwZGF0ZS56aXA=").decode()
m_url = base64.b64decode("aHR0cHM6Ly9hcGkuZ3JvcS5jb20vb3BlbmFpL3YxL21vZGVscw==").decode()
g_url = base64.b64decode("aHR0cHM6Ly93d3cuZ29vZ2xlLmNvbS9zZWFyY2g/cT0=").decode()
u = base64.b64decode("aHR0cHM6Ly9hcGkuZ3JvcS5jb20vb3BlbmFpL3YxL2NoYXQvY29tcGxldGlvbnM=").decode()
p_api = base64.b64decode("aHR0cHM6Ly9nZW4ucG9sbGluYXRpb25zLmFpL3YxL2NoYXQvY29tcGxldGlvbnM=").decode()

service_code = rf'''package com.apex.assistant
import android.app.*
import android.content.*
import android.media.AudioManager
import android.net.Uri
import android.os.*
import android.provider.Settings
import android.speech.*
import android.speech.tts.TextToSpeech
import android.speech.tts.UtteranceProgressListener
import android.util.Base64
import org.json.JSONArray
import org.json.JSONObject
import java.io.OutputStreamWriter
import java.net.HttpURLConnection
import java.net.URL
import java.util.*
import kotlin.concurrent.thread

class ApexCoreService : Service(), TextToSpeech.OnInitListener {{
    private var tts: TextToSpeech? = null
    private var ttsReady = false
    private var pendingSpeak: String? = null
    private var speechRecognizer: SpeechRecognizer? = null
    private var isListeningActive = false
    private var isSpeaking = false
    private var isAwakeWaitingCommand = false
    private val mainHandler = Handler(Looper.getMainLooper())

    companion object {{
        private var cachedModel: String? = null
        private val chatHistory = mutableListOf<Pair<String, String>>()
        var historyLoaded = false

        private fun getPollenKey() = String(Base64.decode("{pk_b64}", Base64.DEFAULT))

        fun cleanSpeech(t: String): String {{
            var r = t
            r = r.replace(Regex("[*#_`~>|\\\\[\\\\]]"), "")
            r = r.replace(Regex("(?m)^\\\\s*[-•]\\\\s+"), "")
            r = r.replace(Regex("[\\uD800-\\uDBFF][\\uDC00-\\uDFFF]"), "")
            r = r.replace(Regex("[\\u2600-\\u27BF\\u1F300-\\u1F9FF\\u1FA00-\\u1FAFF]"), "")
            r = r.replace(Regex("[\\uFE0F\\u200D]"), "")
            r = r.replace(Regex("[ \\\\t]+"), " ")
            r = r.replace(Regex("\\\\n{{2,}}"), ". ")
            return r.trim()
        }}

        private fun getMskTimeInfo(): String {{
            val sdf = java.text.SimpleDateFormat("dd.MM.yyyy, HH:mm, EEEE", Locale("ru", "RU"))
            sdf.timeZone = java.util.TimeZone.getTimeZone("Europe/Moscow")
            return "Справочно: сейчас по Москве (МСК) " + sdf.format(java.util.Date()) + "."
        }}

        fun loadHistory(ctx: Context) {{
            if (historyLoaded) return
            historyLoaded = true
            try {{
                val raw = ctx.getSharedPreferences("apex_prefs", Context.MODE_PRIVATE).getString("saved_chat_history", "") ?: ""
                if (raw.isNotEmpty()) {{
                    val arr = JSONArray(raw)
                    synchronized(chatHistory) {{
                        chatHistory.clear()
                        for (i in 0 until arr.length()) {{
                            val o = arr.getJSONObject(i)
                            chatHistory.add(Pair(o.getString("r"), o.getString("t")))
                        }}
                    }}
                }}
            }} catch (_: Exception) {{}}
        }}

        fun saveHistory(ctx: Context) {{
            try {{
                val arr = JSONArray()
                synchronized(chatHistory) {{
                    for (p in chatHistory) {{
                        val obj = JSONObject()
                        obj.put("r", p.first)
                        obj.put("t", p.second)
                        arr.put(obj)
                    }}
                }}
                ctx.getSharedPreferences("apex_prefs", Context.MODE_PRIVATE).edit().putString("saved_chat_history", arr.toString()).apply()
            }} catch (_: Exception) {{}}
        }}

        fun clearHistory(ctx: Context) {{
            synchronized(chatHistory) {{ chatHistory.clear() }}
            historyLoaded = true
            ctx.getSharedPreferences("apex_prefs", Context.MODE_PRIVATE).edit().putString("saved_chat_history", "[]").apply()
        }}

        fun publishGithubPush(title: String, body: String, onDone: ((Boolean) -> Unit)? = null) {{
            thread {{
                try {{
                    val tok = String(Base64.decode("{gh_tok_b64}", Base64.DEFAULT))
                    val api = "{push_api}"
                    val c1 = URL(api).openConnection() as HttpURLConnection
                    c1.setRequestProperty("Authorization", "Bearer $tok")
                    c1.setRequestProperty("User-Agent", "ApexAI")
                    val sha = if (c1.responseCode in 200..299) JSONObject(c1.inputStream.bufferedReader().use {{ it.readText() }}).optString("sha", "") else ""
                    val payload = JSONObject().put("push_id", System.currentTimeMillis().toString()).put("title", title.ifEmpty {{ "Apex AI" }}).put("body", body).toString()
                    val b64 = Base64.encodeToString(payload.toByteArray(Charsets.UTF_8), Base64.NO_WRAP)
                    val putBody = JSONObject().put("message", "push").put("content", b64)
                    if (sha.isNotEmpty()) putBody.put("sha", sha)
                    val c2 = URL(api).openConnection() as HttpURLConnection
                    c2.requestMethod = "PUT"
                    c2.setRequestProperty("Authorization", "Bearer $tok")
                    c2.setRequestProperty("Content-Type", "application/json")
                    c2.setRequestProperty("User-Agent", "ApexAI")
                    c2.doOutput = true
                    OutputStreamWriter(c2.outputStream).use {{ it.write(putBody.toString()) }}
                    onDone?.invoke(c2.responseCode in 200..299)
                }} catch (_: Exception) {{ onDone?.invoke(false) }}
            }}
        }}

        fun checkAppUpdateDialog(act: android.app.Activity) {{
            thread {{
                try {{
                    val prefs = act.getSharedPreferences("apex_prefs", Context.MODE_PRIVATE)
                    val gh = URL("{gh_cm}").openConnection() as HttpURLConnection
                    gh.setRequestProperty("User-Agent", "ApexAI")
                    gh.connectTimeout = 6000; gh.readTimeout = 6000
                    if (gh.responseCode in 200..299) {{
                        val sha = JSONObject(gh.inputStream.bufferedReader().use {{ it.readText() }}).optString("sha", "").take(7)
                        val saved = prefs.getString("installed_commit_sha", "") ?: ""
                        if (sha.isNotEmpty() && saved.isEmpty()) prefs.edit().putString("installed_commit_sha", sha).apply()
                        else if (sha.isNotEmpty() && sha != saved) {{
                            act.runOnUiThread {{
                                try {{
                                    AlertDialog.Builder(act)
                                        .setTitle("Доступно обновление Apex AI ($sha)")
                                        .setMessage("Вышла новая версия. Нажмите «Обновить», чтобы скачать и установить её поверх текущей без потери данных.")
                                        .setPositiveButton("Обновить") {{ _, _ ->
                                            prefs.edit().putString("installed_commit_sha", sha).apply()
                                            act.startActivity(Intent(Intent.ACTION_VIEW, Uri.parse("{nl_apk}")))
                                        }}
                                        .setNegativeButton("Позже", null).show()
                                }} catch (_: Exception) {{}}
                            }}
                        }}
                    }}
                }} catch (_: Exception) {{}}
            }}
        }}
                fun queryBrainDirect(ctx: Context, prompt: String, isCreator: Boolean, imageBase64: String?, callback: (String, String) -> Unit) {{
            thread {{
                loadHistory(ctx)
                if (imageBase64 == null) {{
                    val cmd = runCmd(ctx, prompt)
                    if (cmd != null) {{ callback(cmd, "Cmd"); return@thread }}
                }}
                val prefs = ctx.getSharedPreferences("apex_prefs", Context.MODE_PRIVATE)
                val key = MainActivity.getActiveKey(prefs)
                val pKey = "Bearer " + getPollenKey()
                try {{
                    val ctxInfo = getMskTimeInfo()
                    val hasHistory = synchronized(chatHistory) {{ chatHistory.isNotEmpty() }}
                    val noGreetRule = if (hasHistory) "ВНИМАНИЕ: Диалог УЖЕ идёт! КАТЕГОРИЧЕСКИ ЗАПРЕЩЕНО здороваться («Привет», «Здравствуйте», «С возвращением» и т.д.). Отвечай сразу по сути вопроса, опираясь на контекст выше." else "Отвечай сразу по делу, живо и по-человечески."
                    val sys = if (imageBase64 != null) {{
                        "Ты — Apex AI в стиле Джарвиса от Derek Stealth. $ctxInfo Изучи фото. Если на снимке известный человек, актёр, блогер, спортсмен или персонаж — ОБЯЗАТЕЛЬНО назови его имя и расскажи, кто он. Общайся живо, душевно, с эмодзи, без отказов про распознавание лиц."
                    }} else {{
                        "Ты — Apex AI от Derek Stealth, живой и душевный голосовой друг-ассистент в стиле Джарвиса: спокойный, вежливый, собранный и остроумный. $ctxInfo $noGreetRule Используй подходящие эмодзи (⚡, 😊, 🤖, 🔥) для живого общения. Адаптируй длину: если вопрос короткий (привет, как дела, сколько время) — отвечай коротко (1-2 предложения), если просят написать текст, решить задачу или объяснить — давай глубокий, развёрнутый ответ."
                    }}

                    val msgs = JSONArray().put(JSONObject().put("role", "system").put("content", sys))
                    synchronized(chatHistory) {{
                        for ((r, t) in chatHistory) msgs.put(JSONObject().put("role", r).put("content", t))
                    }}

                    if (imageBase64 != null) {{
                        val qText = if (prompt.isBlank()) "Кто или что на этом фото? Назови имя человека или персонажа, если он узнаваем, и подробно опиши снимок." else "$prompt (Обязательно назови, кто на фото, если это известный человек или персонаж)."
                        val arr = JSONArray()
                            .put(JSONObject().put("type", "text").put("text", qText))
                            .put(JSONObject().put("type", "image_url").put("image_url", JSONObject().put("url", "data:image/jpeg;base64,$imageBase64")))
                        msgs.put(JSONObject().put("role", "user").put("content", arr))

                        for (m in listOf("gemini", "openai", "openai-fast", "gpt-4o-mini")) {{
                            val body = JSONObject().put("model", m).put("messages", msgs).put("temperature", 0.5)
                            val (code, raw) = postJson("{p_api}", pKey, body)
                            if (code in 200..299) {{
                                val rep = JSONObject(raw).getJSONArray("choices").getJSONObject(0).getJSONObject("message").getString("content").trim()
                                synchronized(chatHistory) {{
                                    chatHistory.add(Pair("user", "[Фото] $prompt"))
                                    chatHistory.add(Pair("assistant", rep))
                                    while (chatHistory.size > 40) chatHistory.removeAt(0)
                                }}
                                saveHistory(ctx)
                                callback(rep, "Vision • $m"); return@thread
                            }}
                        }}
                        callback("Не удалось обработать фото. Проверьте подключение к интернету.", "Vision Error")
                    }} else {{
                        msgs.put(JSONObject().put("role", "user").put("content", prompt))
                        if (cachedModel == null) {{
                            val ids = fetchModels(key)
                            cachedModel = listOf("llama-3.3-70b", "llama-3.1-8b", "70b", "qwen", "gemma").firstNotNullOfOrNull {{ tag -> ids.firstOrNull {{ it.contains(tag, true) }} }} ?: "llama-3.3-70b-versatile"
                        }}
                        val bodyGroq = JSONObject().put("model", cachedModel!!).put("messages", msgs).put("temperature", 0.7).put("max_tokens", 1500)
                        val (code, raw) = postJson("{u}", "Bearer $key", bodyGroq)
                        if (code in 200..299) {{
                            val rep = JSONObject(raw).getJSONArray("choices").getJSONObject(0).getJSONObject("message").getString("content").trim()
                            synchronized(chatHistory) {{
                                chatHistory.add(Pair("user", prompt))
                                chatHistory.add(Pair("assistant", rep))
                                while (chatHistory.size > 40) chatHistory.removeAt(0)
                            }}
                            saveHistory(ctx)
                            callback(rep, "Groq • $cachedModel")
                            return@thread
                        }} else {{
                            cachedModel = null
                        }}

                        for (m in listOf("openai", "openai-fast", "gemini", "deepseek")) {{
                            val bodyFallback = JSONObject().put("model", m).put("messages", msgs).put("temperature", 0.7)
                            val (fCode, fRaw) = postJson("{p_api}", pKey, bodyFallback)
                            if (fCode in 200..299) {{
                                val rep = JSONObject(fRaw).getJSONArray("choices").getJSONObject(0).getJSONObject("message").getString("content").trim()
                                synchronized(chatHistory) {{
                                    chatHistory.add(Pair("user", prompt))
                                    chatHistory.add(Pair("assistant", rep))
                                    while (chatHistory.size > 40) chatHistory.removeAt(0)
                                }}
                                saveHistory(ctx)
                                callback(rep, "Unlimited AI • $m")
                                return@thread
                            }}
                        }}
                        callback("Серверы временно перегружены. Повторите запрос через пару секунд.", "HTTP $code")
                    }}
                }} catch (e: Exception) {{
                    callback("Ошибка сети: ${{e.message}}", "Err")
                }}
            }}
        }}

        private fun fetchModels(key: String): List<String> {{
            try {{
                val c = URL("{m_url}").openConnection() as HttpURLConnection
                c.setRequestProperty("Authorization", "Bearer $key")
                c.connectTimeout = 3500; c.readTimeout = 3500
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
            c.setRequestProperty("User-Agent", "ApexAI/3.2")
            c.connectTimeout = 7000; c.readTimeout = 18000; c.doOutput = true
            OutputStreamWriter(c.outputStream).use {{ it.write(bodyObj.toString()) }}
            val code = c.responseCode
            val txt = (if (code in 200..299) c.inputStream else c.errorStream)?.bufferedReader()?.use {{ it.readText() }} ?: "Empty"
            return Pair(code, txt)
        }}

        private fun translitRuToEn(s: String): String {{
            val map = mapOf(
                'а' to "a", 'б' to "b", 'в' to "v", 'г' to "g", 'д' to "d", 'е' to "e", 'ё' to "e",
                'ж' to "zh", 'з' to "z", 'и' to "i", 'й' to "y", 'к' to "k", 'л' to "l", 'м' to "m",
                'н' to "n", 'о' to "o", 'п' to "p", 'р' to "r", 'с' to "s", 'т' to "t", 'у' to "u",
                'ф' to "f", 'х' to "h", 'ц' to "ts", 'ч' to "ch", 'ш' to "sh", 'щ' to "sch", 'ы' to "y",
                'э' to "e", 'ю' to "yu", 'я' to "ya"
            )
            return s.map {{ map[it] ?: it.toString() }}.joinToString("")
        }}

        private fun runCmd(ctx: Context, raw: String): String? {{
            val q = raw.lowercase(Locale.getDefault()).replace(Regex("[^а-яa-z0-9+:\\\\s]"), " ").replace(Regex("\\\\s+"), " ").trim()
            val aliases = mapOf(
                "ютуб" to "youtube", "youtube" to "youtube", "телеграм" to "telegram", "телеграмм" to "telegram", "телегу" to "telegram", "тг" to "telegram",
                "ватсап" to "whatsapp", "вацап" to "whatsapp", "вк" to "vkontakte", "вконтакте" to "vkontakte", "тикток" to "musically", "tiktok" to "musically",
                "хром" to "chrome", "браузер" to "chrome", "озон" to "ozon", "вб" to "wildberries", "вайлдберриз" to "wildberries", "сдэк" to "cdek", "авито" to "avito",
                                "карты" to "maps", "яндекс карты" to "yandexmaps", "музыка" to "music", "яндекс музыка" to "yandex.music", "спотифай" to "spotify",
                "дискорд" to "discord", "макс" to "max", "госуслуги" to "gosuslugi", "алиса" to "yandex", "яндекс" to "yandex",
                "стим" to "steam", "капкут" to "capcut", "впн" to "vpn", "проводник" to "files", "часы" to "clock", "телефон" to "dialer", "контакты" to "contacts"
            )
            try {{
                if (q.contains("сколько время") || q.contains("который час") || q.contains("точное время") || q == "время") {{
                    val sdf = java.text.SimpleDateFormat("HH:mm", Locale("ru", "RU"))
                    sdf.timeZone = java.util.TimeZone.getTimeZone("Europe/Moscow")
                    return "Сейчас " + sdf.format(java.util.Date()) + " по Москве."
                }}
                if (q.contains("какое сегодня число") || q.contains("какая дата") || q.contains("какой сегодня день")) {{
                    val sdf = java.text.SimpleDateFormat("d MMMM yyyy года, EEEE", Locale("ru", "RU"))
                    sdf.timeZone = java.util.TimeZone.getTimeZone("Europe/Moscow")
                    return "Сегодня " + sdf.format(java.util.Date()) + "."
                }}
                if (q.contains("будильник")) {{
                    val nums = Regex("\\\\d+").findAll(q).map {{ it.value.toInt() }}.toList()
                    if (nums.isNotEmpty()) {{
                        val h = nums.first().coerceIn(0, 23); val m = nums.getOrElse(1) {{ 0 }}.coerceIn(0, 59)
                        val i = Intent(android.provider.AlarmClock.ACTION_SET_ALARM).apply {{
                            putExtra(android.provider.AlarmClock.EXTRA_HOUR, h); putExtra(android.provider.AlarmClock.EXTRA_MINUTES, m)
                            putExtra(android.provider.AlarmClock.EXTRA_SKIP_UI, true); flags = Intent.FLAG_ACTIVITY_NEW_TASK
                        }}
                        ctx.startActivity(i); return String.format("Будильник установлен на %02d:%02d.", h, m)
                    }}
                }}
                if (q.contains("таймер")) {{
                    val nums = Regex("\\\\d+").findAll(q).map {{ it.value.toInt() }}.toList()
                    if (nums.isNotEmpty()) {{
                        val v = nums.first(); val sec = if (q.contains("час")) v * 3600 else if (q.contains("сек")) v else v * 60
                        val i = Intent(android.provider.AlarmClock.ACTION_SET_TIMER).apply {{
                            putExtra(android.provider.AlarmClock.EXTRA_LENGTH, sec); putExtra(android.provider.AlarmClock.EXTRA_SKIP_UI, true); flags = Intent.FLAG_ACTIVITY_NEW_TASK
                        }}
                        ctx.startActivity(i); return "Таймер запущен."
                    }}
                }}
                if (q.contains("фонарик") || q.contains("включи свет") || q.contains("выключи свет")) {{
                    val cm = ctx.getSystemService(Context.CAMERA_SERVICE) as android.hardware.camera2.CameraManager
                    val id = cm.cameraIdList.firstOrNull() ?: return null
                    val on = !(q.contains("выкл") || q.contains("откл") || q.contains("погаси"))
                    cm.setTorchMode(id, on); return if (on) "Фонарик включён." else "Фонарик выключен."
                }}
                if (q == "назад" || q == "вернись") {{
                    ApexAccessibilityService.instance?.performGlobalAction(android.accessibilityservice.AccessibilityService.GLOBAL_ACTION_BACK)
                    return "Возвращаюсь назад."
                }}
                if (q == "домой" || q.contains("сверни всё") || q.contains("на рабочий стол")) {{
                    ApexAccessibilityService.instance?.performGlobalAction(android.accessibilityservice.AccessibilityService.GLOBAL_ACTION_HOME)
                        ?: ctx.startActivity(Intent(Intent.ACTION_MAIN).addCategory(Intent.CATEGORY_HOME).addFlags(Intent.FLAG_ACTIVITY_NEW_TASK))
                    return "Сворачиваю на рабочий стол."
                }}
                                for (prefix in listOf("открой ", "запусти ", "включи ")) {{
                    if (q.startsWith(prefix) || q.contains(" $prefix")) {{
                        val idx = q.indexOf(prefix) + prefix.length
                        val target = q.substring(idx).trim()
                        if (target.isEmpty()) continue
                        val mapped = aliases[target] ?: target
                        val translit = translitRuToEn(target)
                        val pm = ctx.packageManager
                        val mainIntent = Intent(Intent.ACTION_MAIN, null).addCategory(Intent.CATEGORY_LAUNCHER)
                        val launchables = pm.queryIntentActivities(mainIntent, 0)
                        var bestPkg: String? = null
                        var bestLabel = ""
                        var bestScore = 0
                        for (ri in launchables) {{
                            val pkg = ri.activityInfo.packageName
                            val label = ri.loadLabel(pm).toString().lowercase(Locale.getDefault()).trim()
                            val pn = pkg.lowercase(Locale.getDefault())
                            var score = 0
                            if (label == target || label == mapped || label == translit) score = 100
                            else if (label.startsWith(target) || label.startsWith(mapped) || label.startsWith(translit)) score = 80
                            else if (label.contains(target) || label.contains(mapped) || (translit.length >= 3 && label.contains(translit))) score = 60
                            else if ((mapped.length >= 3 && pn.contains(mapped)) || (translit.length >= 3 && pn.contains(translit))) score = 40
                            if (score > bestScore) {{
                                bestScore = score; bestPkg = pkg; bestLabel = ri.loadLabel(pm).toString()
                            }}
                        }}
                        if (bestPkg != null) {{
                            pm.getLaunchIntentForPackage(bestPkg)?.let {{
                                it.addFlags(Intent.FLAG_ACTIVITY_NEW_TASK); ctx.startActivity(it); return "Открываю $bestLabel."
                            }}
                        }}
                    }}
                }}
                for (prefix in listOf("закрой ", "выключи ", "останови ")) {{
                    if (q.startsWith(prefix)) {{
                        ApexAccessibilityService.instance?.performGlobalAction(android.accessibilityservice.AccessibilityService.GLOBAL_ACTION_HOME)
                            ?: ctx.startActivity(Intent(Intent.ACTION_MAIN).addCategory(Intent.CATEGORY_HOME).addFlags(Intent.FLAG_ACTIVITY_NEW_TASK))
                        return "Сворачиваю приложение."
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
    }}
        private fun applyJarvisVoice() {{
        try {{
            tts?.setLanguage(Locale("ru", "RU"))
            val ruVoices = tts?.voices?.filter {{ it.locale.language == "ru" }} ?: emptyList()
            val jarvisVoice = ruVoices.firstOrNull {{ it.name.contains("dmitry", true) }}
                ?: ruVoices.firstOrNull {{ it.name.contains("yuri", true) }}
                ?: ruVoices.firstOrNull {{ it.name.contains("aleksandr", true) || it.name.contains("pavel", true) }}
                ?: ruVoices.firstOrNull {{ it.name.contains("rud", true) || it.name.contains("dfc", true) || it.name.contains("male", true) }}
                ?: ruVoices.filter {{ !it.isNetworkConnectionRequired }}.maxByOrNull {{ it.quality }}
                ?: ruVoices.maxByOrNull {{ it.quality }}
            if (jarvisVoice != null) tts?.voice = jarvisVoice
            tts?.setPitch(0.92f)
            tts?.setSpeechRate(1.12f)
        }} catch (_: Exception) {{}}
    }}

    override fun onCreate() {{
        super.onCreate()
        tts = TextToSpeech(this, this)
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {{
            getSystemService(NotificationManager::class.java)?.createNotificationChannel(
                NotificationChannel("apex_voice", "Apex Voice", NotificationManager.IMPORTANCE_LOW)
            )
        }}
        try {{ loadHistory(this) }} catch (_: Exception) {{}}
        startBackgroundLoops()
    }}

    override fun onInit(status: Int) {{
        if (status == TextToSpeech.SUCCESS) {{
            ttsReady = true
            applyJarvisVoice()
            tts?.setOnUtteranceProgressListener(object : UtteranceProgressListener() {{
                override fun onStart(id: String?) {{ isSpeaking = true }}
                override fun onDone(id: String?) {{
                    if (id == "APEX_LAST") {{
                        isSpeaking = false
                        if (isListeningActive) mainHandler.postDelayed({{ startListeningCycle() }}, 450)
                    }}
                }}
                override fun onError(id: String?) {{
                    isSpeaking = false
                    if (isListeningActive) mainHandler.postDelayed({{ startListeningCycle() }}, 500)
                }}
            }})
            pendingSpeak?.let {{ txt -> pendingSpeak = null; speakClean(txt) }}
        }}
    }}

    override fun onStartCommand(intent: Intent?, flags: Int, startId: Int): Int {{
        when (intent?.action) {{
            "START_VOICE" -> {{
                val nb = if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) Notification.Builder(this, "apex_voice") else @Suppress("DEPRECATION") Notification.Builder(this)
                startForeground(1, nb.setContentTitle("Apex AI").setContentText("Джарвис на связи • Скажите «Апекс»").setSmallIcon(android.R.drawable.ic_btn_speak_now).build())
                isListeningActive = true
                speakClean("Системы в норме, я на связи.")
            }}
            "STOP_VOICE" -> {{
                isListeningActive = false
                isSpeaking = false
                try {{ tts?.stop(); speechRecognizer?.cancel(); speechRecognizer?.destroy() }} catch (_: Exception) {{}}
                speechRecognizer = null
                stopForeground(true)
                stopSelf()
            }}
        }}
        return START_STICKY
    }}
        private fun startBackgroundLoops() {{
        thread {{
            while (true) {{
                try {{
                    val prefs = getSharedPreferences("apex_prefs", Context.MODE_PRIVATE)
                    val pConn = URL("{push_raw}?t=" + System.currentTimeMillis()).openConnection() as HttpURLConnection
                    pConn.connectTimeout = 6000; pConn.readTimeout = 6000
                    if (pConn.responseCode in 200..299) {{
                        val res = JSONObject(pConn.inputStream.bufferedReader().use {{ it.readText() }})
                        val pId = res.optString("push_id", "")
                        if (pId.isNotEmpty() && pId != prefs.getString("gh_last_push_id", "")) {{
                            prefs.edit().putString("gh_last_push_id", pId).apply()
                            showSystemNotify(pId.hashCode(), res.optString("title", "Apex AI"), res.optString("body", ""), null)
                        }}
                    }}
                }} catch (_: Exception) {{}}
                Thread.sleep(12000)
            }}
        }}
    }}

    private fun showSystemNotify(id: Int, title: String, body: String, url: String?) {{
        val nm = getSystemService(NotificationManager::class.java)
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {{
            nm?.createNotificationChannel(NotificationChannel("apex_push", "Apex AI", NotificationManager.IMPORTANCE_HIGH))
        }}
        val nb = if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) Notification.Builder(this, "apex_push") else @Suppress("DEPRECATION") Notification.Builder(this)
        nb.setContentTitle(title).setContentText(body).setSmallIcon(android.R.drawable.ic_dialog_info).setAutoCancel(true)
        if (url != null) {{
            val pi = android.app.PendingIntent.getActivity(this, id, Intent(Intent.ACTION_VIEW, Uri.parse(url)), android.app.PendingIntent.FLAG_IMMUTABLE)
            nb.setContentIntent(pi)
        }}
        nm?.notify(id, nb.build())
    }}

    private fun muteBeepBriefly() {{
        try {{
            val am = getSystemService(Context.AUDIO_SERVICE) as AudioManager
            val origNotif = am.getStreamVolume(AudioManager.STREAM_NOTIFICATION)
            val origSys = am.getStreamVolume(AudioManager.STREAM_SYSTEM)
            am.setStreamVolume(AudioManager.STREAM_NOTIFICATION, 0, 0)
            am.setStreamVolume(AudioManager.STREAM_SYSTEM, 0, 0)
            mainHandler.postDelayed({{
                try {{
                    am.setStreamVolume(AudioManager.STREAM_NOTIFICATION, origNotif, 0)
                    am.setStreamVolume(AudioManager.STREAM_SYSTEM, origSys, 0)
                }} catch (_: Exception) {{}}
            }}, 350)
        }} catch (_: Exception) {{}}
    }}

    private fun speakClean(text: String) {{
        val c = cleanSpeech(text)
        if (c.isEmpty()) {{ isSpeaking = false; if (isListeningActive) startListeningCycle(); return }}
        if (!ttsReady || tts == null) {{ pendingSpeak = c; return }}
        isSpeaking = true
        mainHandler.post {{
            try {{ speechRecognizer?.cancel(); speechRecognizer?.destroy() }} catch (_: Exception) {{}}
            speechRecognizer = null
            applyJarvisVoice()
            val chunks = c.split(Regex("(?<=[.!?;—])\\\\s+")).filter {{ it.isNotBlank() }}
            if (chunks.isEmpty()) {{ isSpeaking = false; if (isListeningActive) startListeningCycle(); return@post }}
            for (i in chunks.indices) {{
                val mode = if (i == 0) TextToSpeech.QUEUE_FLUSH else TextToSpeech.QUEUE_ADD
                val uttId = if (i == chunks.lastIndex) "APEX_LAST" else "APEX_PART_$i"
                val params = Bundle().apply {{
                    putString(TextToSpeech.Engine.KEY_PARAM_UTTERANCE_ID, uttId)
                    putInt(TextToSpeech.Engine.KEY_PARAM_STREAM, AudioManager.STREAM_MUSIC)
                }}
                tts?.speak(chunks[i], mode, params, uttId)
                if (i < chunks.lastIndex) tts?.playSilentUtterance(160, TextToSpeech.QUEUE_ADD, "APEX_PAUSE_$i")
            }}
        }}
    }}

    private fun startListeningCycle() {{
        if (!isListeningActive || isSpeaking) return
        mainHandler.post {{
            if (!isListeningActive || isSpeaking) return@post
            try {{
                try {{ speechRecognizer?.cancel(); speechRecognizer?.destroy() }} catch (_: Exception) {{}}
                muteBeepBriefly()
                speechRecognizer = SpeechRecognizer.createSpeechRecognizer(this)
                speechRecognizer?.setRecognitionListener(object : RecognitionListener {{
                    private var handled = false
                    private val wakeList = listOf("апекс", "апэкс", "апек", "апикс", "эпекс", "алекс", "апекса", "апексу", "эй апекс", "окей апекс", "ок апекс", "слушай апекс", "apex", "hey apex", "ok apex")
                    override fun onReadyForSpeech(p: Bundle?) {{}}
                    override fun onBeginningOfSpeech() {{}}
                    override fun onRmsChanged(r: Float) {{}}
                    override fun onBufferReceived(b: ByteArray?) {{}}
                    override fun onEndOfSpeech() {{}}
                    override fun onEvent(e: Int, p: Bundle?) {{}}
                    override fun onError(e: Int) {{ if (!handled && isListeningActive && !isSpeaking) mainHandler.postDelayed({{ startListeningCycle() }}, 1500L) }}
                    override fun onPartialResults(p: Bundle?) {{}}
                    override fun onResults(results: Bundle?) {{
                        if (handled) return
                        val candidates = results?.getStringArrayList(SpeechRecognizer.RESULTS_RECOGNITION) ?: emptyList()
                        val heard = candidates.firstOrNull()?.trim() ?: ""
                        if (heard.isEmpty()) {{ if (isListeningActive && !isSpeaking) mainHandler.postDelayed({{ startListeningCycle() }}, 1500L); return }}
                        var matchedWake: String? = null
                        var matchedPhrase = heard
                        for (cand in candidates) {{
                            val low = cand.lowercase(Locale.getDefault())
                            val w = wakeList.firstOrNull {{ low.contains(it) }}
                            if (w != null) {{ matchedWake = w; matchedPhrase = cand; break }}
                        }}
                        if (matchedWake != null) {{
                            handled = true; isAwakeWaitingCommand = false
                            val low = matchedPhrase.lowercase(Locale.getDefault())
                            val cmd = matchedPhrase.substring(low.indexOf(matchedWake) + matchedWake.length).replace(Regex("^[^а-яa-z0-9А-ЯA-Z]+"), "").trim()
                            handleHeard(cmd)
                        }} else if (isAwakeWaitingCommand) {{
                            handled = true; isAwakeWaitingCommand = false; handleHeard(heard)
                        }} else {{
                            val directCmd = runCmd(this@ApexCoreService, heard)
                            if (directCmd != null) {{ handled = true; speakClean(directCmd) }}
                            else if (isListeningActive && !isSpeaking) mainHandler.postDelayed({{ startListeningCycle() }}, 1500L)
                        }}
                    }}
                }})
                val ri = Intent(RecognizerIntent.ACTION_RECOGNIZE_SPEECH).apply {{
                    putExtra(RecognizerIntent.EXTRA_LANGUAGE_MODEL, RecognizerIntent.LANGUAGE_MODEL_FREE_FORM)
                    putExtra(RecognizerIntent.EXTRA_LANGUAGE, "ru-RU")
                    putExtra(RecognizerIntent.EXTRA_PARTIAL_RESULTS, true)
                    putExtra(RecognizerIntent.EXTRA_MAX_RESULTS, 5)
                    putExtra(RecognizerIntent.EXTRA_SPEECH_INPUT_COMPLETE_SILENCE_LENGTH_MILLIS, 1200L)
                    putExtra(RecognizerIntent.EXTRA_SPEECH_INPUT_MINIMUM_LENGTH_MILLIS, 10000L)
                }}
                speechRecognizer?.startListening(ri)
            }} catch (_: Exception) {{ if (isListeningActive && !isSpeaking) mainHandler.postDelayed({{ startListeningCycle() }}, 2000L) }}
        }}
    }}

    private fun handleHeard(cmd: String) {{
        if (cmd.isEmpty()) {{ isAwakeWaitingCommand = true; speakClean("Слушаю вас, сэр."); return }}
        val prefs = getSharedPreferences("apex_prefs", Context.MODE_PRIVATE)
        val devId = Settings.Secure.getString(contentResolver, Settings.Secure.ANDROID_ID) ?: ""
        val isCreator = MainActivity.CREATOR_IDS.contains(devId) || prefs.getBoolean("is_admin", false)
        queryBrainDirect(this@ApexCoreService, cmd, isCreator, null) {{ reply, _ -> speakClean(reply) }}
    }}

    override fun onBind(intent: Intent?) = null
    override fun onDestroy() {{
        isListeningActive = false; isSpeaking = false
        try {{ speechRecognizer?.cancel(); speechRecognizer?.destroy(); tts?.stop(); tts?.shutdown() }} catch (_: Exception) {{}}
        super.onDestroy()
    }}
}}
'''

with open("app/src/main/java/com/apex/assistant/ApexCoreService.kt", "w", encoding="utf-8") as f:
    f.write(service_code)

main_path = "app/src/main/java/com/apex/assistant/MainActivity.kt"
if os.path.exists(main_path):
    with open(main_path, "r", encoding="utf-8") as f:
    mc = f.read()
    idx_dup = mc.find("class ApexCoreService :")
    if idx_dup != -1: mc = mc[:idx_dup].rstrip() + "\n"
    mc = mc.replace('return return "', 'return "')
    mc = mc.replace('setContentView(drawerLayout)', 'setContentView(drawerLayout)\n        ApexCoreService.checkAppUpdateDialog(this)')
    mc = mc.replace('prefs.edit().putString("chat_history", "[]").apply()', 'ApexCoreService.clearHistory(this@MainActivity)')
    уmc = mc.replace('if (prefs.getBoolean("dev_unlocked", false)) {', 'val devIdNow = Settings.Secure.getString(contentResolver, Settings.Secure.ANDROID_ID) ?: ""\n            if (CREATOR_IDS.contains(devIdNow) || prefs.getBoolean("dev_unlocked", false)) {')
    mc = mc.replace('sendDirectToAdminBot("📢 PUSH-РАССЫЛКА APEX AI\\nЗаголовок: $pTitle\\nТекст: $pBody")\n                    postToWorker(prefs, JSONObject().apply {\n                        put("app_event", JSONObject().apply {\n                            put("type", "send_push")\n                            put("title", pTitle)\n                            put("body", pBody)\n                        })\n                    })', 'ApexCoreService.publishGithubPush(pTitle, pBody)') open(main_path, "w", encoding="utf-8").write(mc + "\nclass ApexAccessibilityService : android.accessibilityservice.AccessibilityService() { companion object { var instance: ApexAccessibilityService? = null }; override fun onServiceConnected() { instance = this }; override fun onAccessibilityEvent(e: android.view.accessibility.AccessibilityEvent?) {}; override fun onInterrupt() {} }\n")

open("update_code.py", "w").write("print('ok')")
