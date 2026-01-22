# Architecture des Agents IA - Documentation Technique

## Vue d'ensemble

Le système d'agents IA a été restructuré pour donner à chaque agent son propre prompt système et métier, tout en forçant l'utilisation de Gemini pour l'agent Google Shopping.

---

## Agents disponibles

### 1. Agent SEO

**Rôle**: Génère du contenu optimisé SEO pour les produits

**Configuration**:
- **Prompt système**: `seo_system_prompt`
- **Prompt métier**: `seo_prompt`
- **Provider IA**: Tous (OpenAI, Claude, Gemini, Perplexity)
- **Recherche internet**: Optionnelle (selon configuration utilisateur)
- **Champs gérés**: 6 champs
  - SEO Title
  - SEO Description
  - Title (nom du produit)
  - Body (HTML) (description riche)
  - Tags (mots-clés)
  - Image Alt Text

**Contrôle qualité**:
- Validation automatique après génération
- Maximum 2 retries en cas d'échec
- Demande d'explication à l'agent si échec persistant
- Logs des raisons d'échec pour amélioration

---

### 2. Agent Google Shopping

**Rôle**: Catégorise les produits selon la taxonomie Google Shopping

**Configuration**:
- **Prompt système**: `google_shopping_system_prompt`
- **Prompt métier**: `google_category_prompt`
- **Provider IA**: **Gemini UNIQUEMENT** (forcé automatiquement)
- **Recherche internet**: Désactivée (utilise taxonomie locale)
- **Champs gérés**: 1 champ
  - Google Product Category

**Particularités**:
- Accès à la table `google_taxonomy` (base de données locale)
- Injection automatique d'exemples de catégories pertinentes dans le prompt
- Modèle Gemini par défaut: `gemini-2.0-flash-exp`
- Si la clé API Gemini n'est pas configurée, l'agent est désactivé avec un message d'avertissement

---

### 3. Agent Contrôle Qualité

**Rôle**: Valide la qualité des résultats de l'Agent SEO

**Configuration**:
- Utilise le même provider que l'Agent SEO
- Pas de prompt dédié (utilise des règles de validation codées)

**Fonctionnement**:
1. Valide chaque champ généré par l'Agent SEO
2. Vérifie:
   - Champs non vides
   - Longueurs minimales respectées
   - Présence de balises HTML pour body_html
   - Format correct pour tags
3. Si validation échoue:
   - Génère un prompt de retry ciblé
   - Max 2 tentatives
   - Si échec persistant: demande explication à l'agent

---

## Pourquoi Gemini pour Google Shopping?

### Avantages techniques

1. **Meilleure compréhension des catégories**
   - Excellent sur les tâches de classification
   - Bonne performance sur la taxonomie française
   - Capacité à inférer des catégories à partir de descriptions

