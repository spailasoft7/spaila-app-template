#!/usr/bin/env python3
"""
Adds Dynamic Widget barColor, Biometrics, Speech-To-Text, and Share Target.
Checks FIRST. Changes NOTHING if checks fail.
Run from repo root: python3 tools/add_advanced_suite.py
"""
import sys, json

GRADLE   = "app/build.gradle"
MANIFEST = "app/src/main/AndroidManifest.xml"
MAIN     = "app/src/main/java/com/spaila/webview/MainActivity.java"
JS       = "app/src/main/assets/www/spaila.js"
CONFIG   = "app/src/main/assets/www/app-config.json"
TESTS    = "app/src/main/assets/www/features-test.html"
WIDGET_BG= "app/src/main/res/drawable/widget_bg.xml"

with open(GRADLE,   encoding="utf-8") as f: gradle   = f.read()
with open(MANIFEST, encoding="utf-8") as f: manifest = f.read()
with open(MAIN,     encoding="utf-8") as f: main     = f.read()
with open(JS,       encoding="utf-8") as f: js       = f.read()
with open(CONFIG,   encoding="utf-8") as f: cfg_str  = f.read()
with open(TESTS,    encoding="utf-8") as f: tests    = f.read()

checks = [
    (GRADLE,   "dependencies block", "implementation 'androidx.webkit:webkit:1.12.1'"),
    (MANIFEST, "MainActivity tag",   'android:name=".MainActivity"'),
    (MAIN,     "MainActivity class", "public class MainActivity extends Activity"),
    (JS,       "rateApp function",   "rateApp: function"),
    (CONFIG,   "features key",       '"features": {'),
]

all_ok = True
for fname, name, needle in checks:
    src = gradle if fname == GRADLE else (manifest if fname == MANIFEST else (main if fname == MAIN else (js if fname == JS else cfg_str)))
    if needle in src:
        print(f"  OK   {name}")
    else:
        print(f"  FAIL {name}")
        all_ok = False

if not all_ok:
    print("\nAborted. Nothing was changed.")
    sys.exit(1)

print("\nAll checks passed. Applying updates...\n")

# 1. Update widget_bg.xml to use @color/icon_background
with open(WIDGET_BG, "w", encoding="utf-8") as f:
    f.write("""<?xml version="1.0" encoding="utf-8"?>
<shape xmlns:android="http://schemas.android.com/apk/res/android"
    android:shape="rectangle">
    <solid android:color="@color/icon_background" />
    <corners android:radius="20dp" />
    <stroke
        android:width="1.5dp"
        android:color="#475569" />
    <padding
        android:left="16dp"
        android:top="16dp"
        android:right="16dp"
        android:bottom="16dp" />
</shape>
""")
print("  Widget background bound to app barColor")

# 2. Update app-config.json
cfg = json.loads(cfg_str)
cfg["features"]["biometrics"] = True
cfg["features"]["speechToText"] = True
with open(CONFIG, "w", encoding="utf-8") as f:
    json.dump(cfg, f, indent=2)
print("  Updated app-config.json with biometrics and speechToText toggles")

# 3. Update app/build.gradle: dependencies & BuildConfig fields
gradle = gradle.replace(
    "implementation 'androidx.webkit:webkit:1.12.1'",
    "implementation 'androidx.webkit:webkit:1.12.1'\n"
    "    implementation 'androidx.biometric:biometric:1.1.0'\n"
    "    implementation 'androidx.fragment:fragment:1.8.5'"
)

gradle = gradle.replace(
    '        buildConfigField "boolean", "FEATURE_RATE_APP", "${getCfg(\'feature.rateApp\', \'true\')}"\n',
    '        buildConfigField "boolean", "FEATURE_RATE_APP", "${getCfg(\'feature.rateApp\', \'true\')}"\n'
    '        buildConfigField "boolean", "FEATURE_BIOMETRICS", "${getCfg(\'feature.biometrics\', \'true\')}"\n'
    '        buildConfigField "boolean", "FEATURE_SPEECH_TO_TEXT", "${getCfg(\'feature.speechToText\', \'true\')}"\n'
)
with open(GRADLE, "w", encoding="utf-8") as f: f.write(gradle)
print("  Updated app/build.gradle with biometric dependencies")

# 4. Update AndroidManifest.xml: add receive share intent filter & biometric permission
manifest = manifest.replace(
    '<manifest xmlns:android="http://schemas.android.com/apk/res/android">',
    '<manifest xmlns:android="http://schemas.android.com/apk/res/android">\n'
    '    <uses-permission android:name="android.permission.USE_BIOMETRIC" />'
)

