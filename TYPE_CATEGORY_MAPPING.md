# Système de Mapping Type → Catégorie

**Date**: 23 janvier 2026  
**Version**: 1.0  
**Objectif**: Éviter les appels LLM inutiles pour les types de produits récurrents

---

## 🎯 Problème Résolu

### Avant
Si vous avez 100 nappes avec des titres différents:
- ❌ 100 appels LangGraph (5-10s chacun)
- ❌ 300-400 appels API Gemini
- ❌ ~500 secondes de traitement
- ❌ Coût élevé

### Après
Avec une règle `Type "TABLE" → Code 4143`:
- ✅ 1er produit: LangGraph (10s) → Création de la règle
- ✅ 99 produits suivants: Règle directe (0.001s chacun)
- ✅ Total: ~10 secondes
- ✅ Économie: **98% de temps et de coût**

---

## 🏗️ Architecture

### Flux de Vérification (3 niveaux)

```
NOUVEAU PRODUIT (ex: "Nappe en coton - Argelos", Type="TABLE")
    ↓
┌─────────────────────────────────────────────────────────┐
│ 1️⃣ Vérifier type_category_mapping                      │
│    SELECT * FROM type_category_mapping                  │
│    WHERE product_type = 'TABLE' AND is_active = 1       │
└─────────────────────────────────────────────────────────┘
    ↓ TROUVÉ?
   OUI → ✅ Utiliser la règle (0.001s)
    │    source = 'type_mapping'
    │    confidence = 1.0
    │    rationale = "Règle Type: TABLE"
    ↓
┌─────────────────────────────────────────────────────────┐
│ 2️⃣ Vérifier product_category_cache                     │
│    product_key = MD5(Title|Type|Vendor)                 │
│    SELECT * FROM product_category_cache                 │
│    WHERE product_key = ?                                │
└─────────────────────────────────────────────────────────┘
    ↓ TROUVÉ?
   OUI → ✅ Utiliser le cache (0.01s)
    │    source = 'cache'
    ↓
┌─────────────────────────────────────────────────────────┐
│ 3️⃣ Appeler LangGraph                                   │
│    → ProductAgent (Gemini)                              │
│    → TaxonomyAgent (Gemini)                             │
│    → Validation + Fallback parent                       │
└─────────────────────────────────────────────────────────┘
    ↓
   ✅ Résultat LangGraph (5-10s)
      source = 'langgraph'
    ↓
   💾 Sauvegarder dans product_category_cache
```

---

## 📊 Table `type_category_mapping`

### Structure SQL

```sql
CREATE TABLE type_category_mapping (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    product_type TEXT NOT NULL UNIQUE,      -- Type du produit (ex: "TABLE")
    category_code TEXT NOT NULL,            -- Code Google (ex: "4143")
    category_path TEXT NOT NULL,            -- Chemin complet
    confidence REAL DEFAULT 1.0,            -- Toujours 1.0 (règle manuelle)
    created_at TIMESTAMP,
    updated_at TIMESTAMP,
    use_count INTEGER DEFAULT 0,            -- Compteur d'utilisations
    created_by TEXT DEFAULT 'manual',       -- 'manual' ou 'auto_suggestion'
    is_active BOOLEAN DEFAULT 1             -- Activer/désactiver
);
```

### Index pour Performance

```sql
CREATE INDEX idx_type_mapping_type ON type_category_mapping(product_type);
CREATE INDEX idx_type_mapping_active ON type_category_mapping(is_active);
```

---

## 📋 Nouvelle Colonne `source` dans `product_category_cache`

Pour traçabilité, tous les produits ont maintenant une colonne `source`:

| source | Signification |
|--------|---------------|
| `type_mapping` | Catégorisé via règle Type → Catégorie |
| `cache` | Réutilisation cache existant |
| `langgraph` | Catégorisé par LangGraph (LLM) |

---

