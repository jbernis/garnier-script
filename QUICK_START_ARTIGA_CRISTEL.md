# Guide de Démarrage Rapide - Artiga & Cristel

## Vue d'ensemble

Cette nouvelle architecture modulaire permet de :
1. **Collecter** les produits dans une base de données
2. **Traiter** les variants pour extraire les détails
3. **Générer** le CSV Shopify

## Commandes Rapides

### Artiga

#### Workflow Complet (Recommandé)
```bash
# Traiter une sous-catégorie complète en une seule commande
python artiga/scraper-subcategory.py \
  --url "https://www.artiga.fr/nappes-rectangulaires" \
  --category "Nappes" \
  --subcategory "Nappes rectangulaires"
```

#### Workflow Manuel (Étape par Étape)
```bash
# 1. Collecter les produits
python artiga/scraper-collect.py --category "Nappes"

# 2. Traiter les variants
python artiga/scraper-process.py --category "Nappes"

# 3. Générer le CSV
python artiga/scraper-generate-csv.py --category "Nappes"
```

#### Diagnostic
```bash
# Voir les statistiques
python artiga/query_product.py --stats

# Voir un produit spécifique
python artiga/query_product.py <CODE_PRODUIT>

# Lister les catégories disponibles
python artiga/scraper-generate-csv.py --list-categories
```

### Cristel

#### Workflow Complet (Recommandé)
```bash
# Traiter une sous-catégorie complète en une seule commande
python cristel/scraper-subcategory.py \
  --url "https://www.cristel.com/casseroles-inox" \
  --category "Casseroles" \
  --subcategory "Casseroles inox"
```

#### Workflow Manuel (Étape par Étape)
```bash
# 1. Collecter les produits
python cristel/scraper-collect.py --category "Casseroles"

# 2. Traiter les variants
python cristel/scraper-process.py --category "Casseroles"

# 3. Générer le CSV
python cristel/scraper-generate-csv.py --category "Casseroles"
```

#### Diagnostic
```bash
# Voir les statistiques
python cristel/query_product.py --stats

# Voir un produit spécifique
python cristel/query_product.py <CODE_PRODUIT>

# Lister les catégories disponibles
python cristel/scraper-generate-csv.py --list-categories
```

## Options Utiles

### Mode Debug
```bash
# Afficher le navigateur (désactiver headless)
python artiga/scraper-collect.py --category "Nappes" --no-headless
```

### Limiter le Nombre de Produits
```bash
# Collecter seulement 5 produits (pour tester)
python artiga/scraper-collect.py --category "Nappes" --limit 5
```

### Retraiter les Erreurs
```bash
# Retraiter les variants en erreur
python artiga/scraper-process.py --retry-errors
```

### Filtrer par Sous-catégorie
```bash
# Générer le CSV pour une sous-catégorie spécifique
python artiga/scraper-generate-csv.py --subcategory "Nappes rectangulaires"
```

### Ignorer des Étapes
```bash
# Ignorer la collecte (si déjà faite)
python artiga/scraper-subcategory.py \
  --url "..." \
  --category "..." \
  --subcategory "..." \
  --skip-collect

# Ignorer le traitement
python artiga/scraper-subcategory.py \
  --url "..." \
  --category "..." \
  --subcategory "..." \
  --skip-process

# Ignorer la génération CSV
python artiga/scraper-subcategory.py \
  --url "..." \
  --category "..." \
  --subcategory "..." \
  --skip-csv
```

## Exemples Pratiques

### Test Rapide (3 produits)
```bash
# Artiga
python artiga/scraper-collect.py --category "Nappes" --limit 3
python artiga/scraper-process.py --category "Nappes"
python artiga/scraper-generate-csv.py --category "Nappes"
python artiga/query_product.py --stats

# Cristel
python cristel/scraper-collect.py --category "Casseroles" --limit 3
python cristel/scraper-process.py --category "Casseroles"
python cristel/scraper-generate-csv.py --category "Casseroles"
python cristel/query_product.py --stats
```

### Production (Toutes les Catégories)
```bash
# Artiga
python artiga/scraper-collect.py
python artiga/scraper-process.py
python artiga/scraper-generate-csv.py

# Cristel
python cristel/scraper-collect.py
python cristel/scraper-process.py
python cristel/scraper-generate-csv.py
```

### Mise à Jour Incrémentale
```bash
# 1. Collecter les nouveaux produits
python artiga/scraper-collect.py --category "Nappes"

# 2. Traiter seulement les nouveaux variants (status='pending')
python artiga/scraper-process.py --category "Nappes"

# 3. Générer le CSV avec tous les produits
python artiga/scraper-generate-csv.py --category "Nappes"
```

## Fichiers Générés

### Bases de Données
- `artiga_products.db` - Base de données Artiga
- `cristel_products.db` - Base de données Cristel

### Fichiers CSV
- `outputs/artiga/shopify_import_artiga_<categorie>_<timestamp>.csv`
- `outputs/cristel/shopify_import_cristel_<categorie>_<timestamp>.csv`

## Statuts des Produits/Variants

- **pending** : En attente de traitement
- **processing** : En cours de traitement
- **completed** : Traité avec succès
- **error** : Erreur lors du traitement

## Gestion des Erreurs

### Voir les Produits en Erreur
```bash
# Artiga
python artiga/query_product.py --stats

# Cristel
python cristel/query_product.py --stats
```

### Retraiter les Erreurs
```bash
# Artiga
python artiga/scraper-process.py --retry-errors

# Cristel
python cristel/scraper-process.py --retry-errors
```

### Limite de Retry
Les produits/variants en erreur sont automatiquement retentés jusqu'à **3 fois** maximum (`retry_count < 3`).

## Comparaison avec l'Ancienne Architecture

### Ancienne Architecture (Legacy)
```bash
# Un seul script fait tout
python scraper-artiga.py --category "Nappes"
```

**Inconvénients** :
- Pas de persistance (si interruption, tout est perdu)
- Pas de gestion d'erreurs avancée
- Pas de retry automatique
- Difficile de déboguer

### Nouvelle Architecture (Modulaire)
```bash
# Trois scripts séparés (ou un orchestrateur)
python artiga/scraper-collect.py --category "Nappes"
python artiga/scraper-process.py --category "Nappes"
python artiga/scraper-generate-csv.py --category "Nappes"

# OU en une seule commande
python artiga/scraper-subcategory.py \
  --url "..." --category "Nappes" --subcategory "..."
```

**Avantages** :
- ✅ Persistance dans la base de données
- ✅ Gestion d'erreurs avancée avec retry
- ✅ Diagnostic et statistiques
- ✅ Reprise après interruption
- ✅ Filtrage et génération partielle

## Compatibilité

Les **scripts legacy continuent de fonctionner** :
```bash
# Ancienne méthode (toujours fonctionnelle)
python scraper-artiga.py --category "Nappes"
python scraper-cristel.py --category "Casseroles"
```

L'**interface graphique (GUI)** continue d'utiliser les scripts legacy.

## Support

Pour plus de détails, voir :
- `ARCHITECTURE_MIGRATION_SUMMARY.md` - Documentation complète
- `FONCTIONNALITES.md` - Fonctionnalités générales du projet

## Aide

```bash
# Aide pour chaque script
python artiga/scraper-collect.py --help
python artiga/scraper-process.py --help
python artiga/scraper-generate-csv.py --help
python artiga/scraper-subcategory.py --help
python artiga/query_product.py --help
```
