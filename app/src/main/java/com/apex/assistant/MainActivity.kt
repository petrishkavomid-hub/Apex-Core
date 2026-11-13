package com.apex.assistant

import android.Manifest
import android.app.*
import android.content.*
import android.content.res.ColorStateList
import android.graphics.*
import android.graphics.drawable.GradientDrawable
import android.graphics.drawable.RippleDrawable
import android.net.Uri
import android.os.*
import android.provider.Settings
import android.speech.*
import android.speech.tts.TextToSpeech
import android.speech.tts.UtteranceProgressListener
import android.util.Base64
import android.view.Gravity
import android.view.View
import android.widget.*
import androidx.activity.result.contract.ActivityResultContracts
import androidx.appcompat.app.AppCompatActivity
import androidx.core.app.ActivityCompat
import androidx.drawerlayout.widget.DrawerLayout
import org.json.JSONArray
import org.json.JSONObject
import java.io.ByteArrayOutputStream
import java.io.OutputStreamWriter
import java.net.HttpURLConnection
import java.net.URL
import java.util.*
import kotlin.concurrent.thread

class MainActivity : AppCompatActivity() {

    companion object {
        val CREATOR_IDS = setOf("97def6cd87afc85f", "212239d20d74e965")
        const val CREATOR_TG_ID = "5347874574"
        const val BOT_TOKEN = "8813383592:AAEq3jtBj3G9qeSr3KRSvUhOEFpmCHYfuog"

        fun b64(s: String): String = String(Base64.decode(s, Base64.DEFAULT))

        fun getWorkerUrl(prefs: SharedPreferences): String {
            val saved = prefs.getString("worker_url", "")?.trim() ?: ""
            if (saved.isNotEmpty()) return saved
            return b64("aHR0cHM6Ly9hcGV4LWJvdC5wZXRyaXNoa2F2b21pZC53b3JrZXJzLmRldg==")
        }

        fun groqUrl(): String = b64("aHR0cHM6Ly9hcGkuZ3JvcS5jb20vb3BlbmFpL3YxL2NoYXQvY29tcGxldGlvbnM=")
        fun channelTgUri(): String = b64("dGc6Ly9yZXNvbHZlP2RvbWFpbj1BcGV4YXNzaXN0YW50Y29yZQ==")
        fun channelWebUrl(): String = b64("aHR0cHM6Ly90Lm1lL0FwZXhhc3Npc3RhbnRjb3Jl")
        fun tgApiHost(): String = b64("aHR0cHM6Ly9hcGkudGVsZWdyYW0ub3Jn")

        fun getActiveKey(prefs: SharedPreferences): String {
            val saved = prefs.getString("groq_key", "")?.trim() ?: ""
            if (saved.isNotEmpty()) return saved
            return "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"
        }

        fun sendDirectToAdminBot(text: String, onDone: ((Boolean) -> Unit)? = null) {
            thread {
                try {
                    val conn = URL("${tgApiHost()}/bot$BOT_TOKEN/sendMessage").openConnection() as HttpURLConnection
                    conn.requestMethod = "POST"
                    conn.setRequestProperty("Content-Type", "application/json")
                    conn.connectTimeout = 15000
                    conn.readTimeout = 15000
                    conn.doOutput = true
                    val payload = JSONObject().apply {
                        put("chat_id", CREATOR_TG_ID.toLong())
                        put("text", text)
                    }
                    OutputStreamWriter(conn.outputStream).use { it.write(payload.toString()) }
                    val ok = conn.responseCode in 200..299
                    onDone?.invoke(ok)
                } catch (_: Exception) {
                    onDone?.invoke(false)
                }
            }
        }

        fun postToWorker(prefs: SharedPreferences, payload: JSONObject, onResult: ((JSONObject?) -> Unit)? = null) {
            thread {
                try {
                    val conn = URL(getWorkerUrl(prefs)).openConnection() as HttpURLConnection
                    conn.requestMethod = "POST"
                    conn.setRequestProperty("Content-Type", "application/json")
                    conn.setRequestProperty("User-Agent", "ApexAI-Android/2.6")
                    conn.connectTimeout = 15000
                    conn.readTimeout = 15000
                    conn.doOutput = true
                    OutputStreamWriter(conn.outputStream).use { it.write(payload.toString()) }
                    if (conn.responseCode in 200..299) {
                        val txt = conn.inputStream.bufferedReader().use { it.readText() }
                        onResult?.invoke(try { JSONObject(txt) } catch (_: Exception) { JSONObject() })
                    } else {
                        onResult?.invoke(null)
                    }
                } catch (_: Exception) {
                    onResult?.invoke(null)
                }
            }
        }
    }

    private lateinit var drawerLayout: DrawerLayout
    private lateinit var chatScreen: LinearLayout
    private lateinit var infoScreen: ScrollView
    private lateinit var settingsScreen: ScrollView
    private lateinit var devScreen: ScrollView
    private lateinit var messagesContainer: LinearLayout
    private lateinit var chatScroll: ScrollView
    private lateinit var chatInput: EditText
    private lateinit var centerHeroWrap: LinearLayout
    private var selectedImageBase64: String? = null
    private var photoPreviewWrap: LinearLayout? = null
    private var photoPreviewThumb: ImageView? = null
    private var avatarView: ImageView? = null
    private var nickLabel: TextView? = null

    private fun openExternalLink(tgUri: String, webUrl: String) {
        try {
            startActivity(Intent(Intent.ACTION_VIEW, Uri.parse(tgUri)))
        } catch (_: Exception) {
            try {
                startActivity(Intent(Intent.ACTION_VIEW, Uri.parse(webUrl)))
            } catch (_: Exception) {
                Toast.makeText(this, "Не удалось открыть Telegram", Toast.LENGTH_SHORT).show()
            }
        }
    }

    private fun attachBitmapToChat(orig: Bitmap) {
        val maxDim = 1024
        val ratio = maxDim.toFloat() / maxOf(orig.width, orig.height)
        val bmp = if (ratio < 1f) {
            Bitmap.createScaledBitmap(orig, (orig.width * ratio).toInt(), (orig.height * ratio).toInt(), true)
        } else orig
        val out = ByteArrayOutputStream()
        bmp.compress(Bitmap.CompressFormat.JPEG, 82, out)
        selectedImageBase64 = Base64.encodeToString(out.toByteArray(), Base64.NO_WRAP)
        photoPreviewThumb?.setImageBitmap(bmp)
        photoPreviewWrap?.visibility = View.VISIBLE
    }

    private val pickImageLauncher = registerForActivityResult(ActivityResultContracts.GetContent()) { uri: Uri? ->
        if (uri != null) {
            try {
                val input = contentResolver.openInputStream(uri)
                val orig = BitmapFactory.decodeStream(input)
                input?.close()
                if (orig != null) attachBitmapToChat(orig)
            } catch (_: Exception) {
                Toast.makeText(this, "Ошибка загрузки фото", Toast.LENGTH_SHORT).show()
            }
        }
    }

    private val takePhotoLauncher = registerForActivityResult(ActivityResultContracts.TakePicturePreview()) { bmp: Bitmap? ->
        if (bmp != null) attachBitmapToChat(bmp)
    }

    private val pickAvatarLauncher = registerForActivityResult(ActivityResultContracts.GetContent()) { uri: Uri? ->
        if (uri != null) {
            try {
                val input = contentResolver.openInputStream(uri)
                val orig = BitmapFactory.decodeStream(input)
                input?.close()
                if (orig != null) {
                    val bmp = Bitmap.createScaledBitmap(orig, 256, 256, true)
                    val out = ByteArrayOutputStream()
                    bmp.compress(Bitmap.CompressFormat.PNG, 90, out)
                    val b64Str = Base64.encodeToString(out.toByteArray(), Base64.NO_WRAP)
                    getSharedPreferences("apex_prefs", Context.MODE_PRIVATE).edit().putString("user_avatar_b64", b64Str).apply()
                    avatarView?.setImageBitmap(bmp)
                    Toast.makeText(this, "Аватарка обновлена!", Toast.LENGTH_SHORT).show()
                }
            } catch (_: Exception) {}
        }
    }

