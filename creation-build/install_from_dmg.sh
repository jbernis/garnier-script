#!/bin/bash
# Script d'installation pour contourner Gatekeeper

set -e

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

echo -e "${GREEN}╔═══════════════════════════════════════════════════════════╗${NC}"
echo -e "${GREEN}║     Installation ScrapersShopify                          ║${NC}"
echo -e "${GREEN}╚═══════════════════════════════════════════════════════════╝${NC}"
echo ""

# Chercher le DMG
DMG_PATH=""
if [ -f "$1" ]; then
    DMG_PATH="$1"
elif [ -f "ScrapersShopify_MacIntel.dmg" ]; then
    DMG_PATH="ScrapersShopify_MacIntel.dmg"
elif [ -f "dist/ScrapersShopify_MacIntel.dmg" ]; then
    DMG_PATH="dist/ScrapersShopify_MacIntel.dmg"
elif [ -f "../dist/ScrapersShopify_MacIntel.dmg" ]; then
    DMG_PATH="../dist/ScrapersShopify_MacIntel.dmg"
elif [ -f ~/Downloads/ScrapersShopify_MacIntel.dmg ]; then
    DMG_PATH=~/Downloads/ScrapersShopify_MacIntel.dmg
else
    echo -e "${RED}✗ Fichier DMG introuvable${NC}"
    echo -e "${YELLOW}Usage: $0 [chemin/vers/ScrapersShopify_MacIntel.dmg]${NC}"
    exit 1
fi

echo -e "${GREEN}✓ DMG trouvé: ${DMG_PATH}${NC}"

# Étape 1 : Supprimer la quarantine du DMG
echo -e "${YELLOW}🔓 Suppression de la quarantine du DMG...${NC}"
xattr -cr "$DMG_PATH"
echo -e "${GREEN}✓ Quarantine supprimée du DMG${NC}"

# Étape 2 : Monter le DMG
echo -e "${YELLOW}📦 Montage du DMG...${NC}"
hdiutil attach "$DMG_PATH" -quiet
echo -e "${GREEN}✓ DMG monté${NC}"

# Attendre que le volume soit monté
sleep 1

# Étape 3 : Supprimer la quarantine de l'app dans le DMG
echo -e "${YELLOW}🔓 Suppression de la quarantine de l'app...${NC}"
xattr -cr "/Volumes/ScrapersShopify Installer/ScrapersShopify.app"
echo -e "${GREEN}✓ Quarantine supprimée de l'app${NC}"

# Étape 4 : Copier l'app dans Applications
echo -e "${YELLOW}📥 Copie de l'app dans Applications...${NC}"

# Supprimer l'ancienne version si elle existe
if [ -d "/Applications/ScrapersShopify.app" ]; then
    echo -e "${YELLOW}⚠ Suppression de l'ancienne version...${NC}"
    rm -rf /Applications/ScrapersShopify.app
fi

cp -R "/Volumes/ScrapersShopify Installer/ScrapersShopify.app" /Applications/
echo -e "${GREEN}✓ App copiée dans Applications${NC}"

# Étape 5 : Supprimer la quarantine de l'app installée (double sécurité)
echo -e "${YELLOW}🔓 Suppression finale de la quarantine...${NC}"
xattr -cr /Applications/ScrapersShopify.app
echo -e "${GREEN}✓ App prête à l'emploi${NC}"

# Étape 6 : Démonter le DMG
echo -e "${YELLOW}📤 Démontage du DMG...${NC}"
hdiutil detach "/Volumes/ScrapersShopify Installer" -quiet
echo -e "${GREEN}✓ DMG démonté${NC}"

echo ""
echo -e "${GREEN}╔═══════════════════════════════════════════════════════════╗${NC}"
echo -e "${GREEN}║     Installation terminée avec succès!                    ║${NC}"
echo -e "${GREEN}╚═══════════════════════════════════════════════════════════╝${NC}"
echo ""
echo -e "L'application est installée dans:"
echo -e "${GREEN}  /Applications/ScrapersShopify.app${NC}"
echo ""
echo -e "Pour la lancer:"
echo -e "${GREEN}  open /Applications/ScrapersShopify.app${NC}"
echo ""
echo -e "${YELLOW}Note: Chrome doit être installé pour utiliser les scrapers${NC}"
echo ""
