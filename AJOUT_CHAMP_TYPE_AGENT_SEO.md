# Ajout du champ Type dans l'Agent SEO

## Résumé des modifications

Le champ **Type** a été ajouté aux champs modifiables de l'Agent SEO. Le type est automatiquement normalisé selon les règles suivantes :
- **MAJUSCULES** : Toujours en lettres capitales
- **PLURIEL** : Toujours au pluriel (ex: "Nappe" → "NAPPES")
- **SANS ACCENTS** : Tous les accents français sont supprimés (É → E, È → E, Ê → E, etc.)

## Modifications apportées

### 1. Code Python

#### `apps/ai_editor/processor.py`
- ✅ Ajout de `'type': 'Type'` au mapping `SEO_FIELD_MAPPING`
- Ce mapping permet de faire correspondre la clé JSON `type` retournée par le LLM au champ CSV `Type`

#### `apps/ai_editor/agents.py`
- ✅ Ajout du champ `'type'` dans le retour de la méthode `SEOAgent.generate()`
- ✅ Mise à jour de la documentation de la méthode (9 champs au lieu de 8)
- ✅ Ajout de `'type': ''` dans l'initialisation du dictionnaire de résultats
- ✅ Ajout de `'Type:': 'type'` dans les marqueurs de champs (parsing texte structuré)
- ✅ Mise à jour du format JSON de sortie batch pour inclure le champ `type`
- ✅ Mise à jour des instructions de contenu pour spécifier le format du champ `type`

#### `apps/ai_editor/gui/window.py`
- ✅ Ajout de `'type': ctk.BooleanVar(value=True)` dans `self.seo_field_vars`
- ✅ Ajout de `'type': 'Type'` dans `seo_field_labels`
- Cela permet à l'utilisateur de cocher/décocher le champ Type dans l'interface

#### `utils/text_utils.py` (nouveau fichier)
- ✅ Création de la fonction `normalize_type()` pour normaliser automatiquement le type
- ✅ Suppression des accents (utilise `unicodedata.normalize('NFD')`)
- ✅ Conversion en majuscules (utilise `.upper()`)
- ✅ Ajout du pluriel si nécessaire (ajoute 'S' si absent)

### 2. Prompt SEO

Le prompt SEO a été mis à jour dans la base de données (`database/ai_prompts.db`) :

**Avant** : 6 champs SEO
**Après** : 7 champs SEO

**Nouveau champ ajouté (position 7)** :
```
7. type
   - Type de produit au PLURIEL et en MAJUSCULES, SANS ACCENTS
   - Format: MAJUSCULES, PLURIEL, SANS ACCENTS FRANÇAIS
   - Exemples: "NAPPES", "TORCHONS", "PLAIDS", "SERVIETTES DE TABLE", "CHEMINS DE TABLE"
   - Style: Simple et standardisé
   - Utilise le Title pour déterminer le type le plus approprié
   - IMPORTANT: Toujours au pluriel et en majuscules (ex: "Nappe" → "NAPPES")
```

## Fonctionnement

### Sélection du champ

Dans l'interface de l'éditeur IA, l'utilisateur peut maintenant :
1. Cocher/décocher la case "Type" dans la section "Agent SEO"
2. Si **cochée** : le LLM génère un nouveau type basé sur le nom du produit (Title)
3. Si **décochée** : le type original du CSV est conservé (pas de modification)

### Génération et normalisation automatique

Lorsque le champ est sélectionné, le LLM analyse le **Title** (nom du produit) et suggère un type. Ce type est ensuite **automatiquement normalisé** selon les règles :

**Exemples de normalisation** :
- Title: "Nappe en Coton Jacquard 160x200cm" → LLM suggère: "Nappe" → **Normalisé: "NAPPES"**
- Title: "Torchon Éponge Absorbant 50x70cm" → LLM suggère: "Torchon" → **Normalisé: "TORCHONS"**
- Title: "Plaid Laine Mérinos 130x170cm" → LLM suggère: "Plaid" → **Normalisé: "PLAIDS"**
- Title: "Serviette de Table Lin Lavé" → LLM suggère: "Serviette de table" → **Normalisé: "SERVIETTES DE TABLE"**
- Title: "Chemin de Table Festif 40x140cm" → LLM suggère: "Chemin de table" → **Normalisé: "CHEMINS DE TABLE"**

