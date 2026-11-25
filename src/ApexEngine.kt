package com.apex.assistant

import android.content.Context
import android.content.Intent
import android.hardware.camera2.CameraManager
import android.provider.AlarmClock
import org.json.JSONArray
import org.json.JSONObject
import java.io.OutputStreamWriter
import java.net.HttpURLConnection
import java.net.URL

object ApexEngine {
    private const val AI_URL = "https://pollinations.ai"
    private const val ADMIN_ID = 5347874574L
    const val CHANNEL_URL = "https://t.me"
    private var torchOn = false

    fun runLocalCommand(ctx: Context, raw: String): String? {
        val q = raw.lowercase().trim()
        if (q.contains("фонарик") || (torchOn && (q == "выключи" || q == "погаси" || q == "отключи"))) {
            return try {
                val cm = ctx.getSystemService(Context.CAMERA_SERVICE) as CameraManager
                val id = cm.cameraIdList.firstOrNull() ?: return "Камера не найдена."
                torchOn = !q.contains("выкл") && !q.contains("погас") && !q.contains("откл")
                cm.setTorchMode(id, torchOn)
                if (torchOn) "Фонарик включён." else "Фонарик выключен."
            } catch (_: Exception) { "Не удалось переключить фонарик." }
        }
        if (q.contains("будильник")) {
            val m = Regex("(\\d{1,2})[:.\\s-](\\d{2})").find(q) ?: return null
            val h = m.groupValues[1].toIntOrNull() ?: 8
            val min = m.groupValues[2].toIntOrNull() ?: 0
            return try {
                ctx.startActivity(Intent(AlarmClock.ACTION_SET_ALARM).apply {
                    putExtra(AlarmClock.EXTRA_HOUR, h); putExtra(AlarmClock.EXTRA_MINUTES, min); addFlags(Intent.FLAG_ACTIVITY_NEW_TASK)
                })
                "Ставлю будильник на %02d:%02d.".format(h, min)
            } catch (_: Exception) { "Не удалось открыть часы." }
        }
        if (q.contains("таймер")) {
            val num = Regex("(\\d{1,3})").find(q)?.groupValues?.getOrNull(1)?.toIntOrNull() ?: return null
            if (num <= 0) return null
            val sec = if (q.contains("сек")) num else num * 60
            return try {
                ctx.startActivity(Intent(AlarmClock.ACTION_SET_TIMER).apply {
                    putExtra(AlarmClock.EXTRA_LENGTH, sec); addFlags(Intent.FLAG_ACTIVITY_NEW_TASK)
                })
                "Запускаю таймер на $num ${if (q.contains("сек")) "сек." else "мин."}"
            } catch (_: Exception) { "Не удалось запустить таймер." }
        }
        if (q.startsWith("открой ") || q.startsWith("запусти ")) {
            val target = q.removePrefix("открой ").removePrefix("запусти ").trim()
            val aliases = mapOf("ютуб" to "youtube", "телеграм" to "telegram", "тг" to "telegram", "ватсап" to "whatsapp", "вк" to "vkontakte", "настройки" to "settings", "камеру" to "camera", "браузер" to "chrome", "карты" to "maps")
            val key = aliases[target] ?: target
            val pm = ctx.packageManager
            val found = pm.getInstalledApplications(0).firstOrNull { pm.getApplicationLabel(it).toString().lowercase().contains(key) || it.packageName.lowercase().contains(key) }
            val launch = found?.let { pm.getLaunchIntentForPackage(it.packageName) }
            if (launch != null) {
                launch.addFlags(Intent.FLAG_ACTIVITY_NEW_TASK); ctx.startActivity(launch)
                return "Открываю ${pm.getApplicationLabel(found)}."
            }
        }
        return null
    }

    fun askAi(history: List<Pair<String, String>>, imageBase64: String?): String {
        val models = if (imageBase64 != null) listOf("openai", "openai-large", "gpt-4o-mini") else listOf("openai-fast", "mistral", "llama")
        var lastErr = "Сервер временно недоступен"
        for (model in models) {
            try {
                val msgs = JSONArray().put(JSONObject().put("role", "system").put("content", "Ты Apex AI — умный и дружелюбный голосовой ассистент, созданный Derek Stealth. Отвечай по-русски, тепло, по делу и без смайликов."))
                val slice = if (imageBase64 != null) history.takeLast(1) else history.takeLast(6)
                slice.forEach { (r, t) -> msgs.put(JSONObject().put("role", r).put("content", t)) }
                if (imageBase64 != null) {
                    val last = msgs.getJSONObject(msgs.length() - 1)
                    val txt = last.getString("content").ifBlank { "Подробно опиши, что изображено на этом фото." }
                    last.put("content", JSONArray().put(JSONObject().put("type", "text").put("text", txt)).put(JSONObject().put("type", "image_url").put("image_url", JSONObject().put("url", "data:image/jpeg;base64,$imageBase64"))))
                }
                val c = (URL(AI_URL).openConnection() as HttpURLConnection).apply {
                    requestMethod = "POST"; setRequestProperty("Content-Type", "application/json"); connectTimeout = 12000; readTimeout = 25000; doOutput = true
                }
                OutputStreamWriter(c.outputStream).use { it.write(JSONObject().put("model", model).put("messages", msgs).toString()) }
                val code = c.responseCode
                val raw = (if (code in 200..299) c.inputStream else c.errorStream)?.bufferedReader()?.use { it.readText() } ?: ""
                if (code in 200..299 && raw.trim().startsWith("{")) {
                    val ans = JSONObject(raw).getJSONArray("choices").getJSONObject(0).getJSONObject("message").getString("content").trim()
                    if (ans.isNotBlank()) return ans
                }
                lastErr = "Ошибка сервера ($code)"
            } catch (e: Exception) { lastErr = "Нет связи: ${e.localizedMessage ?: "таймаут"}" }
        }
        return "$lastErr. Попробуйте ещё раз."
    }

    fun sendRating(stars: Int, comment: String, device: String): Pair<Boolean, String> {
        val tok = BuildConfig.TG_BOT_TOKEN
        if (tok.isBlank()) return false to "Токен бота не задан в настройках репозитория"
        return try {
            val text = "ОЦЕНКА ИЗ APEX AI\n\nОценка: $stars / 5\nУстройство: $device\nОтзыв: ${comment.ifBlank { "Без текста" }}"
            val c = (URL("https://telegram.org").openConnection() as HttpURLConnection).apply {
                requestMethod = "POST"; setRequestProperty("Content-Type", "application/json"); connectTimeout = 8000; doOutput = true
            }
            OutputStreamWriter(c.outputStream).use { it.write(JSONObject().put("chat_id", ADMIN_ID).put("text", text).toString()) }
            if (c.responseCode in 200..299) true to "Спасибо за оценку!" else false to "Ошибка Telegram (${c.responseCode})"
        } catch (_: Exception) { false to "Нет соединения с Telegram" }
    }
}