2. **Pas besoin d'internet**
   - Utilise uniquement la taxonomie locale
   - Plus rapide (pas d'appels API externes)
   - Plus fiable (pas de dépendance Perplexity)

3. **Coût/performance optimal**
   - Gemini est gratuit pour les petits volumes
   - Très rapide pour les tâches de classification
   - Bon rapport qualité/prix

4. **Spécialisation**
   - Chaque agent a son provider optimal
   - SEO: flexibilité (tous providers)
   - Google Shopping: spécialisé (Gemini)

---

## Structure de la base de données

### Table `ai_prompts`

```sql
CREATE TABLE ai_prompts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    
    -- Prompts système séparés
    seo_system_prompt TEXT,
    google_shopping_system_prompt TEXT,
    
    -- Prompts métier
    seo_prompt TEXT NOT NULL,
    google_category_prompt TEXT NOT NULL,
    
    -- Pour rétrocompatibilité
    system_prompt TEXT NOT NULL,
    
    -- Métadonnées
    is_default INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

### Migration automatique

Lors de la première exécution du script `migrate_prompts_schema.py`:
1. Ajout des colonnes `seo_system_prompt` et `google_shopping_system_prompt`
2. Copie du `system_prompt` global vers les deux nouveaux champs
3. Vous pouvez ensuite personnaliser chaque prompt système

---

## Workflow de traitement

### Pour un produit unique (Test)

```
1. Utilisateur sélectionne un produit
2. Système charge l'ensemble de prompts actif
3. Création des providers IA:
   - Provider SEO: selon choix utilisateur (OpenAI/Claude/Gemini)
   - Provider Google Shopping: Gemini forcé
4. Création des agents:
   - Agent SEO (avec son system_prompt)
   - Agent Google Shopping (avec son system_prompt)
5. Génération du contenu:
   - Agent SEO génère les 6 champs
   - Agent Contrôle Qualité valide
   - Si échec: retry avec prompt amélioré (max 2 fois)
   - Si échec persistant: demande explication
6. Agent Google Shopping génère la catégorie
7. Affichage des résultats dans l'interface
```

### Pour un traitement par lot (CSV)

```
1. Utilisateur sélectionne un CSV et des produits
2. Même logique que ci-dessus pour la création des agents
3. Traitement séquentiel de chaque produit
4. Logs en temps réel dans l'interface
5. Génération d'un nouveau CSV avec les champs mis à jour
```

---

## Interface utilisateur

### Section Prompts

L'interface affiche maintenant **4 textboxes** organisées en 2 sections:

#### Section Agent SEO (bleu)
```
━━━ AGENT SEO ━━━

Prompt système SEO:
[Textbox de 80px de hauteur]

Prompt métier SEO (6 champs: SEO Title, SEO Description, Title, Body HTML, Tags, Image Alt Text):
[Textbox de 120px de hauteur]
```

#### Section Agent Google Shopping (orange)
```
━━━ AGENT GOOGLE SHOPPING (Gemini uniquement) ━━━

Prompt système Google Shopping:
[Textbox de 80px de hauteur]

Prompt métier Google Shopping Category:
[Textbox de 80px de hauteur]
```

### Logs d'exécution

Les logs affichent clairement quel provider est utilisé:

```
ℹ️ Provider SEO: openai
ℹ️ Google Shopping: Gemini forcé (SANS recherche)
```

Si Gemini n'est pas configuré:
```
⚠️ Google Shopping désactivé (clé Gemini manquante)
```

---

## Messages d'erreur

### Clé API Gemini manquante

```
⚠️ Agent Google Shopping désactivé: clé API Gemini manquante

Solution: Configurez votre clé API Gemini dans la section IA
```

### Erreur d'initialisation Gemini

```
⚠️ Google Shopping désactivé (erreur Gemini)

Vérifiez:
1. Que votre clé API est valide
2. Que vous avez accès à Gemini
3. Que le quota n'est pas dépassé
```

---

## Personnalisation des prompts

### Prompt système SEO

**Objectif**: Définir le comportement global de l'agent SEO

**Contenu recommandé**:
- Ton et style d'écriture
- Règles de qualité (longueurs, HTML, etc.)
- Instructions sur l'utilisation des données produit
- Format de réponse (JSON strict)

**Exemple**:
```
Tu es un expert en e-commerce et SEO. Tu génères du contenu optimisé pour Shopify.

Règles strictes:
- Toujours répondre en JSON valide
- Ne JAMAIS laisser un champ vide
- Utiliser toutes les données du produit
- Le body_html DOIT contenir du HTML avec balises
```

### Prompt métier SEO

**Objectif**: Instructions spécifiques pour chaque champ

**Contenu recommandé**:
- Description de chaque champ à générer
- Longueurs min/max
- Exemples
- Structure JSON attendue

### Prompt système Google Shopping

**Objectif**: Définir le comportement de l'agent de catégorisation

**Contenu recommandé**:
- Importance de la précision
- Utilisation de la taxonomie fournie
- Format de réponse

**Exemple**:
```
Tu es un expert en catégorisation produits pour Google Shopping.
Tu DOIS choisir une catégorie de la taxonomie fournie.
Réponds UNIQUEMENT avec le chemin complet en français.
```

### Prompt métier Google Shopping

**Objectif**: Instructions pour choisir la bonne catégorie

**Contenu recommandé**:
- Comment analyser le produit
- Comment choisir entre plusieurs catégories
- Exemples de catégorisation

---

## Logs et debugging

### Logs provider

```python
logger.info(f"Provider SEO: {provider_name} ({model_name})")
logger.info("Provider Google Shopping: gemini (gemini-2.0-flash-exp) - FORCÉ")
```

### Logs réponse brute

Les réponses brutes de l'IA sont loggées pour debug:

```
📝 Réponse brute de l'agent SEO pour {handle}:
--- DÉBUT RÉPONSE ---
{...}
--- FIN RÉPONSE ---
```

### Logs validation

```
⚠️ Validation échouée: body_html: Champ vide, tags: Champ vide
🔄 Retry: demande de compléter les champs manquants...
❓ Demande d'explication à l'agent...
```

### Logs explication

Si l'agent échoue après 2 tentatives:

```
🔍 Explication de l'agent pour {handle}:
--- DÉBUT EXPLICATION ---
{
  "raison_principale": "Limite de tokens atteinte",
  "champs_problematiques": ["body_html"],
  "suggestion_amelioration": "Augmenter max_output_tokens à 4000"
}
--- FIN EXPLICATION ---
```

---

## Améliorations futures possibles

- [ ] Logger les explications dans une table SQL pour analyse
- [ ] Graphiques de distribution des raisons d'échec
- [ ] Auto-ajustement des prompts selon les explications
- [ ] Alerte si même raison répétée (ex: quota dépassé X fois)
- [ ] Support d'autres providers pour Google Shopping (si besoin)
- [ ] Optimisation automatique des prompts via A/B testing

---

## Fichiers modifiés

- `apps/ai_editor/db.py`: Gestion des 4 prompts
- `apps/ai_editor/processor.py`: Création de 2 providers distincts
- `apps/ai_editor/gui/window.py`: Interface avec 4 textboxes
- `migrate_prompts_schema.py`: Script de migration DB

---

## Compatibilité

### Anciennes installations

- Le champ `system_prompt` est conservé pour compatibilité
- Lors du premier lancement, exécuter `python migrate_prompts_schema.py`
- Les prompts seront automatiquement dupliqués
- Vous pouvez ensuite personnaliser chaque prompt système

### Fallback

Si `seo_system_prompt` ou `google_shopping_system_prompt` est vide:
- Le système utilise automatiquement `system_prompt` comme fallback
- Garantit le bon fonctionnement même si les nouveaux champs ne sont pas remplis
