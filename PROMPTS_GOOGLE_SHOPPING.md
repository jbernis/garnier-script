# Prompts Google Shopping - Documentation

## Vue d'ensemble

Ces prompts sont spécifiquement optimisés pour l'agent Google Shopping qui utilise Gemini. Ils se concentrent sur **UNE SEULE TÂCHE**: choisir la catégorie Google Shopping la plus appropriée pour un produit.

---

## Prompt Système Google Shopping

### Objectif
Définir le rôle et le comportement global de l'agent de catégorisation.

### Contenu

```
Tu es un expert en catégorisation de produits pour Google Shopping.

Ta mission est de choisir LA MEILLEURE catégorie de la taxonomie Google Shopping pour chaque produit.

RÈGLES STRICTES:
1. Tu DOIS choisir une catégorie qui existe dans la taxonomie fournie
2. Tu DOIS répondre avec le chemin complet en français
3. Si plusieurs catégories semblent appropriées, choisis la PLUS SPÉCIFIQUE
4. Si aucune catégorie n'est parfaite, choisis la PLUS PROCHE
5. Tu dois TOUJOURS donner UNE réponse (pas de "je ne sais pas")

CONTEXTE:
- Les catégories sont organisées hiérarchiquement (parent > enfant > petit-enfant)
- Plus la catégorie est spécifique, meilleure est la catégorisation
- Google Shopping utilise ces catégories pour mieux référencer les produits

FORMAT DE RÉPONSE:
- Réponds UNIQUEMENT avec le chemin complet de la catégorie
- PAS d'explication, PAS de justification
- JUSTE la catégorie

QUALITÉ:
- Lis attentivement le titre, la description et les métadonnées du produit
- Utilise le contexte (marque, matériaux, usage) pour affiner ton choix
- Pense comme un client qui cherche ce produit sur Google Shopping
```

### Points clés

1. **Rôle clairement défini**: Expert en catégorisation
2. **Règles strictes**: Force à choisir une catégorie existante
3. **Pas d'hésitation**: Doit toujours donner une réponse
4. **Format simple**: Juste la catégorie, pas d'explication
5. **Contextualisation**: Pense comme un utilisateur Google Shopping

---

## Prompt Métier Google Shopping

### Objectif
Instructions précises pour analyser le produit et choisir la bonne catégorie.

### Structure

#### 1. Données du produit
```
DONNÉES DU PRODUIT:
- Handle: {handle}
- Titre: {title}
- Description: {body_html}
- Type: {product_type}
- Vendor: {vendor}
- Tags: {tags}
```

**Pourquoi?** Donne tous les contextes nécessaires à Gemini pour comprendre le produit.

#### 2. Catégories pertinentes
```
CATÉGORIES PERTINENTES DISPONIBLES:
{relevant_categories}
```

**Pourquoi?** L'agent GoogleShoppingAgent injecte automatiquement les catégories les plus pertinentes de la taxonomie locale.

#### 3. Instructions étape par étape
```
INSTRUCTIONS:
1. Lis attentivement toutes les informations du produit
2. Identifie le type de produit principal
3. Identifie les caractéristiques importantes
4. Compare avec les catégories disponibles
5. Choisis la catégorie LA PLUS SPÉCIFIQUE
```

**Pourquoi?** Guide Gemini dans son processus de réflexion.

#### 4. Exemples concrets
```
EXEMPLES DE CATÉGORISATION:

Produit: "Nappe en coton 160x200cm"
→ "Maison et jardin > Linge de maison > Linge de table > Nappes"

Produit: "Serviette de table en lin brodée"
→ "Maison et jardin > Linge de maison > Linge de table > Serviettes de table"

...
```

**Pourquoi?** Gemini apprend par l'exemple. Ces exemples montrent le niveau de spécificité attendu.

#### 5. Attention aux pièges
```
ATTENTION:
- Ne choisis PAS une catégorie trop générique
- Ne choisis PAS une catégorie qui ne correspond pas au produit
- Si le produit a plusieurs usages, choisis l'usage PRINCIPAL
```

