#!/usr/bin/env python3
"""
Add BootReceiver: re-schedules saved alarms after phone restarts.
Checks FIRST. Changes NOTHING if any check fails.
Run from repo root: python3 tools/add_boot_receiver.py
"""
import sys, os

DIR      = "app/src/main/java/com/spaila/webview"
MAIN     = f"{DIR}/MainActivity.java"
ALARM    = f"{DIR}/AlarmReceiver.java"
BOOT     = f"{DIR}/BootReceiver.java"
MANIFEST = "app/src/main/AndroidManifest.xml"

with open(MAIN,     encoding="utf-8") as f: main     = f.read()
with open(ALARM,    encoding="utf-8") as f: alarm    = f.read()
with open(MANIFEST, encoding="utf-8") as f: manifest = f.read()

checks = [
    (MAIN,     "scheduleNotification method",   "private void scheduleNotification("),
    (MAIN,     "cancelScheduledNotification",    "alarmManager.cancel(pending);"),
    (MAIN,     "alarmIntent method",             "private PendingIntent alarmIntent("),
    (MAIN,     "Scheduled notifications section","// ---------- Scheduled notifications ----------"),
    (ALARM,    "AlarmReceiver.onReceive",        "NotificationHelper.show("),
    (MANIFEST, "AlarmReceiver in manifest",      'android:name=".AlarmReceiver"'),
    (MANIFEST, "FOREGROUND_SERVICE_SPECIAL_USE", "FOREGROUND_SERVICE_SPECIAL_USE"),
]

all_ok = True
for fname, name, needle in checks:
    src = main if fname == MAIN else (alarm if fname == ALARM else manifest)
    if needle in src:
        print(f"  OK   {name}")
    else:
        print(f"  FAIL {name}")
        all_ok = False

if os.path.exists(BOOT):
    print(f"  FAIL BootReceiver.java already exists — delete it first")
    all_ok = False
else:
    print(f"  OK   BootReceiver.java does not exist yet")

if not all_ok:
    print("\nAborted. Nothing was changed.")
    sys.exit(1)

print("\nAll checks passed. Applying changes...\n")

# ── Create BootReceiver.java ─────────────────────────────────────────────────
with open(BOOT, "w", encoding="utf-8") as f:
    f.write("""\
package com.spaila.webview;

import android.app.AlarmManager;
import android.app.PendingIntent;
import android.content.BroadcastReceiver;
import android.content.Context;
import android.content.Intent;
import android.content.SharedPreferences;

import org.json.JSONObject;

import java.util.Map;

// Android calls this after the phone restarts so we can put saved alarms back.
public class BootReceiver extends BroadcastReceiver {

    @Override
    public void onReceive(Context context, Intent intent) {
        if (!Intent.ACTION_BOOT_COMPLETED.equals(intent.getAction())) return;

        SharedPreferences prefs =
                context.getSharedPreferences(MainActivity.PREFS, Context.MODE_PRIVATE);
        AlarmManager alarmManager =
                (AlarmManager) context.getSystemService(Context.ALARM_SERVICE);
        long now = System.currentTimeMillis();

        for (Map.Entry<String, ?> entry : prefs.getAll().entrySet()) {
            try {
                JSONObject obj    = new JSONObject((String) entry.getValue());
                int    id         = obj.getInt("id");
                String title      = obj.getString("title");
                String message    = obj.getString("message");
                long   triggerAt  = obj.getLong("triggerAt");

                if (triggerAt <= now) {
                    // The alarm time passed while the phone was off — fire it now.
                    NotificationHelper.show(context, title, message);
                    MainActivity.removeAlarm(context, id);
                } else {
                    // Still in the future — put it back in the alarm clock.
                    Intent i = new Intent(context, AlarmReceiver.class);
                    i.putExtra("id", id);
                    i.putExtra("title", title);
                    i.putExtra("message", message);
                    PendingIntent pending = PendingIntent.getBroadcast(
                            context, id, i,
                            PendingIntent.FLAG_UPDATE_CURRENT | PendingIntent.FLAG_IMMUTABLE);
                    alarmManager.setAndAllowWhileIdle(
                            AlarmManager.RTC_WAKEUP, triggerAt, pending);
                }
            } catch (Exception ignored) {}
        }
    }
}
""")
print("  Created BootReceiver.java")

# ── MainActivity.java ────────────────────────────────────────────────────────

# 1. Add id extra to alarmIntent so AlarmReceiver knows which alarm fired
main = main.replace(
    "        Intent intent = new Intent(this, AlarmReceiver.class);\n"
    "        intent.putExtra(\"title\", title);",
    "        Intent intent = new Intent(this, AlarmReceiver.class);\n"
    "        intent.putExtra(\"id\", id);\n"
    "        intent.putExtra(\"title\", title);",
)
print("  Main-1: added id extra to alarmIntent")

