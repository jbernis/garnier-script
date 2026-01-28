# Guide Rapide - Onglet Taxonomie

## 🎯 Objectif

L'onglet Taxonomie permet de rechercher, visualiser et modifier manuellement les catégorisations Google Shopping des produits du cache.

---

## 🚀 Accès

1. Lancer l'application: `python run_gui.py`
2. Dans la fenêtre principale, cliquer sur **"📊 Taxonomie"** dans la barre latérale
3. L'onglet Taxonomie s'ouvre

---

## 📋 Interface

```
┌─────────────────────────────────────────────────────────┐
│ 📊 Gestion de la Taxonomie Google Shopping             │
│                                                         │
│ Rechercher un produit                                   │
│ Nom du produit: [_________________________]            │
│                                                         │
│ Résultats de recherche:                                │
│ ┌─────────────────────────────────────────────────┐   │
│ │ ○ NAPPE EN COTON - ARGELOS                       │   │
│ │ ● NAPPE EN LIN - BEAUMONT     <-- Sélectionné    │   │
│ │ ○ NAPPE EN SOIE - CHARENTE                       │   │
│ └─────────────────────────────────────────────────┘   │
│                                                         │
│ Détails du produit sélectionné                         │
│ Nom: NAPPE EN LIN - BEAUMONT                           │
│ Type: Nappes                                           │
│ ID (Code): [3320___]  ← Éditable                       │
│ Catégorie: Maison et jardin > Arts de la table > ...  │
│ Confidence: [0.95__]  ← Éditable                       │
│                                                         │
│ [💾 Sauvegarder] [📥 Exporter Tout en CSV]             │
│ ✅ Sauvegardé: 3320 - Maison et jardin > ...           │
└─────────────────────────────────────────────────────────┘
```

---

## 🔍 Rechercher un Produit

### Étape 1: Taper dans la recherche
- Tapez au moins **2 caractères**
- La recherche se fait **en temps réel** (pas besoin de cliquer sur un bouton)
- Maximum **50 résultats** affichés

**Exemple**: Tapez `nappe`

### Étape 2: Résultats
- Les produits apparaissent sous forme de **radio buttons**
- Si plus de résultats que la hauteur (200px), une **barre défilante** apparaît automatiquement

---

## ✏️ Modifier un Produit

### Étape 1: Sélectionner un produit
- Cliquez sur un **radio button** dans les résultats
- Les **5 champs** se remplissent automatiquement:
  1. **Nom** (non éditable)
  2. **Type** (non éditable)
  3. **ID** (éditable)
  4. **Catégorie** (mise à jour automatique)
  5. **Confidence** (éditable)

### Étape 2: Modifier l'ID
- Cliquez dans le champ **ID**
- Modifiez le code (ex: `3320` → `3321`)
- **La catégorie se met à jour automatiquement** en temps réel!
- Si le code n'existe pas: message rouge **"❌ Code non trouvé"**

### Étape 3: Modifier la Confidence
- Cliquez dans le champ **Confidence**
- Entrez une valeur entre **0.0** et **1.0**
- Exemples:
  - `0.95` = très sûr
  - `0.70` = moyen
  - `0.50` = incertain

### Étape 4: Sauvegarder
- Cliquez sur **"💾 Sauvegarder"**
- Un message apparaît en bas: **"✅ Sauvegardé: 3320 - Maison et jardin > ..."**
- **Pas de popup!**

---

## 📥 Exporter TOUS les Produits

### Bouton "Exporter Tout en CSV"
- Exporte **TOUS** les produits du cache (pas seulement les résultats affichés)
- Choisissez l'emplacement et le nom du fichier
- Nom par défaut: `taxonomy_export_YYYYMMDD_HHMMSS.csv`

### Colonnes exportées
- ID, Titre, Type CSV, Vendor
- Catégorie, Code
- Catégorie Originale LLM, Code Original
- Confidence, Rationale
- Utilisations, Créé le, Dernière utilisation

---

## ✅ Messages de Statut

Tous les messages s'affichent **dans l'interface** (pas de popup):

