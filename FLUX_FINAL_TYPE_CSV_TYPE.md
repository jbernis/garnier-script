# Flux Final : type = csv_type

## Question : Le LLM SEO doit-il générer type ET csv_type, ou seulement type ?

### ✅ RÉPONSE : Le LLM génère SEULEMENT `type`

Le système copie automatiquement `type` dans `csv_type` pour garantir qu'ils sont toujours identiques.

## Flux complet et optimisé :

```
┌────────────────────────────────────────────────────────────┐
│ 1. LLM SEO GÉNÈRE                                          │
├────────────────────────────────────────────────────────────┤
│ Le LLM génère UN SEUL champ :                             │
│   • type: "NAPPES" (ou "Nappe" si pas encore normalisé)  │
│                                                            │
│ Format JSON retourné :                                     │
│ {                                                          │
│   "handle": "nappe-coton",                                │
│   "type": "NAPPES",  ← UN SEUL CHAMP                      │
│   "seo_title": "...",                                      │
│   ...                                                      │
│ }                                                          │
└────────────────────────────────────────────────────────────┘
                          ↓
┌────────────────────────────────────────────────────────────┐
│ 2. NORMALISATION AUTOMATIQUE                               │
├────────────────────────────────────────────────────────────┤
│ normalize_type() est appliqué :                           │
│   "Nappe" → "NAPPES"                                      │
│   "Éponge" → "EPONGES"                                    │
│   "Serviette de table" → "SERVIETTES DE TABLE"           │
│                                                            │
│ Règles :                                                   │
│   • MAJUSCULES                                             │
│   • PLURIEL (ajoute S si absent)                          │
│   • SANS ACCENTS (É→E, È→E, À→A, etc.)                   │
│                                                            │
│ Code : processor.py lignes 224-230                        │
└────────────────────────────────────────────────────────────┘
                          ↓
┌────────────────────────────────────────────────────────────┐
│ 3. COPIE AUTOMATIQUE                                       │
├────────────────────────────────────────────────────────────┤
│ Le type normalisé est copié dans 2 endroits :            │
│                                                            │
│ A. CSV Shopify (champ "Type")                             │
│    field_updates['Type'] = "NAPPES"                       │
│    └─→ Visible dans le fichier CSV final                 │
│                                                            │
│ B. Cache interne (champ csv_type)                         │
│    cache.csv_type = "NAPPES"                              │
│    └─→ Utilisé pour la concordance Google Shopping       │
│                                                            │
│ Code : processor.py lignes 350-368                        │
│                                                            │
│ ✅ GARANTIE : CSV.Type = cache.csv_type = "NAPPES"       │
└────────────────────────────────────────────────────────────┘
```

## Code source (processor.py) :

```python
# ÉTAPE 1 : Le LLM retourne 'type'
result = {
    'type': 'NAPPES',  # ← UN SEUL CHAMP généré par le LLM
    'seo_title': '...',
    ...
}

# ÉTAPE 2 : Normalisation
if json_key == 'type':
    original_type = new_value
    new_value = normalize_type(new_value)  # "Nappe" → "NAPPES"
    logger.info(f"Type normalisé: '{original_type}' → '{new_value}'")

# ÉTAPE 3A : Sauvegarde dans le CSV
field_updates['Type'] = new_value  # CSV.Type = "NAPPES"

# ÉTAPE 3B : Copie dans csv_type
type_value = field_updates.get('Type', '').strip()
cursor.execute('''
    UPDATE product_category_cache
    SET csv_type = ?
    WHERE product_key = ?
''', (type_value, product_key))  # cache.csv_type = "NAPPES"

logger.info(f"Type copié → CSV.Type = cache.csv_type = '{type_value}'")
```

## Avantages de cette approche :

✅ **Simple** : Le LLM génère UN SEUL champ
✅ **Cohérent** : type = csv_type garanti par copie automatique
✅ **Maintenable** : Une seule source de vérité (type)
✅ **Performant** : Moins de tokens utilisés

## Format JSON du LLM SEO :

```json
{
  "products": [
    {
      "handle": "nappe-coton-jacquard",
      "seo_title": "Nappe en Coton Jacquard 160x200cm - Linge de Table",
      "seo_description": "Découvrez notre nappe en coton jacquard...",
      "title": "Nappe en Coton Jacquard 160x200cm",
      "body_html": "<p>Magnifique nappe...</p>",
      "tags": "nappe, linge de table, coton, jacquard",
      "image_alt_text": "Nappe en coton jacquard sur table",
      "type": "NAPPES"
    }
  ]
}
```

**Note** : Le LLM génère `type: "NAPPES"` (ou parfois `"Nappe"` si le prompt n'est pas respecté), et le système normalise automatiquement pour garantir le format MAJUSCULES/PLURIEL/SANS ACCENTS.

## Résumé visuel :

```
LLM SEO
   ↓
type = "NAPPES"
   ↓
   ├─→ CSV Shopify : Type = "NAPPES"
   └─→ Cache interne : csv_type = "NAPPES"

✅ CSV.Type = cache.csv_type = "NAPPES"
```

## Garantie :

**À TOUT MOMENT** :
- `product_data['Type']` (CSV) = "NAPPES"
- `cache.csv_type` (DB) = "NAPPES"
- `type_category_mapping.csv_type` (règles) = "NAPPES"

**UNE SEULE VALEUR, TROIS EMPLACEMENTS SYNCHRONISÉS** 🎯
