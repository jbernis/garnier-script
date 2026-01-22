# Affichage des Erreurs de Quota dans la Fenêtre de Test

## 🎯 Objectif

Afficher clairement les erreurs de quota (Gemini, OpenAI, Claude, etc.) dans la fenêtre de test de l'éditeur IA, avec des instructions pour l'utilisateur.

---

## ✅ Modifications Apportées

### 1. Fenêtre de Test (apps/ai_editor/gui/window.py)

#### Détection des Erreurs de Quota

**Ligne ~1554-1573** : Ajout de la détection spécifique des erreurs `AIQuotaError`

```python
except Exception as e:
    # Détecter les erreurs de quota spécifiquement
    from utils.ai_providers import AIQuotaError
    
    if isinstance(e, AIQuotaError):
        # Message clair pour les erreurs de quota
        error_msg = f"⚠️ QUOTA {e.provider.upper()} DÉPASSÉ\n\n"
        error_msg += f"Votre quota {e.provider} est épuisé.\n\n"
        error_msg += "💡 Solutions:\n"
        error_msg += f"  1. Vérifiez votre compte {e.provider}\n"
        error_msg += "  2. Ajoutez des crédits si nécessaire\n"
        error_msg += "  3. Attendez le renouvellement du quota\n"
        error_msg += f"  4. Changez de modèle IA dans Configuration\n\n"
        error_msg += f"Détails: {e.original_error[:200]}"
    else:
        error_msg = str(e)
```

**Bénéfices:**
- Message clair et explicite
- Instructions pratiques pour résoudre le problème
- Indication du provider concerné (Gemini, OpenAI, Claude)

#### Amélioration de l'Affichage

**Ligne ~1701-1722** : Amélioration visuelle de l'affichage d'erreur

```python
def display_test_error(self, error_msg: str):
    """Affiche une erreur de test."""
    # Frame avec fond rouge foncé
    error_frame = ctk.CTkFrame(
        self.test_results_frame, 
        fg_color="#2B0000", 
        corner_radius=10
    )
    error_frame.pack(fill="x", padx=20, pady=20)
    
    error_label = ctk.CTkLabel(
        error_frame,
        text=f"❌ Erreur:\n\n{error_msg}",
        font=ctk.CTkFont(size=12),
        text_color="#FF6B6B",
        wraplength=650,
        justify="left"
    )
    error_label.pack(padx=20, pady=20)
```

**Bénéfices:**
- Fond rouge pour attirer l'attention
- Meilleure lisibilité avec padding
- Texte aligné à gauche pour les listes

---

### 2. Processeur (apps/ai_editor/processor.py)

#### Propagation des Erreurs de Quota

**Ligne ~278-291** : Propagation de l'erreur dans l'agent SEO

```python
except Exception as e:
    from utils.ai_providers import AIQuotaError
    if isinstance(e, AIQuotaError):
        logger.error(f"⚠️ Quota {e.provider} dépassé...")
        if log_callback:
            log_callback(f"  ⚠️ QUOTA {e.provider} DÉPASSÉ")
        # Propager l'erreur de quota pour la fenêtre de test
        raise
    else:
        logger.error(f"Erreur lors du traitement SEO...")
```

**Ligne ~341-355** : Propagation de l'erreur dans l'agent Google Shopping

```python
except Exception as e:
    from utils.ai_providers import AIQuotaError
    if isinstance(e, AIQuotaError):
        logger.error(f"⚠️ Quota {e.provider} dépassé...")
        if log_callback:
            log_callback(f"  ⚠️ QUOTA {e.provider} DÉPASSÉ")
        # Propager l'erreur de quota pour la fenêtre de test
        raise
    else:
        logger.error(f"Erreur lors du traitement Google Shopping...")
```

**Important:** 
- Le `raise` est ajouté **uniquement** dans `process_single_product()` (fenêtre de test)
- Dans `process_csv()`, l'erreur est loggée mais PAS propagée (pour continuer les autres produits)

---

## 📊 Résultat Visuel

### Avant

```
❌ Erreur:
Error calling model API
```

→ Message générique, pas d'information sur la cause

### Après (Quota Dépassé)

```
╔════════════════════════════════════════════════════╗
║  ❌ Erreur:                                         ║
║                                                     ║
║  ⚠️ QUOTA GEMINI DÉPASSÉ                           ║
║                                                     ║
║  Votre quota gemini est épuisé.                    ║
║                                                     ║
║  💡 Solutions:                                      ║
║    1. Vérifiez votre compte gemini                 ║
║    2. Ajoutez des crédits si nécessaire            ║
║    3. Attendez le renouvellement du quota          ║
║    4. Changez de modèle IA dans Configuration      ║
║                                                     ║
║  Détails: Resource exhausted: Quota exceeded...    ║
╚════════════════════════════════════════════════════╝
```

