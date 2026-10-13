#!/usr/bin/env python3
"""
Upgrades Home Widget with:
- Visual progress bar
- Interactive [ +1 ] counter button (runs in background)
- Deep-link [ + Add ] button (opens app to add action)
- Support for Spaila.updateWidget(title, text, progress)
Checks FIRST. Changes NOTHING if checks fail.
Run from repo root: python3 tools/upgrade_widget_suite.py
"""
import sys

LAYOUT   = "app/src/main/res/layout/widget_layout.xml"
WIDGET_J = "app/src/main/java/com/spaila/webview/SpailaWidget.java"
MAIN_J   = "app/src/main/java/com/spaila/webview/MainActivity.java"
JS       = "app/src/main/assets/www/spaila.js"
TESTS    = "app/src/main/assets/www/features-test.html"

with open(LAYOUT,   encoding="utf-8") as f: layout   = f.read()
with open(WIDGET_J, encoding="utf-8") as f: widget_j = f.read()
with open(MAIN_J,   encoding="utf-8") as f: main_j   = f.read()
with open(JS,       encoding="utf-8") as f: js       = f.read()

checks = [
    (LAYOUT,   "widget_title TextView", 'android:id="@+id/widget_title"'),
    (WIDGET_J, "SpailaWidget class",    'public class SpailaWidget extends AppWidgetProvider'),
    (MAIN_J,   "updateWidgetData call", 'updateWidgetData(args.getString(0)'),
    (JS,       "updateWidget function", 'updateWidget: function (title, text)'),
]

all_ok = True
for fname, name, needle in checks:
    src = layout if fname == LAYOUT else (widget_j if fname == WIDGET_J else (main_j if fname == MAIN_J else js))
    if needle in src:
        print(f"  OK   {name}")
    else:
        print(f"  FAIL {name}")
        all_ok = False

if not all_ok:
    print("\nAborted. Nothing was changed.")
    sys.exit(1)

print("\nAll checks passed. Upgrading Widget suite...\n")

# 1. Update widget_layout.xml
with open(LAYOUT, "w", encoding="utf-8") as f:
    f.write("""<?xml version="1.0" encoding="utf-8"?>
<LinearLayout xmlns:android="http://schemas.android.com/apk/res/android"
    android:id="@+id/widget_root"
    android:layout_width="match_parent"
    android:layout_height="match_parent"
    android:orientation="vertical"
    android:background="@drawable/widget_bg">

    <!-- Header Row -->
    <LinearLayout
        android:layout_width="match_parent"
        android:layout_height="wrap_content"
        android:orientation="horizontal"
        android:gravity="center_vertical">

        <TextView
            android:id="@+id/widget_title"
            android:layout_width="0dp"
            android:layout_height="wrap_content"
            android:layout_weight="1"
            android:text="Spaila Soft"
            android:textColor="#FFFFFF"
            android:textSize="15sp"
            android:textStyle="bold"
            android:singleLine="true" />

        <!-- Counter button (interactive without opening app) -->
        <TextView
            android:id="@+id/widget_btn_count"
            android:layout_width="wrap_content"
            android:layout_height="wrap_content"
            android:background="#334155"
            android:paddingLeft="8dp"
            android:paddingTop="3dp"
            android:paddingRight="8dp"
            android:paddingBottom="3dp"
            android:layout_marginEnd="6dp"
            android:text="+1"
            android:textColor="#38BDF8"
            android:textSize="12sp"
            android:textStyle="bold" />

        <!-- Deep link button (opens app into Add mode) -->
        <TextView
            android:id="@+id/widget_btn_add"
            android:layout_width="wrap_content"
            android:layout_height="wrap_content"
            android:background="#2563EB"
            android:paddingLeft="9dp"
            android:paddingTop="3dp"
            android:paddingRight="9dp"
            android:paddingBottom="3dp"
            android:text="＋ NEW"
            android:textColor="#FFFFFF"
            android:textSize="11sp"
            android:textStyle="bold" />
    </LinearLayout>

    <!-- Message / Task Content -->
    <TextView
        android:id="@+id/widget_text"
        android:layout_width="match_parent"
        android:layout_height="0dp"
        android:layout_weight="1"
        android:layout_marginTop="8dp"
        android:gravity="center_vertical"
        android:text="Tap to update from app"
        android:textColor="#E2E8F0"
        android:textSize="13sp"
        android:maxLines="3" />

    <!-- Progress Bar -->
    <ProgressBar
        android:id="@+id/widget_progress"
        style="?android:attr/progressBarStyleHorizontal"
        android:layout_width="match_parent"
        android:layout_height="6dp"
        android:layout_marginTop="8dp"
        android:max="100"
        android:progress="50"
        android:progressTint="#38BDF8"
        android:progressBackgroundTint="#334155" />
</LinearLayout>
""")
print("  Updated widget_layout.xml with progress bar, +1 counter, and deep-link button")

