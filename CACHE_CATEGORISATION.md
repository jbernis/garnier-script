# 💾 Cache de Catégorisation Google Shopping

## Vue d'ensemble

Le système de cache permet de **réduire les coûts LLM** et **accélérer le traitement** en mémorisant les catégorisations réussies des produits identiques.

---

## 🔑 Fonctionnement

### 1. **Clé Unique du Produit**

Chaque produit est identifié par un hash MD5 basé sur:
- `Title` (titre du produit)
- `Type` (type de produit)
- `Vendor` (fournisseur)

**Exemple**:
```python
Title: "NAPPE EN COTON - ARGELOS"
Type: "Nappes"
Vendor: "Garnier-Thiebaut"

→ product_key = MD5("nappe en coton - argelos|nappes|garnier-thiebaut")
→ product_key = "a3f5c8d9e1b2..."
```

**Pourquoi ces 3 champs ?**
- `Title` : Identité principale du produit
- `Type` : Contexte catégoriel
- `Vendor` : Différenciation (même titre, différents fournisseurs)

---

### 2. **Mise en Cache (Sauvegarde)**

#### Conditions pour être mis en cache

Un produit est sauvegardé dans le cache **SEULEMENT SI**:
- ✅ `confidence >= 0.8` (80%)
- ✅ `category_code` valide
- ✅ Catégorisation réussie (pas d'erreur)

#### Ce qui est sauvegardé

```sql
product_key              -- Hash unique
title                   -- Titre original
product_type            -- Type original
vendor                  -- Vendor original
category_code           -- Code Google Shopping (ex: 630)
category_path           -- Chemin complet (ex: "Maison et jardin > Linge > Textiles d'ambiance")
confidence              -- Confidence (0.8-1.0)
rationale               -- Justification
created_at              -- Date de première catégorisation
last_used_at            -- Date de dernière utilisation
use_count               -- Nombre de fois réutilisé
```

---

### 3. **Récupération du Cache (Lecture)**

Lors du traitement d'un produit:

```
1. Générer product_key
2. Chercher dans product_category_cache
3. SI TROUVÉ:
   → Utiliser category_code/category_path du cache
   → Marquer last_used_at = now
   → Incrémenter use_count
   → Rationale += "[FROM CACHE]"
   → SKIP LangGraph (économie LLM) ✅
4. SI NON TROUVÉ:
   → Appeler LangGraph
   → Catégoriser normalement
```

---

## ⬆️ Catégorie Parente (Fallback Intelligent)

### Problème

Si la confidence est **basse** (< 50%), la catégorie spécifique peut être incorrecte.

**Exemple problématique**:
```
Produit: "Boudin de porte"
Catégorie LangGraph: "Maison et jardin > Appareils électroménagers > Systèmes d'ouverture"
Confidence: 40% ⚠️

→ Catégorie probablement fausse!
```

### Solution: Remonter au Parent

Au lieu d'utiliser une catégorie spécifique incertaine, on remonte d'**un niveau**:

```
Catégorie originale:
"Maison et jardin > Appareils électroménagers > Systèmes d'ouverture" (4 niveaux)
Confidence: 40% ⚠️

↓ Remonter au parent

Catégorie parente:
"Maison et jardin > Appareils électroménagers" (3 niveaux)
Confidence: 40% (inchangée)
Needs review: True ✅
```

**Avantages**:
- ✅ Catégorie moins spécifique = moins de risque d'erreur
- ✅ Toujours dans la bonne branche taxonomique
- ✅ Flaggé pour révision manuelle

### Seuil de Confidence

```python
CONFIDENCE_THRESHOLD = 0.5  # 50%
```

**Comportement**:

| Confidence | Action | Exemple |
|------------|--------|---------|
| **≥ 80%** | Utiliser catégorie spécifique + **METTRE EN CACHE** | "... > Couvertures" |
| **50-79%** | Utiliser catégorie spécifique + **needs_review** | "... > Couvertures" ⚠️ |
| **< 50%** | **REMONTER AU PARENT** + needs_review | "... > Literie" ⬆️ |
| **< 30%** | Catégorie très générique (fallback) | "Maison et jardin" |

---

## 🔄 Flux Complet

### Cas 1: Cache HIT (Produit Identique)

```
1. Produit: "NAPPE COTON 160CM" (Garnier-Thiebaut)
2. Générer product_key
3. Chercher dans cache
4. ✅ TROUVÉ: category_path="Maison et jardin > Arts de la table > Linge de table > Nappes"
5. Utiliser directement (SKIP LangGraph)
6. Incrémenter use_count
7. Sauvegarder dans CSV

📊 Résultat: 0 appel LLM | Temps: ~1ms
```

---

### Cas 2: Cache MISS + Haute Confidence

```
1. Produit: "PLAID CACHEMIRE 140X200" (nouveau)
2. Générer product_key
3. Chercher dans cache
4. ❌ PAS TROUVÉ
5. Appeler LangGraph (Agent 1 + SQL + Agent 2)
6. Résultat: category_path="Maison et jardin > Linge > Literie > Couvertures"
   Confidence: 95%
7. ✅ Confidence >= 80% → SAUVEGARDER DANS CACHE
8. Sauvegarder dans CSV

📊 Résultat: 2 appels LLM | Temps: ~3s
🎯 Prochaine fois: Cache HIT (0 appel LLM)
```

---

### Cas 3: Cache MISS + Confidence Basse

```
1. Produit: "BOUDIN DE PORTE TISSU" (nouveau)
2. Générer product_key
3. Chercher dans cache
4. ❌ PAS TROUVÉ
5. Appeler LangGraph
6. Résultat initial: category_path="Maison et jardin > Appareils électroménagers > Systèmes d'ouverture"
   Confidence: 45% ⚠️
7. ⬆️ Confidence < 50% → REMONTER AU PARENT
8. Catégorie finale: category_path="Maison et jardin > Appareils électroménagers"
   Confidence: 45% (inchangée)
   Needs review: True
9. ❌ NE PAS mettre en cache (confidence < 80%)
10. Sauvegarder dans CSV avec flag review

📊 Résultat: 2 appels LLM | Temps: ~3s
⚠️ Révision manuelle requise
```

---

### Cas 4: Cache MISS + Confidence Moyenne

```
1. Produit: "MUG PORCELAINE FLEURS" (nouveau)
2. ❌ PAS dans cache
3. Appeler LangGraph
4. Résultat: category_path="Maison et jardin > Arts de la table > Vaisselle > Mugs et tasses"
   Confidence: 70%
5. ✅ Confidence >= 50% → Utiliser catégorie spécifique
6. ❌ Confidence < 80% → NE PAS mettre en cache
7. Needs review: True (70% < 80%)
8. Sauvegarder dans CSV

📊 Résultat: 2 appels LLM | Temps: ~3s
⚠️ Révision manuelle suggérée
```

---

## 📊 Statistiques du Cache

### Consultation

```python
from apps.ai_editor.db import AIPromptsDB

db = AIPromptsDB()
stats = db.get_cache_stats()

print(f"Total produits en cache: {stats['total_entries']}")
print(f"Confidence moyenne: {stats['avg_confidence']:.2%}")
print(f"Produit le plus utilisé: {stats['max_uses']} fois")
```

**Exemple de sortie**:
```
Total produits en cache: 245
Confidence moyenne: 89.3%
Produit le plus utilisé: 12 fois
```

### Logs

#### Cache HIT
```
✅ Cache HIT: NAPPE EN COTON - ARGELOS → Maison et jardin > Arts de la table > Linge de table > Nappes
💾 ARGECF_1492: Catégorie depuis CACHE: Maison et jardin > ... > Nappes
```

#### Cache MISS
```
❌ Cache MISS: PLAID CACHEMIRE 140X200
🤖 ARGECF_1493: Appel LangGraph (pas dans le cache)
```

#### Sauvegarde Cache
```
💾 Cache SAVED: PLAID CACHEMIRE 140X200 → Maison et jardin > Linge > Literie > Couvertures (conf: 0.95)
```

#### Catégorie Parente
```
⬆️ ARGECF_1494: Confidence basse (45%) → Catégorie parente
  Avant: Maison et jardin > Appareils électroménagers > Systèmes d'ouverture
  Après: Maison et jardin > Appareils électroménagers
```

---

## 🎯 Avantages du Système

### 1. **Réduction des Coûts LLM**

**Sans cache**:
- 100 produits identiques = 200 appels LLM (2 agents × 100)
- Coût: ~$0.20 (selon le modèle)

**Avec cache**:
- 100 produits identiques = 2 appels LLM (première fois seulement)
- Coût: ~$0.002
- **Économie: 99%** 💰

### 2. **Amélioration des Performances**

- **Cache HIT**: ~1ms (lecture SQL)
- **Cache MISS**: ~3s (2 appels LLM)
- **Gain**: 3000x plus rapide

### 3. **Fiabilité Améliorée**

- Catégories parentales pour confidence basse
- Révision manuelle suggérée si incertain
- Pas de catégorisation trop spécifique et fausse

### 4. **Cohérence**

- Même produit = même catégorie (toujours)
- Pas de variation entre les imports
- Traçabilité complète (use_count, last_used_at)

---

## 🔧 Configuration

### Ajuster le Seuil de Cache

Par défaut: `min_confidence = 0.8` (80%)

**Pour mettre en cache plus de produits** (moins strict):
```python
self.db.save_to_cache(
    product_data,
    category_code,
    category_path,
    confidence,
    rationale,
    min_confidence=0.7  # 70% au lieu de 80%
)
```

**Risque**: Catégories moins fiables dans le cache

---

### Ajuster le Seuil de Catégorie Parente

Par défaut: `CONFIDENCE_THRESHOLD = 0.5` (50%)

**Pour remonter plus souvent au parent** (plus prudent):
```python
CONFIDENCE_THRESHOLD = 0.6  # 60% au lieu de 50%
```

**Pour remonter moins souvent** (plus spécifique):
```python
CONFIDENCE_THRESHOLD = 0.4  # 40% au lieu de 50%
```

---

## 📋 Structure de la Table Cache

```sql
CREATE TABLE product_category_cache (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    product_key TEXT NOT NULL UNIQUE,        -- Hash MD5 unique
    title TEXT NOT NULL,                     -- Titre original
    product_type TEXT,                       -- Type original
    vendor TEXT,                             -- Vendor original
    category_code TEXT NOT NULL,             -- Code Google (ex: 630)
    category_path TEXT NOT NULL,             -- Chemin complet
    confidence REAL NOT NULL,                -- Confidence (0.8-1.0)
    rationale TEXT,                          -- Justification
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_used_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    use_count INTEGER DEFAULT 1              -- Nombre d'utilisations
)
```

### Index pour Performance

```sql
CREATE INDEX idx_product_category_cache_key 
ON product_category_cache(product_key)
```

→ Recherche ultra-rapide par clé (O(1))

---

## 🧪 Tests Recommandés

### Test 1: Cache HIT
1. Importer un CSV avec 10 nappes identiques
2. Vérifier que seule la 1ère appelle LangGraph
3. Vérifier que use_count = 10 après traitement

### Test 2: Catégorie Parente
1. Créer un produit ambigu (ex: "Boudin de porte")
2. Vérifier que confidence < 50%
3. Vérifier que la catégorie finale est le parent
4. Vérifier needs_review = True

### Test 3: Cache Performance
1. Importer 100 produits identiques
2. Mesurer le temps total
3. Comparer avec/sans cache
4. Vérifier l'économie de coûts LLM

---

## 🚀 Prochaines Améliorations

### 1. **Cache par Similarité**
Au lieu de hash exact, utiliser une similarité de texte:
```python
if similarity(title1, title2) > 0.95:
    use_cached_category()
```

### 2. **Expiration du Cache**
Supprimer les entrées non utilisées depuis N jours:
```sql
DELETE FROM product_category_cache
WHERE last_used_at < datetime('now', '-90 days')
```

### 3. **Cache Multi-Niveaux**
Catégorie parente aussi en cache pour fallback rapide

### 4. **Statistiques Avancées**
Dashboard avec:
- Taux de cache hit
- Économies LLM estimées
- Catégories les plus fréquentes

---

## 🎯 Résumé

| Fonctionnalité | Seuil | Action |
|----------------|-------|--------|
| **Mise en cache** | Confidence ≥ 80% | Sauvegarder pour réutilisation |
| **Catégorie parente** | Confidence < 50% | Remonter d'un niveau |
| **Needs review** | Confidence < 80% | Flaggé pour révision |
| **Cache lookup** | Toujours | Avant chaque LangGraph |

**Objectif**: Maximiser la qualité et minimiser les coûts! 🎯💰
