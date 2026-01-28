#!/bin/bash

# =============================================================================
# Script pour créer un lanceur macOS avec icône personnalisée
# À ajouter dans le Dock pour un accès rapide
# =============================================================================

set -e  # Arrêter en cas d'erreur

# Configuration
APP_NAME="ScrapersShopify Dev"
APP_BUNDLE_NAME="ScrapersShopify-Dev"
ICON_PATH="$(pwd)/creation-build/app_icon.icns"
SCRIPT_PATH="$(pwd)/run_gui.sh"
APP_PATH="$(pwd)/${APP_BUNDLE_NAME}.app"

# Couleurs pour les logs
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${BLUE}🚀 Création du lanceur macOS pour ${APP_NAME}${NC}"
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""

# Vérifier que l'icône existe
if [ ! -f "$ICON_PATH" ]; then
    echo -e "${RED}✗ Erreur: Icône introuvable: $ICON_PATH${NC}"
    exit 1
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
# 1. Créer l'exécutable principal
# ============================================

echo -e "${GREEN}⚙️  Création de l'exécutable...${NC}"

# Obtenir le chemin absolu du répertoire du projet
PROJECT_ABS_PATH="$(cd "$(dirname "$SCRIPT_PATH")" && pwd)"

cat > "${APP_PATH}/Contents/MacOS/${APP_BUNDLE_NAME}" << EOF
#!/bin/bash

# Chemin absolu du projet (encodé lors de la création du .app)
PROJECT_DIR="${PROJECT_ABS_PATH}"

# Vérifier que le répertoire existe
if [ ! -d "\$PROJECT_DIR" ]; then
    osascript -e 'display alert "Erreur ScrapersShopify" message "Le répertoire du projet est introuvable:\n\$PROJECT_DIR\n\nAs-tu déplacé ou supprimé le projet?" as critical'
    exit 1
fi

# Se déplacer dans le répertoire du projet
cd "\$PROJECT_DIR"

# Vérifier que le script existe
if [ ! -f "./run_gui.sh" ]; then
    osascript -e 'display alert "Erreur ScrapersShopify" message "Le script run_gui.sh est introuvable dans:\n\$PROJECT_DIR" as critical'
    exit 1
fi

# Lancer le script run_gui.sh
# Option 1: Lancer dans un nouveau terminal pour voir les logs
# osascript -e 'tell application "Terminal" to do script "cd \\"\$PROJECT_DIR\\" && ./run_gui.sh"'

# Option 2: Lancer directement (sans nouveau terminal)
./run_gui.sh
EOF

chmod +x "${APP_PATH}/Contents/MacOS/${APP_BUNDLE_NAME}"

# ============================================
# 2. Copier l'icône
# ============================================

echo -e "${GREEN}🎨 Copie de l'icône personnalisée...${NC}"
cp "$ICON_PATH" "${APP_PATH}/Contents/Resources/app_icon.icns"

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
    <string>${APP_BUNDLE_NAME}</string>
    
    <key>CFBundleIconFile</key>
    <string>app_icon.icns</string>
    
    <key>CFBundleIdentifier</key>
    <string>com.shopify.scrapers.dev</string>
    
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
    
    <key>NSRequiresAquaSystemAppearance</key>
    <false/>
</dict>
</plist>
EOF

# ============================================
# 4. Forcer le Finder à rafraîchir l'icône
# ============================================

echo -e "${GREEN}🔄 Rafraîchissement de l'icône...${NC}"
touch "$APP_PATH"
killall Finder 2>/dev/null || true
sleep 1

# ============================================
# Résumé
# ============================================

echo ""
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${GREEN}✅ Lanceur créé avec succès !${NC}"
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""
echo -e "${YELLOW}📍 Emplacement :${NC} ${APP_PATH}"
echo ""
echo -e "${YELLOW}🎯 Pour l'ajouter au Dock :${NC}"
echo -e "   1. ${GREEN}Glisse${NC} ${APP_BUNDLE_NAME}.app vers le ${GREEN}Dock${NC}"
echo -e "   2. Ou fais un ${GREEN}clic droit${NC} → ${GREEN}Options${NC} → ${GREEN}Garder dans le Dock${NC}"
echo ""
echo -e "${YELLOW}🚀 Pour tester :${NC}"
echo -e "   Double-clique sur ${GREEN}${APP_BUNDLE_NAME}.app${NC}"
echo ""
echo -e "${YELLOW}💡 Conseils :${NC}"
echo -e "   • Place le .app dans ${GREEN}~/Applications${NC} pour le retrouver facilement"
echo -e "   • Tu peux déplacer le .app ${GREEN}n'importe où${NC}, il trouvera toujours le projet"
echo ""
echo -e "${YELLOW}⚠️  Important :${NC}"
echo -e "   • Le chemin du projet est encodé dans le .app: ${GREEN}${PROJECT_ABS_PATH}${NC}"
echo -e "   • Si tu ${GREEN}déplaces le projet${NC} ou le ${GREEN}copies sur un autre Mac${NC}:"
echo -e "     ${BLUE}→${NC} Relance ${GREEN}./create_dock_launcher.sh${NC} depuis le nouveau répertoire"
echo ""

# Ouvrir le Finder à l'emplacement du .app
open "$(dirname "$APP_PATH")" 2>/dev/null || true

echo -e "${GREEN}✨ Terminé !${NC}"
