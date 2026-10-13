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
