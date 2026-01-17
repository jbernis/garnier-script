# Résumé de la Migration d'Architecture - Artiga & Cristel

## Date
17 janvier 2026

## Objectif
Aligner l'architecture d'Artiga et Cristel avec celle de Garnier en utilisant une approche modulaire basée sur une base de données SQLite.

## Fichiers Créés

### Utilitaires de Base de Données
- ✅ `utils/artiga_db.py` (26K) - Gestionnaire de base de données pour Artiga
- ✅ `utils/cristel_db.py` (26K) - Gestionnaire de base de données pour Cristel

### Scripts Garnier (dans garnier/)
- ✅ `garnier/scraper-collect.py` (79K) - Collecte des produits dans la DB
- ✅ `garnier/scraper-process.py` (14K) - Traitement des variants
- ✅ `garnier/scraper-generate-csv.py` (19K) - Génération du CSV Shopify
- ✅ `garnier/scraper-gamme.py` (26K) - Script orchestrateur
- ✅ `garnier/query_product.py` (5K) - Outil de diagnostic

### Scripts Artiga (dans artiga/)
- ✅ `artiga/scraper-collect.py` (13K) - Collecte des produits dans la DB
- ✅ `artiga/scraper-process.py` (7.3K) - Traitement des variants
- ✅ `artiga/scraper-generate-csv.py` (12K) - Génération du CSV Shopify
- ✅ `artiga/scraper-subcategory.py` (7.1K) - Script orchestrateur
- ✅ `artiga/query_product.py` (7.8K) - Outil de diagnostic

### Scripts Cristel (dans cristel/)
- ✅ `cristel/scraper-collect.py` (13K) - Collecte des produits dans la DB
- ✅ `cristel/scraper-process.py` (7.3K) - Traitement des variants
- ✅ `cristel/scraper-generate-csv.py` (12K) - Génération du CSV Shopify
- ✅ `cristel/scraper-subcategory.py` (7.1K) - Script orchestrateur
- ✅ `cristel/query_product.py` (7.8K) - Outil de diagnostic

### Configuration
- ✅ `app_config.json` - Mis à jour avec les chemins des bases de données dans `database/`
- ✅ `utils/app_config.py` - Déjà configuré avec `get_artiga_db_path()` et `get_cristel_db_path()`

### Organisation des Fichiers (Janvier 2026)
- ✅ `database/` - Toutes les bases de données (garnier_products.db, artiga_products.db, cristel_products.db, ai_prompts.db)
- ✅ `apps/` - Applications (ai_editor/, csv_generator/, gui/ avec visualiseur CSV)

## Architecture

### Schéma de Base de Données

Les bases de données Artiga et Cristel utilisent le même schéma que Garnier, avec **"subcategory"** au lieu de **"gamme"** :

```sql
-- Table products
CREATE TABLE products (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    product_code TEXT NOT NULL UNIQUE,
    handle TEXT NOT NULL,
    title TEXT,
    description TEXT,
    vendor TEXT,
    product_type TEXT,
    tags TEXT,
    category TEXT,
    subcategory TEXT,  -- Au lieu de "gamme"
    base_url TEXT,
    status TEXT DEFAULT 'pending',
    error_message TEXT,
    is_new INTEGER DEFAULT 0,
    retry_count INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Table product_variants
CREATE TABLE product_variants (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    product_id INTEGER NOT NULL,
    code_vl TEXT NOT NULL UNIQUE,
    url TEXT NOT NULL,
    size_text TEXT,
    status TEXT DEFAULT 'pending',
    error_message TEXT,
    sku TEXT,
    gencode TEXT,
    price_pa TEXT,
    price_pvc TEXT,
    stock INTEGER,
    size TEXT,
    color TEXT,
    material TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (product_id) REFERENCES products(id) ON DELETE CASCADE
);

-- Table product_images
CREATE TABLE product_images (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    product_id INTEGER NOT NULL,
    image_url TEXT NOT NULL,
    image_position INTEGER,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (product_id) REFERENCES products(id) ON DELETE CASCADE
);
```

### Workflow

```
┌─────────────────────────────────────────────────────────────┐
│                    ARTIGA / CRISTEL                         │
└─────────────────────────────────────────────────────────────┘

1. COLLECTE (scraper-{supplier}-collect.py)
   ├─ Parcourt les catégories et sous-catégories
   ├─ Extrait les informations de base des produits
   ├─ Stocke dans la DB avec status='pending'
   └─ Crée les variants avec status='pending'

2. TRAITEMENT (scraper-{supplier}-process.py)
   ├─ Récupère les variants avec status='pending'
   ├─ Extrait les détails (prix, SKU, stock)
   ├─ Met à jour la DB avec status='completed' ou 'error'
   └─ Met à jour le status du produit parent

3. GÉNÉRATION CSV (scraper-{supplier}-generate-csv.py)
   ├─ Récupère les produits avec variants complétés
   ├─ Applique la configuration CSV (csv_config.json)
   ├─ Génère le fichier CSV Shopify
   └─ Sauvegarde dans outputs/{supplier}/

4. ORCHESTRATEUR (scraper-{supplier}-subcategory.py)
   └─ Exécute les 3 étapes séquentiellement pour une sous-catégorie
```

## Fonctionnalités Implémentées

### Gestion des Erreurs
- ✅ Colonnes `status` et `error_message` dans les tables
- ✅ Colonne `retry_count` pour limiter les tentatives (max 3)
- ✅ Méthodes `mark_variant_error()` et `mark_variant_processing()`
- ✅ Méthodes `get_error_variants()` et `get_pending_variants()`

