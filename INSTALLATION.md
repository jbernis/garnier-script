# Guide d'Installation - ScrapersShopify pour Mac Intel

## 📋 Prérequis

### ✅ Obligatoires
- **Mac Intel** (x86_64)
- **macOS 10.9+** (compatible jusqu'aux dernières versions)
- **Chrome ou Chromium** installé ([Télécharger Chrome](https://www.google.com/chrome/))
- **Connexion Internet**

### ❌ PAS nécessaires
- Python (inclus dans l'app)
- pip (inclus dans l'app)
- Environnement virtuel (tout est packagé)

---

## 📦 Installation

### Étape 1 : Télécharger le DMG
Téléchargez le fichier `ScrapersShopify_MacIntel.dmg`

### Étape 2 : Contourner la protection macOS
macOS bloque les apps non signées. **AVANT d'ouvrir le DMG**, ouvrez le Terminal et tapez :

```bash
xattr -cr ~/Downloads/ScrapersShopify_MacIntel.dmg
```

*(Remplacez `~/Downloads/` par le chemin où vous avez téléchargé le DMG)*

### Étape 3 : Ouvrir le DMG
Double-cliquez sur `ScrapersShopify_MacIntel.dmg`

Une fenêtre s'ouvrira avec :
- L'application `ScrapersShopify.app`
- Un raccourci vers le dossier `Applications`
- Un fichier `README.txt`

### Étape 4 : Installer l'application
Glissez `ScrapersShopify.app` dans le dossier `Applications`

### Étape 5 : Supprimer la quarantine de l'app installée
Dans le Terminal :

```bash
xattr -cr /Applications/ScrapersShopify.app
```

### Étape 6 : Lancer l'application
Allez dans **Applications** et double-cliquez sur `ScrapersShopify.app`

---

## 🚨 Si macOS dit "ScrapersShopify est endommagé"

### Solution rapide (Terminal)
```bash
xattr -cr /Applications/ScrapersShopify.app
open /Applications/ScrapersShopify.app
```

### Solution alternative (Clic droit)
1. **Clic droit** sur `ScrapersShopify.app`
2. Maintenez **⌥ Option** enfoncée
3. Choisissez **"Ouvrir"**
4. Cliquez **"Ouvrir"** dans la popup de confirmation

---

## 🎯 Première utilisation

### 1. Configuration des identifiants
Allez dans **⚙️ Configuration** et entrez vos identifiants :
- **Garnier-Thiebaut** : URL + Username + Password
- **Artiga** : URL (pas d'authentification)
- **Cristel** : URL (pas d'authentification)

### 2. (Optionnel) Configuration IA
Si vous voulez utiliser l'éditeur IA, ajoutez vos clés API :
- OpenAI API Key
- Anthropic API Key (Claude)
- Google API Key (Gemini)

### 3. Commencer l'import
Cliquez sur **"Importer des produits"** et suivez les instructions !

---

## 📁 Où sont stockés les fichiers ?

Tous les fichiers de l'application sont dans :

```
~/Library/Application Support/ScrapersShopify/
├── .env                      # Vos identifiants (configuration)
├── outputs/                  # Fichiers CSV générés
│   ├── garnier/
│   ├── artiga/
│   └── cristel/
└── database/                 # Bases de données des produits
    ├── garnier_products.db
    ├── artiga_products.db
    ├── cristel_products.db
    └── ai_prompts.db
```

---

## 🔧 Dépannage

### ❌ "L'app ne se lance pas du tout"
**Solution :**
```bash
xattr -cr /Applications/ScrapersShopify.app
chmod -R 755 /Applications/ScrapersShopify.app
open /Applications/ScrapersShopify.app
```

### ❌ "L'app crash au démarrage (icône clignote puis disparaît)"
**Vérifier les logs :**
```bash
/Applications/ScrapersShopify.app/Contents/MacOS/ScrapersShopify
```

Cela affichera l'erreur exacte dans le Terminal.

### ❌ "L'import ne fonctionne pas"
**Vérifiez que Chrome est installé :**
```bash
ls /Applications/Google\ Chrome.app
```

Si absent, téléchargez Chrome : [https://www.google.com/chrome/](https://www.google.com/chrome/)

### ❌ "Permission refusée lors de la sauvegarde"
L'app n'a peut-être pas accès à Application Support. Donnez les permissions :
```bash
chmod -R 755 ~/Library/Application\ Support/ScrapersShopify
```

---

## 🧹 Désinstallation complète

### Supprimer l'application
```bash
rm -rf /Applications/ScrapersShopify.app
```

### Supprimer toutes les données
```bash
rm -rf ~/Library/Application\ Support/ScrapersShopify
```

---

## 💡 Notes importantes

### Pourquoi "l'app est endommagée" ?
L'app n'est pas signée avec un certificat Apple Developer. C'est normal et sans danger. La commande `xattr -cr` supprime juste l'avertissement de macOS.

### Est-ce sûr ?
Oui ! C'est votre propre application. Le message de macOS est juste une protection pour les apps téléchargées depuis Internet.

### Compatibilité macOS
- **Testé sur :** macOS 10.9 à 15.x
- **Architecture :** Mac Intel (x86_64) uniquement
- **Mac Apple Silicon (M1/M2/M3) :** Fonctionne via Rosetta 2

---

## 📞 Support

Pour toute question ou problème :
1. Consultez la section **📚 Aide** dans l'application
2. Vérifiez la section **🔧 Troubleshooting** dans l'aide
3. Lancez l'app depuis le Terminal pour voir les logs d'erreur

---

## 🎉 Bon import !

Une fois installée, l'application fonctionne de manière autonome. Profitez-en !
