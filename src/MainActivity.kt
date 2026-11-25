package com.apex.assistant

import android.Manifest
import android.app.AlertDialog
import android.content.ClipData
import android.content.ClipboardManager
import android.content.Context
import android.content.Intent
import android.content.pm.PackageManager
import android.graphics.*
import android.graphics.drawable.GradientDrawable
import android.net.Uri
import android.os.Build
import android.os.Bundle
import android.speech.RecognitionListener
import android.speech.RecognizerIntent
import android.speech.SpeechRecognizer
import android.speech.tts.TextToSpeech
import android.util.Base64
import android.view.Gravity
import android.view.View
import android.widget.*
import androidx.activity.result.contract.ActivityResultContracts
import androidx.appcompat.app.AppCompatActivity
import androidx.core.app.ActivityCompat
import androidx.core.content.ContextCompat
import androidx.drawerlayout.widget.DrawerLayout
import org.json.JSONArray
import org.json.JSONObject
import java.io.ByteArrayOutputStream
import java.io.File
import java.io.FileOutputStream
import java.util.Locale
import java.util.UUID
import kotlin.concurrent.thread

class MainActivity : AppCompatActivity() {

    private val prefs by lazy { getSharedPreferences("apex_prefs", Context.MODE_PRIVATE) }
    private var currentChatId: String = UUID.randomUUID().toString()
    private val messages = mutableListOf<Pair<String, String>>()
    private var pendingImageBase64: String? = null
    private var tts: TextToSpeech? = null
    private var ttsReady = false
    private var speechRecognizer: SpeechRecognizer? = null
    private var isListening = false
    private var voiceMode = true
    private var autoSpeak = false
    private var openedChannel = false

    private lateinit var drawerLayout: DrawerLayout
    private lateinit var rootContainer: RelativeLayout
    private lateinit var topBar: LinearLayout
    private lateinit var titleText: TextView
    private lateinit var chatScroll: ScrollView
    private lateinit var chatList: LinearLayout
    private lateinit var heroBox: LinearLayout
    private lateinit var heroTitle: TextView
    private lateinit var heroSub: TextView
    private lateinit var inputBox: LinearLayout
    private lateinit var inputEt: EditText
    private lateinit var micBtn: TextView
    private lateinit var sendBtn: TextView
    private lateinit var imgBadge: TextView
    private lateinit var voiceBanner: TextView

    private lateinit var drawerScroll: ScrollView
    private lateinit var drawerContent: LinearLayout
    private lateinit var profileAvatarView: ImageView
    private lateinit var profileNameView: TextView
    private lateinit var drawerDivider: View
    private lateinit var chatsHeaderTv: TextView
    private lateinit var historyContainer: LinearLayout
    private val navRowViews = mutableListOf<LinearLayout>()

    data class ThemeSpec(val id: String, val bg: String, val surface: String, val border: String, val textPrimary: String, val textSecondary: String, val accent: String)

    private val themes = listOf(
        ThemeSpec("black", "#000000", "#121212", "#262626", "#F8FAFC", "#9CA3AF", "#2563EB"),
        ThemeSpec("red", "#1A0406", "#2B080C", "#6B141E", "#FEF2F2", "#FCA5A5", "#DC2626"),
        ThemeSpec("white", "#F8FAFC", "#FFFFFF", "#CBD5E1", "#0F172A", "#475569", "#2563EB"),
        ThemeSpec("pink", "#1D0614", "#2E0A20", "#701A4E", "#FDF2F8", "#F9A8D4", "#DB2777"),
        ThemeSpec("blue", "#030D21", "#091B3D", "#1E3A8A", "#EFF6FF", "#93C5FD", "#2563EB"),
        ThemeSpec("green", "#03170F", "#07291B", "#14532D", "#ECFDF5", "#6EE7B7", "#059669")
    )

    private fun currentTheme(): ThemeSpec = themes.firstOrNull { it.id == (prefs.getString("theme_id", "black") ?: "black") } ?: themes

    private val pickChatImageLauncher = registerForActivityResult(ActivityResultContracts.GetContent()) { uri: Uri? ->
        if (uri != null) {
            try {
                val bmp = contentResolver.openInputStream(uri)?.use { BitmapFactory.decodeStream(it) } ?: return@registerForActivityResult
                val ratio = minOf(1024f / bmp.width, 1024f / bmp.height, 1f)
                val scaled = Bitmap.createScaledBitmap(bmp, (bmp.width * ratio).toInt(), (bmp.height * ratio).toInt(), true)
                val out = ByteArrayOutputStream()
                scaled.compress(Bitmap.CompressFormat.JPEG, 82, out)
                pendingImageBase64 = Base64.encodeToString(out.toByteArray(), Base64.NO_WRAP)
                imgBadge.visibility = View.VISIBLE
                Toast.makeText(this, "Фото прикреплено", Toast.LENGTH_SHORT).show()
            } catch (_: Exception) { Toast.makeText(this, "Ошибка загрузки фото", Toast.LENGTH_SHORT).show() }
        }
    }

