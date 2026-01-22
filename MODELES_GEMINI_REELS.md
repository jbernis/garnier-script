# Modèles Gemini Réels - Janvier 2026

## ✅ Modèles de Génération de Texte (À GARDER)

### Gemini 2.5 (Stable - Juin 2025)
- **gemini-2.5-flash** ⭐ (RECOMMANDÉ - DÉFAUT)
  - Version stable de juin 2025
  - 1M tokens input, 65K tokens output
  - Rapide et multimodal
  - Thinking mode disponible

- **gemini-2.5-pro**
  - Version stable de juin 2025
  - 1M tokens input, 65K tokens output
  - Plus puissant que Flash
  - Thinking mode disponible

### Gemini 2.0 (Stable - Janvier 2025)
- **gemini-2.0-flash**
  - Version stable de janvier 2025
  - 1M tokens input, 8K tokens output
  - Alternative si 2.5 pose problème

- **gemini-2.0-flash-exp**
  - Version expérimentale
  - Mêmes specs que 2.0-flash
  - Pour tester les nouvelles features

---

## ❌ Modèles À RETIRER (Non pertinents)

### Embedding (Vectorisation)
- embedding-gecko-001
- embedding-001
- text-embedding-004
- gemini-embedding-*

**Raison**: Nous n'avons pas besoin de vectorisation

### Images
- imagen-4.0-*
- nano-banana-*

**Raison**: Génération d'images, pas de texte

### Vidéos
- veo-2.0-*
- veo-3.0-*
- veo-3.1-*

**Raison**: Génération de vidéos

### Audio/TTS
- gemini-2.5-flash-preview-tts
- gemini-2.5-pro-preview-tts
- gemini-2.5-flash-native-audio-latest

**Raison**: Text-to-speech, pas nécessaire

### Modèles Gemma
- gemma-3-1b-it
- gemma-3-4b-it
- gemma-3-12b-it
- gemma-3-27b-it
- gemma-3n-e4b-it

**Raison**: Modèles Gemma (différent de Gemini), plus petits, moins pertinents

### Modèles Spécialisés
- gemini-robotics-er-1.5-preview (Robotique)
- gemini-2.5-computer-use-preview (Usage ordinateur)
- deep-research-pro-preview (Recherche profonde)
- gemini-exp-1206 (Expérimental ancien)
- aqa (Q&A spécifique)

**Raison**: Cas d'usage très spécifiques, pas pour nous

### Variantes Flash Lite/Preview
- gemini-2.0-flash-001
- gemini-2.0-flash-lite-*
- gemini-2.0-flash-lite-preview-*

**Raison**: Versions redondantes, on garde les principales

---

## 🎯 Configuration Recommandée

```json
"gemini": {
  "default": "gemini-2.5-flash",
  "available": [
    "gemini-2.5-flash",
    "gemini-2.5-pro",
    "gemini-2.0-flash",
    "gemini-2.0-flash-exp"
  ]
}
```

---

## 📊 Comparaison

| Modèle | Version | Input | Output | Vitesse | Qualité | Usage |
|--------|---------|-------|--------|---------|---------|-------|
| **gemini-2.5-flash** | Stable | 1M | 65K | ⚡⚡⚡⚡⚡ | 🎯🎯🎯🎯🎯 | **DÉFAUT - Google Shopping + SEO** |
| **gemini-2.5-pro** | Stable | 1M | 65K | ⚡⚡⚡ | 🎯🎯🎯🎯🎯 | **SEO Premium** |
| gemini-2.0-flash | Stable | 1M | 8K | ⚡⚡⚡⚡ | 🎯🎯🎯🎯 | Alternative stable |
| gemini-2.0-flash-exp | Exp | 1M | 8K | ⚡⚡⚡⚡ | 🎯🎯🎯🎯 | Tests nouvelles features |

---

## 💡 Recommandations

### Changement de défaut
**Avant**: `gemini-2.0-flash-exp`  
**Après**: `gemini-2.5-flash` ⭐

**Pourquoi?**
- Version plus récente (juin 2025)
- 65K tokens output (vs 8K pour 2.0)
- Stable (pas experimental)
- Thinking mode inclus
- Meilleure qualité globale

### Pour Google Shopping
**Forcé**: `gemini-2.5-flash`

**Avantages**:
- Plus récent
- Meilleure catégorisation
- Output plus grand (65K vs 8K)
- Stable

### Pour SEO Standard
**Recommandé**: `gemini-2.5-flash`

**Avantages**:
- Descriptions plus riches (65K tokens)
- Plus récent
- Thinking mode pour meilleure réflexion

### Pour SEO Premium
**Recommandé**: `gemini-2.5-pro`

**Avantages**:
- Version Pro (meilleure qualité)
- 65K tokens output
- Thinking mode
- Parfait pour produits haut de gamme

---

## 🔄 Migration

Mettre à jour:
1. `ai_config.json` - Défaut + liste disponibles
2. `processor.py` - Modèle forcé pour Google Shopping
3. `MODELES_GEMINI_FILTRES.md` - Documentation

---

## Total
- **Modèles totaux**: 60+
- **Après filtrage**: 4 modèles pertinents
- **Ratio**: 93% de modèles retirés (non pertinents pour nous)