# 2. Update SpailaWidget.java
with open(WIDGET_J, "w", encoding="utf-8") as f:
    f.write("""package com.spaila.webview;

import android.app.PendingIntent;
import android.appwidget.AppWidgetManager;
import android.appwidget.AppWidgetProvider;
import android.content.ComponentName;
import android.content.Context;
import android.content.Intent;
import android.content.SharedPreferences;
import android.view.View;
import android.widget.RemoteViews;

public class SpailaWidget extends AppWidgetProvider {

    public static final String PREFS = "spaila_widget_prefs";
    public static final String KEY_TITLE = "widget_title";
    public static final String KEY_TEXT = "widget_text";
    public static final String KEY_PROGRESS = "widget_progress";
    public static final String KEY_COUNT = "widget_counter_val";

    public static final String ACTION_COUNT_CLICK = "com.spaila.widget.ACTION_COUNT";

    @Override
    public void onReceive(Context context, Intent intent) {
        super.onReceive(context, intent);
        if (ACTION_COUNT_CLICK.equals(intent.getAction())) {
            SharedPreferences prefs = context.getSharedPreferences(PREFS, Context.MODE_PRIVATE);
            int current = prefs.getInt(KEY_COUNT, 0) + 1;
            prefs.edit().putInt(KEY_COUNT, current).apply();
            updateAllWidgets(context);
        }
    }

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
        String title = prefs.getString(KEY_TITLE, "Spaila Soft");
        String text = prefs.getString(KEY_TEXT, "Tap to update");
        int progress = prefs.getInt(KEY_PROGRESS, -1);
        int counter = prefs.getInt(KEY_COUNT, 0);

        // Tap on widget body -> opens main app
        Intent openAppIntent = new Intent(context, MainActivity.class);
        PendingIntent piOpen = PendingIntent.getActivity(
                context, 10, openAppIntent,
                PendingIntent.FLAG_UPDATE_CURRENT | PendingIntent.FLAG_IMMUTABLE);

        // Tap on [ ＋ NEW ] -> deep links to add action
        Intent addIntent = new Intent(context, MainActivity.class);
        addIntent.putExtra("widget_action", "add");
        PendingIntent piAdd = PendingIntent.getActivity(
                context, 11, addIntent,
                PendingIntent.FLAG_UPDATE_CURRENT | PendingIntent.FLAG_IMMUTABLE);

        // Tap on [ +1 ] -> background broadcast counter
        Intent countIntent = new Intent(context, SpailaWidget.class);
        countIntent.setAction(ACTION_COUNT_CLICK);
        PendingIntent piCount = PendingIntent.getBroadcast(
                context, 12, countIntent,
                PendingIntent.FLAG_UPDATE_CURRENT | PendingIntent.FLAG_IMMUTABLE);

        for (int id : appWidgetIds) {
            RemoteViews views = new RemoteViews(context.getPackageName(), R.layout.widget_layout);
            views.setTextViewText(R.id.widget_title, title + " (" + counter + ")");
            views.setTextViewText(R.id.widget_text, text);

            if (progress >= 0) {
                views.setViewVisibility(R.id.widget_progress, View.VISIBLE);
                views.setProgressBar(R.id.widget_progress, 100, Math.min(100, progress), false);
            } else {
                views.setViewVisibility(R.id.widget_progress, View.GONE);
            }

            views.setOnClickPendingIntent(R.id.widget_root, piOpen);
            views.setOnClickPendingIntent(R.id.widget_btn_add, piAdd);
            views.setOnClickPendingIntent(R.id.widget_btn_count, piCount);

            manager.updateAppWidget(id, views);
        }
    }
}
""")
print("  Updated SpailaWidget.java with counter broadcast and deep linking")

