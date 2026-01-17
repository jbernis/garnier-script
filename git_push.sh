#!/bin/bash
# Script simple pour pousser sur GitHub

cd "$(dirname "$0")"

echo "🚀 Push vers GitHub..."
echo ""

# Initialiser Git si nécessaire
if [ ! -d ".git" ]; then
    git init
fi

# Configurer le remote
git remote remove origin 2>/dev/null || true
git remote add origin https://github.com/jbernis/garnier-script.git 2>/dev/null || git remote set-url origin https://github.com/jbernis/garnier-script.git

# S'assurer que .env n'est pas commité
git rm --cached .env 2>/dev/null || true

# Ajouter tous les fichiers
echo "📝 Ajout des fichiers..."
git add .

# Commit
echo "💾 Création du commit..."
git commit -m "Mise à jour complète: scripts de build Mac Intel, interface graphique, scrapers multi-sites (Garnier, Artiga, Cristel), et toutes les fonctionnalités" || echo "Aucun changement à commiter"

# Push
echo "🚀 Push vers GitHub..."
git branch -M main
git push -u origin main || {
    echo ""
    echo "⚠ Si le push échoue, essayez:"
    echo "   git push -u origin main --force"
}

echo ""
echo "✅ Terminé!"
