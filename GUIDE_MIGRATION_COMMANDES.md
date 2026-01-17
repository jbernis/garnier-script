# Guide de Migration des Commandes

Ce guide vous aide à passer de l'ancienne structure à la nouvelle.

## Table de Correspondance

### Artiga

| Ancienne Commande | Nouvelle Commande |
|-------------------|-------------------|
| `python scraper-artiga-collect.py` | `python artiga/scraper-collect.py` |
| `python scraper-artiga-process.py` | `python artiga/scraper-process.py` |
| `python scraper-artiga-generate-csv.py` | `python artiga/scraper-generate-csv.py` |
| `python scraper-artiga-subcategory.py` | `python artiga/scraper-subcategory.py` |
| `python query_artiga_product.py` | `python artiga/query_product.py` |

### Cristel

| Ancienne Commande | Nouvelle Commande |
|-------------------|-------------------|
| `python scraper-cristel-collect.py` | `python cristel/scraper-collect.py` |
| `python scraper-cristel-process.py` | `python cristel/scraper-process.py` |
| `python scraper-cristel-generate-csv.py` | `python cristel/scraper-generate-csv.py` |
| `python scraper-cristel-subcategory.py` | `python cristel/scraper-subcategory.py` |
| `python query_cristel_product.py` | `python cristel/query_product.py` |

### Garnier

| Ancienne Commande | Nouvelle Commande |
|-------------------|-------------------|
| `python scraper-garnier-collect.py` | `python garnier/scraper-collect.py` |
| `python scraper-garnier-process.py` | `python garnier/scraper-process.py` |
| `python scraper-garnier-generate-csv.py` | `python garnier/scraper-generate-csv.py` |
| `python scraper-garnier-gamme.py` | `python garnier/scraper-gamme.py` |
| `python query_product.py` | `python garnier/query_product.py` |

## Exemples Pratiques

### Artiga - Test Rapide

**Avant :**
```bash
python scraper-artiga-collect.py --category "Nappes" --limit 3
python scraper-artiga-process.py --category "Nappes"
python scraper-artiga-generate-csv.py --category "Nappes"
python query_artiga_product.py --stats
```

**Maintenant :**
```bash
python artiga/scraper-collect.py --category "Nappes" --limit 3
python artiga/scraper-process.py --category "Nappes"
python artiga/scraper-generate-csv.py --category "Nappes"
python artiga/query_product.py --stats
```

### Cristel - Workflow Complet

**Avant :**
```bash
python scraper-cristel-subcategory.py \
  --url "https://www.cristel.com/casseroles" \
  --category "Casseroles" \
  --subcategory "Casseroles inox"
```

**Maintenant :**
```bash
python cristel/scraper-subcategory.py \
  --url "https://www.cristel.com/casseroles" \
  --category "Casseroles" \
  --subcategory "Casseroles inox"
```

### Garnier - Extraction Gamme

**Avant :**
```bash
python scraper-garnier-gamme.py --url "..." --gamme "..."
python query_product.py 37412
```

**Maintenant :**
```bash
python garnier/scraper-gamme.py --url "..." --gamme "..."
python garnier/query_product.py 37412
```

## Astuce : Créer des Alias

Pour faciliter la transition, vous pouvez créer des alias dans votre shell :

```bash
# Ajouter à votre ~/.zshrc ou ~/.bashrc
alias artiga-collect='python artiga/scraper-collect.py'
alias artiga-process='python artiga/scraper-process.py'
alias artiga-csv='python artiga/scraper-generate-csv.py'
alias artiga-sub='python artiga/scraper-subcategory.py'
alias artiga-query='python artiga/query_product.py'

alias cristel-collect='python cristel/scraper-collect.py'
alias cristel-process='python cristel/scraper-process.py'
alias cristel-csv='python cristel/scraper-generate-csv.py'
alias cristel-sub='python cristel/scraper-subcategory.py'
alias cristel-query='python cristel/query_product.py'

alias garnier-collect='python garnier/scraper-collect.py'
alias garnier-process='python garnier/scraper-process.py'
alias garnier-csv='python garnier/scraper-generate-csv.py'
alias garnier-gamme='python garnier/scraper-gamme.py'
alias garnier-query='python garnier/query_product.py'
```

Puis utiliser simplement :
```bash
artiga-collect --category "Nappes"
artiga-query --stats
```

## Scripts dans vos Outils

Si vous avez des scripts personnels qui appellent les anciens chemins, remplacez :

```python
# Avant
subprocess.run(["python", "scraper-artiga-collect.py", ...])

# Maintenant
subprocess.run(["python", "artiga/scraper-collect.py", ...])
```

## Compatibilité

Les **scripts legacy** restent disponibles à la racine :
- `scraper-artiga.py` (continue de fonctionner)
- `scraper-cristel.py` (continue de fonctionner)

L'**interface graphique** (GUI) n'est **pas affectée** par cette réorganisation.

## Questions Fréquentes

**Q: Les anciennes commandes fonctionnent-elles encore ?**  
R: Les scripts modulaires ont été déplacés, mais les scripts legacy (`scraper-artiga.py`, `scraper-cristel.py`) fonctionnent toujours.

**Q: Dois-je modifier mon GUI ?**  
R: Non, l'interface graphique utilise les wrappers dans `scrapers/` qui n'ont pas changé.

**Q: Les bases de données ont-elles été déplacées ?**  
R: Non, les fichiers `.db` restent à la racine du projet.

**Q: Puis-je utiliser l'ancienne et la nouvelle structure en même temps ?**  
R: Oui, elles sont totalement compatibles.

## Support

Pour toute question, consultez :
- `NOUVELLE_ORGANISATION.md` - Guide détaillé de la nouvelle structure
- `QUICK_START_ARTIGA_CRISTEL.md` - Guide de démarrage rapide
- `ARCHITECTURE_MIGRATION_SUMMARY.md` - Documentation complète