# 3. Update MainActivity.java to support progress argument in updateWidget
main_j = main_j.replace(
    '            } else if (fn.equals("updateWidget")) {\n                updateWidgetData(args.getString(0), args.getString(1));',
    '            } else if (fn.equals("updateWidget")) {\n                int prog = args.length() > 2 ? args.optInt(2, -1) : -1;\n                updateWidgetData(args.getString(0), args.getString(1), prog);'
)

old_update_data = """    private void updateWidgetData(String title, String text) {
        getSharedPreferences(SpailaWidget.PREFS, MODE_PRIVATE)
                .edit()
                .putString(SpailaWidget.KEY_TITLE, title)
                .putString(SpailaWidget.KEY_TEXT, text)
                .apply();
        SpailaWidget.updateAllWidgets(this);
    }"""

new_update_data = """    private void updateWidgetData(String title, String text, int progress) {
        getSharedPreferences(SpailaWidget.PREFS, MODE_PRIVATE)
                .edit()
                .putString(SpailaWidget.KEY_TITLE, title)
                .putString(SpailaWidget.KEY_TEXT, text)
                .putInt(SpailaWidget.KEY_PROGRESS, progress)
                .apply();
        SpailaWidget.updateAllWidgets(this);
    }"""

main_j = main_j.replace(old_update_data, new_update_data)

# Handle widget_action in onCreate
main_j = main_j.replace(
    "        handleIncomingShare(getIntent());",
    "        handleIncomingShare(getIntent());\n        handleWidgetAction(getIntent());"
)

# Handle widget_action in onNewIntent
main_j = main_j.replace(
    "        handleIncomingShare(intent);",
    "        handleIncomingShare(intent);\n        handleWidgetAction(intent);"
)

widget_action_helper = """
    private void handleWidgetAction(Intent intent) {
        if (intent != null && intent.hasExtra("widget_action")) {
            String action = intent.getStringExtra("widget_action");
            new Handler(Looper.getMainLooper()).postDelayed(() -> {
                if (webView != null) {
                    webView.evaluateJavascript("if(window.onSpailaWidgetAction) window.onSpailaWidgetAction(" + JSONObject.quote(action) + ");", null);
                }
            }, 800);
        }
    }
"""

main_j = main_j.replace(
    "    private void handleIncomingShare(Intent intent) {",
    widget_action_helper + "\n    private void handleIncomingShare(Intent intent) {"
)

with open(MAIN_J, "w", encoding="utf-8") as f: f.write(main_j)
print("  Updated MainActivity.java to support progress and widget deep-links")

# 4. Update spaila.js
old_js_update = """    // Updates the home screen widget card with title and text
    updateWidget: function (title, text) {
      send("updateWidget", [String(title || ""), String(text || "")]);
    },"""

new_js_update = """    // Updates the home screen widget with title, text, and optional progress (0-100 or -1 to hide)
    updateWidget: function (title, text, progress) {
      var p = typeof progress === "number" ? Math.round(progress) : -1;
      send("updateWidget", [String(title || ""), String(text || ""), p]);
    },"""

js = js.replace(old_js_update, new_js_update)
with open(JS, "w", encoding="utf-8") as f: f.write(js)
print("  Updated spaila.js with updateWidget(title, text, progress)")

print("\nDone. Upgraded Interactive Widget Suite is ready!")
