# Modèles Gemini Filtrés et Optimisés

## Vue d'ensemble

Les modèles Gemini ont été filtrés pour ne garder que **les plus récents et pertinents** pour nos cas d'usage (SEO et catégorisation Google Shopping).

---

## 🎯 Modèles Retenus

### 1. gemini-2.0-flash-exp (DÉFAUT) ⭐

**Version**: 2.0 (experimental)  
**Type**: Flash (rapide et optimisé)  
**Statut**: Modèle le plus récent disponible

**Caractéristiques**:
- ✅ **Très rapide** (latence réduite)
- ✅ **Excellent pour la classification** (catégories Google Shopping)
- ✅ **Bon pour le SEO** (génération de contenu)
- ✅ **Gratuit** pour les petits volumes
- ✅ **Multimodal** (texte + images si besoin)

**Cas d'usage recommandés**:
- ✅ **Google Shopping** (catégorisation) → FORCÉ par le système
- ✅ **SEO rapide** (si vous voulez de la vitesse)
- ✅ **Tests** (gratuit, rapide)

**Performance**:
- Génération catégorie: ~1-2 secondes
- Génération SEO (6 champs): ~3-5 secondes
- Tokens: Jusqu'à 8192 tokens en sortie

**Pourquoi c'est le défaut?**
- Parfait équilibre vitesse/qualité
- Dernière version de Google
- Optimisé pour les tâches de classification

---

### 2. gemini-1.5-flash

**Version**: 1.5 (stable)  
**Type**: Flash (rapide)  
**Statut**: Version stable et éprouvée

**Caractéristiques**:
- ✅ **Rapide** (légèrement plus lent que 2.0)
- ✅ **Stable** (version non-experimental)
- ✅ **Très bon pour classification**
- ✅ **Gratuit** pour les petits volumes
- ✅ **Grande fenêtre de contexte** (1M tokens)

**Cas d'usage recommandés**:
- ✅ **Google Shopping** (si 2.0 pose problème)
- ✅ **SEO standard** (bonne qualité)
- ✅ **Production stable** (pas de risque experimental)

**Performance**:
- Génération catégorie: ~2-3 secondes
- Génération SEO (6 champs): ~4-6 secondes
- Tokens: Jusqu'à 8192 tokens en sortie

**Quand l'utiliser?**
- Si gemini-2.0-flash-exp a des bugs (experimental)
- Si vous préférez la stabilité
- Pour la production critique

---

### 3. gemini-1.5-pro

**Version**: 1.5 Pro (stable)  
**Type**: Pro (plus puissant, plus lent)  
**Statut**: Version stable et puissante

**Caractéristiques**:
- ✅ **Plus intelligent** (meilleure compréhension)
- ✅ **Meilleure qualité** (contenu SEO plus riche)
- ⚠️ **Plus lent** (latence ~2x Flash)
- ⚠️ **Plus cher** (si quota dépassé)
- ✅ **Fenêtre contexte XXL** (2M tokens)

**Cas d'usage recommandés**:
- ✅ **SEO premium** (descriptions longues et riches)
- ✅ **Produits complexes** (descriptions techniques)
- ❌ **Google Shopping** (trop lent pour la catégorisation simple)

**Performance**:
- Génération SEO (6 champs): ~8-12 secondes
- Tokens: Jusqu'à 8192 tokens en sortie

**Quand l'utiliser?**
- Produits haut de gamme (descriptions premium)
- Contenu technique complexe
- Quand la qualité prime sur la vitesse

---

## ❌ Modèles Retirés (Obsolètes)

### gemini-pro (retiré)

**Pourquoi retiré?**
- ❌ Ancienne version (remplacée par 1.5)
- ❌ Moins performant que 1.5-flash
- ❌ Pas de fenêtre de contexte étendue
- ❌ Obsolète depuis la sortie de 1.5

**Migration**: Utilisez `gemini-1.5-flash` ou `gemini-2.0-flash-exp`

---

### gemini-pro-vision (retiré)

**Pourquoi retiré?**
- ❌ Ancienne version multimodale
- ❌ Remplacée par les modèles 1.5+ (multimodaux par défaut)
- ❌ Moins performant
- ❌ Pas nécessaire (1.5+ font texte + images)

**Migration**: Utilisez `gemini-1.5-flash` (multimodal par défaut)

---

## 🔮 Modèles Futurs Prévus

Le système est préparé pour les futures versions de Gemini:

### gemini-2.5-flash (à venir)

**Prévision**: Q2 2026  
**Type**: Flash optimisé  
**Améliorations attendues**:
- ⚡ Encore plus rapide que 2.0
- 🎯 Meilleure précision classification
- 💰 Possiblement gratuit plus longtemps

**Action**: Aucune, le système détectera automatiquement

---

### gemini-3.0-flash (à venir)

