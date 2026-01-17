#!/bin/bash
# Script complet pour créer le DMG avec l'icône JPG

set -e

cd "$(dirname "$0")"
PROJECT_ROOT="$(cd .. && pwd)"
ICON_JPG="/Users/jean-loup/Downloads/icon_1200x1200_optimized.jpg"

echo "╔═══════════════════════════════════════════════════════════╗"
echo "║     Build DMG avec icône                                 ║"
echo "╚═══════════════════════════════════════════════════════════╝"
echo ""

# Vérifier que l'icône existe
if [ ! -f "$ICON_JPG" ]; then
    echo "❌ Erreur: L'icône n'existe pas: $ICON_JPG"
    exit 1
fi

echo "✓ Icône trouvée: $ICON_JPG"
echo ""

# Étape 1: Convertir JPG en PNG
echo "📦 Étape 1/5: Conversion JPG -> PNG..."
ICON_PNG="icon_temp.png"
sips -s format png "$ICON_JPG" --out "$ICON_PNG" > /dev/null 2>&1
if [ ! -f "$ICON_PNG" ]; then
    echo "❌ Erreur lors de la conversion JPG -> PNG"
    exit 1
fi
echo "✓ Conversion réussie"
echo ""

# Étape 2: Convertir PNG en .icns
echo "📦 Étape 2/5: Conversion PNG -> .icns..."
./create_icon.sh "$ICON_PNG" app_icon.icns
if [ ! -f "app_icon.icns" ]; then
    echo "❌ Erreur lors de la conversion PNG -> .icns"
    rm -f "$ICON_PNG"
    exit 1
fi
echo "✓ Icône .icns créée"
echo ""

# Nettoyer le PNG temporaire
rm -f "$ICON_PNG"
echo "✓ Fichier temporaire supprimé"
echo ""

# Étape 3: Nettoyer les anciens builds
echo "🧹 Étape 3/5: Nettoyage des anciens builds..."
python3 setup.py clean
echo ""

# Étape 4: Construire l'application
echo "🔨 Étape 4/5: Construction de l'application..."
echo "   (Cela peut prendre plusieurs minutes...)"
python3 setup.py build
if [ ! -d "$PROJECT_ROOT/dist/ScrapersShopify.app" ]; then
    echo "❌ Erreur: L'application n'a pas été créée"
    exit 1
fi
echo "✓ Application créée: $PROJECT_ROOT/dist/ScrapersShopify.app"
echo ""

# Étape 5: Créer le DMG
echo "📦 Étape 5/5: Création du DMG..."
./build_dmg.sh
if [ ! -f "$PROJECT_ROOT/dist/ScrapersShopify_MacIntel.dmg" ]; then
    echo "❌ Erreur: Le DMG n'a pas été créé"
    exit 1
fi
echo ""

DMG_SIZE=$(du -h "$PROJECT_ROOT/dist/ScrapersShopify_MacIntel.dmg" | cut -f1)

echo "╔═══════════════════════════════════════════════════════════╗"
echo "║     ✅ Build terminé avec succès!                        ║"
echo "╚═══════════════════════════════════════════════════════════╝"
echo ""
echo "📦 Fichiers créés:"
echo "   Application: $PROJECT_ROOT/dist/ScrapersShopify.app"
echo "   DMG:        $PROJECT_ROOT/dist/ScrapersShopify_MacIntel.dmg ($DMG_SIZE)"
echo ""
echo "🎉 Vous pouvez maintenant distribuer le fichier DMG!"
echo ""
