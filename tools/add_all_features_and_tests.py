#!/usr/bin/env python3
"""
Adds Sound Effects, Brightness Control, WhatsApp, and Rate App.
Updates app-config.json, build.gradle, MainActivity.java, spaila.js,
and builds a complete, categorized features-test.html.
Checks FIRST. Changes NOTHING if checks fail.
Run from repo root: python3 tools/add_all_features_and_tests.py
"""
import sys, json

CONFIG = "app/src/main/assets/www/app-config.json"
GRADLE = "app/build.gradle"
MAIN   = "app/src/main/java/com/spaila/webview/MainActivity.java"
JS     = "app/src/main/assets/www/spaila.js"
TESTS  = "app/src/main/assets/www/features-test.html"

with open(CONFIG, encoding="utf-8") as f: config_str = f.read()
with open(GRADLE, encoding="utf-8") as f: gradle     = f.read()
with open(MAIN,   encoding="utf-8") as f: main       = f.read()
with open(JS,     encoding="utf-8") as f: js         = f.read()

checks = [
    (CONFIG, "app-config.json features key", '"features": {'),
    (GRADLE, "build.gradle FEATURE_TTS",     'FEATURE_TTS'),
    (MAIN,   "MainActivity updateWidget",    'fn.equals("updateWidget")'),
    (JS,     "spaila.js updateWidget",       'updateWidget: function'),
]

all_ok = True
for fname, name, needle in checks:
    src = config_str if fname == CONFIG else (gradle if fname == GRADLE else (main if fname == MAIN else js))
    if needle in src:
        print(f"  OK   {name}")
    else:
        print(f"  FAIL {name}")
        all_ok = False

if not all_ok:
    print("\nAborted. Nothing was changed.")
    sys.exit(1)

print("\nAll checks passed. Applying updates...\n")

# 1. Update app-config.json with all features
cfg = json.loads(config_str)
cfg["features"] = {
    "flashlight": True,
    "keepAlive": True,
    "tts": True,
    "sounds": True,
    "brightness": True,
    "whatsapp": True,
    "rateApp": True,
    "widgets": True
}
with open(CONFIG, "w", encoding="utf-8") as f:
    json.dump(cfg, f, indent=2)
print("  Updated app-config.json with all feature flags")

# 2. Update app/build.gradle with new BuildConfig fields
new_fields = """        buildConfigField "boolean", "FEATURE_TTS", "${getCfg('feature.tts', 'true')}"
        buildConfigField "boolean", "FEATURE_SOUNDS", "${getCfg('feature.sounds', 'true')}"
        buildConfigField "boolean", "FEATURE_BRIGHTNESS", "${getCfg('feature.brightness', 'true')}"
        buildConfigField "boolean", "FEATURE_WHATSAPP", "${getCfg('feature.whatsapp', 'true')}"
        buildConfigField "boolean", "FEATURE_RATE_APP", "${getCfg('feature.rateApp', 'true')}"
"""
gradle = gradle.replace('        buildConfigField "boolean", "FEATURE_TTS", "${getCfg(\'feature.tts\', \'true\')}"\n', new_fields)
with open(GRADLE, "w", encoding="utf-8") as f: f.write(gradle)
print("  Updated app/build.gradle with BuildConfig toggles")

# 3. Update MainActivity.java: add imports, cases, and methods
main_imports = """import android.media.AudioManager;
import android.media.ToneGenerator;
"""
main = main.replace("import android.speech.tts.TextToSpeech;", main_imports + "import android.speech.tts.TextToSpeech;")

