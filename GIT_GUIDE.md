# 📦 Guide Git - Scrapers Shopify

## 🎯 Fichiers versionnés (minimum pour que ça marche)

### ✅ CODE SOURCE (essentiel)
```
├── apps/                    # Toute l'application GUI
├── garnier/                 # Scripts Garnier
├── artiga/                  # Scripts Artiga
├── cristel/                # Scripts Cristel
├── scrapers/               # Wrappers des scrapers
├── utils/                  # Utilitaires
├── run_gui.py              # Point d'entrée GUI
├── run_gui.sh              # Script de lancement
├── scraper-*.py            # Scripts de scraping
└── requirements.txt        # Dépendances Python
```

### ✅ CONFIGURATION
```
├── .env.example            # Exemple de configuration (PAS .env)
├── google_taxonomy.txt     # Taxonomie Google
└── creation-build/
    ├── build.spec          # Config PyInstaller
    ├── build_all.sh        # Script de build
    └── app_icon.icns       # Icône de l'app
```

### ✅ STRUCTURE VIDE
```
├── database/.gitkeep       # Préserve le dossier (mais pas les .db)
└── outputs/.gitkeep        # Préserve le dossier (mais pas les CSV)
```

---

## 🚫 Fichiers IGNORÉS (générés automatiquement)

### ❌ DONNÉES GÉNÉRÉES
- `database/*.db` - Bases de données (régénérées à l'utilisation)
- `outputs/` - Fichiers CSV générés
- `*.csv` - Tous les CSV

### ❌ PYTHON
- `__pycache__/`, `*.pyc` - Bytecode Python
- `venv/` - Environnement virtuel

### ❌ BUILD
- `creation-build/dist/` - App compilée
- `creation-build/build/` - Fichiers temporaires de build
- `*.app`, `*.dmg` - Applications macOS

### ❌ CREDENTIALS
- `.env` - Variables d'environnement (CREDENTIALS SENSIBLES !)

### ❌ TEMPORAIRES
- `*.log`, `*.tmp` - Logs et fichiers temporaires
- `.DS_Store` - Fichiers macOS
- `.vscode/`, `.idea/` - Config IDE

---

## 🧹 Nettoyer le cache Git

Si tu as déjà commité des fichiers qui sont maintenant dans `.gitignore`, utilise le script :

```bash
./clean_git_cache.sh
```

Ce script :
1. ✅ Supprime les fichiers du **tracking Git** (mais pas du disque)
2. ✅ Garde les fichiers essentiels
3. ✅ Affiche un résumé des changements

Ensuite, commit les changements :

```bash
git add .gitignore database/.gitkeep outputs/.gitkeep
git commit -m "Update .gitignore and remove tracked generated files"
```

---

## 📥 Cloner et installer le projet

### 1. Cloner le repo
```bash
git clone <ton-repo-url>
cd garnier
```

### 2. Installer les dépendances
```bash
./run_gui.sh
```

Le script `run_gui.sh` va automatiquement :
- ✅ Créer l'environnement virtuel
- ✅ Installer les dépendances depuis `requirements.txt`
- ✅ Lancer l'application

### 3. Configurer les credentials
```bash
cp .env.example .env
nano .env  # Éditer et ajouter tes credentials
```

### 4. Les bases de données seront créées automatiquement
Au premier lancement, l'app créera :
- `database/garnier_products.db`
- `database/artiga_products.db`
- `database/cristel_products.db`
- `database/ai_prompts.db`

---

## 📋 Workflow Git recommandé

### Avant de commiter
```bash
# Vérifier ce qui a changé
git status

# Ajouter seulement le code source
git add apps/ scrapers/ utils/ garnier/ artiga/ cristel/
git add run_gui.py run_gui.sh requirements.txt

# NE PAS ajouter les .db, outputs/, .env
```

### Commit
```bash
git commit -m "Description des changements"
```

### Push
```bash
git push origin main
```

---

## 🔒 SÉCURITÉ : Ne JAMAIS commiter

- ❌ `.env` - Contient tes **credentials** (username, password, API keys)
- ❌ `database/*.db` - Peuvent contenir des données sensibles
- ❌ `outputs/*.csv` - Peuvent contenir des prix et données commerciales

---

## 💡 Astuces

### Vérifier ce qui serait ignoré
```bash
git status --ignored
```

### Voir les fichiers trackés
```bash
git ls-files
```

### Forcer l'ajout d'un fichier ignoré (si vraiment nécessaire)
```bash
git add -f fichier_ignoré.txt
```

---

## 🆘 Problèmes courants

### "J'ai commité .env par erreur !"
```bash
# Supprimer du tracking (garde le fichier sur le disque)
git rm --cached .env

# Commit la suppression
git commit -m "Remove .env from tracking"

# Push (ATTENTION: l'historique garde toujours l'ancien commit!)
git push

# Pour vraiment supprimer de l'historique (avancé):
# git filter-branch ou BFG Repo-Cleaner
```

### "Les fichiers ignorés apparaissent quand même"
```bash
# C'est qu'ils étaient déjà trackés avant le .gitignore
./clean_git_cache.sh
```

### "Je veux versionner les docs aussi"
```bash
# Éditer .gitignore et commenter ces lignes:
# # README.md
# # RESUME_*.md
# # BUILD_*.md
```

---

## 📦 Taille du repo

Avec ce `.gitignore`, ton repo Git devrait faire environ :
- **Sans données** : ~5-10 MB (code source uniquement)
- **Avec historique** : Variable selon le nombre de commits

Les fichiers lourds (bases de données, CSV) ne sont **pas** versionnés.
