#!/usr/bin/env python3
"""
Script de test SIMPLE pour vérifier que le champ de recherche fonctionne.
"""

import customtkinter as ctk

def main():
    """Test basique du champ de recherche."""
    
    # Créer la fenêtre
    root = ctk.CTk()
    root.title("Test - Champ de Recherche")
    root.geometry("800x600")
    
    # Titre
    title = ctk.CTkLabel(
        root,
        text="🔍 Test du Champ de Recherche",
        font=ctk.CTkFont(size=20, weight="bold")
    )
    title.pack(pady=20)
    
    # Message d'instruction
    instruction = ctk.CTkLabel(
        root,
        text="Si vous pouvez taper dans le champ ci-dessous, ça fonctionne !",
        font=ctk.CTkFont(size=14)
    )
    instruction.pack(pady=10)
    
    # Frame pour le champ
    search_frame = ctk.CTkFrame(root)
    search_frame.pack(fill="x", padx=50, pady=20)
    
    # Label
    label = ctk.CTkLabel(
        search_frame,
        text="Rechercher:",
        font=ctk.CTkFont(size=14)
    )
    label.pack(side="left", padx=10)
    
    # Champ de recherche
    entry = ctk.CTkEntry(
        search_frame,
        placeholder_text="Tapez ici pour tester...",
        font=ctk.CTkFont(size=14),
        height=40
    )
    entry.pack(side="left", fill="x", expand=True, padx=(0, 10))
    
    # Label pour afficher ce qui est tapé
    result_label = ctk.CTkLabel(
        root,
        text="Vous tapez : ",
        font=ctk.CTkFont(size=12),
        text_color="gray"
    )
    result_label.pack(pady=10)
    
    # Fonction appelée à chaque frappe
    def on_key(event):
        text = entry.get()
        result_label.configure(text=f"Vous tapez : {text}")
    
    entry.bind("<KeyRelease>", on_key)
    
    # Donner le focus au champ
    entry.focus()
    
    print("✅ Test lancé")
    print("→ Si vous pouvez taper dans le champ, c'est que ça fonctionne")
    print("→ Le texte que vous tapez devrait s'afficher en dessous")
    
    # Lancer l'application
    root.mainloop()

if __name__ == "__main__":
    main()