## 🎨 Interface GUI - Onglet "Règles Types"

### Vue d'ensemble

L'onglet Taxonomie a maintenant **2 sous-onglets**:
1. **Produits** - Interface existante (recherche et modification)
2. **Règles Types** - Nouvelle interface pour gérer les règles

### Structure de l'Onglet "Règles Types"

```
┌────────────────────────────────────────────────────────┐
│ 🔍 Analyser les Patterns                               │
│                                                        │
│ Analyse automatique du cache pour suggérer des règles │
│ (Types avec ≥ 5 produits et confidence ≥ 85%)         │
│                                                        │
│ [🤖 Analyser et Suggérer]  ✅ 3 suggestion(s)         │
│                                                        │
│ ┌──────────────────────────────────────────────────┐ │
│ │ Type: TABLE                                       │ │
│ │ → Maison et jardin > Linge > ... > Nappes        │ │
│ │ 📊 20 produits | Conf moy: 95% | Ex: Nappe...    │ │
│ │ [✅ Créer Règle] [❌ Ignorer]                    │ │
│ └──────────────────────────────────────────────────┘ │
│                                                        │
├────────────────────────────────────────────────────────┤
│ 📋 Règles Actives                                      │
│                                                        │
│ ┌──────────────────────────────────────────────────┐ │
│ │ Type: TABLE                                       │ │
│ │ → Maison et jardin > Linge > Linge de table > N...│ │
│ │ Code: 4143 | Confidence: 100%                    │ │
│ │ 📊 Utilisé 127 fois | Créé: manual | Actif: Oui │ │
│ │ [❌ Désactiver] [🗑️ Supprimer]                  │ │
│ └──────────────────────────────────────────────────┘ │
│                                                        │
│ ┌──────────────────────────────────────────────────┐ │
│ │ Type: SERVIETTES                                  │ │
│ │ → Maison et jardin > Linge > Linge de table > S...│ │
│ │ Code: 4203 | Confidence: 100%                    │ │
│ │ 📊 Utilisé 85 fois | Créé: auto_suggestion       │ │
│ │ [❌ Désactiver] [🗑️ Supprimer]                  │ │
│ └──────────────────────────────────────────────────┘ │
│                                                        │
│ [➕ Ajouter une Règle]  [🔄 Rafraîchir]              │
│                                                        │
│ ✅ Règle créée: TABLE → 4143                          │
└────────────────────────────────────────────────────────┘
```

---

## 🚀 Fonctionnalités

### 1. Analyse Automatique

**Bouton**: "🤖 Analyser et Suggérer"

**Fonction**: Analyse le cache `product_category_cache` pour détecter les patterns:
- Type avec ≥ 5 produits identiques
- Confidence moyenne ≥ 85%
- Même category_code pour tous

**Résultat**: Affiche des cartes de suggestion avec:
- Type détecté
- Catégorie associée
- Statistiques (nombre, confidence, exemple)
- Boutons [✅ Créer Règle] [❌ Ignorer]

**SQL utilisé**:
```sql
SELECT 
    csv_type as product_type,
    category_code,
    category_path,
    COUNT(*) as count,
    AVG(confidence) as avg_confidence,
    MAX(title) as example_title
FROM product_category_cache
WHERE csv_type IS NOT NULL 
  AND csv_type != ''
  AND source = 'langgraph'
GROUP BY csv_type, category_code, category_path
HAVING count >= 5 AND avg_confidence >= 0.85
ORDER BY count DESC
```

---

### 2. Créer Règle Manuellement

**Bouton**: "➕ Ajouter une Règle"

**Formulaire**:
- Champ "Type de produit" (ex: NAPPES, SERVIETTES)
- Champ "Code Google" (ex: 4143)
- Validation en temps réel du code
- Affichage du category_path si code valide

**Validation**:
- ✅ Type non vide
- ✅ Code existe dans `google_taxonomy`
- ✅ Type pas déjà utilisé (UNIQUE)