# 2. Save alarm to prefs after scheduling
main = main.replace(
    "        alarmManager.setAndAllowWhileIdle(AlarmManager.RTC_WAKEUP, triggerAt, pending);\n"
    "    }",
    "        alarmManager.setAndAllowWhileIdle(AlarmManager.RTC_WAKEUP, triggerAt, pending);\n"
    "        saveAlarm(id, title, message, triggerAt);\n"
    "    }",
)
print("  Main-2: saveAlarm() called after scheduling")

# 3. Remove alarm from prefs on cancel
main = main.replace(
    "            alarmManager.cancel(pending);\n"
    "            pending.cancel();\n"
    "        }\n"
    "    }",
    "            alarmManager.cancel(pending);\n"
    "            pending.cancel();\n"
    "        }\n"
    "        removeAlarm(this, id);\n"
    "    }",
)
print("  Main-3: removeAlarm() called on cancel")

# 4. Add PREFS constant + helpers before scheduled notifications section
main = main.replace(
    "    // ---------- Scheduled notifications ----------",
    "    // ---------- Alarm persistence ----------\n"
    "    // Alarms are saved here so they survive a phone restart.\n"
    "    static final String PREFS = \"spaila_alarms\";\n"
    "\n"
    "    private void saveAlarm(int id, String title, String message, long triggerAt) {\n"
    "        try {\n"
    "            JSONObject obj = new JSONObject();\n"
    "            obj.put(\"id\", id);\n"
    "            obj.put(\"title\", title);\n"
    "            obj.put(\"message\", message);\n"
    "            obj.put(\"triggerAt\", triggerAt);\n"
    "            getSharedPreferences(PREFS, MODE_PRIVATE)\n"
    "                    .edit().putString(\"alarm_\" + id, obj.toString()).apply();\n"
    "        } catch (Exception ignored) {}\n"
    "    }\n"
    "\n"
    "    static void removeAlarm(Context context, int id) {\n"
    "        context.getSharedPreferences(PREFS, Context.MODE_PRIVATE)\n"
    "                .edit().remove(\"alarm_\" + id).apply();\n"
    "    }\n"
    "\n"
    "    // ---------- Scheduled notifications ----------",
)
print("  Main-4: added PREFS, saveAlarm(), removeAlarm()")

# ── AlarmReceiver.java ───────────────────────────────────────────────────────
alarm = alarm.replace(
    "        NotificationHelper.show(\n"
    "                context,\n"
    "                title == null ? \"\" : title,\n"
    "                message == null ? \"\" : message);",
    "        NotificationHelper.show(\n"
    "                context,\n"
    "                title == null ? \"\" : title,\n"
    "                message == null ? \"\" : message);\n"
    "        // Remove from saved alarms — it fired, no need to reschedule after reboot.\n"
    "        int id = intent.getIntExtra(\"id\", -1);\n"
    "        if (id >= 0) MainActivity.removeAlarm(context, id);",
)
print("  Alarm: remove from prefs when alarm fires")

# ── AndroidManifest.xml ──────────────────────────────────────────────────────
manifest = manifest.replace(
    '    <uses-permission android:name="android.permission.FOREGROUND_SERVICE_SPECIAL_USE" />',
    '    <uses-permission android:name="android.permission.FOREGROUND_SERVICE_SPECIAL_USE" />\n'
    '    <uses-permission android:name="android.permission.RECEIVE_BOOT_COMPLETED" />',
)
print("  Manifest-1: added RECEIVE_BOOT_COMPLETED permission")

manifest = manifest.replace(
    '        <receiver\n'
    '            android:name=".AlarmReceiver"\n'
    '            android:exported="false" />',
    '        <receiver\n'
    '            android:name=".AlarmReceiver"\n'
    '            android:exported="false" />\n'
    '        <receiver\n'
    '            android:name=".BootReceiver"\n'
    '            android:exported="true">\n'
    '            <intent-filter>\n'
    '                <action android:name="android.intent.action.BOOT_COMPLETED" />\n'
    '            </intent-filter>\n'
    '        </receiver>',
)
print("  Manifest-2: added BootReceiver")

# ── Write files ──────────────────────────────────────────────────────────────
with open(MAIN,     "w", encoding="utf-8") as f: f.write(main)
with open(ALARM,    "w", encoding="utf-8") as f: f.write(alarm)
with open(MANIFEST, "w", encoding="utf-8") as f: f.write(manifest)

print("\nDone. 3 files modified, 1 file created.")
print("Now: commit, push, let GitHub Actions build.")
