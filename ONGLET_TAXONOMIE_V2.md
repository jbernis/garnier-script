# Onglet Taxonomie - Version 2
## Interface Inspirée de l'Onglet Test

**Date**: 23 janvier 2026  
**Version**: 2.0  
**Fichier**: `apps/gui/taxonomy_window.py`

---

## Vue d'ensemble

L'onglet Taxonomie a été complètement réécrit pour adopter la structure de l'onglet Test (`apps/ai_editor/gui/window.py`). Cette nouvelle version offre une interface de recherche + fiche produit éditable, sans popup et sans tableau multi-lignes.

---

## Structure de l'Interface

### 1. Barre de Recherche

```python
# Champ de recherche avec binding sur KeyRelease
self.search_entry.bind("<KeyRelease>", self.on_search_changed)
```

**Comportement**:
- Recherche en temps réel dès 2 caractères
- Recherche par nom de produit dans `product_category_cache`
- Limite: 50 résultats maximum

### 2. Résultats de Recherche

```python
# CTkScrollableFrame avec height=200 (barre défilante automatique)
self.search_results_frame = ctk.CTkScrollableFrame(search_frame, height=200)

# Radio buttons pour sélectionner un produit
for product in results:
    radio = ctk.CTkRadioButton(
        self.search_results_frame,
        text=product['title'][:70],
        variable=self.selected_product_id,
        value=str(product['id']),
        command=self.load_product_details
    )
```

**Comportement**:
- Liste de radio buttons (un par produit)
- Barre défilante si plus de 200px de hauteur
- Clic sur un radio button → charge la fiche produit
- Texte tronqué à 70 caractères

### 3. Fiche Produit (5 Champs)

#### Champ 1: Nom (non éditable)
```python
self.name_value = ctk.CTkLabel(...)
```
Affiche le titre complet du produit.

#### Champ 2: Type (non éditable)
```python
self.type_value = ctk.CTkLabel(...)
```
Affiche le `csv_type` (ex: "Nappes", "Thés", etc.).

#### Champ 3: ID (ÉDITABLE avec mise à jour automatique)
```python
self.id_entry = ctk.CTkEntry(...)
self.id_entry.bind("<KeyRelease>", self.on_id_changed)
```

**Comportement**:
- Éditable par l'utilisateur
- À chaque modification, requête SQL automatique:
  ```sql
  SELECT path FROM google_taxonomy WHERE code = ?
  ```
- Le champ Catégorie se met à jour automatiquement
- Si le code n'existe pas: "❌ Code non trouvé dans la taxonomie"

#### Champ 4: Catégorie (mise à jour automatique)
```python
self.category_value = ctk.CTkLabel(...)
```

**Comportement**:
- Mise à jour automatique quand l'ID change
- Couleur verte si code valide
- Couleur rouge si code invalide

#### Champ 5: Confidence (ÉDITABLE)
```python
self.confidence_entry = ctk.CTkEntry(...)
```

**Comportement**:
- Éditable par l'utilisateur
- Valeur entre 0.0 et 1.0
- Validation lors de la sauvegarde

---

## Fonctions Principales

### `on_search_changed(event)`

Appelée à chaque frappe dans la recherche.

**Logique**:
1. Récupère le terme de recherche
2. Efface les anciens radio buttons
3. Recherche dans `product_category_cache` via `db.search_taxonomy_cache()`
4. Crée un radio button pour chaque résultat
5. Affiche un message si aucun résultat

**Référence**: Inspirée de `window.py` ligne 1992 (`on_search_changed`)

### `load_product_details()`

Appelée quand un produit est sélectionné (clic sur radio button).

**Logique**:
1. Récupère l'ID du produit sélectionné (`self.selected_product_id.get()`)
2. Requête SQL:
   ```sql
   SELECT * FROM product_category_cache WHERE id = ?
   ```
3. Remplit les 5 champs:
   - Nom, Type (labels)
   - ID, Confidence (entries)
   - Catégorie (label mis à jour auto)
4. Sauvegarde `self.current_product_db_id` pour la sauvegarde

### `on_id_changed(event)`

Appelée à chaque modification de l'ID.

**Logique**:
1. Récupère le code saisi
2. Requête SQL:
   ```sql
   SELECT path FROM google_taxonomy WHERE code = ?
   ```
3. Met à jour `self.category_value`:
   - Texte = path trouvé
   - Couleur verte si trouvé
   - Couleur rouge + message d'erreur sinon

### `save_changes()`

Sauvegarde les modifications ID + Confidence.

**Logique**:
1. Validation:
   - Produit sélectionné?
   - Confidence valide (0-1)?
   - Code non vide?
   - Code existe dans `google_taxonomy`?
2. Appel `db.update_taxonomy_cache(id, code, confidence)`
3. Message de succès dans `self.status_label` (pas de popup!)

**Référence**: Utilise `db.update_taxonomy_cache()` déjà implémentée

### `export_csv()`

Exporte TOUS les produits de `product_category_cache`.

**Logique**:
1. Dialogue de sauvegarde de fichier
2. Requête SQL:
   ```sql
   SELECT * FROM product_category_cache ORDER BY last_used_at DESC
   ```
3. Export CSV avec TOUTES les colonnes:
   - ID, Titre, Type, Vendor, Catégorie, Code
   - Catégorie Originale LLM, Code Original
   - Confidence, Rationale
   - Utilisations, Créé le, Dernière utilisation
4. Message de succès dans `self.status_label`

---

## Comparaison Ancien vs Nouveau

### ❌ Ancien (Version 1)