### Statistiques et Diagnostic
- ✅ Méthode `get_stats()` avec comptage des erreurs retriables
- ✅ Scripts `query_{supplier}_product.py` pour afficher les détails d'un produit
- ✅ Option `--stats` pour afficher les statistiques globales

### Configuration CSV Centralisée
- ✅ Utilisation de `csv_config.py` et `csv_config.json`
- ✅ Configuration spécifique par fournisseur (colonnes, handle source, vendor)
- ✅ Support de `handle_source` : barcode, sku, title

### Filtrage
- ✅ Filtrage par catégorie (`--category`)
- ✅ Filtrage par sous-catégorie (`--subcategory`)
- ✅ Limite de produits (`--limit`)

## Utilisation

### Collecte
```bash
# Artiga - Toutes les catégories
python artiga/scraper-collect.py

# Artiga - Catégorie spécifique
python artiga/scraper-collect.py --category "Nappes"

# Artiga - Catégorie et sous-catégorie
python artiga/scraper-collect.py --category "Nappes" --subcategory "Nappes rectangulaires"

# Cristel - Même syntaxe
python cristel/scraper-collect.py --category "Casseroles"
```

### Traitement
```bash
# Artiga - Traiter les variants en attente
python artiga/scraper-process.py

# Artiga - Retraiter les erreurs
python artiga/scraper-process.py --retry-errors

# Artiga - Filtrer par catégorie
python artiga/scraper-process.py --category "Nappes"

# Cristel - Même syntaxe
python cristel/scraper-process.py
```

### Génération CSV
```bash
# Artiga - Générer le CSV
python artiga/scraper-generate-csv.py

# Artiga - Filtrer par sous-catégorie
python artiga/scraper-generate-csv.py --subcategory "Nappes rectangulaires"

# Artiga - Lister les catégories disponibles
python artiga/scraper-generate-csv.py --list-categories

# Cristel - Même syntaxe
python cristel/scraper-generate-csv.py
```

### Orchestrateur (Workflow Complet)
```bash
# Artiga - Traiter une sous-catégorie complète
python artiga/scraper-subcategory.py \
  --url "https://www.artiga.fr/nappes-rectangulaires" \
  --category "Nappes" \
  --subcategory "Nappes rectangulaires"

# Cristel - Traiter une sous-catégorie complète
python cristel/scraper-subcategory.py \
  --url "https://www.cristel.com/casseroles-inox" \
  --category "Casseroles" \
  --subcategory "Casseroles inox"

# Options supplémentaires
--skip-collect    # Ignorer la collecte
--skip-process    # Ignorer le traitement
--skip-csv        # Ignorer la génération CSV
--no-headless     # Afficher le navigateur
```

### Diagnostic
```bash
# Artiga - Afficher un produit spécifique
python artiga/query_product.py NAP123

# Artiga - Afficher les statistiques globales
python artiga/query_product.py --stats

# Cristel - Même syntaxe
python cristel/query_product.py CAS456
python cristel/query_product.py --stats
```

## Bases de Données

Les bases de données sont créées automatiquement au premier lancement :

- `artiga_products.db` - Base de données Artiga
- `cristel_products.db` - Base de données Cristel
- `garnier_products.db` - Base de données Garnier (existante)

## Compatibilité

### Scripts Legacy
Les scripts legacy (`scraper-artiga.py` et `scraper-cristel.py`) **continuent de fonctionner** et peuvent coexister avec la nouvelle architecture.

### Interface Graphique
L'interface graphique (GUI) continue d'utiliser les scripts legacy via les wrappers dans `scrapers/artiga_scraper.py` et `scrapers/cristel_scraper.py`. Aucune modification n'a été apportée aux wrappers pour maintenir la compatibilité.

## Avantages de la Nouvelle Architecture

1. **Persistance** : Les données sont stockées dans une base de données, permettant de reprendre après une interruption
2. **Modularité** : Séparation claire entre collecte, traitement et génération CSV
3. **Gestion d'erreurs** : Suivi détaillé des erreurs avec retry automatique
4. **Diagnostic** : Outils pour inspecter les données et déboguer
5. **Filtrage** : Possibilité de générer des CSV pour des sous-ensembles de produits
6. **Consistance** : Architecture identique pour Garnier, Artiga et Cristel

## Tests

Pour tester la nouvelle architecture :

```bash
# Test rapide Artiga (3 produits)
python artiga/scraper-collect.py --category "Nappes" --limit 3
python artiga/scraper-process.py --category "Nappes"
python artiga/scraper-generate-csv.py --category "Nappes"

# Test rapide Cristel (3 produits)
python cristel/scraper-collect.py --category "Casseroles" --limit 3
python cristel/scraper-process.py --category "Casseroles"
python cristel/scraper-generate-csv.py --category "Casseroles"

# Vérifier les statistiques
python artiga/query_product.py --stats
python cristel/query_product.py --stats
```

## Prochaines Étapes (Optionnel)

1. **Migration GUI** : Modifier les wrappers pour utiliser la nouvelle architecture
2. **Tests d'intégration** : Tester avec de vraies données de production
3. **Documentation utilisateur** : Créer des guides pour les utilisateurs finaux
4. **Optimisations** : Améliorer les performances si nécessaire

## Notes Importantes

- Les bases de données sont créées dans le répertoire racine du projet
- Les CSV sont générés dans `outputs/artiga/` et `outputs/cristel/`
- Le mode headless est activé par défaut (utiliser `--no-headless` pour déboguer)
- Les scripts sont exécutables (`chmod +x` déjà appliqué)

## Conclusion

✅ **Migration terminée avec succès !**

L'architecture d'Artiga et Cristel est maintenant alignée avec celle de Garnier, offrant une base solide pour la maintenance et l'évolution future du projet.
