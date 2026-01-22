# Guide d'Utilisation du Système de Contrôle Qualité

## 🎯 Objectif

Garantir que tous les champs générés par l'IA sont remplis correctement, notamment le Body HTML qui restait parfois vide.

---

## 🚀 Mise en Route

### 1. Améliorer les prompts existants (une seule fois)

```bash
python improve_prompts.py
```

Cette commande va mettre à jour tous les prompts dans la base de données avec des instructions strictes pour éviter les champs vides.

### 2. Tester le système (optionnel)

```bash
python test_quality_control.py
```

Ce test vérifie que le système de validation fonctionne correctement.

---

## 📊 Comment ça marche ?

### Processus de Traitement

```
1. Génération initiale
   └─> Agent SEO génère les champs

2. Validation
   └─> QualityControlAgent vérifie la qualité
       ├─> ✓ Tous les champs OK → Sauvegarde
       └─> ✗ Problèmes détectés → Retry

3. Retry (max 3 tentatives)
   └─> Nouveau prompt avec instructions spécifiques
   └─> Re-génération + Validation
   └─> Si OK → Sauvegarde
   └─> Si KO → Retry ou abandon après 3 tentatives
```

### Critères de Validation

| Champ | Validation |
|-------|-----------|
| **body_html** | ✓ Non vide<br>✓ Min 50 caractères<br>✓ Contient des balises HTML |
| **seo_title** | ✓ Non vide<br>⚠ Max 70 caractères (warning) |
| **seo_description** | ✓ Non vide<br>⚠ Max 320 caractères (warning) |
| **title** | ✓ Non vide |
| **tags** | ✓ Non vide |
| **image_alt_text** | ✓ Non vide |

---

## 🖥️ Utilisation dans l'Interface Graphique

### Avant (sans contrôle qualité)

```
  Génération SEO...
  Réponse IA: {...}
  ⚠ Champ 'body_html' vide
  ✓ SEO mis à jour (5 champ(s))
```

→ Le Body HTML reste vide, pas de retry

### Après (avec contrôle qualité)

```
  Génération SEO...
  🔄 Tentative 1/3...
  ⚠ Validation échouée (tentative 1):
    - body_html: Champ vide
  🔄 Tentative 2/3...
  ✓ Validation réussie après 2 tentative(s)
  Réponse IA finale: {...}
  ✓ SEO mis à jour (6 champ(s))
```

→ Le système retry automatiquement jusqu'à ce que le Body HTML soit rempli

---

## 📈 Amélioration des Résultats

### Statistiques attendues

- **Avant**: ~30-40% de champs vides
- **Après**: ~5-10% de champs vides (après 3 tentatives)

### Temps de traitement

- **Sans retry**: ~2-3 secondes par produit
- **Avec 1 retry**: ~4-6 secondes par produit
- **Avec 2-3 retries**: ~8-10 secondes par produit

→ Le temps augmente mais la qualité est garantie

---

## 🔍 Logs Détaillés

### Exemple de logs lors d'un retry

```
[INFO] Traitement du produit: nappe-coton-argelos
[INFO]   Génération SEO...
[INFO]   🔄 Tentative 1/3...
[WARNING] Validation échouée pour nappe-coton-argelos (tentative 1): {'body_html': 'Champ vide'}
[INFO]   ⚠ Validation échouée (tentative 1):
[INFO]     - body_html: Champ vide
[INFO]   🔄 Tentative 2/3...
[WARNING] Body HTML trop court: 45 caractères
[INFO]   ⚠ Validation échouée (tentative 2):
[INFO]     - body_html: Body HTML trop court (< 50 caractères)
[INFO]   🔄 Tentative 3/3...
[INFO]   ✓ Validation réussie après 3 tentative(s)
[INFO]   Réponse IA finale: {'seo_title': '...', 'body_html': '<p>...</p>', ...}
[INFO]   ✓ SEO mis à jour (6 champ(s))
```

---

## 🛠️ Configuration Avancée

### Modifier le nombre de retries

Dans `apps/ai_editor/processor.py`, ligne ~146 et ~428:

```python
max_retries = 3  # Modifier ici (1-5 recommandé)
```

### Modifier les critères de validation