    private val voiceToInputLauncher = registerForActivityResult(ActivityResultContracts.StartActivityForResult()) { res ->
        if (res.resultCode == Activity.RESULT_OK) {
            val spoken = res.data?.getStringArrayListExtra(RecognizerIntent.EXTRA_RESULTS)?.firstOrNull()
            if (!spoken.isNullOrEmpty()) {
                val cur = chatInput.text.toString().trim()
                chatInput.setText(if (cur.isEmpty()) spoken else "$cur $spoken")
                chatInput.setSelection(chatInput.text.length)
            }
        }
    }
        override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)

        ActivityCompat.requestPermissions(
            this,
            arrayOf(
                Manifest.permission.RECORD_AUDIO,
                Manifest.permission.POST_NOTIFICATIONS,
                Manifest.permission.CALL_PHONE,
                Manifest.permission.CAMERA
            ),
            101
        )

        val prefs = getSharedPreferences("apex_prefs", Context.MODE_PRIVATE)
        val deviceId = Settings.Secure.getString(contentResolver, Settings.Secure.ANDROID_ID) ?: "UNKNOWN"
        val isCreator = CREATOR_IDS.contains(deviceId) || prefs.getBoolean("is_admin", false)

        val themeKey = prefs.getString("app_theme", "amoled") ?: "amoled"
        val bgHex = when (themeKey) {
            "white" -> "#F8FAFC"
            "purple" -> "#13091F"
            "blue" -> "#071324"
            "green" -> "#061710"
            "dark_gray" -> "#090B10"
            else -> "#000000"
        }
        val barHex = when (themeKey) {
            "white" -> "#FFFFFF"
            "purple" -> "#1C0E2E"
            "blue" -> "#0B1D36"
            "green" -> "#0A2419"
            "dark_gray" -> "#0D1017"
            else -> "#050505"
        }
        val cardHex = when (themeKey) {
            "white" -> "#E2E8F0"
            "purple" -> "#26143D"
            "blue" -> "#112847"
            "green" -> "#103324"
            "dark_gray" -> "#161B26"
            else -> "#121212"
        }
        val accentHex = when (themeKey) {
            "white" -> "#0284C7"
            "purple" -> "#C084FC"
            "blue" -> "#38BDF8"
            "green" -> "#34D399"
            else -> "#38BDF8"
        }
        val textMainColor = if (themeKey == "white") Color.parseColor("#0F172A") else Color.WHITE
        val textSubColor = if (themeKey == "white") Color.parseColor("#475569") else Color.parseColor("#E2E8F0")

        window.statusBarColor = Color.parseColor(barHex)
        window.navigationBarColor = Color.parseColor(bgHex)
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.M && themeKey == "white") {
            window.decorView.systemUiVisibility = View.SYSTEM_UI_FLAG_LIGHT_STATUS_BAR
        }
        @Suppress("DEPRECATION")
        setTaskDescription(ActivityManager.TaskDescription("Apex AI", null, Color.parseColor(barHex)))

        postToWorker(prefs, JSONObject().apply {
            put("app_event", JSONObject().apply { put("type", "poll_push") })
        }) { res ->
            val pushObj = res?.optJSONObject("push")
            if (pushObj != null) {
                val pushId = pushObj.optLong("id", 0L)
                val lastShownId = prefs.getLong("last_push_id", 0L)
                if (pushId > lastShownId) {
                    prefs.edit().putLong("last_push_id", pushId).apply()
                    val title = pushObj.optString("title", "Apex AI")
                    val body = pushObj.optString("body", "")
                    runOnUiThread {
                        val nm = getSystemService(Context.NOTIFICATION_SERVICE) as NotificationManager
                        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
                            nm.createNotificationChannel(NotificationChannel("apex_push", "Apex Updates", NotificationManager.IMPORTANCE_HIGH))
                        }
                        val nb = if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) Notification.Builder(this, "apex_push") else @Suppress("DEPRECATION") Notification.Builder(this)
                        nm.notify(
                            (pushId % 100000).toInt(),
                            nb.setContentTitle(title).setContentText(body).setSmallIcon(android.R.drawable.ic_dialog_info).build()
                        )
                    }
                }
            }
        }

        drawerLayout = DrawerLayout(this).apply {
            fitsSystemWindows = true
            setBackgroundColor(Color.parseColor(bgHex))
        }
        val contentStack = FrameLayout(this).apply {
            fitsSystemWindows = true
            setBackgroundColor(Color.parseColor(bgHex))
        }

        fun roundBox(hex: String, radius: Float, strokeHex: String? = null, strokeWidth: Int = 2): GradientDrawable {
            return GradientDrawable().apply {
                setColor(Color.parseColor(hex))
                cornerRadius = radius
                if (strokeHex != null) setStroke(strokeWidth, Color.parseColor(strokeHex))
            }
        }
                var activeMenuRow: LinearLayout? = null
        val menuHighlightBg = if (themeKey == "white") Color.parseColor("#18000000") else Color.parseColor("#22FFFFFF")
        val menuRippleColor = if (themeKey == "white") Color.parseColor("#25000000") else Color.parseColor("#35FFFFFF")

        fun flatMenuItem(iconText: String, label: String, isSelectableTab: Boolean = false, onClick: () -> Unit): LinearLayout {
            return LinearLayout(this).apply {
                orientation = LinearLayout.HORIZONTAL
                gravity = Gravity.CENTER_VERTICAL
                setPadding(44, 30, 44, 30)
                val baseShape = GradientDrawable().apply {
                    setColor(Color.TRANSPARENT)
                    cornerRadius = 28f
                }
                background = RippleDrawable(ColorStateList.valueOf(menuRippleColor), baseShape, null)

                val ico = TextView(this@MainActivity).apply {
                    text = iconText
                    textSize = 18f
                    setTextColor(Color.parseColor(accentHex))
                    setPadding(0, 0, 32, 0)
                }
                val txt = TextView(this@MainActivity).apply {
                    text = label
                    textSize = 15f
                    setTextColor(textMainColor)
                }
                addView(ico)
                addView(txt)

                setOnClickListener {
                    if (isSelectableTab) {
                        activeMenuRow?.background = RippleDrawable(
                            ColorStateList.valueOf(menuRippleColor),
                            GradientDrawable().apply { setColor(Color.TRANSPARENT); cornerRadius = 28f },
                            null
                        )
                        activeMenuRow = this
                        background = RippleDrawable(
                            ColorStateList.valueOf(menuRippleColor),
                            GradientDrawable().apply { setColor(menuHighlightBg); cornerRadius = 28f },
                            null
                        )
                    }
                    drawerLayout.closeDrawers()
                    onClick()
                }
            }
        }

        fun showPage(target: View) {
            chatScreen.visibility = View.GONE
            settingsScreen.visibility = View.GONE
            infoScreen.visibility = View.GONE
            devScreen.visibility = View.GONE
            target.alpha = 0f
            target.visibility = View.VISIBLE
            target.animate().alpha(1f).setDuration(180).start()
        }

        fun showActivationDialog() {
            var clickedChannel = prefs.getBoolean("clicked_channel", false)
            val wrap = LinearLayout(this).apply {
                orientation = LinearLayout.VERTICAL
                setPadding(48, 28, 48, 12)
            }
            val desc = TextView(this).apply {
                text = "Для бесплатного доступа к Apex AI подпишитесь на наш официальный Telegram-канал и нажмите кнопку подтверждения:"
                textSize = 14f
                setPadding(0, 0, 0, 20)
            }
            val btnSubChannel = Button(this).apply {
                text = "1. Подписаться на наш Telegram-канал"
                isAllCaps = false
                setOnClickListener {
                    clickedChannel = true
                    prefs.edit().putBoolean("clicked_channel", true).apply()
                    openExternalLink(channelTgUri(), channelWebUrl())
                }
            }
            wrap.addView(desc)
            wrap.addView(btnSubChannel)

            AlertDialog.Builder(this)
                .setTitle("Активация бесплатного доступа")
                .setView(wrap)
                .setPositiveButton("2. Я подписался — Активировать") { _, _ ->
                    if (!clickedChannel) {
                        Toast.makeText(this@MainActivity, "Сначала нажмите «1. Подписаться на наш Telegram-канал»!", Toast.LENGTH_LONG).show()
                    } else {
                        prefs.edit().putBoolean("tg_subscribed", true).apply()
                        Toast.makeText(this@MainActivity, "✅ Бесплатный доступ к Apex AI активирован!", Toast.LENGTH_LONG).show()
                    }
                }
                .setNegativeButton("Отмена", null)
                .show()
        }

        fun openDevPanelProtected() {
            if (prefs.getBoolean("dev_unlocked", false)) {
                showPage(devScreen)
                return
            }
            val wrap = LinearLayout(this).apply {
                orientation = LinearLayout.VERTICAL
                setPadding(48, 28, 48, 12)
            }
            val idBox = EditText(this).apply {
                hint = "Введите Telegram ID разработчика"
                inputType = android.text.InputType.TYPE_CLASS_NUMBER
            }
            wrap.addView(idBox)

            AlertDialog.Builder(this)
                .setTitle("Доступ только для создателя")
                .setView(wrap)
                .setPositiveButton("Войти") { _, _ ->
                    val entered = idBox.text.toString().trim()
                    if (entered == CREATOR_TG_ID) {
                        prefs.edit()
                            .putBoolean("dev_unlocked", true)
                            .putBoolean("is_admin", true)
                            .putBoolean("tg_subscribed", true)
                            .apply()
                        Toast.makeText(this@MainActivity, "✅ Добро пожаловать, Derek Stealth!", Toast.LENGTH_SHORT).show()
                        showPage(devScreen)
                    } else {
                        Toast.makeText(this@MainActivity, "⛔ Неверный ID. Доступ запрещён!", Toast.LENGTH_LONG).show()
                    }
                }
                .setNegativeButton("Отмена", null)
                .show()
        }
                val welcomePhrases = listOf(
            "Привет! Давай начнём общение.",
            "С возвращением в Apex AI.",
            "Чем я могу помочь сегодня?",
            "На связи. Какую задачу решим?",
            "Готов к работе. Спрашивай что угодно.",
            "Привет! Есть идея или вопрос?"
        )

        fun updateCenterHeroVisibility() {
            centerHeroWrap.visibility = if (messagesContainer.childCount == 0) View.VISIBLE else View.GONE
        }

        fun addChatBubble(message: String, isUser: Boolean) {
            val row = LinearLayout(this).apply {
                orientation = LinearLayout.VERTICAL
                setPadding(36, 14, 36, 14)
                gravity = if (isUser) Gravity.END else Gravity.START
            }
            if (isUser) {
                val bubble = TextView(this).apply {
                    text = message
                    textSize = 15f
                    setTextColor(textMainColor)
                    background = roundBox(cardHex, 36f)
                    setPadding(36, 24, 36, 24)
                }
                row.addView(bubble)
            } else {
                val apexCol = LinearLayout(this).apply {
                    orientation = LinearLayout.VERTICAL
                    setPadding(8, 12, 24, 8)
                }
                val apexWrap = LinearLayout(this).apply {
                    orientation = LinearLayout.HORIZONTAL
                }
                val line = View(this).apply {
                    setBackgroundColor(Color.parseColor(accentHex))
                }
                val txt = TextView(this).apply {
                    text = message
                    textSize = 15f
                    setTextColor(textSubColor)
                    setLineSpacing(6f, 1.15f)
                    setPadding(28, 0, 0, 0)
                    setTextIsSelectable(true)
                }
                apexWrap.addView(line, LinearLayout.LayoutParams(6, LinearLayout.LayoutParams.MATCH_PARENT))
                apexWrap.addView(txt)

                val copyBtn = TextView(this).apply {
                    text = "📋 Скопировать"
                    textSize = 12f
                    setTextColor(Color.parseColor("#94A3B8"))
                    setPadding(34, 16, 20, 8)
                    setOnClickListener {
                        val cm = getSystemService(Context.CLIPBOARD_SERVICE) as ClipboardManager
                        cm.setPrimaryClip(ClipData.newPlainText("Apex Reply", message))
                        text = "✅ Скопировано"
                        setTextColor(Color.parseColor(accentHex))
                        postDelayed({
                            text = "📋 Скопировать"
                            setTextColor(Color.parseColor("#94A3B8"))
                        }, 1800)
                    }
                }

                apexCol.addView(apexWrap)
                apexCol.addView(copyBtn)
                row.addView(apexCol)
            }
            messagesContainer.addView(row)
            updateCenterHeroVisibility()
            chatScroll.post { chatScroll.fullScroll(View.FOCUS_DOWN) }
        }

        chatScreen = LinearLayout(this).apply {
            orientation = LinearLayout.VERTICAL
            setBackgroundColor(Color.parseColor(bgHex))
        }

        val topBar = LinearLayout(this).apply {
            orientation = LinearLayout.HORIZONTAL
            gravity = Gravity.CENTER_VERTICAL
            setPadding(32, 32, 32, 24)
            setBackgroundColor(Color.parseColor(barHex))
        }

        val btnMenu = TextView(this).apply {
            text = "="
            textSize = 26f
            setTextColor(textMainColor)
            gravity = Gravity.CENTER
            background = roundBox(cardHex, 50f)
            setOnClickListener { drawerLayout.openDrawer(Gravity.START) }
        }

        val topTitle = TextView(this).apply {
            text = "APEX"
            textSize = 18f
            typeface = Typeface.DEFAULT_BOLD
            letterSpacing = 0.15f
            setTextColor(textMainColor)
            gravity = Gravity.CENTER
            layoutParams = LinearLayout.LayoutParams(0, LinearLayout.LayoutParams.WRAP_CONTENT, 1f)
        }

        val heroPhraseText = TextView(this).apply {
            text = welcomePhrases.random()
            textSize = 18f
            typeface = Typeface.create("sans-serif-medium", Typeface.NORMAL)
            setTextColor(textMainColor)
            gravity = Gravity.CENTER
            setPadding(48, 28, 48, 0)
        }

        val btnNewChatTop = TextView(this).apply {
            text = "↻"
            textSize = 22f
            setTextColor(Color.parseColor(accentHex))
            gravity = Gravity.CENTER
            background = roundBox(cardHex, 50f)
            setOnClickListener {
                prefs.edit().putString("chat_history", "[]").apply()
                messagesContainer.removeAllViews()
                heroPhraseText.text = welcomePhrases.random()
                updateCenterHeroVisibility()
            }
        }

        topBar.addView(btnMenu, LinearLayout.LayoutParams(96, 96))
        topBar.addView(topTitle)
        topBar.addView(btnNewChatTop, LinearLayout.LayoutParams(96, 96))

        val centerFrame = FrameLayout(this).apply {
            layoutParams = LinearLayout.LayoutParams(LinearLayout.LayoutParams.MATCH_PARENT, 0, 1f)
        }

        chatScroll = ScrollView(this).apply {
            layoutParams = FrameLayout.LayoutParams(FrameLayout.LayoutParams.MATCH_PARENT, FrameLayout.LayoutParams.MATCH_PARENT)
        }
        messagesContainer = LinearLayout(this).apply {
            orientation = LinearLayout.VERTICAL
            setPadding(0, 16, 0, 32)
        }
        chatScroll.addView(messagesContainer)

        val logoBadge = object : View(this) {
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
        }

        centerHeroWrap = LinearLayout(this).apply {
            orientation = LinearLayout.VERTICAL
            gravity = Gravity.CENTER
            layoutParams = FrameLayout.LayoutParams(FrameLayout.LayoutParams.MATCH_PARENT, FrameLayout.LayoutParams.MATCH_PARENT)
            addView(logoBadge, LinearLayout.LayoutParams(150, 150))
            addView(heroPhraseText)
        }

        centerFrame.addView(chatScroll)
        centerFrame.addView(centerHeroWrap)
                val bottomWrap = LinearLayout(this).apply {
            orientation = LinearLayout.VERTICAL
            setPadding(24, 10, 24, 28)
            setBackgroundColor(Color.parseColor(bgHex))
        }

        photoPreviewWrap = LinearLayout(this).apply {
            orientation = LinearLayout.HORIZONTAL
            gravity = Gravity.CENTER_VERTICAL
            background = roundBox(cardHex, 28f)
            setPadding(20, 16, 24, 16)
            visibility = View.GONE
        }

        photoPreviewThumb = ImageView(this).apply {
            scaleType = ImageView.ScaleType.CENTER_CROP
        }
        val previewText = TextView(this).apply {
            text = "Фото прикреплено\nГотово к анализу"
            textSize = 12f
            setTextColor(textMainColor)
            setPadding(24, 0, 24, 0)
            layoutParams = LinearLayout.LayoutParams(0, LinearLayout.LayoutParams.WRAP_CONTENT, 1f)
        }
        val btnRemovePhoto = TextView(this).apply {
            text = "✕"
            textSize = 18f
            setTextColor(Color.parseColor("#F87171"))
            setPadding(16, 8, 16, 8)
            setOnClickListener {
                selectedImageBase64 = null
                photoPreviewWrap?.visibility = View.GONE
            }
        }
        photoPreviewWrap?.addView(photoPreviewThumb, LinearLayout.LayoutParams(110, 110))
        photoPreviewWrap?.addView(previewText)
        photoPreviewWrap?.addView(btnRemovePhoto)

        val inputCapsule = LinearLayout(this).apply {
            orientation = LinearLayout.HORIZONTAL
            gravity = Gravity.CENTER_VERTICAL
            background = roundBox(cardHex, 60f)
            setPadding(14, 10, 14, 10)
        }

        val btnGallery = TextView(this).apply {
            text = "+"
            textSize = 24f
            setTextColor(textMainColor)
            gravity = Gravity.CENTER
            background = roundBox(barHex, 50f)
            setOnClickListener { pickImageLauncher.launch("image/*") }
        }

        val btnCamera = TextView(this).apply {
            text = "📷"
            textSize = 16f
            gravity = Gravity.CENTER
            background = roundBox(barHex, 50f)
            setOnClickListener {
                try {
                    takePhotoLauncher.launch(null)
                } catch (_: Exception) {
                    Toast.makeText(this@MainActivity, "Камера недоступна", Toast.LENGTH_SHORT).show()
                }
            }
        }

        chatInput = EditText(this).apply {
            hint = "Спросить Apex..."
            textSize = 15f
            setTextColor(textMainColor)
            setHintTextColor(Color.parseColor("#64748B"))
            setBackgroundColor(Color.TRANSPARENT)
            setPadding(20, 16, 12, 16)
            layoutParams = LinearLayout.LayoutParams(0, LinearLayout.LayoutParams.WRAP_CONTENT, 1f)
        }

        val btnMicInBar = TextView(this).apply {
            text = "🎙"
            textSize = 18f
            gravity = Gravity.CENTER
            setPadding(12, 14, 12, 14)
            setOnClickListener {
                val intent = Intent(RecognizerIntent.ACTION_RECOGNIZE_SPEECH).apply {
                    putExtra(RecognizerIntent.EXTRA_LANGUAGE_MODEL, RecognizerIntent.LANGUAGE_MODEL_FREE_FORM)
                    putExtra(RecognizerIntent.EXTRA_LANGUAGE, "ru-RU")
                }
                try {
                    voiceToInputLauncher.launch(intent)
                } catch (_: Exception) {
                    Toast.makeText(this@MainActivity, "Голосовой ввод недоступен", Toast.LENGTH_SHORT).show()
                }
            }
        }

        val btnSendCapsule = TextView(this).apply {
            text = "↑"
            textSize = 20f
            typeface = Typeface.DEFAULT_BOLD
            setTextColor(Color.parseColor("#000000"))
            gravity = Gravity.CENTER
            background = roundBox(accentHex, 50f)
            setOnClickListener {
                val hasAccess = isCreator || prefs.getBoolean("tg_subscribed", false)
                if (!hasAccess) {
                    showActivationDialog()
                    return@setOnClickListener
                }
                val rawMsg = chatInput.text.toString().trim()
                val imgB64 = selectedImageBase64
                if (rawMsg.isEmpty() && imgB64 == null) return@setOnClickListener
                val promptToSend = if (rawMsg.isEmpty()) "Подробно разбери это фото или реши задачу на снимке по шагам." else rawMsg
                chatInput.setText("")
                selectedImageBase64 = null
                photoPreviewWrap?.visibility = View.GONE

                addChatBubble((if (imgB64 != null) "📷 [Фото прикреплено]\n" else "") + promptToSend, true)
                ApexCoreService.queryBrainDirect(this@MainActivity, promptToSend, isCreator, imgB64) { reply, diag ->
                    prefs.edit().putString("last_diag", diag).apply()
                    runOnUiThread { addChatBubble(reply, false) }
                }
            }
        }

        val camWrap = LinearLayout(this).apply {
            orientation = LinearLayout.HORIZONTAL
            addView(btnGallery, LinearLayout.LayoutParams(78, 78))
            addView(Space(this@MainActivity).apply { minimumWidth = 10 })
            addView(btnCamera, LinearLayout.LayoutParams(78, 78))
        }

        inputCapsule.addView(camWrap)
        inputCapsule.addView(chatInput)
        inputCapsule.addView(btnMicInBar)
        inputCapsule.addView(btnSendCapsule, LinearLayout.LayoutParams(82, 82))

        val previewHolder = LinearLayout(this).apply {
            orientation = LinearLayout.VERTICAL
            addView(photoPreviewWrap)
            addView(Space(this@MainActivity).apply { minimumHeight = 12 })
        }

        bottomWrap.addView(previewHolder)
        bottomWrap.addView(inputCapsule)

        chatScreen.addView(topBar)
        chatScreen.addView(centerFrame)
        chatScreen.addView(bottomWrap)
                fun makeSubPage(titleText: String, bodyBuilder: (LinearLayout) -> Unit): ScrollView {
            return ScrollView(this).apply {
                visibility = View.GONE
                setBackgroundColor(Color.parseColor(bgHex))
                val box = LinearLayout(this@MainActivity).apply {
                    orientation = LinearLayout.VERTICAL
                    setPadding(40, 40, 40, 60)
                }
                val head = LinearLayout(this@MainActivity).apply {
                    orientation = LinearLayout.HORIZONTAL
                    gravity = Gravity.CENTER_VERTICAL
                    setPadding(0, 0, 0, 32)
                }
                val backBtn = TextView(this@MainActivity).apply {
                    text = "←"
                    textSize = 22f
                    setTextColor(textMainColor)
                    gravity = Gravity.CENTER
                    background = roundBox(cardHex, 45f)
                    setOnClickListener { showPage(chatScreen) }
                }
                val ttl = TextView(this@MainActivity).apply {
                    text = titleText
                    textSize = 18f
                    typeface = Typeface.DEFAULT_BOLD
                    setTextColor(textMainColor)
                    setPadding(28, 0, 0, 0)
                }
                head.addView(backBtn, LinearLayout.LayoutParams(90, 90))
                head.addView(ttl)
                box.addView(head)
                bodyBuilder(box)
                addView(box)
            }
        }

        settingsScreen = makeSubPage("Настройки и разрешения") { box ->
            val btnOverlay = Button(this).apply {
                text = "Разрешить поверх других окон"
                isAllCaps = false
                setTextColor(textMainColor)
                background = roundBox(cardHex, 28f)
                setOnClickListener {
                    if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.M && !Settings.canDrawOverlays(this@MainActivity)) {
                        startActivity(Intent(Settings.ACTION_MANAGE_OVERLAY_PERMISSION, Uri.parse("package:$packageName")))
                    } else {
                        Toast.makeText(this@MainActivity, "Уже разрешено!", Toast.LENGTH_SHORT).show()
                    }
                }
            }
            val btnAppPerm = Button(this).apply {
                text = "Разрешения (Микрофон / Камера)"
                isAllCaps = false
                setTextColor(textMainColor)
                background = roundBox(cardHex, 28f)
                setOnClickListener {
                    startActivity(Intent(Settings.ACTION_APPLICATION_DETAILS_SETTINGS, Uri.parse("package:$packageName")))
                }
            }
            box.addView(btnOverlay)
            box.addView(Space(this).apply { minimumHeight = 20 })
            box.addView(btnAppPerm)
        }

        infoScreen = makeSubPage("О приложении") { box ->
            val fullAboutText = """
О приложении Apex

Apex AI — ваш персональный интеллектуальный помощник.

Apex — это ИИ-ассистент нового поколения, разработанный инженером Derek Stealth. Его главная задача — сделать взаимодействие с технологиями проще, быстрее и естественнее.

Apex создан не просто для ответов на вопросы. Это персональный цифровой помощник, с которым можно общаться голосом или текстом, обсуждать идеи, получать полезную информацию и управлять возможностями своего смартфона.

Возможности Apex:

- Живое общение. Общайтесь с ассистентом естественным языком, задавайте вопросы и получайте понятные ответы.
- Голосовое управление. Используйте голосовые команды для взаимодействия с приложением и поддерживаемыми функциями смартфона.
- Работа с приложениями. Открывайте приложения и выполняйте доступные действия с помощью голосовых команд.
- Интеллектуальная помощь. Получайте объяснения, советы, помощь в решении задач и поиске информации.
- Повседневные задачи. Используйте Apex для планирования, заметок, идей и организации повседневных дел.
- Персональное взаимодействие. Ассистент создан для естественного общения, а не для механического воспроизведения заранее подготовленных фраз.

Apex постоянно развивается. Наша цель — создать удобную интеллектуальную систему, которая станет полезным инструментом в повседневной жизни и будет расширять свои возможности с каждым обновлением.

---

Конфиденциальность и безопасность

Ваше доверие — один из главных принципов разработки Apex.

Мы понимаем, что голосовой помощник может получать доступ к отдельным функциям смартфона. Поэтому хотим подробно объяснить, зачем приложению нужны разрешения и как они используются.

Apex запрашивает только те разрешения, которые необходимы для работы соответствующих функций. Само наличие разрешения не означает, что приложение постоянно использует его или получает доступ ко всему содержимому устройства.

🎙 Микрофон

Доступ к микрофону необходим для распознавания голосовых команд и общения с приложением.

Микрофон используется для получения голосового ввода, когда активирована соответствующая функция. Если голосовая активация отключена, приложение не должно использовать микрофон для постоянного прослушивания.

🔔 Уведомления

Уведомления позволяют Apex сообщать о важных событиях, состоянии ассистента, результатах выполнения команд и доступных обновлениях.

Они не предоставляют приложению доступ к вашим личным перепискам.

📱 Управление функциями смартфона

Для выполнения отдельных команд могут потребоваться дополнительные системные разрешения или специальные возможности Android.

Например, они могут использоваться для открытия приложений, выполнения поддерживаемых действий и взаимодействия с отдельными элементами системы.

Каждое такое разрешение имеет конкретное назначение. Перед его предоставлением вы можете ознакомиться с объяснением того, для чего оно необходимо.

🌐 Передача данных и работа ИИ

Для обработки запросов и формирования интеллектуальных ответов Apex может использовать сетевое соединение и внешние сервисы искусственного интеллекта.

Это означает, что текстовые запросы или другие данные, необходимые для обработки команды, могут передаваться соответствующему сервису.

Не отправляйте через ассистента пароли, банковские данные и другую конфиденциальную информацию, если в этом нет необходимости.

🛡 Ваш контроль над приложением

Вы самостоятельно решаете, какие разрешения предоставлять Apex.

- Вы можете запретить доступ к микрофону через настройки Android.
- Вы можете отключить уведомления в любое время.
- Вы можете отозвать предоставленные разрешения.
- Вы можете остановить работу ассистента с помощью соответствующей функции приложения.
- Вы можете удалить приложение, если больше не хотите им пользоваться.

Отказ от необязательного разрешения может ограничить работу отдельных возможностей, но не должен восприниматься как обязательное условие доверия к приложением.

Наша позиция

Мы стремимся к тому, чтобы Apex был не только функциональным, но и прозрачным для пользователя.

Мы не хотим, чтобы человек предоставлял разрешения, не понимая их назначения. Поэтому каждая функция должна иметь понятное объяснение, а пользователь должен сохранять контроль над своим устройством и данными.

Apex — технологии, которые работают для вас. Ваше устройство, ваши данные, ваш контроль.

---

Разработчик: Derek Stealth
Продукт: Apex AI Assistant
Версия: Информация о текущей версии доступна в приложении.
            """.trimIndent()

            val infoTxt = TextView(this).apply {
                text = fullAboutText
                textSize = 14f
                setTextColor(textSubColor)
                setLineSpacing(6f, 1.18f)
            }
            box.addView(infoTxt)
        }

        devScreen = makeSubPage("Панель разработчика") { box ->
            val devInfo = TextView(this).apply {
                text = "Device ID: $deviceId\nCreator Mode: $isCreator\nПоследняя диагностика:\n${prefs.getString("last_diag", "Нет запросов")}"
                textSize = 13f
                setTextColor(textSubColor)
            }
            box.addView(devInfo)
            box.addView(Space(this).apply { minimumHeight = 28 })

            val lblAccess = TextView(this).apply {
                text = "👑 Управление доступом по Telegram ID"
                textSize = 15f
                typeface = Typeface.DEFAULT_BOLD
                setTextColor(textMainColor)
            }
            val tgTargetInput = EditText(this).apply {
                hint = "Введите Telegram ID пользователя"
                inputType = android.text.InputType.TYPE_CLASS_NUMBER
                setTextColor(textMainColor)
                setHintTextColor(Color.parseColor("#64748B"))
                background = roundBox(cardHex, 24f)
                setPadding(24, 20, 24, 20)
            }

            fun sendGrant(mode: String, okMsg: String) {
                val targetId = tgTargetInput.text.toString().trim()
                if (targetId.isEmpty()) {
                    Toast.makeText(this@MainActivity, "Введите Telegram ID пользователя", Toast.LENGTH_SHORT).show()
                    return
                }
                sendDirectToAdminBot("👑 ВЫДАЧА ПРАВ В APEX AI\nРежим: $mode\nTelegram ID: $targetId")
                postToWorker(prefs, JSONObject().apply {
                    put("app_event", JSONObject().apply {
                        put("type", "grant_access")
                        put("target_tg_id", targetId)
                        put("mode", mode)
                    })
                })
                Toast.makeText(this@MainActivity, okMsg, Toast.LENGTH_LONG).show()
            }

            val btnInfinite = Button(this).apply {
                text = "♾ Выдать бесконечный доступ по TG ID"
                isAllCaps = false
                setTextColor(Color.BLACK)
                background = roundBox(accentHex, 24f)
                setOnClickListener { sendGrant("infinite", "✅ Бесконечный доступ выдан!") }
            }
                        val btnAdmin = Button(this).apply {
                text = "⚡ Выдать админку по TG ID"
                isAllCaps = false
                setTextColor(textMainColor)
                background = roundBox(cardHex, 24f)
                setOnClickListener { sendGrant("admin", "✅ Права администратора выданы!") }
            }
            val btnExtend30 = Button(this).apply {
                text = "⏳ Продлить доступ на 30 дней"
                isAllCaps = false
                setTextColor(textMainColor)
                background = roundBox(cardHex, 24f)
                setOnClickListener { sendGrant("extend30", "✅ Доступ продлён на 30 дней!") }
            }

            box.addView(lblAccess)
            box.addView(Space(this).apply { minimumHeight = 14 })
            box.addView(tgTargetInput)
            box.addView(Space(this).apply { minimumHeight = 14 })
            box.addView(btnInfinite)
            box.addView(Space(this).apply { minimumHeight = 12 })
            box.addView(btnAdmin)
            box.addView(Space(this).apply { minimumHeight = 12 })
            box.addView(btnExtend30)
            box.addView(Space(this).apply { minimumHeight = 36 })

            val lblPush = TextView(this).apply {
                text = "📢 Push-уведомление всем пользователям"
                textSize = 15f
                typeface = Typeface.DEFAULT_BOLD
                setTextColor(textMainColor)
            }
            val pushTitleInput = EditText(this).apply {
                hint = "Заголовок уведомления"
                setTextColor(textMainColor)
                setHintTextColor(Color.parseColor("#64748B"))
                background = roundBox(cardHex, 24f)
                setPadding(24, 20, 24, 20)
            }
            val pushBodyInput = EditText(this).apply {
                hint = "Текст уведомления для всех пользователей..."
                setTextColor(textMainColor)
                setHintTextColor(Color.parseColor("#64748B"))
                background = roundBox(cardHex, 24f)
                setPadding(24, 20, 24, 20)
            }
            val btnSendPush = Button(this).apply {
                text = "🚀 Отправить Push всем пользователям"
                isAllCaps = false
                setTextColor(Color.BLACK)
                background = roundBox(accentHex, 24f)
                setOnClickListener {
                    val pTitle = pushTitleInput.text.toString().trim().ifEmpty { "Apex AI" }
                    val pBody = pushBodyInput.text.toString().trim()
                    if (pBody.isEmpty()) {
                        Toast.makeText(this@MainActivity, "Введите текст уведомления", Toast.LENGTH_SHORT).show()
                        return@setOnClickListener
                    }
                    sendDirectToAdminBot("📢 PUSH-РАССЫЛКА APEX AI\nЗаголовок: $pTitle\nТекст: $pBody")
                    postToWorker(prefs, JSONObject().apply {
                        put("app_event", JSONObject().apply {
                            put("type", "send_push")
                            put("title", pTitle)
                            put("body", pBody)
                        })
                    })
                    pushBodyInput.setText("")
                    Toast.makeText(this@MainActivity, "✅ Push-уведомление отправлено!", Toast.LENGTH_LONG).show()
                }
            }

            box.addView(lblPush)
            box.addView(Space(this).apply { minimumHeight = 14 })
            box.addView(pushTitleInput)
            box.addView(Space(this).apply { minimumHeight = 12 })
            box.addView(pushBodyInput)
            box.addView(Space(this).apply { minimumHeight = 14 })
            box.addView(btnSendPush)
            box.addView(Space(this).apply { minimumHeight = 36 })

            val lblKeys = TextView(this).apply {
                text = "🔧 Настройки API и сервера"
                textSize = 15f
                typeface = Typeface.DEFAULT_BOLD
                setTextColor(textMainColor)
            }
            val workerInput = EditText(this).apply {
                hint = "Адрес Cloudflare Worker"
                setText(getWorkerUrl(prefs))
                setTextColor(textMainColor)
                setHintTextColor(Color.parseColor("#64748B"))
                background = roundBox(cardHex, 24f)
                setPadding(24, 20, 24, 20)
            }
            val keyInput = EditText(this).apply {
                hint = "Свой Groq API Key (необязательно)"
                setText(prefs.getString("groq_key", ""))
                setTextColor(textMainColor)
                setHintTextColor(Color.parseColor("#64748B"))
                background = roundBox(cardHex, 24f)
                setPadding(24, 20, 24, 20)
            }
            val saveKeyBtn = Button(this).apply {
                text = "Сохранить настройки"
                isAllCaps = false
                setTextColor(textMainColor)
                background = roundBox(cardHex, 24f)
                setOnClickListener {
                    prefs.edit()
                        .putString("worker_url", workerInput.text.toString().trim())
                        .putString("groq_key", keyInput.text.toString().trim())
                        .apply()
                    Toast.makeText(this@MainActivity, "✅ Настройки сохранены", Toast.LENGTH_SHORT).show()
                }
            }
            box.addView(lblKeys)
            box.addView(Space(this).apply { minimumHeight = 14 })
            box.addView(workerInput)
            box.addView(Space(this).apply { minimumHeight = 12 })
            box.addView(keyInput)
            box.addView(Space(this).apply { minimumHeight = 14 })
            box.addView(saveKeyBtn)
        }
                contentStack.addView(chatScreen)
        contentStack.addView(settingsScreen)
        contentStack.addView(infoScreen)
        contentStack.addView(devScreen)

        val drawerScroll = ScrollView(this).apply {
            setBackgroundColor(Color.parseColor(barHex))
            layoutParams = DrawerLayout.LayoutParams(780, DrawerLayout.LayoutParams.MATCH_PARENT, Gravity.START)
        }
        val drawerBox = LinearLayout(this).apply {
            orientation = LinearLayout.VERTICAL
            setPadding(24, 56, 24, 48)
        }

        val profileRow = LinearLayout(this).apply {
            orientation = LinearLayout.HORIZONTAL
            gravity = Gravity.CENTER_VERTICAL
            setPadding(20, 12, 20, 32)
        }
        avatarView = ImageView(this).apply {
            scaleType = ImageView.ScaleType.CENTER_CROP
            background = roundBox(cardHex, 60f, accentHex, 2)
            val savedB64 = prefs.getString("user_avatar_b64", null)
            if (!savedB64.isNullOrEmpty()) {
                try {
                    val bytes = Base64.decode(savedB64, Base64.DEFAULT)
                    setImageBitmap(BitmapFactory.decodeByteArray(bytes, 0, bytes.size))
                } catch (_: Exception) {}
            }
            setOnClickListener { pickAvatarLauncher.launch("image/*") }
        }
        val nameCol = LinearLayout(this).apply {
            orientation = LinearLayout.VERTICAL
            setPadding(28, 0, 0, 0)
        }
        val currentNick = prefs.getString("user_name", if (isCreator) "Derek Stealth" else "Пользователь") ?: "Пользователь"
        nickLabel = TextView(this).apply {
            text = currentNick
            textSize = 17f
            typeface = Typeface.DEFAULT_BOLD
            setTextColor(textMainColor)
        }
        val editProfileHint = TextView(this).apply {
            text = (if (isCreator) "Создатель • " else "") + "Изменить фото/ник"
            textSize = 12f
            setTextColor(Color.parseColor(accentHex))
            setOnClickListener {
                val input = EditText(this@MainActivity).apply { setText(nickLabel?.text) }
                AlertDialog.Builder(this@MainActivity)
                    .setTitle("Изменить ник")
                    .setView(input)
                    .setPositiveButton("Сохранить") { _, _ ->
                        val n = input.text.toString().trim()
                        if (n.isNotEmpty()) {
                            prefs.edit().putString("user_name", n).apply()
                            nickLabel?.text = n
                        }
                    }
                    .setNegativeButton("Отмена", null)
                    .show()
            }
        }
        nameCol.addView(nickLabel)
        nameCol.addView(editProfileHint)
        profileRow.addView(avatarView, LinearLayout.LayoutParams(116, 116))
        profileRow.addView(nameCol)
        drawerBox.addView(profileRow)

        val themeLabel = TextView(this).apply {
            text = "Тема оформления"
            textSize = 13f
            setTextColor(Color.parseColor("#94A3B8"))
            setPadding(24, 8, 24, 16)
        }
        drawerBox.addView(themeLabel)

        val themeDotsRow = LinearLayout(this).apply {
            orientation = LinearLayout.HORIZONTAL
            setPadding(24, 0, 24, 32)
        }
        val themes = listOf(
            "amoled" to "#000000",
            "dark_gray" to "#090B10",
            "white" to "#FFFFFF",
            "purple" to "#2E1065",
            "blue" to "#0C4A6E",
            "green" to "#064E3B"
        )
        for ((tKey, tHex) in themes) {
            val isSelected = themeKey == tKey
            val dot = View(this).apply {
                background = roundBox(tHex, 45f, if (isSelected) accentHex else "#475569", if (isSelected) 5 else 2)
                setOnClickListener {
                    prefs.edit().putString("app_theme", tKey).apply()
                    recreate()
                }
            }
            themeDotsRow.addView(dot, LinearLayout.LayoutParams(74, 74))
            themeDotsRow.addView(Space(this).apply { minimumWidth = 18 })
        }
        drawerBox.addView(themeDotsRow)

        val tabChat = flatMenuItem("💬", "Чат и фото-анализ", isSelectableTab = true) { showPage(chatScreen) }
        activeMenuRow = tabChat
        tabChat.background = RippleDrawable(
            ColorStateList.valueOf(menuRippleColor),
            GradientDrawable().apply { setColor(menuHighlightBg); cornerRadius = 28f },
            null
        )
        drawerBox.addView(tabChat)

        drawerBox.addView(flatMenuItem("🎙", "Запустить фоновый голос") {
            val hasAccess = isCreator || prefs.getBoolean("tg_subscribed", false)
            if (!hasAccess) {
                showActivationDialog()
                return@flatMenuItem
            }
            val intent = Intent(this, ApexCoreService::class.java).apply { action = "START_VOICE" }
            if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) startForegroundService(intent) else startService(intent)
            Toast.makeText(this, "Фоновый голос запущен", Toast.LENGTH_SHORT).show()
        })

        drawerBox.addView(flatMenuItem("⏹", "Остановить фоновый голос") {
            val intent = Intent(this, ApexCoreService::class.java).apply { action = "STOP_VOICE" }
            startService(intent)
            Toast.makeText(this, "Фоновый голос остановлен", Toast.LENGTH_SHORT).show()
        })

        drawerBox.addView(flatMenuItem("⚙", "Настройки и разрешения", isSelectableTab = true) { showPage(settingsScreen) })
        drawerBox.addView(flatMenuItem("🛡", "О приложении", isSelectableTab = true) { showPage(infoScreen) })
        drawerBox.addView(flatMenuItem("✈", "Наш Telegram-канал") { openExternalLink(channelTgUri(), channelWebUrl()) })
        drawerBox.addView(flatMenuItem("🔑", "Активировать бесплатный доступ") { showActivationDialog() })
        drawerBox.addView(flatMenuItem("⚡", "Панель разработчика", isSelectableTab = true) { openDevPanelProtected() })

        drawerBox.addView(flatMenuItem("⭐", "Оценить Apex AI") {
            val dialogWrap = LinearLayout(this).apply {
                orientation = LinearLayout.VERTICAL
                setPadding(48, 32, 48, 16)
            }
            var selectedStars = 5
            val starsRow = LinearLayout(this).apply {
                orientation = LinearLayout.HORIZONTAL
                gravity = Gravity.CENTER
            }
            val starViews = mutableListOf<TextView>()
            for (i in 1..5) {
                val sv = TextView(this).apply {
                    text = "⭐"
                    textSize = 28f
                    setPadding(14, 8, 14, 8)
                    setOnClickListener {
                        selectedStars = i
                        for (idx in 0 until 5) {
                            starViews[idx].alpha = if (idx < selectedStars) 1.0f else 0.3f
                        }
                    }
                }
                starViews.add(sv)
                starsRow.addView(sv)
            }
            val commentBox = EditText(this).apply { hint = "Напишите пару слов (необязательно)" }
            dialogWrap.addView(starsRow)
            dialogWrap.addView(Space(this).apply { minimumHeight = 20 })
            dialogWrap.addView(commentBox)

            AlertDialog.Builder(this)
                .setTitle("Оценить Apex AI")
                .setView(dialogWrap)
                .setPositiveButton("Отправить") { _, _ ->
                    val note = commentBox.text.toString().trim()
                    val ratingMsg = "⭐ ОЦЕНКА ИЗ ПРИЛОЖЕНИЯ APEX AI!\n\nОценка: ${"⭐".repeat(selectedStars)} ($selectedStars/5)\nУстройство: ${Build.MANUFACTURER} ${Build.MODEL}\nКомментарий: ${note.ifEmpty { "Без текста" }}"
                    sendDirectToAdminBot(ratingMsg)
                    Toast.makeText(this@MainActivity, "Спасибо за оценку $selectedStars ⭐!", Toast.LENGTH_SHORT).show()
                }
                .setNegativeButton("Отмена", null)
                .show()
        })

        drawerScroll.addView(drawerBox)
        drawerLayout.addView(contentStack)
        drawerLayout.addView(drawerScroll)
        setContentView(drawerLayout)
    }
}
class ApexCoreService : Service(), TextToSpeech.OnInitListener {

