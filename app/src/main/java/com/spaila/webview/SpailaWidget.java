package com.spaila.webview;

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
