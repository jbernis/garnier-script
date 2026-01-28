# 📋 Guide des Logs LangGraph Détaillés

## Vue d'ensemble

Les logs ont été enrichis pour afficher **toutes les étapes** du processus de catégorisation LangGraph avec les réponses complètes des 2 agents.

---

## 📊 Structure des Logs

### 1. **AGENT 1 - Product Specialist** 🔍

```
================================================================================
📋 AGENT 1 - PRODUCT SPECIALIST - RÉPONSE COMPLÈTE:
  • product_type: Boudin de porte
  • usage: Isolation thermique et contre les courants d'air
  • material: Tissu, rembourrage
  • search_keywords: boudin, porte, isolation, textile, maison
================================================================================
```

**Ce que ça signifie**:
- L'Agent 1 analyse le produit (titre, type, tags) et extrait ses caractéristiques sémantiques
- Les `search_keywords` sont utilisés pour la recherche SQL des catégories candidates

---

### 2. **SQL Candidates** 📊

```
📊 Node: Récupération des candidates SQL...
  🔑 Keywords utilisés pour SQL: boudin, porte, isolation, textile, maison
  ✓ 15 catégories candidates trouvées
```

**Ce que ça signifie**:
- Les keywords de l'Agent 1 sont utilisés pour chercher dans la taxonomie Google Shopping
- Le SQL retourne les 15 catégories les plus pertinentes (avec bonus pour "Maison et jardin" et "Aliments, boissons et tabac")

---

### 3. **Candidates Disponibles** 📊

```
================================================================================
📊 CANDIDATES DISPONIBLES (15 catégories):
  1. [536] Maison et jardin
  2. [630] Maison et jardin > Linge > Textiles d'ambiance
  3. [3072] Maison et jardin > Arts de la table > ... > Distributeurs
  4. [609] Maison et jardin > Appareils électroménagers > Systèmes d'ouverture
  ... et 11 autres
================================================================================
```

**Ce que ça signifie**:
- Liste des catégories candidates que l'Agent 2 va évaluer
- Affiche seulement le Top 10 pour ne pas surcharger les logs

---

### 4. **AGENT 2 - Taxonomy Specialist** 🎯

```
📤 Taxonomy Agent - Réponse brute LLM: {"chosen_category":"Maison et jardin > Linge > Textiles d'ambiance","confidence":0.85,"rationale":"Boudin de porte textile"}...
================================================================================
🎯 AGENT 2 - TAXONOMY SPECIALIST - RÉPONSE COMPLÈTE:
  • chosen_category: Maison et jardin > Linge > Textiles d'ambiance
  • confidence: 0.85 (85%)
  • rationale: Boudin de porte textile pour isolation
================================================================================
```

**Ce que ça signifie**:
- **Réponse brute LLM**: JSON retourné par Gemini (tronqué à 200 caractères)
- **chosen_category**: Catégorie choisie parmi les candidates
- **confidence**: Niveau de certitude (0-1)
- **rationale**: Justification du choix

---

### 5. **Validation** ✅

```
✅ Node: Validation...
✓ Validation OK: 630 - Maison et jardin > Linge > Textiles d'ambiance (3 niveaux)
```

**Ce que ça signifie**:
- Vérification que la catégorie existe dans la taxonomie
- Vérification qu'elle a au moins 3 niveaux (pas trop générale)
- Si validation KO → retry automatique

---

### 6. **Résultat Final** 📦

```
📦 ARGECF_1492: Catégorie finale: Maison et jardin > Linge > Textiles d'ambiance (code: 630)
  Confidence: 0.85 | Needs review: False
  Rationale: Boudin de porte textile pour isolation
```

---

## 🔴 Logs d'Erreur

### JSON Tronqué (Partiel)

```
📤 Taxonomy Agent - Réponse brute LLM: {"chosen_category":"Maison et jardin > ... > Portes-encens","
⚠️ JSON partiel: chosen_category OK mais confidence/rationale par défaut
→ Utilise la catégorie extraite avec confidence=0.6
```

