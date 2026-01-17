# Icône Dock macOS pour l’application

Ce guide explique comment obtenir une **icône dans le Dock macOS** pour l’application.  
Sur macOS, l’icône Dock apparaît uniquement pour une **application .app** (bundle).  
La solution consiste donc à générer un bundle macOS via **PyInstaller** et à lui fournir une icône `.icns`.

---

## 1) Préparer l’icône (.icns)

### Option A — Avec un PNG (recommandé)
1. Prépare une image PNG carrée en **1024x1024** (ex: `icon.png`).
2. Convertis-la en `.icns` avec `iconutil` :

```bash
mkdir icon.iconset
sips -z 16 16     icon.png --out icon.iconset/icon_16x16.png
sips -z 32 32     icon.png --out icon.iconset/icon_16x16@2x.png
sips -z 32 32     icon.png --out icon.iconset/icon_32x32.png
sips -z 64 64     icon.png --out icon.iconset/icon_32x32@2x.png
sips -z 128 128   icon.png --out icon.iconset/icon_128x128.png
sips -z 256 256   icon.png --out icon.iconset/icon_128x128@2x.png
sips -z 256 256   icon.png --out icon.iconset/icon_256x256.png
sips -z 512 512   icon.png --out icon.iconset/icon_256x256@2x.png
sips -z 512 512   icon.png --out icon.iconset/icon_512x512.png
sips -z 1024 1024 icon.png --out icon.iconset/icon_512x512@2x.png
iconutil -c icns icon.iconset -o app_icon.icns
```

Tu obtiens `app_icon.icns`.

### Option B — Outil en ligne
Utilise un convertisseur PNG → ICNS si tu préfères.

---

## 2) Déclarer l’icône dans `build.spec`

Ouvre `build.spec` et remplace `icon=None` par le chemin de ton `.icns` **dans les deux blocs** :

- `EXE(..., icon=...)`
- `BUNDLE(..., icon=...)`

Exemple :

```python
icon='docs/app_icon.icns'
```

---

## 3) Générer l’application macOS

Active ton venv, puis lance :

```bash
pyinstaller build.spec
```

Le bundle sera créé dans :

```
dist/ScrapersShopify.app
```

---

## 4) Déplacer dans /Applications

```bash
mv dist/ScrapersShopify.app /Applications/
```

---

## 5) Ajouter au Dock

- Ouvre `/Applications`
- Glisse `ScrapersShopify.app` dans le Dock

L’icône restera et l’application pourra être lancée directement depuis le Dock.

---

## Dépannage

### L’icône n’apparaît pas
- Vérifie que l’icône est bien un `.icns`.
- Vérifie que tu l’as bien déclaré dans **EXE** et **BUNDLE**.
- Rebuild l’app avec `pyinstaller build.spec`.

### L’app ne se lance pas depuis le Dock
- Assure-toi que `dist/ScrapersShopify.app` est le bundle généré récemment.
- Lance-la une fois depuis Finder pour macOS (quarantaine).

---

## Option bonus : changer le nom de l’app

Dans `build.spec` :

```python
name='ScrapersShopify'
```

Et dans `BUNDLE(...)` :

```python
name='ScrapersShopify.app'
```

---

Si tu veux, je peux aussi :
- préparer l’icône `.icns` depuis un PNG,
- mettre à jour `build.spec`,
- lancer le build.