### Succès (vert)
- ✅ Sauvegardé: 3320 - Maison et jardin > ...
- ✅ 125 produits exportés vers taxonomy_export_20260123_143000.csv

### Erreurs (rouge)
- ❌ Aucun produit sélectionné
- ❌ Confidence invalide (doit être un nombre)
- ❌ Confidence doit être entre 0 et 1
- ❌ Le code ne peut pas être vide
- ❌ Code non trouvé dans la taxonomie
- ❌ Échec de la sauvegarde

### Avertissements (orange)
- ⚠️ Aucun produit sélectionné

---

## 💡 Astuces

### 1. Mise à Jour Automatique du category_path
Quand vous modifiez l'ID, le champ Catégorie se met à jour **instantanément** en interrogeant la base de données `google_taxonomy`.

### 2. Validation en Temps Réel
- Si le code ID n'existe pas → message rouge
- Si le code existe → message vert avec le chemin complet

### 3. Pas de Popup
Contrairement à l'ancienne version, **tous les messages** s'affichent dans l'interface, pas de fenêtre popup à fermer!

### 4. Export Complet
Le bouton "Exporter Tout" exporte **TOUS** les produits du cache, pas seulement ceux affichés à l'écran.

---

## 🔄 Workflow Complet

### Exemple: Corriger la catégorie d'un produit

1. **Recherche**
   - Tapez `plaid` dans la recherche
   - 5 résultats apparaissent

2. **Sélection**
   - Cliquez sur `PLAID EN LAINE - BORDEAUX`
   - Les 5 champs se remplissent

3. **Vérification**
   - Nom: PLAID EN LAINE - BORDEAUX
   - Type: Plaids
   - ID: 3320 (catégorie actuelle: "Maison et jardin > Arts de la table > Linge > Nappes")
   - Confidence: 0.45

4. **Correction**
   - L'ID 3320 est incorrect (c'est pour les nappes, pas les plaids)
   - Recherchez le bon code dans Google Shopping Taxonomy
   - Trouvé: **3333** (Maison et jardin > Linge de maison > Plaids)
   - Modifiez l'ID: `3320` → `3333`
   - La catégorie se met à jour automatiquement: "Maison et jardin > Linge de maison > Plaids" ✅

5. **Ajustement de la Confidence**
   - Augmentez la confidence: `0.45` → `0.90`
   - (Vous êtes maintenant sûr de la catégorie)

6. **Sauvegarde**
   - Cliquez sur **"💾 Sauvegarder"**
   - Message: "✅ Sauvegardé: 3333 - Maison et jardin > Linge de maison > Plaids"

7. **Export (optionnel)**
   - Cliquez sur **"📥 Exporter Tout en CSV"**
   - Tous les produits du cache sont exportés

---

## 🛠️ Dépannage

### Problème: Aucun résultat
**Cause**: Le produit n'est pas dans le cache  
**Solution**: Le produit doit avoir été traité au moins une fois par le système de catégorisation LangGraph

### Problème: "Code non trouvé dans la taxonomie"
**Cause**: Le code saisi n'existe pas dans `google_taxonomy`  
**Solution**: Vérifiez le code dans la taxonomie Google Shopping officielle

### Problème: "Confidence invalide"
**Cause**: La valeur saisie n'est pas un nombre ou est hors de [0, 1]  
**Solution**: Entrez un nombre décimal entre 0.0 et 1.0 (ex: 0.85)

---

## 📚 Documentation Technique

Pour plus de détails techniques, voir:
- **ONGLET_TAXONOMIE_V2.md** - Documentation complète de l'architecture
- **apps/gui/taxonomy_window.py** - Code source
- **apps/ai_editor/db.py** - Méthodes de base de données

---

## 🎯 Résumé

| Action | Méthode |
|--------|---------|
| Rechercher | Tapez dans le champ (temps réel) |
| Sélectionner | Clic sur radio button |
| Modifier ID | Éditer le champ ID (catégorie se met à jour) |
| Modifier Confidence | Éditer le champ Confidence |
| Sauvegarder | Clic sur "Sauvegarder" |
| Exporter | Clic sur "Exporter Tout en CSV" |
| Messages | Affichés en bas (pas de popup) |