share_filter = """            <intent-filter>
                <action android:name="android.intent.action.SEND" />
                <category android:name="android.intent.category.DEFAULT" />
                <data android:mimeType="text/plain" />
            </intent-filter>
        </activity>"""
manifest = manifest.replace("        </activity>", share_filter)
with open(MANIFEST, "w", encoding="utf-8") as f: f.write(manifest)
print("  Updated AndroidManifest.xml with Share receiver & Biometric permission")

# 5. Update MainActivity.java
# Switch Activity to FragmentActivity
main = main.replace("import android.app.Activity;", "import androidx.fragment.app.FragmentActivity;")
main = main.replace("public class MainActivity extends Activity", "public class MainActivity extends FragmentActivity")

# Add imports
bio_imports = """
import androidx.biometric.BiometricManager;
import androidx.biometric.BiometricPrompt;
import androidx.core.content.ContextCompat;
import android.speech.RecognizerIntent;
import java.util.concurrent.Executor;
"""
main = main.replace("import android.media.ToneGenerator;", "import android.media.ToneGenerator;" + bio_imports)

# Add member variable for pending speech callback
main = main.replace(
    "    private boolean pageReady = false;",
    "    private boolean pageReady = false;\n    private int pendingSpeechCallId = -1;"
)

# Handle incoming shared text in onCreate
shared_text_handling = """
        setupSpailaBridge();
        handleIncomingShare(getIntent());
"""
main = main.replace("        setupSpailaBridge();", shared_text_handling)

# Bridge dispatcher cases
extra_cases = """            } else if (fn.equals("rateApp")) {
                if (BuildConfig.FEATURE_RATE_APP) {
                    openPlayStoreRating();
                }

            } else if (fn.equals("authenticate")) {
                if (BuildConfig.FEATURE_BIOMETRICS) {
                    authenticateBiometric(callId, args.optString(0, "Authenticate"));
                } else {
                    replyError(callId, "Biometrics feature is disabled");
                }

            } else if (fn.equals("startSpeechRecognition")) {
                if (BuildConfig.FEATURE_SPEECH_TO_TEXT) {
                    startSpeechToText(callId, args.optString(0, "Speak now..."));
                } else {
                    replyError(callId, "Speech-to-text is disabled");
                }
"""
main = main.replace(
    '            } else if (fn.equals("rateApp")) {\n                if (BuildConfig.FEATURE_RATE_APP) {\n                    openPlayStoreRating();\n                }\n',
    extra_cases
)

# Implementation methods
advanced_methods = """
    private void handleIncomingShare(Intent intent) {
        if (intent != null && Intent.ACTION_SEND.equals(intent.getAction()) && "text/plain".equals(intent.getType())) {
            String sharedText = intent.getStringExtra(Intent.EXTRA_TEXT);
            if (sharedText != null && !sharedText.isEmpty()) {
                new Handler(Looper.getMainLooper()).postDelayed(() -> {
                    if (webView != null) {
                        String js = "if(window.onSpailaSharedText) window.onSpailaSharedText(" + JSONObject.quote(sharedText) + ");";
                        webView.evaluateJavascript(js, null);
                    }
                }, 1000);
            }
        }
    }

    private void authenticateBiometric(int callId, String promptText) {
        runOnUiThread(() -> {
            try {
                BiometricManager manager = BiometricManager.from(this);
                int canAuth = manager.canAuthenticate(BiometricManager.Authenticators.BIOMETRIC_WEAK | BiometricManager.Authenticators.DEVICE_CREDENTIAL);
                if (canAuth != BiometricManager.BIOMETRIC_SUCCESS) {
                    reply(callId, "false");
                    return;
                }

                Executor executor = ContextCompat.getMainExecutor(this);
                BiometricPrompt prompt = new BiometricPrompt(this, executor, new BiometricPrompt.AuthenticationCallback() {
                    @Override
                    public void onAuthenticationSucceeded(BiometricPrompt.AuthenticationResult result) {
                        reply(callId, "true");
                    }
                    @Override
                    public void onAuthenticationError(int errorCode, CharSequence errString) {
                        reply(callId, "false");
                    }
                    @Override
                    public void onAuthenticationFailed() {
                        // Keep trying or cancel
                    }
                });

                BiometricPrompt.PromptInfo info = new BiometricPrompt.PromptInfo.Builder()
                        .setTitle(promptText)
                        .setAllowedAuthenticators(BiometricManager.Authenticators.BIOMETRIC_WEAK | BiometricManager.Authenticators.DEVICE_CREDENTIAL)
                        .build();

                prompt.authenticate(info);
            } catch (Exception e) {
                replyError(callId, "Biometric error: " + e.getMessage());
            }
        });
    }

    private void startSpeechToText(int callId, String prompt) {
        try {
            Intent intent = new Intent(RecognizerIntent.ACTION_RECOGNIZE_SPEECH);
            intent.putExtra(RecognizerIntent.EXTRA_LANGUAGE_MODEL, RecognizerIntent.LANGUAGE_MODEL_FREE_FORM);
            intent.putExtra(RecognizerIntent.EXTRA_PROMPT, prompt);
            pendingSpeechCallId = callId;
            startActivityForResult(intent, 2002);
        } catch (Exception e) {
            replyError(callId, "Speech recognition not available: " + e.getMessage());
        }
    }

    @Override
    protected void onActivityResult(int requestCode, int resultCode, Intent data) {
        super.onActivityResult(requestCode, resultCode, data);
        if (requestCode == 2002 && pendingSpeechCallId != -1) {
            if (resultCode == RESULT_OK && data != null) {
                ArrayList<String> matches = data.getStringArrayListExtra(RecognizerIntent.EXTRA_RESULTS);
                if (matches != null && !matches.isEmpty()) {
                    reply(pendingSpeechCallId, JSONObject.quote(matches.get(0)));
                } else {
                    reply(pendingSpeechCallId, JSONObject.quote(""));
                }
            } else {
                replyError(pendingSpeechCallId, "Cancelled or no speech detected");
            }
            pendingSpeechCallId = -1;
        }
    }
"""

