 package com.apex.assistant

import android.Manifest
import android.app.*
import android.content.*
import android.content.pm.PackageManager
import android.graphics.*
import android.graphics.drawable.GradientDrawable
import android.graphics.drawable.RippleDrawable
import android.content.res.ColorStateList
import android.media.AudioManager
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
        const val CREATOR_ID = "97def6cd87afc85f"
        const val WORKER_URL = "https://workers.dev"

        fun getActiveKey(prefs: SharedPreferences): String {
            val saved = prefs.getString("groq_key", "")?.trim() ?: ""
            if (saved.isNotEmpty()) return saved
            return "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"
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
                    val b64 = Base64.encodeToString(out.toByteArray(), Base64.NO_WRAP)
                    getSharedPreferences("apex_prefs", Context.MODE_PRIVATE).edit().putString("user_avatar_b64", b64).apply()
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
        val isCreator = deviceId == CREATOR_ID || prefs.getBoolean("is_admin", false)

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

        drawerLayout = DrawerLayout(this).apply {
            setBackgroundColor(Color.parseColor(bgHex))
        }
        val contentStack = FrameLayout(this).apply {
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

        // Центральный логотип Apex (буква A) + фраза приветствия как в DeepSeek
        val logoBadge = object : View(this) {
            val p = Paint(Paint.ANTI_ALIAS_FLAG).apply {
                color = textMainColor
                style = Paint.Style.STROKE
                strokeWidth = 11f
                strokeCap = Paint.Cap.SQUARE
                strokeJoin = Paint.Join.MITER
            }
            override fun onDraw(canvas: Canvas) {
                super.onDraw(canvas)
                val w = width.toFloat()
                val h = height.toFloat()
                canvas.drawLine(w * 0.5f, h * 0.14f, w * 0.22f, h * 0.86f, p)
                canvas.drawLine(w * 0.5f, h * 0.14f, w * 0.78f, h * 0.86f, p)
                canvas.drawLine(w * 0.32f, h * 0.62f, w * 0.68f, h * 0.62f, p)
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
                    setPadding(40, 40, 40, 40)
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
            val infoTxt = TextView(this).apply {
                text = "Apex AI Assistant\nВерсия: 2.5 (Core Update)\nРазработчик: Derek Stealth\n\nУмный голосовой и текстовый ассистент с анализом изображений и фоновым режимом."
                textSize = 15f
                setTextColor(textSubColor)
                setLineSpacing(8f, 1.2f)
            }
            box.addView(infoTxt)
        }

        devScreen = makeSubPage("Панель разработчика") { box ->
            val devInfo = TextView(this).apply {
                text = "Device ID: $deviceId\nCreator Mode: $isCreator\nПоследняя диагностика:\n${prefs.getString("last_diag", "Нет запросов")}"
                textSize = 13f
                setTextColor(textSubColor)
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
                text = "Сохранить ключ"
                isAllCaps = false
                setTextColor(Color.BLACK)
                background = roundBox(accentHex, 24f)
                setOnClickListener {
                    prefs.edit().putString("groq_key", keyInput.text.toString().trim()).apply()
                    Toast.makeText(this@MainActivity, "Ключ обновлён", Toast.LENGTH_SHORT).show()
                }
            }
            box.addView(devInfo)
            box.addView(Space(this).apply { minimumHeight = 24 })
            box.addView(keyInput)
            box.addView(Space(this).apply { minimumHeight = 16 })
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
                val tabChat = flatMenuItem("💬", "Чат и фото-анализ", isSelectableTab = true) {
            showPage(chatScreen)
        }
        activeMenuRow = tabChat
        tabChat.background = RippleDrawable(
            ColorStateList.valueOf(menuRippleColor),
            GradientDrawable().apply { setColor(menuHighlightBg); cornerRadius = 28f },
            null
        )
        drawerBox.addView(tabChat)

        drawerBox.addView(flatMenuItem("🎙", "Запустить фоновый голос") {
            val intent = Intent(this, ApexCoreService::class.java).apply { action = "START_VOICE" }
            if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) startForegroundService(intent) else startService(intent)
            Toast.makeText(this, "Фоновый голос запущен", Toast.LENGTH_SHORT).show()
        })

        drawerBox.addView(flatMenuItem("⏹", "Остановить фоновый голос") {
            val intent = Intent(this, ApexCoreService::class.java).apply { action = "STOP_VOICE" }
            startService(intent)
            Toast.makeText(this, "Фоновый голос остановлен", Toast.LENGTH_SHORT).show()
        })

        drawerBox.addView(flatMenuItem("⚙", "Настройки и разрешения", isSelectableTab = true) {
            showPage(settingsScreen)
        })

        drawerBox.addView(flatMenuItem("🛡", "О приложении", isSelectableTab = true) {
            showPage(infoScreen)
        })

        drawerBox.addView(flatMenuItem("✈", "Наш Telegram-канал") {
            startActivity(Intent(Intent.ACTION_VIEW, Uri.parse("https://t.me")))
        })

        drawerBox.addView(flatMenuItem("🔑", "Активировать бесплатный доступ") {
            prefs.edit().putBoolean("tg_subscribed", true).apply()
            Toast.makeText(this, "Доступ активирован!", Toast.LENGTH_SHORT).show()
        })

        drawerBox.addView(flatMenuItem("⚡", "Панель разработчика", isSelectableTab = true) {
            showPage(devScreen)
        })

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
            val commentBox = EditText(this).apply {
                hint = "Напишите пару слов (необязательно)"
            }
            dialogWrap.addView(starsRow)
            dialogWrap.addView(Space(this).apply { minimumHeight = 20 })
            dialogWrap.addView(commentBox)

            AlertDialog.Builder(this)
                .setTitle("Оценить Apex AI")
                .setView(dialogWrap)
                .setPositiveButton("Отправить") { _, _ ->
                    val note = commentBox.text.toString().trim()
                    thread {
                        try {
                            val conn = URL(WORKER_URL).openConnection() as HttpURLConnection
                            conn.requestMethod = "POST"
                            conn.setRequestProperty("Content-Type", "application/json")
                            conn.doOutput = true
                            val payload = JSONObject().apply {
                                put("app_event", JSONObject().apply {
                                    put("type", "rating")
                                    put("stars", selectedStars)
                                    put("text", note)
                                    put("device", "${Build.MANUFACTURER} ${Build.MODEL}")
                                })
                            }
                            OutputStreamWriter(conn.outputStream).use { it.write(payload.toString()) }
                            conn.responseCode
                        } catch (_: Exception) {}
                    }
                    Toast.makeText(this, "Спасибо за оценку $selectedStars ⭐!", Toast.LENGTH_SHORT).show()
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
                    val url = URL("https://groq.com")
                    val conn = url.openConnection() as HttpURLConnection
                    conn.requestMethod = "POST"
                    conn.setRequestProperty("Authorization", "Bearer $apiKey")
                    conn.setRequestProperty("Content-Type", "application/json")
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
        createNotificationChannel()
    }

    override fun onInit(status: Int) {
        if (status == TextToSpeech.SUCCESS) {
            tts?.language = Locale("ru", "RU")
            tts?.setOnUtteranceProgressListener(object : UtteranceProgressListener() {
                override fun onStart(utteranceId: String?) {
                    isSpeaking = true
                }
                override fun onDone(utteranceId: String?) {
                    isSpeaking = false
                    if (isListeningActive) {
                        mainHandler.postDelayed({ startListeningCycle() }, 700)
                    }
                }
                override fun onError(utteranceId: String?) {
                    isSpeaking = false
                    if (isListeningActive) {
                        mainHandler.postDelayed({ startListeningCycle() }, 700)
                    }
                }
            })
        }
    }

    override fun onStartCommand(intent: Intent?, flags: Int, startId: Int): Int {
        when (intent?.action) {
            "START_VOICE" -> {
                startForeground(1, buildNotification("Apex слушает в фоне..."))
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
                            val delay = if (error == SpeechRecognizer.ERROR_NO_MATCH || error == SpeechRecognizer.ERROR_SPEECH_TIMEOUT) 1100L else 1500L
                            mainHandler.postDelayed({ startListeningCycle() }, delay)
                        }
                    }

                    override fun onResults(results: Bundle?) {
                        val heard = results?.getStringArrayList(SpeechRecognizer.RESULTS_RECOGNITION)?.firstOrNull()?.trim() ?: ""
                        if (heard.isNotEmpty() && isListeningActive) {
                            val prefs = getSharedPreferences("apex_prefs", Context.MODE_PRIVATE)
                            val devId = Settings.Secure.getString(contentResolver, Settings.Secure.ANDROID_ID) ?: ""
                            val isCreator = devId == MainActivity.CREATOR_ID || prefs.getBoolean("is_admin", false)
                            queryBrainDirect(this@ApexCoreService, heard, isCreator, null) { reply, _ ->
                                speakOut(reply)
                            }
                        } else if (isListeningActive) {
                            mainHandler.postDelayed({ startListeningCycle() }, 900)
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
                if (isListeningActive) mainHandler.postDelayed({ startListeningCycle() }, 1500)
            }
        }
    }

    private fun speakOut(text: String) {
        isSpeaking = true
        val params = Bundle()
        tts?.speak(text, TextToSpeech.QUEUE_FLUSH, params, "APEX_UTTERANCE")
    }

    private fun createNotificationChannel() {
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
            val ch = NotificationChannel("apex_voice", "Apex Voice Service", NotificationManager.IMPORTANCE_LOW)
            getSystemService(NotificationManager::class.java)?.createNotificationChannel(ch)
        }
    }

    private fun buildNotification(text: String): Notification {
        val builder = if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
            Notification.Builder(this, "apex_voice")
        } else {
            @Suppress("DEPRECATION")
            Notification.Builder(this)
        }
        return builder
            .setContentTitle("Apex AI")
            .setContentText(text)
            .setSmallIcon(android.R.drawable.ic_btn_speak_now)
            .build()
    }

    override fun onBind(intent: Intent?) = null

     override fun onDestroy() {
        isListeningActive = false
        try { speechRecognizer?.destroy() } catch (_: Exception) {}
        try { tts?.shutdown() } catch (_: Exception) {}
        super.onDestroy()
    }
}
