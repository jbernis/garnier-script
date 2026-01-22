# Modifications du Générateur CSV

## Vue d'ensemble

Le générateur CSV a été amélioré avec trois fonctionnalités majeures :

1. ✅ **Sélection des sous-catégories pour Artiga et Cristel**
2. ✅ **Sauvegarde de la configuration des champs CSV par fournisseur**
3. ✅ **Masquage de l'option gammes pour les fournisseurs autres que Garnier**

## Architecture : Séparation des configurations

### Avant
- Un seul fichier `csv_config.json` utilisé par l'import ET le générateur CSV
- Système de backup/restore pour éviter les conflits
- Impossible de sauvegarder des configurations différentes

### Après
- `csv_config.json` → Utilisé uniquement par l'import
- `csv_generator_config.json` → Nouveau fichier dédié au générateur CSV
- Pas de conflit possible entre les deux fonctionnalités
- Configurations indépendantes et persistantes

## Fichiers créés

### 1. `apps/csv_generator/csv_generator_config.py`
Nouveau module de gestion de configuration dédié au générateur CSV.

**Fonctionnalités :**
- Classe `CSVGeneratorConfig` pour gérer la configuration
- Méthodes get/set pour columns, handle_source, vendor
- Support des catégories et sous-catégories sauvegardées
- Fichier `csv_generator_config.json` pour la persistance

**API Principale :**
```python
from apps.csv_generator.csv_generator_config import get_csv_generator_config

config = get_csv_generator_config()

# Sauvegarder une configuration complète
config.save_full_config(
    supplier='artiga',
    columns=['Handle', 'Title', ...],
    handle_source='barcode',
    vendor='Artiga',
    categories=None,
    subcategories=['Nappes', 'Serviettes']
)

# Récupérer la configuration
columns = config.get_columns('artiga')
handle_source = config.get_handle_source('artiga')
```

## Fichiers modifiés

### 1. `apps/csv_generator/generator.py`

#### Changements principaux :
- ✅ Suppression du système backup/restore
- ✅ Ajout du paramètre `subcategories` à `generate_csv()`
- ✅ Correction de `get_categories()` pour Artiga/Cristel
- ✅ Ajout de `get_subcategories(supplier, category)`
- ✅ Modification de `get_current_config()` pour utiliser `csv_generator_config`
- ✅ Création d'un fichier temporaire pour la génération

#### Nouvelle signature :
```python
def generate_csv(
    self,
    supplier: str,
    categories: Optional[List[str]],
    subcategories: Optional[List[str]],  # NOUVEAU
    selected_fields: List[str],
    handle_source: str,
    vendor: str,
    gamme: Optional[str] = None,
    output_file: Optional[str] = None
) -> str:
```

#### Filtrage par sous-catégories :
Pour Artiga et Cristel, les sous-catégories sont maintenant passées au lieu des catégories :
```python
# Pour Artiga/Cristel
generate_csv_from_db(
    output_file=output_file,
    output_db=db_path,
    supplier=supplier,
    categories=subcategories if subcategories else categories
)
```

### 2. `apps/csv_generator/gui/window.py`

#### Changements principaux :
- ✅ Import de `csv_generator_config`
- ✅ Ajout de variables pour gérer les sous-catégories
- ✅ Masquage conditionnel de l'option gammes
- ✅ Bouton "💾 Sauvegarder cette configuration"
- ✅ Affichage hiérarchique des catégories/sous-catégories
- ✅ Gestion des sélections en cascade

#### Interface hiérarchique (Artiga/Cristel) :
```
☑ Linge de table
  └─ ☑ Nappes
  └─ ☑ Serviettes
  └─ ☐ Chemins de table
☐ Linge de bain
  └─ ☐ Serviettes de bain
  └─ ☐ Tapis de bain
```

**Comportement :**
- Sélectionner une catégorie → sélectionne toutes ses sous-catégories
- Sélectionner une sous-catégorie → sélectionne automatiquement sa catégorie parente
- Désélectionner une catégorie → désélectionne toutes ses sous-catégories

#### Sauvegarde de configuration :
Un nouveau bouton "💾 Sauvegarder cette configuration" permet de sauvegarder :
- Les champs CSV sélectionnés
- La source du handle
- Le nom du vendor
- (Optionnel) Les catégories/sous-catégories sélectionnées

La configuration est sauvegardée dans `csv_generator_config.json` et rechargée automatiquement au prochain lancement.

#### Masquage des gammes :
L'option "Gamme" n'apparaît plus que pour Garnier :
```python
if value == 'garnier':
    self.gamme_frame.pack(fill="x", padx=20, pady=(0, 10))
    self.load_gammes(value)
else:
    self.gamme_frame.pack_forget()
```

## Comment tester

### Test 1 : Garnier (pas de changement majeur)
1. Ouvrir le générateur CSV
2. Sélectionner "Garnier"
3. ✅ Vérifier que l'option "Gamme" est visible
4. ✅ Vérifier que les catégories s'affichent normalement (liste simple)
5. Sélectionner des champs CSV
6. Cliquer sur "💾 Sauvegarder cette configuration"
7. ✅ Vérifier le message "✓ Configuration sauvegardée pour Garnier"
8. Générer un CSV
9. ✅ Vérifier que le CSV est généré correctement

