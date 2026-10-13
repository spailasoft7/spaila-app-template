#!/usr/bin/env python3
"""
Add launcher shortcuts to the template.
Checks FIRST. Changes NOTHING if checks fail.
Run from repo root: python3 tools/add_shortcuts.py
"""
import sys, os

MANIFEST = "app/src/main/AndroidManifest.xml"
STRINGS  = "app/src/main/res/values/strings.xml"
MAIN     = "app/src/main/java/com/spaila/webview/MainActivity.java"
XML_DIR  = "app/src/main/res/xml"
DRAW_DIR = "app/src/main/res/drawable"
SHORTCUTS_XML = f"{XML_DIR}/shortcuts.xml"
ICON_XML      = f"{DRAW_DIR}/ic_shortcut_star.xml"

with open(MANIFEST, encoding="utf-8") as f: manifest = f.read()
with open(STRINGS,  encoding="utf-8") as f: strings  = f.read()
with open(MAIN,     encoding="utf-8") as f: main     = f.read()

checks = [
    (MANIFEST, "MainActivity tag exists", 'android:name=".MainActivity"'),
    (STRINGS,  "strings resources tag",   '<resources>'),
    (MAIN,     "webView.loadUrl exists",  'webView.loadUrl(ORIGIN + "/assets/www/" + START_PAGE);'),
]

all_ok = True
for fname, name, needle in checks:
    src = manifest if fname == MANIFEST else (strings if fname == STRINGS else main)
    if needle in src:
        print(f"  OK   {name}")
    else:
        print(f"  FAIL {name}")
        all_ok = False

if not all_ok:
    print("\nAborted. Nothing changed.")
    sys.exit(1)

print("\nAll checks passed. Applying changes...\n")

os.makedirs(XML_DIR, exist_ok=True)
os.makedirs(DRAW_DIR, exist_ok=True)

# 1. Create a clean vector star icon for shortcuts
with open(ICON_XML, "w", encoding="utf-8") as f:
    f.write("""<vector xmlns:android="http://schemas.android.com/apk/res/android"
    android:width="24dp"
    android:height="24dp"
    android:viewportWidth="24"
    android:viewportHeight="24">
    <path
        android:fillColor="#FFFFFFFF"
        android:pathData="M12,17.27L18.18,21l-1.64,-7.03L22,9.24l-7.19,-0.61L12,2 9.19,8.63 2,9.24l5.46,4.73L5.82,21z"/>
</vector>
""")
print("  Created ic_shortcut_star.xml")

# 2. Create res/xml/shortcuts.xml
with open(SHORTCUTS_XML, "w", encoding="utf-8") as f:
    f.write("""<?xml version="1.0" encoding="utf-8"?>
<shortcuts xmlns:android="http://schemas.android.com/apk/res/android">
    <shortcut
        android:shortcutId="features_test"
        android:enabled="true"
        android:icon="@drawable/ic_shortcut_star"
        android:shortcutShortLabel="@string/shortcut_features_short"
        android:shortcutLongLabel="@string/shortcut_features_long">
        <intent
            android:action="android.intent.action.VIEW"
            android:targetPackage="com.spaila.newapp"
            android:targetClass="com.spaila.webview.MainActivity">
            <extra android:name="target_page" android:value="features-test.html" />
        </intent>
        <categories android:name="android.shortcut.conversation" />
    </shortcut>
</shortcuts>
""")
print("  Created shortcuts.xml")

# 3. Add string labels into strings.xml
strings = strings.replace(
    "</resources>",
    '    <string name="shortcut_features_short">Features</string>\n'
    '    <string name="shortcut_features_long">Feature Tests</string>\n'
    '</resources>'
)
with open(STRINGS, "w", encoding="utf-8") as f: f.write(strings)
print("  Updated strings.xml")

# 4. Add shortcut metadata to AndroidManifest.xml
manifest = manifest.replace(
    '            <intent-filter>\n'
    '                <action android:name="android.intent.action.MAIN" />\n'
    '                <category android:name="android.intent.category.LAUNCHER" />\n'
    '            </intent-filter>\n'
    '        </activity>',
    '            <intent-filter>\n'
    '                <action android:name="android.intent.action.MAIN" />\n'
    '                <category android:name="android.intent.category.LAUNCHER" />\n'
    '            </intent-filter>\n'
    '            <meta-data\n'
    '                android:name="android.app.shortcuts"\n'
    '                android:resource="@xml/shortcuts" />\n'
    '        </activity>'
)
with open(MANIFEST, "w", encoding="utf-8") as f: f.write(manifest)
print("  Updated AndroidManifest.xml")

# 5. Update MainActivity.java to load target_page from intent
main = main.replace(
    '        webView.loadUrl(ORIGIN + "/assets/www/" + START_PAGE);',
    '        String targetPage = getIntent().getStringExtra("target_page");\n'
    '        String pageToLoad = (targetPage != null && !targetPage.isEmpty()) ? targetPage : START_PAGE;\n'
    '        webView.loadUrl(ORIGIN + "/assets/www/" + pageToLoad);'
)

# Also handle onNewIntent when app is already open in background
on_new_intent_code = """
    @Override
    protected void onNewIntent(Intent intent) {
        super.onNewIntent(intent);
        setIntent(intent);
        String targetPage = intent.getStringExtra("target_page");
        if (targetPage != null && !targetPage.isEmpty() && webView != null) {
            webView.loadUrl(ORIGIN + "/assets/www/" + targetPage);
        }
    }
"""

main = main.replace(
    '    @Override\n    protected void onPause() {',
    on_new_intent_code + '\n    @Override\n    protected void onPause() {'
)

with open(MAIN, "w", encoding="utf-8") as f: f.write(main)
print("  Updated MainActivity.java")

print("\nDone. Launcher shortcuts installed!")
