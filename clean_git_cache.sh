#!/bin/bash

# Script pour nettoyer le cache Git des fichiers maintenant ignorés
# Les fichiers restent sur le disque, mais ne sont plus trackés par Git

echo "🧹 Nettoyage du cache Git..."
echo ""

# Supprimer les bases de données du tracking
echo "📦 Suppression des bases de données (.db)..."
git rm --cached database/*.db 2>/dev/null || echo "   Aucune DB à supprimer"
git rm --cached garnier_products.db 2>/dev/null || echo "   garnier_products.db déjà supprimé"

# Supprimer les outputs du tracking
echo "📂 Suppression du dossier outputs/..."
git rm -r --cached outputs/ 2>/dev/null || echo "   outputs/ déjà supprimé"

# Supprimer les CSV générés du tracking
echo "📄 Suppression des fichiers CSV générés..."
git rm --cached *.csv 2>/dev/null || echo "   Aucun CSV à supprimer"
git rm --cached shopify_import*.csv 2>/dev/null || echo "   Aucun shopify_import CSV"

# Supprimer les fichiers temporaires
echo "🗑️  Suppression des fichiers temporaires..."
git rm --cached *.log 2>/dev/null || echo "   Aucun log"
git rm --cached *.tmp 2>/dev/null || echo "   Aucun tmp"
git rm --cached **/*.pyc 2>/dev/null || echo "   Aucun pyc"

# Supprimer les fichiers de backup
echo "💾 Suppression des backups..."
git rm --cached **/*.bak 2>/dev/null || echo "   Aucun backup"
git rm --cached *.bak 2>/dev/null || echo "   Aucun backup racine"

# Supprimer les fichiers macOS
echo "🍎 Suppression des fichiers macOS..."
git rm --cached .DS_Store 2>/dev/null || echo "   Pas de .DS_Store"
git rm --cached **/.DS_Store 2>/dev/null || echo "   Pas de .DS_Store récursif"

echo ""
echo "✅ Nettoyage terminé !"
echo ""
echo "📋 Les fichiers suivants ne sont plus trackés par Git :"
git status --short
echo ""
echo "💡 Pour finaliser, fais un commit :"
echo "   git add .gitignore"
echo "   git commit -m 'Update .gitignore and remove tracked generated files'"
