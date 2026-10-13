package com.spaila.webview;

import android.content.ClipData;
import android.content.ClipboardManager;
import android.content.Context;
import android.hardware.camera2.CameraCharacteristics;
import android.hardware.camera2.CameraManager;
import android.os.VibrationEffect;
import android.os.Vibrator;
import android.os.VibratorManager;
import android.provider.Settings;
import android.view.WindowManager;

import android.Manifest;
import androidx.fragment.app.FragmentActivity;
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

import android.content.IntentFilter;
import android.os.BatteryManager;


import android.net.ConnectivityManager;
import android.net.NetworkCapabilities;
import android.media.AudioManager;
import android.media.ToneGenerator;
import androidx.biometric.BiometricManager;
import androidx.biometric.BiometricPrompt;
import androidx.core.content.ContextCompat;
import android.speech.RecognizerIntent;
import java.util.concurrent.Executor;

import android.speech.tts.TextToSpeech;
import android.view.HapticFeedbackConstants;
import java.util.Locale;
import org.json.JSONArray;
import org.json.JSONObject;

import java.util.ArrayList;
import java.util.Collections;
import java.util.List;
import java.util.Set;

public class MainActivity extends FragmentActivity implements TextToSpeech.OnInitListener {
    private TextToSpeech tts;
    private boolean ttsReady = false;

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
    private boolean pageReady = false;
    private int pendingSpeechCallId = -1; // true once the page has loaded (or the time limit passed)
    private Handler splashHandler;
    private Runnable splashRunnable;

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
        handleIncomingShare(getIntent());
        handleWidgetAction(getIntent());

        if (BuildConfig.FEATURE_TTS) { tts = new TextToSpeech(this, this); }

