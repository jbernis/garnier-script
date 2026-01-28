# Flux : Type, csv_type et Google Shopping

## Question : Qu'envoie-t-on au LLM Google Shopping ?

### Réponse courte :

Le LLM Google Shopping (LangGraph) reçoit **`product_data`** complet, qui contient **TOUS les champs du CSV**, y compris le champ **`Type`** original du CSV (pas csv_type).

### Flux détaillé :

```
PHASE 1: AGENT SEO
═══════════════════════════════════════════════════════════════
LLM SEO génère:
  ├─→ type = "NAPPES" (normalisé)
  ├─→ seo_title, seo_description, title, body_html, tags, image_alt_text
  └─→ Sauvegarde:
       ├─→ CSV : Champ "Type" = "NAPPES"
       └─→ Cache : csv_type = "NAPPES"


PHASE 2: GOOGLE SHOPPING (si pas de règle existante)
═══════════════════════════════════════════════════════════════
1. Vérification des RÈGLES (type_category_mapping)
   Recherche avec : product_type (original CSV) + csv_type (du cache)
   
   SI RÈGLE TROUVÉE:
   ✅ Utilisation directe (0 appel LLM)
      • category_code = règle.category_code
      • category_path = règle.category_path
      • confidence = règle.confidence  ← CONFIDENCE DE LA RÈGLE
   
   SI PAS DE RÈGLE:
   🤖 Appel LLM Google Shopping (LangGraph)
      • Reçoit: product_data complet (Title, Type, Body HTML, etc.)
      • Le LLM analyse: Title, Type original, Body HTML, Tags, etc.
      • Retourne:
         - category_code
         - category_path
         - confidence ← CONFIDENCE DU LLM GOOGLE SHOPPING
         - needs_review
         - rationale
      
      Puis:
      • Création automatique d'une RÈGLE dans type_category_mapping
        avec la confidence retournée par le LLM Google Shopping
```

## Question : D'où vient la confidence des règles ?

### Réponse :

La **confidence des règles** vient de **2 sources différentes** :

### 1. **Règles créées automatiquement par le LLM Google Shopping**

Quand le LLM Google Shopping catégorise un produit (lignes 542-566 de `processor.py`) :

```python
# Le LLM retourne une confidence
confidence = result['confidence']  # Ex: 0.85

# Cette confidence est utilisée pour créer la règle
self._update_concordance_table(
    product_type=product_type,    # Ex: "Accessoire" (original CSV)
    csv_type=csv_type,            # Ex: "NAPPES" (normalisé)
    category_code=category_code,  # Ex: 536
    category_path=category_path,  # Ex: "Home & Garden > Linens..."
    confidence=confidence  # ← CONFIDENCE DU LLM GOOGLE SHOPPING
)
```

### 2. **Règles créées manuellement**

Quand vous créez une règle manuellement dans l'interface :
- `confidence = 1.0` (par défaut)
- `created_by = 'manual'`

## Schéma récapitulatif :

```
┌─────────────────────────────────────────────────────────────┐
│ PRODUIT                                                      │
├─────────────────────────────────────────────────────────────┤
│ Title: "Nappe en Coton 160x200"                            │
│ Type (CSV original): "Accessoire"  ← PAS ENCORE NORMALISÉ  │
└─────────────────────────────────────────────────────────────┘
                           ↓
┌─────────────────────────────────────────────────────────────┐
│ PHASE 1: AGENT SEO                                          │
├─────────────────────────────────────────────────────────────┤
│ LLM SEO analyse le Title:                                   │
│ "Nappe en Coton 160x200" → "Nappe" → normalize_type()      │
│                                                              │
│ Génère:                                                      │
│ • type = "NAPPES" (MAJUSCULES, PLURIEL, SANS ACCENTS)      │
│                                                              │
│ Sauvegarde:                                                  │
│ • CSV Shopify: Type = "NAPPES"                             │
│ • Cache interne: csv_type = "NAPPES"                       │
└─────────────────────────────────────────────────────────────┘
                           ↓
┌─────────────────────────────────────────────────────────────┐
│ PHASE 2: GOOGLE SHOPPING                                    │
├─────────────────────────────────────────────────────────────┤
│ 1. Recherche règle avec:                                    │
│    • product_type = "Accessoire" (original CSV)            │
│    • csv_type = "NAPPES" (normalisé)                       │
│                                                              │
│ 2a. SI RÈGLE TROUVÉE (ex: "NAPPES" → "Home & Garden")     │
│     ✅ Utilisation directe                                  │
│     • confidence = règle.confidence                         │
│     • 0 appel LLM                                           │
│                                                              │
│ 2b. SI PAS DE RÈGLE                                         │
│     🤖 Appel LLM Google Shopping                            │
│     • Reçoit: product_data complet                          │
│       (Title, Type="Accessoire", Body HTML, Tags, etc.)    │
│     • Retourne: category + CONFIDENCE                       │
│     • Crée automatiquement une RÈGLE:                       │
│       - product_type = "Accessoire"                         │
│       - csv_type = "NAPPES"                                 │
│       - category = "Home & Garden > Linens..."             │
│       - confidence = 0.85 (du LLM)                          │
└─────────────────────────────────────────────────────────────┘
```

## Résumé des réponses :

### Q1: Qu'est-ce qu'on envoie au LLM Google Shopping ?

**Réponse** : On envoie `product_data` complet avec :
- `Title` : "Nappe en Coton 160x200"
- `Type` : "Accessoire" (ou "NAPPES" si déjà mis à jour par SEO)
- `Body (HTML)` : Description complète
- `Tags` : Tags du produit
- Tous les autres champs CSV

⚠️ **Important** : Le LLM Google Shopping reçoit le champ `Type` du CSV (qui peut être l'original "Accessoire" ou le normalisé "NAPPES"), **PAS le csv_type**.

### Q2: La confidence des règles vient bien du LLM Google Shopping ?

**Réponse** : **Oui**, mais avec nuances :

1. **Règles auto-créées** : confidence = celle retournée par le LLM Google Shopping (ex: 0.85)
2. **Règles manuelles** : confidence = 1.0 (par défaut)

La confidence du LLM Google Shopping est utilisée pour :
- Décider si on remonte à la catégorie parente (si < 0.5)
- Protéger les règles contre les modifications automatiques (si ≥ 0.9)
- Créer automatiquement des règles dans `type_category_mapping`

## Code source :

- **Vérification des règles** : `processor.py` lignes 443-488
- **Appel LLM Google Shopping** : `processor.py` lignes 489-566
- **Création de règle** : `processor.py` ligne 560-566 (appelle `_update_concordance_table`)
- **Protection des règles** : `processor.py` ligne 116 (seuil de confidence)
