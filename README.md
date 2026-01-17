# Scraper Shopify CSV Generator

Scripts Python pour extraire les produits de sites web et générer des fichiers CSV d'importation Shopify.

## Scripts disponibles

- **`scraper-garnier.py`** : Scraper pour le site B2B Garnier-Thiebaut (authentification requise)
- **`scraper-artiga.py`** : Scraper pour le site Artiga (https://www.artiga.fr) - site public, pas d'authentification
- **`scraper-cristel.py`** : Scraper pour le site Cristel (https://www.cristel.com) - site public, pas d'authentification

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

**Pour scraper-garnier.py (Garnier-Thiebaut) :**
```env
BASE_URL_GARNIER=https://garnier-thiebaut.adsi.me
USERNAME=votre_username
PASSWORD=votre_password
OUTPUT_CSV_GARNIER=shopify_import_garnier.csv
GARNIER_OUTPUT_DIR=outputs/garnier
```

**Pour scraper-artiga.py (Artiga) :**
```env
ARTIGA_BASE_URL=https://www.artiga.fr
ARTIGA_OUTPUT_CSV=shopify_import_artiga.csv
ARTIGA_OUTPUT_DIR=outputs/artiga
```

**Pour scraper-cristel.py (Cristel) :**
```env
CRISTEL_BASE_URL=https://www.cristel.com
CRISTEL_OUTPUT_CSV=shopify_import_cristel.csv
CRISTEL_OUTPUT_DIR=outputs/cristel
```

**Note** : 
- Artiga et Cristel sont des sites publics, donc pas besoin d'authentification. Seules les variables `BASE_URL` et `OUTPUT_CSV` sont nécessaires.
- Les répertoires de sortie (`*_OUTPUT_DIR`) sont créés automatiquement s'ils n'existent pas. Vous pouvez les personnaliser dans le fichier `.env`.

**Note importante** : Le nom du fichier CSV sera automatiquement généré avec la catégorie et la date/heure. Le format est : `{base}_{categorie}_{date_heure}.csv`

**Exemples de noms générés :**

- **Une catégorie** : `shopify_import_linge-de-table_20260105_183045.csv`
- **Plusieurs catégories** : `shopify_import_linge-de-table_linge-de-lit_linge-de-bain_20260105_183045.csv`
- **Toutes les catégories** (sans spécifier de catégorie) : `shopify_import_20260105_183045.csv`
- **Avec --output personnalisé** : Le nom spécifié est utilisé tel quel (sans date/heure)

Le format de la date/heure est `YYYYMMDD_HHMMSS` (exemple : `20260105_183045` = 5 janvier 2026 à 18:30:45).

#### 4. Vérifier l'installation

**Pour Garnier-Thiebaut :**
```bash
python scraper-garnier.py --list-categories
```

**Pour Artiga :**
```bash
python scraper-artiga.py --list-categories
```

**Pour Cristel :**
```bash
python scraper-cristel.py --list-categories
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

### Script scraper-garnier.py (Garnier-Thiebaut)

#### Extraire toutes les catégories

```bash
python scraper-garnier.py
```

#### Extraire une catégorie spécifique

```bash
python scraper-garnier.py --category "Linge de table"
```

#### Extraire plusieurs catégories

```bash
python scraper-garnier.py --category "Linge de table" --category "Linge de lit" --category "Linge de bain"
```

#### Lister toutes les catégories disponibles

```bash
python scraper-garnier.py --list-categories
```

### Script scraper-artiga.py (Artiga)

#### Extraire toutes les catégories

```bash
python scraper-artiga.py
```

#### Extraire une catégorie spécifique

```bash
python scraper-artiga.py --category "Serviettes De Table"
```

#### Extraire plusieurs catégories

```bash
python scraper-artiga.py --category "Serviettes De Table" --category "Nappes"
```

#### Lister toutes les catégories disponibles

```bash
python scraper-artiga.py --list-categories
```

### Script scraper-cristel.py (Cristel)

#### Extraire toutes les catégories

```bash
python scraper-cristel.py
```

#### Extraire une catégorie spécifique

```bash
python scraper-cristel.py --category "Poêles"
```

#### Extraire plusieurs catégories

```bash
python scraper-cristel.py --category "Poêles" --category "Casseroles"
```

#### Extraire une catégorie et une sous-catégorie spécifiques

```bash
python scraper-cristel.py --category "Poêles" --subcategory "Poêles"
```

#### Lister toutes les catégories principales disponibles

```bash
python scraper-cristel.py --list-categories
```

#### Lister les sous-catégories d'une catégorie

```bash
python scraper-cristel.py --category "Poêles" --list-subcategories
```

#### Générer un fichier CSV par catégorie

```bash
python scraper-cristel.py --category "Poêles" --category "Casseroles" --per-category
```

### Spécifier un fichier de sortie personnalisé

**Garnier-Thiebaut :**
```bash
python scraper-garnier.py --category "Linge de table" --output "linge_table.csv"
```

**Artiga :**
```bash
python scraper-artiga.py --category "Serviettes De Table" --output "serviettes.csv"
```

**Cristel :**
```bash
python scraper-cristel.py --category "Poêles" --output "poeles.csv"
```

### Afficher un aperçu du DataFrame avant de sauvegarder

**Garnier-Thiebaut :**
```bash
python scraper-garnier.py --category "Linge de table" --preview
```

**Artiga :**
```bash
python scraper-artiga.py --category "Serviettes De Table" --preview
```

**Cristel :**
```bash
python scraper-cristel.py --category "Poêles" --subcategory "Poêles" --preview
```

Affiche les 10 premières lignes par défaut. Pour afficher plus de lignes :

```bash
python scraper-garnier.py --category "Linge de table" --preview --preview-rows 20
python scraper-artiga.py --category "Serviettes De Table" --preview --preview-rows 20
python scraper-cristel.py --category "Poêles" --preview --preview-rows 20
```

### Limiter le nombre de produits à extraire (pour tests rapides)

**Garnier-Thiebaut :**
```bash
# Extraire seulement les 5 premiers produits
python scraper-garnier.py --category "Linge de table" --limit 5

# Combiner avec preview pour tester rapidement
python scraper-garnier.py --category "Linge de table" --limit 3 --preview --no-headless
```

**Artiga :**
```bash
# Extraire seulement les 5 premiers produits
python scraper-artiga.py --category "Serviettes De Table" --limit 5

# Combiner avec preview pour tester rapidement
python scraper-artiga.py --category "Serviettes De Table" --limit 3 --preview --no-headless
```

**Cristel :**
```bash
# Extraire seulement les 5 premiers produits
python scraper-cristel.py --category "Poêles" --subcategory "Poêles" --limit 5

# Combiner avec preview pour tester rapidement
python scraper-cristel.py --category "Poêles" --subcategory "Poêles" --limit 3 --preview --no-headless
```

### Options disponibles

- `--category` ou `-c` : Nom de la catégorie à extraire (peut être utilisé plusieurs fois)
- `--list-categories` ou `-l` : Lister toutes les catégories disponibles et quitter
- `--output` ou `-o` : Nom du fichier CSV de sortie (défaut: `shopify_import.csv`)
- `--preview` : Afficher un aperçu du DataFrame avant de sauvegarder le CSV
- `--preview-rows` : Nombre de lignes à afficher dans l'aperçu (défaut: 10)
- `--no-headless` : Désactiver le mode headless de Selenium (afficher le navigateur pour déboguer)
- `--limit N` : Limiter le nombre de produits à extraire (utile pour les tests rapides)

**Options spécifiques à scraper-cristel.py :**
- `--subcategory` : Nom de la sous-catégorie à extraire (peut être utilisé plusieurs fois)
- `--list-subcategories` : Lister toutes les sous-catégories d'une catégorie et quitter
- `--per-category` : Générer un fichier CSV séparé pour chaque catégorie

Le script va :
1. Se connecter au site avec les identifiants fournis
2. Extraire les produits des catégories sélectionnées (ou toutes si aucune sélection)
3. Pour chaque produit :
   - Extraire les détails (nom, description, variantes, prix, stock)
   - Télécharger les images
4. Générer le fichier CSV au format Shopify standard

## Configuration

### scraper-garnier.py (Garnier-Thiebaut)

Les identifiants de connexion sont configurés dans le fichier `.env` :
- `BASE_URL_GARNIER` : URL du site (défaut: https://garnier-thiebaut.adsi.me)
- `USERNAME` : Code client
- `PASSWORD` : Mot de passe
- `OUTPUT_CSV_GARNIER` : Nom du fichier CSV par défaut (sera remplacé par le nom généré automatiquement)
- `GARNIER_OUTPUT_DIR` : Répertoire de sortie pour les fichiers CSV (défaut: `outputs/garnier`)

### scraper-artiga.py (Artiga)

Le site Artiga est public, donc pas besoin d'authentification. Les variables dans `.env` sont :
- `ARTIGA_BASE_URL` : URL du site (défaut: https://www.artiga.fr)
- `ARTIGA_OUTPUT_CSV` : Nom du fichier CSV par défaut (sera remplacé par le nom généré automatiquement)
- `ARTIGA_OUTPUT_DIR` : Répertoire de sortie pour les fichiers CSV (défaut: `outputs/artiga`)

### scraper-cristel.py (Cristel)

Le site Cristel est public, donc pas besoin d'authentification. Les variables dans `.env` sont :
- `CRISTEL_BASE_URL` : URL du site (défaut: https://www.cristel.com)
- `CRISTEL_OUTPUT_CSV` : Nom du fichier CSV par défaut (sera remplacé par le nom généré automatiquement)
- `CRISTEL_OUTPUT_DIR` : Répertoire de sortie pour les fichiers CSV (défaut: `outputs/cristel`)

**Note** : 
- Les noms de fichiers CSV sont automatiquement générés avec la catégorie et la date/heure, sauf si vous utilisez `--output` pour spécifier un nom personnalisé.
- Les répertoires de sortie sont créés automatiquement s'ils n'existent pas.
- Si vous spécifiez un chemin absolu ou un chemin avec répertoire dans `--output`, ce chemin sera utilisé tel quel (le répertoire de sortie par défaut sera ignoré).

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

### scraper-garnier.py (Garnier-Thiebaut)
- `shopify_import_garnier_{categorie}_{date_heure}.csv` : Fichier CSV prêt pour l'importation dans Shopify

### scraper-artiga.py (Artiga)
- `shopify_import_artiga_{categorie}_{date_heure}.csv` : Fichier CSV prêt pour l'importation dans Shopify

### scraper-cristel.py (Cristel)
- `shopify_import_cristel_{categorie}_{date_heure}.csv` : Fichier CSV prêt pour l'importation dans Shopify
- Avec `--per-category` : Un fichier CSV par catégorie (ex: `shopify_import_cristel_poeles_{date_heure}.csv`)

**Note** : Les images ne sont pas téléchargées localement. Le CSV contient les URLs complètes des images pour l'importation Shopify.

## Notes

### scraper-garnier.py (Garnier-Thiebaut)
- Le script utilise Selenium en mode headless pour gérer le JavaScript du site
- Authentification requise avec code client et mot de passe
- Si Selenium n'est pas disponible, le script basculera automatiquement vers requests/BeautifulSoup
- Des pauses sont intégrées entre les requêtes pour ne pas surcharger le serveur
- Les logs détaillent le processus d'extraction pour faciliter le debugging

### scraper-artiga.py (Artiga)
- Le script utilise Selenium en mode headless pour gérer le JavaScript du site
- Pas d'authentification requise (site public)
- Extraction des produits depuis les pages de catégorie
- Support des variantes (couleur, taille) si disponibles
- Les logs détaillent le processus d'extraction pour faciliter le debugging

### scraper-cristel.py (Cristel)
- Le script utilise Selenium en mode headless pour gérer le JavaScript du site
- Pas d'authentification requise (site public)
- Structure hiérarchique : Catégories → Sous-catégories → Produits
- Extraction des données depuis JSON-LD (description, SKU, code-barres, prix, variantes)
- Extraction des images depuis `#images-slider` uniquement
- Support des variantes avec taille, SKU, code-barres (GTIN) et prix par variante
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

# Configurer le .env
cp .env.example .env
# Éditer .env avec vos identifiants

# Exécuter les scripts
python scraper-garnier.py --list-categories  # Test Garnier-Thiebaut
python scraper-artiga.py --list-categories  # Test Artiga
python scraper-cristel.py --list-categories  # Test Cristel
python scraper-garnier.py                     # Extraction complète Garnier-Thiebaut
python scraper-artiga.py                      # Extraction complète Artiga
python scraper-cristel.py                     # Extraction complète Cristel
```

## Dépannage

### scraper-garnier.py (Garnier-Thiebaut)

Si le script échoue à l'authentification :
1. Vérifiez que Chrome/Chromium est installé
2. Vérifiez que les identifiants dans `.env` sont corrects
3. Consultez les logs pour plus de détails

### scraper-artiga.py (Artiga)

Si le script ne trouve pas de produits :
1. Vérifiez que Chrome/Chromium est installé
2. Vérifiez votre connexion internet
3. Utilisez `--no-headless` pour voir ce qui se passe dans le navigateur
4. Consultez les logs pour plus de détails

### scraper-cristel.py (Cristel)

Si le script ne trouve pas de produits :
1. Vérifiez que Chrome/Chromium est installé
2. Vérifiez votre connexion internet
3. Utilisez `--list-subcategories` pour voir les sous-catégories disponibles
4. Utilisez `--no-headless` pour voir ce qui se passe dans le navigateur
5. Consultez les logs pour plus de détails

### Problèmes communs

- **ChromeDriver non trouvé** : Selenium 4.6+ devrait l'installer automatiquement
- **Images manquantes** : Vérifiez votre connexion internet. Les images manquantes seront ignorées mais le produit sera quand même ajouté au CSV
- **Aucun produit trouvé** : Vérifiez que le nom de la catégorie correspond exactement (utilisez `--list-categories` pour voir les noms exacts)

Pour plus d'aide, consultez [SETUP.md](SETUP.md) pour un guide complet d'installation.

## Build pour Mac Intel

Pour créer un fichier d'installation (.dmg) pour Mac Intel, consultez le répertoire `creation-build/` qui contient tous les scripts nécessaires.

### Utilisation rapide

```bash
cd creation-build

# Build complet (nettoyage + build + DMG)
./build_all.sh

# Build avec icône
./build_all.sh --with-icon ../icon.png

# Ou étape par étape
python setup.py clean
python setup.py build
./build_dmg.sh
```

Pour plus de détails, consultez [creation-build/BUILD_MAC_INTEL.md](creation-build/BUILD_MAC_INTEL.md).