- **Tableau Treeview** (multi-lignes)
- **Bouton "Modifier la Sélection"** → popup `EditDialog`
- **Bouton "Supprimer"** → popup de confirmation
- **Bouton "Rechercher"** (action manuelle)
- **Bouton "↻ Tout Afficher"**
- **Pas de mise à jour automatique** du category_path

### ✅ Nouveau (Version 2)

- **Liste de radio buttons** (barre défilante)
- **Fiche produit directe** (5 champs)
- **Pas de popup** (tout en labels)
- **Recherche en temps réel** (KeyRelease)
- **Mise à jour automatique** du category_path
- **2 boutons seulement**: Sauvegarder + Export CSV

---

## Flux d'Utilisation

### Exemple: Modifier la catégorie d'une nappe

1. **Utilisateur tape "nappe" dans la recherche**
   → Les résultats s'affichent en temps réel

2. **Utilisateur clique sur le radio button "NAPPE EN COTON - ARGELOS"**
   → Les 5 champs se remplissent automatiquement:
   - Nom: NAPPE EN COTON - ARGELOS
   - Type: Nappes
   - ID: 3320
   - Catégorie: Maison et jardin > Arts de la table > Linge > Nappes
   - Confidence: 0.95

3. **Utilisateur modifie l'ID: 3320 → 3321**
   → La catégorie se met à jour automatiquement en temps réel

4. **Utilisateur modifie la confidence: 0.95 → 0.85**

5. **Utilisateur clique sur "Sauvegarder"**
   → Message dans le label: "✅ Sauvegardé: 3321 - Maison et jardin > ..."
   → Pas de popup!

6. **Utilisateur clique sur "Exporter Tout en CSV"**
   → Tous les produits sont exportés (pas seulement le sélectionné)

---

## Avantages de la Version 2

### 🚀 Performance
- Pas de chargement initial (pas de `refresh_all()` au démarrage)
- Recherche ciblée (50 résultats max)
- Mise à jour instantanée du category_path

### 💡 UX
- Interface familière (comme Test)
- Pas de popup
- Feedback visuel immédiat
- Recherche en temps réel
- Édition directe

### 🎯 Simplicité
- Moins de boutons (2 au lieu de 4)
- Pas de classe `EditDialog`
- Pas de Treeview (complexe)
- Code plus court et maintenable

---

## Fichiers Modifiés

### `apps/gui/taxonomy_window.py`
**Changements**:
- Supprimé: Treeview, EditDialog, boutons "Modifier" et "Supprimer"
- Ajouté: CTkScrollableFrame avec radio buttons, fiche produit
- Structure inspirée de `apps/ai_editor/gui/window.py` (lignes 1868-1968)

### `apps/gui/main_window.py`
**Changements**:
- Déjà intégré (bouton "📊 Taxonomie" dans la sidebar)
- Import: `from gui.taxonomy_window import TaxonomyWindow`

---

## Méthodes de la Base de Données Utilisées

### `db.search_taxonomy_cache(search_term, limit)`
Recherche dans `product_category_cache` par titre.

### `db.update_taxonomy_cache(cache_id, code, confidence)`
Met à jour le code et la confidence d'un produit.

### Requête SQL directe
```sql
SELECT path FROM google_taxonomy WHERE code = ?
```
Pour vérifier/récupérer le path d'un code.

---

## Messages de Statut (Sans Popup)

Tous les messages s'affichent dans `self.status_label`:

### Succès
- ✅ Sauvegardé: 3320 - Maison et jardin > ...
- ✅ 125 produits exportés vers taxonomy_export_20260123_143000.csv

### Erreurs
- ❌ Aucun produit sélectionné
- ❌ Confidence invalide (doit être un nombre)
- ❌ Confidence doit être entre 0 et 1
- ❌ Le code ne peut pas être vide
- ❌ Code non trouvé dans la taxonomie
- ❌ Échec de la sauvegarde
- ❌ Erreur: [détails]

### Avertissements
- ⚠️ Aucun produit sélectionné

---

## Logs

```python
logger.info(f"Modification enregistrée pour le produit {self.current_product_db_id}")
logger.info(f"Export réussi: {filename}")
logger.error(f"Erreur lors de la recherche: {e}", exc_info=True)
logger.error(f"Erreur lors du chargement du produit: {e}", exc_info=True)
logger.error(f"Erreur lors de la sauvegarde: {e}", exc_info=True)
logger.error(f"Erreur lors de l'export: {e}", exc_info=True)
```

---

## Résumé Technique

| Élément | Ancien | Nouveau |
|---------|--------|---------|
| **Recherche** | Bouton manuel | Temps réel (KeyRelease) |
| **Résultats** | Treeview | Radio buttons dans CTkScrollableFrame |
| **Édition** | Popup EditDialog | Fiche directe |
| **Mise à jour category_path** | Manuelle | Automatique |
| **Messages** | Popup messagebox | Label de statut |
| **Export** | Résultats affichés | TOUS les produits |
| **Boutons** | 4 (Rechercher, Tout, Modifier, Supprimer, Export) | 2 (Sauvegarder, Export) |

---

## Code Référence

**Structure inspirée de**: `apps/ai_editor/gui/window.py`, fonction `create_test_tab()` (lignes 1868-1990)

**Éléments copiés**:
- CTkScrollableFrame pour résultats (ligne 1918)
- Radio buttons (ligne 1921-1922)
- Binding KeyRelease (ligne 1908)
- StringVar pour sélection (ligne 1922)

---

## Prochaines Étapes (Optionnel)

- [ ] Ajouter un bouton "Effacer la recherche"
- [ ] Ajouter des filtres (par confidence, par date)
- [ ] Ajouter une prévisualisation du produit Shopify
- [ ] Ajouter un historique des modifications
