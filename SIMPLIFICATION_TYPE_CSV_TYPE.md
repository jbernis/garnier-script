# Simplification : type = csv_type

## Problème identifié

Le système demandait au LLM de générer **deux champs identiques** :
- `type` : Type pour le CSV Shopify (MAJUSCULES, PLURIEL, SANS ACCENTS)
- `csv_type` : Type pour la concordance interne (MAJUSCULES, PLURIEL, SANS ACCENTS)

**Résultat** : Redondance inutile, le LLM générait la même valeur deux fois.

## Solution

**Un seul champ : `type`**

Le champ `type` est maintenant utilisé pour :
1. Le CSV Shopify (champ "Type")
2. Le cache interne (`product_category_cache.csv_type`)
3. La concordance Google Shopping (`type_category_mapping`)

## Modifications

### 1. `apps/ai_editor/processor.py`

**Avant** :
```python
csv_type = result.get('csv_type', '').strip()
csv_type_confidence = float(result.get('csv_type_confidence', 0.0))
```

**Après** :
```python
type_value = result.get('type', '').strip()
# Pour compatibilité, on accepte aussi csv_type si type n'est pas présent
if not type_value:
    type_value = result.get('csv_type', '').strip()
```

### 2. `apps/ai_editor/agents.py`

**Champs retournés** :
- **Avant** : 9 champs (incluant `csv_type` et `csv_type_confidence`)
- **Après** : 7 champs (seulement `type`)

**Format JSON** :
```json
{
  "products": [
    {
      "handle": "nappe-coton",
      "seo_title": "...",
      "seo_description": "...",
      "title": "...",
      "body_html": "...",
      "tags": "...",
      "image_alt_text": "...",
      "type": "NAPPES"
    }
  ]
}
```

## Flux de données

```
LLM génère "type"
    ↓
normalize_type() → "NAPPES"
    ↓
    ├─→ CSV Shopify (champ "Type")
    └─→ Cache interne (csv_type)
         └─→ type_category_mapping
```

## Avantages

✅ **Simplicité** : Un seul champ à gérer
✅ **Performance** : Moins de tokens utilisés par le LLM
✅ **Cohérence** : Garantie que type = csv_type
✅ **Maintenance** : Code plus simple

## Rétrocompatibilité

Le code accepte encore `csv_type` si `type` n'est pas présent (fallback) :
```python
if not type_value:
    type_value = result.get('csv_type', '').strip()
```

## Résumé

| Champ | Avant | Après |
|-------|-------|-------|
| `type` | Type Shopify (MAJUSCULES, PLURIEL) | Type unique (MAJUSCULES, PLURIEL, SANS ACCENTS) |
| `csv_type` | Type interne (MAJUSCULES, PLURIEL) | ❌ Supprimé du LLM (rempli automatiquement par `type`) |
| `csv_type_confidence` | Confiance du LLM | ❌ Supprimé (non nécessaire) |

**Conclusion** : `type` et `csv_type` sont maintenant **la même chose**, mais `csv_type` n'est plus demandé au LLM, il est rempli automatiquement depuis `type`.
