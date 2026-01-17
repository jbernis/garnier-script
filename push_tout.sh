#!/bin/bash
# Script ultra-simple pour tout pousser sur GitHub

cd /Users/jean-loup/shopify/garnier

echo "🚀 Push de TOUT vers GitHub..."
echo ""

# Initialiser Git
[ ! -d ".git" ] && git init

# Remote
git remote remove origin 2>/dev/null
git remote add origin https://github.com/jbernis/garnier-script.git 2>/dev/null || git remote set-url origin https://github.com/jbernis/garnier-script.git

# Tout ajouter
echo "📦 Ajout de tous les fichiers..."
git add .

# Commit
echo "💾 Commit..."
git commit -m "Mise à jour complète du projet" 2>&1 | grep -v "nothing to commit" || echo "✓ Fichiers ajoutés"

# Push
echo "🚀 Push..."
git branch -M main
git push -u origin main 2>&1 || {
    echo ""
    echo "⚠ Si erreur, essayez: git push -u origin main --force"
}

echo ""
echo "✅ Terminé! Vérifiez: https://github.com/jbernis/garnier-script"
