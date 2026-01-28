#!/usr/bin/env python3
"""
Test ULTRA SIMPLE - juste un champ de recherche sans TabView.
"""

import customtkinter as ctk

def main():
    root = ctk.CTk()
    root.title("Test Simple")
    root.geometry("600x300")
    
    # Titre
    title = ctk.CTkLabel(root, text="🔍 Test Recherche Simple", font=("Arial", 20, "bold"))
    title.pack(pady=20)
    
    # Frame
    frame = ctk.CTkFrame(root)
    frame.pack(fill="x", padx=50, pady=20)
    
    # Label
    label = ctk.CTkLabel(frame, text="Rechercher:")
    label.pack(side="left", padx=10)
    
    # Entry avec StringVar (comme l'onglet Test)
    search_var = ctk.StringVar()
    entry = ctk.CTkEntry(
        frame,
        textvariable=search_var,
        placeholder_text="Tapez ici...",
        width=300
    )
    entry.pack(side="left", padx=10, fill="x", expand=True)
    
    # Résultat
    result = ctk.CTkLabel(root, text="", font=("Arial", 12))
    result.pack(pady=10)
    
    def on_key(event):
        result.configure(text=f"Vous tapez : {search_var.get()}")
    
    entry.bind("<KeyRelease>", on_key)
    entry.focus()
    
    print("✅ Test lancé - essayez de taper dans le champ")
    root.mainloop()

if __name__ == "__main__":
    main()