    private val pickAvatarLauncher = registerForActivityResult(ActivityResultContracts.GetContent()) { uri: Uri? ->
        if (uri != null) {
            try {
                val bmp = contentResolver.openInputStream(uri)?.use { BitmapFactory.decodeStream(it) } ?: return@registerForActivityResult
                val scaled = Bitmap.createScaledBitmap(bmp, 256, 256, true)
                FileOutputStream(File(filesDir, "user_avatar.png")).use { scaled.compress(Bitmap.CompressFormat.PNG, 95, it) }
                loadUserAvatar()
                Toast.makeText(this, "Аватарка обновлена", Toast.LENGTH_SHORT).show()
            } catch (_: Exception) { Toast.makeText(this, "Ошибка выбора фото", Toast.LENGTH_SHORT).show() }
        }
    }
        private fun dp(v: Int): Int = (v * resources.displayMetrics.density).toInt()

    private fun cropCircle(bmp: Bitmap): Bitmap {
        val s = minOf(bmp.width, bmp.height)
        val sq = Bitmap.createBitmap(bmp, (bmp.width - s) / 2, (bmp.height - s) / 2, s, s)
        val out = Bitmap.createBitmap(s, s, Bitmap.Config.ARGB_8888)
        val c = Canvas(out)
        val p = Paint(Paint.ANTI_ALIAS_FLAG)
        c.drawCircle(s / 2f, s / 2f, s / 2f, p)
        p.xfermode = PorterDuffXfermode(PorterDuff.Mode.SRC_IN)
        c.drawBitmap(sq, Rect(0, 0, s, s), Rect(0, 0, s, s), p)
        return out
    }

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        voiceMode = prefs.getBoolean("voice_mode", true)
        autoSpeak = prefs.getBoolean("auto_speak", false)
        tts = TextToSpeech(this) { if (it == TextToSpeech.SUCCESS) { tts?.language = Locale("ru", "RU"); ttsReady = true } }
        buildUI()
        applyTheme()
        loadUserAvatar()
        refreshHistoryList()
        if (!prefs.getBoolean("sub_verified", false)) showAccessGate()
    }

    private fun buildUI() {
        drawerLayout = DrawerLayout(this)
        rootContainer = RelativeLayout(this)

        topBar = LinearLayout(this).apply { id = View.generateViewId(); orientation = LinearLayout.HORIZONTAL; gravity = Gravity.CENTER_VERTICAL; setPadding(dp(16), dp(14), dp(16), dp(14)) }
        val menuBtn = TextView(this).apply { text = "≡"; textSize = 26f; setPadding(dp(8), dp(4), dp(12), dp(4)); setOnClickListener { drawerLayout.openDrawer(Gravity.START) } }
        titleText = TextView(this).apply { text = "APEX AI"; textSize = 18f; typeface = Typeface.DEFAULT_BOLD; gravity = Gravity.CENTER; layoutParams = LinearLayout.LayoutParams(0, LinearLayout.LayoutParams.WRAP_CONTENT, 1f) }
        val newChatTopBtn = TextView(this).apply { text = "+"; textSize = 26f; setPadding(dp(12), dp(4), dp(8), dp(4)); setOnClickListener { startNewChat() } }
        topBar.addView(menuBtn); topBar.addView(titleText); topBar.addView(newChatTopBtn)
        rootContainer.addView(topBar, RelativeLayout.LayoutParams(RelativeLayout.LayoutParams.MATCH_PARENT, RelativeLayout.LayoutParams.WRAP_CONTENT).apply { addRule(RelativeLayout.ALIGN_PARENT_TOP) })

        voiceBanner = TextView(this).apply { id = View.generateViewId(); text = "Слушаю вас... Говорите"; textSize = 14f; typeface = Typeface.DEFAULT_BOLD; gravity = Gravity.CENTER; setPadding(dp(12), dp(8), dp(12), dp(8)); visibility = View.GONE }
        rootContainer.addView(voiceBanner, RelativeLayout.LayoutParams(RelativeLayout.LayoutParams.MATCH_PARENT, RelativeLayout.LayoutParams.WRAP_CONTENT).apply { addRule(RelativeLayout.BELOW, topBar.id) })

        val bottomWrapper = LinearLayout(this).apply { id = View.generateViewId(); orientation = LinearLayout.VERTICAL; setPadding(dp(12), dp(8), dp(12), dp(14)) }
        imgBadge = TextView(this).apply { text = "Фото прикреплено (нажмите, чтобы убрать)"; textSize = 12f; setPadding(dp(12), dp(6), dp(12), dp(6)); visibility = View.GONE; setOnClickListener { pendingImageBase64 = null; visibility = View.GONE } }
        bottomWrapper.addView(imgBadge)

        inputBox = LinearLayout(this).apply { orientation = LinearLayout.HORIZONTAL; gravity = Gravity.CENTER_VERTICAL; setPadding(dp(8), dp(6), dp(8), dp(6)) }
        val attachBtn = TextView(this).apply { text = "+"; textSize = 22f; gravity = Gravity.CENTER; layoutParams = LinearLayout.LayoutParams(dp(38), dp(38)); setOnClickListener { pickChatImageLauncher.launch("image/*") } }
        inputEt = EditText(this).apply { hint = "Спросите Apex AI..."; textSize = 15f; background = null; maxLines = 4; setPadding(dp(8), dp(8), dp(8), dp(8)); layoutParams = LinearLayout.LayoutParams(0, LinearLayout.LayoutParams.WRAP_CONTENT, 1f) }
        micBtn = TextView(this).apply { text = "MIC"; textSize = 11f; typeface = Typeface.DEFAULT_BOLD; gravity = Gravity.CENTER; layoutParams = LinearLayout.LayoutParams(dp(40), dp(38)).apply { marginEnd = dp(6) }; setOnClickListener { toggleVoiceInput() } }
        sendBtn = TextView(this).apply { text = "↑"; textSize = 18f; typeface = Typeface.DEFAULT_BOLD; gravity = Gravity.CENTER; layoutParams = LinearLayout.LayoutParams(dp(38), dp(38)); setOnClickListener { sendMessage() } }
        inputBox.addView(attachBtn); inputBox.addView(inputEt); inputBox.addView(micBtn); inputBox.addView(sendBtn)
        bottomWrapper.addView(inputBox)
        rootContainer.addView(bottomWrapper, RelativeLayout.LayoutParams(RelativeLayout.LayoutParams.MATCH_PARENT, RelativeLayout.LayoutParams.WRAP_CONTENT).apply { addRule(RelativeLayout.ALIGN_PARENT_BOTTOM) })

        heroBox = LinearLayout(this).apply { orientation = LinearLayout.VERTICAL; gravity = Gravity.CENTER; setPadding(dp(24), dp(24), dp(24), dp(24)) }
        val centerImg = ImageView(this).apply {
            scaleType = ImageView.ScaleType.CENTER_CROP
            layoutParams = LinearLayout.LayoutParams(dp(116), dp(116)).apply { bottomMargin = dp(18) }
            val resId = resources.getIdentifier("brand_logo", "drawable", packageName)
            val rawBmp = if (resId != 0) BitmapFactory.decodeResource(resources, resId) else null
            if (rawBmp != null) setImageBitmap(cropCircle(rawBmp))
        }
        heroTitle = TextView(this).apply { text = "Чем помочь сегодня?"; textSize = 22f; typeface = Typeface.DEFAULT_BOLD; gravity = Gravity.CENTER }
        heroSub = TextView(this).apply { text = "Голосовой и текстовый ассистент"; textSize = 14f; gravity = Gravity.CENTER; setPadding(0, dp(6), 0, 0) }
        heroBox.addView(centerImg); heroBox.addView(heroTitle); heroBox.addView(heroSub)
        rootContainer.addView(heroBox, RelativeLayout.LayoutParams(RelativeLayout.LayoutParams.MATCH_PARENT, RelativeLayout.LayoutParams.WRAP_CONTENT).apply { addRule(RelativeLayout.CENTER_IN_PARENT) })

        chatScroll = ScrollView(this).apply { isFillViewport = true }
        chatList = LinearLayout(this).apply { orientation = LinearLayout.VERTICAL; setPadding(dp(14), dp(8), dp(14), dp(16)) }
        chatScroll.addView(chatList)
        rootContainer.addView(chatScroll, RelativeLayout.LayoutParams(RelativeLayout.LayoutParams.MATCH_PARENT, RelativeLayout.LayoutParams.MATCH_PARENT).apply { addRule(RelativeLayout.BELOW, voiceBanner.id); addRule(RelativeLayout.ABOVE, bottomWrapper.id) })
        drawerLayout.addView(rootContainer, DrawerLayout.LayoutParams(DrawerLayout.LayoutParams.MATCH_PARENT, DrawerLayout.LayoutParams.MATCH_PARENT))

        drawerScroll = ScrollView(this).apply { isFillViewport = true }
        drawerContent = LinearLayout(this).apply { orientation = LinearLayout.VERTICAL; setPadding(dp(18), dp(22), dp(18), dp(24)) }

        val profileRow = LinearLayout(this).apply { orientation = LinearLayout.HORIZONTAL; gravity = Gravity.CENTER_VERTICAL; layoutParams = LinearLayout.LayoutParams(LinearLayout.LayoutParams.MATCH_PARENT, LinearLayout.LayoutParams.WRAP_CONTENT).apply { bottomMargin = dp(12) } }
        profileAvatarView = ImageView(this).apply { scaleType = ImageView.ScaleType.CENTER_CROP; layoutParams = LinearLayout.LayoutParams(dp(50), dp(50)).apply { marginEnd = dp(14) }; setOnClickListener { pickAvatarLauncher.launch("image/*") } }
        val nameCol = LinearLayout(this).apply { orientation = LinearLayout.VERTICAL; layoutParams = LinearLayout.LayoutParams(0, LinearLayout.LayoutParams.WRAP_CONTENT, 1f); setOnClickListener { showEditNameDialog() } }
        profileNameView = TextView(this).apply { text = prefs.getString("user_nick", "Пользователь"); textSize = 17f; typeface = Typeface.DEFAULT_BOLD }
        val profileSub = TextView(this).apply { text = "Изменить фото или ник"; textSize = 12f; setPadding(0, dp(2), 0, 0) }
        nameCol.addView(profileNameView); nameCol.addView(profileSub)
        profileRow.addView(profileAvatarView); profileRow.addView(nameCol)
        drawerContent.addView(profileRow)

        val circlesRow = LinearLayout(this).apply { orientation = LinearLayout.HORIZONTAL; gravity = Gravity.CENTER_VERTICAL; layoutParams = LinearLayout.LayoutParams(LinearLayout.LayoutParams.MATCH_PARENT, LinearLayout.LayoutParams.WRAP_CONTENT).apply { bottomMargin = dp(14) } }
        themes.forEach { t ->
            val circle = View(this).apply {
                layoutParams = LinearLayout.LayoutParams(dp(30), dp(30)).apply { marginEnd = dp(12) }
                background = GradientDrawable().apply { shape = GradientDrawable.OVAL; setColor(Color.parseColor(t.bg)); setStroke(dp(2), Color.parseColor(t.accent)) }
                setOnClickListener { prefs.edit().putString("theme_id", t.id).apply(); applyTheme() }
            }
            circlesRow.addView(circle)
        }
        drawerContent.addView(circlesRow)
                navRowViews.clear()
        addNavRow("new", "Новый диалог") { startNewChat(); drawerLayout.closeDrawers() }
        lateinit var voiceLabel: TextView
        voiceLabel = addNavRow("mic", "Голосовой режим: ${if (voiceMode) "ВКЛ" else "ВЫКЛ"}") {
            voiceMode = !voiceMode; prefs.edit().putBoolean("voice_mode", voiceMode).apply()
            voiceLabel.text = "Голосовой режим: ${if (voiceMode) "ВКЛ" else "ВЫКЛ"}"
        }
        lateinit var speakLabel: TextView
        speakLabel = addNavRow("vol", "Автоозвучка: ${if (autoSpeak) "ВКЛ" else "ВЫКЛ"}") {
            autoSpeak = !autoSpeak; prefs.edit().putBoolean("auto_speak", autoSpeak).apply()
            speakLabel.text = "Автоозвучка: ${if (autoSpeak) "ВКЛ" else "ВЫКЛ"}"
        }
        addNavRow("perm", "Разрешения") { drawerLayout.closeDrawers(); showPermissionsDialog() }
        addNavRow("cmd", "Команды и возможности") {
            drawerLayout.closeDrawers()
            showInfoDialog("Команды и возможности", "Доступные команды:\n\n- Включи / выключи фонарик\n- Поставь будильник на 08:30\n- Поставь таймер на 10 минут\n- Открой YouTube / Telegram / Настройки\n- Отправьте фото через + для анализа")
        }
        addNavRow("rate", "Оценить Apex AI") { drawerLayout.closeDrawers(); showRatingDialog() }
        addNavRow("info", "О приложении") { drawerLayout.closeDrawers(); showAboutDialog() }

        drawerDivider = View(this).apply { layoutParams = LinearLayout.LayoutParams(LinearLayout.LayoutParams.MATCH_PARENT, dp(1)).apply { topMargin = dp(12); bottomMargin = dp(12) } }
        drawerContent.addView(drawerDivider)
        chatsHeaderTv = TextView(this).apply { text = "Чаты"; textSize = 13f; typeface = Typeface.DEFAULT_BOLD; setPadding(dp(4), 0, 0, dp(8)) }
        drawerContent.addView(chatsHeaderTv)
        historyContainer = LinearLayout(this).apply { orientation = LinearLayout.VERTICAL; layoutParams = LinearLayout.LayoutParams(LinearLayout.LayoutParams.MATCH_PARENT, LinearLayout.LayoutParams.WRAP_CONTENT) }
        drawerContent.addView(historyContainer)

        drawerScroll.addView(drawerContent)
        drawerLayout.addView(drawerScroll, DrawerLayout.LayoutParams((resources.displayMetrics.widthPixels * 0.80).toInt(), DrawerLayout.LayoutParams.MATCH_PARENT, Gravity.START))
        setContentView(drawerLayout)
    }

    private fun addNavRow(iconType: String, label: String, onClick: () -> Unit): TextView {
        val row = LinearLayout(this).apply {
            orientation = LinearLayout.HORIZONTAL; gravity = Gravity.CENTER_VERTICAL; setPadding(dp(4), dp(11), dp(4), dp(11))
            layoutParams = LinearLayout.LayoutParams(LinearLayout.LayoutParams.MATCH_PARENT, LinearLayout.LayoutParams.WRAP_CONTENT); setOnClickListener { onClick() }
        }
        val iconView = VectorNavIcon(this, iconType).apply { layoutParams = LinearLayout.LayoutParams(dp(22), dp(22)).apply { marginEnd = dp(16) } }
        val tv = TextView(this).apply { text = label; textSize = 16f; layoutParams = LinearLayout.LayoutParams(0, LinearLayout.LayoutParams.WRAP_CONTENT, 1f) }
        row.addView(iconView); row.addView(tv); drawerContent.addView(row); navRowViews.add(row)
        return tv
    }

    private fun applyTheme() {
        val t = currentTheme()
        val bgCol = Color.parseColor(t.bg); val surfCol = Color.parseColor(t.surface); val bordCol = Color.parseColor(t.border)
        val primCol = Color.parseColor(t.textPrimary); val secCol = Color.parseColor(t.textSecondary); val accCol = Color.parseColor(t.accent)
        rootContainer.setBackgroundColor(bgCol); topBar.setBackgroundColor(bgCol); titleText.setTextColor(primCol)
        (topBar.getChildAt(0) as TextView).setTextColor(primCol); (topBar.getChildAt(2) as TextView).setTextColor(primCol)
        heroTitle.setTextColor(primCol); heroSub.setTextColor(secCol); voiceBanner.setBackgroundColor(accCol); voiceBanner.setTextColor(Color.WHITE)
        inputBox.background = GradientDrawable().apply { setColor(surfCol); cornerRadius = dp(24).toFloat(); setStroke(dp(1), bordCol) }
        (inputBox.getChildAt(0) as TextView).setTextColor(primCol); inputEt.setTextColor(primCol); inputEt.setHintTextColor(secCol)
        micBtn.background = GradientDrawable().apply { setColor(if (isListening) Color.parseColor("#DC2626") else bordCol); cornerRadius = dp(19).toFloat() }; micBtn.setTextColor(primCol)
        sendBtn.background = GradientDrawable().apply { setColor(accCol); cornerRadius = dp(19).toFloat() }; sendBtn.setTextColor(Color.WHITE)
        drawerScroll.setBackgroundColor(bgCol); profileNameView.setTextColor(primCol)
        ((drawerContent.getChildAt(0) as LinearLayout).getChildAt(1) as LinearLayout).getChildAt(1).let { (it as TextView).setTextColor(secCol) }
        navRowViews.forEach { row -> (row.getChildAt(0) as VectorNavIcon).setTint(primCol); (row.getChildAt(1) as TextView).setTextColor(primCol) }
        drawerDivider.setBackgroundColor(bordCol); chatsHeaderTv.setTextColor(secCol)
        for (i in 0 until historyContainer.childCount) (historyContainer.getChildAt(i) as? TextView)?.setTextColor(primCol)
        renderChat()
    }

    private fun loadUserAvatar() {
        val file = File(filesDir, "user_avatar.png")
        val bmp = if (file.exists()) BitmapFactory.decodeFile(file.absolutePath) else {
            val resId = resources.getIdentifier("brand_logo", "drawable", packageName)
            if (resId != 0) BitmapFactory.decodeResource(resources, resId) else null
        }
        if (bmp != null) profileAvatarView.setImageBitmap(cropCircle(bmp))
    }

    private fun showEditNameDialog() {
        val et = EditText(this).apply { setText(prefs.getString("user_nick", "Пользователь")); setPadding(dp(16), dp(12), dp(16), dp(12)) }
        AlertDialog.Builder(this).setTitle("Ваш никнейм").setView(et).setPositiveButton("Сохранить") { _, _ ->
            val nick = et.text.toString().trim().ifBlank { "Пользователь" }
            prefs.edit().putString("user_nick", nick).apply(); profileNameView.text = nick
        }.setNegativeButton("Отмена", null).show()
    }
        private fun toggleVoiceInput() {
        if (!voiceMode) { Toast.makeText(this, "Включите голосовой режим в меню", Toast.LENGTH_SHORT).show(); return }
        if (ContextCompat.checkSelfPermission(this, Manifest.permission.RECORD_AUDIO) != PackageManager.PERMISSION_GRANTED) {
            ActivityCompat.requestPermissions(this, arrayOf(Manifest.permission.RECORD_AUDIO), 101); return
        }
        if (isListening) { stopListening(); return }
        if (!SpeechRecognizer.isRecognitionAvailable(this)) { Toast.makeText(this, "Голосовой ввод недоступен", Toast.LENGTH_LONG).show(); return }
        try {
            speechRecognizer?.destroy()
            speechRecognizer = SpeechRecognizer.createSpeechRecognizer(this).apply {
                setRecognitionListener(object : RecognitionListener {
                    override fun onReadyForSpeech(params: Bundle?) { isListening = true; voiceBanner.visibility = View.VISIBLE; applyTheme() }
                    override fun onBeginningOfSpeech() {}
                    override fun onRmsChanged(rmsdB: Float) {}
                    override fun onBufferReceived(buffer: ByteArray?) {}
                    override fun onEndOfSpeech() {}
                    override fun onError(error: Int) { stopListening(); Toast.makeText(this@MainActivity, "Не удалось распознать речь", Toast.LENGTH_SHORT).show() }
                    override fun onResults(results: Bundle?) {
                        stopListening()
                        val spoken = results?.getStringArrayList(SpeechRecognizer.RESULTS_RECOGNITION)?.firstOrNull()
                        if (!spoken.isNullOrBlank()) { inputEt.setText(spoken); sendMessage(fromVoice = true) }
                    }
                    override fun onPartialResults(partialResults: Bundle?) {
                        val partial = partialResults?.getStringArrayList(SpeechRecognizer.RESULTS_RECOGNITION)?.firstOrNull()
                        if (!partial.isNullOrBlank()) voiceBanner.text = partial
                    }
                    override fun onEvent(eventType: Int, params: Bundle?) {}
                })
            }
            val intent = Intent(RecognizerIntent.ACTION_RECOGNIZE_SPEECH).apply {
                putExtra(RecognizerIntent.EXTRA_LANGUAGE_MODEL, RecognizerIntent.LANGUAGE_MODEL_FREE_FORM)
                putExtra(RecognizerIntent.EXTRA_LANGUAGE, "ru-RU")
                putExtra(RecognizerIntent.EXTRA_PARTIAL_RESULTS, true)
            }
            voiceBanner.text = "Слушаю вас... Говорите"
            speechRecognizer?.startListening(intent)
        } catch (_: Exception) { stopListening(); Toast.makeText(this, "Ошибка запуска микрофона", Toast.LENGTH_SHORT).show() }
    }

    private fun stopListening() { isListening = false; voiceBanner.visibility = View.GONE; try { speechRecognizer?.stopListening() } catch (_: Exception) {}; applyTheme() }

    private fun sendMessage(fromVoice: Boolean = false) {
        val rawText = inputEt.text.toString().trim(); val img = pendingImageBase64
        if (rawText.isBlank() && img == null) return
        inputEt.setText(""); pendingImageBase64 = null; imgBadge.visibility = View.GONE; heroBox.visibility = View.GONE
        val displayUser = if (img != null) "[Фото] ${rawText.ifBlank { "Что на изображении?" }}" else rawText
        messages.add("user" to displayUser); renderChat(); saveCurrentChat()
        val localReply = if (img == null) ApexEngine.runLocalCommand(this, rawText) else null
        if (localReply != null) { messages.add("assistant" to localReply); renderChat(); saveCurrentChat(); if (autoSpeak || fromVoice) speakText(localReply); return }
        messages.add("assistant" to "Думаю..."); renderChat()
        val historyCopy = messages.dropLast(1).toList()
        thread {
            val reply = ApexEngine.askAi(historyCopy, img)
            runOnUiThread {
                if (messages.isNotEmpty() && messages.last().second == "Думаю...") messages.removeAt(messages.size - 1)
                messages.add("assistant" to reply); renderChat(); saveCurrentChat()
                if (autoSpeak || fromVoice) speakText(reply)
            }
        }
    }

    private fun renderChat() {
        val t = currentTheme(); chatList.removeAllViews(); heroBox.visibility = if (messages.isEmpty()) View.VISIBLE else View.GONE
        messages.forEach { (role, text) ->
            val isUser = role == "user"
            val row = LinearLayout(this).apply { orientation = LinearLayout.VERTICAL; gravity = if (isUser) Gravity.END else Gravity.START; layoutParams = LinearLayout.LayoutParams(LinearLayout.LayoutParams.MATCH_PARENT, LinearLayout.LayoutParams.WRAP_CONTENT).apply { bottomMargin = dp(12) } }
            val bubble = LinearLayout(this).apply {
                orientation = LinearLayout.VERTICAL; setPadding(dp(14), dp(11), dp(14), dp(11))
                background = GradientDrawable().apply { setColor(if (isUser) Color.parseColor(t.accent) else Color.parseColor(t.surface)); cornerRadius = dp(16).toFloat(); if (!isUser) setStroke(dp(1), Color.parseColor(t.border)) }
                layoutParams = LinearLayout.LayoutParams(LinearLayout.LayoutParams.WRAP_CONTENT, LinearLayout.LayoutParams.WRAP_CONTENT).apply { if (isUser) marginStart = dp(48) else marginEnd = dp(32) }
            }
            bubble.addView(TextView(this).apply { this.text = text; textSize = 15f; setTextColor(if (isUser) Color.WHITE else Color.parseColor(t.textPrimary)) })
            if (!isUser && text != "Думаю...") {
                val actionsRow = LinearLayout(this).apply { orientation = LinearLayout.HORIZONTAL; setPadding(0, dp(8), 0, 0) }
                actionsRow.addView(TextView(this).apply { this.text = "Скопировать"; textSize = 12f; setTextColor(Color.parseColor(t.textSecondary)); setPadding(0, 0, dp(16), 0); setOnClickListener { (getSystemService(Context.CLIPBOARD_SERVICE) as ClipboardManager).setPrimaryClip(ClipData.newPlainText("ApexAI", text)); Toast.makeText(this@MainActivity, "Скопировано", Toast.LENGTH_SHORT).show() } })
                actionsRow.addView(TextView(this).apply { this.text = "Озвучить"; textSize = 12f; setTextColor(Color.parseColor(t.accent)); setOnClickListener { speakText(text) } })
                bubble.addView(actionsRow)
            }
            row.addView(bubble); chatList.addView(row)
        }
        chatScroll.post { chatScroll.fullScroll(View.FOCUS_DOWN) }
    }

    private fun speakText(text: String) { if (ttsReady) tts?.speak(text, TextToSpeech.QUEUE_FLUSH, null, UUID.randomUUID().toString()) }
    private fun startNewChat() { currentChatId = UUID.randomUUID().toString(); messages.clear(); pendingImageBase64 = null; imgBadge.visibility = View.GONE; renderChat() }

    private fun saveCurrentChat() {
        if (messages.isEmpty()) return
        val root = JSONObject(prefs.getString("all_chats", "{}") ?: "{}")
        val arr = JSONArray(); messages.forEach { (r, t) -> if (t != "Думаю...") arr.put(JSONObject().put("r", r).put("t", t)) }
        root.put(currentChatId, JSONObject().put("title", messages.firstOrNull { it.first == "user" }?.second?.take(34) ?: "Диалог").put("msgs", arr))
        prefs.edit().putString("all_chats", root.toString()).apply(); refreshHistoryList()
    }

    private fun refreshHistoryList() {
        val t = currentTheme(); historyContainer.removeAllViews()
        val root = JSONObject(prefs.getString("all_chats", "{}") ?: "{}"); val keys = root.keys(); val items = mutableListOf<Pair<String, String>>()
        while (keys.hasNext()) { val id = keys.next(); root.optJSONObject(id)?.let { items.add(id to it.optString("title", "Диалог")) } }
        if (items.isEmpty()) { historyContainer.addView(TextView(this).apply { text = "Пока нет диалогов"; textSize = 14f; setTextColor(Color.parseColor(t.textSecondary)); setPadding(dp(4), dp(8), dp(4), dp(8)) }); return }
        items.reversed().forEach { (id, title) ->
            historyContainer.addView(TextView(this).apply {
                text = title; textSize = 15f; maxLines = 1; setTextColor(Color.parseColor(t.textPrimary)); setPadding(dp(4), dp(11), dp(4), dp(11))
                setOnClickListener {
                    val arr = root.optJSONObject(id)?.optJSONArray("msgs") ?: return@setOnClickListener
                    currentChatId = id; messages.clear(); for (i in 0 until arr.length()) { val m = arr.getJSONObject(i); messages.add(m.getString("r") to m.getString("t")) }
                    renderChat(); drawerLayout.closeDrawers()
                }
            })
        }
    }

    private fun showAccessGate() {
        val t = currentTheme(); val box = LinearLayout(this).apply { orientation = LinearLayout.VERTICAL; setPadding(dp(22), dp(22), dp(22), dp(22)); setBackgroundColor(Color.parseColor(t.surface)) }
        box.addView(TextView(this).apply { text = "Бесплатный доступ к Apex AI"; textSize = 19f; typeface = Typeface.DEFAULT_BOLD; gravity = Gravity.CENTER; setTextColor(Color.parseColor(t.textPrimary)) })
        box.addView(TextView(this).apply { text = "Для бесплатного использования приложения подпишитесь на наш официальный Telegram-канал по кнопке ниже, после чего нажмите «Продолжить»."; textSize = 14f; gravity = Gravity.CENTER; setTextColor(Color.parseColor(t.textSecondary)); setPadding(0, dp(12), 0, dp(20)) })
        val dlg = AlertDialog.Builder(this).setView(box).setCancelable(false).create()
            private fun showAccessGate() {
        val t = currentTheme()
        val box = LinearLayout(this).apply { orientation = LinearLayout.VERTICAL; setPadding(dp(22), dp(22), dp(22), dp(22)); setBackgroundColor(Color.parseColor(t.surface)) }
        box.addView(TextView(this).apply { text = "Бесплатный доступ к Apex AI"; textSize = 19f; typeface = Typeface.DEFAULT_BOLD; gravity = Gravity.CENTER; setTextColor(Color.parseColor(t.textPrimary)) })
        box.addView(TextView(this).apply { text = "Для бесплатного использования приложения подпишитесь на наш официальный Telegram-канал по кнопке ниже, после чего нажмите «Продолжить»."; textSize = 14f; gravity = Gravity.CENTER; setTextColor(Color.parseColor(t.textSecondary)); setPadding(0, dp(12), 0, dp(20)) })
        val dlg = AlertDialog.Builder(this).setView(box).setCancelable(false).create()
        val btn1 = TextView(this).apply { text = "1. Подписаться на Telegram-канал"; textSize = 15f; typeface = Typeface.DEFAULT_BOLD; gravity = Gravity.CENTER; setTextColor(Color.WHITE); setPadding(dp(16), dp(14), dp(16), dp(14)); background = GradientDrawable().apply { setColor(Color.parseColor("#0284C7")); cornerRadius = dp(12).toFloat() } }
        btn1.layoutParams = LinearLayout.LayoutParams(LinearLayout.LayoutParams.MATCH_PARENT, LinearLayout.LayoutParams.WRAP_CONTENT).apply { bottomMargin = dp(12) }
        btn1.setOnClickListener { openedChannel = true; startActivity(Intent(Intent.ACTION_VIEW, Uri.parse(ApexEngine.CHANNEL_URL))) }
        val btn2 = TextView(this).apply { text = "2. Продолжить"; textSize = 15f; typeface = Typeface.DEFAULT_BOLD; gravity = Gravity.CENTER; setTextColor(Color.WHITE); setPadding(dp(16), dp(14), dp(16), dp(14)); background = GradientDrawable().apply { setColor(Color.parseColor(t.accent)); cornerRadius = dp(12).toFloat() } }
        btn2.setOnClickListener { if (!openedChannel) Toast.makeText(this@MainActivity, "Сначала нажмите кнопку подписки на канал", Toast.LENGTH_SHORT).show() else { prefs.edit().putBoolean("sub_verified", true).apply(); dlg.dismiss() } }
        box.addView(btn1); box.addView(btn2); dlg.show()
    }

    private fun showPermissionsDialog() {
        val perms = mutableListOf(Manifest.permission.RECORD_AUDIO, Manifest.permission.CAMERA)
        if (Build.VERSION.SDK_INT >= 33) perms.add(Manifest.permission.POST_NOTIFICATIONS)
        ActivityCompat.requestPermissions(this, perms.toTypedArray(), 102)
    }

    private fun showRatingDialog() {
        var selectedStars = 5
        val box = LinearLayout(this).apply { orientation = LinearLayout.VERTICAL; setPadding(dp(20), dp(20), dp(20), dp(20)) }
        val starsRow = LinearLayout(this).apply { orientation = LinearLayout.HORIZONTAL; gravity = Gravity.CENTER; setPadding(0, dp(8), 0, dp(14)) }
        val starBtns = mutableListOf<TextView>()
        for (i in 1..5) {
            val tv = TextView(this).apply { text = "[$i]"; textSize = 18f; typeface = Typeface.DEFAULT_BOLD; setPadding(dp(10), dp(8), dp(10), dp(8)); setTextColor(Color.parseColor("#2563EB")) }
            tv.setOnClickListener { selectedStars = i; starBtns.forEachIndexed { idx, b -> b.setTextColor(if (idx < i) Color.parseColor("#2563EB") else Color.GRAY) } }
            starBtns.add(tv); starsRow.addView(tv)
        }
        val et = EditText(this).apply { hint = "Напишите отзыв или пожелание..." }
        box.addView(starsRow); box.addView(et)
        AlertDialog.Builder(this).setTitle("Оценить Apex AI").setView(box).setPositiveButton("Отправить") { _, _ ->
            val comment = et.text.toString().trim(); val device = "${Build.MANUFACTURER} ${Build.MODEL}"
            thread { val (_, msg) = ApexEngine.sendRating(selectedStars, comment, device); runOnUiThread { Toast.makeText(this, msg, Toast.LENGTH_LONG).show() } }
        }.setNegativeButton("Отмена", null).show()
    }
        private fun showAboutDialog() {
        val box = LinearLayout(this).apply { orientation = LinearLayout.VERTICAL; setPadding(dp(20), dp(20), dp(20), dp(20)) }
        box.addView(TextView(this).apply { text = "Apex AI Assistant — быстрый голосовой и текстовый помощник.\n\nВы самостоятельно управляете разрешениями в настройках Android.\n\nСоздатель: Derek Stealth"; textSize = 14f; setPadding(0, 0, 0, dp(16)) })
        val chBtn = TextView(this).apply { text = "Открыть официальный Telegram-канал"; textSize = 15f; typeface = Typeface.DEFAULT_BOLD; gravity = Gravity.CENTER; setTextColor(Color.WHITE); setPadding(dp(16), dp(14), dp(16), dp(14)); background = GradientDrawable().apply { setColor(Color.parseColor("#0284C7")); cornerRadius = dp(12).toFloat() } }
        chBtn.setOnClickListener { startActivity(Intent(Intent.ACTION_VIEW, Uri.parse(ApexEngine.CHANNEL_URL))) }
        box.addView(chBtn)
        AlertDialog.Builder(this).setTitle("О приложении").setView(box).setPositiveButton("Закрыть", null).show()
    }

    private fun showInfoDialog(title: String, body: String) {
        AlertDialog.Builder(this).setTitle(title).setMessage(body).setPositiveButton("Закрыть", null).show()
    }

    override fun onDestroy() { tts?.shutdown(); speechRecognizer?.destroy(); super.onDestroy() }
}

