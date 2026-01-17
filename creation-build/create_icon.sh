#!/bin/bash
# Script pour convertir une icône PNG en format .icns pour macOS

set -e  # Arrêter en cas d'erreur

# Couleurs pour les messages
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}╔═══════════════════════════════════════════════════════════╗${NC}"
echo -e "${GREEN}║     Création de l'icône .icns pour macOS                 ║${NC}"
echo -e "${GREEN}╚═══════════════════════════════════════════════════════════╝${NC}"
echo ""

# Vérifier les arguments
if [ $# -eq 0 ]; then
    echo -e "${YELLOW}Usage: $0 <fichier_png> [nom_sortie]${NC}"
    echo ""
    echo "Exemples:"
    echo "  $0 icon.png"
    echo "  $0 icon.png app_icon.icns"
    echo ""
    echo "Le fichier PNG doit être carré (recommandé: 1024x1024 pixels)"
    exit 1
fi

PNG_FILE="$1"
OUTPUT_NAME="${2:-app_icon.icns}"

# Vérifier que le fichier PNG existe
if [ ! -f "$PNG_FILE" ]; then
    echo -e "${RED}✗ Erreur: Le fichier ${PNG_FILE} n'existe pas${NC}"
    exit 1
fi

# Vérifier que sips est disponible (macOS uniquement)
if ! command -v sips &> /dev/null; then
    echo -e "${RED}✗ Erreur: sips n'est pas disponible (macOS uniquement)${NC}"
    exit 1
fi

# Vérifier que iconutil est disponible
if ! command -v iconutil &> /dev/null; then
    echo -e "${RED}✗ Erreur: iconutil n'est pas disponible${NC}"
    exit 1
fi

echo -e "${GREEN}✓ Fichier source: ${PNG_FILE}${NC}"
echo -e "${GREEN}✓ Fichier de sortie: ${OUTPUT_NAME}${NC}"
echo ""

# Créer le répertoire temporaire pour l'iconset
ICONSET_DIR="icon.iconset"
rm -rf "$ICONSET_DIR"
mkdir -p "$ICONSET_DIR"

echo -e "${GREEN}📦 Génération des différentes tailles d'icônes...${NC}"

# Générer toutes les tailles nécessaires pour macOS
sips -z 16 16     "$PNG_FILE" --out "${ICONSET_DIR}/icon_16x16.png" > /dev/null 2>&1
sips -z 32 32     "$PNG_FILE" --out "${ICONSET_DIR}/icon_16x16@2x.png" > /dev/null 2>&1
sips -z 32 32     "$PNG_FILE" --out "${ICONSET_DIR}/icon_32x32.png" > /dev/null 2>&1
sips -z 64 64     "$PNG_FILE" --out "${ICONSET_DIR}/icon_32x32@2x.png" > /dev/null 2>&1
sips -z 128 128   "$PNG_FILE" --out "${ICONSET_DIR}/icon_128x128.png" > /dev/null 2>&1
sips -z 256 256   "$PNG_FILE" --out "${ICONSET_DIR}/icon_128x128@2x.png" > /dev/null 2>&1
sips -z 256 256   "$PNG_FILE" --out "${ICONSET_DIR}/icon_256x256.png" > /dev/null 2>&1
sips -z 512 512   "$PNG_FILE" --out "${ICONSET_DIR}/icon_256x256@2x.png" > /dev/null 2>&1
sips -z 512 512   "$PNG_FILE" --out "${ICONSET_DIR}/icon_512x512.png" > /dev/null 2>&1
sips -z 1024 1024 "$PNG_FILE" --out "${ICONSET_DIR}/icon_512x512@2x.png" > /dev/null 2>&1

echo -e "${GREEN}✓ Toutes les tailles générées${NC}"

# Convertir l'iconset en .icns
echo -e "${GREEN}🔨 Conversion en format .icns...${NC}"
iconutil -c icns "$ICONSET_DIR" -o "$OUTPUT_NAME"

# Nettoyer le répertoire temporaire
rm -rf "$ICONSET_DIR"

# Vérifier que le fichier .icns a été créé
if [ -f "$OUTPUT_NAME" ]; then
    ICNS_SIZE=$(du -h "$OUTPUT_NAME" | cut -f1)
    echo ""
    echo -e "${GREEN}╔═══════════════════════════════════════════════════════════╗${NC}"
    echo -e "${GREEN}║     Icône créée avec succès!                             ║${NC}"
    echo -e "${GREEN}╚═══════════════════════════════════════════════════════════╝${NC}"
    echo ""
    echo -e "Fichier créé: ${GREEN}${OUTPUT_NAME}${NC}"
    echo -e "Taille: ${ICNS_SIZE}"
    echo ""
    echo -e "L'icône est maintenant prête à être utilisée dans build.spec"
else
    echo -e "${RED}✗ Erreur: Le fichier .icns n'a pas pu être créé${NC}"
    exit 1
fi
