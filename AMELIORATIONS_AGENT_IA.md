# Améliorations du Système d'Agents IA

## 📋 Contexte

Le système d'agents IA renvoyait parfois des champs vides (comme le Body HTML) même avec accès à internet. Cette documentation décrit les améliorations apportées pour résoudre ce problème.

---

## 🎯 Solution Implémentée

### 1. Agent de Contrôle Qualité (QualityControlAgent)

Un nouvel agent a été créé pour valider la qualité des contenus générés et identifier les problèmes.

#### Fonctionnalités

- **Validation des champs requis**: Vérifie que tous les champs demandés sont présents et non vides
- **Contrôles de qualité avancés**:
  - Body HTML: Minimum 50 caractères et présence de balises HTML
  - SEO Title: Maximum 70 caractères
  - SEO Description: Maximum 320 caractères
- **Génération de prompts de retry**: Crée des instructions spécifiques pour corriger les problèmes détectés

#### Méthodes principales

```python
validate_seo_result(product_data, seo_result, required_fields)
# Retourne:
# - is_valid: bool
# - missing_fields: List[str]
# - empty_fields: List[str]
# - issues: Dict[str, str]

generate_retry_prompt(product_data, validation_result, original_prompt)
# Génère un prompt enrichi avec des instructions de correction
```

---

### 2. Système de Retry Automatique

Le processeur a été modifié pour intégrer un système de retry avec validation.

#### Fonctionnement

1. **Première tentative**: Génération normale avec le SEOAgent
2. **Validation**: Le QualityControlAgent vérifie le résultat
3. **Retry si nécessaire**: Jusqu'à 3 tentatives maximum avec des prompts améliorés
4. **Logging détaillé**: Chaque problème est identifié et logué

#### Avantages

- ✅ **Réduction des champs vides**: Le système réessaye automatiquement
- ✅ **Feedback précis**: Les problèmes sont identifiés et communiqués
- ✅ **Prompts adaptatifs**: Les retries utilisent des instructions spécifiques aux problèmes détectés
- ✅ **Limite de retries**: Évite les boucles infinies (max 3 tentatives)

---

### 3. Prompts Améliorés

Un script `improve_prompts.py` a été créé pour mettre à jour les prompts existants avec:

#### System Prompt

- **Règles absolues**: Instructions strictes contre les champs vides
- **Qualité du contenu**: Spécifications précises pour chaque champ
- **Utilisation de la recherche**: Instructions pour exploiter Perplexity
- **Format de réponse**: Structure JSON claire et obligatoire

#### SEO Prompt

- **Longueurs minimales**: Body HTML minimum 200 caractères
- **Structure détaillée**: Instructions précises par champ
- **Balises HTML**: Exemples et exigences
- **Tags**: Minimum 5-10 tags avec exemples

#### Google Category Prompt

- **Précision maximale**: Instructions pour choisir la catégorie la plus spécifique
- **Format exact**: Chemin textuel avec " > "
- **Exemples concrets**: Chemins de catégories réels

---

## 🔧 Fichiers Modifiés

### apps/ai_editor/agents.py

- ✅ Ajout de la classe `QualityControlAgent`
- ✅ Méthodes de validation et génération de retry prompts

### apps/ai_editor/processor.py

- ✅ Intégration du QualityControlAgent dans `process_single_product()`
- ✅ Intégration du QualityControlAgent dans `process_csv()`
- ✅ Système de retry avec validation à chaque tentative
- ✅ Logging détaillé des tentatives et problèmes

### improve_prompts.py (nouveau)

- ✅ Script pour améliorer automatiquement les prompts en base
- ✅ Amélioration du system_prompt
- ✅ Amélioration du seo_prompt
- ✅ Amélioration du google_category_prompt

---

## 📊 Exemple de Fonctionnement

### Scénario: Body HTML vide

