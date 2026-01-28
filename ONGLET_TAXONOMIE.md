# 📊 Nouvel Onglet: Gestion de la Taxonomie

## Vue d'ensemble

Un nouvel onglet **"Taxonomie"** a été ajouté à l'interface graphique pour **visualiser, rechercher et modifier** toutes les catégorisations Google Shopping.

---

## 🎯 Fonctionnalités

### 1. **Sauvegarde Automatique**

**TOUS les produits** traités (test ou batch) sont maintenant sauvegardés dans la table `product_category_cache`:

- ✅ **Avant**: Seulement les produits avec confidence >= 80%
- ✅ **Après**: **TOUS les produits**, quelle que soit la confidence

**Nouvelles colonnes ajoutées**:
- `original_category_code`: Code Google fourni par le LLM (avant fallback parent)
- `original_category_path`: Chemin complet fourni par le LLM (avant fallback parent)
- `csv_type`: Type du produit tel qu'il apparaît dans le CSV d'import

---

### 2. **Recherche**

🔍 **Barre de recherche** pour filtrer par:
- Nom du produit (titre)
- Type du produit (Type CSV)
- Vendor

**Exemples**:
```
"NAPPE"       → Trouve toutes les nappes
"Thé"         → Trouve tous les thés
"Garnier"     → Trouve tous les produits Garnier-Thiebaut
```

---

### 3. **Visualisation**

📊 **Tableau avec colonnes**:

| Colonne | Description |
|---------|-------------|
| **ID** | ID unique dans la base |
| **Titre** | Titre du produit |
| **Type CSV** | Type du produit dans le CSV original |
| **Vendor** | Fournisseur |
| **Catégorie Google** | Catégorie finale utilisée |
| **Code** | Code Google Shopping (ex: 630) |
| **Original LLM** | Catégorie fournie par le LLM (avant fallback) |
| **Conf %** | Niveau de confiance (0-100%) |
| **Utilisations** | Nombre de fois que le cache a été utilisé |

---

### 4. **Modification**

✏️ **Double-clic** sur une ligne pour modifier:
- **Code Google Shopping**: Changer la catégorie
- **Confidence**: Ajuster le niveau de confiance (0-1)

**Validation automatique**:
- Vérification que le code existe dans la taxonomie Google
- Affichage du chemin complet de la catégorie
- Mise à jour automatique du path quand le code change

**Interface d'édition**:
- Entrée de texte pour le code
- Slider pour ajuster la confidence (0-1)
- Affichage en temps réel de la catégorie correspondante
- Validation avant sauvegarde

---

### 5. **Suppression**

🗑️ **Bouton Supprimer** pour retirer une entrée:
- Confirmation obligatoire avant suppression
- Suppression permanente de la base de données

**Quand supprimer ?**
- Produit obsolète qui n'est plus vendu
- Erreur de catégorisation à corriger en re-processant
- Tests qui polluent la base

---

### 6. **Export CSV**

📥 **Bouton Exporter CSV** pour télécharger:
- Toutes les catégorisations en CSV
- Format compatible Excel/Google Sheets
- Colonnes: ID, Titre, Type, Vendor, Catégorie, Code, Original LLM, Confidence, Rationale, Utilisations, Dates

**Utilité**:
- Analyser les catégorisations hors ligne
- Partager avec l'équipe
- Faire des statistiques dans Excel

---

### 7. **Statistiques**

📊 **Affichage en temps réel**:
```
📊 Total: 245 produits | Confidence moyenne: 89.3% | Max utilisations: 12
```

**Informations**:
- **Total produits**: Nombre total d'entrées dans la base
- **Confidence moyenne**: Qualité globale des catégorisations
- **Max utilisations**: Produit le plus réutilisé (efficacité du cache)

---

## 🔄 Flux Complet

### Cas 1: Traitement d'un Nouveau Produit

```
1. Utilisateur importe un CSV avec "NAPPE COTON 160CM"
2. Traitement (Test ou Batch) → LangGraph catégorise
3. Résultat LLM: "Maison et jardin > Arts de la table > Linge de table > Nappes" (conf: 95%)
4. Aucun fallback parent (conf >= 50%)
5. ✅ SAUVEGARDE dans product_category_cache:
   - category_code: 3320
   - category_path: "Maison et jardin > Arts de la table > Linge de table > Nappes"
   - original_category_code: 3320 (identique)
   - original_category_path: "..." (identique)
   - confidence: 0.95
   - csv_type: "Nappes"
6. Visible immédiatement dans l'onglet Taxonomie
```

---

### Cas 2: Traitement avec Fallback Parent