---

### 3. Liste des Règles Actives

**Affichage**: Carte par règle avec:
- Type de produit
- Catégorie complète
- Code
- Statistiques d'utilisation
- Origine (manual ou auto_suggestion)
- Statut (actif/inactif)

**Actions**:
- **Modifier**: Permet de changer le code/catégorie (Type non modifiable)
- **Activer/Désactiver**: Toggle le statut `is_active`
- **Supprimer**: Supprime la règle (pas de popup, confirmation dans label)

---

## 📝 Méthodes Python dans `db.py`

### 1. `get_type_mapping(product_type)`

Récupère la règle pour un type.

```python
# Vérifie si une règle existe pour le type
mapping = db.get_type_mapping('TABLE')

if mapping:
    # mapping = {
    #   'category_code': '4143',
    #   'category_path': 'Maison et jardin > ...',
    #   'confidence': 1.0,
    #   'use_count': 127
    # }
```

**Comportement**:
- Incrémente automatiquement `use_count`
- Met à jour `updated_at`
- Retourne `None` si pas de règle ou règle inactive

---

### 2. `save_type_mapping(product_type, code, path, confidence, created_by)`

Crée ou met à jour une règle.

```python
success = db.save_type_mapping(
    'TABLE',
    '4143',
    'Maison et jardin > Linge > Linge de table > Nappes',
    confidence=1.0,
    created_by='manual'
)
```

**Comportement**:
- `INSERT OR REPLACE` (écrase si existe)
- `is_active = 1` par défaut
- Log: "💾 Type Mapping SAVED: TABLE → ..."

---

### 3. `update_type_mapping(mapping_id, code, path)`

Met à jour uniquement le code et le path d'une règle existante.

```python
success = db.update_type_mapping(
    mapping_id=1,
    category_code='500044',
    category_path='Maison et jardin > Linge > Linge de table'
)
```

**Comportement**:
- Met à jour `category_code`, `category_path` et `updated_at`
- Ne modifie PAS le `product_type` (intentionnel)
- Log: "✏️ Type Mapping modifié: ID 1 → ..."

**Note**: Pour changer le Type, il faut supprimer la règle et la recréer.

---

### 4. `get_all_type_mappings()`

Récupère toutes les règles (actives et inactives).

```python
rules = db.get_all_type_mappings()
# Retourne: [
#   {'id': 1, 'product_type': 'TABLE', 'category_code': '4143', ...},
#   {'id': 2, 'product_type': 'SERVIETTES', 'category_code': '4203', ...}
# ]
```

**Tri**: Par `use_count DESC` puis `product_type ASC`

---

### 5. `delete_type_mapping(mapping_id)`

Supprime une règle.

```python
success = db.delete_type_mapping(1)
# Log: "🗑️ Type Mapping supprimé: ID 1"
```

---

### 6. `toggle_type_mapping(mapping_id, is_active)`

Active ou désactive une règle.

```python
success = db.toggle_type_mapping(1, False)  # Désactiver
# Log: "🔄 Type Mapping désactivé: ID 1"

success = db.toggle_type_mapping(1, True)   # Activer
# Log: "🔄 Type Mapping activé: ID 1"
```

---

### 7. `analyze_cache_patterns(min_count, min_confidence)`

Analyse le cache et retourne les suggestions.

```python
suggestions = db.analyze_cache_patterns(min_count=5, min_confidence=0.85)
# Retourne: [
#   {
#     'product_type': 'TABLE',
#     'category_code': '4143',
#     'category_path': 'Maison et jardin > ...',
#     'count': 20,
#     'avg_confidence': 0.95,
#     'example_title': 'Nappe en coton - Argelos'
#   }
# ]
```

**Filtre**: Exclut les Types qui ont déjà une règle

---

## 🔄 Modifications dans `processor.py`

### Nouveau Flux de Catégorisation

