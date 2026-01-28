# Fix : Problème de Champ de Recherche dans l'Onglet Taxonomie

## Problème Identifié

Le champ de recherche dans l'onglet "Recherche" de la fenêtre Taxonomie est grisé et ne permet pas la saisie de texte.

### Cause

CustomTkinter `CTkTabview` désactive automatiquement les widgets `CTkEntry` des onglets non actifs pour des raisons de performance. Même après avoir sélectionné l'onglet, le champ reste parfois désactivé.

## Solutions Tentées

1. ✅ Ajout de `configure(state="normal")` après création → **Ne fonctionne pas**
2. ✅ Bind d'événements pour forcer l'activation → **Ne fonctionne pas**
3. ✅ Utilisation de `CTkTextbox` au lieu de `CTkEntry` → **Ne fonctionne pas**
4. ✅ Création dans un frame transparent → **À tester**

## Solution Finale Recommandée

Si le problème persiste après toutes les tentatives, il existe deux solutions définitives :

### Option 1 : Créer le Champ EN DEHORS du TabView

```python
# Dans setup_ui(), AVANT de créer le tabview
# Créer un frame pour la recherche qui ne sera jamais désactivé
self.search_container = ctk.CTkFrame(self)
self.search_container.pack(fill="x", padx=10, pady=10)

# Créer le champ de recherche ici (il sera toujours actif)
search_label = ctk.CTkLabel(self.search_container, text="🔍 Recherche Google Shopping:")
search_label.pack(side="left", padx=(10, 10))

self.search_entry = ctk.CTkEntry(
    self.search_container,
    placeholder_text="Ex: nappes, serviettes, linge de table...",
    width=500
)
self.search_entry.pack(side="left", fill="x", expand=True, padx=(0, 10))
self.search_entry.bind("<KeyRelease>", self.on_search_text_changed)

# Rendre le container invisible par défaut
self.search_container.pack_forget()

# Dans on_tab_selected(), montrer/cacher le champ selon l'onglet
if current_tab == "🔍 Recherche":
    self.search_container.pack(fill="x", padx=10, pady=10, before=self.tabview)
else:
    self.search_container.pack_forget()
```

### Option 2 : Ne Pas Utiliser de TabView pour la Recherche

Créer deux sections séparées avec des boutons pour basculer entre "Règles" et "Recherche".

## Test Manuel

Pour vérifier si le champ est désactivé :

```python
# Ajouter dans _activate_search_entry()
state = self.search_entry.cget("state")
print(f"État du champ: {state}")  # Devrait être "normal"
```

## Version CustomTkinter

Vérifier la version installée :
```bash
python3 -c "import customtkinter; print(customtkinter.__version__)"
```

Certaines versions de CustomTkinter ont des bugs avec les Entry dans les TabView.

## Actions Immédiates

1. **Relancer l'application complètement** (pas juste fermer la fenêtre)
2. **Vérifier qu'il n'y a pas d'erreurs dans le terminal**
3. **Cliquer directement dans le champ** après avoir ouvert l'onglet
4. Si ça ne fonctionne toujours pas, implémenter l'Option 1 ci-dessus