**Pourquoi?** Évite les erreurs courantes.

#### 6. Format de réponse
```
RÉPONSE ATTENDUE:
Réponds UNIQUEMENT avec le chemin complet de la catégorie en français, 
sans guillemets, sans explication.
```

**Pourquoi?** Facilite le parsing de la réponse par le système.

---

## Exemples de catégorisation

### Linge de table

| Produit | Catégorie |
|---------|-----------|
| Nappe en coton 160x200cm | Maison et jardin > Linge de maison > Linge de table > Nappes |
| Serviette de table en lin brodée | Maison et jardin > Linge de maison > Linge de table > Serviettes de table |
| Set de table en bambou | Maison et jardin > Linge de maison > Linge de table > Sets de table |
| Chemin de table en jute | Maison et jardin > Linge de maison > Linge de table > Chemins de table |

### Linge de lit

| Produit | Catégorie |
|---------|-----------|
| Drap housse en percale de coton 90x190cm | Maison et jardin > Linge de maison > Linge de lit > Draps housses |
| Housse de couette 240x220cm en lin lavé | Maison et jardin > Linge de maison > Linge de lit > Housses de couette |
| Taie d'oreiller en satin | Maison et jardin > Linge de maison > Linge de lit > Taies d'oreiller |
| Parure de lit complète 2 personnes | Maison et jardin > Linge de maison > Linge de lit > Parures de lit |

### Linge de cuisine

| Produit | Catégorie |
|---------|-----------|
| Torchon de cuisine en coton bio | Maison et jardin > Linge de maison > Linge de cuisine > Torchons |
| Tablier de cuisine en lin | Maison et jardin > Linge de maison > Linge de cuisine > Tabliers |
| Manique en silicone | Maison et jardin > Linge de maison > Linge de cuisine > Maniques |

---

## Optimisations pour Gemini

### 1. Format conversationnel
Les prompts utilisent un ton direct et conversationnel ("Tu es...", "Tu dois...") qui fonctionne bien avec Gemini.

### 2. Exemples concrets
Gemini excelle avec le "few-shot learning". Les 5 exemples fournis aident à calibrer ses réponses.

### 3. Instructions claires et structurées
Les listes numérotées et les sections bien définies aident Gemini à suivre un processus logique.

### 4. Contraintes explicites
Les règles strictes ("DOIT choisir", "TOUJOURS donner une réponse") réduisent les hésitations.

### 5. Pas de JSON
Contrairement au prompt SEO, Google Shopping répond en texte simple (juste la catégorie), ce qui est plus naturel pour Gemini.

---

## Utilisation dans le système

### 1. Injection automatique de contexte

L'agent `GoogleShoppingAgent` enrichit automatiquement le prompt avec:
- Les données réelles du produit (titre, description, etc.)
- Les catégories pertinentes de la taxonomie locale
- Le contexte de la marque et du type de produit

### 2. Pas de recherche internet

L'agent Google Shopping:
- N'utilise PAS Perplexity
- N'a PAS accès à internet
- Utilise UNIQUEMENT la taxonomie locale (table `google_taxonomy`)

**Pourquoi?** 
- Plus rapide
- Plus fiable
- Pas de coût supplémentaire
- La taxonomie locale est suffisante

### 3. Provider forcé à Gemini

Le système force automatiquement l'utilisation de Gemini pour cet agent:
```python
google_shopping_provider = get_provider(
    'gemini',  # FORCÉ
    api_key=gemini_api_key, 
    model='gemini-2.0-flash-exp',
    enable_search=False
)
```

**Pourquoi Gemini?**
- Excellent pour la classification
- Gratuit pour petits volumes
- Très rapide
- Bonne compréhension du français

---

## Personnalisation

Vous pouvez personnaliser ces prompts dans l'interface:

### Section Google Shopping (orange)

1. **Prompt système**: Modifier le rôle et les règles générales
2. **Prompt métier**: Ajouter vos propres exemples ou instructions

### Suggestions de personnalisation

#### Pour des produits alimentaires
Ajoutez des exemples:
```
Produit: "Confiture de fraises bio 250g"
→ "Aliments, boissons et tabac > Aliments > Condiments et sauces > Confitures et gelées"
```