```python
# ÉTAPE 0: Vérifier les règles Type → Catégorie (PRIORITAIRE!)
product_type = product_data.get('Type', '').strip()
type_mapping = None
if product_type:
    type_mapping = self.db.get_type_mapping(product_type)

if type_mapping:
    # ✅ RÈGLE TYPE trouvée - Utilisation directe
    category_code = type_mapping['category_code']
    category_path = type_mapping['category_path']
    confidence = type_mapping['confidence']
    rationale = f"Règle Type: {product_type} (utilisé {type_mapping['use_count']} fois)"
    needs_review = False
    
    logger.info(f"📋 {handle}: Catégorie depuis RÈGLE TYPE: {category_path}")
    
    # Sauvegarder dans le cache pour historique
    self.db.save_to_cache(..., source='type_mapping')
else:
    # ÉTAPE 1: Vérifier le cache produit
    cached_result = self.db.get_cached_category(product_data)
    
    if cached_result:
        # Cache produit
    else:
        # ÉTAPE 2: LangGraph
```

### Logs Améliorés

**Avec règle Type**:
```
📋 ARGECF_1492: Catégorie depuis RÈGLE TYPE: Maison et jardin > Linge > Linge de table > Nappes
✅ ARGECF_1492: Catégorie finale: ... (code: 4143)
  Confidence: 1.00 | Needs review: False
  Rationale: Règle Type: TABLE (utilisé 127 fois)
```

**Sans règle (cache ou LangGraph)**:
```
💾 ARGECF_1492: Catégorie depuis CACHE: ...
ou
🤖 ARGECF_1492: Appel LangGraph (pas dans le cache)
```

---

## 📚 Utilisation de l'Onglet "Règles Types"

### Scénario 1: Analyser et Créer des Règles Automatiquement

1. **Ouvrir l'onglet Taxonomie** → Cliquer sur **"Règles Types"**
2. **Cliquer sur "🤖 Analyser et Suggérer"**
3. Le système analyse le cache et affiche des suggestions:
   ```
   Type: TABLE
   → Maison et jardin > Linge > Linge de table > Nappes
   📊 20 produits | Conf moy: 95% | Ex: Nappe en coton...
   [✅ Créer Règle] [❌ Ignorer]
   ```
4. **Cliquer sur "✅ Créer Règle"**
5. Message: "✅ Règle créée: TABLE → 4143"
6. La règle apparaît dans "Règles Actives"

---

### Scénario 2: Ajouter une Règle Manuellement

1. **Cliquer sur "➕ Ajouter une Règle"**
2. Un formulaire s'affiche:
   - Type de produit: `[PLAIDS_______]`
   - Code Google: `[1985__]`
   - Validation: ✅ Maison et jardin > Linge > Literie > Couvertures
3. **Cliquer sur "💾 Créer Règle"**
4. Message: "✅ Règle créée: PLAIDS → 1985"
5. La règle apparaît dans "Règles Actives"

---

### Scénario 3: Désactiver Temporairement une Règle

1. Dans "Règles Actives", trouver la règle
2. **Cliquer sur "❌ Désactiver"**
3. Message: "✅ Règle désactivée"
4. La règle reste dans la liste mais n'est plus utilisée
5. Pour réactiver: **Cliquer sur "✅ Activer"**

---

### Scénario 4: Modifier une Règle Existante

1. Dans "Règles Actives", trouver la règle à modifier
2. **Cliquer sur "✏️ Modifier"**
3. Un formulaire s'affiche avec:
   - Type: `TABLE` (non modifiable, en gris)
   - Code Google: `[4143__]` (modifiable)
   - Validation: ✅ Maison et jardin > Linge > Linge de table > Nappes
4. Modifier le code: `500044`
5. Validation se met à jour: ✅ Maison et jardin > Linge > Linge de table
6. **Cliquer sur "💾 Sauvegarder"**
7. Message: "✅ Règle modifiée: 500044 → Maison et jardin > Linge..."
8. La règle est mise à jour dans "Règles Actives"

