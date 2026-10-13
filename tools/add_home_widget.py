#!/usr/bin/env python3
"""
Add Home Screen Widget support.
Checks FIRST. Changes NOTHING if checks fail.
Run from repo root: python3 tools/add_home_widget.py
"""
import sys, os

MANIFEST = "app/src/main/AndroidManifest.xml"
MAIN     = "app/src/main/java/com/spaila/webview/MainActivity.java"
JS       = "app/src/main/assets/www/spaila.js"

LAYOUT_DIR = "app/src/main/res/layout"
XML_DIR    = "app/src/main/res/xml"
WIDGET_JAVA= "app/src/main/java/com/spaila/webview/SpailaWidget.java"
WIDGET_XML = f"{XML_DIR}/widget_info.xml"
LAYOUT_XML = f"{LAYOUT_DIR}/widget_layout.xml"

with open(MANIFEST, encoding="utf-8") as f: manifest = f.read()
with open(MAIN,     encoding="utf-8") as f: main     = f.read()
with open(JS,       encoding="utf-8") as f: js       = f.read()

checks = [
    (MANIFEST, "AlarmReceiver in manifest", 'android:name=".AlarmReceiver"'),
    (MAIN,     "getDeviceInfo case in MainActivity", 'fn.equals("getDeviceInfo")'),
    (JS,       "getDeviceInfo in spaila.js", 'getDeviceInfo: function () {'),
]

all_ok = True
for fname, name, needle in checks:
    src = manifest if fname == MANIFEST else (main if fname == MAIN else js)
    if needle in src:
        print(f"  OK   {name}")
    else:
        print(f"  FAIL {name}")
        all_ok = False

if not all_ok:
    print("\nAborted. Nothing was changed.")
    sys.exit(1)

print("\nAll checks passed. Applying changes...\n")

os.makedirs(LAYOUT_DIR, exist_ok=True)
os.makedirs(XML_DIR, exist_ok=True)

# 1. Create widget layout XML
with open(LAYOUT_XML, "w", encoding="utf-8") as f:
    f.write("""<?xml version="1.0" encoding="utf-8"?>
<LinearLayout xmlns:android="http://schemas.android.com/apk/res/android"
    android:id="@+id/widget_root"
    android:layout_width="match_parent"
    android:layout_height="match_parent"
    android:orientation="vertical"
    android:padding="16dp"
    android:background="#0A1F4C">

    <TextView
        android:id="@+id/widget_title"
        android:layout_width="match_parent"
        android:layout_height="wrap_content"
        android:text="Spaila App"
        android:textColor="#FFFFFF"
        android:textSize="16sp"
        android:textStyle="bold" />

    <TextView
        android:id="@+id/widget_text"
        android:layout_width="match_parent"
        android:layout_height="0dp"
        android:layout_weight="1"
        android:layout_marginTop="6dp"
        android:text="Tap to open"
        android:textColor="#9CC2FF"
        android:textSize="14sp" />

    <TextView
        android:layout_width="wrap_content"
        android:layout_height="wrap_content"
        android:layout_gravity="end"
        android:text="OPEN →"
        android:textColor="#22C55E"
        android:textSize="12sp"
        android:textStyle="bold" />
</LinearLayout>
""")
print("  Created widget_layout.xml")

# 2. Create widget info XML
with open(WIDGET_XML, "w", encoding="utf-8") as f:
    f.write("""<?xml version="1.0" encoding="utf-8"?>
<appwidget-provider xmlns:android="http://schemas.android.com/apk/res/android"
    android:minWidth="120dp"
    android:minHeight="80dp"
    android:updatePeriodMillis="0"
    android:initialLayout="@layout/widget_layout"
    android:resizeMode="horizontal|vertical"
    android:widgetCategory="home_screen">
</appwidget-provider>
""")
print("  Created widget_info.xml")

