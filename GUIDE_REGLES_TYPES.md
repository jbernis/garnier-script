# Guide Rapide - Règles Types → Catégorie

## 🎯 Objectif

Créer des règles pour que les produits du même Type (ex: "TABLE") utilisent automatiquement la même catégorie Google Shopping, **sans appeler le LLM**.

---

## 🚀 Avantages

### Exemple: 100 Nappes

**Sans règle**:
- 100 appels LangGraph
- ~1000 secondes (16 minutes)
- 300-400 appels API

**Avec règle `TABLE → 4143`**:
- 1 appel LangGraph (1ère nappe)
- 99 utilisations de la règle
- **10 secondes total**
- **Économie: 99%** 🎉

---

## 📋 Comment Ça Marche?

### Flux de Vérification

Pour chaque produit:
1. **Règle Type?** → Oui → Utiliser directement (instant!)
2. **Dans cache?** → Oui → Utiliser cache
3. **Nouveau?** → Appeler LangGraph (5-10s)

---

## 🎨 Accès à l'Interface

1. Lancer l'application: `python run_gui.py`
2. Cliquer sur **"📊 Taxonomie"** dans la sidebar
3. Cliquer sur l'onglet **"Règles Types"**

---

## 🔍 Méthode 1: Analyse Automatique (Recommandé)

### Prérequis
Vous devez avoir déjà traité des produits (pour peupler le cache).

### Étapes

1. **Cliquez sur "🤖 Analyser et Suggérer"**
   
   Le système analyse `product_category_cache` et détecte les patterns:
   - Type avec ≥ 5 produits
   - Même catégorie pour tous
   - Confidence moyenne ≥ 85%

2. **Résultats affichés**
   
   Des cartes de suggestion apparaissent:
   ```
   Type: TABLE
   → Maison et jardin > Linge > Linge de table > Nappes (code: 4143)
   📊 20 produits | Conf moy: 95% | Ex: Nappe en coton - Argelos
   [✅ Créer Règle] [❌ Ignorer]
   ```

3. **Accepter ou Ignorer**
   
   - **✅ Créer Règle**: Crée la règle et l'active immédiatement
   - **❌ Ignorer**: Ferme la suggestion

4. **Confirmation**
   
   Message: "✅ Règle créée: TABLE → 4143"

---

## ➕ Méthode 2: Ajout Manuel

### Quand l'utiliser?

- Vous connaissez déjà la catégorie correcte
- Vous voulez créer une règle avant de traiter les produits
- Le type n'a pas assez de produits pour l'analyse auto (< 5)

### Étapes

1. **Cliquez sur "➕ Ajouter une Règle"**

2. **Remplir le formulaire**
   
   - Type de produit: `PLAIDS`
   - Code Google: `1985`
   
   La validation se fait en temps réel:
   - Si code valide: ✅ Maison et jardin > Linge > Literie > Couvertures
   - Si code invalide: ❌ Code non trouvé

3. **Cliquez sur "💾 Créer Règle"**

4. **Confirmation**
   
   Message: "✅ Règle créée: PLAIDS → 1985"
   
5. **Annuler**
   
   Si vous changez d'avis: **"❌ Annuler"**

---

## 🎛️ Gérer les Règles Existantes

### Voir toutes les règles

La section **"📋 Règles Actives"** affiche toutes les règles (actives et inactives).

Pour chaque règle:
- Type de produit
- Catégorie complète
- Code
- Statistiques (combien de fois utilisée)
- Origine (manual ou auto_suggestion)
- Statut (actif/inactif)

---

### Modifier une règle

**Bouton**: "✏️ Modifier"

**Formulaire**:
- Type de produit (non modifiable, affiché en gris)
- Code Google (modifiable)
- Validation en temps réel du nouveau code
- Affichage du nouveau category_path

**Quand l'utiliser**:
- Corriger un code incorrect
- Changer de catégorie pour un type existant
- Affiner la catégorisation

**Exemple**:
```
Règle actuelle: TABLE → 4143 (Nappes)
Modifier pour: TABLE → 500044 (Linge de table)
```

**⚠️ Important**: Le Type ne peut pas être modifié. Si vous devez changer le Type, supprimez la règle et recréez-en une nouvelle.

---

### Désactiver une règle (temporaire)

**Bouton**: "❌ Désactiver"

**Effet**:
- La règle reste dans la base
- Elle n'est plus utilisée pour les nouveaux produits
- Les produits déjà catégorisés ne changent pas

**Réactiver**: Cliquez sur "✅ Activer"

**Quand l'utiliser**:
- Tester temporairement sans règle
- Changer de stratégie de catégorisation

---

### Supprimer une règle (permanent)

**Bouton**: "🗑️ Supprimer"

**Effet**:
- La règle disparaît complètement
- Perte des statistiques d'utilisation
- Non récupérable

**⚠️ Attention**: Pas de popup de confirmation! Pas d'undo!

**Quand l'utiliser**:
- Règle incorrecte ou obsolète
- Type qui n'existe plus

---

### Rafraîchir l'affichage

**Bouton**: "🔄 Rafraîchir"

Recharge la liste des règles depuis la base de données.

---

## 📊 Comprendre les Statistiques

### Exemple de Règle

```
Type: TABLE
→ Maison et jardin > Linge > Linge de table > Nappes
Code: 4143 | Confidence: 100%
📊 Utilisé 127 fois | Créé: manual | Actif: Oui
```

**Signification**:
- **Type: TABLE** → Tous les produits avec Type="TABLE"
- **Code: 4143** → Catégorie Google Shopping
- **Confidence: 100%** → Règle manuelle (toujours 100%)
- **Utilisé 127 fois** → 127 produits ont utilisé cette règle
- **Créé: manual** → Créée manuellement (vs auto_suggestion)
- **Actif: Oui** → La règle est active