# Bridge dispatcher cases
main_cases = """            } else if (fn.equals("updateWidget")) {
                updateWidgetData(args.getString(0), args.getString(1));

            } else if (fn.equals("playSound")) {
                if (BuildConfig.FEATURE_SOUNDS) {
                    playSystemSound(args.getString(0));
                }

            } else if (fn.equals("setBrightness")) {
                if (BuildConfig.FEATURE_BRIGHTNESS) {
                    setScreenBrightness((float) args.getDouble(0));
                }

            } else if (fn.equals("openWhatsApp")) {
                if (BuildConfig.FEATURE_WHATSAPP) {
                    openWhatsAppChat(args.getString(0), args.getString(1));
                }

            } else if (fn.equals("rateApp")) {
                if (BuildConfig.FEATURE_RATE_APP) {
                    openPlayStoreRating();
                }
"""
main = main.replace(
    '            } else if (fn.equals("updateWidget")) {\n                updateWidgetData(args.getString(0), args.getString(1));\n',
    main_cases
)

# Implementation methods
new_methods = """
    private void playSystemSound(String type) {
        try {
            ToneGenerator toneGen = new ToneGenerator(AudioManager.STREAM_NOTIFICATION, 80);
            switch (type) {
                case "beep":
                    toneGen.startTone(ToneGenerator.TONE_PROP_BEEP, 150);
                    break;
                case "success":
                    toneGen.startTone(ToneGenerator.TONE_PROP_ACK, 200);
                    break;
                case "alert":
                    toneGen.startTone(ToneGenerator.TONE_PROP_BEEP2, 300);
                    break;
                case "click":
                default:
                    toneGen.startTone(ToneGenerator.TONE_PROP_BEEP, 50);
                    break;
            }
        } catch (Exception ignored) {}
    }

    private void setScreenBrightness(float brightness) {
        runOnUiThread(() -> {
            try {
                WindowManager.LayoutParams lp = getWindow().getAttributes();
                if (brightness < 0) {
                    lp.screenBrightness = WindowManager.LayoutParams.BRIGHTNESS_OVERRIDE_NONE;
                } else {
                    lp.screenBrightness = Math.max(0.01f, Math.min(1.0f, brightness));
                }
                getWindow().setAttributes(lp);
            } catch (Exception ignored) {}
        });
    }

    private void openWhatsAppChat(String phone, String message) {
        try {
            String cleanPhone = phone.replaceAll("[^0-9]", "");
            String url = "https://api.whatsapp.com/send?phone=" + cleanPhone + "&text=" + Uri.encode(message);
            Intent intent = new Intent(Intent.ACTION_VIEW, Uri.parse(url));
            startActivity(intent);
        } catch (Exception e) {
            Toast.makeText(this, "Could not open WhatsApp", Toast.LENGTH_SHORT).show();
        }
    }

    private void openPlayStoreRating() {
        try {
            startActivity(new Intent(Intent.ACTION_VIEW, Uri.parse("market://details?id=" + getPackageName())));
        } catch (Exception e) {
            try {
                startActivity(new Intent(Intent.ACTION_VIEW, Uri.parse("https://play.google.com/store/apps/details?id=" + getPackageName())));
            } catch (Exception e2) {
                Toast.makeText(this, "Could not open Play Store", Toast.LENGTH_SHORT).show();
            }
        }
    }
"""

main = main.replace(
    "    private void updateWidgetData(String title, String text) {",
    new_methods + "\n    private void updateWidgetData(String title, String text) {"
)
with open(MAIN, "w", encoding="utf-8") as f: f.write(main)
print("  Updated MainActivity.java with new feature implementations")

# 4. Update spaila.js with new JS functions
new_js_funcs = """    // Updates the home screen widget card with title and text
    updateWidget: function (title, text) {
      send("updateWidget", [String(title || ""), String(text || "")]);
    },
    // Plays a zero-latency system tone: "click", "beep", "success", "alert"
    playSound: function (type) {
      send("playSound", [String(type || "click")]);
    },
    // Sets screen brightness: 0.0 (dimmest) to 1.0 (full brightness), or -1 for system default
    setBrightness: function (level) {
      send("setBrightness", [Number(level)]);
    },
    // Opens WhatsApp chat directly to phone number (e.g. "+27123456789") with pre-filled message
    openWhatsApp: function (phone, message) {
      send("openWhatsApp", [String(phone || ""), String(message || "")]);
    },
    // Opens Google Play Store to rate this app
    rateApp: function () {
      send("rateApp", []);
    },"""