**Note**: Si vous devez changer le Type (ex: "TABLE" → "NAPPES"), vous devez supprimer la règle et en créer une nouvelle.

---

### Scénario 5: Supprimer une Règle

1. Dans "Règles Actives", trouver la règle
2. **Cliquer sur "🗑️ Supprimer"**
3. Message: "✅ Règle supprimée"
4. La règle disparaît de la liste
5. **Pas de popup de confirmation** (conformément à la demande)

---

## 📊 Statistiques et Métriques

### Dans les Règles

Chaque règle affiche:
- **use_count**: Nombre de fois que la règle a été utilisée
- **created_by**: `manual` ou `auto_suggestion`
- **is_active**: Oui/Non

### Exemple
```
Type: TABLE
→ Maison et jardin > Linge > Linge de table > Nappes
Code: 4143 | Confidence: 100%
📊 Utilisé 127 fois | Créé: manual | Actif: Oui
```

---

## 🎯 Workflow Complet

### Étape 1: Traiter vos premiers produits

1. Importez votre CSV
2. Lancez le traitement
3. Les produits sont catégorisés par LangGraph
4. Tout est sauvegardé dans `product_category_cache`

### Étape 2: Analyser les patterns

1. Ouvrez **Taxonomie → Règles Types**
2. Cliquez sur **"🤖 Analyser et Suggérer"**
3. Le système détecte:
   - Type "TABLE" → 20 produits → Code 4143
   - Type "SERVIETTES" → 15 produits → Code 4203
   - etc.

### Étape 3: Créer les règles

1. Pour chaque suggestion, cliquez **"✅ Créer Règle"**
2. Les règles sont créées et activées

### Étape 4: Traiter de nouveaux produits

1. Importez un nouveau CSV avec des nappes
2. Lancez le traitement
3. **Toutes les nappes utilisent la règle** (0 appel LLM!)
4. Logs:
   ```
   📋 nappe-1: Catégorie depuis RÈGLE TYPE: Nappes
   📋 nappe-2: Catégorie depuis RÈGLE TYPE: Nappes
   ...
   📋 nappe-100: Catégorie depuis RÈGLE TYPE: Nappes
   ```

---

## ⚡ Performance

### Comparaison avec/sans règles

| Opération | Sans règles | Avec règle Type |
|-----------|-------------|-----------------|
| **1er produit "Nappe X"** | LangGraph (10s) | LangGraph (10s) |
| **2ème produit "Nappe Y"** | Cache (0.01s) OU LangGraph (10s) | Règle (0.001s) |
| **100 nappes différentes** | 100-1000s (si titres différents) | 10s (1 LangGraph + 99 règles) |
| **Coût API** | 300-400 appels | 3-4 appels |
| **Économie** | - | **95-98%** |

---

## 🔍 Cas d'Usage

### Cas 1: Collection de Nappes

Vous avez 200 nappes avec des titres tous différents:
- "Nappe coton Argelos 160cm"
- "Nappe lin Beaumont 140cm"
- "Nappe soie Charente 180cm"
- etc.

**Sans règle**:
- Chaque nappe = nouveau `product_key` (hash différent)
- Cache ne fonctionne pas
- 200 appels LangGraph = 2000s (~33 minutes)

**Avec règle `TABLE → 4143`**:
- 200 nappes utilisent la règle
- 200 x 0.001s = 0.2s (~instant!)
- Économie: **99.99%**

---

### Cas 2: Types Variés

Vous vendez:
- 50 nappes (Type: TABLE)
- 30 serviettes (Type: SERVIETTES)
- 20 plaids (Type: DÉCO → devrait être PLAIDS)
- 10 thés (Type: THÉS)