```
1. Utilisateur importe "BOUDIN DE PORTE TISSU"
2. Traitement → LangGraph catégorise
3. Résultat LLM: "Maison et jardin > Appareils électroménagers > Systèmes d'ouverture" (conf: 45%)
4. ⚠️ Confidence < 50% → Fallback parent
5. Catégorie finale: "Maison et jardin > Appareils électroménagers"
6. ✅ SAUVEGARDE dans product_category_cache:
   - category_code: 609 (parent)
   - category_path: "Maison et jardin > Appareils électroménagers" (parent)
   - original_category_code: 8042 (original LLM)
   - original_category_path: "... > Systèmes d'ouverture" (original LLM)
   - confidence: 0.45
   - csv_type: "Décoration"
7. Dans l'onglet Taxonomie:
   - Colonne "Catégorie": Parent (609)
   - Colonne "Original LLM": LLM complet (8042)
   → L'utilisateur VOIT ce que le LLM avait proposé initialement!
```

---

### Cas 3: Modification Manuelle

```
1. Utilisateur ouvre l'onglet Taxonomie
2. Recherche "boudin" → Trouve le produit
3. Double-clic sur la ligne
4. Fenêtre d'édition s'ouvre:
   - Code actuel: 609 ("Maison et jardin > Appareils électroménagers")
   - Confidence: 45%
5. Utilisateur change:
   - Code: 630 ("Maison et jardin > Linge > Textiles d'ambiance")
   - Confidence: 85%
6. Validation automatique: ✅ Code 630 existe
7. Sauvegarde
8. ✅ Prochain import du même produit:
   - Cache HIT avec la nouvelle catégorie 630
   - Pas d'appel LLM (économie)
```

---

## 📋 Structure de la Table

### Anciennes Colonnes

| Colonne | Type | Description |
|---------|------|-------------|
| `id` | INTEGER | ID unique |
| `product_key` | TEXT | Hash MD5 (Title+Type+Vendor) |
| `title` | TEXT | Titre du produit |
| `product_type` | TEXT | Type du produit |
| `vendor` | TEXT | Fournisseur |
| `category_code` | TEXT | Code Google final |
| `category_path` | TEXT | Chemin complet final |
| `confidence` | REAL | Niveau de confiance |
| `rationale` | TEXT | Justification |
| `created_at` | TIMESTAMP | Date de création |
| `last_used_at` | TIMESTAMP | Dernière utilisation |
| `use_count` | INTEGER | Nombre d'utilisations |

### ✨ Nouvelles Colonnes

| Colonne | Type | Description |
|---------|------|-------------|
| `original_category_code` | TEXT | **Code fourni par le LLM** (avant fallback) |
| `original_category_path` | TEXT | **Chemin fourni par le LLM** (avant fallback) |
| `csv_type` | TEXT | **Type du CSV original** |

**Intérêt**:
- Voir ce que le LLM avait proposé initialement
- Analyser pourquoi le fallback parent a été appliqué
- Ajuster les prompts LLM si nécessaire

---

## 🎯 Cas d'Usage

### 1. **Vérifier les Catégorisations Basses**

```sql
SELECT title, category_path, confidence, original_category_path
FROM product_category_cache
WHERE confidence < 0.5
ORDER BY confidence ASC;
```

**Dans l'onglet**: Trier par confidence pour voir les moins fiables

---

### 2. **Corriger des Catégories Incorrectes**

**Scénario**: "Plaid" catégorisé comme "Embrasses et glands de rideaux"

1. Rechercher "plaid" dans l'onglet Taxonomie
2. Voir la catégorie actuelle (incorrecte)
3. Double-clic → Modifier
4. Changer le code pour "Maison et jardin > Linge > Literie > Couvertures"
5. Augmenter la confidence à 95%
6. Sauvegarder
7. ✅ Tous les imports futurs utiliseront la bonne catégorie

---

### 3. **Analyser les Produits Fréquents**

**Dans l'onglet**: Trier par "Utilisations" pour voir:
- Quels produits sont le plus souvent importés
- Quels produits bénéficient le plus du cache
- ROI du système de cache

---

### 4. **Exporter pour Analyse**

1. Cliquer sur "📥 Exporter CSV"
2. Ouvrir dans Excel
3. Créer un tableau croisé dynamique:
   - Lignes: Type CSV
   - Valeurs: Moyenne de Confidence
   - Filtre: Confidence < 80%
4. Identifier les types de produits problématiques

---

## 🔧 Configuration

### Changer la Limite de Recherche

Par défaut, l'onglet affiche **500 résultats max**.

**Pour augmenter**:
```python
# Dans apps/gui/taxonomy_window.py, ligne ~87
results = self.db.search_taxonomy_cache(search_term, limit=1000)  # Au lieu de 500
```

---

### Colonnes Personnalisées

Pour ajouter/retirer des colonnes, modifier `apps/gui/taxonomy_window.py`:

```python
# Ligne ~73
columns = ("id", "title", "type", "vendor", "category", "code", "original", "confidence", "uses")

# Ajouter "rationale" par exemple:
columns = ("id", "title", "type", "vendor", "category", "code", "original", "confidence", "rationale", "uses")
```

---

## 📊 Requêtes SQL Utiles

### 1. Produits avec Fallback Parent

