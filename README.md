# Scraper Shopify CSV Generator

Script Python pour extraire les produits du site B2B Garnier-Thiebaut et générer un fichier CSV d'importation Shopify.

## Installation

### Prérequis

- Python 3.8 ou supérieur
- Chrome ou Chromium installé (pour Selenium)
- ChromeDriver (sera installé automatiquement par Selenium 4.6+)

### Procédure d'installation avec environnement virtuel (recommandé)

#### 1. Créer un environnement virtuel

**macOS/Linux:**
```bash
# Créer l'environnement virtuel
python3 -m venv venv

# Activer l'environnement virtuel
source venv/bin/activate
```

**Windows:**
```bash
# Créer l'environnement virtuel
python -m venv venv

# Activer l'environnement virtuel
venv\Scripts\activate
```

#### 2. Installer les dépendances

Une fois l'environnement virtuel activé (vous verrez `(venv)` dans votre terminal), installez les dépendances :

```bash
pip install --upgrade pip
pip install -r requirements.txt
```

#### 3. Configurer les credentials

Créez un fichier `.env` à partir de `.env.example` :

```bash
cp .env.example .env
```

Puis éditez le fichier `.env` et remplissez vos identifiants :

```env
BASE_URL=https://garnier-thiebaut.adsi.me
USERNAME=votre_username
PASSWORD=votre_password
OUTPUT_CSV=shopify_import.csv
```

**Note importante** : Le nom du fichier CSV sera automatiquement généré avec la catégorie et la date/heure. Le format est : `{base}_{categorie}_{date_heure}.csv`

**Exemples de noms générés :**

- **Une catégorie** : `shopify_import_linge-de-table_20260105_183045.csv`
- **Plusieurs catégories** : `shopify_import_linge-de-table_linge-de-lit_linge-de-bain_20260105_183045.csv`
- **Toutes les catégories** (sans spécifier de catégorie) : `shopify_import_20260105_183045.csv`
- **Avec --output personnalisé** : Le nom spécifié est utilisé tel quel (sans date/heure)

Le format de la date/heure est `YYYYMMDD_HHMMSS` (exemple : `20260105_183045` = 5 janvier 2026 à 18:30:45).

#### 4. Vérifier l'installation

```bash
python scraper.py --list-categories
```

Si tout fonctionne, vous devriez voir la liste des catégories disponibles.

#### 4. Désactiver l'environnement virtuel (quand vous avez terminé)

```bash
deactivate
```

### Installation sans environnement virtuel (non recommandé)

Si vous préférez installer directement dans votre environnement Python global :

```bash
pip install -r requirements.txt
```

**Note** : L'utilisation d'un environnement virtuel est fortement recommandée pour éviter les conflits avec d'autres projets Python.

### Installation de ChromeDriver (si nécessaire)

Selenium 4.6+ installe automatiquement ChromeDriver. Si vous rencontrez des problèmes :

**macOS:**
```bash
brew install chromedriver
```

**Linux:**
```bash
# Télécharger depuis https://chromedriver.chromium.org/
# Ou utiliser votre gestionnaire de paquets
sudo apt-get install chromium-chromedriver  # Ubuntu/Debian
```

**Windows:**
Télécharger depuis https://chromedriver.chromium.org/ et ajouter au PATH.

## Utilisation

### Extraire toutes les catégories

```bash
python scraper.py
```

### Extraire une catégorie spécifique

```bash
python scraper.py --category "Linge de table"
```

### Extraire plusieurs catégories

```bash
python scraper.py --category "Linge de table" --category "Linge de lit" --category "Linge de bain"
```

### Lister toutes les catégories disponibles

```bash
python scraper.py --list-categories
```

### Spécifier un fichier de sortie personnalisé

```bash
python scraper.py --category "Linge de table" --output "linge_table.csv"
```

### Afficher un aperçu du DataFrame avant de sauvegarder

```bash
python scraper.py --category "Linge de table" --preview
```

