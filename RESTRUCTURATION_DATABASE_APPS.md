# Restructuration Database & Apps

## Date
17 janvier 2026

## Objectif
Organiser le projet en séparant clairement les bases de données et les applications dans des répertoires dédiés.

## Changements Effectués

### 1. Création de Nouveaux Répertoires

#### `database/`
Contient toutes les bases de données SQLite :
- `garnier_products.db` - Produits Garnier-Thiebaut
- `artiga_products.db` - Produits Artiga
- `cristel_products.db` - Produits Cristel
- `ai_prompts.db` - Prompts et imports pour l'éditeur IA

#### `apps/`
Contient toutes les applications :
- `ai_editor/` - Éditeur IA pour les descriptions de produits
- `csv_generator/` - Générateur de CSV Shopify
- `gui/` - Interface graphique principale + **visualiseur CSV** (viewer_window.py)

### 2. Mise à Jour des Chemins de Base de Données

#### `utils/app_config.py`
Fonction `get_supplier_db_path()` mise à jour :
```python
def get_supplier_db_path(supplier: str) -> str:
    supplier_lower = supplier.lower().strip()
    return f"database/{supplier_lower}_products.db"
```

#### `apps/ai_editor/db.py`
Chemin par défaut mis à jour :
```python
DEFAULT_DB_PATH = "database/ai_prompts.db"
```

#### `app_config.json`
Configuration mise à jour :
```json
{
  "delete_outputs_on_close": false,
  "database_paths": {
    "garnier": "database/garnier_products.db",
    "artiga": "database/artiga_products.db",
    "cristel": "database/cristel_products.db",
    "ai_prompts": "database/ai_prompts.db"
  }
}
```

### 3. Mise à Jour des Imports

Tous les imports ont été mis à jour pour refléter la nouvelle structure :

#### Applications
- `from gui.xxx import` → `from apps.gui.xxx import`
- `from ai_editor.xxx import` → `from apps.ai_editor.xxx import`
- `from csv_generator.xxx import` → `from apps.csv_generator.xxx import`

#### Fichiers Modifiés
- `run_gui.py` - Point d'entrée principal
- `apps/gui/main.py` - Point d'entrée alternatif
- Tous les fichiers dans `apps/gui/` (13 fichiers)
- Tous les fichiers dans `apps/ai_editor/` (7 fichiers)
- Tous les fichiers dans `apps/csv_generator/` (4 fichiers)

### 4. Structure Finale

```
/Users/jean-loup/shopify/garnier/
├── database/                    ← NOUVEAU - Bases de données
│   ├── garnier_products.db
│   ├── artiga_products.db
│   ├── cristel_products.db
│   └── ai_prompts.db
├── apps/                        ← NOUVEAU - Applications
│   ├── ai_editor/               (éditeur IA)
│   │   ├── db.py
│   │   ├── processor.py
│   │   ├── agents.py
│   │   └── gui/
│   │       ├── window.py
│   │       └── viewer.py
│   ├── csv_generator/           (générateur CSV)
│   │   ├── generator.py
│   │   └── gui/
│   │       └── window.py
│   └── gui/                     (interface + visualiseur CSV)
│       ├── main_window.py
│       ├── viewer_window.py     ← Visualiseur CSV
│       ├── import_window.py
│       ├── config_window.py
│       ├── csv_config_window.py
│       ├── ai_editor_window.py
│       ├── setup_window.py
│       ├── progress_window.py
│       └── reprocess_window.py
├── garnier/                     ← Scripts + Modules Garnier
│   ├── garnier_functions.py        (fonctions principales)
│   ├── scraper_garnier_module.py   (wrapper/utilitaires)
│   ├── scraper-collect.py
│   ├── scraper-process.py
│   ├── scraper-generate-csv.py
│   ├── scraper-gamme.py
│   └── query_product.py
├── artiga/                      ← Inchangé
│   ├── scraper-collect.py
│   ├── scraper-process.py
│   ├── scraper-generate-csv.py
│   ├── scraper-subcategory.py
│   └── query_product.py
├── cristel/                     ← Inchangé
│   ├── scraper-collect.py
│   ├── scraper-process.py
│   ├── scraper-generate-csv.py
│   ├── scraper-subcategory.py
│   └── query_product.py
├── utils/                       ← Inchangé
│   ├── artiga_db.py
│   ├── cristel_db.py
│   ├── garnier_db.py
│   └── app_config.py
├── scrapers/                    ← Inchangé
│   ├── artiga_scraper.py
│   ├── cristel_scraper.py
│   └── garnier_scraper.py
└── outputs/                     ← Inchangé
    ├── garnier/
    ├── artiga/
    └── cristel/
```

## Avantages

### Organisation Claire
- ✅ Séparation nette entre données (`database/`) et code applicatif (`apps/`)
- ✅ Facilite la sauvegarde et la restauration des bases de données
- ✅ Simplifie la gestion des backups

### Scalabilité
- ✅ Facile d'ajouter de nouvelles applications dans `apps/`
- ✅ Facile d'ajouter de nouveaux fournisseurs avec leur propre DB
- ✅ Structure modulaire et extensible

### Maintenance
- ✅ Code mieux organisé et plus facile à maintenir
- ✅ Séparation des responsabilités claire
- ✅ Imports explicites et cohérents

## Compatibilité

### Scripts de Scraping
- ✅ Les scripts dans `garnier/`, `artiga/`, `cristel/` fonctionnent sans modification
- ✅ Les wrappers dans `scrapers/` fonctionnent sans modification
- ✅ Les utilitaires dans `utils/` fonctionnent sans modification

### Interface Graphique
- ✅ L'interface graphique fonctionne avec les nouveaux chemins
- ✅ Le visualiseur CSV (`apps/gui/viewer_window.py`) fonctionne correctement
- ✅ L'éditeur IA fonctionne avec la nouvelle DB path

### Bases de Données
- ✅ Toutes les bases de données sont accessibles via `utils/app_config.py`
- ✅ Les chemins sont configurables via `app_config.json`
- ✅ Rétrocompatibilité assurée

## Tests Effectués

```bash
# Vérifier la structure
ls -l database/
ls -l apps/

# Tester les scripts de diagnostic
python artiga/query_product.py --stats
python cristel/query_product.py --stats
python garnier/query_product.py --stats

# Tester l'interface graphique
python run_gui.py
```

## Migration depuis l'Ancienne Structure

Si vous avez des bases de données à la racine du projet :
```bash
# Déplacer les bases de données
mv *.db database/

# Vérifier que tout fonctionne
python run_gui.py
```

## Notes

- Les fichiers `.gitignore` doivent être mis à jour pour ignorer `database/*.db` si nécessaire
- Les scripts de backup doivent pointer vers `database/` au lieu de la racine
- La documentation a été mise à jour pour refléter la nouvelle structure
