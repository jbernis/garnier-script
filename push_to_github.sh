#!/bin/bash
# Script pour pousser le projet vers GitHub

set -e

cd "$(dirname "$0")"

echo "╔═══════════════════════════════════════════════════════════╗"
echo "║     Push vers GitHub                                      ║"
echo "╚═══════════════════════════════════════════════════════════╝"
echo ""

# Vérifier que .env n'est pas commité
if git ls-files | grep -q "\.env$"; then
    echo "⚠ ATTENTION: .env est dans les fichiers suivis!"
    echo "  Suppression de .env de l'index Git..."
    git rm --cached .env 2>/dev/null || true
fi

# Vérifier que app_config.json n'est pas commité (contient des chemins locaux)
if git ls-files | grep -q "app_config.json$"; then
    echo "⚠ app_config.json est dans les fichiers suivis (normal si c'est la config par défaut)"
fi

# Initialiser Git si nécessaire
if [ ! -d ".git" ]; then
    echo "📦 Initialisation du dépôt Git..."
    git init
fi

# Ajouter le remote
echo "🔗 Configuration du remote GitHub..."
git remote remove origin 2>/dev/null || true
git remote add origin https://github.com/jbernis/garnier-script.git

# Ajouter tous les fichiers (sauf ceux dans .gitignore)
echo "📝 Ajout des fichiers..."
git add .

# Vérifier ce qui va être commité
echo ""
echo "📋 Fichiers à commiter:"
git status --short | head -20
echo ""

# Demander confirmation
read -p "Continuer avec le commit? (o/n) " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Oo]$ ]]; then
    echo "Annulé."
    exit 1
fi

# Commit
echo ""
echo "💾 Création du commit..."
git commit -m "Mise à jour: ajout des scripts de build Mac Intel et améliorations" || {
    echo "⚠ Aucun changement à commiter (ou commit déjà fait)"
}

# Push
echo ""
echo "🚀 Push vers GitHub..."
git branch -M main 2>/dev/null || true
git push -u origin main || {
    echo ""
    echo "❌ Erreur lors du push. Essayez:"
    echo "   git push -u origin main --force"
    echo ""
    echo "Ou si c'est la première fois:"
    echo "   git push -u origin main"
    exit 1
}

echo ""
echo "╔═══════════════════════════════════════════════════════════╗"
echo "║     ✅ Push réussi!                                       ║"
echo "╚═══════════════════════════════════════════════════════════╝"
echo ""
echo "🌐 Votre code est maintenant sur:"
echo "   https://github.com/jbernis/garnier-script"
echo ""