        String targetPage = getIntent().getStringExtra("target_page");
        String pageToLoad = (targetPage != null && !targetPage.isEmpty()) ? targetPage : START_PAGE;
        webView.loadUrl(ORIGIN + "/assets/www/" + pageToLoad);
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
        splashHandler = new Handler(Looper.getMainLooper());
        splashRunnable = this::markPageReady;
        splashHandler.postDelayed(splashRunnable, SPLASH_MAX_MS);
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
            JSONArray args = json.optJSONArray("args");
            if (args == null) args = new JSONArray();
            int callId = json.optInt("id", -1); // -1 = no reply expected

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
            } else if (fn.equals("vibrate")) {
                vibrate(args.getLong(0));

            } else if (fn.equals("share")) {
                share(args.getString(0));

            } else if (fn.equals("copyToClipboard")) {
                copyToClipboard(args.getString(0));

            } else if (fn.equals("keepScreenOn")) {
                setKeepScreenOn(args.getBoolean(0));

            } else if (fn.equals("flashlight")) {
                if (BuildConfig.FEATURE_FLASHLIGHT) {
                    setFlashlight(args.getBoolean(0), true);
                } else {
                    Toast.makeText(this, "Flashlight feature is disabled in this app", Toast.LENGTH_SHORT).show();
                }

            } else if (fn.equals("openBatterySettings")) {
                openBatterySettings();

            } else if (fn.equals("startKeepAlive")) {
                if (BuildConfig.FEATURE_KEEPALIVE) {
                    final String kTitle = args.getString(0);
                    final String kText = args.getString(1);
                    withNotificationPermission(() -> startKeepAlive(kTitle, kText));
                } else {
                    Toast.makeText(this, "Keep-alive service is disabled in this app", Toast.LENGTH_SHORT).show();
                }

            } else if (fn.equals("stopKeepAlive")) {
                stopKeepAlive();

            } else if (fn.equals("getBatteryLevel")) {
                getBatteryLevel(callId);

            } else if (fn.equals("speak")) {
                speakText(args.getString(0), (float) args.getDouble(1), (float) args.getDouble(2));

            } else if (fn.equals("stopSpeaking")) {
                if (tts != null) tts.stop();

            } else if (fn.equals("haptic")) {
                performHaptic(args.getString(0));

            } else if (fn.equals("getDeviceInfo")) {
                getDeviceInfo(callId);

            } else if (fn.equals("updateWidget")) {
                int prog = args.length() > 2 ? args.optInt(2, -1) : -1;
                updateWidgetData(args.getString(0), args.getString(1), prog);

            } else if (fn.equals("playSound")) {
                if (BuildConfig.FEATURE_SOUNDS) {
                    playSystemSound(args.getString(0));
                }

            } else if (fn.equals("setBrightness")) {
                if (BuildConfig.FEATURE_BRIGHTNESS) {
                    setScreenBrightness((float) args.getDouble(0));
                }

            } else if (fn.equals("openWhatsApp")) {
                if (BuildConfig.FEATURE_WHATSAPP) {
                    openWhatsAppChat(args.getString(0), args.getString(1));
                }

            } else if (fn.equals("rateApp")) {
                if (BuildConfig.FEATURE_RATE_APP) {
                    openPlayStoreRating();
                }

            } else if (fn.equals("authenticate")) {
                if (BuildConfig.FEATURE_BIOMETRICS) {
                    authenticateBiometric(callId, args.optString(0, "Authenticate"));
                } else {
                    replyError(callId, "Biometrics feature is disabled");
                }

            } else if (fn.equals("startSpeechRecognition")) {
                if (BuildConfig.FEATURE_SPEECH_TO_TEXT) {
                    startSpeechToText(callId, args.optString(0, "Speak now..."));
                } else {
                    replyError(callId, "Speech-to-text is disabled");
                }

            }
        } catch (Exception e) {
            // Ignore bad messages for now
        }
    }

    // ---------- Keep alive ----------

    // Starts a service with a small ongoing notification, to help the app stay alive.
    private void startKeepAlive(String title, String text) {
        Intent i = new Intent(this, KeepAliveService.class);
        i.putExtra("title", title);
        i.putExtra("text", text);
        if (Build.VERSION.SDK_INT >= 26) {
            startForegroundService(i);
        } else {
            startService(i);
        }
    }

    private void stopKeepAlive() {
        stopService(new Intent(this, KeepAliveService.class));
    }

    // Opens the phone's battery settings so the user can let this app run freely.
    private void openBatterySettings() {
        try {
            startActivity(new Intent(Settings.ACTION_IGNORE_BATTERY_OPTIMIZATION_SETTINGS));
        } catch (Exception e) {
            try {
                Intent i = new Intent(Settings.ACTION_APPLICATION_DETAILS_SETTINGS);
                i.setData(Uri.parse("package:" + getPackageName()));
                startActivity(i);
            } catch (Exception e2) {
                Toast.makeText(this, "Open Settings, then Apps, then this app, then Battery", Toast.LENGTH_LONG).show();
            }
        }
    }

    // ---------- Easy phone features ----------

    private void vibrate(long ms) {
        ms = Math.max(1, Math.min(ms, 5000));
        Vibrator v;
        if (Build.VERSION.SDK_INT >= 31) {
            v = getSystemService(VibratorManager.class).getDefaultVibrator();
        } else {
            v = (Vibrator) getSystemService(Context.VIBRATOR_SERVICE);
        }
        if (v == null || !v.hasVibrator()) return;
        if (Build.VERSION.SDK_INT >= 26) {
            v.vibrate(VibrationEffect.createOneShot(ms, VibrationEffect.DEFAULT_AMPLITUDE));
        } else {
            v.vibrate(ms);
        }
    }

    private void share(String text) {
        try {
            Intent send = new Intent(Intent.ACTION_SEND);
            send.setType("text/plain");
            send.putExtra(Intent.EXTRA_TEXT, text);
            startActivity(Intent.createChooser(send, null));
        } catch (Exception e) {
            Toast.makeText(this, "Could not open share", Toast.LENGTH_SHORT).show();
        }
    }

    private void copyToClipboard(String text) {
        ClipboardManager cm = (ClipboardManager) getSystemService(Context.CLIPBOARD_SERVICE);
        if (cm != null) {
            cm.setPrimaryClip(ClipData.newPlainText("text", text));
        }
    }

    private void setKeepScreenOn(boolean on) {
        if (on) {
            getWindow().addFlags(WindowManager.LayoutParams.FLAG_KEEP_SCREEN_ON);
        } else {
            getWindow().clearFlags(WindowManager.LayoutParams.FLAG_KEEP_SCREEN_ON);
        }
    }

    // The flashlight needs no permission. It uses the back camera's flash.
    private String torchCameraId(CameraManager cm) throws Exception {
        for (String id : cm.getCameraIdList()) {
            CameraCharacteristics c = cm.getCameraCharacteristics(id);
            Boolean flash = c.get(CameraCharacteristics.FLASH_INFO_AVAILABLE);
            Integer facing = c.get(CameraCharacteristics.LENS_FACING);
            if (flash != null && flash && facing != null
                    && facing == CameraCharacteristics.LENS_FACING_BACK) {
                return id;
            }
        }
        return null;
    }

    private void setFlashlight(boolean on, boolean showErrors) {
        try {
            CameraManager cm = getSystemService(CameraManager.class);
            String id = torchCameraId(cm);
            if (id == null) {
                if (showErrors) Toast.makeText(this, "No flashlight on this phone", Toast.LENGTH_SHORT).show();
                return;
            }
            cm.setTorchMode(id, on);
        } catch (Exception e) {
            if (showErrors) Toast.makeText(this, "Flashlight not available right now", Toast.LENGTH_SHORT).show();
        }
    }


    @Override
    protected void onNewIntent(Intent intent) {
        super.onNewIntent(intent);
        setIntent(intent);
        String targetPage = intent.getStringExtra("target_page");
        handleIncomingShare(intent);
        handleWidgetAction(intent);
        if (targetPage != null && !targetPage.isEmpty() && webView != null) {
            webView.loadUrl(ORIGIN + "/assets/www/" + targetPage);
        }
    }

    @Override
    protected void onPause() {
        super.onPause();
        if (webView != null) webView.onPause();
    }

    @Override
    protected void onResume() {
        super.onResume();
        if (webView != null) webView.onResume();
    }

    @Override
    protected void onDestroy() {
        if (splashHandler != null) splashHandler.removeCallbacks(splashRunnable);
        setFlashlight(false, false);
        if (tts != null) { tts.stop(); tts.shutdown(); } // never leave the torch on after the app closes
        super.onDestroy();
    }

    // ---------- Two-way bridge ----------

    // Sends a result back to JS. The Promise in the web page will resolve.
    private void reply(int callId, String jsonValue) {
        if (callId < 0 || webView == null) return;
        final String js = "window.Spaila._handleReply(" + callId + "," + jsonValue + ",null)";
        runOnUiThread(() -> webView.evaluateJavascript(js, null));
    }

    private void replyError(int callId, String errorMessage) {
        if (callId < 0 || webView == null) return;
        final String js = "window.Spaila._handleReply(" + callId + ",null,"
                + JSONObject.quote(errorMessage) + ")";
        runOnUiThread(() -> webView.evaluateJavascript(js, null));
    }


    @Override
    public void onInit(int status) {
        if (status == TextToSpeech.SUCCESS) {
            tts.setLanguage(Locale.getDefault());
            ttsReady = true;
        }
    }

    private void speakText(String text, float pitch, float rate) {
        if (!ttsReady || tts == null || text == null || text.isEmpty()) return;
        tts.setPitch(Math.max(0.1f, Math.min(pitch, 2.0f)));
        tts.setSpeechRate(Math.max(0.1f, Math.min(rate, 2.0f)));
        if (Build.VERSION.SDK_INT >= 21) {
            tts.speak(text, TextToSpeech.QUEUE_FLUSH, null, "spaila_tts");
        } else {
            tts.speak(text, TextToSpeech.QUEUE_FLUSH, null);
        }
    }

    private void performHaptic(String style) {
        if (webView == null) return;
        int feedback;
        switch (style) {
            case "heavy":
                feedback = HapticFeedbackConstants.LONG_PRESS;
                break;
            case "tick":
                if (Build.VERSION.SDK_INT >= 27) {
                    feedback = HapticFeedbackConstants.KEYBOARD_TAP;
                } else {
                    feedback = HapticFeedbackConstants.VIRTUAL_KEY;
                }
                break;
            case "double":
                vibrate(40);
                new Handler(Looper.getMainLooper()).postDelayed(() -> vibrate(40), 100);
                return;
            case "click":
            default:
                feedback = HapticFeedbackConstants.VIRTUAL_KEY;
                break;
        }
        webView.performHapticFeedback(feedback, HapticFeedbackConstants.FLAG_IGNORE_GLOBAL_SETTING);
    }



    private void playSystemSound(String type) {
        try {
            ToneGenerator toneGen = new ToneGenerator(AudioManager.STREAM_NOTIFICATION, 80);
            switch (type) {
                case "beep":
                    toneGen.startTone(ToneGenerator.TONE_PROP_BEEP, 150);
                    break;
                case "success":
                    toneGen.startTone(ToneGenerator.TONE_PROP_ACK, 200);
                    break;
                case "alert":
                    toneGen.startTone(ToneGenerator.TONE_PROP_BEEP2, 300);
                    break;
                case "click":
                default:
                    toneGen.startTone(ToneGenerator.TONE_PROP_BEEP, 50);
                    break;
            }
        } catch (Exception ignored) {}
    }

    private void setScreenBrightness(float brightness) {
        runOnUiThread(() -> {
            try {
                WindowManager.LayoutParams lp = getWindow().getAttributes();
                if (brightness < 0) {
                    lp.screenBrightness = WindowManager.LayoutParams.BRIGHTNESS_OVERRIDE_NONE;
                } else {
                    lp.screenBrightness = Math.max(0.01f, Math.min(1.0f, brightness));
                }
                getWindow().setAttributes(lp);
            } catch (Exception ignored) {}
        });
    }

    private void openWhatsAppChat(String phone, String message) {
        try {
            String cleanPhone = phone.replaceAll("[^0-9]", "");
            String url = "https://api.whatsapp.com/send?phone=" + cleanPhone + "&text=" + Uri.encode(message);
            Intent intent = new Intent(Intent.ACTION_VIEW, Uri.parse(url));
            startActivity(intent);
        } catch (Exception e) {
            Toast.makeText(this, "Could not open WhatsApp", Toast.LENGTH_SHORT).show();
        }
    }



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

    private void handleIncomingShare(Intent intent) {
        if (intent != null && Intent.ACTION_SEND.equals(intent.getAction()) && "text/plain".equals(intent.getType())) {
            String sharedText = intent.getStringExtra(Intent.EXTRA_TEXT);
            if (sharedText != null && !sharedText.isEmpty()) {
                new Handler(Looper.getMainLooper()).postDelayed(() -> {
                    if (webView != null) {
                        String js = "if(window.onSpailaSharedText) window.onSpailaSharedText(" + JSONObject.quote(sharedText) + ");";
                        webView.evaluateJavascript(js, null);
                    }
                }, 1000);
            }
        }
    }

    private void authenticateBiometric(int callId, String promptText) {
        runOnUiThread(() -> {
            try {
                BiometricManager manager = BiometricManager.from(this);
                int canAuth = manager.canAuthenticate(BiometricManager.Authenticators.BIOMETRIC_WEAK | BiometricManager.Authenticators.DEVICE_CREDENTIAL);
                if (canAuth != BiometricManager.BIOMETRIC_SUCCESS) {
                    reply(callId, "false");
                    return;
                }

                Executor executor = ContextCompat.getMainExecutor(this);
                BiometricPrompt prompt = new BiometricPrompt(this, executor, new BiometricPrompt.AuthenticationCallback() {
                    @Override
                    public void onAuthenticationSucceeded(BiometricPrompt.AuthenticationResult result) {
                        reply(callId, "true");
                    }
                    @Override
                    public void onAuthenticationError(int errorCode, CharSequence errString) {
                        reply(callId, "false");
                    }
                    @Override
                    public void onAuthenticationFailed() {
                        // Keep trying or cancel
                    }
                });

                BiometricPrompt.PromptInfo info = new BiometricPrompt.PromptInfo.Builder()
                        .setTitle(promptText)
                        .setAllowedAuthenticators(BiometricManager.Authenticators.BIOMETRIC_WEAK | BiometricManager.Authenticators.DEVICE_CREDENTIAL)
                        .build();

                prompt.authenticate(info);
            } catch (Exception e) {
                replyError(callId, "Biometric error: " + e.getMessage());
            }
        });
    }

    private void startSpeechToText(int callId, String prompt) {
        try {
            Intent intent = new Intent(RecognizerIntent.ACTION_RECOGNIZE_SPEECH);
            intent.putExtra(RecognizerIntent.EXTRA_LANGUAGE_MODEL, RecognizerIntent.LANGUAGE_MODEL_FREE_FORM);
            intent.putExtra(RecognizerIntent.EXTRA_PROMPT, prompt);
            pendingSpeechCallId = callId;
            startActivityForResult(intent, 2002);
        } catch (Exception e) {
            replyError(callId, "Speech recognition not available: " + e.getMessage());
        }
    }

    @Override
    protected void onActivityResult(int requestCode, int resultCode, Intent data) {
        super.onActivityResult(requestCode, resultCode, data);
        if (requestCode == 2002 && pendingSpeechCallId != -1) {
            if (resultCode == RESULT_OK && data != null) {
                ArrayList<String> matches = data.getStringArrayListExtra(RecognizerIntent.EXTRA_RESULTS);
                if (matches != null && !matches.isEmpty()) {
                    reply(pendingSpeechCallId, JSONObject.quote(matches.get(0)));
                } else {
                    reply(pendingSpeechCallId, JSONObject.quote(""));
                }
            } else {
                replyError(pendingSpeechCallId, "Cancelled or no speech detected");
            }
            pendingSpeechCallId = -1;
        }
    }

    private void openPlayStoreRating() {
        try {
            startActivity(new Intent(Intent.ACTION_VIEW, Uri.parse("market://details?id=" + getPackageName())));
        } catch (Exception e) {
            try {
                startActivity(new Intent(Intent.ACTION_VIEW, Uri.parse("https://play.google.com/store/apps/details?id=" + getPackageName())));
            } catch (Exception e2) {
                Toast.makeText(this, "Could not open Play Store", Toast.LENGTH_SHORT).show();
            }
        }
    }

    private void updateWidgetData(String title, String text, int progress) {
        getSharedPreferences(SpailaWidget.PREFS, MODE_PRIVATE)
                .edit()
                .putString(SpailaWidget.KEY_TITLE, title)
                .putString(SpailaWidget.KEY_TEXT, text)
                .putInt(SpailaWidget.KEY_PROGRESS, progress)
                .apply();
        SpailaWidget.updateAllWidgets(this);
    }

    private void getDeviceInfo(int callId) {
        try {
            JSONObject info = new JSONObject();
            info.put("osVersion", "Android " + Build.VERSION.RELEASE + " (API " + Build.VERSION.SDK_INT + ")");
            info.put("brand", Build.MANUFACTURER);
            info.put("model", Build.MODEL);
            info.put("appVersion", BuildConfig.VERSION_NAME);

            ConnectivityManager cm = (ConnectivityManager) getSystemService(Context.CONNECTIVITY_SERVICE);
            boolean isOnline = false;
            String netType = "offline";
            if (cm != null) {
                if (Build.VERSION.SDK_INT >= 23) {
                    android.net.Network network = cm.getActiveNetwork();
                    NetworkCapabilities caps = cm.getNetworkCapabilities(network);
                    if (caps != null) {
                        if (caps.hasTransport(NetworkCapabilities.TRANSPORT_WIFI)) {
                            isOnline = true;
                            netType = "wifi";
                        } else if (caps.hasTransport(NetworkCapabilities.TRANSPORT_CELLULAR)) {
                            isOnline = true;
                            netType = "cellular";
                        } else if (caps.hasCapability(NetworkCapabilities.NET_CAPABILITY_INTERNET)) {
                            isOnline = true;
                            netType = "other";
                        }
                    }
                } else {
                    android.net.NetworkInfo netInfo = cm.getActiveNetworkInfo();
                    if (netInfo != null && netInfo.isConnected()) {
                        isOnline = true;
                        netType = netInfo.getTypeName().toLowerCase();
                    }
                }
            }
            info.put("isOnline", isOnline);
            info.put("networkType", netType);

            reply(callId, info.toString());
        } catch (Exception e) {
            replyError(callId, "Failed to get device info: " + e.getMessage());
        }
    }

    private void getBatteryLevel(int callId) {
        try {
            IntentFilter ifilter = new IntentFilter(Intent.ACTION_BATTERY_CHANGED);
            Intent batteryStatus = registerReceiver(null, ifilter);
            int level = batteryStatus != null
                    ? batteryStatus.getIntExtra(BatteryManager.EXTRA_LEVEL, -1) : -1;
            int scale = batteryStatus != null
                    ? batteryStatus.getIntExtra(BatteryManager.EXTRA_SCALE, -1) : -1;
            int percent = (level >= 0 && scale > 0)
                    ? Math.round(level * 100f / scale) : -1;
            reply(callId, String.valueOf(percent));
        } catch (Exception e) {
            replyError(callId, "Could not read battery level");
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

    // ---------- Alarm persistence ----------
    // Alarms are saved here so they survive a phone restart.
    static final String PREFS = "spaila_alarms";

    private void saveAlarm(int id, String title, String message, long triggerAt) {
        try {
            JSONObject obj = new JSONObject();
            obj.put("id", id);
            obj.put("title", title);
            obj.put("message", message);
            obj.put("triggerAt", triggerAt);
            getSharedPreferences(PREFS, MODE_PRIVATE)
                    .edit().putString("alarm_" + id, obj.toString()).apply();
        } catch (Exception ignored) {}
    }

    static void removeAlarm(Context context, int id) {
        context.getSharedPreferences(PREFS, Context.MODE_PRIVATE)
                .edit().remove("alarm_" + id).apply();
    }

    // ---------- Scheduled notifications ----------

    private PendingIntent alarmIntent(int id, String title, String message, int flags) {
        Intent intent = new Intent(this, AlarmReceiver.class);
        intent.putExtra("id", id);
        intent.putExtra("title", title);
        intent.putExtra("message", message);
        return PendingIntent.getBroadcast(this, id, intent, flags | PendingIntent.FLAG_IMMUTABLE);
    }

    private void scheduleNotification(int id, String title, String message, long triggerAt) {
        AlarmManager alarmManager = getSystemService(AlarmManager.class);
        PendingIntent pending = alarmIntent(id, title, message, PendingIntent.FLAG_UPDATE_CURRENT);
        alarmManager.setAndAllowWhileIdle(AlarmManager.RTC_WAKEUP, triggerAt, pending);
        saveAlarm(id, title, message, triggerAt);
    }

    private void cancelScheduledNotification(int id) {
        AlarmManager alarmManager = getSystemService(AlarmManager.class);
        PendingIntent pending = alarmIntent(id, "", "", PendingIntent.FLAG_NO_CREATE);
        if (pending != null) {
            alarmManager.cancel(pending);
            pending.cancel();
        }
        removeAlarm(this, id);
    }
}
