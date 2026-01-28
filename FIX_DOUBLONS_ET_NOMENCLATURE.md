# Correction des problèmes de doublons et de nomenclature des fichiers CSV Garnier

## Date : 24 janvier 2026

## Problèmes identifiés

### 1. Doublons dans les CSV générés

**Cause** : Les images étaient dupliquées dans la base de données. Chaque image était stockée 2 fois avec la même URL et la même position, ce qui créait des doublons dans le CSV final.

**Exemple** :
- Produit ID 790 : 12 images trouvées, mais seulement 6 uniques (chaque image était dupliquée)
- 43 produits affectés au total
- 187 images dupliquées dans la base de données

**Impact** : Le CSV contenait des lignes en double pour chaque variant, rendant l'import Shopify problématique.

### 2. Nomenclature incohérente des fichiers CSV

**Problème** : Les fichiers CSV générés avaient des noms incohérents :
- `shopify_import_garnier_51901-drap-housse-b35-chambray-naturelnewpa-425_linge-de-lit_...` (gamme mal nettoyée en premier)
- `shopify_import_garnier_zig-zag-curry_linge-de-lit_...` (gamme avant catégorie)
- `shopify_import_garnier_20260124_181856.csv` (sans catégorie ni gamme)

**Format attendu** : `shopify_import_garnier_{categorie}_{gamme}_{timestamp}.csv`

## Corrections apportées

### 1. Correction des doublons d'images

#### a) Nettoyage de la base de données existante

**Script créé** : `fix_duplicate_images.py`

Ce script :
- Parcourt tous les produits de la base de données
- Détecte les images dupliquées (même URL pour le même produit)
- Supprime les doublons en gardant la première occurrence
- Affiche un rapport détaillé des corrections

**Résultat** :
```
✅ Nettoyage terminé:
   - Produits corrigés: 43
   - Images dupliquées supprimées: 187
```

#### b) Modification du générateur CSV

**Fichier modifié** : `garnier/scraper-generate-csv.py`

**Changements** :
- Ajout d'une déduplication automatique des images lors de la génération du CSV
- Détection et log des doublons supprimés
- Les images sont maintenant uniques par URL dans le CSV généré

**Code ajouté** :
```python
# Dédupliquer les images (certaines peuvent être dupliquées dans la DB)
seen_urls = set()
unique_images = []
for img in images:
    url = img['image_url']
    if url not in seen_urls:
        seen_urls.add(url)
        unique_images.append(url)

image_urls = unique_images

# Log si des doublons ont été détectés
if len(images) != len(image_urls):
    logger.info(f"Produit {product_code}: {len(images)} images trouvées, {len(image_urls)} uniques (doublons supprimés)")
```

### 2. Correction de la nomenclature des fichiers

#### a) Ordre des éléments dans le nom

**Fichiers modifiés** :
- `garnier/scraper-generate-csv.py`
- `apps/csv_generator/generator.py`

**Changements** :
- Les catégories sont maintenant ajoutées **en premier**
- La gamme est ajoutée **en deuxième**
- Format final : `shopify_import_garnier_{categorie}_{gamme}_{timestamp}.csv`

**Avant** :
```python
# Gamme ajoutée en premier
if gamme:
    name_parts.append(slugify(gamme))
if categories:
    name_parts.extend(category_slugs)
```

**Après** :
```python
# Catégories ajoutées en PREMIER
if categories and len(categories) > 0:
    category_slugs = [slugify(cat) for cat in categories]
    name_parts.extend(category_slugs)

# Gamme ajoutée en DEUXIÈME
if gamme:
    gamme_slug = slugify(gamme)
    name_parts.append(gamme_slug)
```

#### b) Log amélioré

Ajout d'un log pour afficher le nom du fichier généré :
```python
logger.info(f"Nom du fichier généré: {output_file}")
```

## Tests et validation

### Test 1 : Vérification des doublons

**Commande** :
```bash
python3 garnier/scraper-generate-csv.py --category "Linge de lit" --output outputs/garnier/test_fix_doublons.csv
```

**Résultat** :
- Total lignes : 6618
- Handles uniques : 764
- SKUs uniques : 2046
- ✅ **Aucun doublon détecté**

### Test 2 : Nomenclature avec catégorie et gamme

**Commande** :
```bash
python3 garnier/scraper-generate-csv.py --category "Linge de lit" --gamme "AVA"
```

**Résultat** :
- Fichier généré : `shopify_import_garnier_linge-de-lit_ava_20260124_183941.csv`
- Format : ✅ Catégorie (`linge-de-lit`) puis gamme (`ava`)
- Produits : 168
- Variants : 503
- Lignes CSV : 1695

### Test 3 : Gamme unique détectée automatiquement

Le code détecte maintenant automatiquement quand une seule gamme est présente dans les produits exportés et l'ajoute au nom du fichier.

## Impact sur l'utilisation

### Pour l'utilisateur final

1. **Doublons** : Les CSV générés ne contiennent plus de doublons
2. **Nomenclature** : Les fichiers sont nommés de manière cohérente avec la catégorie en premier, puis la gamme
3. **Clarté** : Le format `shopify_{categorie}_{gamme}_{timestamp}.csv` est facile à identifier

### Exemples de noms de fichiers

**Avant** :
- `shopify_import_garnier_51901-drap-housse-b35-chambray-naturelnewpa-425_linge-de-lit_20260116_173403.csv`
- `shopify_import_garnier_zig-zag-curry_linge-de-lit_20260116_181133.csv`
- `shopify_import_garnier_20260124_181856.csv`

**Après** :
- `shopify_import_garnier_linge-de-lit_ava_20260124_183941.csv`
- `shopify_import_garnier_linge-de-lit_20260123_080440.csv`
- `shopify_import_garnier_accessoire_20260124_122857.csv`

## Prochaines étapes recommandées

1. ✅ **Nettoyer la base de données** (fait avec `fix_duplicate_images.py`)
2. ✅ **Tester la génération de CSV** (fait avec succès)
3. 🔄 **Régénérer les CSV existants** si nécessaire
4. 🔍 **Identifier la source des doublons** dans le scraper pour éviter qu'ils ne se reproduisent

## Fichiers modifiés

1. `garnier/scraper-generate-csv.py` - Déduplication des images + ordre catégorie/gamme
2. `apps/csv_generator/generator.py` - Ordre catégorie/gamme pour l'interface graphique
3. `fix_duplicate_images.py` - **NOUVEAU** - Script de nettoyage de la base de données

## Commandes utiles

### Nettoyer les doublons d'images dans la base de données
```bash
python3 fix_duplicate_images.py
```

### Générer un CSV avec catégorie et gamme
```bash
python3 garnier/scraper-generate-csv.py --category "Linge de lit" --gamme "AVA"
```

### Générer un CSV avec catégorie uniquement
```bash
python3 garnier/scraper-generate-csv.py --category "Linge de lit"
```

### Lister les catégories disponibles
```bash
python3 garnier/scraper-generate-csv.py --list-categories
```