→ Message clair avec instructions pratiques

---

## 🧪 Test

### Scénario de Test

1. **Configurer un provider avec quota épuisé**
   - Onglet Configuration → Sélectionner Gemini
   - Utiliser une clé API avec quota dépassé

2. **Tester avec un produit**
   - Onglet Test → Sélectionner un article
   - Cliquer sur "🧪 Tester avec cet article"

3. **Vérifier l'affichage**
   - L'erreur s'affiche dans un cadre rouge
   - Le message indique clairement "QUOTA GEMINI DÉPASSÉ"
   - Les solutions sont listées

### Providers Supportés

Les erreurs de quota sont détectées pour:
- ✅ **OpenAI** (GPT-3.5, GPT-4, GPT-4o, etc.)
- ✅ **Gemini** (gemini-pro, gemini-1.5-pro, etc.)
- ✅ **Claude** (claude-3-opus, claude-3-sonnet, etc.)
- ✅ **Perplexity** (pplx-7b-online, etc.)

---

## 🔍 Cas d'Utilisation

### Cas 1: Quota OpenAI Dépassé

**Message affiché:**
```
⚠️ QUOTA OPENAI DÉPASSÉ

Votre quota openai est épuisé.

💡 Solutions:
  1. Vérifiez votre compte openai
  2. Ajoutez des crédits si nécessaire
  3. Attendez le renouvellement du quota
  4. Changez de modèle IA dans Configuration

Détails: You exceeded your current quota, please check your plan...
```

### Cas 2: Quota Gemini Dépassé

**Message affiché:**
```
⚠️ QUOTA GEMINI DÉPASSÉ

Votre quota gemini est épuisé.

💡 Solutions:
  1. Vérifiez votre compte gemini
  2. Ajoutez des crédits si nécessaire
  3. Attendez le renouvellement du quota
  4. Changez de modèle IA dans Configuration

Détails: Resource exhausted: Quota exceeded for quota metric...
```

### Cas 3: Autre Erreur (Non-Quota)

**Message affiché:**
```
❌ Erreur:

Invalid API key provided
```

→ Message d'erreur standard pour les autres types d'erreurs

---

## 💡 Avantages

### Pour l'Utilisateur

1. **Clarté**: Comprend immédiatement la cause du problème
2. **Autonomie**: Peut résoudre le problème sans support technique
3. **Instructions**: Solutions pratiques fournies directement
4. **Rapidité**: Sait exactement quoi faire (ajouter crédits, changer modèle, etc.)

### Pour le Support

1. **Moins de tickets**: Les utilisateurs résolvent eux-mêmes
2. **Diagnostics clairs**: Les captures d'écran montrent le problème exact
3. **Logs détaillés**: Les détails techniques sont toujours disponibles

---

## 📝 Notes Techniques

### Différence Test vs. Traitement Complet

**Fenêtre de Test** (`process_single_product`):
- Les erreurs de quota sont **propagées** (`raise`)
- L'utilisateur voit immédiatement l'erreur
- Le traitement s'arrête

**Traitement Complet** (`process_csv`):
- Les erreurs de quota sont **loggées** mais pas propagées
- Le traitement continue avec les autres produits
- L'utilisateur voit les warnings dans les logs

### Détection des Erreurs

Les erreurs de quota sont détectées via:
```python
from utils.ai_providers import AIQuotaError

if isinstance(e, AIQuotaError):
    # C'est une erreur de quota
    provider = e.provider      # "openai", "gemini", etc.
    details = e.original_error # Message d'erreur détaillé
```

---

## 🎯 Résumé

### Ce qui a été fait

- [x] ✅ Détection spécifique des erreurs de quota dans la fenêtre de test
- [x] ✅ Message clair avec provider concerné (OpenAI, Gemini, etc.)
- [x] ✅ Instructions pratiques pour résoudre le problème
- [x] ✅ Amélioration visuelle de l'affichage d'erreur
- [x] ✅ Propagation des erreurs depuis le processeur
- [x] ✅ Différenciation test/traitement complet

### Résultat

Les erreurs de quota (Gemini, OpenAI, Claude, etc.) s'affichent maintenant **clairement** dans la fenêtre de test avec:
- 🎯 Provider concerné (QUOTA GEMINI DÉPASSÉ, etc.)
- 💡 Solutions pratiques (vérifier compte, ajouter crédits, changer modèle)
- 📝 Détails techniques pour diagnostic
- 🎨 Affichage visuel amélioré (fond rouge, padding)

🎉 **L'utilisateur sait immédiatement quoi faire en cas de quota dépassé!**
