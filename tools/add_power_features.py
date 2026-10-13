#!/usr/bin/env python3
"""
Add TTS, Rich Haptics, and Device/Network Info.
Checks FIRST. Changes NOTHING if any check fails.
Run from repo root: python3 tools/add_power_features.py
"""
import sys

JAVA     = "app/src/main/java/com/spaila/webview/MainActivity.java"
JS       = "app/src/main/assets/www/spaila.js"
MANIFEST = "app/src/main/AndroidManifest.xml"

with open(JAVA,     encoding="utf-8") as f: java     = f.read()
with open(JS,       encoding="utf-8") as f: js       = f.read()
with open(MANIFEST, encoding="utf-8") as f: manifest = f.read()

checks = [
    (JAVA,     "getBatteryLevel case exists", 'fn.equals("getBatteryLevel")'),
    (JAVA,     "getBatteryLevel method exists", 'private void getBatteryLevel(int callId) {'),
    (JAVA,     "onDestroy exists", 'protected void onDestroy() {'),
    (JS,       "getBatteryLevel in JS", 'getBatteryLevel: function () {'),
    (MANIFEST, "INTERNET permission exists", 'android.permission.INTERNET'),
]

all_ok = True
for fname, name, needle in checks:
    src = java if fname == JAVA else (js if fname == JS else manifest)
    if needle in src:
        print(f"  OK   {name}")
    else:
        print(f"  FAIL {name}")
        all_ok = False

if not all_ok:
    print("\nAborted. Nothing was changed.")
    sys.exit(1)

print("\nAll checks passed. Applying changes...\n")

# 1. Manifest: add ACCESS_NETWORK_STATE
manifest = manifest.replace(
    '<uses-permission android:name="android.permission.INTERNET" />',
    '<uses-permission android:name="android.permission.INTERNET" />\n'
    '    <uses-permission android:name="android.permission.ACCESS_NETWORK_STATE" />'
)
print("  Manifest updated with ACCESS_NETWORK_STATE")

# 2. JS: add speak, stopSpeaking, haptic, getDeviceInfo
js = js.replace(
    '    getBatteryLevel: function () {\n'
    '      return sendAndWait("getBatteryLevel", []);\n'
    '    },',
    '    getBatteryLevel: function () {\n'
    '      return sendAndWait("getBatteryLevel", []);\n'
    '    },\n'
    '    // Speak text using the phone\'s built-in voice engine (offline)\n'
    '    speak: function (text, pitch, rate) {\n'
    '      send("speak", [String(text || ""), Number(pitch || 1.0), Number(rate || 1.0)]);\n'
    '    },\n'
    '    stopSpeaking: function () {\n'
    '      send("stopSpeaking", []);\n'
    '    },\n'
    '    // Precise tactile click: "click", "tick", "heavy", or "double"\n'
    '    haptic: function (style) {\n'
    '      send("haptic", [String(style || "click")]);\n'
    '    },\n'
    '    // Two-way: returns { osVersion, brand, model, appVersion, isOnline, networkType }\n'
    '    getDeviceInfo: function () {\n'
    '      return sendAndWait("getDeviceInfo", []);\n'
    '    },'
)
print("  spaila.js updated with speak, stopSpeaking, haptic, getDeviceInfo")

# 3. Java: imports
java_imports = """
import android.net.ConnectivityManager;
import android.net.NetworkCapabilities;
import android.speech.tts.TextToSpeech;
import android.view.HapticFeedbackConstants;
import java.util.Locale;
"""
java = java.replace(
    "import org.json.JSONArray;",
    java_imports + "import org.json.JSONArray;"
)

# 4. Java: field for TextToSpeech
java = java.replace(
    "public class MainActivity extends Activity {",
    "public class MainActivity extends Activity implements TextToSpeech.OnInitListener {\n"
    "    private TextToSpeech tts;\n"
    "    private boolean ttsReady = false;"
)

# 5. Java: init TTS in onCreate
java = java.replace(
    "        setupSpailaBridge();",
    "        setupSpailaBridge();\n        tts = new TextToSpeech(this, this);"
)

# 6. Java: handleMessage cases
java = java.replace(
    '            } else if (fn.equals("getBatteryLevel")) {\n'
    '                getBatteryLevel(callId);\n\n'
    '            }',
    '            } else if (fn.equals("getBatteryLevel")) {\n'
    '                getBatteryLevel(callId);\n\n'
    '            } else if (fn.equals("speak")) {\n'
    '                speakText(args.getString(0), (float) args.getDouble(1), (float) args.getDouble(2));\n\n'
    '            } else if (fn.equals("stopSpeaking")) {\n'
    '                if (tts != null) tts.stop();\n\n'
    '            } else if (fn.equals("haptic")) {\n'
    '                performHaptic(args.getString(0));\n\n'
    '            } else if (fn.equals("getDeviceInfo")) {\n'
    '                getDeviceInfo(callId);\n\n'
    '            }'
)

