# Modification des Règles Types

**Date**: 23 janvier 2026  
**Feature**: Modification des règles Type → Catégorie existantes

---

## ✨ Nouvelle Fonctionnalité

Vous pouvez maintenant **modifier** une règle existante sans avoir à la supprimer et la recréer!

---

## 🎯 Ce qui Peut Être Modifié

### ✅ Modifiable
- **Code Google Shopping** (ex: `4143` → `500044`)
- **Catégorie Path** (mis à jour automatiquement avec le code)

### ❌ Non Modifiable
- **Type de produit** (ex: "TABLE")
  - Raison: Le Type est la clé unique
  - Solution: Supprimer la règle et en créer une nouvelle

---

## 🖱️ Interface

### Bouton "✏️ Modifier"

Chaque règle dans "Règles Actives" a maintenant 4 boutons:
1. **✏️ Modifier** (nouveau!)
2. **❌ Désactiver** / **✅ Activer**
3. **🗑️ Supprimer**

### Formulaire de Modification

Quand vous cliquez sur "✏️ Modifier":

```
┌─────────────────────────────────────────────────────┐
│ ✏️ Modifier la Règle: TABLE                         │
│                                                     │
│ Type de produit:  TABLE  (non modifiable)          │
│                                                     │
│ Code Google:  [4143___]                            │
│ ✅ Maison et jardin > Linge > Linge de table > N... │
│                                                     │
│ [💾 Sauvegarder]  [❌ Annuler]                     │
└─────────────────────────────────────────────────────┘
```

**Validation en Temps Réel**:
- Tapez un nouveau code
- La catégorie s'affiche immédiatement
- ✅ Vert si code valide
- ❌ Rouge si code invalide

---

## 📝 Cas d'Usage

### Cas 1: Affiner la Catégorie

**Situation**: Vos nappes sont dans "Linge de table > Nappes" (code 4143) mais vous voulez être plus général.

**Action**:
1. Cliquez sur "✏️ Modifier" pour la règle TABLE
2. Changez le code: `4143` → `500044`
3. Vérifiez: ✅ Maison et jardin > Linge > Linge de table (plus général)
4. Cliquez "💾 Sauvegarder"

**Résultat**: Tous les **futurs** produits TYPE="TABLE" utiliseront le nouveau code.

**⚠️ Important**: Les produits déjà traités ne sont **pas** mis à jour automatiquement!

---

### Cas 2: Corriger une Erreur

**Situation**: Vous avez créé une règle avec le mauvais code par erreur.

**Action**:
1. Cliquez sur "✏️ Modifier"
2. Corrigez le code
3. Sauvegardez

**Avantage**: Pas besoin de recréer la règle, les stats `use_count` sont conservées.

---

### Cas 3: Changer le Type (impossible directement)

**Situation**: Vous voulez changer "TABLE" → "NAPPES".

**Action**:
1. **Supprimer** la règle "TABLE"
2. **Créer** une nouvelle règle "NAPPES"

**Raison**: Le Type est la clé unique de la table.

---

## 🔧 Implémentation Technique

### Nouvelle Méthode dans `db.py`

```python
def update_type_mapping(self, mapping_id: int, category_code: str, 
                       category_path: str) -> bool:
    """Met à jour uniquement le code et le path."""
    cursor.execute('''
        UPDATE type_category_mapping
        SET category_code = ?,
            category_path = ?,
            updated_at = CURRENT_TIMESTAMP
        WHERE id = ?
    ''', (category_code, category_path, mapping_id))
```

**Caractéristiques**:
- Met à jour `category_code`, `category_path`, `updated_at`
- Ne touche PAS à `product_type`, `use_count`, `created_by`, `is_active`
- Log: `✏️ Type Mapping modifié: ID 1 → ...`

---

### Fonction GUI dans `taxonomy_window.py`

```python
def edit_rule(self, rule):
    """Affiche le formulaire de modification."""
    # Formulaire avec Type non modifiable
    # Code modifiable avec validation temps réel
    # Sauvegarde via update_type_mapping()
```

**Caractéristiques**:
- Formulaire inline (pas de popup!)
- Type affiché en gris (non modifiable)
- Validation en temps réel du code
- Fermeture auto après sauvegarde

---

## ⚠️ Points d'Attention

### 1. Produits Déjà Traités

**Important**: Modifier une règle n'affecte **pas** les produits déjà catégorisés.

