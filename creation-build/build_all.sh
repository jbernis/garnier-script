#!/bin/bash
# Script récapitulatif pour effectuer un build complet

set -e  # Arrêter en cas d'erreur

# Couleurs pour les messages
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"

echo -e "${BLUE}╔═══════════════════════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║     Build complet pour Mac Intel                          ║${NC}"
echo -e "${BLUE}╚═══════════════════════════════════════════════════════════╝${NC}"
echo ""

# Vérifier que nous sommes dans le bon répertoire
if [ ! -f "${SCRIPT_DIR}/build.spec" ]; then
    echo -e "${RED}✗ Erreur: Ce script doit être exécuté depuis le répertoire creation-build${NC}"
    exit 1
fi

# Option pour l'icône
if [ "$1" == "--with-icon" ] && [ -n "$2" ]; then
    ICON_PNG="$2"
    if [ ! -f "$ICON_PNG" ]; then
        # Essayer depuis le répertoire parent
        ICON_PNG="${PROJECT_ROOT}/${2}"
        if [ ! -f "$ICON_PNG" ]; then
            echo -e "${RED}✗ Erreur: Fichier icône non trouvé: $2${NC}"
            exit 1
        fi
    fi
    echo -e "${GREEN}📦 Conversion de l'icône...${NC}"
    "${SCRIPT_DIR}/create_icon.sh" "$ICON_PNG" "${SCRIPT_DIR}/app_icon.icns"
    echo ""
fi

# Nettoyer
echo -e "${GREEN}🧹 Nettoyage des anciens builds...${NC}"
cd "$SCRIPT_DIR"
python setup.py clean
echo ""

# Build
echo -e "${GREEN}🔨 Construction de l'application...${NC}"
python setup.py build
echo ""

# Créer le DMG
echo -e "${GREEN}📦 Création du DMG...${NC}"
"${SCRIPT_DIR}/build_dmg.sh"
echo ""

echo -e "${GREEN}╔═══════════════════════════════════════════════════════════╗${NC}"
echo -e "${GREEN}║     Build terminé avec succès!                            ║${NC}"
echo -e "${GREEN}╚═══════════════════════════════════════════════════════════╝${NC}"
echo ""
echo -e "Fichiers créés:"
echo -e "  ${GREEN}${PROJECT_ROOT}/dist/ScrapersShopify.app${NC}"
echo -e "  ${GREEN}${PROJECT_ROOT}/dist/ScrapersShopify_MacIntel.dmg${NC}"
echo ""
