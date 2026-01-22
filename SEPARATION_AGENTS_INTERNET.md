# Séparation des Agents IA - Accès Internet

## 🎯 Objectif

Séparer l'accès à internet entre les agents IA:
- **Agent SEO**: AVEC accès à internet (Perplexity) pour enrichir le contenu
- **Agent Google Shopping**: SANS accès à internet (utilise la taxonomie locale)

---

## ✅ Modifications Apportées

### 1. Processeur CSV (processor.py)

#### Avant
```python
# Un seul fournisseur IA pour tous les agents
ai_provider = get_provider(
    provider_name, 
    api_key=api_key, 
    model=model_name,
    enable_search=enable_search  # Appliqué à TOUS les agents
)

# Tous les agents utilisent le même fournisseur
agents['seo'] = SEOAgent(ai_provider, ...)
agents['google_category'] = GoogleShoppingAgent(ai_provider, ...)
```

#### Après
```python
# Deux fournisseurs IA distincts

# 1. AVEC recherche internet (pour SEO)
ai_provider_with_search = get_provider(
    provider_name, 
    api_key=api_key, 
    model=model_name,
    enable_search=enable_search  # Activable par l'utilisateur
)

# 2. SANS recherche internet (pour Google Shopping)
ai_provider_no_search = get_provider(
    provider_name, 
    api_key=api_key, 
    model=model_name,
    enable_search=False  # TOUJOURS désactivé
)

# Chaque agent utilise son propre fournisseur
agents['seo'] = SEOAgent(ai_provider_with_search, ...)
agents['google_category'] = GoogleShoppingAgent(ai_provider_no_search, ...)

# Donner accès à la taxonomie
agents['google_category'].set_database(self.db)
```

---

### 2. Agent Google Shopping (agents.py)

#### Nouvelles Fonctionnalités

**a) Méthode `set_database(db)`**
```python
def set_database(self, db):
    """Configure l'accès à la taxonomie Google Shopping."""
    self.db = db
```

**b) Méthode `_get_taxonomy_sample(product_data)`**
```python
def _get_taxonomy_sample(self, product_data):
    """
    Récupère un échantillon de catégories pertinentes
    depuis la taxonomie locale (SANS internet).
    
    Extrait des mots-clés du produit (titre, type, tags)
    et recherche dans la table google_taxonomy.
    
    Returns:
        Chaîne avec max 10 catégories pertinentes
    """
```

**c) Prompt enrichi avec taxonomie**
```python
def _build_full_prompt(self, product_data):
    """
    Construit le prompt avec:
    - Données du produit
    - Catégories pertinentes de la taxonomie locale
    - Instructions pour choisir parmi les catégories disponibles
    """
```

---

### 3. Prompts Améliorés (improve_prompts.py)

#### Prompt Google Shopping Mis à Jour

```
⚠️ IMPORTANT: Tu N'AS PAS BESOIN d'accès à internet pour cette tâche.
Les catégories pertinentes te seront fournies dans le contexte si disponibles.

📊 INSTRUCTIONS:
- Si des catégories pertinentes sont listées, CHOISIS parmi celles-ci
- Ne pas se limiter aux catégories générales
- Privilégier la précision

⚠️ RÈGLES STRICTES:
- Répondre UNIQUEMENT avec le chemin complet
- Si des catégories pertinentes sont listées, privilégie-les
```

---

## 📊 Architecture du Système

```
┌───────────────────────────────────────────────────────────────┐
│                        PROCESSEUR CSV                          │
│                                                                 │
│  ┌─────────────────────────────────────────────────────────┐  │
│  │ Fournisseur IA AVEC Internet (Perplexity)              │  │
│  │ - enable_search = True (si activé par l'utilisateur)   │  │
│  └─────────────────┬───────────────────────────────────────┘  │
│                    │                                            │
│                    ├──> Agent SEO                               │
│                    │    - Génère: Title, Body HTML, Tags, etc. │
│                    │    - Utilise Perplexity pour enrichir     │
│                    │                                            │
│  ┌─────────────────────────────────────────────────────────┐  │
│  │ Fournisseur IA SANS Internet                            │  │
│  │ - enable_search = False (TOUJOURS)                      │  │
│  └─────────────────┬───────────────────────────────────────┘  │
│                    │                                            │
│                    └──> Agent Google Shopping                  │
│                         - Génère: Google Product Category      │
│                         - Utilise la taxonomie locale          │
│                         - Accès à la DB pour catégories        │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

---

## 🔍 Fonctionnement Détaillé

### Agent Google Shopping - Processus

```
1. Récupère les données du produit
   ├─> Titre: "Nappe en coton bio"
   ├─> Type: "Linge de table"
   └─> Tags: "nappe, coton, linge"

2. Extrait des mots-clés
   └─> ["nappe", "coton", "linge", "table"]

3. Recherche dans la taxonomie locale (google_taxonomy)
   └─> SELECT * FROM google_taxonomy 
       WHERE path LIKE '%nappe%' OR path LIKE '%table%'
       LIMIT 10

4. Enrichit le prompt avec les catégories trouvées
   ├─> "📚 CATÉGORIES PERTINENTES DISPONIBLES:"
   ├─> "  - Home & Garden > Linens & Bedding > Table Linens"
   ├─> "  - Home & Garden > Kitchen & Dining > Tableware"
   └─> "💡 Choisis une catégorie parmi celles ci-dessus"

