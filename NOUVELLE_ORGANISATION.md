# Nouvelle Organisation des Scripts

## Vue d'ensemble

Les scripts de chaque fournisseur sont maintenant organisés dans leur propre répertoire :

```
/Users/jean-loup/shopify/garnier/
├── database/             # Bases de données
│   ├── garnier_products.db
│   ├── artiga_products.db
│   ├── cristel_products.db
│   └── ai_prompts.db
├── apps/                 # Applications
│   ├── ai_editor/        (éditeur IA)
│   ├── csv_generator/    (générateur CSV)
│   └── gui/              (interface + visualiseur CSV)
├── garnier/              # Scripts + Modules Garnier
│   ├── garnier_functions.py        (fonctions principales)
│   ├── scraper_garnier_module.py   (wrapper/utilitaires)
│   ├── scraper-collect.py
│   ├── scraper-process.py
│   ├── scraper-generate-csv.py
│   ├── scraper-gamme.py
│   └── query_product.py
├── artiga/               # Scripts Artiga
│   ├── scraper-collect.py
│   ├── scraper-process.py
│   ├── scraper-generate-csv.py
│   ├── scraper-subcategory.py
│   └── query_product.py
├── cristel/              # Scripts Cristel
│   ├── scraper-collect.py
│   ├── scraper-process.py
│   ├── scraper-generate-csv.py
│   ├── scraper-subcategory.py
│   └── query_product.py
├── utils/                # Utilitaires partagés
│   ├── artiga_db.py
│   ├── cristel_db.py
│   ├── garnier_db.py
│   └── app_config.py
├── scrapers/             # Wrappers pour la GUI
│   ├── artiga_scraper.py
│   ├── cristel_scraper.py
│   └── garnier_scraper.py
└── outputs/              # Fichiers CSV générés
    ├── garnier/
    ├── artiga/
    └── cristel/
```

## Avantages

✅ **Organisation claire** : Chaque fournisseur a son propre répertoire  
✅ **Noms simplifiés** : Plus de préfixe `scraper-{fournisseur}-`  
✅ **Maintenabilité** : Facile de trouver les scripts d'un fournisseur  
✅ **Scalabilité** : Facile d'ajouter de nouveaux fournisseurs  

## Utilisation

### Garnier

```bash
# Workflow complet
python garnier/scraper-gamme.py --url "..." --gamme "..."

# Étape par étape
python garnier/scraper-collect.py
python garnier/scraper-process.py
python garnier/scraper-generate-csv.py

# Diagnostic
python garnier/query_product.py <CODE_PRODUIT>
python garnier/query_product.py --stats
```

### Artiga

```bash
# Workflow complet
python artiga/scraper-subcategory.py \
  --url "..." --category "..." --subcategory "..."

# Étape par étape
python artiga/scraper-collect.py --category "Nappes"
python artiga/scraper-process.py --category "Nappes"
python artiga/scraper-generate-csv.py --category "Nappes"

# Diagnostic
python artiga/query_product.py <CODE_PRODUIT>
python artiga/query_product.py --stats
```

### Cristel

```bash
# Workflow complet
python cristel/scraper-subcategory.py \
  --url "..." --category "..." --subcategory "..."

# Étape par étape
python cristel/scraper-collect.py --category "Casseroles"
python cristel/scraper-process.py --category "Casseroles"
python cristel/scraper-generate-csv.py --category "Casseroles"

# Diagnostic
python cristel/query_product.py <CODE_PRODUIT>
python cristel/query_product.py --stats
```

## Migration depuis l'ancienne structure

### Ancienne structure
```bash
python scraper-artiga-collect.py --category "Nappes"
```

### Nouvelle structure
```bash
python artiga/scraper-collect.py --category "Nappes"
```

## Scripts Legacy

Les scripts monolithiques restent disponibles à la racine pour compatibilité :
- `scraper-artiga.py` (legacy)
- `scraper-cristel.py` (legacy)

## Documentation Mise à Jour

- ✅ `QUICK_START_ARTIGA_CRISTEL.md` - Mis à jour avec les nouveaux chemins
- ✅ `ARCHITECTURE_MIGRATION_SUMMARY.md` - Mis à jour avec la nouvelle structure
- ✅ `NOUVELLE_ORGANISATION.md` (ce fichier) - Guide de la nouvelle organisation

## Tests

Pour vérifier que tout fonctionne :

```bash
# Test Artiga
python artiga/scraper-collect.py --category "Nappes" --limit 1
python artiga/query_product.py --stats

# Test Cristel
python cristel/scraper-collect.py --category "Casseroles" --limit 1
python cristel/query_product.py --stats

# Test Garnier
python garnier/query_product.py --stats
```

## Compatibilité

- ✅ Les scripts legacy continuent de fonctionner
- ✅ L'interface graphique (GUI) n'est pas affectée
- ✅ Les wrappers dans `scrapers/` n'ont pas changé
- ✅ Les bases de données restent à la racine du projet

## Résumé

Cette réorganisation améliore significativement la structure du projet sans casser la compatibilité existante. Tous les scripts ont été testés et fonctionnent correctement avec la nouvelle structure.