---

## 🔄 Workflow Complet

### Étape 1: Premier Traitement (Peupler le Cache)

```bash
# 1. Importez votre CSV
# 2. Configurez batch_size = 10
# 3. Lancez le traitement
# → Tous les produits sont catégorisés par LangGraph
# → Tout est sauvegardé dans product_category_cache
```

### Étape 2: Analyser et Créer des Règles

```
Taxonomie → Règles Types
↓
[🤖 Analyser et Suggérer]
↓
Suggestions affichées:
• TABLE → 4143 (20 produits)
• SERVIETTES → 4203 (15 produits)
↓
[✅ Créer Règle] pour chaque
↓
✅ Règles créées!
```

### Étape 3: Traiter de Nouveaux Produits

```bash
# Importez un nouveau CSV
# Lancez le traitement
# → Les produits avec Type="TABLE" utilisent la règle (instant!)
# → Les autres types passent par cache ou LangGraph
```

### Résultat dans les Logs

```
📋 nappe-1: Catégorie depuis RÈGLE TYPE: Maison et jardin > ... > Nappes
📋 nappe-2: Catégorie depuis RÈGLE TYPE: Maison et jardin > ... > Nappes
💾 plaid-1: Catégorie depuis CACHE: Maison et jardin > ... > Couvertures
🤖 coupe-froid-1: Appel LangGraph (pas dans le cache)
```

---

## 💡 Bonnes Pratiques

### 1. Types Spécifiques

**❌ Mauvais**:
- Type: "DÉCO" (trop générique)
- Type: "LINGE" (trop vague)
- Type: "PRODUITS" (inutile)

**✅ Bon**:
- Type: "NAPPES"
- Type: "SERVIETTES_TABLE"
- Type: "PLAIDS"
- Type: "COUPE_FROID"

**Règle**: Plus le Type est spécifique, mieux c'est!

---

### 2. Corriger les Types dans les Scrapers

Si vous voyez `Type: "DÉCO"` pour des plaids:

**Modifier le scraper**:
```python
# garnier/scraper-generate-csv.py
if 'plaid' in title.lower():
    type_value = "PLAIDS"
elif 'coupe' in title.lower() and 'froid' in title.lower():
    type_value = "COUPE_FROID"
else:
    type_value = category  # Catégorie du site
```

Puis re-scraper les produits pour avoir des Types corrects.

---

### 3. Vérifier les Règles Régulièrement

1. Ouvrez **Taxonomie → Règles Types**
2. Regardez les statistiques `use_count`
3. Si une règle n'est jamais utilisée (use_count = 0):
   - Soit le Type n'existe plus dans vos produits
   - Soit le Type est mal orthographié
   - → Supprimer ou corriger

---

### 4. Analyser Après Chaque Import

**Workflow recommandé**:
```
1. Importer CSV
2. Traiter les produits
3. Taxonomie → Règles Types → Analyser
4. Créer les règles suggérées
5. Prochain import → Les règles s'appliquent automatiquement!
```

---

## ⚠️ Limitations

### 1. Types Multiples

Si un produit peut être dans plusieurs catégories selon le contexte:
- Ex: "Thé Earl Grey" vs "Thé Vert" (catégories différentes?)

**Solution**: Créer des Types plus spécifiques:
- Type: "THÉ_NOIR" → Code X
- Type: "THÉ_VERT" → Code Y

---

### 2. Évolution des Catégories

Si Google change sa taxonomie:
- Les codes peuvent devenir obsolètes
- Vous devrez mettre à jour les règles manuellement

**Solution**: Vérifier régulièrement les codes avec Google Shopping Taxonomy

---

## 🔍 Dépannage

### Problème: "Aucune suggestion trouvée"

**Causes**:
1. Pas assez de produits dans le cache (< 5 par type)
2. Confidence trop basse (< 85%)
3. Types trop variés (pas de pattern)

**Solution**: Traiter plus de produits d'abord

---

### Problème: Règle pas utilisée

**Causes**:
1. Type dans la règle ≠ Type dans les produits (casse différente?)
2. Règle désactivée (`is_active = 0`)
3. Type mal orthographié

**Solution**: 
- Vérifier l'orthographe exacte du Type
- Vérifier que la règle est active
- Regarder les logs: `📋 ... depuis RÈGLE TYPE` doit apparaître

---

### Problème: "Code non trouvé"

**Cause**: Le code n'existe pas dans `google_taxonomy`

**Solution**: Vérifier le code sur Google Shopping Taxonomy officielle

---

## 📖 Commandes SQL Utiles

### Voir toutes les règles

```sql
SELECT * FROM type_category_mapping 
WHERE is_active = 1 
ORDER BY use_count DESC;
```

### Voir les produits d'un Type

```sql
SELECT title, category_code, source 
FROM product_category_cache 
WHERE csv_type = 'TABLE' 
LIMIT 10;
```

### Statistiques par source

```sql
SELECT source, COUNT(*) as count 
FROM product_category_cache 
GROUP BY source;
```

Résultat attendu:
```
type_mapping | 200
cache        | 0
langgraph    | 50
```

---

## 🎯 Résumé en 3 Points

1. **Règles Type → Catégorie** = 0 appel LLM pour types récurrents
2. **Onglet "Règles Types"** = Analyse auto + Gestion manuelle
3. **Économie** = 95-98% de temps et coût pour produits similaires

---

**Version**: 1.0  
**Date**: 23 janvier 2026  
**Fichiers modifiés**:
- `apps/ai_editor/db.py` (+180 lignes)
- `apps/ai_editor/processor.py` (+30 lignes)
- `apps/gui/taxonomy_window.py` (+300 lignes)