# 7. Java: cleanup in onDestroy
java = java.replace(
    "        if (splashHandler != null) splashHandler.removeCallbacks(splashRunnable);\n"
    "        setFlashlight(false, false);",
    "        if (splashHandler != null) splashHandler.removeCallbacks(splashRunnable);\n"
    "        setFlashlight(false, false);\n"
    "        if (tts != null) { tts.stop(); tts.shutdown(); }"
)

# 8. Java: implementation methods
methods = """
    @Override
    public void onInit(int status) {
        if (status == TextToSpeech.SUCCESS) {
            tts.setLanguage(Locale.getDefault());
            ttsReady = true;
        }
    }

    private void speakText(String text, float pitch, float rate) {
        if (!ttsReady || tts == null || text == null || text.isEmpty()) return;
        tts.setPitch(Math.max(0.1f, Math.min(pitch, 2.0f)));
        tts.setSpeechRate(Math.max(0.1f, Math.min(rate, 2.0f)));
        if (Build.VERSION.SDK_INT >= 21) {
            tts.speak(text, TextToSpeech.QUEUE_FLUSH, null, "spaila_tts");
        } else {
            tts.speak(text, TextToSpeech.QUEUE_FLUSH, null);
        }
    }

    private void performHaptic(String style) {
        if (webView == null) return;
        int feedback;
        switch (style) {
            case "heavy":
                feedback = HapticFeedbackConstants.LONG_PRESS;
                break;
            case "tick":
                if (Build.VERSION.SDK_INT >= 27) {
                    feedback = HapticFeedbackConstants.KEYBOARD_TAP;
                } else {
                    feedback = HapticFeedbackConstants.VIRTUAL_KEY;
                }
                break;
            case "double":
                vibrate(40);
                new Handler(Looper.getMainLooper()).postDelayed(() -> vibrate(40), 100);
                return;
            case "click":
            default:
                feedback = HapticFeedbackConstants.VIRTUAL_KEY;
                break;
        }
        webView.performHapticFeedback(feedback, HapticFeedbackConstants.FLAG_IGNORE_GLOBAL_SETTING);
    }

    private void getDeviceInfo(int callId) {
        try {
            JSONObject info = new JSONObject();
            info.put("osVersion", "Android " + Build.VERSION.RELEASE + " (API " + Build.VERSION.SDK_INT + ")");
            info.put("brand", Build.MANUFACTURER);
            info.put("model", Build.MODEL);
            info.put("appVersion", BuildConfig.VERSION_NAME);

            ConnectivityManager cm = (ConnectivityManager) getSystemService(Context.CONNECTIVITY_SERVICE);
            boolean isOnline = false;
            String netType = "offline";
            if (cm != null) {
                if (Build.VERSION.SDK_INT >= 23) {
                    android.net.Network network = cm.getActiveNetwork();
                    NetworkCapabilities caps = cm.getNetworkCapabilities(network);
                    if (caps != null) {
                        if (caps.hasTransport(NetworkCapabilities.TRANSPORT_WIFI)) {
                            isOnline = true;
                            netType = "wifi";
                        } else if (caps.hasTransport(NetworkCapabilities.TRANSPORT_CELLULAR)) {
                            isOnline = true;
                            netType = "cellular";
                        } else if (caps.hasCapability(NetworkCapabilities.NET_CAPABILITY_INTERNET)) {
                            isOnline = true;
                            netType = "other";
                        }
                    }
                } else {
                    android.net.NetworkInfo netInfo = cm.getActiveNetworkInfo();
                    if (netInfo != null && netInfo.isConnected()) {
                        isOnline = true;
                        netType = netInfo.getTypeName().toLowerCase();
                    }
                }
            }
            info.put("isOnline", isOnline);
            info.put("networkType", netType);

            reply(callId, info.toString());
        } catch (Exception e) {
            replyError(callId, "Failed to get device info: " + e.getMessage());
        }
    }
"""

java = java.replace(
    "    private void getBatteryLevel(int callId) {",
    methods + "\n    private void getBatteryLevel(int callId) {"
)

with open(MANIFEST, "w", encoding="utf-8") as f: f.write(manifest)
with open(JS,       "w", encoding="utf-8") as f: f.write(js)
with open(JAVA,     "w", encoding="utf-8") as f: f.write(java)

print("Done. Text-To-Speech, Rich Haptics, and Device/Network Info added!")
