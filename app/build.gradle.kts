plugins {
    id("com.android.application")
    id("org.jetbrains.kotlin.android")
}
android {
    namespace = "com.apex.assistant"
    compileSdk = 34
    defaultConfig {
        applicationId = "com.apex.assistant"
        minSdk = 26
        targetSdk = 34
        versionCode = 1
        versionName = "4.0"
        val tgTok = System.getenv("TG_BOT_TOKEN") ?: ""
        buildConfigField("String", "TG_BOT_TOKEN", "\"$tgTok\"")
    }
    buildFeatures { buildConfig = true }
    compileOptions {
        sourceCompatibility = JavaVersion.VERSION_17
        targetCompatibility = JavaVersion.VERSION_17
    }
    kotlinOptions { jvmTarget = "17" }
}
dependencies {
    implementation("androidx.core:core-ktx:1.12.0")
    implementation("androidx.appcompat:appcompat:1.6.1")
}