5. Génère la catégorie (SANS internet, uniquement avec le prompt)
   └─> "Home & Garden > Linens & Bedding > Table Linens > Tablecloths"

6. Recherche le code dans la taxonomie
   └─> Code numérique trouvé et sauvegardé
```

---

## 🧪 Tests

### Script de Test: `test_google_shopping_no_internet.py`

```bash
python test_google_shopping_no_internet.py
```

#### Résultats Attendus

```
✅ Taxonomie Google Shopping: 5595 catégories disponibles
✅ Catégories pertinentes trouvées pour le produit
✅ enable_search = False (pas d'accès à internet)
🎯 L'agent Google Shopping fonctionne sans internet!
```

---

## 📈 Avantages

### Économies
- **Coût API réduit**: Pas d'appels Perplexity pour Google Shopping
- **Temps réduit**: Pas d'attente réseau pour la catégorisation

### Précision
- **Catégories validées**: Seules les catégories existantes dans la taxonomie
- **Cohérence**: Toujours les mêmes catégories pour des produits similaires

### Performance
- **Plus rapide**: Recherche locale vs. requête réseau
- **Fiable**: Pas de dépendance à un service externe

---

## 🎯 Utilisation

### Dans l'Interface Graphique

Quand vous traitez des produits:

**1. Agent SEO (avec recherche si activée)**
```
  Génération SEO...
  🌐 Recherche Internet activée (Perplexity)
  ✓ Body HTML enrichi avec informations en ligne
```

**2. Agent Google Shopping (sans recherche)**
```
  Génération catégorie Google Shopping...
  ℹ️ Agent Google Shopping configuré SANS recherche internet
  📚 Catégories pertinentes: 10 trouvées
  ✓ Catégorie: Home & Garden > Linens & Bedding
  ✓ Code: 632
```

---

## 🔧 Configuration

### Modifier le Comportement

Si vous voulez **forcer** l'accès internet pour Google Shopping (non recommandé):

Dans `processor.py`, ligne ~425:
```python
# Changer False en True
ai_provider_no_search = get_provider(
    provider_name, 
    api_key=api_key, 
    model=model_name,
    enable_search=True,  # ⚠️ Non recommandé
    ...
)
```

---

## 📚 Taxonomie Google Shopping

### Vérifier la Taxonomie

```python
from apps.ai_editor.db import AIPromptsDB

db = AIPromptsDB()
count = db.get_taxonomy_count()
print(f"Catégories disponibles: {count}")
```

### Importer/Mettre à Jour la Taxonomie

```bash
python import_google_taxonomy.py
```

---

## 🎓 Exemple de Logs

### Traitement avec Séparation des Agents

```
[INFO] Import du CSV...
[INFO] CSV importé (ID: 15)

[INFO] Création des fournisseurs IA...
[INFO] ✅ Fournisseur avec recherche créé (OpenAI GPT-4)
[INFO] ✅ Fournisseur sans recherche créé (OpenAI GPT-4)
[INFO] ℹ️ Agent Google Shopping configuré SANS recherche internet
[INFO] Agent Google Shopping configuré avec accès à la taxonomie

[INFO] Traitement du produit: nappe-coton-argelos
[INFO]   Génération SEO...
[INFO]   🌐 Utilisation de Perplexity pour enrichir le contenu
[INFO]   ✓ SEO mis à jour (6 champ(s))

[INFO]   Génération catégorie Google Shopping...
[INFO]   📚 10 catégories pertinentes trouvées dans la taxonomie
[INFO]   ✓ Catégorie Google Shopping mise à jour (Code: 632)

[INFO] ✓ Produit nappe-coton-argelos traité avec succès
```

---

## ✅ Checklist de Vérification

Après avoir appliqué ces modifications:

- [x] ✅ Deux fournisseurs IA créés (avec/sans recherche)
- [x] ✅ Agent SEO utilise le fournisseur avec recherche
- [x] ✅ Agent Google Shopping utilise le fournisseur sans recherche
- [x] ✅ Agent Google Shopping a accès à la taxonomie via `set_database()`
- [x] ✅ Méthode `_get_taxonomy_sample()` implémentée
- [x] ✅ Prompt Google Shopping mis à jour (sans mention d'internet)
- [x] ✅ Tests validés avec `test_google_shopping_no_internet.py`
- [x] ✅ Taxonomie Google disponible (5595 catégories)

---

## 📝 Résumé

### Avant
- Tous les agents partageaient le même fournisseur IA
- Accès internet activé/désactivé pour TOUS les agents
- Agent Google Shopping utilisait inutilement Perplexity

### Après
- Chaque type d'agent a son propre fournisseur IA
- **Agent SEO**: AVEC internet (si activé par l'utilisateur)
- **Agent Google Shopping**: SANS internet (toujours), AVEC taxonomie locale
- Économies de coûts API
- Meilleure précision pour Google Shopping

---

## 🎉 Conclusion

L'agent Google Shopping fonctionne maintenant **sans accès à internet** et utilise la **taxonomie locale** pour identifier les catégories. Cela permet:

- ✅ Économies sur les appels API Perplexity
- ✅ Catégories plus précises (basées sur la taxonomie officielle)
- ✅ Traitement plus rapide
- ✅ Pas de dépendance à un service externe

🎯 **Le système est maintenant optimisé et économique!**
