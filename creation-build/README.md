# Scripts de Build pour Mac Intel

Ce répertoire contient tous les scripts et fichiers de configuration nécessaires pour créer un fichier d'installation (.dmg) pour Mac Intel.

## Fichiers

- **`build.spec`** : Configuration PyInstaller pour créer l'application bundle
- **`setup.py`** : Script Python principal pour gérer le build (clean, build, dist)
- **`build_dmg.sh`** : Script shell pour créer le fichier DMG d'installation
- **`create_icon.sh`** : Script shell pour convertir une icône PNG en format .icns
- **`BUILD_MAC_INTEL.md`** : Guide détaillé d'utilisation

## Utilisation rapide

### Depuis le répertoire creation-build

```bash
cd creation-build

# 1. Nettoyer les anciens builds
python setup.py clean

# 2. Construire l'application
python setup.py build

# 3. Créer le DMG
python setup.py dist
# ou directement
./build_dmg.sh
```

### Avec icône

```bash
cd creation-build

# 1. Convertir l'icône PNG en .icns
./create_icon.sh ../icon.png app_icon.icns

# 2. Build et créer le DMG
python setup.py build && ./build_dmg.sh
```

## Résultat

L'application sera créée dans `../dist/ScrapersShopify.app` et le DMG dans `../dist/ScrapersShopify_MacIntel.dmg` (relatif à la racine du projet).

## Documentation

Pour plus de détails, consultez `BUILD_MAC_INTEL.md`.