```sql
SELECT title, category_path, original_category_path, confidence
FROM product_category_cache
WHERE original_category_path != category_path
  AND original_category_path IS NOT NULL;
```

**Résultat**: Tous les produits où la catégorie finale diffère de l'original LLM

---

### 2. Produits Jamais Réutilisés

```sql
SELECT title, category_path, confidence, use_count
FROM product_category_cache
WHERE use_count = 1
ORDER BY created_at DESC;
```

**Résultat**: Produits catégorisés une seule fois (candidats à la suppression si obsolètes)

---

### 3. Catégories les Plus Fréquentes

```sql
SELECT category_path, COUNT(*) as count
FROM product_category_cache
GROUP BY category_path
ORDER BY count DESC
LIMIT 10;
```

**Résultat**: Top 10 des catégories les plus utilisées

---

### 4. Évolution de la Confidence Moyenne

```sql
SELECT 
    DATE(created_at) as date,
    AVG(confidence) as avg_confidence,
    COUNT(*) as products_count
FROM product_category_cache
GROUP BY DATE(created_at)
ORDER BY date DESC;
```

**Résultat**: Suivi de la qualité des catégorisations dans le temps

---

## 🎓 Bonnes Pratiques

### 1. **Révision Régulière**

- Consulter l'onglet Taxonomie après chaque batch
- Vérifier les produits avec confidence < 50%
- Corriger manuellement les erreurs détectées

### 2. **Nettoyage du Cache**

- Supprimer les produits obsolètes (plus vendus)
- Supprimer les tests (produits de démo)
- Garder uniquement les vrais produits

### 3. **Amélioration Continue**

- Analyser les `original_category_path` vs `category_path`
- Si beaucoup de fallbacks parent sur un type → Améliorer le prompt LLM
- Si même erreur répétée → Ajouter des règles dans le fallback intelligent

### 4. **Export Mensuel**

- Exporter le CSV chaque mois
- Archiver pour historique
- Comparer l'évolution de la confidence moyenne

---

## 🚀 Raccourcis Clavier

| Touche | Action |
|--------|--------|
| `Entrée` | Rechercher (dans la barre de recherche) |
| `Double-clic` | Modifier l'entrée sélectionnée |
| `Ctrl+R` | Rafraîchir (tout afficher) |

---

## 📸 Captures d'Écran

### Vue Principale

```
┌─────────────────────────────────────────────────────────────────┐
│ 📊 Gestion de la Taxonomie Google Shopping                     │
├─────────────────────────────────────────────────────────────────┤
│ 🔍 Rechercher: [_____________] [Rechercher] [↻ Tout Afficher]  │
│ 📊 Total: 245 produits | Confidence moyenne: 89.3% | Max: 12   │
├───┬─────────┬──────┬────────┬──────────────┬──────┬──────────┬──┤
│ID │ Titre   │ Type │ Vendor │ Catégorie    │ Code │ Original │%│
├───┼─────────┼──────┼────────┼──────────────┼──────┼──────────┼──┤
│ 1 │ NAPPE...│Nappes│Garnier │Maison>Arts...│ 3320 │ (aucun)  │95│
│ 2 │ PLAID...│Linge │Garnier │Maison>Linge..│  574 │ (aucun)  │92│
│ 3 │ BOUDIN..│Décor │Garnier │Maison>App... │  609 │Maison>...│45│
└───┴─────────┴──────┴────────┴──────────────┴──────┴──────────┴──┘
  [✏️ Modifier]  [🗑️ Supprimer]  [📥 Exporter CSV]
```

### Fenêtre d'Édition

```
┌──────────────────────────────────────────────┐
│ Modifier: NAPPE EN COTON - ARGELOS          │
├──────────────────────────────────────────────┤
│                                              │
│ Code Google Shopping:                        │
│ [3320_____________________________]          │
│                                              │
│ Confidence (0-1):                           │
│ [0.95______________________________]         │
│ [=============================>   ] 95%      │
│                                              │
│ ✅ Catégorie valide:                        │
│ Maison et jardin > Arts de la table >       │
│ Linge de table > Nappes                     │
│                                              │
│  [✅ Enregistrer]     [❌ Annuler]           │
└──────────────────────────────────────────────┘
```

---

## 🎯 Résumé

| Fonctionnalité | Avant | Après |
|----------------|-------|-------|
| **Sauvegarde** | Seulement conf >= 80% | **TOUS les produits** |
| **Visibilité** | Aucune interface | **Onglet Taxonomie** dédié |
| **Recherche** | SQL manuel | **Interface graphique** |
| **Modification** | SQL manuel | **Double-clic** + fenêtre |
| **Original LLM** | Perdu après fallback | **Conservé** dans DB |
| **Type CSV** | Non sauvegardé | **Sauvegardé** |
| **Export** | Impossible | **Bouton Export CSV** |

**Gain**: Contrôle total sur les catégorisations + Transparence sur les décisions du LLM! 🎉