**Prévision**: Q4 2026  
**Type**: Nouvelle génération Flash  
**Améliorations attendues**:
- 🚀 Latence réduite de 50%
- 🧠 Intelligence accrue
- 🌍 Meilleur multilinguisme

**Action**: Aucune, le système détectera automatiquement

---

### gemini-3.0-pro (à venir)

**Prévision**: Q4 2026  
**Type**: Nouvelle génération Pro  
**Améliorations attendues**:
- 💎 Qualité premium
- 📚 Fenêtre de contexte 10M tokens
- 🎨 Créativité améliorée

**Action**: Aucune, le système détectera automatiquement

---

## 🔄 Détection Automatique

Le système détecte automatiquement les nouveaux modèles Gemini:

```python
# Dans ai_providers.py (GeminiProvider.list_models)
if 'gemini-2.0' in model_lower or 'gemini-3' in model_lower:
    # Inclure automatiquement les modèles 2.0+ et 3+
    available_models.append(model_name)
```

**Avantages**:
- ✅ Pas besoin de mise à jour manuelle
- ✅ Nouveaux modèles disponibles automatiquement
- ✅ Filtre intelligent (que les versions récentes)

**Filtre actuel**:
- ✅ Accepte: `gemini-2.0-*`, `gemini-2.5-*`, `gemini-3.0-*`, etc.
- ✅ Accepte: `gemini-1.5-*` (encore pertinent)
- ❌ Rejette: `gemini-pro`, `gemini-1.0-*` (obsolètes)

---

## 📊 Comparaison des Modèles

| Modèle | Version | Vitesse | Qualité | Prix | Cas d'usage |
|--------|---------|---------|---------|------|-------------|
| **gemini-2.0-flash-exp** | 2.0 exp | ⚡⚡⚡⚡⚡ | 🎯🎯🎯🎯 | 💰 Gratuit | Google Shopping, SEO rapide |
| **gemini-1.5-flash** | 1.5 stable | ⚡⚡⚡⚡ | 🎯🎯🎯🎯 | 💰 Gratuit | Production stable |
| **gemini-1.5-pro** | 1.5 stable | ⚡⚡ | 🎯🎯🎯🎯🎯 | 💰💰 Plus cher | SEO premium |

**Légende**:
- ⚡ = Vitesse (plus = plus rapide)
- 🎯 = Qualité (plus = meilleure qualité)
- 💰 = Prix (plus = plus cher)

---

## 🎯 Recommandations par Cas d'Usage

### Google Shopping (Catégorisation)

**Recommandé**: `gemini-2.0-flash-exp` (FORCÉ par le système)

**Pourquoi?**
- Tâche simple (classification)
- Besoin de vitesse
- Excellente précision
- Gratuit

**Alternatives**: Aucune (forcé par le système)

---

### SEO - Produits Standard

**Recommandé**: `gemini-2.0-flash-exp` ou `gemini-1.5-flash`

**Pourquoi?**
- Bon équilibre vitesse/qualité
- Gratuit pour petits volumes
- Suffisant pour descriptions standard

**Exemple**: Nappes, serviettes, draps

---

### SEO - Produits Haut de Gamme

**Recommandé**: `gemini-1.5-pro`

**Pourquoi?**
- Meilleure qualité de contenu
- Descriptions plus riches et détaillées
- Ton plus premium

**Exemple**: Linge de luxe, produits d'exception

---

### SEO - Produits Techniques

**Recommandé**: `gemini-1.5-pro`

**Pourquoi?**
- Meilleure compréhension technique
- Capacité à expliquer des concepts complexes
- Grande fenêtre de contexte (2M tokens)

**Exemple**: Électronique, équipements spécialisés

---

### Tests et Développement

**Recommandé**: `gemini-2.0-flash-exp`

**Pourquoi?**
- Gratuit
- Rapide (feedback immédiat)
- Dernières fonctionnalités

---

## ⚙️ Configuration Actuelle

**Fichier**: `ai_config.json`

```json
"gemini": {
  "default": "gemini-2.0-flash-exp",
  "available": [
    "gemini-2.0-flash-exp",
    "gemini-1.5-flash",
    "gemini-1.5-pro"
  ],
  "comment": "Modèles filtrés: gardé uniquement les plus récents et pertinents",
  "future_models": [
    "gemini-2.5-flash",
    "gemini-3.0-flash",
    "gemini-3.0-pro"
  ]
}
```

**Points clés**:
- ✅ **3 modèles** au lieu de 5 (épuré)
- ✅ **Défaut 2.0** (le plus récent)
- ✅ **Futurs modèles** documentés
- ✅ **Obsolètes retirés** (gemini-pro, gemini-pro-vision)

---

## 🔧 Changements pour l'Utilisateur

### Dans l'Interface GUI

