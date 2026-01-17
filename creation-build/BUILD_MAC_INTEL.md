# Guide de Build pour Mac Intel

Ce guide explique comment créer un fichier d'installation (.dmg) pour Mac Intel.

## Prérequis

- macOS avec Xcode Command Line Tools installés
- Python 3.8+ avec environnement virtuel
- PyInstaller installé
- Toutes les dépendances installées (voir `requirements.txt`)

## Étapes de Build

**Important:** Tous les scripts de build sont dans le répertoire `creation-build/`. Vous devez exécuter les commandes depuis ce répertoire ou utiliser les chemins relatifs.

### 1. Préparer l'environnement

```bash
# Activer l'environnement virtuel (depuis la racine du projet)
source venv/bin/activate

# Vérifier que PyInstaller est installé
pip install pyinstaller
```

### 2. Préparer l'icône (optionnel mais recommandé)

Si vous avez une icône PNG (recommandé: 1024x1024 pixels), convertissez-la en format .icns :

```bash
# Depuis le répertoire creation-build
cd creation-build

# Convertir votre icône PNG en .icns
./create_icon.sh ../votre_icone.png app_icon.icns
# ou si l'icône est déjà dans creation-build
./create_icon.sh votre_icone.png app_icon.icns
```

L'icône sera créée dans le répertoire `creation-build/`. Le fichier `build.spec` la détectera automatiquement.

**Note:** Si vous n'avez pas d'icône, l'application fonctionnera quand même, mais sans icône personnalisée dans le Dock.

### 3. Nettoyer les anciens builds (recommandé)

```bash
cd creation-build
python setup.py clean
```

Ou manuellement depuis la racine du projet :

```bash
rm -rf build dist __pycache__
find . -type d -name __pycache__ -exec rm -r {} +
```

### 4. Construire l'application

```bash
cd creation-build
python setup.py build
```

Ou directement avec PyInstaller depuis la racine du projet :

```bash
pyinstaller creation-build/build.spec --clean
```

L'application sera créée dans `dist/ScrapersShopify.app` (à la racine du projet)

### 5. Tester l'application (optionnel)

Avant de créer le DMG, vous pouvez tester l'application :

```bash
open dist/ScrapersShopify.app
```

### 6. Créer le fichier DMG d'installation

```bash
cd creation-build
./build_dmg.sh
```

Ou via setup.py :

```bash
cd creation-build
python setup.py dist
```

Le fichier DMG sera créé dans `dist/ScrapersShopify_MacIntel.dmg` (à la racine du projet)

## Utilisation du fichier DMG

### Installation

1. Double-cliquez sur `ScrapersShopify_MacIntel.dmg`
2. Glissez `ScrapersShopify.app` dans le dossier Applications
3. Ouvrez Applications et lancez l'application

### Première utilisation

Lors de la première utilisation, macOS peut afficher un avertissement de sécurité :

1. Allez dans **Préférences Système > Sécurité et confidentialité**
2. Cliquez sur **Ouvrir quand même** à côté du message d'avertissement
3. Confirmez que vous voulez ouvrir l'application

**Note:** Pour éviter cet avertissement, vous pouvez signer l'application avec un certificat de développeur Apple (nécessite un compte développeur payant).

## Structure du build

### Répertoire creation-build/

Contient tous les scripts et fichiers de configuration pour le build :
- `build.spec` : Configuration PyInstaller
- `setup.py` : Script de build principal
- `build_dmg.sh` : Script pour créer le DMG
- `create_icon.sh` : Script pour convertir PNG en .icns
- `BUILD_MAC_INTEL.md` : Ce guide

### Fichiers inclus dans l'application

- `run_gui.py` : Point d'entrée principal (à la racine)
- `app_config.json` : Configuration de l'application (à la racine)
- `csv_config.json` : Configuration des champs CSV (à la racine)
- `ai_config.json` : Configuration de l'éditeur IA (à la racine)
- `apps/gui/viewer_window_simple.html` : Template HTML du visualiseur
- Tous les modules Python nécessaires

### Répertoires créés à l'exécution

- `database/` : Bases de données SQLite (créées automatiquement)
- `outputs/` : Fichiers CSV générés (selon la configuration)

## Dépannage

### L'application ne se lance pas

1. Vérifiez les logs dans la console macOS :
   ```bash
   Console.app
   ```
   Recherchez les erreurs liées à `ScrapersShopify`

2. Essayez de lancer depuis le terminal :
   ```bash
   dist/ScrapersShopify.app/Contents/MacOS/ScrapersShopify
   ```

### L'icône n'apparaît pas

1. Vérifiez que le fichier `.icns` existe dans `creation-build/` ou à la racine du projet
2. Le fichier `build.spec` cherche l'icône dans plusieurs emplacements automatiquement
3. Rebuild l'application après avoir ajouté l'icône
4. Videz le cache macOS :
   ```bash
   sudo killall Finder
   ```

### Erreurs de dépendances manquantes

Si certaines dépendances ne sont pas incluses dans le build :

1. Vérifiez le fichier `creation-build/build.spec` et ajoutez les modules manquants dans `hiddenimports`
2. Rebuild l'application

### Taille du DMG trop importante

Pour réduire la taille du DMG :

1. Vérifiez que UPX est activé dans `build.spec` (par défaut: `upx=True`)
2. Excluez les modules non utilisés dans la section `excludes` de `build.spec`

## Commandes rapides

```bash
# Depuis le répertoire creation-build

# Build complet en une commande
cd creation-build
python setup.py clean && python setup.py build && ./build_dmg.sh

# Build avec icône
cd creation-build
./create_icon.sh ../icon.png app_icon.icns && python setup.py build && ./build_dmg.sh

# Test rapide
cd creation-build
python setup.py build && open ../dist/ScrapersShopify.app
```

## Notes importantes

- **Architecture:** Le build est configuré pour Mac Intel (x86_64). Pour Mac Apple Silicon (ARM), modifiez `target_arch='arm64'` dans `build.spec`
- **Code signing:** Par défaut, l'application n'est pas signée. Pour distribuer l'application, vous devrez la signer avec un certificat Apple Developer
- **Notarisation:** Pour macOS Catalina et supérieur, vous devrez notariser l'application via Apple Developer
- **Version:** La version de l'application est définie dans `build.spec` (actuellement 1.0.0)

## Support

Pour plus d'informations, consultez :
- `README.md` : Documentation générale du projet
- `FONCTIONNALITES.md` : Liste des fonctionnalités
- `docs/icone-dock-macos.md` : Guide spécifique pour les icônes
