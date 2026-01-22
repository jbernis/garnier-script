# Debug: Voir la réponse brute de l'agent IA

## Modifications apportées

### 1. Logs dans `SEOAgent.generate()` (agents.py)

Ajout de logs **avant** le parsing JSON pour afficher la réponse brute:

```python
# LOG: Afficher la réponse brute pour déboguer
logger.info(f"📝 Réponse brute de l'agent SEO pour {product_data.get('Handle', 'unknown')}:")
logger.info(f"--- DÉBUT RÉPONSE ---")
logger.info(response)
logger.info(f"--- FIN RÉPONSE ---")
```

### 2. Logs dans le retry (processor.py)

Même chose pour les tentatives de retry:

```python
# LOG: Afficher la réponse brute du retry pour déboguer
logger.info(f"📝 Réponse brute du retry (tentative {attempt}) pour {handle}:")
logger.info(f"--- DÉBUT RÉPONSE ---")
logger.info(seo_result)
logger.info(f"--- FIN RÉPONSE ---")
```

---

## Comment utiliser

### 1. Tester un produit

1. **Lancez l'application** si elle n'est pas déjà en cours
2. **Allez dans l'onglet Test**
3. **Sélectionnez un produit** (ex: 3661842387918)
4. **Cliquez sur "Tester avec article sélectionné"**

### 2. Regarder le terminal

**Ouvrez le terminal** où vous avez lancé `./run_gui.sh`

Vous verrez maintenant:

```
13:21:23 [INFO] 📝 Réponse brute de l'agent SEO pour nappe-coton-argelos:
13:21:23 [INFO] --- DÉBUT RÉPONSE ---
13:21:23 [INFO] (ICI LA RÉPONSE BRUTE DE GEMINI)
13:21:23 [INFO] --- FIN RÉPONSE ---
13:21:23 [WARNING] Impossible de parser la réponse JSON pour 3661842387918 (tentative 3): Expecting value: line 1 column 1 (char 0)
```

---

## Cas possibles

### ✅ Cas 1: Réponse vide

```
--- DÉBUT RÉPONSE ---

--- FIN RÉPONSE ---
```
→ **Gemini ne renvoie rien du tout**

**Solutions:**
- Vérifier le quota Gemini
- Vérifier la clé API
- Essayer un autre modèle (gemini-1.5-flash)

### ⚠️ Cas 2: Réponse en texte brut (pas JSON)

```
--- DÉBUT RÉPONSE ---
Voici le titre SEO: Nappe en coton Argelos
Et la description: Belle nappe...
--- FIN RÉPONSE ---
```
→ **Gemini répond en texte au lieu de JSON**

**Solutions:**
- Le prompt avec l'exemple JSON devrait résoudre ça
- Si ça persiste, problème avec le modèle gemini-2.0-flash-exp

### ✅ Cas 3: JSON valide

```
--- DÉBUT RÉPONSE ---
{
  "seo_title": "Nappe en coton Argelos...",
  "seo_description": "...",
  ...
}
--- FIN RÉPONSE ---
```
→ **JSON parfait, le parsing devrait fonctionner**

### ⚠️ Cas 4: JSON avec texte avant/après

```
--- DÉBUT RÉPONSE ---
Voici la réponse JSON demandée:

{
  "seo_title": "...",
  ...
}

J'espère que ça convient!
--- FIN RÉPONSE ---
```
→ **JSON valide mais pollué par du texte**

**Solutions:**
- Le prompt dit "UNIQUEMENT avec ce JSON, sans texte avant ni après"
- Si ça persiste, il faudra nettoyer la réponse avant parsing

---

## Prochaines étapes

1. **Testez maintenant** et copiez-collez la réponse brute ici
2. **Selon le cas**, on ajustera:
   - Le prompt (si texte au lieu de JSON)
   - Le parsing (si JSON avec du texte autour)
   - Le modèle (si quota/erreur)
   - L'API (si réponse vide)

---

## Notes techniques

- Les logs `INFO` s'affichent dans le **terminal uniquement**
- Ils n'apparaissent **pas** dans l'interface graphique (fenêtre de test)
- C'est volontaire pour éviter de surcharger l'interface
- Le niveau de log est configuré dans `run_gui.py` (logging.INFO)