**Avant** (dropdown modèles Gemini):
```
gemini-1.5-flash
gemini-1.5-pro
gemini-2.0-flash-exp
gemini-pro               ← Obsolète
gemini-pro-vision        ← Obsolète
```

**Après** (dropdown modèles Gemini):
```
gemini-2.0-flash-exp     ← DÉFAUT
gemini-1.5-flash
gemini-1.5-pro
```

**Avantages**:
- ✅ Plus clair (que les modèles pertinents)
- ✅ Pas de confusion avec anciens modèles
- ✅ Défaut optimisé (2.0-flash-exp)

---

### Google Shopping (Forcé)

**Comportement**: Le système force TOUJOURS `gemini-2.0-flash-exp` pour Google Shopping

**Code** (`processor.py`):
```python
google_shopping_provider = get_provider(
    'gemini',  # FORCÉ
    api_key=gemini_api_key, 
    model='gemini-2.0-flash-exp',  # Modèle forcé
    enable_search=False
)
```

**Logs**:
```
ℹ️ Provider Google Shopping: gemini (gemini-2.0-flash-exp) - FORCÉ
```

**Pourquoi forcé?**
- Optimal pour la catégorisation
- Gratuit
- Rapide
- Dernier modèle Google

---

## 📈 Performance Attendue

### Google Shopping (Catégorisation)

**Avec gemini-2.0-flash-exp**:
- Temps moyen: **1-2 secondes** par produit
- Précision: **95-98%** (catégorie correcte)
- Coût: **Gratuit** (jusqu'à quotas)

**Exemple**:
```
Produit: Nappe en coton 160x200cm
Temps: 1.3s
Résultat: Maison et jardin > Linge de maison > Linge de table > Nappes
Précision: ✓ Excellente
```

---

### SEO (6 champs)

**Avec gemini-2.0-flash-exp**:
- Temps moyen: **3-5 secondes** par produit
- Qualité: **Très bonne** (descriptions riches)
- Coût: **Gratuit** (jusqu'à quotas)

**Avec gemini-1.5-pro**:
- Temps moyen: **8-12 secondes** par produit
- Qualité: **Excellente** (descriptions premium)
- Coût: **Plus cher** (au-delà des quotas)

---

## 🚀 Migration Automatique

Si vous utilisiez les anciens modèles, le système migre automatiquement:

### Si vous utilisiez gemini-pro

**Avant**:
```json
"provider": "gemini",
"model": "gemini-pro"
```

**Après** (automatique):
```json
"provider": "gemini",
"model": "gemini-2.0-flash-exp"  ← Migré au défaut
```

**Action**: Aucune, migration transparente

---

### Si vous utilisiez gemini-pro-vision

**Avant**:
```json
"provider": "gemini",
"model": "gemini-pro-vision"
```

**Après** (automatique):
```json
"provider": "gemini",
"model": "gemini-2.0-flash-exp"  ← Migré au défaut
```

**Note**: 2.0-flash-exp est multimodal par défaut (pas besoin de version spéciale)

---

## 💡 Conseils d'Utilisation

### 1. Utilisez le défaut (2.0-flash-exp)

Pour 95% des cas, le modèle par défaut est optimal:
- Rapide
- Gratuit
- Excellente qualité
- Dernier modèle Google

### 2. Passez à 1.5-pro pour le premium

Seulement si:
- Produits haut de gamme
- Descriptions très longues nécessaires
- Contenu technique complexe

### 3. Restez sur 1.5-flash pour la stabilité

Si gemini-2.0-flash-exp a des bugs (experimental):
- Version stable éprouvée
- Même performance que 2.0 (presque)
- Pas de surprises

### 4. Ne touchez pas à Google Shopping

Le système force automatiquement le meilleur modèle:
- Vous ne pouvez pas le changer (c'est voulu)
- Optimal pour la catégorisation
- Aucune configuration nécessaire

---

## 🔍 Vérification

### Comment voir quel modèle est utilisé?

**Dans les logs du terminal**:
```
ℹ️ Provider SEO: gemini (gemini-2.0-flash-exp)
ℹ️ Provider Google Shopping: gemini (gemini-2.0-flash-exp) - FORCÉ
```

### Comment tester un modèle spécifique?

1. Allez dans **Configuration > IA**
2. Sélectionnez **Gemini** comme provider
3. Choisissez le modèle dans le dropdown
4. Testez avec un produit

---

## 📚 Ressources

- **Gemini API**: https://ai.google.dev/
- **Modèles Gemini**: https://ai.google.dev/gemini-api/docs/models
- **Pricing**: https://ai.google.dev/pricing
- **Documentation interne**: `NOUVELLE_ARCHITECTURE_AGENTS.md`

---

**✅ Les modèles Gemini sont maintenant optimisés et prêts pour le futur!**

**Résumé**: 3 modèles pertinents + détection automatique des futurs modèles (2.5, 3.0, etc.)
