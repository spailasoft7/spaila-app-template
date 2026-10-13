#!/usr/bin/env bash
# Makes this app's signing key and saves the 4 secrets to this GitHub repo.
set -e
cd "$(dirname "$0")/.."
unset GITHUB_TOKEN GH_TOKEN
command -v keytool >/dev/null || { echo "STOP: keytool not found (Java is missing)"; exit 1; }
gh auth status >/dev/null 2>&1 || { echo "STOP: run  gh auth login --web  first, then run this again"; exit 1; }

if [ -f "app/src/main/assets/www/app-config.json" ]; then
  APP_ID=$(python3 -c "import json; print(json.load(open('app/src/main/assets/www/app-config.json')).get('appId',''))")
else
  APP_ID=$(grep '^appId=' app.properties | cut -d= -f2)
fi
[ "$APP_ID" = "com.spaila.newapp" ] && { echo "STOP: edit app-config.json first (the appId is still the placeholder)"; exit 1; }
SLUG=${APP_ID##*.}
KS="keys/${SLUG}-upload.jks"

[ -f "$KS" ] && { echo "STOP: $KS already exists. Not overwriting a key."; exit 1; }
if gh secret list | grep -q '^KEYSTORE_BASE64'; then
  echo "STOP: this repo already has signing secrets. Not overwriting them."; exit 1
fi

mkdir -p keys
PASS=$(openssl rand -base64 32 | tr -dc 'A-Za-z0-9' | head -c 20)
keytool -genkeypair -keystore "$KS" -storetype PKCS12 -alias "$SLUG" \
  -keyalg RSA -keysize 2048 -validity 10000 \
  -storepass "$PASS" -keypass "$PASS" \
  -dname "CN=Spaila Soft, O=Spaila Soft, C=ZA" >/dev/null 2>&1

gh secret set KEYSTORE_BASE64 --body "$(base64 -w0 "$KS")"
gh secret set KEYSTORE_PASSWORD --body "$PASS"
gh secret set KEY_ALIAS --body "$SLUG"
gh secret set KEY_PASSWORD --body "$PASS"

echo ""
echo "DONE. Signing is set up for $APP_ID"
echo "Key file : $KS"
echo "Alias    : $SLUG"
echo "Password : $PASS"
echo ""
echo "SAVE BOTH NOW: download the .jks file and keep the password somewhere safe."
echo "If you lose the key you cannot update the app on Google Play."
