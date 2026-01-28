#!/bin/bash
# Script post-build pour copier l'icône personnalisée

echo "📦 Post-build: copie de l'icône personnalisée..."

# Chemins
ICON_SOURCE="creation-build/app_icon.icns"
ICON_TARGET="dist/ScrapersShopify.app/Contents/Resources/icon-windowed.icns"

# Vérifier que l'icône source existe
if [ ! -f "$ICON_SOURCE" ]; then
    echo "❌ Erreur: Icône source introuvable: $ICON_SOURCE"
    exit 1
fi

# Vérifier que l'app existe
if [ ! -d "dist/ScrapersShopify.app" ]; then
    echo "❌ Erreur: Application introuvable: dist/ScrapersShopify.app"
    exit 1
fi

# Copier l'icône
cp "$ICON_SOURCE" "$ICON_TARGET"
if [ $? -eq 0 ]; then
    echo "✅ Icône copiée avec succès: $ICON_TARGET"
    
    # Touch l'app pour forcer macOS à recharger les métadonnées
    touch dist/ScrapersShopify.app
    echo "✅ App actualisée (touch)"
else
    echo "❌ Erreur lors de la copie de l'icône"
    exit 1
fi

echo "✨ Post-build terminé !"
