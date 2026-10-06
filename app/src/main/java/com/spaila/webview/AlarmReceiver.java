package com.spaila.webview;

import android.content.BroadcastReceiver;
import android.content.Context;
import android.content.Intent;

// Android calls this when a scheduled alarm fires, even if the app is closed.
public class AlarmReceiver extends BroadcastReceiver {

    @Override
    public void onReceive(Context context, Intent intent) {
        String title = intent.getStringExtra("title");
        String message = intent.getStringExtra("message");
        NotificationHelper.show(
                context,
                title == null ? "" : title,
                message == null ? "" : message);
    }
}
