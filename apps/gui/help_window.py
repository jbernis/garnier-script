"""
Fenêtre d'aide pour expliquer le fonctionnement de l'application.
"""

import customtkinter as ctk
import sys
import os
from pathlib import Path

class HelpWindow(ctk.CTkToplevel):
    """Fenêtre d'aide avec documentation complète."""
    
    def __init__(self, parent):
        super().__init__(parent)
        
        self.title("Aide - Scrapers Shopify")
        self.geometry("900x700")
        self.resizable(True, True)
        
        # Configuration CustomTkinter
        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("blue")
        
        # Container principal avec sidebar
        main_container = ctk.CTkFrame(self)
        main_container.pack(fill="both", expand=True)
        
        # Sidebar pour navigation
        sidebar = ctk.CTkFrame(main_container, width=200)
        sidebar.pack(side="left", fill="y", padx=10, pady=10)
        sidebar.pack_propagate(False)
        
        # Titre sidebar
        sidebar_title = ctk.CTkLabel(
            sidebar,
            text="Sections",
            font=ctk.CTkFont(size=18, weight="bold")
        )
        sidebar_title.pack(pady=(20, 30))
        
        # Boutons de navigation
        self.sections = {
            "Vue d'ensemble": self.show_overview,
            "Import de produits": self.show_import_help,
            "Configuration": self.show_config_help,
            "Configuration CSV": self.show_csv_config_help,
            "Éditeur IA": self.show_ai_editor_help,
            "Générateur CSV": self.show_csv_generator_help,
            "Viewer CSV": self.show_viewer_help,
            "Troubleshooting": self.show_troubleshooting,
        }
        
        for section_name, callback in self.sections.items():
            btn = ctk.CTkButton(
                sidebar,
                text=section_name,
                command=callback,
                width=180,
                height=40,
                anchor="w",
                font=ctk.CTkFont(size=13)
            )
            btn.pack(pady=5, padx=10)
        
        # Zone de contenu avec scrollbar
        self.content_frame = ctk.CTkScrollableFrame(main_container)
        self.content_frame.pack(side="right", fill="both", expand=True, padx=10, pady=10)
        
        # Afficher la vue d'ensemble par défaut
        self.show_overview()
        
        # Centrer la fenêtre
        self.center_window()
        
        # Garder la fenêtre au premier plan par rapport au parent
        try:
            self.transient(parent)
        except Exception:
            pass
        self.after(100, self._bring_to_front)
    
    def center_window(self):
        """Centre la fenêtre sur l'écran."""
        self.update_idletasks()
        width = self.winfo_width()
        height = self.winfo_height()
        x = (self.winfo_screenwidth() // 2) - (width // 2)
        y = (self.winfo_screenheight() // 2) - (height // 2)
        self.geometry(f"{width}x{height}+{x}+{y}")
    
    def _bring_to_front(self):
        """Amène la fenêtre au premier plan."""
        try:
            self.lift()
            self.focus_force()
        except:
            pass
    
    def clear_content(self):
        """Efface le contenu actuel."""
        for widget in self.content_frame.winfo_children():
            widget.destroy()
    
    def add_title(self, text):
        """Ajoute un titre de section."""
        title = ctk.CTkLabel(
            self.content_frame,
            text=text,
            font=ctk.CTkFont(size=24, weight="bold")
        )
        title.pack(anchor="w", pady=(0, 20))
    
    def add_subtitle(self, text):
        """Ajoute un sous-titre."""
        subtitle = ctk.CTkLabel(
            self.content_frame,
            text=text,
            font=ctk.CTkFont(size=18, weight="bold")
        )
        subtitle.pack(anchor="w", pady=(20, 10))
    
    def add_text(self, text):
        """Ajoute du texte normal."""
        label = ctk.CTkLabel(
            self.content_frame,
            text=text,
            font=ctk.CTkFont(size=13),
            justify="left",
            wraplength=750,
            anchor="w"
        )
        label.pack(anchor="w", pady=(0, 10), fill="x")
    
    def add_code(self, text):
        """Ajoute un bloc de code."""
        code_frame = ctk.CTkFrame(self.content_frame, fg_color=("gray85", "gray20"))
        code_frame.pack(fill="x", pady=(0, 15))
        
        code_label = ctk.CTkLabel(
            code_frame,
            text=text,
            font=ctk.CTkFont(family="Courier", size=12),
            justify="left",
            anchor="w"
        )
        code_label.pack(anchor="w", padx=15, pady=10)
    
    def show_overview(self):
        """Affiche la vue d'ensemble."""
        self.clear_content()
        self.add_title("📚 Vue d'ensemble")
        
        self.add_text(
            "Bienvenue dans Scrapers Shopify ! Cette application vous permet d'importer "
            "automatiquement des produits depuis plusieurs fournisseurs (Garnier-Thiebaut, "
            "Artiga, Cristel) et de générer des fichiers CSV compatibles avec Shopify."
        )
        
        self.add_subtitle("🎯 Workflow principal")
        self.add_text("1. Configuration : Entrez vos identifiants dans la section Configuration")
        self.add_text("2. Import : Sélectionnez un fournisseur et des catégories à importer")
        self.add_text("3. Traitement : L'app scrape les produits et génère un CSV")
        self.add_text("4. Édition IA (optionnel) : Améliorez vos descriptions avec l'IA")
        self.add_text("5. Import dans Shopify : Utilisez le CSV généré pour importer dans Shopify")
    
    def show_import_help(self):
        """Affiche l'aide sur l'import de produits."""
        self.clear_content()
        self.add_title("📦 Import de produits")
        
        self.add_subtitle("Comment importer des produits ?")
        self.add_text(
            "1. Cliquez sur 'Importer des produits' depuis la page d'accueil"
        )
        self.add_text(
            "2. Sélectionnez un fournisseur dans la liste déroulante (Garnier-Thiebaut, Artiga, Cristel)"
        )
        self.add_text(
            "3. Attendez que les catégories se chargent (affichage progressif)"
        )
        self.add_text(
            "4. Cochez les catégories que vous souhaitez importer"
        )
        self.add_text(
            "5. Cliquez sur 'Démarrer l'import'"
        )
        
        self.add_subtitle("Options avancées")
        self.add_text(
            "• Mode Gamme (Garnier uniquement) : Importez une gamme spécifique via son URL"
        )
        self.add_text(
            "• Sous-catégories : Disponibles pour Artiga et Cristel"
        )
        self.add_text(
            "• Tout sélectionner / Tout désélectionner : Cochez/décochez toutes les catégories d'un coup"
        )
        
        self.add_subtitle("Pendant l'import")
        self.add_text(
            "Une fenêtre de progression s'affiche avec :"
        )
        self.add_text("• Barre de progression visuelle")
        self.add_text("• Logs en temps réel de l'extraction")
        self.add_text("• Bouton d'annulation si besoin")
        self.add_text("• Bouton de téléchargement du CSV une fois terminé")
    
    def show_config_help(self):
        """Affiche l'aide sur la configuration."""
        self.clear_content()
        self.add_title("⚙️ Configuration")
        
        self.add_subtitle("Configuration des fournisseurs")
        self.add_text(
            "Entrez vos identifiants pour chaque fournisseur :"
        )
        
        self.add_text("• Garnier-Thiebaut : URL de base + Nom d'utilisateur + Mot de passe")
        self.add_text("• Artiga : URL de base (pas d'authentification)")
        self.add_text("• Cristel : URL de base (pas d'authentification)")
        
        self.add_subtitle("Configuration des fournisseurs IA (optionnel)")
        self.add_text(
            "Si vous souhaitez utiliser l'éditeur IA pour améliorer vos descriptions, "
            "entrez vos clés API :"
        )
        self.add_text("• OpenAI API Key (GPT-4, GPT-3.5)")
        self.add_text("• Anthropic API Key (Claude)")
        self.add_text("• Google API Key (Gemini)")
        
        self.add_subtitle("Paramètres de l'application")
        self.add_text(
            "• Supprimer le répertoire outputs à la fermeture : "
            "Si activé, les fichiers CSV générés seront supprimés automatiquement "
            "lorsque vous fermez l'application"
        )
    
    def show_csv_config_help(self):
        """Affiche l'aide sur la configuration CSV."""
        self.clear_content()
        self.add_title("📝 Configuration CSV")
        
        self.add_subtitle("Personnaliser les colonnes du CSV Shopify")
        self.add_text(
            "Cette section vous permet de configurer quelles colonnes seront incluses "
            "dans les fichiers CSV générés pour Shopify."
        )
        
        self.add_text(
            "• Cochez les colonnes que vous souhaitez exporter"
        )
        self.add_text(
            "• Décochez celles qui ne vous intéressent pas"
        )
        self.add_text(
            "• Les colonnes obligatoires pour Shopify ne peuvent pas être décochées"
        )
        
        self.add_subtitle("Colonnes importantes")
        self.add_text("• Handle : Identifiant unique du produit")
        self.add_text("• Title : Nom du produit")
        self.add_text("• Body (HTML) : Description complète")
        self.add_text("• Variant SKU : Code SKU de la variante")
        self.add_text("• Variant Price : Prix de vente")
        self.add_text("• Image Src : URL de l'image")
    
    def show_ai_editor_help(self):
        """Affiche l'aide sur l'éditeur IA."""
        self.clear_content()
        self.add_title("🤖 Éditeur IA")
        
        self.add_subtitle("À quoi sert l'éditeur IA ?")
        self.add_text(
            "L'éditeur IA vous permet d'améliorer automatiquement les descriptions de "
            "vos produits en utilisant des modèles d'intelligence artificielle "
            "(OpenAI GPT-4, Claude, Gemini)."
        )
        
        self.add_subtitle("Comment l'utiliser ?")
        self.add_text("1. Chargez un fichier CSV Shopify existant")
        self.add_text("2. Sélectionnez un prompt set (instructions pour l'IA)")
        self.add_text("3. Configurez le fournisseur IA et le modèle")
        self.add_text("4. Lancez le traitement")
        self.add_text("5. Visualisez les résultats et téléchargez le CSV amélioré")
        
        self.add_subtitle("Options de traitement")
        self.add_text("• Batch size : Nombre de produits traités en parallèle")
        self.add_text("• Max tokens : Limite de tokens par requête")
        self.add_text("• Seuil de confiance : Qualité minimale acceptée")
        
        self.add_subtitle("Gestion des prompts")
        self.add_text(
            "Vous pouvez créer, modifier et supprimer des prompt sets personnalisés "
            "pour adapter les instructions données à l'IA selon vos besoins."
        )
    
    def show_csv_generator_help(self):
        """Affiche l'aide sur le générateur CSV."""
        self.clear_content()
        self.add_title("📊 Générateur de CSV")
        
        self.add_subtitle("À quoi sert le générateur ?")
        self.add_text(
            "Le générateur CSV vous permet de créer des fichiers CSV Shopify directement "
            "depuis les bases de données de produits existantes, sans avoir à relancer "
            "un import complet."
        )
        
        self.add_subtitle("Comment l'utiliser ?")
        self.add_text("1. Sélectionnez un fournisseur")
        self.add_text("2. Choisissez une ou plusieurs catégories")
        self.add_text("3. Configurez les options de filtrage")
        self.add_text("4. Générez le CSV")
        
        self.add_subtitle("Avantages")
        self.add_text("• Rapide : Pas besoin de re-scraper les produits")
        self.add_text("• Flexible : Choisissez exactement ce que vous voulez exporter")
        self.add_text("• Réutilisable : Générez plusieurs CSV différents depuis la même base")
    
    def show_viewer_help(self):
        """Affiche l'aide sur le viewer CSV."""
        self.clear_content()
        self.add_title("👁️ Viewer CSV")
        
        self.add_subtitle("Visualiser vos fichiers CSV")
        self.add_text(
            "Le viewer CSV vous permet de visualiser le contenu de vos fichiers CSV "
            "avant de les importer dans Shopify."
        )
        
        self.add_subtitle("Fonctionnalités")
        self.add_text("• Affichage sous forme de cartes produits")
        self.add_text("• Aperçu des images")
        self.add_text("• Lecture de la description HTML")
        self.add_text("• Filtrage et recherche")
        self.add_text("• Navigation facile entre les produits")
    
    def show_troubleshooting(self):
        """Affiche l'aide de dépannage."""
        self.clear_content()
        self.add_title("🔧 Troubleshooting")
        
        self.add_subtitle("Où sont stockés mes fichiers ?")
        
        # Déterminer le chemin en fonction du mode
        if getattr(sys, "frozen", False):
            base_path = str(Path.home() / "Library" / "Application Support" / "ScrapersShopify")
        else:
            base_path = str(Path.cwd())
        
        self.add_text("En mode application packagée, tous les fichiers sont dans :")
        self.add_code(base_path)
        
        self.add_text("Structure des dossiers :")
        self.add_code(
            "ScrapersShopify/\n"
            "├── .env                    # Configuration (identifiants)\n"
            "├── outputs/                # Fichiers CSV générés\n"
            "│   ├── garnier/\n"
            "│   ├── artiga/\n"
            "│   └── cristel/\n"
            "└── database/               # Bases de données SQLite\n"
            "    ├── garnier_products.db\n"
            "    ├── artiga_products.db\n"
            "    ├── cristel_products.db\n"
            "    └── ai_prompts.db"
        )
        
        self.add_subtitle("Problèmes fréquents")
        
        self.add_text("❌ L'import ne démarre pas")
        self.add_text(
            "→ Vérifiez que vos identifiants sont corrects dans Configuration"
        )
        self.add_text(
            "→ Vérifiez votre connexion internet"
        )
        
        self.add_text("❌ L'éditeur IA ne fonctionne pas")
        self.add_text(
            "→ Vérifiez que vous avez entré une clé API valide dans Configuration"
        )
        self.add_text(
            "→ Vérifiez que vous avez du crédit sur votre compte API"
        )
        
        self.add_text("❌ Le CSV généré est vide")
        self.add_text(
            "→ Vérifiez que les catégories sélectionnées contiennent des produits"
        )
        self.add_text(
            "→ Vérifiez les logs de l'import pour voir les erreurs"
        )
        
        self.add_subtitle("Nettoyage et réinitialisation")
        
        self.add_text("Pour réinitialiser complètement l'application :")
        self.add_text("1. Fermez l'application")
        self.add_text("2. Supprimez le dossier Application Support :")
        self.add_code(f"rm -rf '{base_path}'")
        self.add_text("3. Relancez l'application et reconfigurez vos identifiants")
        
        self.add_subtitle("Support")
        self.add_text(
            "Si vous rencontrez un problème persistant, consultez les logs dans le terminal "
            "en lançant l'application depuis la ligne de commande :"
        )
        self.add_code("open /Applications/ScrapersShopify.app")