**Ce qui se passe**:
- Le LLM a retourné un JSON incomplet (tronqué)
- Le système récupère quand même le `chosen_category` et utilise des valeurs par défaut pour le reste

### JSON Totalement Cassé

```
❌ Fallback complet: Première catégorie prioritaire par défaut
→ Confidence: 0.30 | Needs review: True
```

**Ce qui se passe**:
- Aucun JSON valide n'a pu être extrait
- Le système utilise un fallback intelligent basé sur les mots-clés du product_type
- La confidence est très basse (30%) et le produit est flaggé pour révision

---

## 🎯 Interprétation

### ✅ Bon Résultat

```
Confidence: 0.85+ | Needs review: False
```
→ Catégorie fiable, peut être utilisée directement

### ⚠️ Résultat Incertain

```
Confidence: 0.60-0.79 | Needs review: True
```
→ Catégorie probable mais à vérifier manuellement

### 🔴 Résultat Douteux

```
Confidence: < 0.60 | Needs review: True
```
→ Catégorie peu fiable, révision OBLIGATOIRE

---

## 📝 Exemples Complets

### Exemple 1: Catégorisation Réussie

```
📋 AGENT 1: product_type=Plaid, usage=Protection/confort, keywords=plaid,couverture,literie
📊 SQL: 15 candidates (bonus "Maison et jardin")
🎯 AGENT 2: chosen="Maison et jardin > Linge > Literie > Couvertures", confidence=0.95
✅ Validation OK (4 niveaux)
📦 Résultat: Couvertures (code: 574) | conf: 95% | review: False
```

### Exemple 2: JSON Tronqué mais Récupéré

```
📋 AGENT 1: product_type=Boudin de porte, keywords=boudin,porte,isolation
📊 SQL: 15 candidates
📤 AGENT 2 Réponse: {"chosen_category":"... > Portes-encens","
⚠️ JSON partiel récupéré
🎯 AGENT 2: chosen="... > Portes-encens", confidence=0.60 (défaut)
✅ Validation OK (4 niveaux)
📦 Résultat: Portes-encens | conf: 60% | review: True
```

### Exemple 3: Catégorie Trop Générale (Retry)

```
📋 AGENT 1: product_type=Thé, keywords=thé,infusion,boisson
📊 SQL: 15 candidates
🎯 AGENT 2: chosen="Aliments, boissons et tabac", confidence=0.70
⚠️ Validation KO: Catégorie trop générale (1 niveau)
🔄 Retry 1/2
📊 SQL: Seulement catégories ≥3 niveaux
🎯 AGENT 2: chosen="Aliments... > Boissons > Thé et infusions", confidence=0.90
✅ Validation OK (3 niveaux)
📦 Résultat: Thé et infusions | conf: 90% | review: False
```

---

## 🔧 Débogage

Si vous voyez des erreurs répétées:

### 1. **JSON toujours tronqué**
→ Augmenter `max_tokens` dans `taxonomy_agent.py` (actuellement 1200)

### 2. **Catégories trop générales**
→ Les catégories < 3 niveaux sont automatiquement rejetées (retry)

### 3. **Confidence toujours basse**
→ Vérifier que les `search_keywords` de l'Agent 1 sont pertinents

### 4. **Mauvaises catégories**
→ Vérifier les logs de l'Agent 1 (product_type, usage) et les candidates SQL

---

## 📌 Points Clés

1. **Agent 1 (Product)**: Définit le produit sémantiquement
2. **SQL**: Trouve les candidates avec les keywords enrichis
3. **Agent 2 (Taxonomy)**: Choisit la meilleure catégorie parmi les candidates
4. **Validation**: Vérifie spécificité (≥3 niveaux) et existence
5. **Retry**: Si validation KO, retry avec catégories plus spécifiques

---

## 🎯 Prochaine Fois

Regardez ces sections dans les logs:
1. **AGENT 1** → Les keywords sont-ils pertinents?
2. **CANDIDATES** → La bonne catégorie est-elle dans la liste?
3. **AGENT 2** → Le choix est-il logique?
4. **Validation** → Pourquoi OK/KO?
