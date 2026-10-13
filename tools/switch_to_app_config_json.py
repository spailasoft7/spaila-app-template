#!/usr/bin/env python3
"""
Switch master config to app/src/main/assets/www/app-config.json
Checks FIRST. Changes NOTHING if checks fail.
Run from repo root: python3 tools/switch_to_app_config_json.py
"""
import sys, os

GRADLE = "app/build.gradle"
SETUP  = "tools/setup-signing.sh"
JS     = "app/src/main/assets/www/spaila.js"
CONFIG = "app/src/main/assets/www/app-config.json"

with open(GRADLE, encoding="utf-8") as f: gradle = f.read()
with open(SETUP,  encoding="utf-8") as f: setup  = f.read()
with open(JS,     encoding="utf-8") as f: js     = f.read()

checks = [
    (GRADLE, "Properties loading code", "def cfg = new Properties()"),
    (SETUP,  "setup-signing.sh grep",   "APP_ID=$(grep '^appId=' app.properties"),
    (JS,     "window.Spaila declaration","window.Spaila = {"),
]

all_ok = True
for fname, name, needle in checks:
    src = gradle if fname == GRADLE else (setup if fname == SETUP else js)
    if needle in src:
        print(f"  OK   {name}")
    else:
        print(f"  FAIL {name}")
        all_ok = False

if not all_ok:
    print("\nAborted. Nothing was changed.")
    sys.exit(1)

print("\nAll checks passed. Applying changes...\n")

# 1. Create app-config.json
with open(CONFIG, "w", encoding="utf-8") as f:
    f.write("""{
  "appId": "com.spaila.newapp",
  "appName": "New App",
  "versionName": "1.0.0",
  "startPage": "index.html",
  "barColor": "0A1F4C",
  "features": {
    "flashlight": true,
    "keepAlive": true,
    "tts": true
  }
}
""")
print("  Created app/src/main/assets/www/app-config.json")

# 2. Update app/build.gradle to read JSON with fallback
old_gradle_cfg = """// Read this app's settings from app.properties (in the repo root)
def cfg = new Properties()
file("../app.properties").withInputStream { cfg.load(it) }"""

new_gradle_cfg = """import groovy.json.JsonSlurper

// Read app settings from app-config.json (inside www assets)
def configFile = file("src/main/assets/www/app-config.json")
def cfgJson = configFile.exists() ? new JsonSlurper().parse(configFile) : null

def legacyProp = new Properties()
def propFile = file("../app.properties")
if (propFile.exists()) {
    propFile.withInputStream { legacyProp.load(it) }
}

def getCfg = { key, defaultVal ->
    if (cfgJson != null) {
        if (key.startsWith("feature.")) {
            def featName = key.substring(8)
            return (cfgJson.features != null && cfgJson.features[featName] != null) ? cfgJson.features[featName].toString() : defaultVal
        }
        return cfgJson[key] != null ? cfgJson[key].toString() : defaultVal
    }
    return legacyProp.getProperty(key, defaultVal)
}"""

gradle = gradle.replace(old_gradle_cfg, new_gradle_cfg)

gradle = gradle.replace('applicationId cfg.appId', 'applicationId getCfg("appId", "com.spaila.newapp")')
gradle = gradle.replace('versionName cfg.versionName', 'versionName getCfg("versionName", "1.0.0")')
gradle = gradle.replace('buildConfigField "String", "START_PAGE", "\\"${cfg.startPage}\\""', 'buildConfigField "String", "START_PAGE", "\\"${getCfg(\'startPage\', \'index.html\')}\\""')
gradle = gradle.replace('buildConfigField "int", "BAR_COLOR", "0xFF${cfg.barColor}"', 'buildConfigField "int", "BAR_COLOR", "0xFF${getCfg(\'barColor\', \'0A1F4C\')}"')
gradle = gradle.replace('buildConfigField "boolean", "FEATURE_FLASHLIGHT", "${cfg.getProperty(\'feature.flashlight\', \'true\')}"', 'buildConfigField "boolean", "FEATURE_FLASHLIGHT", "${getCfg(\'feature.flashlight\', \'true\')}"')
gradle = gradle.replace('buildConfigField "boolean", "FEATURE_KEEPALIVE", "${cfg.getProperty(\'feature.keepAlive\', \'true\')}"', 'buildConfigField "boolean", "FEATURE_KEEPALIVE", "${getCfg(\'feature.keepAlive\', \'true\')}"')
gradle = gradle.replace('buildConfigField "boolean", "FEATURE_TTS", "${cfg.getProperty(\'feature.tts\', \'true\')}"', 'buildConfigField "boolean", "FEATURE_TTS", "${getCfg(\'feature.tts\', \'true\')}"')
gradle = gradle.replace('resValue "string", "app_name", cfg.appName', 'resValue "string", "app_name", getCfg("appName", "New App")')
gradle = gradle.replace('resValue "color", "icon_background", "#${cfg.barColor}"', 'resValue "color", "icon_background", "#${getCfg(\'barColor\', \'0A1F4C\')}"')

with open(GRADLE, "w", encoding="utf-8") as f: f.write(gradle)
print("  Updated app/build.gradle to parse JSON")

# 3. Update tools/setup-signing.sh
old_setup = """APP_ID=$(grep '^appId=' app.properties | cut -d= -f2)
[ "$APP_ID" = "com.spaila.newapp" ] && { echo "STOP: edit app.properties first (the app ID is still the placeholder)"; exit 1; }"""

new_setup = """if [ -f "app/src/main/assets/www/app-config.json" ]; then
  APP_ID=$(python3 -c "import json; print(json.load(open('app/src/main/assets/www/app-config.json')).get('appId',''))")
else
  APP_ID=$(grep '^appId=' app.properties | cut -d= -f2)
fi
[ "$APP_ID" = "com.spaila.newapp" ] && { echo "STOP: edit app-config.json first (the appId is still the placeholder)"; exit 1; }"""

setup = setup.replace(old_setup, new_setup)
with open(SETUP, "w", encoding="utf-8") as f: f.write(setup)
print("  Updated tools/setup-signing.sh")

# 4. In spaila.js: load app-config.json on startup
js = js.replace(
    "  window.Spaila = {",
    "  // Load local config asynchronously\n"
    "  var _config = {};\n"
    "  try {\n"
    "    fetch('app-config.json').then(function(r){return r.json();}).then(function(c){\n"
    "      _config = c;\n"
    "      window.Spaila.config = c;\n"
    "    }).catch(function(){});\n"
    "  } catch(e) {}\n\n"
    "  window.Spaila = {\n"
    "    config: _config,"
)
with open(JS, "w", encoding="utf-8") as f: f.write(js)
print("  Updated spaila.js with Spaila.config")

print("\nDone. Option B is complete: app-config.json is now the master config!")