main = main.replace(
    "    private void openPlayStoreRating() {",
    advanced_methods + "\n    private void openPlayStoreRating() {"
)

# Also handle share in onNewIntent
main = main.replace(
    "        if (targetPage != null && !targetPage.isEmpty() && webView != null) {",
    "        handleIncomingShare(intent);\n        if (targetPage != null && !targetPage.isEmpty() && webView != null) {"
)

with open(MAIN, "w", encoding="utf-8") as f: f.write(main)
print("  Updated MainActivity.java with Biometrics, Speech-To-Text, and Share handler")

# 6. Update spaila.js with new JS functions
new_js_methods = """    // Authenticates using Fingerprint, Face, or Phone PIN. Returns Promise<boolean>
    authenticate: function (prompt) {
      return sendAndWait("authenticate", [String(prompt || "Verify your identity")]);
    },
    // Opens voice recognition dialog and returns recognized spoken text as a Promise<string>
    startSpeechRecognition: function (prompt) {
      return sendAndWait("startSpeechRecognition", [String(prompt || "Speak now...")]);
    },
    // Opens Google Play Store to rate this app
    rateApp: function () {"""

js = js.replace(
    '    // Opens Google Play Store to rate this app\n    rateApp: function () {',
    new_js_methods
)
with open(JS, "w", encoding="utf-8") as f: f.write(js)
print("  Updated spaila.js with authenticate and startSpeechRecognition")

# 7. Add buttons in features-test.html
new_test_sections = """  <!-- 9. SECURITY & VOICE INPUT -->
  <div class="section">
    <div class="section-title">🔐 Biometrics & Voice Input (Two-Way)</div>
    <button class="green" onclick="Spaila.authenticate('Unlock Spaila Test').then(function(ok){ Spaila.toast(ok ? 'Authenticated successfully!' : 'Auth failed or cancelled'); }).catch(function(e){ Spaila.toast('Err: ' + e.message); })">Biometric / Fingerprint Unlock</button>
    <button class="green" onclick="Spaila.startSpeechRecognition('Say something...').then(function(text){ alert('You said: ' + text); }).catch(function(e){ Spaila.toast('Err: ' + e.message); })">Speech-To-Text (Voice Dictation)</button>
  </div>

  <script>
    // Called automatically if someone shares text to this app from another app!
    window.onSpailaSharedText = function (text) {
      alert('Received shared text:\\n' + text);
    };
"""
tests = tests.replace("  <script>\n    // Handle physical Android back button", new_test_sections + "    // Handle physical Android back button")
with open(TESTS, "w", encoding="utf-8") as f: f.write(tests)
print("  Updated features-test.html with Biometrics, Speech Recognition & Share Handler")

print("\nDone! Dynamic widget color, Biometrics, Speech-To-Text, and Share receiver added!")
