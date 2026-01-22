# Séparation des Prompts SEO - Technique vs Métier

## Contexte

Les prompts SEO ont été réorganisés pour séparer clairement:
- **Aspects TECHNIQUES** (system prompt) → Règles strictes, format JSON, validation
- **Aspects MÉTIER** (user prompt) → Instructions personnalisables, champs à générer

Cette séparation permet de **protéger** les règles techniques critiques tout en permettant la **personnalisation** des instructions métier.

---

## Structure des Prompts SEO

### 1. System Prompt SEO (TECHNIQUE - PROTÉGÉ)

**Rôle**: Définir les règles techniques absolues et non-négociables

**Contenu**:

#### 1.1 Format de réponse obligatoire
```json
{
  "seo_title": "...",
  "seo_description": "...",
  "title": "...",
  "body_html": "<p>...</p>",
  "tags": "tag1, tag2, tag3",
  "image_alt_text": "..."
}
```

**Règles**:
- ❌ PAS de texte avant/après le JSON
- ❌ PAS de backticks markdown (```json)
- ❌ PAS d'explication ou commentaire
- ✅ UNIQUEMENT le JSON pur

#### 1.2 Règle absolue: Aucun champ vide
- Tous les 6 champs DOIVENT être remplis
- Un champ vide = échec grave
- Validation automatique avec longueurs minimales

#### 1.3 Qualité technique du HTML
- Balises autorisées: `<p>`, `<strong>`, `<em>`, `<ul>`, `<li>`, `<br>`, `<h3>`
- Balises interdites: `<script>`, `<style>`, `<iframe>`
- HTML valide et bien structuré

#### 1.4 Format des tags
- Séparés par ", " (virgule + espace)
- Minuscules (sauf marques)
- Sans caractères spéciaux (#, @, etc.)

#### 1.5 Longueurs techniques strictes

| Champ | Minimum | Optimal | Maximum |
|-------|---------|---------|---------|
| seo_title | 30 | 50-70 | 70 |
| seo_description | 100 | 150-320 | 320 |
| title | 10 | 20-50 | 255 |
| body_html | 200 | 500-1000 | - |
| tags | 3 tags | 5-10 tags | 250 chars total |
| image_alt_text | 10 | 50-125 | 125 |

#### 1.6 Utilisation de la recherche internet
- Si Perplexity disponible → UTILISER pour enrichir
- Sinon → Connaissances générales + créativité

#### 1.7 Gestion des erreurs et retry
- Max 2 tentatives pour corriger
- À la 3ème tentative → expliquer pourquoi

**Pourquoi protéger?**
- Évite les erreurs de format (JSON cassé)
- Garantit la qualité technique
- Assure la compatibilité avec le système
- Empêche les modifications accidentelles

---

### 2. User Prompt SEO (MÉTIER - PERSONNALISABLE)

**Rôle**: Décrire les 6 champs à générer avec exemples et style

**Contenu**:

#### 2.1 Description de chaque champ

**seo_title** (50-70 caractères):
- Titre optimisé pour Google
- Inclure: nom produit + mots-clés
- Style: Accrocheur et professionnel
- Exemple: "Nappe en Coton Bio 160x200cm - Motif Basque Artiga"

**seo_description** (150-320 caractères):
- Description pour Google
- Inclure: bénéfices, caractéristiques, CTA
- Style: Persuasif et informatif
- Exemple: "Découvrez notre nappe en coton bio 160x200cm avec motif basque traditionnel. Qualité Artiga, tissage résistant, facile d'entretien..."

**title**:
- Nom du produit pour Shopify
- Format: [Produit] - [Caractéristique] - [Marque]
- Exemple: "Nappe en Coton Bio 160x200cm - Motif Basque - Artiga"

**body_html** (minimum 200 caractères):
- Description HTML riche
- Structure: intro + caractéristiques (liste) + utilisation/entretien
- Ton: Professionnel, informatif, vendeur
- Exemple de structure fournie

**tags** (5-10 tags):
- Tags SEO Shopify
- Inclure: catégorie, matériaux, marque, couleurs, style
- Exemple: "nappe, linge de table, coton bio, 160x200, artiga, basque, motif traditionnel"

**image_alt_text**:
- Description image pour accessibilité
- Format: [Produit] - [Caractéristique visuelle]
- Exemple: "Nappe en coton bio avec motif basque rouge et blanc"

#### 2.2 Espace personnalisation

```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
✏️ INSTRUCTIONS PERSONNALISABLES
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

[ESPACE POUR VOS INSTRUCTIONS PERSONNALISÉES]

Exemples d'instructions personnalisables:
- Ton spécifique (ex: "Utilise un ton chaleureux et familier")
- Vocabulaire à privilégier (ex: "Utilise 'artisanal' plutôt que 'fait main'")
- Éléments à mettre en avant (ex: "Insiste sur l'aspect écologique")
- Mots-clés spécifiques à inclure (ex: "Toujours mentionner 'made in France'")
- Style de la marque (ex: "Style luxe et raffiné")
```

**Pourquoi personnalisable?**
- Adapter le ton à la marque
- Ajouter des instructions spécifiques
- Tester différentes approches
- Flexibilité métier

---

## Interface Utilisateur

### System Prompt SEO - PROTÉGÉ 🔒

**État par défaut**: VERROUILLÉ (grisé, non éditable)

**Apparence**:
```
┌─────────────────────────────────────────────────────────┐
│ Prompt système SEO (RÈGLES TECHNIQUES) 🔒  [✏️ Modifier]│
├─────────────────────────────────────────────────────────┤
│ Tu es un expert en optimisation...                     │
│ (texte grisé, non éditable)                            │
│ ...                                                     │
└─────────────────────────────────────────────────────────┘
```

**Bouton "✏️ Modifier"**:
- Déverrouille le textbox
- Change la couleur du texte (blanc)
- Affiche le bouton "💾 Sauvegarder"
- Cache le bouton "Modifier"
- Status: "🔓 Prompt système SEO déverrouillé"

**Bouton "💾 Sauvegarder"**:
- Sauvegarde les modifications dans la base
- Reverrouille le textbox
- Grise le texte (#888888)
- Affiche le bouton "Modifier"
- Cache le bouton "Sauvegarder"
- Status: "🔒 Prompt système SEO verrouillé et sauvegardé"

**Couleurs**:
- Label: Orange (#FFA500) pour indiquer "PROTÉGÉ"
- Bouton Modifier: Orange (#FFA500)
- Bouton Sauvegarder: Vert (#28a745)

---

### User Prompt SEO - ÉDITABLE ✏️

**État par défaut**: DÉVERROUILLÉ (toujours éditable)

**Apparence**:
```
┌─────────────────────────────────────────────────────────┐
│ Prompt métier SEO (6 champs...)                        │
├─────────────────────────────────────────────────────────┤
│ 🎯 MISSION: Générer les 6 champs...                   │
│ (texte blanc, éditable)                                │
│ ...                                                     │
│ [ESPACE POUR VOS INSTRUCTIONS PERSONNALISÉES]          │
└─────────────────────────────────────────────────────────┘
```

**Pas de boutons spéciaux**:
- Toujours éditable
- Modifiable à volonté
- Sauvegardé avec le bouton "💾 Sauvegarder l'ensemble"

---

## Workflow d'Utilisation

### 1. Chargement initial

```
Application démarre
   ↓
Charge l'ensemble de prompts par défaut
   ↓
System prompt SEO: VERROUILLÉ 🔒
User prompt SEO: Éditable ✏️
```

### 2. Modification du user prompt (normal)

```
Utilisateur modifie le user prompt
   ↓
Ajoute instructions personnalisées
   ↓
Clique "💾 Sauvegarder l'ensemble"
   ↓
✓ User prompt sauvegardé
   ↓
Peut tester avec un produit
```

### 3. Modification du system prompt (rare)

```
Utilisateur clique "✏️ Modifier"
   ↓
System prompt DÉVERROUILLÉ 🔓
   ↓
Modifie les règles techniques
   ↓
Clique "💾 Sauvegarder"
   ↓
System prompt sauvegardé
   ↓
System prompt REVERROUILLÉ 🔒
```

---

## Exemples de Personnalisation

### Exemple 1: Ton chaleureux et familier

**Dans le user prompt**, ajoutez:
```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
✏️ MES INSTRUCTIONS PERSONNALISÉES
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

TON: Chaleureux et familier
- Tutoyer le client ("tu" au lieu de "vous")
- Utiliser des expressions conviviales ("Craquez pour...", "Offrez-vous...")
- Style décontracté mais professionnel

VOCABULAIRE:
- "artisanal" plutôt que "fait main"
- "authentique" pour les produits traditionnels
- "doux" et "confortable" pour les textiles
```

### Exemple 2: Focus écologique

**Dans le user prompt**, ajoutez:
```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
✏️ MES INSTRUCTIONS PERSONNALISÉES
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

FOCUS: Aspect écologique et durable

ÉLÉMENTS À METTRE EN AVANT:
- Matériaux bio et naturels (coton bio, lin, etc.)
- Fabrication écoresponsable
- Durabilité et longévité du produit
- Certifications (Oeko-Tex, GOTS, etc.)

MOTS-CLÉS À INCLURE:
- "bio", "écologique", "durable", "naturel"
- "made in France" si applicable
- "écoresponsable", "respectueux de l'environnement"

TAGS:
- Toujours inclure "bio", "écologique", "durable" si pertinent
```

### Exemple 3: Style luxe

**Dans le user prompt**, ajoutez:
```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
✏️ MES INSTRUCTIONS PERSONNALISÉES
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

STYLE: Luxe et raffiné

TON:
- Vouvoiement ("vous")
- Vocabulaire élégant et sophistiqué
- Éviter les expressions familières

VOCABULAIRE PRIVILÉGIÉ:
- "exceptionnel", "raffiné", "élégant", "prestigieux"
- "savoir-faire", "excellence", "noble"
- "confection", "finitions soignées"

STRUCTURE BODY_HTML:
- Commencer par l'héritage et le savoir-faire
- Mettre en avant la qualité premium
- Terminer par l'invitation à découvrir
```

---

## Avantages de cette Séparation

### ✅ Pour l'utilisateur

1. **Sécurité**: Les règles techniques ne peuvent pas être cassées par erreur
2. **Flexibilité**: Personnalisation facile des instructions métier
3. **Clarté**: Séparation visible entre technique et métier
4. **Simplicité**: Focus sur ce qui compte (le métier)

### ✅ Pour le système

1. **Fiabilité**: Format JSON garanti
2. **Validation**: Règles de qualité protégées
3. **Maintenance**: Règles techniques centralisées
4. **Évolution**: Peut améliorer les règles techniques sans casser les prompts utilisateur

### ✅ Pour l'équipe

1. **Rôles clairs**:
   - Admin système: Gère les règles techniques
   - Utilisateur métier: Personnalise les instructions
2. **Collaboration**: Chacun son domaine
3. **Formation**: Plus facile à expliquer

---

## Cas d'Usage

### CAS 1: Utilisateur normal

**Objectif**: Personnaliser les descriptions pour sa marque

**Action**:
1. Ouvre l'onglet Prompts
2. Modifie le **user prompt SEO** (toujours éditable)
3. Ajoute ses instructions dans l'espace personnalisé
4. Clique "💾 Sauvegarder l'ensemble"
5. Teste avec un produit

**System prompt**: Reste verrouillé, aucune action nécessaire

---

### CAS 2: Admin système

**Objectif**: Améliorer les règles techniques (ex: ajouter une validation)

**Action**:
1. Ouvre l'onglet Prompts
2. Clique "✏️ Modifier" sur le system prompt SEO
3. Modifie les règles techniques
4. Clique "💾 Sauvegarder"
5. System prompt reverrouillé

**Impact**: Tous les utilisateurs bénéficient de l'amélioration

---

### CAS 3: Débogage

**Objectif**: Comprendre pourquoi l'agent échoue

**Action**:
1. Vérifie les logs du terminal
2. Si erreur de format JSON → Problème dans system prompt (rare)
3. Si contenu inadapté → Problème dans user prompt (normal)
4. Ajuste le prompt concerné

---

## Troubleshooting

### Le system prompt est grisé, je ne peux pas le modifier

**C'est normal!** C'est le comportement attendu.

**Solution**: Cliquez sur "✏️ Modifier" pour le déverrouiller.

---

### J'ai modifié le system prompt mais je ne vois pas le bouton Sauvegarder

**Cause**: Le bouton Sauvegarder n'apparaît que si vous avez cliqué sur "Modifier".

**Solution**: 
1. Assurez-vous d'avoir cliqué sur "✏️ Modifier"
2. Le bouton "💾 Sauvegarder" devrait apparaître à droite

---

### Le system prompt ne se verrouille pas après sauvegarde

**Cause**: Erreur lors de la sauvegarde ou bug d'affichage.

**Solution**:
1. Rechargez l'application (Ctrl+C, puis ./run_gui.sh)
2. Vérifiez que les modifications ont été sauvegardées
3. Le system prompt devrait être verrouillé au redémarrage

---

### Je veux revenir aux prompts par défaut

**Solution**: Exécutez à nouveau le script de mise à jour:
```bash
python update_seo_prompts_separation.py
```

---

## Fichiers Modifiés

- `update_seo_prompts_separation.py`: Script de mise à jour
- `apps/ai_editor/gui/window.py`: Interface avec système de verrouillage
- `database/ai_prompts.db`: Nouveaux prompts sauvegardés
- `SEPARATION_PROMPTS_SEO.md`: Cette documentation

---

## Comparaison Avant/Après

### AVANT (Prompts mélangés)

```
┌─────────────────────────────────────────────────┐
│ Prompt système (global)                        │
├─────────────────────────────────────────────────┤
│ Mélange de:                                     │
│ - Règles techniques (format JSON)              │
│ - Instructions métier (6 champs)               │
│ - Exemples                                      │
│ - Tout éditable sans protection                │
└─────────────────────────────────────────────────┘
│ Prompt SEO (6 champs)                          │
├─────────────────────────────────────────────────┤
│ - Description des champs                        │
│ - Plus d'exemples                               │
│ - Toujours éditable                             │
└─────────────────────────────────────────────────┘

Problèmes:
❌ Règles techniques modifiables par erreur
❌ Séparation floue technique/métier
❌ Risque de casser le format JSON
❌ Difficile de savoir quoi modifier
```

### APRÈS (Prompts séparés)

```
┌─────────────────────────────────────────────────┐
│ System Prompt SEO (RÈGLES TECHNIQUES) 🔒       │
│                              [✏️ Modifier]      │
├─────────────────────────────────────────────────┤
│ - Format JSON obligatoire                       │
│ - Aucun champ vide                              │
│ - Qualité HTML                                  │
│ - Longueurs strictes                            │
│ - Gestion erreurs                               │
│ GRISÉ - PROTÉGÉ - VERROUILLÉ                   │
└─────────────────────────────────────────────────┘
│ User Prompt SEO (MÉTIER) ✏️                    │
├─────────────────────────────────────────────────┤
│ - Description 6 champs                          │
│ - Exemples                                      │
│ - [ESPACE PERSONNALISATION]                     │
│ BLANC - ÉDITABLE - PERSONNALISABLE             │
└─────────────────────────────────────────────────┘

Avantages:
✅ Règles techniques protégées
✅ Séparation claire technique/métier
✅ Format JSON garanti
✅ Facile de personnaliser le métier
✅ Rôles utilisateur bien définis
```

---

## Prochaines Étapes

1. **Testez** la nouvelle interface après redémarrage
2. **Personnalisez** le user prompt selon vos besoins
3. **Documentez** vos personnalisations pour votre équipe
4. **Partagez** vos meilleures instructions métier

---

**✅ La séparation des prompts SEO est maintenant opérationnelle!**

**System prompt**: Protégé 🔒 (règles techniques)  
**User prompt**: Personnalisable ✏️ (instructions métier)
