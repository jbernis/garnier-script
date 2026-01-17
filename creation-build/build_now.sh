#!/bin/bash
# Script pour créer le DMG maintenant

set -e

cd "$(dirname "$0")"
PROJECT_ROOT="$(cd .. && pwd)"

echo "╔═══════════════════════════════════════════════════════════╗"
echo "║     Build DMG pour Mac Intel                              ║"
echo "╚═══════════════════════════════════════════════════════════╝"
echo ""

# Vérifier si une icône existe
ICON_FOUND=""
if [ -f "$PROJECT_ROOT/icon.png" ]; then
    ICON_FOUND="$PROJECT_ROOT/icon.png"
elif [ -f "$PROJECT_ROOT/app_icon.png" ]; then
    ICON_FOUND="$PROJECT_ROOT/app_icon.png"
elif [ -f "icon.png" ]; then
    ICON_FOUND="icon.png"
elif [ -f "app_icon.png" ]; then
    ICON_FOUND="app_icon.png"
fi

# Convertir l'icône si trouvée
if [ -n "$ICON_FOUND" ]; then
    echo "📦 Conversion de l'icône trouvée: $ICON_FOUND"
    ./create_icon.sh "$ICON_FOUND" app_icon.icns
    echo ""
else
    echo "⚠ Aucune icône trouvée. Le build continuera sans icône personnalisée."
    echo "  (Placez votre icône PNG dans le projet et relancez si nécessaire)"
    echo ""
fi

# Nettoyer
echo "🧹 Nettoyage..."
python3 setup.py clean
echo ""

# Build
echo "🔨 Construction de l'application..."
python3 setup.py build
echo ""

# Créer le DMG
echo "📦 Création du DMG..."
./build_dmg.sh
echo ""

echo "╔═══════════════════════════════════════════════════════════╗"
echo "║     Build terminé!                                        ║"
echo "╚═══════════════════════════════════════════════════════════╝"
echo ""
echo "Fichiers créés:"
echo "  $PROJECT_ROOT/dist/ScrapersShopify.app"
echo "  $PROJECT_ROOT/dist/ScrapersShopify_MacIntel.dmg"
echo ""
