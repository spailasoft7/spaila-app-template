#!/usr/bin/env python3
"""
4 small fixes to MainActivity.java.
Checks FIRST. Changes NOTHING if any check fails.
Run from repo root: python3 tools/fix_template_v1.py
"""
import sys

FILE = "app/src/main/java/com/spaila/webview/MainActivity.java"

with open(FILE, "r", encoding="utf-8") as f:
    src = f.read()

checks = [
    ("Fix 2 unsafe args",    'JSONArray args = json.getJSONArray("args");'),
    ("Fix 3 lifecycle hook", "protected void onDestroy() {"),
    ("Fix 4 handler leak",   "new Handler(Looper.getMainLooper()).postDelayed(this::markPageReady, SPLASH_MAX_MS);"),
]

all_ok = True
for name, needle in checks:
    if needle in src:
        print(f"  OK   {name}")
    else:
        print(f"  FAIL {name}  — pattern not found")
        all_ok = False

if not all_ok:
    print("\nAborted. Nothing was changed.")
    sys.exit(1)

print("\nAll checks passed. Applying fixes...\n")

# Fix 1: typo
src = src.replace(
    '"Open Settings, then Apps, then this app, thenBattery"',
    '"Open Settings, then Apps, then this app, then Battery"',
)
print("  Fix 1 done: typo")

# Fix 2: null-safe args
src = src.replace(
    'JSONArray args = json.getJSONArray("args");',
    'JSONArray args = json.optJSONArray("args");\n            if (args == null) args = new JSONArray();',
)
print("  Fix 2 done: null-safe args")

# Fix 3: add onPause/onResume before onDestroy
src = src.replace(
    '    @Override\n    protected void onDestroy() {',
    '    @Override\n'
    '    protected void onPause() {\n'
    '        super.onPause();\n'
    '        if (webView != null) webView.onPause();\n'
    '    }\n'
    '\n'
    '    @Override\n'
    '    protected void onResume() {\n'
    '        super.onResume();\n'
    '        if (webView != null) webView.onResume();\n'
    '    }\n'
    '\n'
    '    @Override\n'
    '    protected void onDestroy() {',
)
print("  Fix 3 done: WebView lifecycle")

# Fix 4a: add two fields after pageReady
if 'splashHandler' not in src:
    src = src.replace(
        '    private boolean pageReady = false; // true once the page has loaded (or the time limit passed)',
        '    private boolean pageReady = false; // true once the page has loaded (or the time limit passed)\n'
        '    private Handler splashHandler;\n'
        '    private Runnable splashRunnable;',
    )

# Fix 4b: store handler in field instead of anonymous
src = src.replace(
    '        new Handler(Looper.getMainLooper()).postDelayed(this::markPageReady, SPLASH_MAX_MS);',
    '        splashHandler = new Handler(Looper.getMainLooper());\n'
    '        splashRunnable = this::markPageReady;\n'
    '        splashHandler.postDelayed(splashRunnable, SPLASH_MAX_MS);',
)

# Fix 4c: cancel it in onDestroy
src = src.replace(
    '    protected void onDestroy() {\n'
    '        setFlashlight(false, false);',
    '    protected void onDestroy() {\n'
    '        if (splashHandler != null) splashHandler.removeCallbacks(splashRunnable);\n'
    '        setFlashlight(false, false);',
)
print("  Fix 4 done: handler leak")

with open(FILE, "w", encoding="utf-8") as f:
    f.write(src)

print(f"\nAll done. File written: {FILE}")
print("Now: git add, git commit, git push.")