**Exemple**:
- 100 nappes déjà traitées avec code `4143`
- Vous modifiez la règle TABLE: `4143` → `500044`
- **Résultat**: Les 100 nappes gardent `4143` dans la base
- Seules les **nouvelles** nappes auront `500044`

**Solution**: Si vous voulez re-catégoriser les anciens produits:
1. Supprimez-les du cache (`product_category_cache`)
2. Retraitez-les (ils utiliseront la nouvelle règle)

---

### 2. Colonne `updated_at`

Chaque modification met à jour `updated_at`:
- Permet de voir quand la règle a été modifiée
- Utile pour l'audit

---

### 3. Conservation des Stats

**Avantage de Modifier vs Supprimer/Recréer**:

| Action | use_count | created_at | created_by |
|--------|-----------|------------|------------|
| **Modifier** | ✅ Conservé | ✅ Conservé | ✅ Conservé |
| **Supprimer + Recréer** | ❌ Perdu (repart à 0) | ❌ Nouveau | ❌ Réinitialisé |

**Recommandation**: Préférez **Modifier** pour conserver l'historique.

---

## 🎨 Exemples Visuels

### Avant Modification

```
📋 Règles Actives

┌──────────────────────────────────────────────┐
│ Type: TABLE                                   │
│ → Maison et jardin > Linge > Nappes          │
│ Code: 4143 | Confidence: 100%                │
│ 📊 Utilisé 127 fois | Créé: manual           │
│ [✏️ Modifier] [❌ Désactiver] [🗑️ Supprimer] │
└──────────────────────────────────────────────┘
```

### Clic sur "✏️ Modifier"

```
┌────────────────────────────────────────────────┐
│ ✏️ Modifier la Règle: TABLE                    │
│                                                │
│ Type de produit:  TABLE  (non modifiable)     │
│                                                │
│ Code Google:  [500044]                        │
│ ✅ Maison et jardin > Linge > Linge de table  │
│                                                │
│ [💾 Sauvegarder]  [❌ Annuler]                │
└────────────────────────────────────────────────┘
```

### Après Modification

```
📋 Règles Actives

┌──────────────────────────────────────────────┐
│ Type: TABLE                                   │
│ → Maison et jardin > Linge > Linge de table  │
│ Code: 500044 | Confidence: 100%              │
│ 📊 Utilisé 127 fois | Créé: manual           │
│ [✏️ Modifier] [❌ Désactiver] [🗑️ Supprimer] │
└──────────────────────────────────────────────┘

✅ Règle modifiée: 500044 → Maison et jardin > Linge...
```

---

## 🚀 Test Rapide

### 1. Ouvrir l'Application

```bash
python run_gui.py
```

### 2. Naviguer vers Taxonomie → Règles Types

### 3. Créer une Règle Test

- Type: `TEST_MODIF`
- Code: `4143`

### 4. Modifier la Règle

- Cliquez "✏️ Modifier"
- Changez le code: `500044`
- Sauvegardez

### 5. Vérifier

- La règle affiche maintenant: Code `500044`
- Le `use_count` est conservé
- Message: "✅ Règle modifiée..."

---

## 📊 Statistiques SQL

### Voir l'historique des modifications

```sql
SELECT 
    product_type,
    category_code,
    category_path,
    use_count,
    created_at,
    updated_at,
    (julianday(updated_at) - julianday(created_at)) as days_since_creation
FROM type_category_mapping
WHERE updated_at > created_at  -- Règles qui ont été modifiées
ORDER BY updated_at DESC;
```

---

## 📚 Résumé

| Feature | Disponible |
|---------|------------|
| Créer règle | ✅ |
| Modifier code/catégorie | ✅ (nouveau!) |
| Modifier type | ❌ (supprimer + recréer) |
| Activer/Désactiver | ✅ |
| Supprimer | ✅ |
| Analyser patterns | ✅ |
| Stats conservées après modif | ✅ |
| Validation temps réel | ✅ |
| Pas de popup | ✅ |

---

**Version**: 1.1  
**Statut**: ✅ Implémenté et documenté  
**Fichiers modifiés**:
- `apps/ai_editor/db.py` (+30 lignes, méthode `update_type_mapping`)
- `apps/gui/taxonomy_window.py` (+180 lignes, fonctions `edit_rule`, `validate_edit_rule_code`, `save_edited_rule`)
