# Résumé du Fonctionnement : Système product_type et csv_type avec Table de Concordance

## Vue d'ensemble

Le système sépare deux concepts de "type" pour améliorer la précision de la catégorisation Google Shopping :

- **`product_type`** : Type original du CSV (ex: "table", "serviettes") - **JAMAIS modifié**
- **`csv_type`** : Type suggéré par le LLM SEO basé sur le nom/produit (ex: "NAPPES", "COUVERTURES") - **Modifiable**

## Flux de traitement complet

### 1. Import CSV
```
CSV importé → product_type = Type original du CSV (ex: "table")
```

### 2. Phase SEO
```
LLM SEO analyse le produit → suggère csv_type avec confiance
Exemple: "Nappe en coton" → csv_type = "NAPPES", csv_type_confidence = 0.95
```

**Résultat sauvegardé** :
- `product_category_cache.product_type` = "table" (original, jamais modifié)
- `product_category_cache.csv_type` = "NAPPES" (suggéré par SEO)

**Si `csv_type_confidence >= 0.8`** :
- Création d'une entrée dans `type_category_mapping` avec `product_type` + `csv_type`
- Mais sans `category_code` et `category_path` (seront remplis après Google Shopping)

### 3. Phase Google Shopping

#### Étape 0 : Vérifier la table de concordance (PRIORITAIRE)

```
1. Récupérer product_type (original) et csv_type (suggéré) depuis le cache
2. Chercher dans type_category_mapping avec product_type + csv_type
3. Si trouvé ET confidence >= 0.7 → Utiliser la catégorie (PAS de LLM!)
4. Si trouvé mais confidence < 0.7 → LLM Google Shopping
5. Si rien trouvé → LLM Google Shopping
```

#### Étape 1 : Si pas de règle trouvée → LLM Google Shopping

```
LangGraph catégorise le produit → trouve catégorie Google Shopping
Exemple: "Maison et jardin > Linge > Literie > Couvertures"
```

#### Étape 2 : Mise à jour de la table de concordance

```
Après catégorisation réussie :
- Mettre à jour type_category_mapping avec :
  * product_type = "table" (original)
  * csv_type = "NAPPES" (suggéré par SEO)
  * category_code = "123456"
  * category_path = "Maison et jardin > Linge > Literie > Couvertures"
  * confidence = confidence de la catégorisation
```

### 4. Export CSV

```
Lors de l'export CSV :
- Le champ "Type" utilise csv_type depuis product_category_cache
- Si csv_type non disponible, utilise product_type (original)
```

## Protection des règles à confiance élevée

### Seuil de protection : `confidence >= 0.9`

**Règles protégées** :
- Ne peuvent **PAS** être modifiées automatiquement
- Peuvent être modifiées **UNIQUEMENT** manuellement via l'UI (avec `force_update=True`)

**Méthodes protégées** :
1. `_update_concordance_table()` : Vérifie avant création/mise à jour
2. `save_type_mapping()` : Vérifie avant INSERT OR REPLACE
3. `update_type_mapping()` : Vérifie avant UPDATE

**Comportement** :
- Si règle existe avec `confidence >= 0.9` ET `force_update=False` → **Ne pas modifier**
- Si règle existe avec `confidence >= 0.9` ET `force_update=True` → **Permettre modification** (modifications manuelles)

## Structure de la table de concordance

### Table `type_category_mapping`

```sql
CREATE TABLE type_category_mapping (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    product_type TEXT NOT NULL,      -- Type original du CSV (ex: "table")
    csv_type TEXT NOT NULL,          -- Type suggéré par SEO (ex: "NAPPES")
    category_code TEXT NOT NULL,     -- Code Google Shopping
    category_path TEXT NOT NULL,     -- Chemin complet de la catégorie
    confidence REAL DEFAULT 1.0,     -- Confiance de la règle (0.0 - 1.0)
    created_at TIMESTAMP,
    updated_at TIMESTAMP,
    use_count INTEGER DEFAULT 0,    -- Nombre d'utilisations
    created_by TEXT,                 -- 'manual', 'seo_auto', 'llm_google_shopping'
    is_active BOOLEAN DEFAULT 1,
    UNIQUE(product_type, csv_type, category_code)  -- Contrainte composite
)
```

## Exemple concret

### Produit : "Nappe en coton Argelos"

1. **Import CSV** :
   - `Type` = "table"
   - `product_type` = "table" (sauvegardé dans cache)

2. **Phase SEO** :
   - LLM analyse : "Nappe en coton" → suggère `csv_type` = "NAPPES"
   - `csv_type_confidence` = 0.95
   - Sauvegarde : `product_type` = "table", `csv_type` = "NAPPES"
   - Création concordance : `(product_type="table", csv_type="NAPPES")` sans catégorie

3. **Phase Google Shopping** :
   - Cherche dans concordance : `product_type="table"` + `csv_type="NAPPES"`
   - Si règle trouvée avec `confidence >= 0.7` → Utilise directement la catégorie (pas de LLM)
   - Sinon → LLM catégorise → trouve "Maison et jardin > Linge > Literie > Nappes"
   - Mise à jour concordance avec catégorie complète

4. **Export CSV** :
   - Champ `Type` = "NAPPES" (depuis `csv_type`)

## Avantages du système

1. **Précision améliorée** : `csv_type` capture mieux la sémantique réelle du produit
2. **Performance** : Réutilisation des règles évite les appels LLM répétés
3. **Traçabilité** : `product_type` conserve toujours le type original du CSV
4. **Protection** : Les règles validées (confiance >= 0.9) ne sont pas écrasées automatiquement
5. **Flexibilité** : Possibilité de modifier manuellement via l'UI même les règles protégées

## Cas d'usage

### Nouveau produit avec type connu

```
Produit: "Nappe en lin"
Type CSV: "table"
→ SEO suggère: csv_type = "NAPPES" (confiance 0.95)
→ Concordance existe: (product_type="table", csv_type="NAPPES") → catégorie "Nappes"
→ Utilise directement la catégorie (0 appel LLM)
```

### Nouveau produit sans règle

```
Produit: "Plaid en laine"
Type CSV: "couverture"
→ SEO suggère: csv_type = "COUVERTURES" (confiance 0.90)
→ Aucune concordance trouvée
→ LLM catégorise → trouve "Maison et jardin > Linge > Literie > Couvertures"
→ Crée nouvelle règle dans concordance
```

### Règle protégée

```
Règle existante: (product_type="table", csv_type="NAPPES") avec confidence=0.95
→ Tentative modification automatique → BLOQUÉE (confidence >= 0.9)
→ Modification manuelle via UI → AUTORISÉE (force_update=True)
```
