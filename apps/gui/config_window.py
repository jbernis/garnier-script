"""
Fenêtre de configuration pour gérer le fichier .env.
"""

import customtkinter as ctk
from typing import Dict, Optional
import sys
import os

# Ajouter le répertoire parent au path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.env_manager import EnvManager
from utils.app_config import load_config, save_config as save_app_config


class ConfigWindow(ctk.CTkToplevel):
    """Fenêtre de configuration pour gérer le fichier .env."""
    
    def __init__(self, parent):
        super().__init__(parent)
        
        self.title("Configuration")
        self.geometry("800x700")
        self.resizable(True, True)
        
        # Configuration CustomTkinter
        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("blue")
        
        # EnvManager
        self.env_manager = EnvManager()
        
        # Variables pour stocker les entrées
        self.entries: Dict[str, Dict[str, ctk.CTkEntry]] = {}
        
        # Variables pour les options de l'application
        self.delete_outputs_var = ctk.BooleanVar(value=False)
        
        # Frame principal avec scrollbar
        main_frame = ctk.CTkScrollableFrame(self)
        main_frame.pack(fill="both", expand=True, padx=20, pady=20)
        
        # Titre
        title_label = ctk.CTkLabel(
            main_frame,
            text="Configuration des fournisseurs",
            font=ctk.CTkFont(size=24, weight="bold")
        )
        title_label.pack(pady=(0, 30))
        
        # Créer les sections pour chaque fournisseur
        self.create_garnier_section(main_frame)
        self.create_artiga_section(main_frame)
        self.create_cristel_section(main_frame)
        self.create_app_settings_section(main_frame)
        
        # Frame pour les boutons
        button_frame = ctk.CTkFrame(self)
        button_frame.pack(fill="x", padx=20, pady=20)
        
        # Bouton Sauvegarder
        save_button = ctk.CTkButton(
            button_frame,
            text="Sauvegarder",
            command=self.save_config,
            width=150,
            height=30
        )
        save_button.pack(side="left", padx=10)
        
        # Bouton Annuler
        cancel_button = ctk.CTkButton(
            button_frame,
            text="Annuler",
            command=self.destroy,
            width=150,
            height=30,
            fg_color="gray",
            hover_color="darkgray"
        )
        cancel_button.pack(side="right", padx=10)
        
        # Message de statut
        self.status_label = ctk.CTkLabel(
            button_frame,
            text="",
            font=ctk.CTkFont(size=12)
        )
        self.status_label.pack(side="left", padx=20)
        
        # Charger les valeurs existantes
        self.load_config()
        self.load_app_config()
        
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
            self.update_idletasks()
            self.lift()
            self.focus_force()
            self.attributes('-topmost', True)
            self.after(150, lambda: self.attributes('-topmost', False))
        except Exception:
            pass
    
    def create_garnier_section(self, parent):
        """Crée la section de configuration pour Garnier."""
        section_frame = ctk.CTkFrame(parent)
        section_frame.pack(fill="x", pady=(0, 20))
        
        # Titre de la section
        title = ctk.CTkLabel(
            section_frame,
            text="Garnier-Thiebaut",
            font=ctk.CTkFont(size=18, weight="bold")
        )
        title.pack(anchor="w", padx=20, pady=(20, 15))
        
        # Formulaire
        form_frame = ctk.CTkFrame(section_frame)
        form_frame.pack(fill="x", padx=20, pady=(0, 20))
        
        self.entries['garnier'] = {}
        
        # Base URL
        self.create_field(form_frame, 'garnier', 'BASE_URL_GARNIER', 'URL de base:', 'https://garnier-thiebaut.adsi.me')
        
        # Username
        self.create_field(form_frame, 'garnier', 'USERNAME', 'Nom d\'utilisateur:', '')
        
        # Password (masqué)
        self.create_field(form_frame, 'garnier', 'PASSWORD', 'Mot de passe:', '', is_password=True)
    
    def create_artiga_section(self, parent):
        """Crée la section de configuration pour Artiga."""
        section_frame = ctk.CTkFrame(parent)
        section_frame.pack(fill="x", pady=(0, 20))
        
        # Titre de la section
        title = ctk.CTkLabel(
            section_frame,
            text="Artiga",
            font=ctk.CTkFont(size=18, weight="bold")
        )
        title.pack(anchor="w", padx=20, pady=(20, 15))
        
        # Formulaire
        form_frame = ctk.CTkFrame(section_frame)
        form_frame.pack(fill="x", padx=20, pady=(0, 20))
        
        self.entries['artiga'] = {}
        
        # Base URL
        self.create_field(form_frame, 'artiga', 'ARTIGA_BASE_URL', 'URL de base:', 'https://www.artiga.fr')
    
    def create_cristel_section(self, parent):
        """Crée la section de configuration pour Cristel."""
        section_frame = ctk.CTkFrame(parent)
        section_frame.pack(fill="x", pady=(0, 20))
        
        # Titre de la section
        title = ctk.CTkLabel(
            section_frame,
            text="Cristel",
            font=ctk.CTkFont(size=18, weight="bold")
        )
        title.pack(anchor="w", padx=20, pady=(20, 15))
        
        # Formulaire
        form_frame = ctk.CTkFrame(section_frame)
        form_frame.pack(fill="x", padx=20, pady=(0, 20))
        
        self.entries['cristel'] = {}
        
        # Base URL
        self.create_field(form_frame, 'cristel', 'CRISTEL_BASE_URL', 'URL de base:', 'https://www.cristel.com')
    
    def create_app_settings_section(self, parent):
        """Crée la section des paramètres de l'application."""
        section_frame = ctk.CTkFrame(parent)
        section_frame.pack(fill="x", pady=(0, 20))
        
        # Titre de la section
        title = ctk.CTkLabel(
            section_frame,
            text="Paramètres de l'application",
            font=ctk.CTkFont(size=18, weight="bold")
        )
        title.pack(anchor="w", padx=20, pady=(20, 15))
        
        # Formulaire
        form_frame = ctk.CTkFrame(section_frame)
        form_frame.pack(fill="x", padx=20, pady=(0, 20))
        
        # Checkbox pour supprimer outputs à la fermeture
        checkbox_frame = ctk.CTkFrame(form_frame, fg_color="transparent")
        checkbox_frame.pack(fill="x", padx=10, pady=10)
        
        self.delete_outputs_checkbox = ctk.CTkCheckBox(
            checkbox_frame,
            text="Supprimer le répertoire 'outputs' à la fermeture de l'application",
            variable=self.delete_outputs_var,
            font=ctk.CTkFont(size=12)
        )
        self.delete_outputs_checkbox.pack(side="left", padx=10)
        
        # Label d'aide
        help_label = ctk.CTkLabel(
            checkbox_frame,
            text="(Si activé, le répertoire 'outputs' sera supprimé automatiquement à la fermeture)",
            font=ctk.CTkFont(size=10),
            text_color="gray"
        )
        help_label.pack(side="left", padx=(10, 0))
    
    def create_field(self, parent, provider: str, key: str, label: str, default: str = '', is_password: bool = False):
        """Crée un champ de formulaire."""
        field_frame = ctk.CTkFrame(parent)
        field_frame.pack(fill="x", padx=10, pady=10)
        
        # Label
        label_widget = ctk.CTkLabel(
            field_frame,
            text=label,
            font=ctk.CTkFont(size=12),
            width=200,
            anchor="w"
        )
        label_widget.pack(side="left", padx=10)
        
        # Entry
        if is_password:
            entry = ctk.CTkEntry(
                field_frame,
                placeholder_text=default,
                show="*",
                width=400
            )
        else:
            entry = ctk.CTkEntry(
                field_frame,
                placeholder_text=default,
                width=400
            )
        entry.pack(side="left", padx=10, fill="x", expand=True)
        
        self.entries[provider][key] = entry
    
    def load_config(self):
        """Charge la configuration depuis le fichier .env."""
        # Charger les valeurs pour Garnier
        garnier_vars = self.env_manager.get_by_provider("garnier")
        if 'BASE_URL_GARNIER' in self.entries.get('garnier', {}):
            self.entries['garnier']['BASE_URL_GARNIER'].insert(0, garnier_vars.get('BASE_URL_GARNIER', ''))
        if 'USERNAME' in self.entries.get('garnier', {}):
            self.entries['garnier']['USERNAME'].insert(0, garnier_vars.get('USERNAME', ''))
        if 'PASSWORD' in self.entries.get('garnier', {}):
            self.entries['garnier']['PASSWORD'].insert(0, garnier_vars.get('PASSWORD', ''))
        
        # Charger les valeurs pour Artiga
        artiga_vars = self.env_manager.get_by_provider("artiga")
        if 'ARTIGA_BASE_URL' in self.entries.get('artiga', {}):
            self.entries['artiga']['ARTIGA_BASE_URL'].insert(0, artiga_vars.get('ARTIGA_BASE_URL', ''))
        
        # Charger les valeurs pour Cristel
        cristel_vars = self.env_manager.get_by_provider("cristel")
        if 'CRISTEL_BASE_URL' in self.entries.get('cristel', {}):
            self.entries['cristel']['CRISTEL_BASE_URL'].insert(0, cristel_vars.get('CRISTEL_BASE_URL', ''))
    
    def load_app_config(self):
        """Charge la configuration de l'application."""
        config = load_config()
        self.delete_outputs_var.set(config.get('delete_outputs_on_close', False))
    
    def save_config(self):
        """Sauvegarde la configuration dans le fichier .env."""
        try:
            # Récupérer les valeurs depuis les champs
            for provider, fields in self.entries.items():
                provider_vars = {}
                for key, entry in fields.items():
                    value = entry.get().strip()
                    if value:
                        provider_vars[key] = value
                
                if provider_vars:
                    self.env_manager.set_provider_vars(provider, provider_vars)
            
            # Sauvegarder la configuration .env
            env_saved = self.env_manager.save()
            
            # Sauvegarder la configuration de l'application
            app_config = {
                'delete_outputs_on_close': self.delete_outputs_var.get()
            }
            save_app_config(app_config)
            
            # Afficher le message de statut
            if env_saved:
                self.status_label.configure(text="✓ Configuration sauvegardée", text_color="green")
                self.after(2000, lambda: self.status_label.configure(text=""))
            else:
                self.status_label.configure(text="✗ Erreur lors de la sauvegarde", text_color="red")
        
        except Exception as e:
            self.status_label.configure(text=f"✗ Erreur: {e}", text_color="red")