# 3. Create SpailaWidget.java
with open(WIDGET_JAVA, "w", encoding="utf-8") as f:
    f.write("""package com.spaila.webview;

import android.app.PendingIntent;
import android.appwidget.AppWidgetManager;
import android.appwidget.AppWidgetProvider;
import android.content.ComponentName;
import android.content.Context;
import android.content.Intent;
import android.content.SharedPreferences;
import android.widget.RemoteViews;

public class SpailaWidget extends AppWidgetProvider {

    public static final String PREFS = "spaila_widget_prefs";
    public static final String KEY_TITLE = "widget_title";
    public static final String KEY_TEXT = "widget_text";

    @Override
    public void onUpdate(Context context, AppWidgetManager appWidgetManager, int[] appWidgetIds) {
        updateAllWidgets(context);
    }

    public static void updateAllWidgets(Context context) {
        AppWidgetManager manager = AppWidgetManager.getInstance(context);
        ComponentName widget = new ComponentName(context, SpailaWidget.class);
        int[] appWidgetIds = manager.getAppWidgetIds(widget);
        if (appWidgetIds == null || appWidgetIds.length == 0) return;

        SharedPreferences prefs = context.getSharedPreferences(PREFS, Context.MODE_PRIVATE);
        String title = prefs.getString(KEY_TITLE, "Spaila App");
        String text = prefs.getString(KEY_TEXT, "Tap to open");

        Intent intent = new Intent(context, MainActivity.class);
        PendingIntent pendingIntent = PendingIntent.getActivity(
                context, 0, intent,
                PendingIntent.FLAG_UPDATE_CURRENT | PendingIntent.FLAG_IMMUTABLE);

        for (int id : appWidgetIds) {
            RemoteViews views = new RemoteViews(context.getPackageName(), R.layout.widget_layout);
            views.setTextViewText(R.id.widget_title, title);
            views.setTextViewText(R.id.widget_text, text);
            views.setOnClickPendingIntent(R.id.widget_root, pendingIntent);
            manager.updateAppWidget(id, views);
        }
    }
}
""")
print("  Created SpailaWidget.java")

# 4. Update AndroidManifest.xml
manifest = manifest.replace(
    '        <receiver\n'
    '            android:name=".AlarmReceiver"\n'
    '            android:exported="false" />',
    '        <receiver\n'
    '            android:name=".AlarmReceiver"\n'
    '            android:exported="false" />\n'
    '        <receiver\n'
    '            android:name=".SpailaWidget"\n'
    '            android:exported="true">\n'
    '            <intent-filter>\n'
    '                <action android:name="android.appwidget.action.APPWIDGET_UPDATE" />\n'
    '            </intent-filter>\n'
    '            <meta-data\n'
    '                android:name="android.appwidget.provider"\n'
    '                android:resource="@xml/widget_info" />\n'
    '        </receiver>'
)
with open(MANIFEST, "w", encoding="utf-8") as f: f.write(manifest)
print("  Updated AndroidManifest.xml")

# 5. Update MainActivity.java
main = main.replace(
    '            } else if (fn.equals("getDeviceInfo")) {\n'
    '                getDeviceInfo(callId);\n\n'
    '            }',
    '            } else if (fn.equals("getDeviceInfo")) {\n'
    '                getDeviceInfo(callId);\n\n'
    '            } else if (fn.equals("updateWidget")) {\n'
    '                updateWidgetData(args.getString(0), args.getString(1));\n\n'
    '            }'
)

widget_helper = """
    private void updateWidgetData(String title, String text) {
        getSharedPreferences(SpailaWidget.PREFS, MODE_PRIVATE)
                .edit()
                .putString(SpailaWidget.KEY_TITLE, title)
                .putString(SpailaWidget.KEY_TEXT, text)
                .apply();
        SpailaWidget.updateAllWidgets(this);
    }
"""

main = main.replace(
    "    private void getDeviceInfo(int callId) {",
    widget_helper + "\n    private void getDeviceInfo(int callId) {"
)
with open(MAIN, "w", encoding="utf-8") as f: f.write(main)
print("  Updated MainActivity.java")

# 6. Update spaila.js
js = js.replace(
    '    getDeviceInfo: function () {\n'
    '      return sendAndWait("getDeviceInfo", []);\n'
    '    },',
    '    getDeviceInfo: function () {\n'
    '      return sendAndWait("getDeviceInfo", []);\n'
    '    },\n'
    '    // Updates the home screen widget card with title and text\n'
    '    updateWidget: function (title, text) {\n'
    '      send("updateWidget", [String(title || ""), String(text || "")]);\n'
    '    },'
)
with open(JS, "w", encoding="utf-8") as f: f.write(js)
print("  Updated spaila.js")

print("\nDone. Home Screen Widget support successfully added!")
