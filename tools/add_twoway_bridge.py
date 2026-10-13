#!/usr/bin/env python3
"""
Add two-way bridge to spaila.js and MainActivity.java.
Checks FIRST. Changes NOTHING if any check fails.
Run from repo root: python3 tools/add_twoway_bridge.py
"""
import sys

JAVA = "app/src/main/java/com/spaila/webview/MainActivity.java"
JS   = "app/src/main/assets/www/spaila.js"

with open(JAVA, "r", encoding="utf-8") as f: java = f.read()
with open(JS,   "r", encoding="utf-8") as f: js   = f.read()

checks = [
    (JAVA, "Java: optJSONArray already applied", 'if (args == null) args = new JSONArray();'),
    (JAVA, "Java: stopKeepAlive case exists",    'fn.equals("stopKeepAlive")'),
    (JAVA, "Java: org.json imports",             "import org.json.JSONArray;"),
    (JAVA, "Java: Notification section marker",  "// ---------- Notification permission ----------"),
    (JS,   "JS: send() function",                "function send(fn, args) {"),
    (JS,   "JS: window.Spaila object",           "window.Spaila = {"),
    (JS,   "JS: stopKeepAlive in Spaila",        'send("stopKeepAlive", []);'),
]

all_ok = True
for fname, name, needle in checks:
    src = java if fname == JAVA else js
    if needle in src:
        print(f"  OK   {name}")
    else:
        print(f"  FAIL {name}")
        all_ok = False

if not all_ok:
    print("\nAborted. Nothing was changed.")
    sys.exit(1)

print("\nAll checks passed. Applying changes...\n")

# ── spaila.js ──────────────────────────────────────────────────────────────

# JS-1: add _callbacks map and _nextId counter
js = js.replace(
    "(function () {\n"
    "  function send(fn, args) {",
    "(function () {\n"
    "  var _callbacks = {};  // id -> {resolve, reject} for waiting two-way calls\n"
    "  var _nextId = 1;      // increases by 1 for each new call\n"
    "\n"
    "  function send(fn, args) {",
)
print("  JS-1: added _callbacks and _nextId")

# JS-2: add sendAndWait() just before window.Spaila
js = js.replace(
    "  window.Spaila = {",
    "  // Like send(), but returns a Promise. Android will call _handleReply with the result.\n"
    "  function sendAndWait(fn, args) {\n"
    "    return new Promise(function (resolve, reject) {\n"
    "      if (!window.SpailaNative) {\n"
    '        reject(new Error("Not running inside the Android app"));\n'
    "        return;\n"
    "      }\n"
    "      var id = _nextId++;\n"
    "      _callbacks[id] = { resolve: resolve, reject: reject };\n"
    "      window.SpailaNative.postMessage(JSON.stringify({ fn: fn, args: args, id: id }));\n"
    "    });\n"
    "  }\n"
    "\n"
    "  window.Spaila = {",
)
print("  JS-2: added sendAndWait()")

# JS-3: add getBatteryLevel() and _handleReply() at the end of window.Spaila
js = js.replace(
    "    stopKeepAlive: function () {\n"
    '      send("stopKeepAlive", []);\n'
    "    }\n"
    "  };",
    "    stopKeepAlive: function () {\n"
    '      send("stopKeepAlive", []);\n'
    "    },\n"
    "    // Two-way: returns a Promise that resolves with battery level 0-100 (or -1).\n"
    "    getBatteryLevel: function () {\n"
    "      return sendAndWait(\"getBatteryLevel\", []);\n"
    "    },\n"
    "    // Android calls this to deliver a reply. Do not call this yourself.\n"
    "    _handleReply: function (id, result, error) {\n"
    "      var cb = _callbacks[id];\n"
    "      if (!cb) return;\n"
    "      delete _callbacks[id];\n"
    "      if (error != null) { cb.reject(new Error(error)); }\n"
    "      else { cb.resolve(result); }\n"
    "    }\n"
    "  };",
)
print("  JS-3: added getBatteryLevel() and _handleReply()")

