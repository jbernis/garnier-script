"""
Fenêtre principale de l'application avec menu de navigation.
"""

import customtkinter as ctk
from typing import Optional
import sys
import os

# Ajouter le répertoire parent au path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from apps.gui.setup_window import SetupWindow
from apps.gui.config_window import ConfigWindow
from apps.gui.import_window import ImportWindow
from apps.gui.csv_config_window import CSVConfigWindow
from apps.gui.cleanup_window import CleanupWindow
from apps.ai_editor.gui.window import AIEditorWindow
from utils.setup_checker import SetupChecker
from utils.cleanup import remove_outputs_directory
from utils.app_config import get_config

# Importer viewer_window de manière optionnelle (nécessite tkinterweb)
try:
    from apps.gui.viewer_window import ViewerWindow
    VIEWER_AVAILABLE = True
except ImportError as e:
    VIEWER_AVAILABLE = False
    ViewerWindow = None
    import logging
    logging.getLogger(__name__).warning(f"Visualiseur CSV non disponible: {e}")


class MainWindow(ctk.CTk):
    """Fenêtre principale de l'application."""
    
    def __init__(self):
        super().__init__()
        
        self.title("Scrapers Shopify - Interface Graphique")
        self.geometry("1000x700")
        self.resizable(True, True)
        
        # Configuration CustomTkinter
        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("blue")
        
        # Variables pour les fenêtres ouvertes
        self.setup_window: Optional[SetupWindow] = None
        self.config_window: Optional[ConfigWindow] = None
        self.csv_config_window: Optional[CSVConfigWindow] = None
        self.import_window: Optional[ImportWindow] = None
        self.cleanup_window: Optional[CleanupWindow] = None
        self.viewer_window: Optional[ViewerWindow] = None
        self.ai_editor_window: Optional[AIEditorWindow] = None
        self.csv_generator_window = None
        
        # SetupChecker pour vérifier l'état
        self.setup_checker = SetupChecker()
        
        # Frame principal avec sidebar
        main_container = ctk.CTkFrame(self)
        main_container.pack(fill="both", expand=True)
        
        # Sidebar
        self.create_sidebar(main_container)
        
        # Zone de contenu principale (alignée à gauche)
        self.content_frame = ctk.CTkFrame(main_container)
        self.content_frame.pack(side="right", fill="both", expand=True, padx=(20, 20), pady=20)
        
        # Vérifier l'état du setup et mettre à jour les boutons
        self.check_setup_status()
        
        # Afficher la page d'accueil
        self.show_home()
        
        # Centrer la fenêtre
        self.center_window()
        
        # Amener la fenêtre au premier plan immédiatement
        self.bring_to_front()
        
        # Configurer le handler de fermeture pour nettoyer les fichiers générés
        self.protocol("WM_DELETE_WINDOW", self.on_closing)
    
    def bring_to_front(self):
        """Amène la fenêtre au premier plan."""
        # Forcer la mise à jour de la fenêtre avant de la mettre au premier plan
        self.update_idletasks()
        
        # Sur macOS, utiliser osascript AVANT les autres méthodes pour amener l'application au premier plan
        import platform
        if platform.system() == "Darwin":  # macOS
            try:
                import subprocess
                # Obtenir le PID du processus Python actuel
                pid = os.getpid()
                # Utiliser osascript pour amener l'application au premier plan
                subprocess.run([
                    "osascript", "-e",
                    f'tell application "System Events" to set frontmost of every process whose unix id is {pid} to true'
                ], check=False, timeout=1, capture_output=True)
            except:
                pass  # Ignorer les erreurs
        
        # Méthodes Tkinter pour amener la fenêtre au premier plan
        self.lift()
        self.focus_force()
        
        # Temporairement mettre la fenêtre au-dessus de tout
        try:
            self.attributes('-topmost', True)
            # Retirer après un court délai pour permettre l'interaction normale
            self.after(100, lambda: self.attributes('-topmost', False))
        except:
            pass  # Certains systèmes peuvent ne pas supporter cette option
    
    def center_window(self):
        """Centre la fenêtre sur l'écran."""
        self.update_idletasks()
        width = self.winfo_width()
        height = self.winfo_height()
        x = (self.winfo_screenwidth() // 2) - (width // 2)
        y = (self.winfo_screenheight() // 2) - (height // 2)
        self.geometry(f"{width}x{height}+{x}+{y}")
    
    def create_sidebar(self, parent):
        """Crée la barre latérale de navigation."""
        sidebar = ctk.CTkFrame(parent, width=200)
        sidebar.pack(side="left", fill="y", padx=20, pady=20)
        sidebar.pack_propagate(False)
        
        # Logo/Titre
        title_label = ctk.CTkLabel(
            sidebar,
            text="Scrapers\nShopify",
            font=ctk.CTkFont(size=24, weight="bold"),
            justify="center"
        )
        title_label.pack(pady=(30, 40))
        
        # Boutons de navigation dans la sidebar
        nav_buttons = [
            ("🏠 Accueil", self.show_home),
            ("📝 Configuration CSV", self.open_csv_config),
            ("⚙️ Configuration", self.open_config),
            ("🗑️ Nettoyage BDD", self.open_cleanup),
            ("ℹ️ À propos", self.show_about),
        ]
        if not getattr(sys, "frozen", False):
            nav_buttons.insert(3, ("🔧 Setup", self.open_setup))
        
        self.nav_buttons = {}
        for text, command in nav_buttons:
            button = ctk.CTkButton(
                sidebar,
                text=text,
                command=command,
                width=180,
                height=30,
                anchor="w",
                font=ctk.CTkFont(size=14)
            )
            button.pack(pady=5, padx=10)
            self.nav_buttons[text] = button
        
        # Stocker les références aux boutons qui doivent être désactivés si setup n'est pas OK
        self.config_button = self.nav_buttons.get("⚙️ Configuration")
        self.csv_config_button = self.nav_buttons.get("📝 Configuration CSV")
        self.cleanup_button = self.nav_buttons.get("🗑️ Nettoyage BDD")
        self.home_button = self.nav_buttons.get("🏠 Accueil")
        self.about_button = self.nav_buttons.get("ℹ️ À propos")
        
        # Séparateur
        separator = ctk.CTkFrame(sidebar, height=2, fg_color="gray")
        separator.pack(fill="x", padx=20, pady=20)
        
        # Version
        version_label = ctk.CTkLabel(
            sidebar,
            text="Version 1.0.0",
            font=ctk.CTkFont(size=10),
            text_color="gray"
        )
        version_label.pack(side="bottom", pady=20)
    
    def clear_content(self):
        """Efface le contenu de la zone principale."""
        for widget in self.content_frame.winfo_children():
            widget.destroy()
    
    def show_home(self):
        """Affiche la page d'accueil."""
        self.clear_content()
        
        # Titre
        title = ctk.CTkLabel(
            self.content_frame,
            text="Bienvenue",
            font=ctk.CTkFont(size=32, weight="bold")
        )
        title.pack(pady=(40, 20))
        
        # Description
        desc = ctk.CTkLabel(
            self.content_frame,
            text="Interface graphique pour l'importation de produits depuis différents fournisseurs vers Shopify",
            font=ctk.CTkFont(size=14),
            text_color="gray",
            wraplength=600
        )
        desc.pack(pady=(0, 20))
        
        # Cards pour les actions rapides - Container principal avec scrollbar
        cards_container = ctk.CTkScrollableFrame(self.content_frame)
        cards_container.pack(fill="both", expand=True, padx=40, pady=20)
        
        # Frame pour contenir les cartes avec layout responsive, aligné à gauche
        cards_wrapper = ctk.CTkFrame(cards_container)
        cards_wrapper.pack(pady=20, fill="x", padx=20, anchor="w")  # anchor="w" pour aligner à gauche
        
        # Fonction helper pour créer une carte carrée responsive avec sa propre frame
        def create_card(parent, title, description, button_text, command, button_color=None, button_hover=None, enabled=True):
            """Crée une carte carrée responsive avec titre, description et bouton."""
            # Taille fixe pour la carte carrée (ne s'étire pas)
            card_size = 280  # Taille fixe pour une carte carrée
            
            # Créer une frame individuelle pour chaque carte (sans expand pour garder la taille fixe)
            card_frame = ctk.CTkFrame(parent)
            card_frame.pack(side="left", padx=20, pady=15)  # Pas de fill/expand
            
            # Créer la carte avec dimensions carrées fixes et bordure fine
            card = ctk.CTkFrame(
                card_frame,
                width=card_size,
                height=card_size,
                corner_radius=10,
                border_width=1,  # Bordure fine
                border_color=("#D3D3D3", "#4A4A4A")  # Couleur de bordure subtile
            )
            card.pack()
            card.pack_propagate(False)  # Empêcher le redimensionnement automatique
            
            # Padding interne pour l'espacement
            card_inner = ctk.CTkFrame(card, fg_color="transparent")
            card_inner.pack(fill="both", expand=True, padx=20, pady=20)
            
            card_title = ctk.CTkLabel(
                card_inner,
                text=title,
                font=ctk.CTkFont(size=18, weight="bold")
            )
            card_title.pack(pady=(0, 10))
            
            card_desc = ctk.CTkLabel(
                card_inner,
                text=description,
                font=ctk.CTkFont(size=12),
                text_color="gray",
                wraplength=card_size - 60,  # Largeur max pour le texte (carte - padding)
                justify="center"
            )
            card_desc.pack(pady=(0, 15))
            
            card_button = ctk.CTkButton(
                card_inner,
                text=button_text,
                command=command,
                width=150,
                state="normal" if enabled and self.is_setup_ok() else "disabled",
                fg_color=button_color if enabled and self.is_setup_ok() else "gray",
                hover_color=button_hover if enabled and self.is_setup_ok() else "gray"
            )
            card_button.pack(pady=(0, 0))
            
            return card_frame
        
        # Créer les cartes dans la zone centrale - organisées par lignes (2 cartes max par ligne)
        # Première ligne : Import et Générateur CSV
        first_row_cards = []
        
        # Card Import
        first_row_cards.append({
            'title': "📥 Import",
            'description': "Importez des produits depuis les fournisseurs configurés",
            'button_text': "Ouvrir",
            'command': self.open_import,
            'button_color': "green",
            'button_hover': "darkgreen",
            'enabled': True
        })
        
        # Card Générateur CSV
        first_row_cards.append({
            'title': "📄 Générateur CSV",
            'description': "Générez des CSV Shopify personnalisés en sélectionnant les champs et catégories",
            'button_text': "Ouvrir",
            'command': self.open_csv_generator,
            'button_color': "orange",
            'button_hover': "darkorange",
            'enabled': True
        })
        
        # Créer la première rangée de cartes
        first_row_frame = ctk.CTkFrame(cards_wrapper)
        first_row_frame.pack(pady=10, fill="x", anchor="w")
        
        for card_info in first_row_cards:
            create_card(
                first_row_frame,
                card_info['title'],
                card_info['description'],
                card_info['button_text'],
                card_info['command'],
                card_info.get('button_color'),
                card_info.get('button_hover'),
                card_info.get('enabled', True)
            )
        
        # Deuxième ligne : Visualiseur CSV et Éditeur IA
        second_row_cards = []
        
        # Card Visualiseur CSV (si disponible)
        if VIEWER_AVAILABLE:
            second_row_cards.append({
                'title': "📋 Visualiseur CSV",
                'description': "Visualisez et sélectionnez des produits depuis un CSV Shopify",
                'button_text': "Ouvrir",
                'command': self.open_viewer,
                'button_color': ["#3B8ED0", "#1F6AA5"],
                'button_hover': ["#36719F", "#144870"],
                'enabled': True
            })
        
        # Card Éditeur IA
        second_row_cards.append({
            'title': "🤖 Éditeur IA",
            'description': "Modifiez les descriptions et optimisez les champs Google Shopping avec l'IA",
            'button_text': "Ouvrir",
            'command': self.open_ai_editor,
            'button_color': "purple",
            'button_hover': "darkviolet",
            'enabled': True
        })
        
        # Créer la deuxième rangée de cartes
        if second_row_cards:
            second_row_frame = ctk.CTkFrame(cards_wrapper)
            second_row_frame.pack(pady=10, fill="x", anchor="w")
            
            for card_info in second_row_cards:
                create_card(
                    second_row_frame,
                    card_info['title'],
                    card_info['description'],
                    card_info['button_text'],
                    card_info['command'],
                    card_info.get('button_color'),
                    card_info.get('button_hover'),
                    card_info.get('enabled', True)
                )
    
    def open_config(self):
        """Ouvre la fenêtre de configuration."""
        # Vérifier que le setup est OK
        if not self.is_setup_ok():
            return
        
        if self.config_window is None or not self.config_window.winfo_exists():
            self.config_window = ConfigWindow(self)
            self.config_window.protocol("WM_DELETE_WINDOW", self.on_config_close)
        else:
            self.config_window.lift()
    
    def on_config_close(self):
        """Appelé quand la fenêtre de configuration est fermée."""
        if self.config_window:
            self.config_window.destroy()
        self.config_window = None
    
    def open_csv_config(self):
        """Ouvre la fenêtre de configuration CSV."""
        # Vérifier que le setup est OK
        if not self.is_setup_ok():
            return
        
        if self.csv_config_window is None or not self.csv_config_window.winfo_exists():
            self.csv_config_window = CSVConfigWindow(self)
            self.csv_config_window.protocol("WM_DELETE_WINDOW", self.on_csv_config_close)
        else:
            self.csv_config_window.lift()
    
    def on_csv_config_close(self):
        """Appelé quand la fenêtre de configuration CSV est fermée."""
        if self.csv_config_window:
            self.csv_config_window.destroy()
        self.csv_config_window = None
    
    def open_import(self):
        """Ouvre la fenêtre d'import."""
        # Vérifier que le setup est OK
        if not self.is_setup_ok():
            return
        
        if self.import_window is None or not self.import_window.winfo_exists():
            self.import_window = ImportWindow(self)
            self.import_window.protocol("WM_DELETE_WINDOW", self.on_import_close)
        else:
            self.import_window.lift()
    
    def is_setup_ok(self) -> bool:
        """Vérifie si le setup est OK (toutes les dépendances installées)."""
        if getattr(sys, "frozen", False):
            return True
        # Vérifier Python, pip et Chrome
        python_ok, _ = self.setup_checker.check_python_version()
        pip_ok, _ = self.setup_checker.check_pip()
        chrome_ok, _ = self.setup_checker.check_chrome()
        
        # Vérifier aussi que tous les packages sont installés
        if pip_ok:
            packages_ok, _, _ = self.setup_checker.check_packages()
            return python_ok and pip_ok and chrome_ok and packages_ok
        
        return python_ok and pip_ok and chrome_ok
    
    def on_import_close(self):
        """Appelé quand la fenêtre d'import est fermée."""
        if self.import_window:
            # Désélectionner toutes les catégories avant de fermer
            self.import_window.deselect_all_categories()
            self.import_window.destroy()
        self.import_window = None
    
    def open_viewer(self):
        """Ouvre la fenêtre de visualisation CSV."""
        # Vérifier que le setup est OK
        if not self.is_setup_ok():
            return
        
        if not VIEWER_AVAILABLE:
            import tkinter.messagebox as messagebox
            messagebox.showerror(
                "Fonctionnalité non disponible",
                "Le visualiseur CSV nécessite tkinterweb.\n\n"
                "Veuillez installer tkinterweb avec:\n"
                "pip install tkinterweb"
            )
            return
        
        if self.viewer_window is None or not self.viewer_window.winfo_exists():
            self.viewer_window = ViewerWindow(self)
            self.viewer_window.protocol("WM_DELETE_WINDOW", self.on_viewer_close)
        else:
            self.viewer_window.lift()
    
    def on_viewer_close(self):
        """Appelé quand la fenêtre de visualisation est fermée."""
        if self.viewer_window:
            self.viewer_window.destroy()
        self.viewer_window = None
    
    def open_ai_editor(self):
        """Ouvre la fenêtre d'édition IA."""
        # Vérifier que le setup est OK
        if not self.is_setup_ok():
            return
        
        if self.ai_editor_window is None or not self.ai_editor_window.winfo_exists():
            self.ai_editor_window = AIEditorWindow(self)
            self.ai_editor_window.protocol("WM_DELETE_WINDOW", self.on_ai_editor_close)
        else:
            self.ai_editor_window.lift()
    
    def on_ai_editor_close(self):
        """Appelé quand la fenêtre d'édition IA est fermée."""
        if self.ai_editor_window:
            self.ai_editor_window.destroy()
        self.ai_editor_window = None
    
    def open_csv_generator(self):
        """Ouvre la fenêtre de génération CSV."""
        # Vérifier que le setup est OK
        if not self.is_setup_ok():
            return
        
        if self.csv_generator_window is None or not self.csv_generator_window.winfo_exists():
            from csv_generator.gui.window import CSVGeneratorWindow
            self.csv_generator_window = CSVGeneratorWindow(self)
            self.csv_generator_window.protocol("WM_DELETE_WINDOW", self.on_csv_generator_close)
        else:
            self.csv_generator_window.lift()
    
    def on_csv_generator_close(self):
        """Appelé quand la fenêtre de génération CSV est fermée."""
        if self.csv_generator_window:
            self.csv_generator_window.destroy()
        self.csv_generator_window = None
    
    def open_cleanup(self):
        """Ouvre la fenêtre de nettoyage."""
        # Vérifier que le setup est OK
        if not self.is_setup_ok():
            return
        
        if self.cleanup_window is None or not self.cleanup_window.winfo_exists():
            self.cleanup_window = CleanupWindow(self)
            self.cleanup_window.protocol("WM_DELETE_WINDOW", self.on_cleanup_close)
        else:
            self.cleanup_window.lift()
    
    def on_cleanup_close(self):
        """Appelé quand la fenêtre de nettoyage est fermée."""
        if self.cleanup_window:
            self.cleanup_window.destroy()
        self.cleanup_window = None
    
    def open_setup(self):
        """Ouvre la fenêtre de setup."""
        if self.setup_window is None or not self.setup_window.winfo_exists():
            self.setup_window = SetupWindow(self)
            self.setup_window.protocol("WM_DELETE_WINDOW", self.on_setup_close)
        else:
            self.setup_window.lift()
    
    def on_setup_close(self):
        """Appelé quand la fenêtre de setup est fermée."""
        if self.setup_window:
            self.setup_window.destroy()
        self.setup_window = None
        # Re-vérifier l'état du setup après fermeture
        # Attendre un peu pour que les packages soient bien installés
        self.after(500, self.check_setup_status)
        # Si on est sur la page d'accueil, la rafraîchir pour mettre à jour les boutons des cartes
        self.after(600, self.refresh_home_if_needed)
    
    def refresh_home_if_needed(self):
        """Rafraîchit la page d'accueil si elle est affichée."""
        # Vérifier si la page d'accueil est actuellement affichée
        # En regardant si le content_frame contient le titre "Bienvenue"
        for widget in self.content_frame.winfo_children():
            if isinstance(widget, ctk.CTkLabel):
                if widget.cget("text") == "Bienvenue":
                    # Rafraîchir la page d'accueil
                    self.show_home()
                    break
    
    def check_setup_status(self):
        """Vérifie l'état du setup et active/désactive les boutons en conséquence."""
        # Vérifier toutes les dépendances (Python, pip, Chrome ET packages)
        setup_ok = self.is_setup_ok()
        
        # Activer/désactiver tous les boutons sauf Setup et Accueil
        buttons_to_disable = [
            self.config_button,
            self.csv_config_button,
            self.cleanup_button,
            self.home_button,
            self.about_button,
        ]
        
        for button in buttons_to_disable:
            if button:
                if setup_ok:
                    # Réactiver le bouton avec ses couleurs par défaut
                    if button == self.config_button or button == self.csv_config_button:
                        button.configure(
                            state="normal",
                            fg_color=["#3B8ED0", "#1F6AA5"],  # Couleur par défaut bleue
                            hover_color=["#36719F", "#144870"]
                        )
                    else:
                        # Pour les autres boutons (Accueil, À propos), utiliser les couleurs par défaut de CustomTkinter
                        button.configure(
                            state="normal",
                            fg_color=["#3B8ED0", "#1F6AA5"],  # Couleur par défaut bleue
                            hover_color=["#36719F", "#144870"]
                        )
                else:
                    # Désactiver le bouton
                    button.configure(
                        state="disabled",
                        fg_color="gray",
                        hover_color="gray"
                    )
    
    def show_about(self):
        """Affiche la page À propos."""
        # Vérifier que le setup est OK
        if not self.is_setup_ok():
            return
        
        self.clear_content()
        
        # Titre
        title = ctk.CTkLabel(
            self.content_frame,
            text="À propos",
            font=ctk.CTkFont(size=32, weight="bold")
        )
        title.pack(pady=(40, 20))
        
        # Informations
        info_text = """
        Scrapers Shopify - Interface Graphique
        
        Version: 1.0.0
        
        Cette application permet d'importer des produits depuis différents
        fournisseurs (Garnier-Thiebaut, Artiga, Cristel) et de générer des
        fichiers CSV compatibles avec Shopify.
        
        Fonctionnalités:
        • Configuration des identifiants par fournisseur
        • Sélection de catégories et sous-catégories
        • Import avec barre de progression en temps réel
        • Génération de fichiers CSV Shopify
        
        Développé avec Python et CustomTkinter
        """
        
        info_label = ctk.CTkLabel(
            self.content_frame,
            text=info_text,
            font=ctk.CTkFont(size=12),
            justify="left",
            wraplength=600
        )
        info_label.pack(pady=20, padx=40)
    
    def on_closing(self):
        """Appelé quand l'utilisateur ferme l'application."""
        # Fermer toutes les fenêtres ouvertes
        if self.config_window:
            self.config_window.destroy()
        if self.csv_config_window:
            self.csv_config_window.destroy()
        if self.import_window:
            self.import_window.destroy()
        if self.cleanup_window:
            self.cleanup_window.destroy()
        if self.setup_window:
            self.setup_window.destroy()
        if self.viewer_window:
            self.viewer_window.destroy()
        if self.ai_editor_window:
            self.ai_editor_window.destroy()
        if self.csv_generator_window:
            self.csv_generator_window.destroy()
        
        # Supprimer le répertoire outputs si l'option est activée
        if get_config('delete_outputs_on_close', False):
            remove_outputs_directory()
        
        # Fermer l'application
        self.destroy()