#### Pour des vêtements
Ajoutez des exemples:
```
Produit: "Robe d'été en coton pour femme"
→ "Vêtements et accessoires > Vêtements > Robes"
```

#### Pour modifier le ton
Changez "Tu es..." par "Vous êtes..." si vous préférez le vouvoiement.

#### Pour plus de rigueur
Ajoutez une règle:
```
6. Si tu hésites entre 2 catégories, choisis celle qui génère le plus de ventes sur Google Shopping
```

---

## Tests et validation

### Comment tester

1. Redémarrez l'application: `Ctrl+C` puis `./run_gui.sh`
2. Allez dans l'onglet **Prompts**
3. Vérifiez que les prompts Google Shopping sont bien chargés
4. Allez dans l'onglet **Test**
5. Sélectionnez un produit
6. Cochez **Google Product Category**
7. Cliquez sur **"Tester avec cet article"**

### Vérifications dans les logs

```
ℹ️ Provider Google Shopping: gemini (gemini-2.0-flash-exp) - FORCÉ
ℹ️ Google Shopping: Gemini forcé (SANS recherche)
✓ Catégorie Google Shopping générée: Maison et jardin > Linge de maison > Linge de table > Nappes
```

### Qualité attendue

Une bonne catégorisation doit être:
- ✅ **Spécifique**: Pas "Maison et jardin" seul, mais le chemin complet
- ✅ **Cohérente**: Toujours la même catégorie pour des produits similaires
- ✅ **Pertinente**: Correspond vraiment au produit
- ✅ **En français**: Suit la taxonomie française

---

## Troubleshooting

### La catégorie est trop générique

**Problème**: "Maison et jardin" au lieu de "Maison et jardin > Linge de maison > Linge de table > Nappes"

**Solution**: Renforcez la règle dans le prompt système:
```
3. Si plusieurs catégories semblent appropriées, choisis la PLUS SPÉCIFIQUE (minimum 3 niveaux)
```

### La catégorie n'existe pas dans la taxonomie

**Problème**: Gemini invente une catégorie

**Solution**: Ajoutez dans le prompt système:
```
IMPORTANT: Tu ne peux PAS inventer de catégorie. Tu DOIS choisir parmi celles fournies.
```

### La catégorie est en anglais

**Problème**: "Home & Garden" au lieu de "Maison et jardin"

**Solution**: Vérifiez que votre table `google_taxonomy` est en français. Si besoin, réimportez-la.

### Pas de réponse ou erreur

**Problème**: L'agent ne répond pas

**Vérifications**:
1. Clé API Gemini configurée?
2. Quota Gemini pas dépassé?
3. Logs dans le terminal: quel message d'erreur?

---

## Comparaison avec le prompt SEO

| Aspect | Prompt SEO | Prompt Google Shopping |
|--------|-----------|------------------------|
| **Nombre de champs** | 6 champs | 1 champ |
| **Format de réponse** | JSON structuré | Texte simple |
| **Provider** | Tous (choix utilisateur) | Gemini forcé |
| **Recherche internet** | Optionnelle | Désactivée |
| **Complexité** | Haute (contenu créatif) | Basse (classification) |
| **Longueur** | Longue (descriptions HTML) | Courte (chemin de catégorie) |
| **Contrôle qualité** | Oui (retry + explication) | Non (simple validation) |

---

## Fichiers modifiés

- `update_google_shopping_prompts.py`: Script de mise à jour (ce fichier)
- `database/ai_prompts.db`: Base de données avec les nouveaux prompts
- `PROMPTS_GOOGLE_SHOPPING.md`: Cette documentation

---

## Ressources

- **Taxonomie Google Shopping**: https://support.google.com/merchants/answer/6324436
- **Documentation Gemini**: https://ai.google.dev/docs
- **Architecture complète**: `NOUVELLE_ARCHITECTURE_AGENTS.md`

---

**✅ Les prompts sont maintenant optimisés pour la catégorisation avec Gemini!**
