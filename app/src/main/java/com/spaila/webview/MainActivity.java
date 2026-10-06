package com.spaila.webview;

import android.Manifest;
import android.app.Activity;
import android.app.AlarmManager;
import android.app.PendingIntent;
import android.content.Intent;
import android.content.pm.PackageManager;
import android.graphics.Insets;
import android.net.Uri;
import android.os.Build;
import android.os.Bundle;
import android.os.Handler;
import android.os.Looper;
import android.os.Message;
import android.view.View;
import android.view.ViewTreeObserver;
import android.view.WindowInsets;
import android.view.WindowInsetsController;
import android.webkit.WebChromeClient;
import android.webkit.WebResourceRequest;
import android.webkit.WebResourceResponse;
import android.webkit.WebSettings;
import android.webkit.WebView;
import android.webkit.WebViewClient;
import android.widget.FrameLayout;
import android.widget.Toast;
import android.window.OnBackInvokedDispatcher;

import androidx.webkit.WebMessageCompat;
import androidx.webkit.WebViewAssetLoader;
import androidx.webkit.WebViewCompat;
import androidx.webkit.WebViewFeature;

import org.json.JSONArray;
import org.json.JSONObject;

import java.util.ArrayList;
import java.util.Collections;
import java.util.List;
import java.util.Set;

public class MainActivity extends Activity {

    // ----- Per-app settings (they come from app.properties) -----
    private static final String START_PAGE = BuildConfig.START_PAGE;
    private static final int BAR_COLOR = BuildConfig.BAR_COLOR; // status bar and bottom bar colour
    private static final int SPLASH_MAX_MS = 10000;   // the splash never stays longer than this
    // ----------------------------

    private static final String ORIGIN = "https://appassets.androidplatform.net";
    private static final int REQ_NOTIFICATIONS = 1001;