Affiche les 10 premières lignes par défaut. Pour afficher plus de lignes :

```bash
python scraper.py --category "Linge de table" --preview --preview-rows 20
```

### Limiter le nombre de produits à extraire (pour tests rapides)

```bash
# Extraire seulement les 5 premiers produits
python scraper.py --category "Linge de table" --limit 5

# Combiner avec preview pour tester rapidement
python scraper.py --category "Linge de table" --limit 3 --preview --no-headless
```

### Options disponibles

- `--category` ou `-c` : Nom de la catégorie à extraire (peut être utilisé plusieurs fois)
- `--list-categories` ou `-l` : Lister toutes les catégories disponibles et quitter
- `--output` ou `-o` : Nom du fichier CSV de sortie (défaut: `shopify_import.csv`)
- `--preview` : Afficher un aperçu du DataFrame avant de sauvegarder le CSV
- `--preview-rows` : Nombre de lignes à afficher dans l'aperçu (défaut: 10)
- `--no-headless` : Désactiver le mode headless de Selenium (afficher le navigateur pour déboguer)
- `--limit N` : Limiter le nombre de produits à extraire (utile pour les tests rapides)

Le script va :
1. Se connecter au site avec les identifiants fournis
2. Extraire les produits des catégories sélectionnées (ou toutes si aucune sélection)
3. Pour chaque produit :
   - Extraire les détails (nom, description, variantes, prix, stock)
   - Télécharger les images
4. Générer le fichier CSV au format Shopify standard

## Configuration

Les identifiants de connexion sont configurés dans le script (`scraper.py`) :
- Code client : `164049`
- Mot de passe : `thierry`

Pour modifier ces valeurs, éditez les constantes `USERNAME` et `PASSWORD` dans le fichier `scraper.py`.

## Format du CSV généré

Le fichier CSV suit le format d'importation standard de Shopify avec les colonnes suivantes :
- Handle, Title, Body (HTML), Vendor, Type, Tags
- Variant SKU, Variant Price, Variant Compare At Price
- Variant Inventory Qty (stock)
- Image Src (URL complète de l'image depuis le site)
- Option1 Name/Value (Taille/Dimensions)
- Et toutes les autres colonnes Shopify standard

**Note** : Les images sont également téléchargées localement dans le dossier `images/` pour sauvegarde, mais le CSV contient les URLs complètes des images pour l'importation Shopify.

## Fichiers générés

- `shopify_import.csv` : Fichier CSV prêt pour l'importation dans Shopify
- `images/` : Dossier contenant toutes les images téléchargées (nommées selon le code article)

## Notes

- Le script utilise Selenium en mode headless pour gérer le JavaScript du site
- Si Selenium n'est pas disponible, le script basculera automatiquement vers requests/BeautifulSoup
- Des pauses sont intégrées entre les requêtes pour ne pas surcharger le serveur
- Les logs détaillent le processus d'extraction pour faciliter le debugging

## Guide de démarrage rapide

Pour une procédure détaillée avec environnement virtuel, consultez [SETUP.md](SETUP.md).

**Résumé rapide :**
```bash
# Créer et activer l'environnement virtuel
python3 -m venv venv
source venv/bin/activate  # macOS/Linux
# ou venv\Scripts\activate  # Windows

# Installer les dépendances
pip install --upgrade pip
pip install -r requirements.txt

# Exécuter le script
python scraper.py --list-categories  # Test
python scraper.py                     # Extraction complète
```

## Dépannage

Si le script échoue à l'authentification :
1. Vérifiez que Chrome/Chromium est installé
2. Vérifiez que les identifiants sont corrects
3. Consultez les logs pour plus de détails

Si certaines images ne sont pas téléchargées :
- Vérifiez votre connexion internet
- Les images manquantes seront ignorées mais le produit sera quand même ajouté au CSV

Pour plus d'aide, consultez [SETUP.md](SETUP.md) pour un guide complet d'installation.