    private var tts: TextToSpeech? = null
    private var speechRecognizer: SpeechRecognizer? = null
    private var isListeningActive = false
    private var isSpeaking = false
    private val mainHandler = Handler(Looper.getMainLooper())

    companion object {
                private var sharedTts: TextToSpeech? = null
        private var sharedTtsReady = false

        fun speakNatural(ctx: Context, rawText: String, onDone: (() -> Unit)? = null) {
            val clean = rawText.replace(Regex("[*#_`~>|\\[\\]]"), "").replace(Regex("\\s+"), " ").trim()
            if (clean.isEmpty()) { onDone?.invoke(); return }
            fun doSpeak(e: TextToSpeech) {
                try {
                    val v = e.voices?.filter { it.locale.language == "ru" }
                    val best = v?.firstOrNull { it.name.contains("ruf", true) || it.name.contains("rud", true) } ?: v?.maxByOrNull { it.quality }
                    if (best != null) e.voice = best
                } catch (_: Exception) {}
                e.setPitch(0.95f)
                e.setSpeechRate(1.02f)
                e.setOnUtteranceProgressListener(object : UtteranceProgressListener() {
                    override fun onStart(id: String?) {}
                    override fun onDone(id: String?) { onDone?.invoke() }
                    override fun onError(id: String?) { onDone?.invoke() }
                })
                e.speak(clean, TextToSpeech.QUEUE_FLUSH, Bundle(), "APEX_VOICE")
            }
            if (sharedTts != null && sharedTtsReady) doSpeak(sharedTts!!) else {
                sharedTts = TextToSpeech(ctx.applicationContext) { st ->
                    if (st == TextToSpeech.SUCCESS) { sharedTts?.setLanguage(Locale("ru", "RU")); sharedTtsReady = true; doSpeak(sharedTts!!) } else onDone?.invoke()
                }
            }
        }

        private fun runSmartCommand(ctx: Context, raw: String): String? {
            val q = raw.lowercase(Locale.getDefault()).trim()
            try {
                if (q.contains("фонарик") || q.contains("включи свет") || q.contains("выключи свет")) {
                    val cm = ctx.getSystemService(Context.CAMERA_SERVICE) as android.hardware.camera2.CameraManager
                    val id = cm.cameraIdList.firstOrNull() ?: return null
                    val on = !(q.contains("выкл") || q.contains("откл") || q.contains("погаси"))
                    cm.setTorchMode(id, on)
                    return if (on) "🔦 Фонарик включён." else "🔦 Фонарик выключен."
                }
                if (q.startsWith("открой ") || q.startsWith("запусти ") || q.startsWith("включи ")) {
                    val t = q.removePrefix("открой ").removePrefix("запусти ").removePrefix("включи ").trim()
                    val map = mapOf("ютуб" to "youtube", "телеграм" to "telegram", "тг" to "telegram", "ватсап" to "whatsapp", "вк" to "vk", "тикток" to "tiktok", "хром" to "chrome", "озон" to "ozon", "вб" to "wildberries", "сдэк" to "cdek", "авито" to "avito")
                    val w = map[t] ?: t
                    val pm = ctx.packageManager
                    for (app in pm.getInstalledApplications(0)) {
                        val lbl = pm.getApplicationLabel(app).toString().lowercase(Locale.getDefault())
                        if ((lbl.contains(w) || app.packageName.lowercase().contains(w)) && w.length >= 2) {
                            pm.getLaunchIntentForPackage(app.packageName)?.let { it.addFlags(Intent.FLAG_ACTIVITY_NEW_TASK); ctx.startActivity(it); return "🚀 Открываю ${pm.getApplicationLabel(app)}..." }
                        }
                    }
                    if (t.contains("камер")) { ctx.startActivity(Intent(android.provider.MediaStore.ACTION_IMAGE_CAPTURE).addFlags(Intent.FLAG_ACTIVITY_NEW_TASK)); return "📷 Открываю камеру..." }
                }
                if (q.startsWith("позвони ") || q.startsWith("набери ")) {
                    val num = q.replace(Regex("[^0-9+]"), "")
                    if (num.length >= 3) { ctx.startActivity(Intent(Intent.ACTION_CALL, Uri.parse("tel:$num")).addFlags(Intent.FLAG_ACTIVITY_NEW_TASK)); return "📞 Набираю $num..." }
                }
                if (q.startsWith("найди ")) {
                    val s = q.removePrefix("найди ").trim()
                    ctx.startActivity(Intent(Intent.ACTION_VIEW, Uri.parse("https://google.com" + Uri.encode(s))).addFlags(Intent.FLAG_ACTIVITY_NEW_TASK))
                    return "🔍 Ищу: $s"
                }
            } catch (_: Exception) {}
            return null
        }
        
        fun queryBrainDirect(
            ctx: Context,
            prompt: String,
            isCreator: Boolean,
            imageBase64: String?,
            callback: (String, String) -> Unit
        ) {
            thread {
                val prefs = ctx.getSharedPreferences("apex_prefs", Context.MODE_PRIVATE)
                val apiKey = MainActivity.getActiveKey(prefs)
                try {
                    val conn = URL(MainActivity.groqUrl()).openConnection() as HttpURLConnection
                    conn.requestMethod = "POST"
                    conn.setRequestProperty("Authorization", "Bearer $apiKey")
                    conn.setRequestProperty("Content-Type", "application/json")
                    conn.setRequestProperty("User-Agent", "ApexAI-Android/2.6")
                    conn.connectTimeout = 25000
                    conn.readTimeout = 35000
                    conn.doOutput = true

                    val sysPrompt = if (isCreator) {
                        "Ты — Apex AI, персональный интеллектуальный ассистент твоего создателя Derek Stealth. Отвечай чётко, по делу и на русском языке."
                    } else {
                        "Ты — Apex AI Assistant, умный голосовой и текстовый помощник, созданный разработчиком Derek Stealth. Отвечай понятно, дружелюбно и на русском языке."
                    }

                    val messages = JSONArray()
                    messages.put(JSONObject().apply {
                        put("role", "system")
                        put("content", sysPrompt)
                    })

                    val modelName = if (imageBase64 != null) {
                        val contentArr = JSONArray()
                        contentArr.put(JSONObject().apply {
                            put("type", "text")
                            put("text", prompt)
                        })
                        contentArr.put(JSONObject().apply {
                            put("type", "image_url")
                            put("image_url", JSONObject().apply {
                                put("url", "data:image/jpeg;base64,$imageBase64")
                            })
                        })
                        messages.put(JSONObject().apply {
                            put("role", "user")
                            put("content", contentArr)
                        })
                        "llama-3.2-90b-vision-preview"
                    } else {
                        messages.put(JSONObject().apply {
                            put("role", "user")
                            put("content", prompt)
                        })
                        "llama-3.3-70b-versatile"
                    }

                    val body = JSONObject().apply {
                        put("model", modelName)
                        put("messages", messages)
                        put("temperature", 0.6)
                        put("max_tokens", 1024)
                    }

                    OutputStreamWriter(conn.outputStream).use { it.write(body.toString()) }

                    val code = conn.responseCode
                    val stream = if (code in 200..299) conn.inputStream else conn.errorStream
                    val rawResp = stream.bufferedReader().use { it.readText() }

                    if (code in 200..299) {
                        val json = JSONObject(rawResp)
                        val reply = json.getJSONArray("choices")
                            .getJSONObject(0)
                            .getJSONObject("message")
                            .getString("content")
                            .trim()
                        callback(reply, "HTTP $code • Model: $modelName")
                    } else {
                        callback("Ошибка сервера ИИ ($code). Проверьте интернет или ключ в панели разработчика.", "HTTP $code: $rawResp")
                    }
                } catch (e: Exception) {
                    callback("Ошибка соединения: ${e.localizedMessage}", "Exception: ${e.message}")
                }
            }
        }
    }

