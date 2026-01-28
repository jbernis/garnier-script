# Correction: Gestion de la colonne Google Product Category

## Date
2026-01-25

## Problème identifié

Lors de la régénération d'un CSV depuis l'historique, deux problèmes survenaient :

1. **Colonne "Product Category"** : était systématiquement vidée alors qu'elle devrait conserver sa valeur d'origine
2. **Colonne "Google Shopping / Google Product Category"** : contenait parfois le chemin textuel (ex: "Maison et jardin > Linge > Literie") au lieu de l'ID numérique Google (ex: "569")

## Solution implémentée

### 1. Suppression du vidage de "Product Category"

**Fichier** : `apps/ai_editor/csv_storage.py` (fonction `export_csv()`)

**Modification** : Supprimé les lignes qui vidaient systématiquement la colonne "Product Category"

```python
# AVANT (lignes 405-408) - SUPPRIMÉ
if 'Product Category' in df.columns:
    df['Product Category'] = ''
    logger.debug("Colonne 'Product Category' vidée")
```

**Résultat** : La colonne "Product Category" conserve maintenant sa valeur d'origine lors de l'export.

---

### 2. Conversion automatique des chemins en IDs

**Fichier** : `apps/ai_editor/csv_storage.py` (fonction `export_csv()`)

**Modification** : Ajout d'une logique de conversion après la ligne 403

```python
# Convertir les chemins textuels en IDs numériques
converted_count = 0
for idx in df.index:
    google_cat = df.at[idx, 'Google Shopping / Google Product Category']
    
    # Si la valeur contient " > ", c'est un chemin textuel, pas un ID
    if google_cat and isinstance(google_cat, str) and ' > ' in google_cat:
        # Tenter de retrouver l'ID dans la taxonomie
        category_id = self.db.search_google_category(google_cat)
        if category_id:
            df.at[idx, 'Google Shopping / Google Product Category'] = category_id
            converted_count += 1
            logger.debug(f"Converti chemin → ID: '{google_cat}' → '{category_id}'")
        # Si ID non trouvé, on laisse la valeur telle quelle (pas de vidage forcé)

if converted_count > 0:
    logger.info(f"✓ Converti {converted_count} chemin(s) textuel(s) en ID(s) Google")
```

**Comportement** :
- ✅ Si la valeur contient " > " (chemin textuel) → recherche l'ID dans la taxonomie
- ✅ Si ID trouvé → remplace le chemin par l'ID
- ✅ Si ID non trouvé → laisse la valeur telle quelle (pas de vidage forcé)
- ✅ Si la valeur est déjà un ID ou vide → aucune modification

---

### 3. Validation dans processor.py

**Fichier** : `apps/ai_editor/processor.py` (ligne 536)

**Modification** : Ajout d'un warning si `category_code` contient un chemin au lieu d'un ID

```python
if category_code:
    # Validation : vérifier que category_code est bien un ID, pas un chemin
    if isinstance(category_code, str) and ' > ' in category_code:
        logger.warning(f"⚠️ {handle}: category_code contient un chemin au lieu d'un ID: '{category_code}'")
        logger.warning(f"  Ce chemin devrait être un ID numérique. Vérifier search_google_category().")
    
    # Sauvegarder dans la base...
```

**Résultat** : Alerte les développeurs si un chemin textuel est sauvegardé au lieu d'un ID.

---

## Tests effectués

### Script de test : `test_google_category_conversion.py`

Testé avec différents types de valeurs :

| Valeur d'entrée | Résultat |
|----------------|----------|
| `"Maison et jardin > Linge > Literie"` | ✅ Converti en ID `569` |
| `"Maison et jardin > Arts de la table > Linge de table"` | ✅ Converti en ID `4708` |
| `"Maison et jardin > Cuisine > Ustensiles de cuisson"` | ✅ Converti en ID `3713` |
| `"Alimentation, boissons et tabac > Boissons > Thé et infusions"` | ✅ Converti en ID `2073` |
| `"Chemin invalide qui n'existe pas"` | ✅ Laissé tel quel (pas de vidage) |
| `""` (vide) | ✅ Laissé vide |
| `"12345"` (déjà un ID) | ✅ Laissé tel quel |

---

## Impact

### Positif
- ✅ La colonne "Product Category" n'est plus vidée (conserve sa valeur d'origine)
- ✅ Les chemins textuels dans "Google Shopping / Google Product Category" sont automatiquement convertis en IDs lors de l'export
- ✅ Les valeurs invalides ne sont pas forcées à vide (préservation des données)
- ✅ Meilleure traçabilité avec des logs informatifs

### Fichiers modifiés
1. `apps/ai_editor/csv_storage.py` - Fonction `export_csv()`
2. `apps/ai_editor/processor.py` - Validation avant sauvegarde

### Tests
- Script de test créé : `test_google_category_conversion.py`
- Tous les tests passent ✅

---

## Utilisation

Lors de la régénération d'un CSV depuis l'historique :

1. Ouvrir l'onglet "Historique" dans l'application
2. Sélectionner un import
3. Cliquer sur "Régénérer le CSV"
4. Le CSV exporté contiendra :
   - ✅ "Google Shopping / Google Product Category" avec l'ID numérique (pas le chemin)
   - ✅ "Product Category" avec sa valeur d'origine (non vidée)

---

## Notes techniques

- La fonction `search_google_category()` cherche l'ID dans la table `google_taxonomy`
- Les chemins sont détectés par la présence du caractère " > "
- La conversion est faite uniquement lors de l'export CSV (pas lors du traitement IA)
- Les warnings sont loggés si un chemin est sauvegardé au lieu d'un ID
