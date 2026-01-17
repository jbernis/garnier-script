# Guide d'installation et d'exécution

Ce guide vous explique étape par étape comment configurer et exécuter les scripts de scraping.

## Scripts disponibles

- **`scraper-garnier.py`** : Scraper pour le site B2B Garnier-Thiebaut (authentification requise)
- **`scraper-artiga.py`** : Scraper pour le site Artiga (https://www.artiga.fr) - site public, pas d'authentification

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

### Étape 6 : Configurer les variables d'environnement

Créez un fichier `.env` à partir de `.env.example` (si disponible) ou créez-le manuellement :

```bash
# Créer le fichier .env
touch .env
```

Puis éditez le fichier `.env` avec vos identifiants :

**Pour scraper-garnier.py (Garnier-Thiebaut) :**
```env
BASE_URL_GARNIER=https://garnier-thiebaut.adsi.me
USERNAME=votre_username
PASSWORD=votre_password
OUTPUT_CSV_GARNIER=shopify_import_garnier.csv
```

**Pour scraper-artiga.py (Artiga) :**
```env
ARTIGA_BASE_URL=https://www.artiga.fr
ARTIGA_OUTPUT_CSV=shopify_import_artiga.csv
```

**Note** : Artiga est un site public, donc pas besoin d'authentification.

### Étape 7 : Vérifier l'installation

Testez que tout fonctionne en listant les catégories :

**Pour Garnier-Thiebaut :**
```bash
python scraper-garnier.py --list-categories
```

**Pour Artiga :**
```bash
python scraper-artiga.py --list-categories
```

Si vous voyez la liste des catégories, l'installation est réussie !

### Étape 8 : Exécuter les scripts

#### scraper-garnier.py (Garnier-Thiebaut)

**Extraire toutes les catégories :**
```bash
python scraper-garnier.py
```

**Extraire une catégorie spécifique :**
```bash
python scraper-garnier.py --category "Linge de table"
```

**Extraire plusieurs catégories :**
```bash
python scraper-garnier.py --category "Linge de table" --category "Linge de lit"
```

#### scraper-artiga.py (Artiga)

**Extraire toutes les catégories :**
```bash
python scraper-artiga.py
```

**Extraire une catégorie spécifique :**
```bash
python scraper-artiga.py --category "Serviettes De Table"
```

**Extraire plusieurs catégories :**
```bash
python scraper-artiga.py --category "Serviettes De Table" --category "Nappes"
```

### Étape 9 : Désactiver l'environnement virtuel

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

# 4. Configurer le .env (voir Étape 6)

# 5. Exécuter les scripts
python scraper-garnier.py --list-categories  # Test Garnier-Thiebaut
python scraper-artiga.py --list-categories  # Test Artiga
python scraper-garnier.py                    # Extraction complète Garnier-Thiebaut
python scraper-artiga.py             # Extraction complète Artiga
python scraper-garnier.py --category "Linge de table"  # Une catégorie Garnier-Thiebaut
python scraper-artiga.py --category "Serviettes De Table"  # Une catégorie Artiga

# 6. Désactiver l'environnement virtuel
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

### Erreur d'authentification (scraper-garnier.py uniquement)
- Vérifiez que les identifiants dans `.env` sont corrects
- Vérifiez votre connexion internet
- Consultez les logs pour plus de détails

### Aucun produit trouvé (scraper-artiga.py)
- Vérifiez que le nom de la catégorie correspond exactement (utilisez `--list-categories`)
- Utilisez `--no-headless` pour voir ce qui se passe dans le navigateur
- Vérifiez votre connexion internet

## Structure des fichiers après exécution

```
garnier/
├── venv/                    # Environnement virtuel (ne pas modifier)
├── .env                     # Variables d'environnement (credentials)
├── shopify_import*.csv      # Fichiers CSV générés
├── scraper-garnier.py       # Script principal Garnier-Thiebaut
├── scraper-artiga.py        # Script principal Artiga
├── requirements.txt         # Dépendances
├── README.md                # Documentation
└── SETUP.md                 # Ce fichier
```

## Notes importantes

- **Toujours activer l'environnement virtuel** avant d'exécuter les scripts
- **scraper-garnier.py** nécessite des identifiants dans `.env` (USERNAME, PASSWORD, BASE_URL_GARNIER, OUTPUT_CSV_GARNIER)
- **scraper-artiga.py** ne nécessite pas d'authentification (site public, utilise ARTIGA_BASE_URL et ARTIGA_OUTPUT_CSV)
- Les images ne sont pas téléchargées localement, le CSV contient les URLs complètes
- Le fichier CSV peut être importé directement dans Shopify
- Les logs détaillent chaque étape du processus
- Les noms de fichiers CSV sont générés automatiquement avec la catégorie et la date/heure

