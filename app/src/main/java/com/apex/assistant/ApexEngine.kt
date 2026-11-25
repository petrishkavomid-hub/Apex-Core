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
    private const val AI_URL = "https://text.pollinations.ai/openai"
    private const val ADMIN_ID = 5347874574L
    private var torchOn = false

    fun runLocalCommand(ctx: Context, raw: String): String? {
        val q = raw.lowercase().trim()
        if (q.contains("фонарик")) {
            return try {
                val cm = ctx.getSystemService(Context.CAMERA_SERVICE) as CameraManager
                val id = cm.cameraIdList.firstOrNull() ?: return "Камера не найдена."
                torchOn = !q.contains("выкл") && !q.contains("погас")
                cm.setTorchMode(id, torchOn)
                if (torchOn) "Фонарик включён." else "Фонарик выключен."
            } catch (_: Exception) { "Не удалось переключить фонарик." }
        }
        if (q.contains("будильник")) {
            val m = Regex("(\\d{1,2})[:.\\s-](\\d{2})").find(q)
            if (m != null) {
                val h = m.groupValues.toIntOrNull() ?: 8
                val min = m.groupValues.toIntOrNull() ?: 0
                return try {
                    ctx.startActivity(Intent(AlarmClock.ACTION_SET_ALARM).apply {
                        putExtra(AlarmClock.EXTRA_HOUR, h)
                        putExtra(AlarmClock.EXTRA_MINUTES, min)
                        putExtra(AlarmClock.EXTRA_SKIP_UI, false)
                        addFlags(Intent.FLAG_ACTIVITY_NEW_TASK)
                    })
                    "Ставлю будильник на %02d:%02d.".format(h, min)
                } catch (_: Exception) { "Не удалось открыть часы." }
            }
        }
        if (q.startsWith("открой ") || q.startsWith("запусти ")) {
            val target = q.removePrefix("открой ").removePrefix("запусти ").trim()
            val aliases = mapOf(
                "ютуб" to "youtube",
                "телеграм" to "telegram",
                "тг" to "telegram",
                "ватсап" to "whatsapp",
                "вк" to "vkontakte",
                "настройки" to "settings",
                "камеру" to "camera",
                "браузер" to "chrome",
                "карты" to "maps"
            )
            val key = aliases[target] ?: target
            val pm = ctx.packageManager
            val found = pm.getInstalledApplications(0).firstOrNull {
                pm.getApplicationLabel(it).toString().lowercase().contains(key) ||
                    it.packageName.lowercase().contains(key)
            }
            if (found != null) {
                val launch = pm.getLaunchIntentForPackage(found.packageName)
                if (launch != null) {
                    launch.addFlags(Intent.FLAG_ACTIVITY_NEW_TASK)
                    ctx.startActivity(launch)
                    return "Открываю ${pm.getApplicationLabel(found)}."
                }
            }
        }
        return null
    }

    fun askAi(history: List<Pair<String, String>>, imageBase64: String?): String {
        return try {
            val msgs = JSONArray()
            msgs.put(JSONObject().put("role", "system").put("content", "Ты Apex AI — быстрый, умный и дружелюбный голосовой ассистент, созданный Derek Stealth. Отвечай по-русски, чётко, по делу и без смайликов."))
            history.takeLast(12).forEach { (role, text) ->
                msgs.put(JSONObject().put("role", role).put("content", text))
            }
            if (imageBase64 != null) {
                val lastIdx = msgs.length() - 1
                val lastText = msgs.getJSONObject(lastIdx).getString("content")
                val parts = JSONArray()
                    .put(JSONObject().put("type", "text").put("text", lastText.ifBlank { "Подробно опиши, что изображено на этом фото." }))
                    .put(JSONObject().put("type", "image_url").put("image_url", JSONObject().put("url", "data:image/jpeg;base64,$imageBase64")))
                msgs.getJSONObject(lastIdx).put("content", parts)
            }
            val payload = JSONObject()
                .put("model", if (imageBase64 != null) "openai" else "openai-fast")
                .put("messages", msgs)
            val c = URL(AI_URL).openConnection() as HttpURLConnection
            c.requestMethod = "POST"
            c.setRequestProperty("Content-Type", "application/json")
            c.connectTimeout = 10000
            c.readTimeout = 25000
            c.doOutput = true
            OutputStreamWriter(c.outputStream).use { it.write(payload.toString()) }
            val code = c.responseCode
            val raw = (if (code in 200..299) c.inputStream else c.errorStream)?.bufferedReader()?.use { it.readText() } ?: ""
            if (code in 200..299 && raw.trim().startsWith("{")) {
                JSONObject(raw).getJSONArray("choices").getJSONObject(0).getJSONObject("message").getString("content").trim()
            } else "Ошибка сервера ($code). Попробуйте ещё раз."
        } catch (e: Exception) {
            "Нет связи с сервером: ${e.localizedMessage ?: "таймаут"}"
        }
    }

    fun sendRating(stars: Int, comment: String, device: String): Boolean {
        val tok = BuildConfig.TG_BOT_TOKEN
        if (tok.isBlank()) return false
        return try {
            val text = "ОЦЕНКА ИЗ APEX AI 4.0\n\nОценка: ${"⭐".repeat(stars)} ($stars/5)\nУстройство: $device\nОтзыв: ${comment.ifBlank { "Без текста" }}"
            val body = JSONObject().put("chat_id", ADMIN_ID).put("text", text)
            val c = URL("https://api.telegram.org/bot$tok/sendMessage").openConnection() as HttpURLConnection
            c.requestMethod = "POST"
            c.setRequestProperty("Content-Type", "application/json")
            c.connectTimeout = 8000
            c.doOutput = true
            OutputStreamWriter(c.outputStream).use { it.write(body.toString()) }
            c.responseCode in 200..299
        } catch (_: Exception) { false }
    }
}