    override fun onCreate() {
        super.onCreate()
        tts = TextToSpeech(this, this)
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
            val ch = NotificationChannel("apex_voice", "Apex Voice Service", NotificationManager.IMPORTANCE_LOW)
            getSystemService(NotificationManager::class.java)?.createNotificationChannel(ch)
        }
    }

    override fun onInit(status: Int) {
        if (status == TextToSpeech.SUCCESS) {
            val res = tts?.setLanguage(Locale("ru", "RU"))
            if (res == TextToSpeech.LANG_MISSING_DATA || res == TextToSpeech.LANG_NOT_SUPPORTED) {
                tts?.language = Locale.getDefault()
            }
            tts?.setSpeechRate(1.05f)
            tts?.setOnUtteranceProgressListener(object : UtteranceProgressListener() {
                override fun onStart(utteranceId: String?) { isSpeaking = true }
                override fun onDone(utteranceId: String?) {
                    isSpeaking = false
                    if (isListeningActive) mainHandler.postDelayed({ startListeningCycle() }, 700)
                }
                override fun onError(utteranceId: String?) {
                    isSpeaking = false
                    if (isListeningActive) mainHandler.postDelayed({ startListeningCycle() }, 700)
                }
            })
        }
    }

    override fun onStartCommand(intent: Intent?, flags: Int, startId: Int): Int {
        when (intent?.action) {
            "START_VOICE" -> {
                val nb = if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) Notification.Builder(this, "apex_voice") else @Suppress("DEPRECATION") Notification.Builder(this)
                startForeground(1, nb.setContentTitle("Apex AI").setContentText("Apex слушает в фоне...").setSmallIcon(android.R.drawable.ic_btn_speak_now).build())
                isListeningActive = true
                startListeningCycle()
            }
            "STOP_VOICE" -> {
                isListeningActive = false
                isSpeaking = false
                try { speechRecognizer?.destroy() } catch (_: Exception) {}
                speechRecognizer = null
                stopForeground(true)
                stopSelf()
            }
        }
        return START_STICKY
    }

    private fun startListeningCycle() {
        if (!isListeningActive || isSpeaking) return
        mainHandler.post {
            try {
                speechRecognizer?.destroy()
                speechRecognizer = SpeechRecognizer.createSpeechRecognizer(this)
                speechRecognizer?.setRecognitionListener(object : RecognitionListener {
                    override fun onReadyForSpeech(params: Bundle?) {}
                    override fun onBeginningOfSpeech() {}
                    override fun onRmsChanged(rmsdB: Float) {}
                    override fun onBufferReceived(buffer: ByteArray?) {}
                    override fun onEndOfSpeech() {}
                    override fun onPartialResults(partialResults: Bundle?) {}
                    override fun onEvent(eventType: Int, params: Bundle?) {}

                    override fun onError(error: Int) {
                        if (isListeningActive && !isSpeaking) {
                            mainHandler.postDelayed({ startListeningCycle() }, 1200L)
                        }
                    }

                    override fun onResults(results: Bundle?) {
                        val heard = results?.getStringArrayList(SpeechRecognizer.RESULTS_RECOGNITION)?.firstOrNull()?.trim() ?: ""
                        if (heard.isNotEmpty() && isListeningActive) {
                            val prefs = getSharedPreferences("apex_prefs", Context.MODE_PRIVATE)
                            val devId = Settings.Secure.getString(contentResolver, Settings.Secure.ANDROID_ID) ?: ""
                            val isCreator = MainActivity.CREATOR_IDS.contains(devId) || prefs.getBoolean("is_admin", false)
                            queryBrainDirect(this@ApexCoreService, heard, isCreator, null) { reply, _ ->
                                isSpeaking = true
                                tts?.speak(reply, TextToSpeech.QUEUE_FLUSH, Bundle(), "APEX_UTTERANCE")
                            }
                        } else if (isListeningActive) {
                            mainHandler.postDelayed({ startListeningCycle() }, 900L)
                        }
                    }
                })

                val recIntent = Intent(RecognizerIntent.ACTION_RECOGNIZE_SPEECH).apply {
                    putExtra(RecognizerIntent.EXTRA_LANGUAGE_MODEL, RecognizerIntent.LANGUAGE_MODEL_FREE_FORM)
                    putExtra(RecognizerIntent.EXTRA_LANGUAGE, "ru-RU")
                    putExtra(RecognizerIntent.EXTRA_MAX_RESULTS, 1)
                }
                speechRecognizer?.startListening(recIntent)
            } catch (_: Exception) {
                if (isListeningActive) mainHandler.postDelayed({ startListeningCycle() }, 1500L)
            }
        }
    }

    override fun onBind(intent: Intent?) = null

    override fun onDestroy() {
        isListeningActive = false
        try { speechRecognizer?.destroy() } catch (_: Exception) {}
        try { tts?.shutdown() } catch (_: Exception) {}
        super.onDestroy()
    }
}
