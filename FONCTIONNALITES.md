# Résumé des Fonctionnalités

## Vue d'ensemble

Ce projet contient deux scripts Python pour extraire des produits de sites web e-commerce et générer des fichiers CSV compatibles avec l'importation Shopify.

### Scripts disponibles

1. **`scraper-garnier.py`** - Scraper pour Garnier-Thiebaut (site B2B avec authentification)
2. **`scraper-artiga.py`** - Scraper pour Artiga (site public, pas d'authentification)

---

## Fonctionnalités communes aux deux scripts

### 1. Extraction de produits

- ✅ **Extraction par catégorie** : Sélection d'une ou plusieurs catégories spécifiques
- ✅ **Extraction complète** : Extraction de toutes les catégories disponibles
- ✅ **Liste des catégories** : Commande pour afficher toutes les catégories disponibles
- ✅ **Limite de produits** : Option `--limit` pour limiter le nombre de produits extraits (utile pour les tests)

### 2. Gestion des variantes

- ✅ **Détection automatique** : Détection automatique des variantes (taille, couleur, etc.)
- ✅ **Extraction des données par variante** :
  - Prix spécifique par variante
  - SKU unique par variante
  - Code-barres (EAN13) par variante
  - Options (Option1 Name/Value) pour Shopify

### 3. Extraction des images

- ✅ **Toutes les images** : Extraction de toutes les images du produit
- ✅ **URLs complètes** : Les URLs complètes des images sont incluses dans le CSV
- ✅ **Filtrage intelligent** : Exclusion automatique des images non-produits (logos, icônes, etc.)

### 4. Génération du CSV Shopify

- ✅ **Format standard** : CSV conforme au format d'importation Shopify
- ✅ **Colonnes complètes** : Toutes les colonnes nécessaires pour Shopify :
  - Handle, Title, Body (HTML), Vendor, Type, Tags
  - Variant SKU, Variant Price, Variant Compare At Price
  - Variant Inventory Qty
  - Image Src, Image Position, Image Alt Text
  - Option1 Name/Value
  - Variant Barcode (EAN13)
- ✅ **Gestion des images multiples** : Une ligne par image avec le même Handle
- ✅ **Gestion des variantes** : Une ligne par variante avec le même Handle

### 5. Options de ligne de commande

- ✅ **`--category` / `-c`** : Sélectionner une ou plusieurs catégories
- ✅ **`--list-categories` / `-l`** : Lister toutes les catégories disponibles
- ✅ **`--output` / `-o`** : Spécifier un nom de fichier CSV personnalisé
- ✅ **`--preview`** : Afficher un aperçu du DataFrame avant sauvegarde
- ✅ **`--preview-rows`** : Nombre de lignes à afficher dans l'aperçu (défaut: 10)
- ✅ **`--no-headless`** : Désactiver le mode headless (afficher le navigateur pour déboguer)
- ✅ **`--limit N`** : Limiter le nombre de produits à extraire

### 6. Nommage automatique des fichiers

- ✅ **Nom avec catégorie** : Le nom du fichier inclut la catégorie extraite
- ✅ **Nom avec date/heure** : Format `YYYYMMDD_HHMMSS` pour traçabilité
- ✅ **Exemples** :
  - `shopify_import_garnier_linge-de-table_20260105_183045.csv`
  - `shopify_import_artiga_nappes_20260105_183045.csv`

### 7. Gestion des erreurs et robustesse

- ✅ **Gestion des sessions Selenium** : Reconnexion automatique en cas de session invalide
- ✅ **Fallback** : Si Selenium n'est pas disponible, utilisation de requests/BeautifulSoup
- ✅ **Logging détaillé** : Logs informatifs pour suivre le processus d'extraction
- ✅ **Gestion des timeouts** : Attentes intelligentes pour le chargement JavaScript

---

## Fonctionnalités spécifiques à scraper-garnier.py

### Authentification

- ✅ **Authentification automatique** : Connexion avec username/password depuis `.env`
- ✅ **Gestion de session** : Maintien de la session authentifiée
- ✅ **Reconnexion automatique** : Reconnexion si la session expire

### Navigation multi-niveaux

- ✅ **Structure hiérarchique** : 
  - Catalogue → Catégorie → Gamme → Produit → Variante
- ✅ **Défilement automatique** : Défilement automatique pour charger tous les produits
- ✅ **Extraction des gammes** : Détection et extraction des gammes dans chaque catégorie

### Extraction des données produits

- ✅ **Description HTML** : Extraction de la description complète en HTML
- ✅ **Prix de base** : Prix principal du produit
- ✅ **Stock** : Quantité en stock par variante
- ✅ **Code produit** : Code unique du produit
- ✅ **Gencode** : Code-barres EAN13

---

## Fonctionnalités spécifiques à scraper-artiga.py

### Site public (pas d'authentification)

- ✅ **Accès direct** : Pas besoin de credentials, site public
- ✅ **Navigation simplifiée** : Catalogue → Catégorie → Produit → Variante

### Extraction avancée du prix via AJAX

- ✅ **Interception AJAX** : Capture des requêtes AJAX pour récupérer les prix des variantes
- ✅ **Prix dynamiques** : Extraction précise des prix qui changent selon la variante sélectionnée
- ✅ **Fallback DOM** : Si AJAX échoue, extraction depuis le DOM
- ✅ **WebDriver Manager** : Gestion automatique de ChromeDriver via `webdriver-manager`

### Extraction de la description

- ✅ **Onglets dynamiques** : Clic automatique sur les onglets (Description, Détails, Conseils)
- ✅ **HTML complet** : Extraction du HTML complet de tous les onglets
- ✅ **Body (HTML)** : Contenu HTML complet pour Shopify

### Gestion des variantes

- ✅ **Dropdown interactif** : Interaction avec les dropdowns de sélection de variantes
- ✅ **Reconstruction d'URL** : Reconstruction des URLs avec hash pour chaque variante
- ✅ **Sélection JavaScript** : Utilisation de JavaScript pour forcer la sélection des variantes
- ✅ **Attente intelligente** : Attente de la mise à jour du prix après sélection

---

## Technologies utilisées

### Bibliothèques Python

- **Selenium** : Automatisation du navigateur pour JavaScript
- **BeautifulSoup** : Parsing HTML
- **requests** : Requêtes HTTP
- **pandas** : Manipulation de données et génération CSV
- **python-dotenv** : Gestion des variables d'environnement
- **webdriver-manager** : Gestion automatique de ChromeDriver (Artiga uniquement)

### Navigateur

- **Chrome/Chromium** : Navigateur utilisé par Selenium
- **Mode headless** : Par défaut, exécution sans interface graphique
- **Logs de performance** : Capture des requêtes réseau (Artiga uniquement)

---

## Format du CSV généré

### Structure des lignes

- **Une ligne par variante** : Chaque variante a sa propre ligne
- **Une ligne par image** : Chaque image a sa propre ligne (même Handle que le produit)
- **Colonnes principales** :
  - `Handle` : Identifiant unique du produit (slug)
  - `Title` : Nom du produit
  - `Body (HTML)` : Description HTML complète
  - `Variant SKU` : Code SKU de la variante
  - `Variant Price` : Prix de la variante
  - `Variant Barcode` : Code-barres EAN13
  - `Option1 Name` : Nom de l'option (ex: "Taille")
  - `Option1 Value` : Valeur de l'option (ex: "160 cm")
  - `Image Src` : URL complète de l'image
  - `Image Position` : Position de l'image (1, 2, 3, ...)

### Exemple de structure

```
Handle,Title,Variant SKU,Variant Price,Option1 Name,Option1 Value,Image Src,Image Position
nappe-coton-argelos,NAPPE EN COTON - ARGELOS,ARGEN160_1492_160CM,115.00,Taille,160 cm,https://...,1
nappe-coton-argelos,NAPPE EN COTON - ARGELOS,ARGEN160_1492_160CM,115.00,Taille,160 cm,https://...,2
nappe-coton-argelos,NAPPE EN COTON - ARGELOS,ARGEN160_1492_200CM,129.00,Taille,200 cm,https://...,1
nappe-coton-argelos,NAPPE EN COTON - ARGELOS,ARGEN160_1492_200CM,129.00,Taille,200 cm,https://...,2
```

---

## Cas d'usage

### 1. Test rapide

```bash
# Extraire 3 produits d'une catégorie avec aperçu
python scraper-artiga.py --category "Nappes" --limit 3 --preview --no-headless
```

### 2. Extraction complète d'une catégorie

```bash
# Extraire tous les produits d'une catégorie
python scraper-garnier.py --category "Linge de table"
```

### 3. Extraction de plusieurs catégories

```bash
# Extraire plusieurs catégories en une seule exécution
python scraper-artiga.py --category "Nappes" --category "Serviettes De Table"
```

### 4. Extraction avec nom de fichier personnalisé

```bash
# Spécifier un nom de fichier personnalisé
python scraper-garnier.py --category "Linge de table" --output "mon_import.csv"
```

### 5. Débogage

```bash
# Voir le navigateur pendant l'extraction
python scraper-artiga.py --category "Nappes" --limit 1 --no-headless
```

---

## Points forts

### Robustesse

- ✅ Gestion automatique des erreurs
- ✅ Reconnexion automatique en cas de problème
- ✅ Fallback si Selenium n'est pas disponible
- ✅ Gestion des timeouts et attentes

### Précision

- ✅ Extraction précise des prix via AJAX (Artiga)
- ✅ Détection automatique des variantes
- ✅ Extraction complète des métadonnées

### Flexibilité

- ✅ Options de ligne de commande nombreuses
- ✅ Extraction sélective par catégorie
- ✅ Limite de produits pour tests rapides
- ✅ Aperçu avant sauvegarde

### Compatibilité Shopify

- ✅ Format CSV conforme à Shopify
- ✅ Gestion correcte des variantes
- ✅ Gestion correcte des images multiples
- ✅ Toutes les colonnes nécessaires

---

## Limitations connues

1. **Dépendance Chrome** : Nécessite Chrome/Chromium installé
2. **Vitesse** : L'extraction peut être lente pour de nombreux produits (délais pour JavaScript)
3. **Structure du site** : Les scripts sont adaptés aux structures spécifiques de chaque site
4. **Images** : Les images ne sont pas téléchargées localement, seules les URLs sont dans le CSV

---

## Améliorations futures possibles

- [ ] Support d'autres sites e-commerce
- [ ] Téléchargement optionnel des images
- [ ] Support multi-threading pour accélérer l'extraction
- [ ] Interface graphique (GUI)
- [ ] Export vers d'autres formats (JSON, Excel)
- [ ] Mise à jour incrémentale (détection des changements)