# ── MainActivity.java ──────────────────────────────────────────────────────

# Java-1: add two imports alongside org.json ones
java = java.replace(
    "import org.json.JSONArray;\n"
    "import org.json.JSONObject;",
    "import android.content.IntentFilter;\n"
    "import android.os.BatteryManager;\n"
    "\n"
    "import org.json.JSONArray;\n"
    "import org.json.JSONObject;",
)
print("  Java-1: added IntentFilter and BatteryManager imports")

# Java-2: extract callId in handleMessage (right after the args null-check)
java = java.replace(
    "            if (args == null) args = new JSONArray();\n"
    "\n"
    '            if (fn.equals("toast")) {',
    "            if (args == null) args = new JSONArray();\n"
    "            int callId = json.optInt(\"id\", -1); // -1 = no reply expected\n"
    "\n"
    '            if (fn.equals("toast")) {',
)
print("  Java-2: added callId extraction in handleMessage")

# Java-3: add getBatteryLevel case in the if-else chain
java = java.replace(
    '            } else if (fn.equals("stopKeepAlive")) {\n'
    "                stopKeepAlive();\n"
    "\n"
    "            }",
    '            } else if (fn.equals("stopKeepAlive")) {\n'
    "                stopKeepAlive();\n"
    "\n"
    '            } else if (fn.equals("getBatteryLevel")) {\n'
    "                getBatteryLevel(callId);\n"
    "\n"
    "            }",
)
print("  Java-3: added getBatteryLevel case")

# Java-4: add reply helpers + getBatteryLevel method before Notification section
java = java.replace(
    "    // ---------- Notification permission ----------",
    "    // ---------- Two-way bridge ----------\n"
    "\n"
    "    // Sends a result back to JS. The Promise in the web page will resolve.\n"
    "    private void reply(int callId, String jsonValue) {\n"
    "        if (callId < 0 || webView == null) return;\n"
    "        final String js = \"window.Spaila._handleReply(\" + callId + \",\" + jsonValue + \",null)\";\n"
    "        runOnUiThread(() -> webView.evaluateJavascript(js, null));\n"
    "    }\n"
    "\n"
    "    private void replyError(int callId, String errorMessage) {\n"
    "        if (callId < 0 || webView == null) return;\n"
    "        final String js = \"window.Spaila._handleReply(\" + callId + \",null,\"\n"
    "                + JSONObject.quote(errorMessage) + \")\";\n"
    "        runOnUiThread(() -> webView.evaluateJavascript(js, null));\n"
    "    }\n"
    "\n"
    "    private void getBatteryLevel(int callId) {\n"
    "        try {\n"
    "            IntentFilter ifilter = new IntentFilter(Intent.ACTION_BATTERY_CHANGED);\n"
    "            Intent batteryStatus = registerReceiver(null, ifilter);\n"
    "            int level = batteryStatus != null\n"
    "                    ? batteryStatus.getIntExtra(BatteryManager.EXTRA_LEVEL, -1) : -1;\n"
    "            int scale = batteryStatus != null\n"
    "                    ? batteryStatus.getIntExtra(BatteryManager.EXTRA_SCALE, -1) : -1;\n"
    "            int percent = (level >= 0 && scale > 0)\n"
    "                    ? Math.round(level * 100f / scale) : -1;\n"
    "            reply(callId, String.valueOf(percent));\n"
    "        } catch (Exception e) {\n"
    "            replyError(callId, \"Could not read battery level\");\n"
    "        }\n"
    "    }\n"
    "\n"
    "    // ---------- Notification permission ----------",
)
print("  Java-4: added reply(), replyError(), getBatteryLevel()")

with open(JS,   "w", encoding="utf-8") as f: f.write(js)
with open(JAVA, "w", encoding="utf-8") as f: f.write(java)

print(f"\nDone. Two files updated.")
print("Now: commit, push, build, and test in the APK.")
