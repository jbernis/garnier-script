# Système de Debug Intelligent pour l'Agent IA

## Vue d'ensemble

Le système a été modifié pour passer d'un **retry automatique silencieux** à un **système de debugging intelligent** qui demande à l'agent d'expliquer pourquoi il ne peut pas compléter certains champs.

---

## ✅ Modifications effectuées

### 1. Réduction des tentatives

**Avant:**
```python
max_retries = 3  # 3 tentatives automatiques
```

**Après:**
```python
max_retries = 2  # 1 génération + 1 retry si nécessaire
```

---

### 2. Message de retry plus clair

**Avant:**
```python
log_callback(f"  🔄 Tentative {attempt}/{max_retries}...")
```

**Après:**
```python
log_callback(f"  🔄 Retry: demande de compléter les champs manquants...")
```

---

### 3. Système d'explication intelligent

**Nouveau:** Si la validation échoue après le retry, le système demande à l'agent **POURQUOI** il ne peut pas compléter:

```python
# Si c'est la dernière tentative, demander POURQUOI
if attempt == max_retries:
    if log_callback:
        log_callback(f"  ❓ Demande d'explication à l'agent...")
    
    # Construire le prompt d'explication
    explain_prompt = f"""Tu viens de générer du contenu SEO pour ce produit, mais certains champs sont incomplets ou invalides.

Problèmes détectés:
{chr(10).join([f"- {field}: {issue}" for field, issue in validation_result['issues'].items()])}

EXPLIQUE-MOI POURQUOI tu n'as pas pu compléter correctement ces champs:
- Manque d'information dans les données du produit?
- Limite de tokens atteinte?
- Consignes du prompt pas claires?
- Autre raison technique?

Réponds en JSON avec cette structure exacte:
{{
  "raison_principale": "description de la raison principale",
  "champs_problematiques": ["liste", "des", "champs"],
  "suggestion_amelioration": "comment améliorer le prompt ou les données"
}}"""
    
    try:
        explanation = agents['seo'].ai_provider.generate(explain_prompt, context=product_data)
        logger.warning(f"🔍 Explication de l'agent pour {handle}:")
        logger.warning(f"--- DÉBUT EXPLICATION ---")
        logger.warning(explanation)
        logger.warning(f"--- FIN EXPLICATION ---")
        
        if log_callback:
            log_callback(f"  📝 Explication loggée (voir terminal)")
    except Exception as e:
        logger.error(f"Impossible d'obtenir l'explication de l'agent: {e}")
```

---

## 🎯 Fonctionnement

### Étape 1: Génération normale
```
[INFO] Génération SEO pour le produit 3661842470436...
[INFO] 📝 Réponse brute de l'agent SEO pour 3661842470436:
[INFO] --- DÉBUT RÉPONSE ---
[INFO] { "seo_title": "...", ... }
[INFO] --- FIN RÉPONSE ---
```

### Étape 2: Validation

#### ✅ Si validation réussit:
```
[INFO] ✓ Tous les champs sont valides
[INFO] Réponse IA (SEO) pour 3661842470436: {...}
```

#### ❌ Si validation échoue:
```
[WARNING] Validation échouée pour 3661842470436 (tentative 1): {'body_html': 'Champ vide', 'tags': 'Champ vide'}
[INFO] 🔄 Retry: demande de compléter les champs manquants...
```

### Étape 3: Retry (si nécessaire)

Le système génère un **prompt de retry** qui indique à l'agent quels champs sont manquants:

```
[INFO] 📝 Réponse brute du retry (tentative 2) pour 3661842470436:
[INFO] --- DÉBUT RÉPONSE ---
[INFO] { "seo_title": "...", "body_html": "...", "tags": "..." }
[INFO] --- FIN RÉPONSE ---
```

### Étape 4: Si échec persiste

#### Demande d'explication:
```
[INFO] ❓ Demande d'explication à l'agent...
[WARNING] 🔍 Explication de l'agent pour 3661842470436:
[WARNING] --- DÉBUT EXPLICATION ---
[WARNING] {
  "raison_principale": "Limite de tokens atteinte lors de la génération du body_html",
  "champs_problematiques": ["body_html"],
  "suggestion_amelioration": "Augmenter max_output_tokens à 4000 ou réduire le prompt système"
}
[WARNING] --- FIN EXPLICATION ---
[INFO] 📝 Explication loggée (voir terminal)
```

---

## 📊 Avantages

### 1. **Moins de retries inutiles**
- ✅ 2 tentatives max au lieu de 3
- ✅ Pas de retry silencieux et coûteux

### 2. **Debugging transparent**
- ✅ L'agent explique **pourquoi** il échoue
- ✅ Identification des vrais problèmes (quota, tokens, données, prompt)

### 3. **Amélioration continue**
- ✅ L'agent suggère des améliorations
- ✅ Permet d'optimiser les prompts
- ✅ Permet d'identifier les produits problématiques

### 4. **Logs clairs**
- ✅ Réponse brute visible dans le terminal
- ✅ Explication visible dans le terminal
- ✅ Messages clairs dans l'interface

---

## 🔍 Exemple de log complet

```
13:45:00 [INFO] Génération SEO pour le produit 3661842470436...
13:45:00 [INFO] 📝 Réponse brute de l'agent SEO pour 3661842470436:
13:45:00 [INFO] --- DÉBUT RÉPONSE ---
13:45:00 [INFO] ```json
{
  "seo_title": "Nappe Coton Bio...",
  "seo_description": "Sublimez votre table...",
  "title": "Nappe ARTIGA...",
  "body_html": "",
  "tags": "",
  "image_alt_text": "Nappe ARTIGA..."
}
```
13:45:00 [INFO] --- FIN RÉPONSE ---
13:45:00 [WARNING] Champ vide: body_html
13:45:00 [WARNING] Champ vide: tags
13:45:00 [WARNING] Validation échouée pour 3661842470436 (tentative 1): {'body_html': 'Champ vide', 'tags': 'Champ vide'}
13:45:01 [INFO] 🔄 Retry: demande de compléter les champs manquants...
13:45:12 [INFO] 📝 Réponse brute du retry (tentative 2) pour 3661842470436:
13:45:12 [INFO] --- DÉBUT RÉPONSE ---
13:45:12 [INFO] {
  "seo_title": "Nappe Coton Bio...",
  "body_html": "<p>Description complète...</p>",
  "tags": "nappe, coton, bio..."
}
13:45:12 [INFO] --- FIN RÉPONSE ---
13:45:12 [INFO] ✓ Validation réussie après retry
13:45:12 [INFO] Réponse IA (SEO) pour 3661842470436: {...}
```

---

## 📁 Fichiers modifiés

- **`apps/ai_editor/processor.py`**:
  - Lignes 181-310 (`process_single_product`)
  - Lignes 635-750 (`process_csv`)
  - Réduction de `max_retries` à 2
  - Ajout du système d'explication
  - Messages de log plus clairs

---

## 🔄 Pour tester

1. **Redémarrez l'application**
2. **Testez avec un produit**
3. **Regardez le terminal** pour voir:
   - La réponse brute
   - Les validations
   - Les retries (si nécessaire)
   - Les explications (si échec)

---

## 💡 Améliorations futures possibles

- [ ] **Logger les explications dans une table SQL** pour analyse
- [ ] **Graphiques de distribution des raisons d'échec**
- [ ] **Auto-ajustement des prompts** selon les explications
- [ ] **Alerte si même raison répétée** (ex: quota dépassé X fois)
