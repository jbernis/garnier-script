"""
Fenêtre d'édition IA pour modifier les descriptions et optimiser les champs Google Shopping.
"""

import customtkinter as ctk
from typing import Optional, Dict, Set, Callable
import pandas as pd
import os
import sys
import threading
import json
import logging
from pathlib import Path
from tkinter import filedialog, messagebox

logger = logging.getLogger(__name__)

# Ajouter le répertoire parent au path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.ai_providers import get_provider, AIProviderError
from utils.csv_ai_processor import CSVAIProcessor
from utils.google_shopping_optimizer import GoogleShoppingOptimizer
from utils.env_manager import EnvManager
from apps.gui.progress_window import ProgressWindow


class AIEditorWindow(ctk.CTkToplevel):
    """Fenêtre d'édition IA pour les fichiers CSV Shopify."""
    
    def __init__(self, parent):
        super().__init__(parent)
        
        self.title("Éditeur IA - CSV Shopify")
        self.geometry("1000x800")
        self.resizable(True, True)
        
        # Configuration CustomTkinter
        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("blue")
        
        # Variables
        self.env_manager = EnvManager()
        self.csv_path: Optional[str] = None
        self.df: Optional[pd.DataFrame] = None
        self.products: Dict[str, Dict] = {}
        self.selected_handles: Set[str] = set()
        self.progress_window: Optional[ProgressWindow] = None
        
        # Frame principal avec scrollbar
        main_frame = ctk.CTkScrollableFrame(self)
        main_frame.pack(fill="both", expand=True, padx=20, pady=20)
        
        # Titre
        title_label = ctk.CTkLabel(
            main_frame,
            text="🤖 Éditeur IA",
            font=ctk.CTkFont(size=24, weight="bold")
        )
        title_label.pack(pady=(0, 30))
        
        # Section 1: Configuration
        self.create_config_section(main_frame)
        
        # Section 2: Chargement CSV
        self.create_csv_section(main_frame)
        
        # Section 3: Sélection des produits
        self.create_selection_section(main_frame)
        
        # Section 4: Options de traitement
        self.create_options_section(main_frame)
        
        # Section 5: Boutons d'action
        self.create_action_section(main_frame)
        
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
    
    def create_config_section(self, parent):
        """Crée la section de configuration de l'IA."""
        config_frame = ctk.CTkFrame(parent)
        config_frame.pack(fill="x", pady=(0, 20))
        
        config_title = ctk.CTkLabel(
            config_frame,
            text="Configuration IA",
            font=ctk.CTkFont(size=16, weight="bold")
        )
        config_title.pack(anchor="w", padx=20, pady=(20, 10))
        
        # Fournisseur IA
        provider_frame = ctk.CTkFrame(config_frame)
        provider_frame.pack(fill="x", padx=20, pady=(0, 10))
        
        provider_label = ctk.CTkLabel(
            provider_frame,
            text="Fournisseur IA:",
            width=150
        )
        provider_label.pack(side="left", padx=10)
        
        self.provider_var = ctk.StringVar(value="openai")
        provider_dropdown = ctk.CTkComboBox(
            provider_frame,
            values=["openai", "claude", "gemini"],
            variable=self.provider_var,
            command=self.on_provider_changed,
            width=200
        )
        provider_dropdown.pack(side="left", padx=10)
        
        # Clé API
        api_key_frame = ctk.CTkFrame(config_frame)
        api_key_frame.pack(fill="x", padx=20, pady=(0, 10))
        
        api_key_label = ctk.CTkLabel(
            api_key_frame,
            text="Clé API:",
            width=150
        )
        api_key_label.pack(side="left", padx=10)
        
        self.api_key_var = ctk.StringVar(value="")
        self.api_key_entry = ctk.CTkEntry(
            api_key_frame,
            textvariable=self.api_key_var,
            width=400
        )
        self.api_key_entry.pack(side="left", padx=10, fill="x", expand=True)
        self.api_key_entry.bind('<FocusIn>', self.on_api_key_focus_in)
        self.api_key_entry.bind('<FocusOut>', self.on_api_key_focus_out)
        self.api_key_entry.bind('<KeyRelease>', self.on_api_key_typing)
        self.api_key_actual = ""  # Stocker la vraie clé API
        self.is_obfuscated = False  # Indicateur si la clé affichée est obfusquée
        
        # Bouton charger depuis .env
        load_env_button = ctk.CTkButton(
            api_key_frame,
            text="Charger depuis .env",
            command=self.load_api_key_from_env,
            width=150
        )
        load_env_button.pack(side="left", padx=10)
        
        # Bouton sauvegarder dans .env
        save_env_button = ctk.CTkButton(
            api_key_frame,
            text="Sauvegarder",
            command=self.save_api_key_to_env,
            width=120
        )
        save_env_button.pack(side="left", padx=10)
        
        # Modèle
        model_frame = ctk.CTkFrame(config_frame)
        model_frame.pack(fill="x", padx=20, pady=(0, 10))
        
        model_label = ctk.CTkLabel(
            model_frame,
            text="Modèle:",
            width=150
        )
        model_label.pack(side="left", padx=10)
        
        self.model_var = ctk.StringVar(value="")
        self.model_dropdown = ctk.CTkComboBox(
            model_frame,
            values=[],
            variable=self.model_var,
            width=400,
            state="disabled"
        )
        self.model_dropdown.pack(side="left", padx=10, fill="x", expand=True)
        
        # Bouton charger les modèles
        self.load_models_button = ctk.CTkButton(
            model_frame,
            text="Charger les modèles",
            command=self.load_models,
            width=150,
            state="disabled"
        )
        self.load_models_button.pack(side="left", padx=10)
        
        # Message de statut
        self.config_status_label = ctk.CTkLabel(
            config_frame,
            text="",
            font=ctk.CTkFont(size=11),
            text_color="gray"
        )
        self.config_status_label.pack(anchor="w", padx=20, pady=(0, 20))
        
        # Charger la clé depuis .env au démarrage
        self.load_api_key_from_env()
        
        # Charger le modèle par défaut
        self.load_default_model()
    
    def create_csv_section(self, parent):
        """Crée la section de chargement CSV."""
        csv_frame = ctk.CTkFrame(parent)
        csv_frame.pack(fill="x", pady=(0, 20))
        
        csv_title = ctk.CTkLabel(
            csv_frame,
            text="Fichier CSV",
            font=ctk.CTkFont(size=16, weight="bold")
        )
        csv_title.pack(anchor="w", padx=20, pady=(20, 10))
        
        # Bouton charger CSV
        load_csv_button = ctk.CTkButton(
            csv_frame,
            text="📁 Charger un fichier CSV",
            command=self.load_csv_file,
            width=250,
            height=40
        )
        load_csv_button.pack(side="left", padx=20, pady=(0, 20))
        
        # Info fichier
        self.csv_info_label = ctk.CTkLabel(
            csv_frame,
            text="Aucun fichier chargé",
            font=ctk.CTkFont(size=12),
            text_color="gray"
        )
        self.csv_info_label.pack(side="left", padx=20, pady=(0, 20))
    
    def create_selection_section(self, parent):
        """Crée la section de sélection des produits."""
        selection_frame = ctk.CTkFrame(parent)
        selection_frame.pack(fill="both", expand=True, pady=(0, 20))
        
        selection_title = ctk.CTkLabel(
            selection_frame,
            text="Sélection des produits",
            font=ctk.CTkFont(size=16, weight="bold")
        )
        selection_title.pack(anchor="w", padx=20, pady=(20, 10))
        
        # Checkbox "Traiter tous les produits"
        self.process_all_var = ctk.BooleanVar(value=True)
        process_all_checkbox = ctk.CTkCheckBox(
            selection_frame,
            text="Traiter tous les produits",
            variable=self.process_all_var,
            command=self.on_process_all_changed
        )
        process_all_checkbox.pack(anchor="w", padx=20, pady=(0, 10))
        
        # Liste des produits (scrollable)
        self.products_listbox_frame = ctk.CTkScrollableFrame(selection_frame)
        self.products_listbox_frame.pack(fill="both", expand=True, padx=20, pady=(0, 20))
        
        self.product_checkboxes: Dict[str, ctk.CTkCheckBox] = {}
        
        # Message initial
        self.empty_products_label = ctk.CTkLabel(
            self.products_listbox_frame,
            text="Chargez un fichier CSV pour voir les produits",
            font=ctk.CTkFont(size=12),
            text_color="gray"
        )
        self.empty_products_label.pack(pady=20)
    
    def create_options_section(self, parent):
        """Crée la section des options de traitement."""
        options_frame = ctk.CTkFrame(parent)
        options_frame.pack(fill="x", pady=(0, 20))
        
        options_title = ctk.CTkLabel(
            options_frame,
            text="Options de traitement",
            font=ctk.CTkFont(size=16, weight="bold")
        )
        options_title.pack(anchor="w", padx=20, pady=(20, 10))
        
        # Option 1: Modifier les descriptions
        self.modify_descriptions_var = ctk.BooleanVar(value=False)
        modify_desc_checkbox = ctk.CTkCheckBox(
            options_frame,
            text="Modifier les descriptions",
            variable=self.modify_descriptions_var,
            command=self.on_modify_descriptions_changed
        )
        modify_desc_checkbox.pack(anchor="w", padx=20, pady=(0, 10))
        
        # Champ prompt pour les descriptions
        prompt_frame = ctk.CTkFrame(options_frame)
        prompt_frame.pack(fill="x", padx=40, pady=(0, 10))
        
        prompt_label = ctk.CTkLabel(
            prompt_frame,
            text="Prompt pour les descriptions:",
            font=ctk.CTkFont(size=12)
        )
        prompt_label.pack(anchor="w", padx=10, pady=(10, 5))
        
        self.prompt_textbox = ctk.CTkTextbox(
            prompt_frame,
            height=100,
            state="disabled"
        )
        self.prompt_textbox.pack(fill="x", padx=10, pady=(0, 10))
        default_prompt = "Réécris la description de ce produit de manière plus engageante et optimisée pour la vente en ligne. Inclus les avantages principaux et un appel à l'action."
        self.prompt_textbox.insert("1.0", default_prompt)
        
        # Option 2: Optimiser Google Shopping
        self.optimize_google_var = ctk.BooleanVar(value=False)
        optimize_google_checkbox = ctk.CTkCheckBox(
            options_frame,
            text="Optimiser les champs Google Shopping",
            variable=self.optimize_google_var,
            command=self.on_optimize_google_changed
        )
        optimize_google_checkbox.pack(anchor="w", padx=20, pady=(10, 10))
        
        # Bouton configurer les champs Google
        config_google_button = ctk.CTkButton(
            options_frame,
            text="⚙️ Configurer les champs Google Shopping",
            command=self.open_google_config,
            width=300,
            state="disabled"
        )
        config_google_button.pack(anchor="w", padx=40, pady=(0, 20))
        self.config_google_button = config_google_button
    
    def create_action_section(self, parent):
        """Crée la section des boutons d'action."""
        action_frame = ctk.CTkFrame(parent)
        action_frame.pack(fill="x", pady=(0, 20))
        
        # Bouton démarrer
        self.start_button = ctk.CTkButton(
            action_frame,
            text="🚀 Démarrer le traitement",
            command=self.start_processing,
            width=250,
            height=50,
            fg_color="green",
            hover_color="darkgreen",
            state="disabled",
            font=ctk.CTkFont(size=16, weight="bold")
        )
        self.start_button.pack(side="left", padx=20, pady=20)
        
        # Message de statut
        self.status_label = ctk.CTkLabel(
            action_frame,
            text="",
            font=ctk.CTkFont(size=12),
            text_color="gray"
        )
        self.status_label.pack(side="left", padx=20, pady=20)
    
    def on_provider_changed(self, value):
        """Appelé quand le fournisseur IA change."""
        # Sauvegarder la clé actuelle si elle a été modifiée
        if not self.is_obfuscated and self.api_key_var.get().strip():
            current_key = self.api_key_var.get().strip()
            if current_key != self.api_key_actual:
                self.api_key_actual = current_key
        
        self.load_api_key_from_env()
        # Charger le modèle par défaut (qui va aussi mettre à jour la liste déroulante)
        self.load_default_model()
    
    def on_api_key_focus_in(self, event=None):
        """Appelé quand le champ API reçoit le focus."""
        # Si la clé est obfusquée, afficher la vraie clé pour l'édition
        if self.is_obfuscated and self.api_key_actual:
            self.api_key_var.set(self.api_key_actual)
            self.is_obfuscated = False
    
    def on_api_key_typing(self, event=None):
        """Appelé quand l'utilisateur tape dans le champ API."""
        # Si on tape, c'est qu'on entre une nouvelle clé (pas obfusquée)
        self.is_obfuscated = False
        api_key = self.api_key_var.get().strip()
        self.load_models_button.configure(state="normal" if api_key else "disabled")
    
    def on_api_key_focus_out(self, event=None):
        """Appelé quand le champ API perd le focus."""
        if not self.is_obfuscated:
            current_value = self.api_key_var.get().strip()
            if current_value:
                # Stocker la nouvelle clé
                self.api_key_actual = current_value
                # Obfusquer l'affichage
                obfuscated = self.obfuscate_api_key(current_value)
                self.api_key_var.set(obfuscated)
                self.is_obfuscated = True
                # Activer le bouton charger modèles
                self.load_models_button.configure(state="normal")
    
    def obfuscate_api_key(self, api_key: str) -> str:
        """Obfusque une clé API en montrant les 6 premiers et 5 derniers caractères."""
        if not api_key:
            return ""
        
        if len(api_key) <= 11:
            # Si la clé est trop courte, masquer tout sauf les premiers caractères
            if len(api_key) <= 6:
                return api_key[0] + "*" * (len(api_key) - 1) if len(api_key) > 1 else "*"
            else:
                return api_key[:3] + "*" * (len(api_key) - 3)
        
        first_part = api_key[:6]
        last_part = api_key[-5:]
        middle_part = "*" * (len(api_key) - 11)
        
        return f"{first_part}...{last_part}"
    
    def load_default_model(self):
        """Charge le modèle par défaut pour le fournisseur sélectionné."""
        provider = self.provider_var.get()
        
        default_models = {
            "openai": "gpt-4o-mini",
            "claude": "claude-haiku-4-5-20251001",
            "gemini": "gemini-1.5-flash"
        }
        
        default_model = default_models.get(provider, "")
        if default_model:
            # Toujours afficher le modèle par défaut dans la liste déroulante
            self.model_dropdown.configure(values=[default_model], state="readonly")
            self.model_var.set(default_model)
    
    def load_api_key_from_env(self):
        """Charge la clé API depuis le fichier .env."""
        provider = self.provider_var.get()
        
        key_map = {
            "openai": "OPENAI_API_KEY",
            "claude": "ANTHROPIC_API_KEY",
            "gemini": "GOOGLE_API_KEY"
        }
        
        key_name = key_map.get(provider)
        if key_name:
            api_key = self.env_manager.get(key_name)
            if api_key:
                self.api_key_actual = api_key
                obfuscated = self.obfuscate_api_key(api_key)
                self.api_key_var.set(obfuscated)
                self.is_obfuscated = True
                self.config_status_label.configure(
                    text=f"✓ Clé API chargée depuis .env",
                    text_color="green"
                )
                self.load_models_button.configure(state="normal")
            else:
                self.api_key_actual = ""
                self.api_key_var.set("")
                self.is_obfuscated = False
                self.config_status_label.configure(
                    text="⚠️ Aucune clé API trouvée dans .env",
                    text_color="orange"
                )
                self.load_models_button.configure(state="disabled")
    
    def save_api_key_to_env(self):
        """Sauvegarde la clé API dans le fichier .env."""
        provider = self.provider_var.get()
        
        # Récupérer la clé API actuelle
        current_value = self.api_key_var.get().strip()
        
        # Si c'est obfusquée, utiliser la vraie clé stockée
        if self.is_obfuscated and self.api_key_actual:
            api_key = self.api_key_actual
        # Sinon, utiliser la valeur actuelle (nouvelle clé entrée)
        else:
            api_key = current_value
        
        if not api_key:
            messagebox.showwarning("Attention", "La clé API ne peut pas être vide")
            return
        
        key_map = {
            "openai": "OPENAI_API_KEY",
            "claude": "ANTHROPIC_API_KEY",
            "gemini": "GOOGLE_API_KEY"
        }
        
        key_name = key_map.get(provider)
        if key_name:
            self.env_manager.set(key_name, api_key)
            if self.env_manager.save():
                self.api_key_actual = api_key
                obfuscated = self.obfuscate_api_key(api_key)
                self.api_key_var.set(obfuscated)
                self.is_obfuscated = True
                self.config_status_label.configure(
                    text=f"✓ Clé API sauvegardée dans .env",
                    text_color="green"
                )
            else:
                self.config_status_label.configure(
                    text="✗ Erreur lors de la sauvegarde",
                    text_color="red"
                )
    
    def load_models(self):
        """Charge les modèles disponibles depuis l'API."""
        provider = self.provider_var.get()
        
        # Récupérer la vraie clé API
        if self.is_obfuscated and self.api_key_actual:
            api_key = self.api_key_actual
        else:
            api_key = self.api_key_var.get().strip()
        
        if not api_key:
            messagebox.showerror("Erreur", "Veuillez entrer une clé API valide")
            return
        
        # Désactiver le bouton pendant le chargement
        self.load_models_button.configure(state="disabled", text="Chargement...")
        self.config_status_label.configure(
            text="Chargement des modèles...",
            text_color="#FFFF99"
        )
        
        def load_thread():
            try:
                from utils.ai_providers import get_provider
                
                # Créer un provider temporaire pour lister les modèles
                ai_provider = get_provider(provider, api_key=api_key)
                models = ai_provider.list_models()
                
                # Mettre à jour l'interface dans le thread principal
                self.after(0, lambda: self.models_loaded(models))
            
            except Exception as e:
                error_msg = str(e)
                logger.error(f"Erreur lors du chargement des modèles: {e}", exc_info=True)
                self.after(0, lambda: self.models_load_error(error_msg))
        
        threading.Thread(target=load_thread, daemon=True).start()
    
    def models_loaded(self, models: list[str]):
        """Appelé quand les modèles sont chargés."""
        if models:
            self.model_dropdown.configure(values=models, state="readonly")
            # Sélectionner le modèle par défaut s'il est dans la liste
            default_model = self.model_var.get()
            if default_model in models:
                self.model_var.set(default_model)
            elif models:
                self.model_var.set(models[0])
            
            self.config_status_label.configure(
                text=f"✓ {len(models)} modèle(s) chargé(s)",
                text_color="green"
            )
        else:
            self.config_status_label.configure(
                text="⚠️ Aucun modèle trouvé",
                text_color="orange"
            )
        
        self.load_models_button.configure(state="normal", text="Charger les modèles")
    
    def models_load_error(self, error_msg: str):
        """Appelé en cas d'erreur lors du chargement des modèles."""
        self.config_status_label.configure(
            text=f"✗ Erreur: {error_msg[:50]}...",
            text_color="red"
        )
        self.load_models_button.configure(state="normal", text="Charger les modèles")
        # Utiliser les modèles par défaut depuis la config
        self.load_default_model()
    
    def load_csv_file(self):
        """Charge un fichier CSV."""
        file_path = filedialog.askopenfilename(
            title="Sélectionner un fichier CSV Shopify",
            filetypes=[("Fichiers CSV", "*.csv"), ("Tous les fichiers", "*.*")]
        )
        
        if file_path:
            try:
                self.csv_path = file_path
                self.df = pd.read_csv(file_path, encoding='utf-8', dtype=str, keep_default_na=False)
                
                # Vérifier le format
                if 'Handle' not in self.df.columns:
                    messagebox.showerror("Erreur", "Le fichier CSV ne semble pas être au format Shopify.\nLa colonne 'Handle' est manquante.")
                    return
                
                # Grouper par Handle
                self.products = {}
                unique_handles = self.df['Handle'].unique()
                
                for handle in unique_handles:
                    if pd.isna(handle) or handle == '':
                        continue
                    
                    handle_rows = self.df[self.df['Handle'] == handle]
                    first_row = handle_rows.iloc[0]
                    
                    self.products[str(handle)] = {
                        'handle': str(handle),
                        'title': first_row.get('Title', ''),
                        'vendor': first_row.get('Vendor', ''),
                        'type': first_row.get('Type', '')
                    }
                
                # Mettre à jour l'interface
                self.update_csv_info()
                self.update_products_list()
                self.update_start_button_state()
                
            except Exception as e:
                messagebox.showerror("Erreur", f"Erreur lors du chargement du CSV:\n{str(e)}")
                logger.error(f"Erreur lors du chargement du CSV: {e}", exc_info=True)
    
    def update_csv_info(self):
        """Met à jour les informations sur le CSV chargé."""
        if self.csv_path and self.products:
            filename = os.path.basename(self.csv_path)
            count = len(self.products)
            self.csv_info_label.configure(
                text=f"✓ {filename} - {count} produit(s)",
                text_color="green"
            )
        else:
            self.csv_info_label.configure(
                text="Aucun fichier chargé",
                text_color="gray"
            )
    
    def update_products_list(self):
        """Met à jour la liste des produits."""
        # Nettoyer la liste existante
        for widget in self.products_listbox_frame.winfo_children():
            widget.destroy()
        
        self.product_checkboxes.clear()
        
        if not self.products:
            self.empty_products_label = ctk.CTkLabel(
                self.products_listbox_frame,
                text="Aucun produit disponible",
                font=ctk.CTkFont(size=12),
                text_color="gray"
            )
            self.empty_products_label.pack(pady=20)
            return
        
        # Créer les checkboxes
        for handle, product in self.products.items():
            var = ctk.BooleanVar(value=False)
            checkbox = ctk.CTkCheckBox(
                self.products_listbox_frame,
                text=f"{product['title']} ({handle})",
                variable=var,
                command=lambda h=handle: self.on_product_selection_changed(h)
            )
            checkbox.pack(anchor="w", padx=10, pady=2)
            self.product_checkboxes[handle] = {'var': var, 'checkbox': checkbox}
    
    def on_process_all_changed(self):
        """Appelé quand la checkbox 'Traiter tous' change."""
        process_all = self.process_all_var.get()
        
        # Désactiver/activer les checkboxes individuelles
        for handle, data in self.product_checkboxes.items():
            data['checkbox'].configure(state="normal" if not process_all else "disabled")
            if process_all:
                data['var'].set(False)
        
        self.update_start_button_state()
    
    def on_product_selection_changed(self, handle: str):
        """Appelé quand la sélection d'un produit change."""
        if not self.process_all_var.get():
            # Mettre à jour le set de sélection
            if self.product_checkboxes[handle]['var'].get():
                self.selected_handles.add(handle)
            else:
                self.selected_handles.discard(handle)
        
        self.update_start_button_state()
    
    def on_modify_descriptions_changed(self):
        """Appelé quand l'option 'Modifier descriptions' change."""
        enabled = self.modify_descriptions_var.get()
        self.prompt_textbox.configure(state="normal" if enabled else "disabled")
        self.update_start_button_state()
    
    def on_optimize_google_changed(self):
        """Appelé quand l'option 'Optimiser Google Shopping' change."""
        enabled = self.optimize_google_var.get()
        self.config_google_button.configure(state="normal" if enabled else "disabled")
        self.update_start_button_state()
    
    def open_google_config(self):
        """Ouvre la fenêtre de configuration Google Shopping."""
        # Pour l'instant, on affiche juste un message
        # TODO: Créer une fenêtre dédiée pour configurer les champs Google
        messagebox.showinfo(
            "Configuration Google Shopping",
            "La configuration des champs Google Shopping se fait via le fichier ai_config.json.\n\n"
            "Vous pouvez modifier ce fichier pour activer/désactiver les champs à optimiser."
        )
    
    def update_start_button_state(self):
        """Met à jour l'état du bouton Démarrer."""
        # Vérifier les conditions
        has_csv = self.csv_path is not None and len(self.products) > 0
        has_api_key = bool(self.api_key_var.get().strip())
        has_option = self.modify_descriptions_var.get() or self.optimize_google_var.get()
        
        # Vérifier la sélection
        if not self.process_all_var.get():
            has_selection = len(self.selected_handles) > 0
        else:
            has_selection = True
        
        # Vérifier le prompt si modification descriptions
        if self.modify_descriptions_var.get():
            prompt = self.prompt_textbox.get("1.0", "end-1c").strip()
            has_prompt = bool(prompt)
        else:
            has_prompt = True
        
        enabled = has_csv and has_api_key and has_option and has_selection and has_prompt
        
        self.start_button.configure(state="normal" if enabled else "disabled")
    
    def start_processing(self):
        """Démarre le traitement."""
        # Vérifier les prérequis
        if not self.csv_path:
            messagebox.showerror("Erreur", "Veuillez charger un fichier CSV")
            return
        
        api_key = self.api_key_var.get().strip()
        if not api_key:
            messagebox.showerror("Erreur", "Veuillez entrer une clé API")
            return
        
        provider = self.provider_var.get()
        
        # Vérifier les options
        modify_descriptions = self.modify_descriptions_var.get()
        optimize_google = self.optimize_google_var.get()
        
        if not modify_descriptions and not optimize_google:
            messagebox.showerror("Erreur", "Veuillez sélectionner au moins une option de traitement")
            return
        
        # Récupérer la sélection
        if self.process_all_var.get():
            selected_handles = None
        else:
            selected_handles = self.selected_handles.copy()
        
        # Récupérer la vraie clé API
        if self.is_obfuscated and self.api_key_actual:
            api_key = self.api_key_actual
        else:
            api_key = self.api_key_var.get().strip()
        
        # Récupérer le modèle sélectionné
        model = self.model_var.get()
        
        # Créer le provider IA
        try:
            ai_provider = get_provider(provider, api_key=api_key, model=model)
        except AIProviderError as e:
            messagebox.showerror("Erreur", f"Erreur lors de l'initialisation du fournisseur IA:\n{str(e)}")
            return
        
        # Ouvrir la fenêtre de progression
        self.progress_window = ProgressWindow(self, "Traitement IA")
        
        # Démarrer le traitement dans un thread
        def process_thread():
            try:
                success = False
                output_path = None
                error = None
                temp_output = None
                csv_to_optimize = self.csv_path
                
                # Traitement 1: Modifier les descriptions
                if modify_descriptions:
                    prompt = self.prompt_textbox.get("1.0", "end-1c").strip()
                    
                    processor = CSVAIProcessor(ai_provider)
                    
                    def progress_cb(msg, current, total):
                        if self.progress_window and not self.progress_window.is_cancelled:
                            self.progress_window.after(0, lambda: self.progress_window.update_progress(msg, current, total))
                    
                    def log_cb(msg):
                        if self.progress_window:
                            self.progress_window.after(0, lambda: self.progress_window.add_log(msg))
                    
                    def cancel_cb():
                        return self.progress_window.is_cancelled if self.progress_window else False
                    
                    # Générer un chemin de sortie temporaire si on optimise aussi Google
                    if optimize_google:
                        import tempfile
                        temp_output = tempfile.mktemp(suffix='.csv', dir=os.path.dirname(self.csv_path))
                    
                    success, output_path, error = processor.process_csv(
                        self.csv_path,
                        output_path=temp_output,
                        prompt=prompt,
                        selected_handles=selected_handles,
                        progress_callback=progress_cb,
                        log_callback=log_cb,
                        cancel_check=cancel_cb
                    )
                    
                    if not success or (self.progress_window and self.progress_window.is_cancelled):
                        if self.progress_window:
                            self.progress_window.after(0, lambda: self.progress_window.finish(success, output_path, error))
                        return
                    
                    # Si on optimise aussi Google, utiliser le fichier modifié comme entrée
                    csv_to_optimize = output_path if temp_output else output_path
                
                # Traitement 2: Optimiser Google Shopping
                if optimize_google:
                    optimizer = GoogleShoppingOptimizer(ai_provider)
                    
                    def progress_cb(msg, current, total):
                        if self.progress_window and not self.progress_window.is_cancelled:
                            self.progress_window.after(0, lambda: self.progress_window.update_progress(msg, current, total))
                    
                    def log_cb(msg):
                        if self.progress_window:
                            self.progress_window.after(0, lambda: self.progress_window.add_log(msg))
                    
                    def cancel_cb():
                        return self.progress_window.is_cancelled if self.progress_window else False
                    
                    success, output_path, error = optimizer.optimize_csv(
                        csv_to_optimize,
                        output_path=None,  # Générer automatiquement
                        selected_handles=selected_handles,
                        progress_callback=progress_cb,
                        log_callback=log_cb,
                        cancel_check=cancel_cb
                    )
                    
                    # Nettoyer le fichier temporaire si créé
                    if temp_output and os.path.exists(temp_output):
                        try:
                            os.remove(temp_output)
                        except:
                            pass
                
                # Finaliser
                if self.progress_window:
                    self.progress_window.after(0, lambda: self.progress_window.finish(success, output_path, error))
            
            except Exception as e:
                error_msg = f"Erreur lors du traitement: {str(e)}"
                logger.error(error_msg, exc_info=True)
                if self.progress_window:
                    self.progress_window.after(0, lambda: self.progress_window.finish(False, None, error_msg))
        
        threading.Thread(target=process_thread, daemon=True).start()

