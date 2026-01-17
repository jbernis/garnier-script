#!/bin/bash
# Script pour pousser TOUT le projet vers GitHub (scripts inclus)

set -e

cd "$(dirname "$0")"

echo "╔═══════════════════════════════════════════════════════════╗"
echo "║     Push COMPLET vers GitHub (tous les scripts)          ║"
echo "╚═══════════════════════════════════════════════════════════╝"
echo ""

# Vérifier que les fichiers sensibles ne sont pas commités
echo "🔒 Vérification de la sécurité..."

# S'assurer que .env n'est pas dans l'index
if git ls-files 2>/dev/null | grep -q "\.env$"; then
    echo "  ⚠ Suppression de .env de l'index Git (ne doit pas être commité)"
    git rm --cached .env 2>/dev/null || true
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

# Ajouter TOUS les fichiers (sauf ceux explicitement dans .gitignore)
echo "📝 Ajout de tous les fichiers..."
echo ""
echo "Fichiers qui seront inclus:"
echo "  ✓ Tous les scripts Python (.py)"
echo "  ✓ Scripts de build (creation-build/)"
echo "  ✓ Configuration (JSON, config files)"
echo "  ✓ Documentation (README, MD files)"
echo "  ✓ Requirements (requirements.txt)"
echo ""
echo "Fichiers exclus (via .gitignore):"
echo "  ✗ .env (credentials)"
echo "  ✗ venv/ (environnement virtuel)"
echo "  ✗ __pycache__/ (cache Python)"
echo "  ✗ build/ et dist/ (fichiers de build)"
echo "  ✗ *.dmg et *.app (fichiers compilés)"
echo "  ✗ images/ (images téléchargées)"
echo "  ✗ *.csv (fichiers CSV générés)"
echo ""

# Ajouter tous les fichiers
git add .

# Afficher un résumé de ce qui va être commité
echo "📋 Résumé des fichiers à commiter:"
echo ""
git status --short | head -50
echo ""
echo "... (il peut y avoir plus de fichiers)"
echo ""

# Compter les fichiers
FILE_COUNT=$(git status --short | wc -l | tr -d ' ')
echo "📊 Total: $FILE_COUNT fichiers/modifications"
echo ""

# Demander confirmation
read -p "Continuer avec le commit et le push? (o/n) " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Oo]$ ]]; then
    echo "❌ Annulé par l'utilisateur."
    exit 1
fi

# Commit
echo ""
echo "💾 Création du commit..."
COMMIT_MSG="Mise à jour complète: scripts de build Mac Intel, interface graphique, scrapers multi-sites (Garnier, Artiga, Cristel), et toutes les fonctionnalités"

if git diff --cached --quiet; then
    echo "⚠ Aucun changement à commiter (tout est déjà à jour)"
else
    git commit -m "$COMMIT_MSG"
    echo "✓ Commit créé"
fi

# Push
echo ""
echo "🚀 Push vers GitHub..."
git branch -M main 2>/dev/null || true

# Essayer le push normal d'abord
if git push -u origin main 2>&1; then
    echo ""
    echo "╔═══════════════════════════════════════════════════════════╗"
    echo "║     ✅ Push réussi!                                       ║"
    echo "╚═══════════════════════════════════════════════════════════╝"
    echo ""
    echo "🌐 Votre code est maintenant sur:"
    echo "   https://github.com/jbernis/garnier-script"
    echo ""
    echo "📦 Fichiers inclus:"
    echo "   • Tous les scripts Python"
    echo "   • Scripts de build (creation-build/)"
    echo "   • Configuration et documentation"
    echo "   • Requirements et dépendances"
    echo ""
else
    echo ""
    echo "⚠ Le push a échoué. Cela peut être normal si:"
    echo "   • C'est la première fois et le dépôt GitHub n'est pas vide"
    echo "   • Il y a des conflits"
    echo ""
    echo "Options:"
    echo ""
    echo "1. Si c'est la première fois et vous voulez écraser GitHub:"
    echo "   git push -u origin main --force"
    echo ""
    echo "2. Si vous voulez fusionner avec ce qui existe:"
    echo "   git pull origin main --allow-unrelated-histories"
    echo "   git push -u origin main"
    echo ""
    read -p "Voulez-vous essayer avec --force? (o/n) " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Oo]$ ]]; then
        git push -u origin main --force
        echo ""
        echo "✅ Push avec --force réussi!"
    else
        echo "❌ Push annulé. Exécutez les commandes manuellement si nécessaire."
        exit 1
    fi
fi