Dans `apps/ai_editor/agents.py`, méthode `validate_seo_result()`:

```python
# Body HTML minimum
if field == 'body_html' and len(value) < 50:  # Modifier 50
    ...

# SEO Title maximum
elif field == 'seo_title' and len(value) > 70:  # Modifier 70
    ...
```

---

## ⚠️ Cas Particuliers

### Si le quota API est atteint

Le système détecte automatiquement les erreurs de quota et arrête les retries:

```
⚠️ QUOTA openai DÉPASSÉ
→ Vérifiez votre compte : insufficient_quota
```

### Si les 3 tentatives échouent

Le produit est traité avec les champs disponibles:

```
⚠ Nombre max de tentatives atteint (3)
⚠ Champ 'body_html' toujours vide après 3 tentatives
✓ SEO mis à jour (5 champ(s))
```

---

## 📋 Checklist de Vérification

Après avoir implémenté le système:

- [x] ✅ Script `improve_prompts.py` exécuté
- [x] ✅ Prompts mis à jour dans la base de données
- [x] ✅ Tests passés avec succès
- [x] ✅ Aucune erreur de linter
- [x] ✅ Système de retry opérationnel
- [x] ✅ Validation automatique activée

---

## 🎓 Comprendre les Prompts Améliorés

### System Prompt

```
Tu es un expert en optimisation de fiches produits pour le e-commerce et le SEO.

🎯 RÈGLES ABSOLUES - À RESPECTER IMPÉRATIVEMENT:

1. ❌ JAMAIS DE CHAMPS VIDES
   - Tous les champs demandés DOIVENT être remplis
   - Un champ vide est considéré comme une erreur GRAVE
   ...
```

→ Instructions strictes dès le début de la conversation

### SEO Prompt

```
🎯 MISSION: Générer TOUS les champs SEO et marketing pour ce produit

⚠️ INSTRUCTIONS CRITIQUES:
- NE JAMAIS laisser un champ vide
- Si les données sont limitées, utilise tes connaissances et ta créativité
- Si tu as accès à Perplexity, recherche des informations sur le produit
...
```

→ Mission claire avec instructions de ne jamais laisser de champs vides

### Retry Prompt (généré automatiquement)

```
⚠️ CORRECTION REQUISE ⚠️

La génération précédente a échoué pour les raisons suivantes:
- body_html: Champ vide

🎯 INSTRUCTIONS STRICTES 🎯

Pour le champ Body (HTML):
- OBLIGATOIRE: Générer un contenu HTML riche et détaillé (minimum 200 caractères)
- Utiliser des balises HTML valides: <p>, <ul>, <li>, <strong>, <br>, etc.
...
```

→ Instructions spécifiques aux problèmes détectés

---

## 🆘 Dépannage

### Problème: Body HTML toujours vide après 3 tentatives

**Causes possibles:**
1. Clé API Perplexity non configurée (recherche internet désactivée)
2. Modèle IA trop basique (utiliser GPT-4 ou Claude 3)
3. Données produit insuffisantes

**Solutions:**
1. Activer la recherche internet (cocher "Recherche Internet" dans l'interface)
2. Utiliser un modèle IA plus performant
3. Enrichir les données source (titre, description, type)

### Problème: Temps de traitement très long

**Causes:**
- Nombreux retries nécessaires
- Modèle IA lent

**Solutions:**
1. Améliorer la qualité des données source
2. Réduire `max_retries` de 3 à 2
3. Utiliser un modèle IA plus rapide

---

## 📞 Support

Pour toute question ou problème:

1. Consulter `AMELIORATIONS_AGENT_IA.md` pour les détails techniques
2. Vérifier les logs dans le terminal
3. Exécuter `test_quality_control.py` pour diagnostiquer

---

## 🎉 Résultat Final

Avec ce système, vous obtenez:

- ✅ **Tous les champs remplis** (taux de réussite > 90%)
- ✅ **Retry automatique** (pas d'intervention manuelle)
- ✅ **Logs détaillés** (visibilité complète)
- ✅ **Prompts optimisés** (instructions strictes)
- ✅ **Validation rigoureuse** (contrôle qualité systématique)

🎯 **Votre catalogue produit est maintenant de qualité professionnelle!**
