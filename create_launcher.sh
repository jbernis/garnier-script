#!/bin/bash
# Script pour créer une application macOS qui lance run_gui.sh

APP_NAME="ScrapersShopify Dev"
APP_DIR="${PWD}/${APP_NAME}.app"
SCRIPT_PATH="${PWD}/run_gui.sh"

echo "🚀 Création de l'application ${APP_NAME}..."

# Créer la structure .app
mkdir -p "${APP_DIR}/Contents/MacOS"
mkdir -p "${APP_DIR}/Contents/Resources"

# Créer le script exécutable
cat > "${APP_DIR}/Contents/MacOS/${APP_NAME}" << EXECSCRIPT
#!/bin/bash
cd "${PWD}"
open -a Terminal "${SCRIPT_PATH}"
EXECSCRIPT

chmod +x "${APP_DIR}/Contents/MacOS/${APP_NAME}"

# Créer Info.plist
cat > "${APP_DIR}/Contents/Info.plist" << PLIST
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>CFBundleExecutable</key>
    <string>${APP_NAME}</string>
    <key>CFBundleIdentifier</key>
    <string>com.shopify.scrapers.dev</string>
    <key>CFBundleName</key>
    <string>${APP_NAME}</string>
    <key>CFBundlePackageType</key>
    <string>APPL</string>
    <key>CFBundleShortVersionString</key>
    <string>1.0</string>
    <key>CFBundleVersion</key>
    <string>1.0</string>
</dict>
</plist>
PLIST

echo "✅ Application créée: ${APP_DIR}"
echo "📍 Tu peux maintenant la glisser dans le Dock !"
echo "🚀 Ou double-cliquer dessus pour lancer"
