# Guide d'installation et d'exécution

Ce guide vous explique étape par étape comment configurer et exécuter le script de scraping.

## Procédure complète

### Étape 1 : Vérifier Python

Vérifiez que Python 3.8+ est installé :

```bash
python3 --version
# ou
python --version
```

Si Python n'est pas installé, téléchargez-le depuis [python.org](https://www.python.org/downloads/).

### Étape 2 : Créer l'environnement virtuel

Créez un environnement virtuel pour isoler les dépendances du projet :

**macOS/Linux:**
```bash
cd /Users/jean-loup/shopify/garnier
python3 -m venv venv
```

**Windows:**
```bash
cd C:\chemin\vers\garnier
python -m venv venv
```

### Étape 3 : Activer l'environnement virtuel

**macOS/Linux:**
```bash
source venv/bin/activate
```

**Windows:**
```bash
venv\Scripts\activate
```

Vous devriez voir `(venv)` apparaître au début de votre ligne de commande.

### Étape 4 : Mettre à jour pip

```bash
pip install --upgrade pip
```

### Étape 5 : Installer les dépendances

```bash
pip install -r requirements.txt
```

Cela installera :
- requests
- beautifulsoup4
- pandas
- lxml
- selenium

### Étape 6 : Vérifier l'installation

Testez que tout fonctionne en listant les catégories :

```bash
python scraper.py --list-categories
```

Si vous voyez la liste des catégories, l'installation est réussie !

### Étape 7 : Exécuter le script

#### Extraire toutes les catégories :
```bash
python scraper.py
```

#### Extraire une catégorie spécifique :
```bash
python scraper.py --category "Linge de table"
```

#### Extraire plusieurs catégories :
```bash
python scraper.py --category "Linge de table" --category "Linge de lit"
```

### Étape 8 : Désactiver l'environnement virtuel

Quand vous avez terminé :

```bash
deactivate
```

## Résumé des commandes

```bash
# 1. Créer l'environnement virtuel
python3 -m venv venv

# 2. Activer l'environnement virtuel
source venv/bin/activate  # macOS/Linux
# ou
venv\Scripts\activate     # Windows

# 3. Installer les dépendances
pip install --upgrade pip
pip install -r requirements.txt

# 4. Exécuter le script
python scraper.py --list-categories  # Test
python scraper.py                    # Extraction complète
python scraper.py --category "Linge de table"  # Une catégorie

# 5. Désactiver l'environnement virtuel
deactivate
```

## Dépannage

### Erreur "python3: command not found"
- Sur Windows, utilisez `python` au lieu de `python3`
- Vérifiez que Python est dans votre PATH

### Erreur "pip: command not found"
- Utilisez `python -m pip` au lieu de `pip`
- Ou réinstallez Python avec l'option "Add Python to PATH"

### Erreur avec ChromeDriver
- Assurez-vous que Chrome/Chromium est installé
- Selenium 4.6+ devrait installer ChromeDriver automatiquement
- Sinon, installez-le manuellement (voir README.md)

### Erreur d'authentification
- Vérifiez que les identifiants dans `scraper.py` sont corrects
- Vérifiez votre connexion internet
- Consultez les logs pour plus de détails

## Structure des fichiers après exécution

```
garnier/
├── venv/                    # Environnement virtuel (ne pas modifier)
├── images/                  # Images téléchargées
│   ├── 51298_0.jpg
│   └── ...
├── shopify_import.csv       # Fichier CSV généré
├── scraper.py               # Script principal
├── requirements.txt         # Dépendances
├── README.md                # Documentation
└── SETUP.md                 # Ce fichier
```

## Notes importantes

- **Toujours activer l'environnement virtuel** avant d'exécuter le script
- Les images sont téléchargées dans `images/` mais le CSV contient les URLs
- Le fichier CSV peut être importé directement dans Shopify
- Les logs détaillent chaque étape du processus