    private WebView webView;
    private final List<Runnable> pendingActions = new ArrayList<>();
    private boolean permissionRequestInFlight = false;
    private boolean pageReady = false; // true once the page has loaded (or the time limit passed)

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);

        webView = new WebView(this);

        FrameLayout root = new FrameLayout(this);
        root.setBackgroundColor(BAR_COLOR);
        root.addView(webView, new FrameLayout.LayoutParams(
                FrameLayout.LayoutParams.MATCH_PARENT,
                FrameLayout.LayoutParams.MATCH_PARENT));
        setContentView(root);

        // The WebView is white by default. Make it navy so nothing white can flash.
        webView.setBackgroundColor(BAR_COLOR);

        holdSplashUntilReady();

        setupSystemBars(root);
        setupBackHandling();

        WebSettings settings = webView.getSettings();
        settings.setJavaScriptEnabled(true);
        settings.setDomStorageEnabled(true);
        settings.setSupportMultipleWindows(true);

        final WebViewAssetLoader assetLoader = new WebViewAssetLoader.Builder()
                .addPathHandler("/assets/", new WebViewAssetLoader.AssetsPathHandler(this))
                .build();

        webView.setWebViewClient(new WebViewClient() {
            @Override
            public WebResourceResponse shouldInterceptRequest(WebView view, WebResourceRequest request) {
                return assetLoader.shouldInterceptRequest(request.getUrl());
            }

            @Override
            public void onPageFinished(WebView view, String url) {
                markPageReady();
            }

            @Override
            public boolean shouldOverrideUrlLoading(WebView view, WebResourceRequest request) {
                Uri uri = request.getUrl();
                if (uri.toString().startsWith(ORIGIN)) {
                    return false; // our own pages stay inside the app
                }
                openInBrowser(uri);
                return true;
            }
        });

        // Handles window.open(...) and links with target="_blank"
        webView.setWebChromeClient(new WebChromeClient() {
            @Override
            public boolean onCreateWindow(WebView view, boolean isDialog,
                                          boolean isUserGesture, Message resultMsg) {
                WebView temp = new WebView(MainActivity.this);
                temp.setWebViewClient(new WebViewClient() {
                    @Override
                    public boolean shouldOverrideUrlLoading(WebView v, WebResourceRequest request) {
                        openInBrowser(request.getUrl());
                        return true;
                    }
                });
                WebView.WebViewTransport transport = (WebView.WebViewTransport) resultMsg.obj;
                transport.setWebView(temp);
                resultMsg.sendToTarget();
                return true;
            }
        });

        setupSpailaBridge();

        webView.loadUrl(ORIGIN + "/assets/www/" + START_PAGE);
    }

    // ---------- Splash screen ----------

    // Android keeps showing the splash until the app draws its first frame.
    // So we refuse to draw until the page is ready, or until SPLASH_MAX_MS passes.
    private void holdSplashUntilReady() {
        final View content = findViewById(android.R.id.content);
        content.getViewTreeObserver().addOnPreDrawListener(new ViewTreeObserver.OnPreDrawListener() {
            @Override
            public boolean onPreDraw() {
                if (pageReady) {
                    content.getViewTreeObserver().removeOnPreDrawListener(this);
                    return true;  // ready: draw now, the splash goes away
                }
                return false;     // not ready: skip drawing, the splash stays
            }
        });

        // Safety net: never get stuck on the splash forever.
        new Handler(Looper.getMainLooper()).postDelayed(this::markPageReady, SPLASH_MAX_MS);
    }

    private void markPageReady() {
        pageReady = true;
    }

    // ---------- System bars (status bar and bottom bar) ----------

    private void setupSystemBars(FrameLayout root) {
        // Colours: used on Android 14 and older. On 15+ the root's navy background shows through.
        getWindow().setStatusBarColor(BAR_COLOR);
        getWindow().setNavigationBarColor(BAR_COLOR);

        // Light icons (white clock, battery) because the bars are dark.
        if (Build.VERSION.SDK_INT >= 30) {
            WindowInsetsController controller = getWindow().getInsetsController();
            if (controller != null) {
                controller.setSystemBarsAppearance(0,
                        WindowInsetsController.APPEARANCE_LIGHT_STATUS_BARS
                                | WindowInsetsController.APPEARANCE_LIGHT_NAVIGATION_BARS);
            }
        } else {
            View decor = getWindow().getDecorView();
            int flags = decor.getSystemUiVisibility();
            flags &= ~View.SYSTEM_UI_FLAG_LIGHT_STATUS_BAR;
            flags &= ~View.SYSTEM_UI_FLAG_LIGHT_NAVIGATION_BAR;
            decor.setSystemUiVisibility(flags);
        }

        // Keep the page away from the bars and the keyboard.
        root.setOnApplyWindowInsetsListener((v, insets) -> {
            int left, top, right, bottom;
            if (Build.VERSION.SDK_INT >= 30) {
                Insets i = insets.getInsets(WindowInsets.Type.systemBars() | WindowInsets.Type.ime());
                left = i.left;
                top = i.top;
                right = i.right;
                bottom = i.bottom;
            } else {
                left = insets.getSystemWindowInsetLeft();
                top = insets.getSystemWindowInsetTop();
                right = insets.getSystemWindowInsetRight();
                bottom = insets.getSystemWindowInsetBottom();
            }
            v.setPadding(left, top, right, bottom);
            return insets;
        });
    }

    // ---------- Back button ----------

    private void setupBackHandling() {
        if (Build.VERSION.SDK_INT >= 33) {
            getOnBackInvokedDispatcher().registerOnBackInvokedCallback(
                    OnBackInvokedDispatcher.PRIORITY_DEFAULT, this::handleBack);
        }
    }

    // Used on Android 12 and older.
    @Override
    public void onBackPressed() {
        handleBack();
    }

    // Ask the page first. If it doesn't handle Back, send the app to the background.
    private void handleBack() {
        webView.evaluateJavascript(
                "(function(){try{return !!(window.onSpailaBack && window.onSpailaBack());}catch(e){return false;}})()",
                value -> {
                    if (!"true".equals(value)) {
                        moveTaskToBack(true);
                    }
                });
    }

    private void openInBrowser(Uri uri) {
        try {
            startActivity(new Intent(Intent.ACTION_VIEW, uri));
        } catch (Exception e) {
            Toast.makeText(this, "Could not open link", Toast.LENGTH_SHORT).show();
        }
    }

    // ---------- Bridge ----------

    private void setupSpailaBridge() {
        if (!WebViewFeature.isFeatureSupported(WebViewFeature.WEB_MESSAGE_LISTENER)) {
            Toast.makeText(this, "Spaila bridge not supported on this device", Toast.LENGTH_LONG).show();
            return;
        }

        Set<String> allowedOrigins = Collections.singleton(ORIGIN);

        WebViewCompat.addWebMessageListener(webView, "SpailaNative", allowedOrigins,
                (view, message, sourceOrigin, isMainFrame, replyProxy) -> {
                    handleMessage(message);
                });
    }

    private void handleMessage(WebMessageCompat message) {
        try {
            JSONObject json = new JSONObject(message.getData());
            String fn = json.getString("fn");
            JSONArray args = json.getJSONArray("args");

            if (fn.equals("toast")) {
                Toast.makeText(this, args.getString(0), Toast.LENGTH_SHORT).show();

            } else if (fn.equals("showNotification")) {
                final String title = args.getString(0);
                final String text = args.getString(1);
                withNotificationPermission(() -> NotificationHelper.show(this, title, text));

            } else if (fn.equals("scheduleNotification")) {
                final int id = args.getInt(0);
                final String title = args.getString(1);
                final String text = args.getString(2);
                // The alarm time is fixed now, even if the permission popup takes a while.
                final long triggerAt = System.currentTimeMillis() + args.getLong(3) * 1000L;
                withNotificationPermission(() -> scheduleNotification(id, title, text, triggerAt));

            } else if (fn.equals("cancelScheduledNotification")) {
                cancelScheduledNotification(args.getInt(0));
            }
        } catch (Exception e) {
            // Ignore bad messages for now
        }
    }

    // ---------- Notification permission ----------

    // Runs the action now if allowed. Otherwise it waits, asks once, and runs
    // everything that is waiting if the user says yes.
    private void withNotificationPermission(Runnable action) {
        if (Build.VERSION.SDK_INT >= 33
                && checkSelfPermission(Manifest.permission.POST_NOTIFICATIONS)
                != PackageManager.PERMISSION_GRANTED) {
            pendingActions.add(action);
            if (!permissionRequestInFlight) {
                permissionRequestInFlight = true;
                requestPermissions(new String[]{Manifest.permission.POST_NOTIFICATIONS}, REQ_NOTIFICATIONS);
            }
            return;
        }
        action.run();
    }

    @Override
    public void onRequestPermissionsResult(int requestCode, String[] permissions, int[] grantResults) {
        super.onRequestPermissionsResult(requestCode, permissions, grantResults);
        if (requestCode == REQ_NOTIFICATIONS) {
            permissionRequestInFlight = false;
            boolean granted = grantResults.length > 0
                    && grantResults[0] == PackageManager.PERMISSION_GRANTED;

            List<Runnable> toRun = new ArrayList<>(pendingActions);
            pendingActions.clear();

            if (granted) {
                for (Runnable action : toRun) {
                    action.run();
                }
            } else {
                Toast.makeText(this, "Notifications are turned off for this app", Toast.LENGTH_LONG).show();
            }
        }
    }

    // ---------- Scheduled notifications ----------

    private PendingIntent alarmIntent(int id, String title, String message, int flags) {
        Intent intent = new Intent(this, AlarmReceiver.class);
        intent.putExtra("title", title);
        intent.putExtra("message", message);
        return PendingIntent.getBroadcast(this, id, intent, flags | PendingIntent.FLAG_IMMUTABLE);
    }

    private void scheduleNotification(int id, String title, String message, long triggerAt) {
        AlarmManager alarmManager = getSystemService(AlarmManager.class);
        PendingIntent pending = alarmIntent(id, title, message, PendingIntent.FLAG_UPDATE_CURRENT);
        alarmManager.setAndAllowWhileIdle(AlarmManager.RTC_WAKEUP, triggerAt, pending);
    }

    private void cancelScheduledNotification(int id) {
        AlarmManager alarmManager = getSystemService(AlarmManager.class);
        PendingIntent pending = alarmIntent(id, "", "", PendingIntent.FLAG_NO_CREATE);
        if (pending != null) {
            alarmManager.cancel(pending);
            pending.cancel();
        }
    }
}
