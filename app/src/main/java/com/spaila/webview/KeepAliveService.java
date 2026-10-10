package com.spaila.webview;

import android.app.Notification;
import android.app.NotificationChannel;
import android.app.NotificationManager;
import android.app.PendingIntent;
import android.app.Service;
import android.content.Intent;
import android.content.pm.ServiceInfo;
import android.os.Build;
import android.os.IBinder;

// Keeps a small ongoing notification so Android is less likely to kill the app.
public class KeepAliveService extends Service {

    private static final String CHANNEL_ID = "spaila_keepalive";

    @Override
    public IBinder onBind(Intent intent) {
        return null;
    }

    @Override
    public int onStartCommand(Intent intent, int flags, int startId) {
        String title = (intent != null && intent.getStringExtra("title") != null)
                ? intent.getStringExtra("title") : "Running";
        String text = (intent != null && intent.getStringExtra("text") != null)
                ? intent.getStringExtra("text") : "Tap to open";

        if (Build.VERSION.SDK_INT >= 26) {
            NotificationChannel channel = new NotificationChannel(
                    CHANNEL_ID, "Background", NotificationManager.IMPORTANCE_LOW);
            getSystemService(NotificationManager.class).createNotificationChannel(channel);
        }

        Intent open = new Intent(this, MainActivity.class);
        open.setFlags(Intent.FLAG_ACTIVITY_NEW_TASK | Intent.FLAG_ACTIVITY_SINGLE_TOP);
        PendingIntent pending = PendingIntent.getActivity(this, 0, open,
                PendingIntent.FLAG_IMMUTABLE | PendingIntent.FLAG_UPDATE_CURRENT);

        Notification.Builder b = (Build.VERSION.SDK_INT >= 26)
                ? new Notification.Builder(this, CHANNEL_ID)
                : new Notification.Builder(this);
        Notification n = b.setSmallIcon(R.drawable.ic_stat_notify)
                .setContentTitle(title)
                .setContentText(text)
                .setContentIntent(pending)
                .setOngoing(true)
                .build();

        if (Build.VERSION.SDK_INT >= 34) {
            startForeground(1, n, ServiceInfo.FOREGROUND_SERVICE_TYPE_SPECIAL_USE);
        } else {
            startForeground(1, n);
        }
        return START_STICKY;
    }
}