**Stratégie**:
1. Créer règles pour TABLE, SERVIETTES
2. Corriger le Type "DÉCO" → "PLAIDS" dans le scraper
3. Créer règle pour PLAIDS
4. Laisser "THÉS" utiliser LangGraph (trop varié)

**Résultat**:
- 100 produits (TABLE + SERVIETTES + PLAIDS) = règles (instant)
- 10 produits (THÉS) = LangGraph (100s)
- Total: 100s au lieu de 1000s
- **Économie: 90%**

---

## 🛡️ Sécurité et Validation

### Validations Automatiques

1. **Code existe**: Vérifié dans `google_taxonomy` avant création
2. **Type unique**: `UNIQUE` constraint en SQL
3. **Type non vide**: Validation côté GUI
4. **Pas de doublons**: `INSERT OR REPLACE` écrase si existe

### Désactivation vs Suppression

**Désactiver**: 
- ✅ La règle reste dans la base (historique)
- ✅ `use_count` conservé
- ✅ Réactivable en 1 clic

**Supprimer**:
- ❌ La règle disparaît complètement
- ❌ Perte des statistiques
- ❌ Non récupérable

**Recommandation**: Préférer **désactiver** plutôt que supprimer

---

## 📈 Statistiques

### Colonne `use_count`

Chaque fois qu'une règle est utilisée:
```sql
UPDATE type_category_mapping
SET use_count = use_count + 1,
    updated_at = CURRENT_TIMESTAMP
WHERE product_type = ?
```

Permet de voir:
- Quelles règles sont les plus utilisées
- Si une règle n'est jamais utilisée (peut être supprimée)

---

## 🔄 Migration et Rétrocompatibilité

### Anciens Produits

Les produits déjà catégorisés dans `product_category_cache` continuent de fonctionner normalement.

### Nouveaux Produits

Si vous créez une règle `TABLE → 4143`:
- Les produits TYPE "TABLE" utiliseront la règle
- Ils seront quand même sauvegardés dans `product_category_cache` avec `source='type_mapping'`
- Cela permet de garder un historique complet

---

## 💾 Colonne `source` dans `product_category_cache`

Tous les produits ont maintenant:
```sql
source TEXT DEFAULT 'langgraph'
```

Valeurs possibles:
- `'type_mapping'` → Règle Type utilisée
- `'cache'` → Cache produit réutilisé (OBSOLÈTE, pas vraiment sauvegardé)
- `'langgraph'` → Catégorisé par LLM

**Utilité**: 
- Savoir d'où vient chaque catégorisation
- Filtrer dans les analyses (ex: "Quels produits viennent du LLM uniquement?")
- Statistiques: % de produits par règle vs LLM

---

## 🎯 Résumé

| Feature | Description |
|---------|-------------|
| **Table `type_category_mapping`** | Règles prioritaires Type → Catégorie |
| **Vérification 1** | Type mapping (0.001s) |
| **Vérification 2** | Cache produit (0.01s) |
| **Vérification 3** | LangGraph (5-10s) |
| **Économie** | 95-98% temps et coût pour types récurrents |
| **GUI** | Onglet "Règles Types" avec analyse auto + gestion |
| **Traçabilité** | Colonne `source` + `use_count` |
| **Pas de popup** | Tous les messages dans labels |

---

## 📝 Prochaines Étapes

### Immédiat
1. ✅ Traiter vos premiers produits (pour peupler le cache)
2. ✅ Analyser les patterns (bouton "Analyser et Suggérer")
3. ✅ Créer les règles suggérées
4. ✅ Traiter de nouveaux produits (utilisation des règles)

### Optionnel
- [ ] Export des règles en JSON/CSV
- [ ] Import de règles depuis un fichier
- [ ] Statistiques détaillées par règle
- [ ] Suggestions basées sur les Tags en plus du Type

---

**Version**: 1.0  
**Statut**: ✅ Implémenté et testé  
**Date**: 23 janvier 2026
