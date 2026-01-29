#!/bin/bash

# =============================================================================
# Script pour créer un lanceur macOS avec AppleScript (plus compatible)
# =============================================================================

set -e

# Configuration
APP_NAME="ScrapersShopify Dev"
APP_BUNDLE_NAME="ScrapersShopify"
ICON_PATH="$(pwd)/creation-build/app_icon.icns"
SCRIPT_PATH="$(pwd)/run_gui.sh"
APP_PATH="$(pwd)/${APP_BUNDLE_NAME}.app"

# Obtenir le chemin absolu du répertoire du projet
PROJECT_ABS_PATH="$(cd "$(dirname "$SCRIPT_PATH")" && pwd)"

# Couleurs
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${BLUE}🚀 Création du lanceur AppleScript pour ${APP_NAME}${NC}"
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""

# Vérifier que l'icône existe
if [ ! -f "$ICON_PATH" ]; then
    echo -e "${YELLOW}⚠️  Icône introuvable: $ICON_PATH${NC}"
    echo -e "   Création sans icône..."
fi

# Vérifier que le script existe
if [ ! -f "$SCRIPT_PATH" ]; then
    echo -e "${RED}✗ Erreur: Script introuvable: $SCRIPT_PATH${NC}"
    exit 1
fi

# Supprimer l'ancien .app s'il existe
if [ -d "$APP_PATH" ]; then
    echo -e "${YELLOW}🗑️  Suppression de l'ancien lanceur...${NC}"
    rm -rf "$APP_PATH"
fi

echo -e "${GREEN}📦 Création de la structure de l'application...${NC}"

# Créer la structure du bundle macOS
mkdir -p "${APP_PATH}/Contents/MacOS"
mkdir -p "${APP_PATH}/Contents/Resources"

# ============================================
# 1. Créer le script AppleScript compilé
# ============================================

echo -e "${GREEN}⚙️  Création de l'AppleScript...${NC}"

# Créer le fichier AppleScript temporaire
cat > "/tmp/launcher_script.applescript" << EOF
#!/usr/bin/osascript

-- Chemin du projet
set projectPath to "${PROJECT_ABS_PATH}"

-- Vérifier que le répertoire existe
tell application "System Events"
    if not (exists folder projectPath) then
        display alert "Erreur ScrapersShopify" message "Le répertoire du projet est introuvable:" & return & return & projectPath & return & return & "As-tu déplacé ou supprimé le projet?" as critical
        return
    end if
end tell

-- Lancer le script via Terminal (en arrière-plan)
do shell script "cd " & quoted form of projectPath & " && ./run_gui.sh > /dev/null 2>&1 &"
EOF

# Compiler l'AppleScript en binaire
osacompile -o "${APP_PATH}/Contents/MacOS/applet" "/tmp/launcher_script.applescript"

# Nettoyer
rm "/tmp/launcher_script.applescript"

# ============================================
# 2. Copier l'icône
# ============================================

if [ -f "$ICON_PATH" ]; then
    echo -e "${GREEN}🎨 Copie de l'icône personnalisée...${NC}"
    cp "$ICON_PATH" "${APP_PATH}/Contents/Resources/applet.icns"
fi

# ============================================
# 3. Créer le fichier Info.plist
# ============================================

echo -e "${GREEN}📋 Création du fichier Info.plist...${NC}"

cat > "${APP_PATH}/Contents/Info.plist" << EOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>CFBundleExecutable</key>
    <string>applet</string>
    
    <key>CFBundleIconFile</key>
    <string>applet.icns</string>
    
    <key>CFBundleIdentifier</key>
    <string>com.shopify.scrapers</string>
    
    <key>CFBundleName</key>
    <string>${APP_NAME}</string>
    
    <key>CFBundleDisplayName</key>
    <string>${APP_NAME}</string>
    
    <key>CFBundlePackageType</key>
    <string>APPL</string>
    
    <key>CFBundleShortVersionString</key>
    <string>1.0.0</string>
    
    <key>CFBundleVersion</key>
    <string>1</string>
    
    <key>LSMinimumSystemVersion</key>
    <string>10.13</string>
    
    <key>NSHighResolutionCapable</key>
    <true/>
    
    <key>LSUIElement</key>
    <false/>
</dict>
</plist>
EOF

# ============================================
# 4. Définir les permissions
# ============================================

echo -e "${GREEN}🔑 Configuration des permissions...${NC}"
chmod -R 755 "${APP_PATH}"
chmod +x "${APP_PATH}/Contents/MacOS/applet"

# ============================================
# 5. Forcer le rafraîchissement macOS
# ============================================

echo -e "${GREEN}🔄 Rafraîchissement de macOS...${NC}"
touch "$APP_PATH"

# Supprimer l'attribut de quarantaine
xattr -cr "$APP_PATH" 2>/dev/null || true

# ============================================
# Résumé
# ============================================

echo ""
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${GREEN}✅ Lanceur AppleScript créé avec succès !${NC}"
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""
echo -e "${YELLOW}📍 Emplacement :${NC} ${APP_PATH}"
echo ""
echo -e "${YELLOW}🎯 Pour l'ajouter au Dock :${NC}"
echo -e "   1. ${GREEN}Glisse${NC} ${APP_BUNDLE_NAME}.app vers le ${GREEN}Dock${NC}"
echo -e "   2. ${GREEN}Double-clique${NC} pour tester !"
echo ""
echo -e "${YELLOW}💡 Avantages de l'AppleScript :${NC}"
echo -e "   • ${GREEN}Compatible${NC} avec tous les modes de lancement"
echo -e "   • ${GREEN}Reconnu${NC} nativement par macOS"
echo -e "   • ${GREEN}Fonctionne${NC} via double-clic, Dock, et Spotlight"
echo ""
echo -e "${YELLOW}⚠️  Important :${NC}"
echo -e "   • Chemin encodé : ${GREEN}${PROJECT_ABS_PATH}${NC}"
echo -e "   • Si tu déplaces le projet : ${GREEN}relance ce script${NC}"
echo ""

# Ouvrir le Finder
open "$(dirname "$APP_PATH")" 2>/dev/null || true

echo -e "${GREEN}✨ Terminé !${NC}"