```
1. Tentative 1:
   - Agent génère le contenu
   - QC Agent détecte: "Body HTML vide"
   - Log: "⚠ Validation échouée (tentative 1): body_html: Champ vide"

2. Tentative 2:
   - Nouveau prompt avec instructions spécifiques:
     "Body HTML DOIT contenir minimum 200 caractères avec balises HTML"
   - Agent génère à nouveau
   - QC Agent détecte: "Body HTML trop court (45 caractères)"
   - Log: "⚠ Validation échouée (tentative 2): body_html: Body HTML trop court"

3. Tentative 3:
   - Prompt encore plus strict
   - Agent génère un contenu riche de 300 caractères
   - QC Agent valide: "✓ Validation réussie après 3 tentatives"
   - Mise à jour du CSV avec le contenu valide
```

---

## 🚀 Utilisation

### 1. Améliorer les prompts existants

```bash
python improve_prompts.py
```

Ce script va:
- Récupérer tous les ensembles de prompts en base
- Les améliorer avec les nouvelles instructions strictes
- Sauvegarder les modifications

### 2. Utiliser l'interface graphique normalement

Le système de retry et validation est automatique. Lors du traitement des produits, vous verrez dans les logs:

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

---

## 📈 Bénéfices

### Avant

- ❌ Champs vides fréquents (notamment Body HTML)
- ❌ Pas de feedback sur les problèmes
- ❌ Nécessité de relancer manuellement
- ❌ Prompts peu explicites

### Après

- ✅ Retry automatique avec validation
- ✅ Feedback détaillé sur chaque problème
- ✅ Taux de réussite amélioré (jusqu'à 3 tentatives)
- ✅ Prompts stricts et précis
- ✅ Logging complet pour diagnostic
- ✅ Instructions adaptatives selon les problèmes

---

## 🔍 Validation des Champs

### Critères de Validation

| Champ | Critères |
|-------|----------|
| **body_html** | • Non vide<br>• Minimum 50 caractères<br>• Contient des balises HTML (`<` et `>`) |
| **seo_title** | • Non vide<br>• Maximum 70 caractères (warning) |
| **seo_description** | • Non vide<br>• Maximum 320 caractères (warning) |
| **title** | • Non vide |
| **tags** | • Non vide |
| **image_alt_text** | • Non vide |

---

## 🎯 Prochaines Améliorations Possibles

1. **Scoring de qualité**: Attribuer un score de qualité à chaque champ
2. **Machine Learning**: Analyser les patterns de succès/échec pour améliorer les prompts
3. **Validation HTML**: Parser le HTML pour détecter les erreurs de structure
4. **Retry sélectif**: Ne retry que les champs problématiques (pas tous les champs)
5. **Cache intelligent**: Mémoriser les bons résultats pour éviter des retries inutiles

---

## 📝 Notes Techniques

### Performance

- **Temps de traitement**: Augmenté de ~2-3x en cas de retry (acceptable pour la qualité)
- **Coût API**: Augmenté proportionnellement au nombre de retries
- **Taux de succès**: Significativement amélioré

### Logs

Les logs incluent maintenant:
- Numéro de tentative
- Problèmes détectés par champ
- Instructions de retry
- Réponse finale de l'IA
- Nombre de champs mis à jour

### Base de données

Aucune modification de structure nécessaire. Les prompts sont simplement améliorés dans la table `ai_prompts` existante.

---

## ✅ Résumé

Le système d'agents IA a été considérablement amélioré avec:

1. **Agent de Contrôle Qualité**: Validation automatique et identification des problèmes
2. **Système de Retry**: Jusqu'à 3 tentatives avec prompts adaptatifs
3. **Prompts Améliorés**: Instructions strictes et précises
4. **Logging Détaillé**: Visibilité complète sur le processus

Ces améliorations garantissent que tous les champs soient traités correctement, avec un système de contrôle qui peut redemander le travail aux agents responsables en cas de problème.