class VectorNavIcon(ctx: Context, private val type: String) : View(ctx) {
    private val p = Paint(Paint.ANTI_ALIAS_FLAG).apply { style = Paint.Style.STROKE; strokeWidth = 3.5f; strokeCap = Paint.Cap.ROUND; strokeJoin = Paint.Join.ROUND; color = Color.WHITE }
    fun setTint(col: Int) { p.color = col; invalidate() }
    override fun onDraw(canvas: Canvas) {
        val w = width.toFloat(); val h = height.toFloat()
        when (type) {
            "new" -> { canvas.drawRoundRect(w * 0.15f, h * 0.15f, w * 0.85f, h * 0.85f, 6f, 6f, p); canvas.drawLine(w * 0.5f, h * 0.32f, w * 0.5f, h * 0.68f, p); canvas.drawLine(w * 0.32f, h * 0.5f, w * 0.68f, h * 0.5f, p) }
            "mic" -> { canvas.drawRoundRect(w * 0.36f, h * 0.14f, w * 0.64f, h * 0.58f, 10f, 10f, p); canvas.drawArc(w * 0.24f, h * 0.28f, w * 0.76f, h * 0.72f, 0f, 180f, false, p); canvas.drawLine(w * 0.5f, h * 0.72f, w * 0.5f, h * 0.88f, p) }
            "vol" -> { val path = Path().apply { moveTo(w * 0.18f, h * 0.38f); lineTo(w * 0.36f, h * 0.38f); lineTo(w * 0.58f, h * 0.20f); lineTo(w * 0.58f, h * 0.80f); lineTo(w * 0.36f, h * 0.62f); lineTo(w * 0.18f, h * 0.62f); close() }; canvas.drawPath(path, p); canvas.drawArc(w * 0.55f, h * 0.32f, w * 0.82f, h * 0.68f, -50f, 100f, false, p) }
            "perm" -> { val path = Path().apply { moveTo(w * 0.5f, h * 0.14f); lineTo(w * 0.82f, h * 0.28f); lineTo(w * 0.82f, h * 0.54f); quadTo(w * 0.82f, h * 0.78f, w * 0.5f, h * 0.88f); quadTo(w * 0.18f, h * 0.78f, w * 0.18f, h * 0.54f); lineTo(w * 0.18f, h * 0.28f); close() }; canvas.drawPath(path, p) }
            "cmd" -> { val path = Path().apply { moveTo(w * 0.56f, h * 0.14f); lineTo(w * 0.26f, h * 0.54f); lineTo(w * 0.50f, h * 0.54f); lineTo(w * 0.44f, h * 0.86f); lineTo(w * 0.74f, h * 0.46f); lineTo(w * 0.50f, h * 0.46f); close() }; canvas.drawPath(path, p) }
            "rate" -> { canvas.drawCircle(w * 0.5f, h * 0.5f, w * 0.36f, p); canvas.drawCircle(w * 0.5f, h * 0.5f, w * 0.12f, p) }
            "info" -> { canvas.drawCircle(w * 0.5f, h * 0.5f, w * 0.36f, p); canvas.drawLine(w * 0.5f, h * 0.46f, w * 0.5f, h * 0.68f, p); canvas.drawPoint(w * 0.5f, h * 0.32f, p) }
        }
    }