js = js.replace(
    '    // Updates the home screen widget card with title and text\n    updateWidget: function (title, text) {\n      send("updateWidget", [String(title || ""), String(text || "")]);\n    },',
    new_js_funcs
)
with open(JS, "w", encoding="utf-8") as f: f.write(js)
print("  Updated spaila.js with new bridge methods")

# 5. Overwrite features-test.html with comprehensive test suite
with open(TESTS, "w", encoding="utf-8") as f:
    f.write("""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Spaila Native Feature Tests</title>
  <script src="spaila.js"></script>
  <style>
    * { box-sizing: border-box; }
    body {
      margin: 0;
      padding: 16px;
      background: #0A1F4C;
      color: #FFFFFF;
      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
      padding-bottom: 40px;
    }
    header {
      display: flex;
      align-items: center;
      justify-content: space-between;
      margin-bottom: 20px;
    }
    a.back {
      color: #9CC2FF;
      text-decoration: none;
      font-size: 16px;
      font-weight: bold;
    }
    h1 {
      font-size: 20px;
      margin: 0;
    }
    .section {
      background: rgba(255, 255, 255, 0.06);
      border: 1px solid rgba(255, 255, 255, 0.12);
      border-radius: 12px;
      padding: 14px;
      margin-bottom: 16px;
    }
    .section-title {
      font-size: 15px;
      font-weight: bold;
      color: #9CC2FF;
      margin-bottom: 10px;
      display: flex;
      align-items: center;
      gap: 6px;
    }
    button {
      display: block;
      width: 100%;
      margin: 8px 0;
      padding: 12px 14px;
      font-size: 15px;
      font-weight: 600;
      border: 0;
      border-radius: 10px;
      background: #1E3A8A;
      color: #FFFFFF;
      text-align: left;
    }
    button:active {
      background: #2563EB;
      transform: scale(0.99);
    }
    button.green {
      background: #166534;
      color: #DCFCE7;
    }
    button.amber {
      background: #854D0E;
      color: #FEF9C3;
    }
  </style>
</head>
<body>

  <header>
    <a href="index.html" class="back">← Back</a>
    <h1>Native Feature Suite</h1>
  </header>

  <!-- 1. NOTIFICATIONS & ALARMS -->
  <div class="section">
    <div class="section-title">📢 Notifications & Alarms</div>
    <button onclick="Spaila.toast('Toast message popped up!')">Toast Popup</button>
    <button onclick="Spaila.showNotification('Spaila App', 'Instant notification from JavaScript!')">Notify Now</button>
    <button onclick="Spaila.scheduleNotification(101, 'Spaila Alarm', '15 seconds elapsed!', 15); Spaila.toast('Alarm scheduled for +15s');">Schedule Alarm (+15 sec)</button>
    <button class="amber" onclick="Spaila.cancelScheduledNotification(101); Spaila.toast('Alarm 101 cancelled');">Cancel Alarm</button>
  </div>

  <!-- 2. BATTERY & DEVICE INFO (TWO-WAY) -->
  <div class="section">
    <div class="section-title">🔋 Battery & Device (Two-Way)</div>
    <button class="green" onclick="Spaila.getBatteryLevel().then(function(l){ Spaila.toast('Battery: ' + l + '%'); }).catch(function(e){ Spaila.toast('Err: ' + e.message); })">Get Battery Level</button>
    <button class="green" onclick="Spaila.getDeviceInfo().then(function(d){ alert(JSON.stringify(d, null, 2)); }).catch(function(e){ Spaila.toast('Err: ' + e.message); })">Get Device & Network Info</button>
    <button onclick="Spaila.openBatterySettings()">Open Battery Optimization Settings</button>
  </div>

  <!-- 3. VOICE & HAPTICS -->
  <div class="section">
    <div class="section-title">🗣️ Voice & Haptics</div>
    <button onclick="Spaila.speak('Welcome Given! Text to speech is working offline.', 1.0, 1.0)">Speak: Welcome Message</button>
    <button onclick="Spaila.stopSpeaking()">Stop Speaking</button>
    <button onclick="Spaila.haptic('click')">Haptic: Subtle Click</button>
    <button onclick="Spaila.haptic('tick')">Haptic: Tick</button>
    <button onclick="Spaila.haptic('heavy')">Haptic: Heavy Press</button>
    <button onclick="Spaila.haptic('double')">Haptic: Double Pulse</button>
    <button onclick="Spaila.vibrate(300)">Raw Vibrate (300ms)</button>
  </div>

  <!-- 4. SOUND EFFECTS -->
  <div class="section">
    <div class="section-title">🔊 Native Sound Effects (Zero-Lag)</div>
    <button onclick="Spaila.playSound('click')">Sound: Click</button>
    <button onclick="Spaila.playSound('beep')">Sound: Beep</button>
    <button onclick="Spaila.playSound('success')">Sound: Success</button>
    <button onclick="Spaila.playSound('alert')">Sound: Alert</button>
  </div>

  <!-- 5. SCREEN & HARDWARE -->
  <div class="section">
    <div class="section-title">📱 Screen, Brightness & Torch</div>
    <button onclick="Spaila.keepScreenOn(true); Spaila.toast('Screen will stay on')">Keep Screen On: ON</button>
    <button onclick="Spaila.keepScreenOn(false); Spaila.toast('Screen back to normal')">Keep Screen On: OFF</button>
    <button onclick="Spaila.setBrightness(0.1); Spaila.toast('Brightness: 10% (Dim)')">Brightness: 10% (Dim)</button>
    <button onclick="Spaila.setBrightness(1.0); Spaila.toast('Brightness: 100% (Max)')">Brightness: 100% (Max)</button>
    <button onclick="Spaila.setBrightness(-1); Spaila.toast('Brightness: System Auto')">Brightness: Auto/Default</button>
    <button onclick="Spaila.flashlight(true)">Flashlight: ON</button>
    <button onclick="Spaila.flashlight(false)">Flashlight: OFF</button>
  </div>

  <!-- 6. SYSTEM, CLIPBOARD & SHARE -->
  <div class="section">
    <div class="section-title">📋 Clipboard & Share</div>
    <button onclick="Spaila.copyToClipboard('Copied text from Spaila template!'); Spaila.toast('Copied to clipboard');">Copy Text</button>
    <button onclick="Spaila.share('Check out my new Android app built with Spaila Soft!')">Open Share Sheet</button>
  </div>

  <!-- 7. WIDGET & BACKGROUND -->
  <div class="section">
    <div class="section-title">🏃 Home Widget & Background</div>
    <button onclick="Spaila.updateWidget('Spaila Soft', 'Updated from JS at ' + new Date().toLocaleTimeString()); Spaila.toast('Home widget updated!');">Update Home Widget Text</button>
    <button onclick="Spaila.startKeepAlive('Spaila Running', 'Keeps timers going in background')">Start Keep-Alive Service</button>
    <button class="amber" onclick="Spaila.stopKeepAlive(); Spaila.toast('Keep-alive stopped');">Stop Keep-Alive Service</button>
  </div>

  <!-- 8. SOCIAL & APP STORE -->
  <div class="section">
    <div class="section-title">🌐 WhatsApp & Google Play</div>
    <button onclick="Spaila.openWhatsApp('+27000000000', 'Hello from my Spaila app!')">Open WhatsApp Chat</button>
    <button onclick="Spaila.rateApp()">Rate App on Google Play</button>
  </div>

  <script>
    // Handle physical Android back button to navigate to index.html
    window.onSpailaBack = function () {
      location.href = 'index.html';
      return true;
    };
  </script>
</body>
</html>
""")
print("  Generated complete features-test.html suite")

print("\nAll done! All features integrated and test suite generated.")
