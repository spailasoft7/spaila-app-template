#!/usr/bin/env python3
"""
Add feature switches in app.properties, app/build.gradle, and MainActivity.java.
Checks FIRST. Changes NOTHING if checks fail.
Run from repo root: python3 tools/add_feature_switches.py
"""
import sys

PROP   = "app.properties"
GRADLE = "app/build.gradle"
MAIN   = "app/src/main/java/com/spaila/webview/MainActivity.java"

with open(PROP,   encoding="utf-8") as f: prop   = f.read()
with open(GRADLE, encoding="utf-8") as f: gradle = f.read()
with open(MAIN,   encoding="utf-8") as f: main   = f.read()

checks = [
    (PROP,   "barColor line in app.properties", 'barColor='),
    (GRADLE, "BAR_COLOR field in build.gradle", 'buildConfigField "int", "BAR_COLOR"'),
    (MAIN,   "flashlight call in MainActivity", 'fn.equals("flashlight")'),
    (MAIN,   "startKeepAlive call in MainActivity", 'fn.equals("startKeepAlive")'),
    (MAIN,   "tts init in MainActivity", 'tts = new TextToSpeech(this, this);'),
]

all_ok = True
for fname, name, needle in checks:
    src = prop if fname == PROP else (gradle if fname == GRADLE else main)
    if needle in src:
        print(f"  OK   {name}")
    else:
        print(f"  FAIL {name}")
        all_ok = False

if not all_ok:
    print("\nAborted. Nothing was changed.")
    sys.exit(1)

print("\nAll checks passed. Applying changes...\n")

# 1. Update app.properties with feature flags
prop_add = """
# Feature switches (true = enabled, false = disabled)
feature.flashlight=true
feature.keepAlive=true
feature.tts=true
"""
if "feature.flashlight" not in prop:
    prop = prop.strip() + "\n" + prop_add
    with open(PROP, "w", encoding="utf-8") as f: f.write(prop)
    print("  Updated app.properties with feature switches")

# 2. Update app/build.gradle
gradle_fields = """        buildConfigField "int", "BAR_COLOR", "0xFF${cfg.barColor}"
        buildConfigField "boolean", "FEATURE_FLASHLIGHT", "${cfg.getProperty('feature.flashlight', 'true')}"
        buildConfigField "boolean", "FEATURE_KEEPALIVE", "${cfg.getProperty('feature.keepAlive', 'true')}"
        buildConfigField "boolean", "FEATURE_TTS", "${cfg.getProperty('feature.tts', 'true')}"
"""
gradle = gradle.replace('        buildConfigField "int", "BAR_COLOR", "0xFF${cfg.barColor}"\n', gradle_fields)
with open(GRADLE, "w", encoding="utf-8") as f: f.write(gradle)
print("  Updated app/build.gradle with BuildConfig fields")

# 3. Update MainActivity.java: guard TTS initialization
main = main.replace(
    "        setupSpailaBridge();\n        tts = new TextToSpeech(this, this);",
    "        setupSpailaBridge();\n        if (BuildConfig.FEATURE_TTS) { tts = new TextToSpeech(this, this); }"
)

# Guard flashlight
main = main.replace(
    '            } else if (fn.equals("flashlight")) {\n'
    '                setFlashlight(args.getBoolean(0), true);',
    '            } else if (fn.equals("flashlight")) {\n'
    '                if (BuildConfig.FEATURE_FLASHLIGHT) {\n'
    '                    setFlashlight(args.getBoolean(0), true);\n'
    '                } else {\n'
    '                    Toast.makeText(this, "Flashlight feature is disabled in this app", Toast.LENGTH_SHORT).show();\n'
    '                }'
)

# Guard startKeepAlive
main = main.replace(
    '            } else if (fn.equals("startKeepAlive")) {\n'
    '                final String kTitle = args.getString(0);\n'
    '                final String kText = args.getString(1);\n'
    '                withNotificationPermission(() -> startKeepAlive(kTitle, kText));',
    '            } else if (fn.equals("startKeepAlive")) {\n'
    '                if (BuildConfig.FEATURE_KEEPALIVE) {\n'
    '                    final String kTitle = args.getString(0);\n'
    '                    final String kText = args.getString(1);\n'
    '                    withNotificationPermission(() -> startKeepAlive(kTitle, kText));\n'
    '                } else {\n'
    '                    Toast.makeText(this, "Keep-alive service is disabled in this app", Toast.LENGTH_SHORT).show();\n'
    '                }'
)

with open(MAIN, "w", encoding="utf-8") as f: f.write(main)
print("  Updated MainActivity.java with feature guards")

print("\nDone. Feature switches successfully installed!")