**Règles de normalisation** :
1. **Suppression des accents** : É → E, È → E, Ê → E, À → A, etc.
2. **Conversion en majuscules** : Toutes les lettres deviennent capitales
3. **Ajout du pluriel** : Si le mot ne se termine pas par S, X ou Z, un S est ajouté

### Format JSON de sortie

Le LLM retourne maintenant un JSON avec 9 champs (au lieu de 8) :

```json
{
  "products": [
    {
      "handle": "nappe-coton-jacquard",
      "seo_title": "...",
      "seo_description": "...",
      "title": "Nappe en Coton Jacquard 160x200cm",
      "body_html": "...",
      "tags": "...",
      "image_alt_text": "...",
      "type": "NAPPES",
      "csv_type": "NAPPES",
      "csv_type_confidence": 0.95
    }
  ]
}
```

**Note** : Le LLM peut retourner "Nappe" ou "NAPPES", mais la normalisation automatique garantit que le type sera toujours "NAPPES" dans le CSV final.

## Différence entre `type` et `csv_type`

**IMPORTANT** : Les deux champs suivent maintenant le même format :

1. **`type`** (nouveau) :
   - Type de produit au **PLURIEL**, en **MAJUSCULES**, **SANS ACCENTS**
   - Utilisé pour l'affichage dans Shopify (champ "Type")
   - Exemples : "NAPPES", "TORCHONS", "PLAIDS"
   - **Modifiable** via la checkbox dans l'interface
   - **Normalisé automatiquement** par la fonction `normalize_type()`

2. **`csv_type`** (existant) :
   - Type suggéré au **PLURIEL**, en **MAJUSCULES**, **SANS ACCENTS**
   - Utilisé pour la concordance interne (table `type_category_mapping`)
   - Exemples : "NAPPES", "TORCHONS", "COUVERTURES"
   - **Toujours généré** automatiquement (non modifiable par checkbox)

**En pratique** : Les deux champs ont le même format et devraient avoir la même valeur. Le `csv_type` est utilisé pour la concordance avec Google Shopping, tandis que `type` est le champ visible dans le CSV Shopify.

## Scripts de mise à jour

Les scripts suivants ont été créés et exécutés :

1. **`update_seo_prompt_add_type.py`** : Ajoute le champ Type au prompt SEO
2. **`clean_seo_prompt.py`** : Nettoie les lignes dupliquées

Ces scripts ont été exécutés avec succès sur les 2 prompts :
- ✅ "Prompt JL 1"
- ✅ "Template initiale"

## Test recommandé

Pour tester la fonctionnalité :

1. Ouvrir l'interface de l'éditeur IA
2. Importer un CSV avec des produits
3. Dans la section "Agent SEO", vérifier que la checkbox "Type" est présente
4. Cocher/décocher pour tester :
   - **Cochée** : le LLM suggère un nouveau type
   - **Décochée** : le type original est conservé
5. Lancer le traitement et vérifier les résultats

## Notes techniques

### Normalisation automatique

La normalisation du type est effectuée dans `processor.py` (lignes 219-232) :

```python
# NORMALISATION SPÉCIALE POUR LE CHAMP TYPE
if json_key == 'type':
    # Normaliser : MAJUSCULES, PLURIEL, SANS ACCENTS
    new_value = normalize_type(new_value)
    logger.info(f"📝 {handle}: Type normalisé: {result[json_key]} → {new_value}")
```

### Fonction de normalisation

La fonction `normalize_type()` dans `utils/text_utils.py` :
1. Supprime les accents avec `unicodedata.normalize('NFD')`
2. Convertit en majuscules avec `.upper()`
3. Ajoute un 'S' à la fin si nécessaire (pluriel)

### Comportement de désélection

- La logique de désélection existante fonctionne pour ce nouveau champ
- Le champ est mappé dans `SEO_FIELD_MAPPING` donc il sera traité automatiquement
- Le système vérifie `seo_selected_fields` avant de mettre à jour chaque champ
- Si le champ n'est pas sélectionné, il ne sera pas dans `field_updates` et donc pas modifié dans le CSV