### Test 2 : Artiga (nouveau comportement)
1. Ouvrir le générateur CSV
2. Sélectionner "Artiga"
3. ✅ Vérifier que l'option "Gamme" est CACHÉE
4. ✅ Vérifier l'affichage hiérarchique :
   - Catégories avec sous-catégories indentées (└─)
   - Checkboxes pour catégories ET sous-catégories
5. Tester la sélection en cascade :
   - Sélectionner une catégorie → toutes ses sous-catégories sont sélectionnées
   - Sélectionner une sous-catégorie → la catégorie parente est sélectionnée
   - Désélectionner une catégorie → toutes ses sous-catégories sont désélectionnées
6. Sélectionner des sous-catégories spécifiques
7. Sélectionner des champs CSV
8. Cliquer sur "💾 Sauvegarder cette configuration"
9. Générer un CSV avec les sous-catégories sélectionnées
10. ✅ Vérifier que le CSV contient uniquement les produits des sous-catégories sélectionnées

### Test 3 : Cristel (même comportement qu'Artiga)
1. Ouvrir le générateur CSV
2. Sélectionner "Cristel"
3. ✅ Vérifier que l'option "Gamme" est CACHÉE
4. ✅ Vérifier l'affichage hiérarchique
5. Tester la sélection en cascade (comme Artiga)
6. Générer un CSV avec des sous-catégories spécifiques

### Test 4 : Persistance de la configuration
1. Configurer les champs pour Artiga (décocher certains champs)
2. Cliquer sur "💾 Sauvegarder cette configuration"
3. Fermer et rouvrir le générateur CSV
4. Sélectionner "Artiga"
5. ✅ Vérifier que les champs sauvegardés sont correctement cochés/décochés
6. Configurer les champs différemment pour Garnier
7. Sauvegarder
8. Basculer entre Artiga et Garnier
9. ✅ Vérifier que chaque fournisseur a sa propre configuration

### Test 5 : Indépendance avec l'import
1. Ouvrir la configuration CSV (Configuration → Configuration CSV)
2. Modifier les champs pour un fournisseur
3. Sauvegarder
4. Ouvrir le générateur CSV
5. Sélectionner le même fournisseur
6. ✅ Vérifier que les champs du générateur sont indépendants
7. Modifier les champs dans le générateur et sauvegarder
8. Faire un import
9. ✅ Vérifier que l'import utilise toujours `csv_config.json` (pas affecté)

## Structure des fichiers de configuration

### csv_config.json (pour l'import)
```json
{
  "garnier": {
    "columns": ["Handle", "Title", ...],
    "handle_source": "barcode",
    "vendor": "Garnier-Thiebaut"
  },
  "artiga": {
    "columns": ["Handle", "Title", ...],
    "handle_source": "barcode",
    "vendor": "Artiga"
  }
}
```

### csv_generator_config.json (pour le générateur)
```json
{
  "garnier": {
    "columns": ["Handle", "Title", "Vendor", ...],
    "handle_source": "barcode",
    "vendor": "Garnier-Thiebaut"
  },
  "artiga": {
    "columns": ["Handle", "Title", "Body (HTML)", ...],
    "handle_source": "barcode",
    "vendor": "Artiga",
    "subcategories": ["Nappes", "Serviettes De Table"]
  }
}
```

## Points d'attention

### 1. Base de données
Les bases de données Artiga et Cristel utilisent deux champs :
- `category` : La catégorie principale
- `subcategory` : La sous-catégorie (ce qui est affiché dans l'interface)

Le générateur filtre par le champ `subcategory` quand des sous-catégories sont sélectionnées.

### 2. Nommage des fichiers CSV
Le nom du fichier généré inclut maintenant les sous-catégories si spécifiées :
- Avant : `shopify_import_artiga_20260119_150000.csv`
- Après : `shopify_import_artiga_nappes_serviettes_20260119_150000.csv`

### 3. Compatibilité
✅ Les scripts de génération CSV existants (`scraper-generate-csv.py`) n'ont pas été modifiés
✅ L'import continue de fonctionner normalement
✅ Pas de breaking changes pour les utilisateurs existants

## Résumé des améliorations

| Fonctionnalité | Avant | Après |
|----------------|-------|-------|
| **Option gammes** | Visible pour tous | Visible uniquement pour Garnier |
| **Catégories Artiga/Cristel** | Liste simple | Arborescence hiérarchique |
| **Sélection sous-catégories** | ❌ Non supporté | ✅ Sélection granulaire |
| **Sauvegarde configuration** | ❌ Temporaire (backup/restore) | ✅ Persistante par fournisseur |
| **Indépendance import/générateur** | ❌ Conflits potentiels | ✅ Configurations séparées |
| **Sélection en cascade** | ❌ N/A | ✅ Catégorie ↔ Sous-catégories |

## Migration

Aucune migration nécessaire ! Le nouveau système :
- Crée automatiquement `csv_generator_config.json` si absent
- Fallback sur les valeurs par défaut si pas de configuration
- Compatible avec les anciennes bases de données

Les utilisateurs peuvent continuer à utiliser le générateur normalement, avec les nouvelles fonctionnalités disponibles immédiatement.
