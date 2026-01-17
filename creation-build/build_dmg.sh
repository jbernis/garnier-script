#!/bin/bash
# Script pour créer un fichier DMG d'installation pour Mac Intel

set -e  # Arrêter en cas d'erreur

# Couleurs pour les messages
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Variables
APP_NAME="ScrapersShopify"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
APP_BUNDLE="${PROJECT_ROOT}/dist/${APP_NAME}.app"
DMG_NAME="${APP_NAME}_MacIntel"
DMG_PATH="${PROJECT_ROOT}/dist/${DMG_NAME}.dmg"
VOLUME_NAME="${APP_NAME} Installer"

echo -e "${GREEN}╔═══════════════════════════════════════════════════════════╗${NC}"
echo -e "${GREEN}║     Build DMG pour Mac Intel                              ║${NC}"
echo -e "${GREEN}╚═══════════════════════════════════════════════════════════╝${NC}"
echo ""

# Vérifier que l'application existe
if [ ! -d "$APP_BUNDLE" ]; then
    echo -e "${RED}✗ Erreur: L'application ${APP_BUNDLE} n'existe pas.${NC}"
    echo -e "${YELLOW}  Lancez d'abord: cd creation-build && python setup.py build${NC}"
    exit 1
fi

echo -e "${GREEN}✓ Application trouvée: ${APP_BUNDLE}${NC}"

# Créer un répertoire temporaire pour le DMG
TEMP_DMG_DIR="${PROJECT_ROOT}/dist/dmg_temp"
rm -rf "$TEMP_DMG_DIR"
mkdir -p "$TEMP_DMG_DIR"

# Copier l'application dans le répertoire temporaire
echo -e "${GREEN}📦 Copie de l'application...${NC}"
cp -R "$APP_BUNDLE" "$TEMP_DMG_DIR/"

# Créer un lien symbolique vers Applications
echo -e "${GREEN}🔗 Création du lien vers Applications...${NC}"
ln -s /Applications "$TEMP_DMG_DIR/Applications"

# Créer un fichier README si nécessaire
README_FILE="$TEMP_DMG_DIR/README.txt"
cat > "$README_FILE" << EOF
Scrapers Shopify - Installation

1. Glissez ${APP_NAME}.app dans le dossier Applications
2. Ouvrez Applications et lancez ${APP_NAME}.app
3. Si macOS vous demande de vérifier la sécurité, allez dans:
   Préférences Système > Sécurité et confidentialité > Ouvrir quand même

Pour plus d'informations, consultez le README.md du projet.
EOF

echo -e "${GREEN}✓ Fichier README créé${NC}"

# Supprimer l'ancien DMG s'il existe
if [ -f "$DMG_PATH" ]; then
    echo -e "${YELLOW}⚠ Suppression de l'ancien DMG...${NC}"
    rm -f "$DMG_PATH"
fi

# Créer le DMG
echo -e "${GREEN}📦 Création du DMG...${NC}"
hdiutil create -volname "$VOLUME_NAME" \
    -srcfolder "$TEMP_DMG_DIR" \
    -ov \
    -format UDZO \
    "$DMG_PATH"

# Vérifier que le DMG a été créé
if [ -f "$DMG_PATH" ]; then
    DMG_SIZE=$(du -h "$DMG_PATH" | cut -f1)
    echo -e "${GREEN}✓ DMG créé avec succès: ${DMG_PATH}${NC}"
    echo -e "${GREEN}  Taille: ${DMG_SIZE}${NC}"
    
    # Nettoyer le répertoire temporaire
    rm -rf "$TEMP_DMG_DIR"
    
    echo ""
    echo -e "${GREEN}╔═══════════════════════════════════════════════════════════╗${NC}"
    echo -e "${GREEN}║     Build terminé avec succès!                            ║${NC}"
    echo -e "${GREEN}╚═══════════════════════════════════════════════════════════╝${NC}"
    echo ""
    echo -e "Le fichier d'installation est disponible ici:"
    echo -e "${GREEN}  ${DMG_PATH}${NC}"
    echo ""
    echo -e "Pour tester l'installation:"
    echo -e "  open ${DMG_PATH}"
else
    echo -e "${RED}✗ Erreur: Le DMG n'a pas pu être créé${NC}"
    rm -rf "$TEMP_DMG_DIR"
    exit 1
fi
