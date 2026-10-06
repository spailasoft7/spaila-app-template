# Spailã App Template

Android WebView app template with the Spaila bridge.

## New app
1. Tap "Use this template" on GitHub.
2. Edit app.properties (app ID, name, version, start page, bar colour).
3. Replace branding/icon.png with your 512x512 icon.
4. Put your web app in app/src/main/assets/www/ (keep spaila.js).
5. Make a signing key for this app and add 4 repo secrets:
   KEYSTORE_BASE64, KEYSTORE_PASSWORD, KEY_ALIAS, KEY_PASSWORD.
6. Push. GitHub Actions builds the debug APK and release AAB.
