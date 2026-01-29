#!/bin/bash

# =============================================================================
# Script pour créer un lanceur macOS universel (shell + osascript)
# Compatible tous Mac, pas de compilation nécessaire
# =============================================================================

set -e

# Configuration
APP_NAME="ScrapersShopify"
ICON_PATH="$(pwd)/creation-build/app_icon.icns"
SCRIPT_PATH="$(pwd)/run_gui.sh"
APP_PATH="$(pwd)/${APP_NAME}.app"

# Obtenir le chemin absolu du répertoire du projet
PROJECT_ABS_PATH="$(cd "$(dirname "$SCRIPT_PATH")" && pwd)"

# Couleurs
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${BLUE}🚀 Création du lanceur UNIVERSEL pour ${APP_NAME}${NC}"
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""

# Vérifier que l'icône existe
if [ ! -f "$ICON_PATH" ]; then
    echo -e "${YELLOW}⚠️  Icône introuvable: $ICON_PATH${NC}"
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
# 1. Créer l'exécutable wrapper (shell + osascript)
# ============================================

echo -e "${GREEN}⚙️  Création de l'exécutable wrapper...${NC}"

cat > "${APP_PATH}/Contents/MacOS/${APP_NAME}" << 'WRAPPER_EOF'
#!/bin/bash

# Récupérer le chemin du .app (on est dans Contents/MacOS, donc remonter 2 niveaux)
APP_PATH="$(cd "$(dirname "$0")/../.." && pwd)"
APP_NAME="$(basename "$APP_PATH" .app)"

# Lire le chemin du projet depuis le fichier de config
CONFIG_FILE="$APP_PATH/Contents/Resources/project_path.txt"

if [ ! -f "$CONFIG_FILE" ]; then
    osascript -e "display alert \"Erreur Configuration\" message \"Fichier de configuration introuvable!\" as critical"
    exit 1
fi

PROJECT_DIR="$(cat "$CONFIG_FILE")"

# Vérifier que le répertoire existe
if [ ! -d "$PROJECT_DIR" ]; then
    osascript -e "display alert \"Erreur ScrapersShopify\" message \"Le répertoire du projet est introuvable: $PROJECT_DIR\" as critical"
    exit 1
fi

# Lancer le script en arrière-plan
cd "$PROJECT_DIR" || exit 1

if [ ! -f "./run_gui.sh" ]; then
    osascript -e "display alert \"Erreur ScrapersShopify\" message \"Le script run_gui.sh est introuvable dans: $PROJECT_DIR\" as critical"
    exit 1
fi

# Lancer le script et capturer son PID
./run_gui.sh > /dev/null 2>&1 &
SCRIPT_PID=$!

# Attendre que le processus Python démarre
sleep 3

# Trouver le PID du processus Python (run_gui.py)
PYTHON_PID=$(pgrep -f "run_gui.py" | head -1)

# Si Python tourne, attendre qu'il se termine pour garder l'app dans le Dock
if [ -n "$PYTHON_PID" ]; then
    # Attendre que le processus Python se termine
    while kill -0 "$PYTHON_PID" 2>/dev/null; do
        sleep 2
    done
fi

# Fermer quand Python est terminé
exit 0
WRAPPER_EOF

chmod +x "${APP_PATH}/Contents/MacOS/${APP_NAME}"

# ============================================
# 2. Sauvegarder le chemin du projet
# ============================================

echo -e "${GREEN}💾 Sauvegarde du chemin du projet...${NC}"
echo "$PROJECT_ABS_PATH" > "${APP_PATH}/Contents/Resources/project_path.txt"

# ============================================
# 3. Copier l'icône
# ============================================

if [ -f "$ICON_PATH" ]; then
    echo -e "${GREEN}🎨 Copie de l'icône personnalisée...${NC}"
    cp "$ICON_PATH" "${APP_PATH}/Contents/Resources/${APP_NAME}.icns"
fi

# ============================================
# 4. Créer le fichier Info.plist
# ============================================

echo -e "${GREEN}📋 Création du fichier Info.plist...${NC}"

cat > "${APP_PATH}/Contents/Info.plist" << EOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>CFBundleExecutable</key>
    <string>${APP_NAME}</string>
    
    <key>CFBundleIconFile</key>
    <string>${APP_NAME}.icns</string>
    
    <key>CFBundleIdentifier</key>
    <string>com.shopify.scrapers</string>
    
    <key>CFBundleName</key>
    <string>${APP_NAME}</string>
    
    <key>CFBundleDisplayName</key>
    <string>Scrapers Shopify</string>
    
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
    
    <key>NSAppleScriptEnabled</key>
    <true/>
</dict>
</plist>
EOF

# ============================================
# 5. Définir les permissions
# ============================================

echo -e "${GREEN}🔑 Configuration des permissions...${NC}"
chmod -R 755 "${APP_PATH}"
chmod +x "${APP_PATH}/Contents/MacOS/${APP_NAME}"

# ============================================
# 6. Nettoyer les attributs de quarantaine
# ============================================

echo -e "${GREEN}🔄 Suppression de la quarantaine...${NC}"
xattr -cr "$APP_PATH" 2>/dev/null || true

# ============================================
# 7. Forcer le rafraîchissement macOS
# ============================================

echo -e "${GREEN}🔄 Rafraîchissement de macOS...${NC}"
touch "$APP_PATH"

# ============================================
# Résumé
# ============================================

echo ""
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${GREEN}✅ Lanceur universel créé avec succès !${NC}"
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""
echo -e "${YELLOW}📍 Emplacement :${NC} ${APP_PATH}"
echo ""
echo -e "${YELLOW}🎯 Pour l'utiliser :${NC}"
echo -e "   1. ${GREEN}Double-clique${NC} sur ${APP_NAME}.app"
echo -e "   2. ${GREEN}Glisse-le${NC} dans le Dock pour un accès rapide"
echo ""
echo -e "${YELLOW}✨ Avantages :${NC}"
echo -e "   • ${GREEN}100% compatible${NC} avec tous les Mac (Intel/Apple Silicon)"
echo -e "   • ${GREEN}Pas de compilation${NC} nécessaire"
echo -e "   • ${GREEN}Fonctionne${NC} via double-clic, Dock, et Spotlight"
echo -e "   • ${GREEN}Portable${NC} - copie le .app sur n'importe quel Mac !"
echo ""
echo -e "${YELLOW}⚠️  Important :${NC}"
echo -e "   • Chemin encodé : ${GREEN}${PROJECT_ABS_PATH}${NC}"
echo -e "   • Si tu déplaces le projet : ${GREEN}relance ce script${NC}"
echo ""

# Ouvrir le Finder
open "$(dirname "$APP_PATH")" 2>/dev/null || true

echo -e "${GREEN}✨ Terminé !${NC}"
