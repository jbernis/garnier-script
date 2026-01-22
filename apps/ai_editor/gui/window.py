"""
Fenêtre principale de l'éditeur IA pour modifier les descriptions et optimiser les champs Google Shopping.
"""

import customtkinter as ctk
from tkinter import messagebox, filedialog
from typing import Optional, Dict, Set
import pandas as pd
import os
import sys
import threading
import logging
from pathlib import Path

logger = logging.getLogger(__name__)

# Ajouter le répertoire parent au path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from apps.ai_editor.db import AIPromptsDB
from apps.ai_editor.csv_storage import CSVStorage
from apps.ai_editor.processor import CSVAIProcessor, SEO_FIELD_MAPPING
from utils.ai_providers import get_provider, AIProviderError
from gui.progress_window import ProgressWindow


class AIEditorWindow(ctk.CTkToplevel):
    """Fenêtre d'édition IA pour les fichiers CSV Shopify."""
    
    def __init__(self, parent):
        super().__init__(parent)
        
        self.title("Éditeur IA - CSV Shopify")
        self.geometry("1200x900")
        self.resizable(True, True)
        
        # Configuration CustomTkinter
        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("blue")
        
        # Variables
        self.db = AIPromptsDB()
        self.csv_storage = CSVStorage(self.db)
        self.csv_import_id: Optional[int] = None
        self.csv_path: Optional[str] = None
        self.selected_handles: Set[str] = set()
        self.progress_window: Optional[ProgressWindow] = None
        self.current_prompt_set_id: Optional[int] = None
        self.prompt_sets_mapping: Dict[str, int] = {}  # Mapping nom -> ID
        
        # Variables pour l'obfuscation de la clé API
        self.api_key_actual = ""
        self.is_obfuscated = False
        
        # Variables pour l'obfuscation de la clé Perplexity
        self.perplexity_key_actual = ""
        self.is_perplexity_obfuscated = False
        
        # Titre principal
        title_label = ctk.CTkLabel(
            self,
            text="🤖 Éditeur IA",
            font=ctk.CTkFont(size=24, weight="bold")
        )
        title_label.pack(pady=(20, 10))
        
        # Onglets principaux
        self.tabview = ctk.CTkTabview(self)
        self.tabview.pack(fill="both", expand=True, padx=20, pady=(0, 20))
        
        # Créer les 5 onglets
        self.tab_config = self.tabview.add("Configuration")
        self.tab_test = self.tabview.add("Test")
        self.tab_processing = self.tabview.add("Traitement")
        self.tab_diagnostic = self.tabview.add("Diagnostic")
        self.tab_visualizer = self.tabview.add("Visualiser")
        
        # Remplir l'onglet Configuration
        self.create_config_tab()
        
        # Remplir l'onglet Test
        self.create_test_tab()
        
        # Remplir l'onglet Traitement
        self.create_processing_tab()
        
        # Remplir l'onglet Diagnostic
        self.create_diagnostic_tab()
        
        # Remplir l'onglet Visualiser
        self.create_visualizer_tab()
        
        # Centrer la fenêtre
        self.center_window()
        
        # Garder la fenêtre au premier plan
        try:
            self.transient(parent)
        except Exception:
            pass
        self.after(100, self._bring_to_front)
        
        # Charger les prompts au démarrage
        self.load_prompt_sets()
        
        # Restaurer le dernier import CSV (si disponible)
        self.restore_last_import()
    
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
            if not hasattr(self, 'winfo_exists') or not self.winfo_exists():
                return
            
            self.update_idletasks()
            self.lift()
            self.focus_force()
            self.attributes('-topmost', True)
            self.after(150, lambda: self._reset_topmost())
        except Exception:
            pass
    
    def _reset_topmost(self):
        """Désactive l'attribut topmost."""
        try:
            if hasattr(self, 'winfo_exists') and self.winfo_exists():
                self.attributes('-topmost', False)
        except Exception:
            pass
    
    def restore_last_import(self):
        """Restaure automatiquement le dernier import CSV si disponible."""
        try:
            last_import = self.csv_storage.get_last_import()
            
            if last_import:
                # Restaurer les variables d'état
                self.csv_import_id = last_import['id']
                self.csv_path = last_import['original_file_path']
                
                # Charger les handles pour l'onglet Test
                handles = self.csv_storage.get_unique_handles(self.csv_import_id)
                self.selected_handles = set(handles)
                
                # Mettre à jour l'affichage de l'onglet Traitement
                if hasattr(self, 'csv_info_label'):
                    import os
                    filename = os.path.basename(self.csv_path)
                    self.csv_info_label.configure(
                        text=f"✓ {len(handles)} produit(s) restauré(s) depuis {filename}",
                        text_color="green"
                    )
                
                # Activer les boutons de traitement
                if hasattr(self, 'start_processing_button'):
                    self.start_processing_button.configure(state="normal")
                if hasattr(self, 'export_csv_button'):
                    self.export_csv_button.configure(state="normal")
                
                # Charger les données du diagnostic
                if hasattr(self, 'load_diagnostic_summary'):
                    self.load_diagnostic_summary()
                
                logger.info(f"✅ Import restauré: {last_import['original_file_path']} ({len(handles)} produits)")
            else:
                logger.info("Aucun import précédent trouvé")
        
        except Exception as e:
            logger.error(f"Erreur lors de la restauration de l'import: {e}", exc_info=True)
    
    def create_tooltip(self, widget, text):
        """Crée une infobulle pour un widget."""
        tooltip = None
        
        def on_enter(event):
            nonlocal tooltip
            try:
                if tooltip:
                    return
                
                x, y, _, _ = widget.bbox("insert")
                x += widget.winfo_rootx() + 25
                y += widget.winfo_rooty() + 25
                
                tooltip = ctk.CTkToplevel(widget)
                tooltip.wm_overrideredirect(True)
                tooltip.wm_geometry(f"+{x}+{y}")
                
                label = ctk.CTkLabel(
                    tooltip,
                    text=text,
                    fg_color=("gray75", "gray25"),
                    corner_radius=6,
                    padx=10,
                    pady=5
                )
                label.pack()
            except Exception:
                pass
        
        def on_leave(event):
            nonlocal tooltip
            try:
                if tooltip:
                    tooltip.destroy()
                    tooltip = None
            except Exception:
                pass
        
        widget.bind("<Enter>", on_enter)
        widget.bind("<Leave>", on_leave)
    
    # ========== ONGLET CONFIGURATION ==========
    
    def create_config_tab(self):
        """Crée l'onglet de configuration."""
        # Frame scrollable pour la configuration
        config_scroll = ctk.CTkScrollableFrame(self.tab_config)
        config_scroll.pack(fill="both", expand=True, padx=10, pady=10)
        
        # Section 1: Configuration IA
        self.create_config_section(config_scroll)
        
        # Section 2: Gestion des prompts
        self.create_prompts_section(config_scroll)
        
        # Section 3: Chargement CSV
        self.create_csv_section(config_scroll)
        
        # Section 4: Configuration du batch
        self.create_batch_config_section(config_scroll)
        
        # Section 5: Sélection des champs à traiter
        self.create_fields_section(config_scroll)
    
    # ========== Section 1: Configuration IA ==========
    
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
        
        provider_label = ctk.CTkLabel(provider_frame, text="Fournisseur IA:", width=150)
        provider_label.pack(side="left", padx=10)
        
        # Récupérer le dernier provider utilisé depuis la DB (sinon openai par défaut)
        last_provider = self.db.get_last_used_provider() or "openai"
        self.provider_var = ctk.StringVar(value=last_provider)
        self.provider_dropdown = ctk.CTkComboBox(
            provider_frame,
            values=["openai", "claude", "gemini"],
            variable=self.provider_var,
            command=self.on_provider_changed,
            width=200
        )
        self.provider_dropdown.pack(side="left", padx=10)
        
        # Clé API
        api_key_frame = ctk.CTkFrame(config_frame)
        api_key_frame.pack(fill="x", padx=20, pady=(0, 10))
        
        api_key_label = ctk.CTkLabel(api_key_frame, text="Clé API:", width=150)
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
        
        # Modèle
        model_frame = ctk.CTkFrame(config_frame)
        model_frame.pack(fill="x", padx=20, pady=(0, 10))
        
        model_label = ctk.CTkLabel(model_frame, text="Modèle:", width=150)
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
        self.load_models_button.pack(side="left", padx=5)
        
        # Bouton sauvegarder la configuration
        self.save_config_button = ctk.CTkButton(
            model_frame,
            text="💾 Sauvegarder",
            command=self.save_ai_configuration,
            width=120,
            fg_color="green",
            hover_color="darkgreen"
        )
        self.save_config_button.pack(side="left", padx=5)
        
        # === RECHERCHE INTERNET (PERPLEXITY) ===
        # Séparateur visuel
        separator = ctk.CTkFrame(config_frame, height=2, fg_color="gray30")
        separator.pack(fill="x", padx=20, pady=(15, 15))
        
        # Frame principal pour la recherche Internet
        self.search_main_frame = ctk.CTkFrame(config_frame, fg_color="transparent")
        self.search_main_frame.pack(fill="x", padx=20, pady=(0, 0))
        
        # Titre + Switch sur la même ligne
        search_header = ctk.CTkFrame(self.search_main_frame, fg_color="transparent")
        search_header.pack(fill="x", pady=(0, 10))
        
        search_title_label = ctk.CTkLabel(
            search_header,
            text="🔍 Recherche Internet",
            font=ctk.CTkFont(size=14, weight="bold")
        )
        search_title_label.pack(side="left", padx=0)
        
        self.enable_search_var = ctk.BooleanVar(value=False)
        self.enable_search_switch = ctk.CTkSwitch(
            search_header,
            text="",
            variable=self.enable_search_var,
            command=self.on_search_toggled,
            width=50
        )
        self.enable_search_switch.pack(side="left", padx=15)
        
        # Label d'information (OpenAI et Claude uniquement)
        self.search_info_label = ctk.CTkLabel(
            search_header,
            text="(OpenAI et Claude uniquement)",
            font=ctk.CTkFont(size=11),
            text_color="gray"
        )
        self.search_info_label.pack(side="left", padx=10)
        
        # Frame pour la clé Perplexity (caché par défaut)
        self.perplexity_key_frame = ctk.CTkFrame(self.search_main_frame, fg_color="transparent")
        
        # Ligne 1: Clé API
        perplexity_key_row = ctk.CTkFrame(self.perplexity_key_frame, fg_color="transparent")
        perplexity_key_row.pack(fill="x", pady=(0, 5))
        
        perplexity_label = ctk.CTkLabel(perplexity_key_row, text="Clé API Perplexity:", width=150)
        perplexity_label.pack(side="left", padx=10)
        
        self.perplexity_key_var = ctk.StringVar(value="")
        self.perplexity_key_entry = ctk.CTkEntry(
            perplexity_key_row,
            textvariable=self.perplexity_key_var,
            width=400,
            placeholder_text="Entrez votre clé API Perplexity..."
        )
        self.perplexity_key_entry.pack(side="left", padx=10, fill="x", expand=True)
        self.perplexity_key_entry.bind('<FocusIn>', self.on_perplexity_key_focus_in)
        self.perplexity_key_entry.bind('<FocusOut>', self.on_perplexity_key_focus_out)
        self.perplexity_key_entry.bind('<KeyRelease>', self.on_perplexity_key_typing)
        
        # Ligne 2: Modèle + Boutons
        perplexity_model_row = ctk.CTkFrame(self.perplexity_key_frame, fg_color="transparent")
        perplexity_model_row.pack(fill="x", pady=(0, 0))
        
        perplexity_model_label = ctk.CTkLabel(perplexity_model_row, text="Modèle Perplexity:", width=150)
        perplexity_model_label.pack(side="left", padx=10)
        
        self.perplexity_model_var = ctk.StringVar(value="sonar")
        self.perplexity_model_dropdown = ctk.CTkComboBox(
            perplexity_model_row,
            values=["sonar", "sonar-reasoning", "sonar-pro", "sonar-reasoning-pro"],
            variable=self.perplexity_model_var,
            width=200,
            state="readonly"
        )
        self.perplexity_model_dropdown.pack(side="left", padx=10)
        
        # Bouton pour charger les modèles depuis l'API
        self.load_perplexity_models_button = ctk.CTkButton(
            perplexity_model_row,
            text="Charger les modèles",
            command=self.load_perplexity_models_from_api,
            width=150,
            state="disabled"
        )
        self.load_perplexity_models_button.pack(side="left", padx=5)
        
        # Boutons pour charger/sauvegarder config
        load_perplexity_button = ctk.CTkButton(
            perplexity_model_row,
            text="Charger",
            command=self.load_perplexity_key_from_db,
            width=80
        )
        load_perplexity_button.pack(side="left", padx=5)
        
        save_perplexity_button = ctk.CTkButton(
            perplexity_model_row,
            text="Sauvegarder",
            command=self.save_perplexity_key_to_db,
            width=100,
            fg_color="green",
            hover_color="darkgreen"
        )
        save_perplexity_button.pack(side="left", padx=5)
        
        # Message de statut
        self.config_status_label = ctk.CTkLabel(
            config_frame,
            text="",
            font=ctk.CTkFont(size=11),
            text_color="gray"
        )
        self.config_status_label.pack(anchor="w", padx=20, pady=(0, 20))
        
        # Charger les credentials depuis la base de données
        self.load_api_key_from_db()
        self.load_default_model()
        self.update_search_visibility()  # Afficher/cacher la recherche selon le provider
    
    def on_provider_changed(self, value=None):
        """Appelé quand le fournisseur IA change."""
        self.load_api_key_from_db()
        self.load_default_model()
        self.update_search_visibility()
    
    def update_search_visibility(self):
        """Met à jour la visibilité de la section recherche Internet selon le provider."""
        provider = self.provider_dropdown.get()
        
        if provider.lower() == "gemini":
            # Cacher la recherche Internet pour Gemini
            self.search_main_frame.pack_forget()
            # Désactiver la recherche si elle était activée
            self.enable_search_var.set(False)
            self.perplexity_key_frame.pack_forget()
        else:
            # Afficher la recherche Internet pour OpenAI et Claude
            self.search_main_frame.pack(fill="x", padx=20, pady=(0, 0))
    
    def on_search_toggled(self):
        """Appelé quand le switch de recherche Internet change."""
        if self.enable_search_var.get():
            # Afficher le champ de clé Perplexity
            self.perplexity_key_frame.pack(fill="x", pady=(0, 10))
            self.load_perplexity_key_from_db()
        else:
            # Cacher le champ
            self.perplexity_key_frame.pack_forget()
    
    def on_perplexity_key_focus_in(self, event=None):
        """Appelé quand le champ Perplexity reçoit le focus."""
        if self.is_perplexity_obfuscated and self.perplexity_key_actual:
            self.perplexity_key_var.set(self.perplexity_key_actual)
            self.is_perplexity_obfuscated = False
    
    def on_perplexity_key_typing(self, event=None):
        """Appelé quand l'utilisateur tape dans le champ Perplexity."""
        self.is_perplexity_obfuscated = False
        # Activer le bouton "Charger les modèles" si une clé est présente
        perplexity_key = self.perplexity_key_var.get().strip()
        self.load_perplexity_models_button.configure(state="normal" if perplexity_key else "disabled")
    
    def on_perplexity_key_focus_out(self, event=None):
        """Appelé quand le champ Perplexity perd le focus."""
        if not self.is_perplexity_obfuscated:
            current_value = self.perplexity_key_var.get().strip()
            if current_value:
                self.perplexity_key_actual = current_value
                # Obfusquer l'affichage
                obfuscated = self._obfuscate_api_key(current_value)
                self.perplexity_key_var.set(obfuscated)
                self.is_perplexity_obfuscated = True
                # Activer le bouton "Charger les modèles"
                self.load_perplexity_models_button.configure(state="normal")
    
    def load_perplexity_key_from_db(self):
        """Charge la clé Perplexity et le modèle depuis la base de données."""
        try:
            perplexity_key = self.db.get_ai_credentials("perplexity")
            perplexity_model = self.db.get_ai_model("perplexity")
            
            if perplexity_key:
                self.perplexity_key_actual = perplexity_key
                obfuscated = self._obfuscate_api_key(perplexity_key)
                self.perplexity_key_var.set(obfuscated)
                self.is_perplexity_obfuscated = True
                
                # Activer le bouton "Charger les modèles"
                self.load_perplexity_models_button.configure(state="normal")
                
                # Charger le modèle ou utiliser "sonar" par défaut
                if perplexity_model:
                    self.perplexity_model_var.set(perplexity_model)
                else:
                    self.perplexity_model_var.set("sonar")
                
                self.config_status_label.configure(
                    text=f"✓ Configuration Perplexity chargée (modèle: {self.perplexity_model_var.get()})",
                    text_color="green"
                )
            else:
                self.perplexity_key_actual = ""
                self.perplexity_key_var.set("")
                self.is_perplexity_obfuscated = False
                self.perplexity_model_var.set("sonar")
                self.load_perplexity_models_button.configure(state="disabled")
                self.config_status_label.configure(
                    text="⚠️ Aucune clé Perplexity configurée. Entrez votre clé API.",
                    text_color="orange"
                )
        except Exception as e:
            logger.error(f"Erreur lors du chargement de la clé Perplexity: {e}")
            self.config_status_label.configure(
                text=f"✗ Erreur: {str(e)[:50]}...",
                text_color="red"
            )
    
    def load_perplexity_models_from_api(self):
        """Charge les modèles Perplexity disponibles depuis l'API."""
        # Récupérer la clé réelle (non obfusquée)
        if self.is_perplexity_obfuscated and self.perplexity_key_actual:
            perplexity_key = self.perplexity_key_actual
        else:
            perplexity_key = self.perplexity_key_var.get().strip()
        
        if not perplexity_key:
            self.config_status_label.configure(text="✗ Veuillez entrer une clé API Perplexity valide", text_color="red")
            return
        
        self.load_perplexity_models_button.configure(state="disabled", text="Chargement...")
        self.config_status_label.configure(
            text="Chargement des modèles Perplexity...",
            text_color="#FFFF99"
        )
        
        def load_thread():
            try:
                from utils.search_tools import PerplexitySearchTool
                
                # Créer une instance temporaire pour lister les modèles
                tool = PerplexitySearchTool(perplexity_key)
                models = tool.list_models_from_api()
                
                # Vérifier que la fenêtre existe toujours avant de mettre à jour
                try:
                    if hasattr(self, 'winfo_exists') and self.winfo_exists():
                        self.after(0, lambda: self.perplexity_models_loaded(models))
                except Exception:
                    pass  # Fenêtre fermée, ignorer
            except Exception as e:
                error_msg = str(e)
                logger.error(f"Erreur lors du chargement des modèles Perplexity: {e}", exc_info=True)
                # Vérifier que la fenêtre existe toujours avant de mettre à jour
                try:
                    if hasattr(self, 'winfo_exists') and self.winfo_exists():
                        self.after(0, lambda: self.perplexity_models_load_error(error_msg))
                except Exception:
                    pass  # Fenêtre fermée, ignorer
        
        threading.Thread(target=load_thread, daemon=True).start()
    
    def perplexity_models_loaded(self, models: list[str]):
        """Appelé quand les modèles Perplexity sont chargés."""
        try:
            if not hasattr(self, 'winfo_exists') or not self.winfo_exists():
                return
            
            if models:
                self.perplexity_model_dropdown.configure(values=models, state="readonly")
                current_model = self.perplexity_model_var.get()
                if current_model not in models and models:
                    self.perplexity_model_var.set(models[0])
                
                self.config_status_label.configure(
                    text=f"✓ {len(models)} modèle(s) Perplexity chargé(s)",
                    text_color="green"
                )
            else:
                self.config_status_label.configure(
                    text="⚠️ Aucun modèle trouvé, utilisation de la liste par défaut",
                    text_color="orange"
                )
            
            self.load_perplexity_models_button.configure(state="normal", text="Charger les modèles")
        except Exception as e:
            logger.error(f"Erreur dans perplexity_models_loaded: {e}")
    
    def perplexity_models_load_error(self, error_msg: str):
        """Appelé en cas d'erreur lors du chargement des modèles Perplexity."""
        try:
            if not hasattr(self, 'winfo_exists') or not self.winfo_exists():
                return
            
            self.config_status_label.configure(
                text=f"✗ Erreur: {error_msg[:50]}...",
                text_color="red"
            )
            self.load_perplexity_models_button.configure(state="normal", text="Charger les modèles")
        except Exception as e:
            logger.error(f"Erreur dans perplexity_models_load_error: {e}")
    
    def save_perplexity_key_to_db(self):
        """Sauvegarde la clé Perplexity et le modèle dans la base de données."""
        try:
            # Récupérer la clé réelle (non obfusquée)
            if self.is_perplexity_obfuscated and self.perplexity_key_actual:
                perplexity_key = self.perplexity_key_actual
            else:
                perplexity_key = self.perplexity_key_var.get().strip()
            
            if not perplexity_key:
                self.config_status_label.configure(
                    text="⚠️ Veuillez entrer une clé Perplexity",
                    text_color="orange"
                )
                return
            
            # Récupérer le modèle sélectionné
            perplexity_model = self.perplexity_model_var.get()
            
            # Sauvegarder dans la base de données avec le modèle
            self.db.save_ai_credentials("perplexity", perplexity_key, perplexity_model)
            
            # Obfusquer si ce n'est pas déjà fait
            if not self.is_perplexity_obfuscated:
                self.perplexity_key_actual = perplexity_key
                obfuscated = self._obfuscate_api_key(perplexity_key)
                self.perplexity_key_var.set(obfuscated)
                self.is_perplexity_obfuscated = True
            
            self.config_status_label.configure(
                text=f"✓ Configuration Perplexity sauvegardée (modèle: {perplexity_model})",
                text_color="green"
            )
        except Exception as e:
            logger.error(f"Erreur lors de la sauvegarde de la clé Perplexity: {e}")
            self.config_status_label.configure(
                text=f"✗ Erreur: {str(e)[:50]}...",
                text_color="red"
            )
    
    def on_api_key_focus_in(self, event=None):
        """Appelé quand le champ API reçoit le focus."""
        if self.is_obfuscated and self.api_key_actual:
            self.api_key_var.set(self.api_key_actual)
            self.is_obfuscated = False
    
    def on_api_key_typing(self, event=None):
        """Appelé quand l'utilisateur tape dans le champ API."""
        self.is_obfuscated = False
        api_key = self.api_key_var.get().strip()
        self.load_models_button.configure(state="normal" if api_key else "disabled")
    
    def on_api_key_focus_out(self, event=None):
        """Appelé quand le champ API perd le focus."""
        if not self.is_obfuscated:
            current_value = self.api_key_var.get().strip()
            if current_value:
                self.api_key_actual = current_value
                # Sauvegarder dans la base de données (avec le modèle actuel si disponible)
                provider = self.provider_var.get()
                current_model = self.model_var.get() if self.model_var.get() else None
                self.db.save_ai_credentials(provider, current_value, current_model)
                # Obfusquer l'affichage
                obfuscated = self._obfuscate_api_key(current_value)
                self.api_key_var.set(obfuscated)
                self.is_obfuscated = True
                self.load_models_button.configure(state="normal")
    
    def _obfuscate_api_key(self, key: str) -> str:
        """Obfuscates the API key, showing only the first 6 and last 5 characters."""
        if len(key) > 11:
            return f"{key[:6]}...{key[-5:]}"
        return "*" * len(key) if key else ""
    
    def load_api_key_from_db(self):
        """Charge la clé API depuis la base de données."""
        provider = self.provider_var.get()
        api_key = self.db.get_ai_credentials(provider)
        
        if api_key:
            self.api_key_actual = api_key
            obfuscated = self._obfuscate_api_key(api_key)
            self.api_key_var.set(obfuscated)
            self.is_obfuscated = True
            self.load_models_button.configure(state="normal")
            self.config_status_label.configure(
                text=f"✓ Clé API chargée depuis la base de données",
                text_color="green"
            )
        else:
            self.api_key_actual = ""
            self.api_key_var.set("")
            self.is_obfuscated = False
            self.load_models_button.configure(state="disabled")
            self.config_status_label.configure(
                text="⚠️ Aucune clé API configurée. Entrez votre clé API.",
                text_color="orange"
            )
    
    def load_default_model(self):
        """Charge le modèle par défaut pour le fournisseur sélectionné."""
        provider = self.provider_var.get()
        
        # Essayer de charger le modèle sauvegardé depuis la base de données
        saved_model = self.db.get_ai_model(provider)
        
        if saved_model:
            self.model_dropdown.configure(values=[saved_model], state="readonly")
            self.model_var.set(saved_model)
            self.config_status_label.configure(
                text=f"✓ Modèle chargé depuis la base de données: {saved_model}",
                text_color="green"
            )
        else:
            # Utiliser le modèle par défaut
            default_models = {
                "openai": "gpt-4o-mini",
                "claude": "claude-haiku-4-5-20251001",
                "gemini": "gemini-1.5-flash"
            }
            
            default_model = default_models.get(provider, "")
            if default_model:
                self.model_dropdown.configure(values=[default_model], state="readonly")
                self.model_var.set(default_model)
    
    def load_models(self):
        """Charge les modèles disponibles depuis l'API."""
        provider = self.provider_var.get()
        
        if self.is_obfuscated and self.api_key_actual:
            api_key = self.api_key_actual
        else:
            api_key = self.api_key_var.get().strip()
        
        if not api_key:
            self.config_status_label.configure(text="✗ Veuillez entrer une clé API valide", text_color="red")
            return
        
        self.load_models_button.configure(state="disabled", text="Chargement...")
        self.config_status_label.configure(
            text="Chargement des modèles...",
            text_color="#FFFF99"
        )
        
        def load_thread():
            try:
                ai_provider = get_provider(provider, api_key=api_key)
                models = ai_provider.list_models()
                # Vérifier que la fenêtre existe toujours avant de mettre à jour
                try:
                    if hasattr(self, 'winfo_exists') and self.winfo_exists():
                        self.after(0, lambda: self.models_loaded(models))
                except Exception:
                    pass  # Fenêtre fermée, ignorer
            except Exception as e:
                error_msg = str(e)
                logger.error(f"Erreur lors du chargement des modèles: {e}", exc_info=True)
                # Vérifier que la fenêtre existe toujours avant de mettre à jour
                try:
                    if hasattr(self, 'winfo_exists') and self.winfo_exists():
                        self.after(0, lambda: self.models_load_error(error_msg))
                except Exception:
                    pass  # Fenêtre fermée, ignorer
        
        threading.Thread(target=load_thread, daemon=True).start()
    
    def models_loaded(self, models: list[str]):
        """Appelé quand les modèles sont chargés."""
        try:
            if not hasattr(self, 'winfo_exists') or not self.winfo_exists():
                return
            
            if models:
                self.model_dropdown.configure(values=models, state="readonly")
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
        except Exception as e:
            logger.error(f"Erreur dans models_loaded: {e}")
    
    def models_load_error(self, error_msg: str):
        """Appelé en cas d'erreur lors du chargement des modèles."""
        try:
            if not hasattr(self, 'winfo_exists') or not self.winfo_exists():
                return
            
            self.config_status_label.configure(
                text=f"✗ Erreur: {error_msg[:50]}...",
                text_color="red"
            )
            self.load_models_button.configure(state="normal", text="Charger les modèles")
        except Exception as e:
            logger.error(f"Erreur dans models_load_error: {e}")
    
    def save_ai_configuration(self):
        """Sauvegarde la configuration IA (clé API + modèle)."""
        provider = self.provider_var.get()
        model = self.model_var.get()
        
        # Récupérer la clé API
        if self.is_obfuscated and self.api_key_actual:
            api_key = self.api_key_actual
        else:
            api_key = self.api_key_var.get().strip()
        
        if not api_key:
            self.config_status_label.configure(
                text="⚠️ Veuillez entrer une clé API",
                text_color="orange"
            )
            return
        
        if not model:
            self.config_status_label.configure(
                text="⚠️ Veuillez sélectionner un modèle",
                text_color="orange"
            )
            return
        
        try:
            # Sauvegarder la clé API et le modèle
            self.db.save_ai_credentials(provider, api_key, model)
            
            # Obfusquer la clé API si ce n'est pas déjà fait
            if not self.is_obfuscated:
                self.api_key_actual = api_key
                obfuscated = self._obfuscate_api_key(api_key)
                self.api_key_var.set(obfuscated)
                self.is_obfuscated = True
            
            self.config_status_label.configure(
                text=f"✓ Configuration sauvegardée: {provider} - {model}",
                text_color="green"
            )
            
        except Exception as e:
            logger.error(f"Erreur lors de la sauvegarde de la configuration: {e}", exc_info=True)
            self.config_status_label.configure(
                text=f"✗ Erreur lors de la sauvegarde: {str(e)[:50]}...",
                text_color="red"
            )
    
    # ========== Section 2: Gestion des prompts ==========
    
    def create_prompts_section(self, parent):
        """Crée la section de gestion des prompts."""
        prompts_frame = ctk.CTkFrame(parent)
        prompts_frame.pack(fill="x", pady=(0, 20))
        
        prompts_title = ctk.CTkLabel(
            prompts_frame,
            text="Gestion des prompts",
            font=ctk.CTkFont(size=16, weight="bold")
        )
        prompts_title.pack(anchor="w", padx=20, pady=(20, 10))
        
        # Liste déroulante des prompts
        prompt_select_frame = ctk.CTkFrame(prompts_frame)
        prompt_select_frame.pack(fill="x", padx=20, pady=(0, 10))
        
        prompt_label = ctk.CTkLabel(prompt_select_frame, text="Ensemble de prompts:", width=150)
        prompt_label.pack(side="left", padx=10)
        
        self.prompt_set_var = ctk.StringVar(value="")
        self.prompt_set_dropdown = ctk.CTkComboBox(
            prompt_select_frame,
            values=[],
            variable=self.prompt_set_var,
            command=self.on_prompt_set_selected,
            width=300
        )
        self.prompt_set_dropdown.pack(side="left", padx=10, fill="x", expand=True)
        
        # Boutons de gestion
        buttons_frame = ctk.CTkFrame(prompt_select_frame)
        buttons_frame.pack(side="left", padx=10)
        
        # Bouton Nouveau
        new_btn = ctk.CTkButton(
            buttons_frame, 
            text="➕ Nouveau", 
            command=self.create_new_prompt_set, 
            width=100
        )
        new_btn.pack(side="left", padx=2)
        self.create_tooltip(new_btn, "Créer un nouvel ensemble de prompts")
        
        # Bouton Dupliquer
        duplicate_btn = ctk.CTkButton(
            buttons_frame, 
            text="📋 Dupliquer", 
            command=self.duplicate_prompt_set, 
            width=110
        )
        duplicate_btn.pack(side="left", padx=2)
        self.create_tooltip(duplicate_btn, "Dupliquer l'ensemble sélectionné")
        
        # Bouton Supprimer
        delete_btn = ctk.CTkButton(
            buttons_frame, 
            text="🗑️ Supprimer", 
            command=self.delete_prompt_set, 
            width=110, 
            fg_color="red", 
            hover_color="darkred"
        )
        delete_btn.pack(side="left", padx=2)
        self.create_tooltip(delete_btn, "Supprimer l'ensemble sélectionné")
        
        # Label de statut pour les messages
        self.prompts_status_label = ctk.CTkLabel(
            prompts_frame,
            text="",
            text_color="gray",
            font=ctk.CTkFont(size=12)
        )
        self.prompts_status_label.pack(pady=(0, 10))
        
        # Champs de prompts
        prompts_fields_frame = ctk.CTkFrame(prompts_frame)
        prompts_fields_frame.pack(fill="both", expand=True, padx=20, pady=(0, 10))
        
        # === SECTION AGENT SEO ===
        seo_section_label = ctk.CTkLabel(
            prompts_fields_frame, 
            text="━━━ AGENT SEO ━━━",
            font=ctk.CTkFont(size=14, weight="bold"),
            text_color="#4A9EFF"
        )
        seo_section_label.pack(fill="x", padx=10, pady=(10, 5))
        
        # Prompt système SEO (PROTÉGÉ)
        seo_system_header_frame = ctk.CTkFrame(prompts_fields_frame, fg_color="transparent")
        seo_system_header_frame.pack(fill="x", padx=10, pady=(10, 5))
        
        seo_system_label = ctk.CTkLabel(
            seo_system_header_frame, 
            text="Prompt système SEO (RÈGLES TECHNIQUES) 🔒", 
            anchor="w",
            text_color="#FFA500"
        )
        seo_system_label.pack(side="left", fill="x", expand=True)
        
        # Boutons Modifier/Sauvegarder
        self.seo_system_edit_btn = ctk.CTkButton(
            seo_system_header_frame,
            text="✏️ Modifier",
            width=100,
            height=28,
            command=self.unlock_seo_system_prompt,
            fg_color="#FFA500",
            hover_color="#FF8C00"
        )
        self.seo_system_edit_btn.pack(side="right", padx=5)
        
        self.seo_system_save_btn = ctk.CTkButton(
            seo_system_header_frame,
            text="💾 Sauvegarder",
            width=100,
            height=28,
            command=self.lock_seo_system_prompt,
            fg_color="#28a745",
            hover_color="#218838"
        )
        self.seo_system_save_btn.pack(side="right")
        self.seo_system_save_btn.pack_forget()  # Caché par défaut
        
        # Textbox prompt système SEO (grisé par défaut)
        self.seo_system_prompt_text = ctk.CTkTextbox(prompts_fields_frame, height=120)
        self.seo_system_prompt_text.pack(fill="x", padx=10, pady=(0, 10))
        self.seo_system_prompt_text.configure(state="disabled", text_color="#888888")  # Grisé par défaut
        self.seo_system_locked = True  # État de verrouillage
        
        # Prompt métier SEO avec header et boutons
        seo_metier_header_frame = ctk.CTkFrame(prompts_fields_frame, fg_color="transparent")
        seo_metier_header_frame.pack(fill="x", padx=10, pady=(10, 5))
        
        seo_metier_label = ctk.CTkLabel(
            seo_metier_header_frame, 
            text="Prompt métier SEO (6 champs: SEO Title, SEO Description, Title, Body HTML, Tags, Image Alt Text)  🔒 PROTÉGÉ",
            anchor="w",
            text_color="#FFA500"
        )
        seo_metier_label.pack(side="left", fill="x", expand=True)
        
        # Boutons Modifier/Sauvegarder pour SEO métier
        self.seo_metier_edit_btn = ctk.CTkButton(
            seo_metier_header_frame,
            text="✏️ Modifier",
            width=100,
            height=28,
            command=self.unlock_seo_metier_prompt,
            fg_color="#FFA500",
            hover_color="#FF8C00"
        )
        self.seo_metier_edit_btn.pack(side="right", padx=5)
        
        self.seo_metier_save_btn = ctk.CTkButton(
            seo_metier_header_frame,
            text="💾 Sauvegarder",
            width=100,
            height=28,
            command=self.lock_seo_metier_prompt,
            fg_color="#28a745",
            hover_color="#218838"
        )
        self.seo_metier_save_btn.pack(side="right")
        self.seo_metier_save_btn.pack_forget()  # Caché par défaut
        
        self.seo_prompt_text = ctk.CTkTextbox(prompts_fields_frame, height=120)
        self.seo_prompt_text.pack(fill="x", padx=10, pady=(0, 10))
        self.seo_prompt_text.configure(state="disabled", text_color="#888888")  # Grisé par défaut
        self.seo_metier_locked = True  # État de verrouillage
        
        # === SECTION AGENT GOOGLE SHOPPING ===
        google_section_label = ctk.CTkLabel(
            prompts_fields_frame, 
            text="━━━ AGENT GOOGLE SHOPPING (Gemini uniquement) ━━━",
            font=ctk.CTkFont(size=14, weight="bold"),
            text_color="#FFB84D"
        )
        google_section_label.pack(fill="x", padx=10, pady=(20, 5))
        
        # Prompt système Google Shopping avec header et boutons
        google_system_header_frame = ctk.CTkFrame(prompts_fields_frame, fg_color="transparent")
        google_system_header_frame.pack(fill="x", padx=10, pady=(10, 5))
        
        google_system_label = ctk.CTkLabel(
            google_system_header_frame, 
            text="Prompt système Google Shopping  🔒 PROTÉGÉ",
            anchor="w",
            text_color="#FFA500"
        )
        google_system_label.pack(side="left", fill="x", expand=True)
        
        # Boutons Modifier/Sauvegarder pour Google Shopping système
        self.google_system_edit_btn = ctk.CTkButton(
            google_system_header_frame,
            text="✏️ Modifier",
            width=100,
            height=28,
            command=self.unlock_google_system_prompt,
            fg_color="#FFA500",
            hover_color="#FF8C00"
        )
        self.google_system_edit_btn.pack(side="right", padx=5)
        
        self.google_system_save_btn = ctk.CTkButton(
            google_system_header_frame,
            text="💾 Sauvegarder",
            width=100,
            height=28,
            command=self.lock_google_system_prompt,
            fg_color="#28a745",
            hover_color="#218838"
        )
        self.google_system_save_btn.pack(side="right")
        self.google_system_save_btn.pack_forget()  # Caché par défaut
        
        self.google_shopping_system_prompt_text = ctk.CTkTextbox(prompts_fields_frame, height=80)
        self.google_shopping_system_prompt_text.pack(fill="x", padx=10, pady=(0, 10))
        self.google_shopping_system_prompt_text.configure(state="disabled", text_color="#888888")  # Grisé par défaut
        self.google_system_locked = True  # État de verrouillage
        
        # Prompt métier Google Shopping avec header et boutons
        google_metier_header_frame = ctk.CTkFrame(prompts_fields_frame, fg_color="transparent")
        google_metier_header_frame.pack(fill="x", padx=10, pady=(10, 5))
        
        google_metier_label = ctk.CTkLabel(
            google_metier_header_frame, 
            text="Prompt métier Google Shopping Category  🔒 PROTÉGÉ",
            anchor="w",
            text_color="#FFA500"
        )
        google_metier_label.pack(side="left", fill="x", expand=True)
        
        # Boutons Modifier/Sauvegarder pour Google Shopping métier
        self.google_metier_edit_btn = ctk.CTkButton(
            google_metier_header_frame,
            text="✏️ Modifier",
            width=100,
            height=28,
            command=self.unlock_google_metier_prompt,
            fg_color="#FFA500",
            hover_color="#FF8C00"
        )
        self.google_metier_edit_btn.pack(side="right", padx=5)
        
        self.google_metier_save_btn = ctk.CTkButton(
            google_metier_header_frame,
            text="💾 Sauvegarder",
            width=100,
            height=28,
            command=self.lock_google_metier_prompt,
            fg_color="#28a745",
            hover_color="#218838"
        )
        self.google_metier_save_btn.pack(side="right")
        self.google_metier_save_btn.pack_forget()  # Caché par défaut
        
        self.google_category_prompt_text = ctk.CTkTextbox(prompts_fields_frame, height=80)
        self.google_category_prompt_text.pack(fill="x", padx=10, pady=(0, 20))
        self.google_category_prompt_text.configure(state="disabled", text_color="#888888")  # Grisé par défaut
        self.google_metier_locked = True  # État de verrouillage
        
        # Garder system_prompt pour rétrocompatibilité (caché)
        self.system_prompt_text = ctk.CTkTextbox(prompts_fields_frame, height=0)
        self.system_prompt_text.pack_forget()
    
    def load_prompt_sets(self):
        """Charge la liste des ensembles de prompts."""
        prompt_sets = self.db.list_prompt_sets()
        
        if prompt_sets:
            # Créer un mapping nom -> ID (sans afficher l'ID)
            self.prompt_sets_mapping = {ps['name']: ps['id'] for ps in prompt_sets}
            names = [ps['name'] for ps in prompt_sets]
            self.prompt_set_dropdown.configure(values=names)
            
            # Sélectionner dans cet ordre de priorité:
            # 1. Le dernier utilisé (last_used_at)
            # 2. Le défaut (is_default)
            # 3. Le premier de la liste
            
            last_used = self.db.get_last_used_prompt_set()
            if last_used and last_used['id'] in self.prompt_sets_mapping.values():
                # Trouver le nom correspondant à cet ID
                name = next((n for n, id in self.prompt_sets_mapping.items() if id == last_used['id']), None)
                if name:
                    self.prompt_set_dropdown.set(name)
                    self.on_prompt_set_selected(name)
                    return
            
            # Sinon, sélectionner le défaut ou le premier
            default_set = next((ps for ps in prompt_sets if ps['is_default']), None)
            if default_set:
                idx = prompt_sets.index(default_set)
                self.prompt_set_dropdown.set(names[idx])
                self.on_prompt_set_selected(names[idx])
            else:
                self.prompt_set_dropdown.set(names[0])
                self.on_prompt_set_selected(names[0])
        else:
            self.prompt_sets_mapping = {}
            self.prompt_set_dropdown.configure(values=["Aucun prompt"])
    
    def on_prompt_set_selected(self, value):
        """Appelé quand un ensemble de prompts est sélectionné."""
        if not value or value == "Aucun prompt":
            return
        
        # Récupérer l'ID depuis le mapping
        try:
            if not hasattr(self, 'prompt_sets_mapping'):
                return
            
            prompt_set_id = self.prompt_sets_mapping.get(value)
            if not prompt_set_id:
                return
            
            prompt_set = self.db.get_prompt_set(prompt_set_id)
            
            if prompt_set:
                self.current_prompt_set_id = prompt_set_id
                
                # Sauvegarder comme dernier utilisé
                self.db.save_last_used_prompt_set(prompt_set_id)
                
                # Logger le prompt set chargé
                import logging
                logger = logging.getLogger(__name__)
                logger.info(f"📝 Prompt set sélectionné dans l'interface: '{prompt_set.get('name', 'Sans nom')}' (ID: {prompt_set_id})")
                
                # Charger les prompts système séparés (avec fallback sur system_prompt)
                seo_sys_prompt = prompt_set.get('seo_system_prompt') or prompt_set.get('system_prompt', '')
                google_sys_prompt = prompt_set.get('google_shopping_system_prompt') or prompt_set.get('system_prompt', '')
                
                # SEO
                # Déverrouiller temporairement pour charger
                self.seo_system_prompt_text.configure(state="normal")
                self.seo_system_prompt_text.delete("1.0", "end")
                self.seo_system_prompt_text.insert("1.0", seo_sys_prompt)
                # Reverrouiller après chargement
                self.seo_system_prompt_text.configure(state="disabled", text_color="#888888")
                self.seo_system_locked = True
                # S'assurer que le bon bouton est affiché
                if hasattr(self, 'seo_system_save_btn'):
                    self.seo_system_save_btn.pack_forget()
                if hasattr(self, 'seo_system_edit_btn'):
                    self.seo_system_edit_btn.pack(side="right", padx=5)
                
                # Prompt métier SEO
                self.seo_prompt_text.configure(state="normal")
                self.seo_prompt_text.delete("1.0", "end")
                self.seo_prompt_text.insert("1.0", prompt_set['seo_prompt'])
                self.seo_prompt_text.configure(state="disabled", text_color="#888888")
                self.seo_metier_locked = True
                if hasattr(self, 'seo_metier_save_btn'):
                    self.seo_metier_save_btn.pack_forget()
                if hasattr(self, 'seo_metier_edit_btn'):
                    self.seo_metier_edit_btn.pack(side="right", padx=5)
                
                # Prompt système Google Shopping
                self.google_shopping_system_prompt_text.configure(state="normal")
                self.google_shopping_system_prompt_text.delete("1.0", "end")
                self.google_shopping_system_prompt_text.insert("1.0", google_sys_prompt)
                self.google_shopping_system_prompt_text.configure(state="disabled", text_color="#888888")
                self.google_system_locked = True
                if hasattr(self, 'google_system_save_btn'):
                    self.google_system_save_btn.pack_forget()
                if hasattr(self, 'google_system_edit_btn'):
                    self.google_system_edit_btn.pack(side="right", padx=5)
                
                # Prompt métier Google Shopping
                self.google_category_prompt_text.configure(state="normal")
                self.google_category_prompt_text.delete("1.0", "end")
                self.google_category_prompt_text.insert("1.0", prompt_set['google_category_prompt'])
                self.google_category_prompt_text.configure(state="disabled", text_color="#888888")
                self.google_metier_locked = True
                if hasattr(self, 'google_metier_save_btn'):
                    self.google_metier_save_btn.pack_forget()
                if hasattr(self, 'google_metier_edit_btn'):
                    self.google_metier_edit_btn.pack(side="right", padx=5)
                
                # Système (pour compatibilité)
                self.system_prompt_text.delete("1.0", "end")
                self.system_prompt_text.insert("1.0", prompt_set.get('system_prompt', seo_sys_prompt))
        except Exception as e:
            logger.error(f"Erreur lors du chargement du prompt set: {e}")
    
    def create_new_prompt_set(self):
        """Crée un nouvel ensemble de prompts."""
        dialog = ctk.CTkInputDialog(text="Nom de l'ensemble de prompts:", title="Nouvel ensemble")
        name = dialog.get_input()
        
        if name:
            # Récupérer les 4 prompts
            seo_sys_prompt = self.seo_system_prompt_text.get("1.0", "end-1c")
            google_sys_prompt = self.google_shopping_system_prompt_text.get("1.0", "end-1c")
            system_prompt = seo_sys_prompt  # Pour compatibilité
            
            prompt_set_id = self.db.create_prompt_set(
                name,
                system_prompt,
                self.seo_prompt_text.get("1.0", "end-1c"),
                self.google_category_prompt_text.get("1.0", "end-1c"),
                seo_system_prompt=seo_sys_prompt,
                google_shopping_system_prompt=google_sys_prompt,
                is_default=False
            )
            
            # Recharger la liste des prompts
            self.load_prompt_sets()
            
            # Sélectionner automatiquement le nouvel ensemble créé
            self.current_prompt_set_id = prompt_set_id
            new_prompt_name = f"{name} (ID: {prompt_set_id})"
            self.prompt_set_dropdown.set(new_prompt_name)
            
            self.show_prompts_status(f"✓ Ensemble de prompts '{name}' créé et sélectionné", "green")
    
    def duplicate_prompt_set(self):
        """Duplique l'ensemble de prompts sélectionné."""
        if not self.current_prompt_set_id:
            self.show_prompts_status("⚠️ Sélectionnez d'abord un ensemble de prompts", "orange")
            return
        
        prompt_set = self.db.get_prompt_set(self.current_prompt_set_id)
        if prompt_set:
            dialog = ctk.CTkInputDialog(text="Nom du nouvel ensemble:", title="Dupliquer")
            name = dialog.get_input()
            
            if name:
                # Récupérer les prompts système séparés avec fallback
                seo_sys_prompt = prompt_set.get('seo_system_prompt') or prompt_set.get('system_prompt', '')
                google_sys_prompt = prompt_set.get('google_shopping_system_prompt') or prompt_set.get('system_prompt', '')
                
                prompt_set_id = self.db.create_prompt_set(
                    name,
                    prompt_set.get('system_prompt', seo_sys_prompt),
                    prompt_set['seo_prompt'],
                    prompt_set['google_category_prompt'],
                    seo_system_prompt=seo_sys_prompt,
                    google_shopping_system_prompt=google_sys_prompt,
                    is_default=False
                )
                
                # Recharger la liste des prompts
                self.load_prompt_sets()
                
                # Sélectionner automatiquement le nouvel ensemble créé
                self.current_prompt_set_id = prompt_set_id
                new_prompt_name = f"{name} (ID: {prompt_set_id})"
                self.prompt_set_dropdown.set(new_prompt_name)
                
                self.show_prompts_status(f"✓ Ensemble de prompts '{name}' créé et sélectionné", "green")
    
    def show_prompt_history(self):
        """Affiche l'historique des prompts."""
        if not self.current_prompt_set_id:
            self.show_prompts_status("⚠️ Sélectionnez d'abord un ensemble de prompts", "orange")
            return
        
        history = self.db.get_prompt_history(self.current_prompt_set_id)
        if not history:
            self.show_prompts_status("ℹ️ Aucun historique disponible", "gray")
            return
        
        # Afficher le nombre de versions dans le label de statut
        self.show_prompts_status(f"ℹ️ {len(history)} version(s) dans l'historique", "blue")
        # TODO: Implémenter l'affichage de l'historique avec possibilité de restauration
    
    def show_prompts_status(self, message: str, color: str = "gray"):
        """Affiche un message de statut dans la section prompts."""
        try:
            if hasattr(self, 'prompts_status_label') and self.prompts_status_label.winfo_exists():
                self.prompts_status_label.configure(text=message, text_color=color)
                # Faire disparaître le message après 5 secondes (sauf erreurs)
                if color != "red":
                    self.after(5000, lambda: self._clear_prompts_status())
        except Exception:
            pass
    
    def _clear_prompts_status(self):
        """Efface le message de statut des prompts."""
        try:
            if hasattr(self, 'prompts_status_label') and self.prompts_status_label.winfo_exists():
                self.prompts_status_label.configure(text="")
        except Exception:
            pass
    
    def delete_prompt_set(self):
        """Supprime l'ensemble de prompts sélectionné."""
        if not self.current_prompt_set_id:
            self.show_prompts_status("⚠️ Sélectionnez d'abord un ensemble de prompts", "orange")
            return
        
        try:
            # Récupérer le nom de l'ensemble avant de le supprimer
            prompt_set = self.db.get_prompt_set(self.current_prompt_set_id)
            if not prompt_set:
                self.show_prompts_status("✗ Ensemble de prompts introuvable", "red")
                return
            
            # Supprimer l'ensemble
            self.db.delete_prompt_set(self.current_prompt_set_id)
            
            # Réinitialiser la sélection
            self.current_prompt_set_id = None
            
            # Déverrouiller temporairement pour vider les textboxes
            self.seo_system_prompt_text.configure(state="normal")
            self.seo_system_prompt_text.delete("1.0", "end")
            self.seo_system_prompt_text.configure(state="disabled")
            
            self.seo_prompt_text.configure(state="normal")
            self.seo_prompt_text.delete("1.0", "end")
            self.seo_prompt_text.configure(state="disabled")
            
            self.google_shopping_system_prompt_text.configure(state="normal")
            self.google_shopping_system_prompt_text.delete("1.0", "end")
            self.google_shopping_system_prompt_text.configure(state="disabled")
            
            self.google_category_prompt_text.configure(state="normal")
            self.google_category_prompt_text.delete("1.0", "end")
            self.google_category_prompt_text.configure(state="disabled")
            
            self.system_prompt_text.delete("1.0", "end")
            
            # Recharger la liste
            self.load_prompt_sets()
            
            self.show_prompts_status(f"✓ Ensemble '{prompt_set['name']}' supprimé", "green")
            logger.info(f"Ensemble de prompts supprimé: {prompt_set['name']}")
        except Exception as e:
            self.show_prompts_status(f"✗ Erreur: {str(e)}", "red")
            logger.error(f"Erreur lors de la suppression: {e}", exc_info=True)
    
    def unlock_seo_system_prompt(self):
        """Déverrouille le prompt système SEO pour édition."""
        if not hasattr(self, 'seo_system_prompt_text'):
            return
        
        # Déverrouiller le textbox
        self.seo_system_prompt_text.configure(state="normal", text_color="#FFFFFF")
        self.seo_system_locked = False
        
        # Afficher bouton Sauvegarder, cacher bouton Modifier
        self.seo_system_edit_btn.pack_forget()
        self.seo_system_save_btn.pack(side="right")
        
        self.show_prompts_status("🔓 Prompt système SEO déverrouillé (édition activée)", "#FFA500")
        logger.info("Prompt système SEO déverrouillé pour édition")
    
    def lock_seo_system_prompt(self):
        """Verrouille le prompt système SEO et sauvegarde."""
        if not hasattr(self, 'seo_system_prompt_text'):
            return
        
        # Sauvegarder d'abord
        if self.current_prompt_set_id:
            seo_sys_prompt = self.seo_system_prompt_text.get("1.0", "end-1c")
            google_sys_prompt = self.google_shopping_system_prompt_text.get("1.0", "end-1c")
            
            self.db.update_prompt_set(
                self.current_prompt_set_id,
                system_prompt=seo_sys_prompt,
                seo_prompt=self.seo_prompt_text.get("1.0", "end-1c"),
                google_category_prompt=self.google_category_prompt_text.get("1.0", "end-1c"),
                seo_system_prompt=seo_sys_prompt,
                google_shopping_system_prompt=google_sys_prompt
            )
        
        # Reverrouiller le textbox
        self.seo_system_prompt_text.configure(state="disabled", text_color="#888888")
        self.seo_system_locked = True
        
        # Afficher bouton Modifier, cacher bouton Sauvegarder
        self.seo_system_save_btn.pack_forget()
        self.seo_system_edit_btn.pack(side="right", padx=5)
        
        self.show_prompts_status("🔒 Prompt système SEO verrouillé et sauvegardé", "green")
        logger.info("Prompt système SEO verrouillé et sauvegardé")
    
    def unlock_seo_metier_prompt(self):
        """Déverrouille le prompt métier SEO pour édition."""
        if not hasattr(self, 'seo_prompt_text'):
            return
        
        self.seo_prompt_text.configure(state="normal", text_color="#FFFFFF")
        self.seo_metier_locked = False
        
        self.seo_metier_edit_btn.pack_forget()
        self.seo_metier_save_btn.pack(side="right")
        
        self.show_prompts_status("🔓 Prompt métier SEO déverrouillé (édition activée)", "#FFA500")
        logger.info("Prompt métier SEO déverrouillé pour édition")
    
    def lock_seo_metier_prompt(self):
        """Verrouille le prompt métier SEO et sauvegarde."""
        if not hasattr(self, 'seo_prompt_text'):
            return
        
        if self.current_prompt_set_id:
            seo_prompt = self.seo_prompt_text.get("1.0", "end-1c")
            
            self.db.update_prompt_set(
                self.current_prompt_set_id,
                seo_prompt=seo_prompt
            )
        
        self.seo_prompt_text.configure(state="disabled", text_color="#888888")
        self.seo_metier_locked = True
        
        self.seo_metier_save_btn.pack_forget()
        self.seo_metier_edit_btn.pack(side="right", padx=5)
        
        self.show_prompts_status("🔒 Prompt métier SEO verrouillé et sauvegardé", "green")
        logger.info("Prompt métier SEO verrouillé et sauvegardé")
    
    def unlock_google_system_prompt(self):
        """Déverrouille le prompt système Google Shopping pour édition."""
        if not hasattr(self, 'google_shopping_system_prompt_text'):
            return
        
        self.google_shopping_system_prompt_text.configure(state="normal", text_color="#FFFFFF")
        self.google_system_locked = False
        
        self.google_system_edit_btn.pack_forget()
        self.google_system_save_btn.pack(side="right")
        
        self.show_prompts_status("🔓 Prompt système Google Shopping déverrouillé (édition activée)", "#FFA500")
        logger.info("Prompt système Google Shopping déverrouillé pour édition")
    
    def lock_google_system_prompt(self):
        """Verrouille le prompt système Google Shopping et sauvegarde."""
        if not hasattr(self, 'google_shopping_system_prompt_text'):
            return
        
        if self.current_prompt_set_id:
            google_sys_prompt = self.google_shopping_system_prompt_text.get("1.0", "end-1c")
            
            self.db.update_prompt_set(
                self.current_prompt_set_id,
                google_shopping_system_prompt=google_sys_prompt
            )
        
        self.google_shopping_system_prompt_text.configure(state="disabled", text_color="#888888")
        self.google_system_locked = True
        
        self.google_system_save_btn.pack_forget()
        self.google_system_edit_btn.pack(side="right", padx=5)
        
        self.show_prompts_status("🔒 Prompt système Google Shopping verrouillé et sauvegardé", "green")
        logger.info("Prompt système Google Shopping verrouillé et sauvegardé")
    
    def unlock_google_metier_prompt(self):
        """Déverrouille le prompt métier Google Shopping pour édition."""
        if not hasattr(self, 'google_category_prompt_text'):
            return
        
        self.google_category_prompt_text.configure(state="normal", text_color="#FFFFFF")
        self.google_metier_locked = False
        
        self.google_metier_edit_btn.pack_forget()
        self.google_metier_save_btn.pack(side="right")
        
        self.show_prompts_status("🔓 Prompt métier Google Shopping déverrouillé (édition activée)", "#FFA500")
        logger.info("Prompt métier Google Shopping déverrouillé pour édition")
    
    def lock_google_metier_prompt(self):
        """Verrouille le prompt métier Google Shopping et sauvegarde."""
        if not hasattr(self, 'google_category_prompt_text'):
            return
        
        if self.current_prompt_set_id:
            google_metier_prompt = self.google_category_prompt_text.get("1.0", "end-1c")
            
            self.db.update_prompt_set(
                self.current_prompt_set_id,
                google_category_prompt=google_metier_prompt
            )
        
        self.google_category_prompt_text.configure(state="disabled", text_color="#888888")
        self.google_metier_locked = True
        
        self.google_metier_save_btn.pack_forget()
        self.google_metier_edit_btn.pack(side="right", padx=5)
        
        self.show_prompts_status("🔒 Prompt métier Google Shopping verrouillé et sauvegardé", "green")
        logger.info("Prompt métier Google Shopping verrouillé et sauvegardé")
    
    def save_prompt_set(self):
        """Sauvegarde l'ensemble de prompts."""
        if not self.current_prompt_set_id:
            self.show_prompts_status("⚠️ Sélectionnez d'abord un ensemble de prompts", "orange")
            return
        
        # Récupérer les 4 prompts
        seo_sys_prompt = self.seo_system_prompt_text.get("1.0", "end-1c")
        google_sys_prompt = self.google_shopping_system_prompt_text.get("1.0", "end-1c")
        
        self.db.update_prompt_set(
            self.current_prompt_set_id,
            system_prompt=seo_sys_prompt,  # Pour compatibilité
            seo_prompt=self.seo_prompt_text.get("1.0", "end-1c"),
            google_category_prompt=self.google_category_prompt_text.get("1.0", "end-1c"),
            seo_system_prompt=seo_sys_prompt,
            google_shopping_system_prompt=google_sys_prompt
        )
        self.show_prompts_status("✓ Ensemble de prompts sauvegardé", "green")
    
    # ========== Section 3: Chargement CSV ==========
    
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
        
        load_csv_button = ctk.CTkButton(
            csv_frame,
            text="📁 Charger un fichier CSV",
            command=self.load_csv_file,
            width=250,
            height=30
        )
        load_csv_button.pack(side="left", padx=20, pady=(0, 20))
        
        self.csv_info_label = ctk.CTkLabel(
            csv_frame,
            text="Aucun fichier chargé",
            font=ctk.CTkFont(size=12),
            text_color="gray"
        )
        self.csv_info_label.pack(side="left", padx=20, pady=(0, 20))
    
    def load_csv_file(self):
        """Charge un fichier CSV."""
        file_path = filedialog.askopenfilename(
            title="Sélectionner un fichier CSV",
            filetypes=[("CSV files", "*.csv"), ("All files", "*.*")]
        )
        
        if file_path:
            try:
                self.csv_path = file_path
                self.csv_import_id = self.csv_storage.import_csv(file_path)
                
                # Récupérer les handles uniques
                handles = self.csv_storage.get_unique_handles(self.csv_import_id)
                
                self.csv_info_label.configure(
                    text=f"✓ {len(handles)} produit(s) chargé(s) depuis {os.path.basename(file_path)}",
                    text_color="green"
                )
                
                # Activer les boutons de traitement
                self.start_processing_button.configure(state="normal")
                self.export_csv_button.configure(state="normal")
                
                logger.info(f"CSV chargé avec succès: {len(handles)} produits")
                
            except ValueError as e:
                # Erreur de validation du format Shopify
                logger.error(f"Erreur de validation: {e}")
                self.csv_info_label.configure(
                    text=f"❌ Erreur de validation: {str(e)}",
                    text_color="red"
                )
            except Exception as e:
                logger.error(f"Erreur lors du chargement du CSV: {e}", exc_info=True)
                self.csv_info_label.configure(
                    text=f"❌ Erreur: {str(e)}",
                    text_color="red"
                )
    
    # ========== Section 4: Configuration du batch ==========
    
    def create_batch_config_section(self, parent):
        """Crée la section de configuration du nombre de lignes par batch."""
        batch_frame = ctk.CTkFrame(parent)
        batch_frame.pack(fill="x", pady=(0, 20))
        
        batch_title = ctk.CTkLabel(
            batch_frame,
            text="Configuration du traitement",
            font=ctk.CTkFont(size=16, weight="bold")
        )
        batch_title.pack(anchor="w", padx=20, pady=(20, 10))
        
        # Configuration du batch size
        batch_size_frame = ctk.CTkFrame(batch_frame)
        batch_size_frame.pack(fill="x", padx=20, pady=(0, 10))
        
        batch_label = ctk.CTkLabel(
            batch_size_frame,
            text="Produits par batch:",
            width=200
        )
        batch_label.pack(side="left", padx=10)
        
        # Utiliser le ComboBox sans variable liée pour éviter les problèmes de callback
        self.batch_dropdown = ctk.CTkComboBox(
            batch_size_frame,
            values=["1", "5", "10", "20", "50"],
            width=100,
            state="readonly"
        )
        self.batch_dropdown.set("20")  # Valeur par défaut
        self.batch_dropdown.pack(side="left", padx=10)
        
        # Bouton pour sauvegarder le batch size
        save_batch_button = ctk.CTkButton(
            batch_size_frame,
            text="💾 Sauvegarder",
            width=120,
            command=self.save_batch_size
        )
        save_batch_button.pack(side="left", padx=10)
        
        batch_info = ctk.CTkLabel(
            batch_size_frame,
            text="(nombre de produits traités simultanément)",
            font=ctk.CTkFont(size=11),
            text_color="gray"
        )
        batch_info.pack(side="left", padx=10)
        
        # Label de confirmation de sauvegarde
        self.batch_save_status_label = ctk.CTkLabel(
            batch_frame,
            text="",
            font=ctk.CTkFont(size=11),
            text_color="green"
        )
        self.batch_save_status_label.pack(fill="x", padx=20, pady=(0, 10))
        
        # Charger la valeur depuis la base de données
        self.load_batch_size()
    
    
    def save_batch_size(self):
        """Sauvegarde la taille du batch dans la base de données."""
        try:
            batch_size_str = self.batch_dropdown.get()
            if not batch_size_str or batch_size_str == "":
                self.batch_dropdown.set("20")
                return
            
            batch_size = int(batch_size_str)
            
            self.db.save_config('batch_size', batch_size)
            logger.info(f"Taille du batch sauvegardée: {batch_size}")
            
            # Afficher le message de confirmation
            self.batch_save_status_label.configure(text=f"✓ Sauvegardé (batch_size = {batch_size})")
            
            # Faire disparaître le message après 2 secondes
            self.after(2000, lambda: self.batch_save_status_label.configure(text=""))
            
        except ValueError:
            logger.error(f"Valeur invalide pour la taille du batch: {batch_size_str}")
            self.batch_dropdown.set("20")
            self.batch_save_status_label.configure(text="✗ Erreur: valeur invalide", text_color="red")
            self.after(2000, lambda: self.batch_save_status_label.configure(text="", text_color="green"))
        except Exception as e:
            logger.error(f"Erreur lors de la sauvegarde du batch size: {e}", exc_info=True)
            self.batch_save_status_label.configure(text="✗ Erreur de sauvegarde", text_color="red")
            self.after(2000, lambda: self.batch_save_status_label.configure(text="", text_color="green"))
    
    def load_batch_size(self):
        """Charge la taille du batch depuis la base de données."""
        try:
            batch_size = self.db.get_config_int('batch_size', default=20)
            # S'assurer que la valeur est dans la liste autorisée
            batch_size_str = str(batch_size)
            if batch_size_str not in ["1", "5", "10", "20", "50"]:
                batch_size_str = "20"  # Fallback si valeur invalide
            self.batch_dropdown.set(batch_size_str)
            logger.info(f"Taille du batch chargée: {batch_size}")
        except Exception as e:
            logger.error(f"Erreur lors du chargement du batch size: {e}", exc_info=True)
            self.batch_dropdown.set("20")  # Valeur par défaut en cas d'erreur
    
    
    # ========== Section 5: Sélection des champs ==========
    
    def create_fields_section(self, parent):
        """Crée la section de sélection des champs à traiter."""
        fields_frame = ctk.CTkFrame(parent)
        fields_frame.pack(fill="x", pady=(0, 20))
        
        fields_title = ctk.CTkLabel(
            fields_frame,
            text="Champs à traiter",
            font=ctk.CTkFont(size=16, weight="bold")
        )
        fields_title.pack(anchor="w", padx=20, pady=(20, 10))
        
        # 1. Agent SEO avec sous-checkboxes
        seo_main_frame = ctk.CTkFrame(fields_frame)
        seo_main_frame.pack(fill="x", padx=20, pady=(0, 10))
        
        # Checkbox principale SEO
        self.seo_enabled_var = ctk.BooleanVar(value=True)
        seo_main_checkbox = ctk.CTkCheckBox(
            seo_main_frame,
            text="Agent SEO",
            variable=self.seo_enabled_var,
            command=self.on_seo_toggled,
            font=ctk.CTkFont(size=13, weight="bold")
        )
        seo_main_checkbox.pack(anchor="w", padx=10, pady=(10, 5))
        
        # Sous-frame avec les 6 champs SEO
        self.seo_fields_frame = ctk.CTkFrame(seo_main_frame)
        self.seo_fields_frame.pack(fill="x", padx=10, pady=(0, 10))
        
        self.seo_field_vars = {
            'seo_title': ctk.BooleanVar(value=True),
            'seo_description': ctk.BooleanVar(value=True),
            'title': ctk.BooleanVar(value=True),
            'body_html': ctk.BooleanVar(value=True),
            'tags': ctk.BooleanVar(value=True),
            'image_alt_text': ctk.BooleanVar(value=True)
        }
        
        seo_field_labels = {
            'seo_title': 'SEO Title',
            'seo_description': 'SEO Description',
            'title': 'Title',
            'body_html': 'Body (HTML)',
            'tags': 'Tags',
            'image_alt_text': 'Image Alt Text'
        }
        
        for field_key, label in seo_field_labels.items():
            checkbox = ctk.CTkCheckBox(
                self.seo_fields_frame,
                text=label,
                variable=self.seo_field_vars[field_key]
            )
            checkbox.pack(anchor="w", padx=40, pady=2)
        
        # 2. Agent Google Shopping (simple checkbox)
        self.google_category_var = ctk.BooleanVar(value=True)
        google_checkbox = ctk.CTkCheckBox(
            fields_frame,
            text="Google Shopping Category",
            variable=self.google_category_var,
            font=ctk.CTkFont(size=13, weight="bold")
        )
        google_checkbox.pack(anchor="w", padx=20, pady=5)
    
    def on_seo_toggled(self):
        """Appelé quand la checkbox principale SEO change."""
        if self.seo_enabled_var.get():
            # Activer les sous-checkboxes
            for checkbox_var in self.seo_field_vars.values():
                # Réactiver les widgets enfants
                for widget in self.seo_fields_frame.winfo_children():
                    widget.configure(state="normal")
        else:
            # Désactiver les sous-checkboxes
            for widget in self.seo_fields_frame.winfo_children():
                widget.configure(state="disabled")
    
    # ========== ONGLET TEST ==========
    
    def create_test_tab(self):
        """Crée l'onglet de test avec un seul produit."""
        # Frame scrollable
        test_scroll = ctk.CTkScrollableFrame(self.tab_test)
        test_scroll.pack(fill="both", expand=True, padx=10, pady=10)
        
        # Titre
        title = ctk.CTkLabel(
            test_scroll,
            text="Zone de test - Tester avec un seul produit",
            font=ctk.CTkFont(size=18, weight="bold")
        )
        title.pack(pady=(10, 20))
        
        # Section recherche
        search_frame = ctk.CTkFrame(test_scroll)
        search_frame.pack(fill="x", padx=20, pady=(0, 20))
        
        search_title = ctk.CTkLabel(
            search_frame,
            text="Rechercher un article",
            font=ctk.CTkFont(size=14, weight="bold")
        )
        search_title.pack(anchor="w", padx=20, pady=(10, 5))
        
        # Champ de recherche
        search_input_frame = ctk.CTkFrame(search_frame)
        search_input_frame.pack(fill="x", padx=20, pady=(0, 10))
        
        search_label = ctk.CTkLabel(search_input_frame, text="Nom de l'article:", width=150)
        search_label.pack(side="left", padx=10)
        
        self.search_var = ctk.StringVar()
        self.search_entry = ctk.CTkEntry(
            search_input_frame,
            textvariable=self.search_var,
            placeholder_text="Tapez pour rechercher...",
            width=400
        )
        self.search_entry.pack(side="left", padx=10, fill="x", expand=True)
        self.search_entry.bind("<KeyRelease>", self.on_search_changed)
        
        # Liste des résultats
        results_label = ctk.CTkLabel(
            search_frame,
            text="Résultats de recherche:",
            font=ctk.CTkFont(size=12)
        )
        results_label.pack(anchor="w", padx=20, pady=(10, 5))
        
        self.search_results_frame = ctk.CTkScrollableFrame(search_frame, height=200)
        self.search_results_frame.pack(fill="x", padx=20, pady=(0, 10))
        
        self.search_result_radios = []
        self.selected_test_handle = ctk.StringVar(value="")
        
        # Message initial
        self.no_results_label = ctk.CTkLabel(
            self.search_results_frame,
            text="Chargez un CSV et recherchez un article",
            text_color="gray"
        )
        self.no_results_label.pack(pady=20)
        
        # Bouton tester
        test_button_frame = ctk.CTkFrame(search_frame)
        test_button_frame.pack(fill="x", padx=20, pady=(10, 20))
        
        self.test_button = ctk.CTkButton(
            test_button_frame,
            text="🧪 Tester avec cet article",
            command=self.test_selected_article,
            width=250,
            height=35,
            fg_color="blue",
            hover_color="darkblue",
            state="disabled"
        )
        self.test_button.pack(pady=10)
        
        # Section résultats
        results_frame = ctk.CTkFrame(test_scroll)
        results_frame.pack(fill="both", expand=True, padx=20, pady=(0, 20))
        
        results_title = ctk.CTkLabel(
            results_frame,
            text="Résultats du test",
            font=ctk.CTkFont(size=14, weight="bold")
        )
        results_title.pack(anchor="w", padx=20, pady=(10, 5))
        
        # Frame de résultats
        self.test_results_frame = ctk.CTkScrollableFrame(results_frame, height=400)
        self.test_results_frame.pack(fill="both", expand=True, padx=20, pady=(0, 20))
        
        # Message initial
        self.test_no_results_label = ctk.CTkLabel(
            self.test_results_frame,
            text="Sélectionnez un article et lancez le test pour voir les résultats",
            text_color="gray"
        )
        self.test_no_results_label.pack(pady=50)
    
    def on_search_changed(self, event=None):
        """Appelé quand l'utilisateur tape dans le champ de recherche."""
        query = self.search_var.get().strip().lower()
        
        if not self.csv_import_id or not query:
            # Effacer les résultats
            for widget in self.search_results_frame.winfo_children():
                widget.destroy()
            
            self.no_results_label = ctk.CTkLabel(
                self.search_results_frame,
                text="Tapez au moins 2 caractères pour rechercher",
                text_color="gray"
            )
            self.no_results_label.pack(pady=20)
            return
        
        if len(query) < 2:
            return
        
        # Rechercher les handles
        try:
            all_handles = self.csv_storage.get_unique_handles(self.csv_import_id)
            
            # Récupérer les titres pour chaque handle
            matching_products = []
            for handle in all_handles:
                rows = self.csv_storage.get_csv_rows(self.csv_import_id, handles={handle})
                if rows:
                    product_data = rows[0]['data']
                    title = product_data.get('Title', '')
                    
                    # Recherche dans le titre et le handle
                    if query in title.lower() or query in handle.lower():
                        matching_products.append({
                            'handle': handle,
                            'title': title
                        })
            
            # Afficher les résultats
            for widget in self.search_results_frame.winfo_children():
                widget.destroy()
            
            if matching_products:
                for product in matching_products[:20]:  # Limiter à 20 résultats
                    radio = ctk.CTkRadioButton(
                        self.search_results_frame,
                        text=f"{product['title'][:80]} ({product['handle']})",
                        variable=self.selected_test_handle,
                        value=product['handle'],
                        command=self.on_test_selection_changed
                    )
                    radio.pack(anchor="w", padx=10, pady=2)
            else:
                self.no_results_label = ctk.CTkLabel(
                    self.search_results_frame,
                    text="Aucun résultat trouvé",
                    text_color="gray"
                )
                self.no_results_label.pack(pady=20)
        
        except Exception as e:
            logger.error(f"Erreur lors de la recherche: {e}")
    
    def on_test_selection_changed(self):
        """Appelé quand un article est sélectionné pour le test."""
        self.test_button.configure(state="normal" if self.selected_test_handle.get() else "disabled")
    
    def test_selected_article(self):
        """Teste le traitement avec l'article sélectionné."""
        handle = self.selected_test_handle.get()
        
        if not handle:
            messagebox.showwarning("Attention", "Veuillez sélectionner un article")
            return
        
        if not self.current_prompt_set_id:
            messagebox.showwarning("Attention", "Veuillez sélectionner un ensemble de prompts dans l'onglet Configuration")
            return
        
        provider = self.provider_var.get()
        model = self.model_var.get()
        
        if not model:
            messagebox.showwarning("Attention", "Veuillez sélectionner un modèle dans l'onglet Configuration")
            return
        
        # Récupérer les champs sélectionnés
        selected_fields = {
            'seo': {
                'enabled': self.seo_enabled_var.get(),
                'fields': [
                    field_key 
                    for field_key, var in self.seo_field_vars.items() 
                    if var.get()
                ]
            },
            'google_category': self.google_category_var.get()
        }
        
        # Vérifier qu'au moins un agent est activé
        seo_enabled = selected_fields['seo']['enabled'] and len(selected_fields['seo']['fields']) > 0
        google_enabled = selected_fields['google_category']
        
        if not (seo_enabled or google_enabled):
            messagebox.showwarning("Attention", "Veuillez sélectionner au moins un champ à traiter dans l'onglet Configuration")
            return
        
        # Désactiver le bouton pendant le traitement
        self.test_button.configure(state="disabled", text="Traitement en cours...")
        
        # Effacer les résultats précédents
        for widget in self.test_results_frame.winfo_children():
            widget.destroy()
        
        # Label de traitement en cours
        processing_label = ctk.CTkLabel(
            self.test_results_frame,
            text="⏳ Traitement en cours...",
            font=ctk.CTkFont(size=14),
            text_color="#FFFF99"
        )
        processing_label.pack(pady=30)
        
        # Récupérer l'état de la recherche Internet
        enable_search = self.enable_search_var.get()
        
        def process_thread():
            try:
                # Créer une nouvelle connexion DB pour ce thread
                thread_db = AIPromptsDB()
                processor = CSVAIProcessor(thread_db)
                
                success, changes_dict = processor.process_single_product(
                    self.csv_import_id,
                    handle,
                    self.current_prompt_set_id,
                    provider,
                    model,
                    selected_fields,
                    log_callback=None,
                    enable_search=enable_search
                )
                
                # Fermer la connexion du thread
                thread_db.close()
                
                # Mettre à jour l'interface dans le thread principal
                if hasattr(self, 'winfo_exists') and self.winfo_exists():
                    self.after(0, lambda: self.display_test_results(success, handle, changes_dict))
            
            except Exception as e:
                # Détecter les erreurs de quota spécifiquement
                from utils.ai_providers import AIQuotaError
                
                if isinstance(e, AIQuotaError):
                    # Message clair pour les erreurs de quota
                    error_msg = f"⚠️ QUOTA {e.provider.upper()} DÉPASSÉ\n\n"
                    error_msg += f"Votre quota {e.provider} est épuisé.\n\n"
                    error_msg += "💡 Solutions:\n"
                    error_msg += f"  1. Vérifiez votre compte {e.provider}\n"
                    error_msg += "  2. Ajoutez des crédits si nécessaire\n"
                    error_msg += "  3. Attendez le renouvellement du quota\n"
                    error_msg += f"  4. Changez de modèle IA dans Configuration\n\n"
                    error_msg += f"Détails: {e.original_error}"
                else:
                    error_msg = str(e)
                
                logger.error(f"Erreur lors du test: {e}", exc_info=True)
                if hasattr(self, 'winfo_exists') and self.winfo_exists():
                    self.after(0, lambda: self.display_test_error(error_msg))
        
        threading.Thread(target=process_thread, daemon=True).start()
    
    def display_test_results(self, success: bool, handle: str, changes_dict: Dict):
        """Affiche les résultats du test."""
        # Réactiver le bouton
        self.test_button.configure(state="normal", text="🧪 Tester avec cet article")
        
        # Effacer les widgets
        for widget in self.test_results_frame.winfo_children():
            widget.destroy()
        
        if not success or not changes_dict:
            error_label = ctk.CTkLabel(
                self.test_results_frame,
                text="❌ Aucune modification générée",
                font=ctk.CTkFont(size=14),
                text_color="red"
            )
            error_label.pack(pady=30)
            return
        
        # Titre de succès
        success_label = ctk.CTkLabel(
            self.test_results_frame,
            text=f"✅ Test réussi pour: {handle}",
            font=ctk.CTkFont(size=14, weight="bold"),
            text_color="green"
        )
        success_label.pack(pady=(10, 20))
        
        # Afficher chaque champ modifié
        for field_name, change_data in changes_dict.items():
            field_frame = ctk.CTkFrame(self.test_results_frame)
            field_frame.pack(fill="x", padx=10, pady=10)
            
            # Nom du champ
            field_label = ctk.CTkLabel(
                field_frame,
                text=f"📝 {field_name}",
                font=ctk.CTkFont(size=13, weight="bold")
            )
            field_label.pack(anchor="w", padx=10, pady=(10, 5))
            
            # Avant
            before_label = ctk.CTkLabel(
                field_frame,
                text="Avant:",
                font=ctk.CTkFont(size=11, weight="bold"),
                text_color="gray"
            )
            before_label.pack(anchor="w", padx=10, pady=(5, 2))
            
            # Doubler la hauteur pour Body (HTML)
            before_height = 120 if field_name == "Body (HTML)" else 60
            before_text = ctk.CTkTextbox(field_frame, height=before_height, wrap="word")
            before_text.pack(fill="x", padx=10, pady=(0, 10))
            before_text.insert("1.0", change_data['original'] or "(vide)")
            before_text.configure(state="disabled")
            
            # Après
            after_label = ctk.CTkLabel(
                field_frame,
                text="Après:",
                font=ctk.CTkFont(size=11, weight="bold"),
                text_color="green"
            )
            after_label.pack(anchor="w", padx=10, pady=(5, 2))
            
            # Doubler la hauteur pour Body (HTML)
            after_height = 120 if field_name == "Body (HTML)" else 60
            after_text = ctk.CTkTextbox(field_frame, height=after_height, wrap="word")
            after_text.pack(fill="x", padx=10, pady=(0, 10))
            after_text.insert("1.0", change_data['new'])
            after_text.configure(state="disabled", fg_color=("gray85", "gray25"))
            
            # Pour Body (HTML), ajouter un aperçu du rendu HTML
            if field_name == "Body (HTML)" and change_data['new']:
                html_preview_label = ctk.CTkLabel(
                    field_frame,
                    text="Aperçu du rendu HTML:",
                    font=ctk.CTkFont(size=11, weight="bold"),
                    text_color="blue"
                )
                html_preview_label.pack(anchor="w", padx=10, pady=(5, 2))
                
                # Créer un textbox pour le rendu HTML (simulé en texte)
                html_preview = ctk.CTkTextbox(field_frame, height=150, wrap="word")
                html_preview.pack(fill="x", padx=10, pady=(0, 10))
                
                # Convertir le HTML en texte simple pour l'aperçu
                import html
                from html.parser import HTMLParser
                
                class HTMLTextExtractor(HTMLParser):
                    def __init__(self):
                        super().__init__()
                        self.text_parts = []
                        self.in_list = False
                    
                    def handle_starttag(self, tag, attrs):
                        if tag == 'p':
                            self.text_parts.append('\n')
                        elif tag == 'br':
                            self.text_parts.append('\n')
                        elif tag in ['ul', 'ol']:
                            self.in_list = True
                            self.text_parts.append('\n')
                        elif tag == 'li' and self.in_list:
                            self.text_parts.append('\n  • ')
                        elif tag == 'strong':
                            self.text_parts.append('**')
                        elif tag == 'em':
                            self.text_parts.append('_')
                    
                    def handle_endtag(self, tag):
                        if tag == 'p':
                            self.text_parts.append('\n')
                        elif tag in ['ul', 'ol']:
                            self.in_list = False
                            self.text_parts.append('\n')
                        elif tag == 'strong':
                            self.text_parts.append('**')
                        elif tag == 'em':
                            self.text_parts.append('_')
                    
                    def handle_data(self, data):
                        self.text_parts.append(data.strip())
                    
                    def get_text(self):
                        return ''.join(self.text_parts).strip()
                
                try:
                    parser = HTMLTextExtractor()
                    parser.feed(change_data['new'])
                    rendered_text = parser.get_text()
                    html_preview.insert("1.0", rendered_text)
                except Exception as e:
                    html_preview.insert("1.0", f"Erreur lors du rendu HTML: {e}")
                
                html_preview.configure(state="disabled", fg_color=("white", "gray20"))
    
    def display_test_error(self, error_msg: str):
        """Affiche une erreur de test avec barre de défilement."""
        # Réactiver le bouton
        self.test_button.configure(state="normal", text="🧪 Tester avec cet article")
        
        # Effacer les widgets
        for widget in self.test_results_frame.winfo_children():
            widget.destroy()
        
        # Frame pour l'erreur
        error_frame = ctk.CTkFrame(self.test_results_frame, fg_color="#2B0000", corner_radius=10)
        error_frame.pack(fill="both", expand=True, padx=20, pady=20)
        
        # Titre
        title_label = ctk.CTkLabel(
            error_frame,
            text="❌ Erreur:",
            font=ctk.CTkFont(size=14, weight="bold"),
            text_color="#FF6B6B"
        )
        title_label.pack(padx=20, pady=(20, 10), anchor="w")
        
        # Textbox avec scrollbar pour le message d'erreur
        error_textbox = ctk.CTkTextbox(
            error_frame,
            font=ctk.CTkFont(size=12),
            fg_color="#3B0000",
            text_color="#FF6B6B",
            wrap="word",
            height=300  # Hauteur fixe pour forcer la scrollbar si nécessaire
        )
        error_textbox.pack(fill="both", expand=True, padx=20, pady=(0, 20))
        
        # Insérer le message d'erreur
        error_textbox.insert("1.0", error_msg)
        
        # Rendre le textbox en lecture seule
        error_textbox.configure(state="disabled")
    
    # ========== ONGLET TRAITEMENT ==========
    
    def create_processing_tab(self):
        """Crée l'onglet de traitement complet."""
        # Frame principal avec barre de défilement
        processing_frame = ctk.CTkScrollableFrame(self.tab_processing)
        processing_frame.pack(fill="both", expand=True, padx=10, pady=10)
        
        # Titre
        title = ctk.CTkLabel(
            processing_frame,
            text="Traitement complet du fichier CSV",
            font=ctk.CTkFont(size=18, weight="bold")
        )
        title.pack(pady=(10, 20))
        
        # Configuration
        config_frame = ctk.CTkFrame(processing_frame)
        config_frame.pack(fill="x", padx=20, pady=(0, 10))
        
        # Sélection des produits
        selection_label = ctk.CTkLabel(
            config_frame,
            text="Sélection des produits",
            font=ctk.CTkFont(size=14, weight="bold")
        )
        selection_label.pack(anchor="w", padx=20, pady=(10, 5))
        
        self.process_all_var = ctk.BooleanVar(value=True)
        process_all_checkbox = ctk.CTkCheckBox(
            config_frame,
            text="Traiter tous les produits",
            variable=self.process_all_var
        )
        process_all_checkbox.pack(anchor="w", padx=40, pady=5)
        
        # Boutons d'action
        action_frame = ctk.CTkFrame(processing_frame)
        action_frame.pack(fill="x", padx=20, pady=(10, 10))
        
        self.start_processing_button = ctk.CTkButton(
            action_frame,
            text="▶️ Démarrer le traitement",
            command=self.start_full_processing,
            width=250,
            height=40,
            fg_color="green",
            hover_color="darkgreen",
            font=ctk.CTkFont(size=14, weight="bold"),
            state="disabled"
        )
        self.start_processing_button.pack(side="left", padx=20, pady=10)
        
        self.export_csv_button = ctk.CTkButton(
            action_frame,
            text="💾 Générer le CSV",
            command=self.generate_csv,
            width=200,
            height=40,
            fg_color="blue",
            hover_color="darkblue",
            font=ctk.CTkFont(size=14, weight="bold"),
            state="disabled"
        )
        self.export_csv_button.pack(side="left", padx=20, pady=10)
        
        # Barre de progression
        progress_frame = ctk.CTkFrame(processing_frame)
        progress_frame.pack(fill="x", padx=20, pady=(10, 5))
        
        self.processing_progress_label = ctk.CTkLabel(
            progress_frame,
            text="En attente...",
            font=ctk.CTkFont(size=12)
        )
        self.processing_progress_label.pack(anchor="w", padx=10, pady=(5, 2))
        
        self.processing_progress_bar = ctk.CTkProgressBar(progress_frame)
        self.processing_progress_bar.pack(fill="x", padx=10, pady=(0, 10))
        self.processing_progress_bar.set(0)
        
        # Zone de logs
        logs_label = ctk.CTkLabel(
            processing_frame,
            text="Logs du traitement:",
            font=ctk.CTkFont(size=12, weight="bold")
        )
        logs_label.pack(anchor="w", padx=20, pady=(10, 5))
        
        self.processing_logs_textbox = ctk.CTkTextbox(
            processing_frame,
            height=400,
            state="disabled",
            wrap="word"
        )
        self.processing_logs_textbox.pack(fill="both", expand=True, padx=20, pady=(0, 20))
    
    def start_reprocessing(self, handles_to_reprocess: list, use_diagnostic_logs: bool = False):
        """
        Démarre le retraitement séquentiel des produits en erreur.
        
        Args:
            handles_to_reprocess: Liste des handles à retraiter
            use_diagnostic_logs: Si True, utilise les logs du diagnostic au lieu de ceux du traitement
        """
        if not self.csv_import_id:
            logger.info("Aucun CSV chargé")
            return
        
        if not self.current_prompt_set_id:
            logger.info("Aucun ensemble de prompts sélectionné")
            return
        
        provider = self.provider_var.get()
        model = self.model_var.get()
        
        if not model:
            logger.info("Aucun modèle sélectionné")
            return
        
        # Récupérer les champs sélectionnés (tous activés pour le retraitement)
        selected_fields = {
            'seo': {
                'enabled': True,
                'fields': list(SEO_FIELD_MAPPING.keys())  # Tous les champs SEO
            },
            'google_category': True
        }
        
        # Choisir la fonction de log à utiliser
        log_func = self.add_diagnostic_log if use_diagnostic_logs else self.add_processing_log
        
        # Désactiver les boutons
        self.start_processing_button.configure(state="disabled")
        
        # Effacer les logs (selon le contexte)
        if not use_diagnostic_logs:
            self.processing_logs_textbox.configure(state="normal")
            self.processing_logs_textbox.delete("1.0", "end")
            self.processing_logs_textbox.configure(state="disabled")
        
        # Réinitialiser la barre de progression
        self.processing_progress_bar.set(0)
        self.processing_progress_label.configure(text="Démarrage du retraitement séquentiel...")
        
        # Log du mode séquentiel
        log_func(f"🔄 RETRAITEMENT SÉQUENTIEL")
        log_func(f"📦 Produits à retraiter: {len(handles_to_reprocess)}")
        log_func(f"⚙️  Mode: 1 produit à la fois (séquentiel)")
        log_func(f"")
        
        # Récupérer l'état de la recherche Internet
        enable_search = self.enable_search_var.get()
        
        def process_thread():
            try:
                # Créer une nouvelle connexion DB pour ce thread
                thread_db = AIPromptsDB()
                processor = CSVAIProcessor(thread_db)
                
                # IMPORTANT: Forcer batch_size à 1 pour le mode séquentiel
                # Sauvegarder temporairement le batch_size actuel
                cursor = thread_db.conn.cursor()
                cursor.execute("SELECT value FROM app_config WHERE key = 'batch_size'")
                result = cursor.fetchone()
                original_batch_size = result[0] if result else "5"
                
                # Forcer batch_size à 1 pour le retraitement
                cursor.execute("""
                    INSERT OR REPLACE INTO app_config (key, value, updated_at)
                    VALUES ('batch_size', '1', CURRENT_TIMESTAMP)
                """)
                thread_db.conn.commit()
                
                try:
                    success, output_path, changes_dict, processing_result_id = processor.process_csv(
                        self.csv_path,
                        self.current_prompt_set_id,
                        provider,
                        model,
                        selected_fields,
                        handles_to_reprocess,  # Seulement les handles sélectionnés
                        progress_callback=self.update_processing_progress,
                        log_callback=log_func,
                        cancel_check=None,
                        enable_search=enable_search,
                        csv_import_id=self.csv_import_id  # Utiliser l'import existant
                    )
                finally:
                    # Restaurer le batch_size original
                    cursor.execute("""
                        INSERT OR REPLACE INTO app_config (key, value, updated_at)
                        VALUES ('batch_size', ?, CURRENT_TIMESTAMP)
                    """, (original_batch_size,))
                    thread_db.conn.commit()
                
                # Fermer la connexion du thread
                thread_db.close()
                
                # Finaliser dans le thread principal et rafraîchir le Diagnostic
                if hasattr(self, 'winfo_exists') and self.winfo_exists():
                    self.after(0, lambda: self.reprocessing_completed(success, output_path, changes_dict))
            
            except Exception as e:
                error_msg = str(e)
                logger.error(f"Erreur lors du retraitement: {e}", exc_info=True)
                if hasattr(self, 'winfo_exists') and self.winfo_exists():
                    self.after(0, lambda: self.processing_error(error_msg))
        
        threading.Thread(target=process_thread, daemon=True).start()
    
    def reprocessing_completed(self, success: bool, output_path: Optional[str], changes_dict: Dict):
        """Appelé quand le retraitement est terminé."""
        try:
            if not hasattr(self, 'winfo_exists') or not self.winfo_exists():
                return
            
            self.start_processing_button.configure(state="normal")
            self.export_csv_button.configure(state="normal")
            
            if success:
                self.processing_progress_bar.set(1.0)
                self.processing_progress_label.configure(
                    text=f"✅ Retraitement terminé: {len(changes_dict)} produit(s) traité(s)",
                    text_color="green"
                )
                self.add_processing_log(f"\n✅ Retraitement terminé avec succès!")
                if output_path:
                    self.add_processing_log(f"📄 Fichier généré: {output_path}")
                else:
                    self.add_processing_log(f"💡 Cliquez sur 'Générer CSV' pour exporter le fichier")
                
                # Rafraîchir le Diagnostic
                if hasattr(self, 'load_diagnostic_summary'):
                    self.load_diagnostic_summary()
            else:
                self.processing_progress_label.configure(
                    text="❌ Le retraitement a échoué",
                    text_color="red"
                )
        except Exception as e:
            logger.error(f"Erreur dans reprocessing_completed: {e}")
    
    def start_full_processing(self):
        """Démarre le traitement complet."""
        if not self.csv_import_id:
            messagebox.showwarning("Attention", "Veuillez charger un fichier CSV")
            return
        
        if not self.current_prompt_set_id:
            messagebox.showwarning("Attention", "Veuillez sélectionner un ensemble de prompts")
            return
        
        provider = self.provider_var.get()
        model = self.model_var.get()
        
        if not model:
            messagebox.showwarning("Attention", "Veuillez sélectionner un modèle")
            return
        
        # Récupérer les champs sélectionnés
        selected_fields = {
            'seo': {
                'enabled': self.seo_enabled_var.get(),
                'fields': [
                    field_key 
                    for field_key, var in self.seo_field_vars.items() 
                    if var.get()
                ]
            },
            'google_category': self.google_category_var.get()
        }
        
        # Vérifier qu'au moins un agent est activé
        seo_enabled = selected_fields['seo']['enabled'] and len(selected_fields['seo']['fields']) > 0
        google_enabled = selected_fields['google_category']
        
        if not (seo_enabled or google_enabled):
            messagebox.showwarning("Attention", "Veuillez sélectionner au moins un champ à traiter")
            return
        
        # Récupérer la sélection
        if self.process_all_var.get():
            selected_handles = None
        else:
            messagebox.showinfo("Information", "La sélection manuelle n'est pas encore implémentée. Tous les produits seront traités.")
            selected_handles = None
        
        # Désactiver le bouton
        self.start_processing_button.configure(state="disabled")
        
        # Effacer les logs
        self.processing_logs_textbox.configure(state="normal")
        self.processing_logs_textbox.delete("1.0", "end")
        self.processing_logs_textbox.configure(state="disabled")
        
        # Réinitialiser la barre de progression
        self.processing_progress_bar.set(0)
        self.processing_progress_label.configure(text="Démarrage du traitement...")
        
        # Récupérer l'état de la recherche Internet
        enable_search = self.enable_search_var.get()
        
        def process_thread():
            try:
                # Créer une nouvelle connexion DB pour ce thread
                thread_db = AIPromptsDB()
                processor = CSVAIProcessor(thread_db)
                
                success, output_path, changes_dict, processing_result_id = processor.process_csv(
                    self.csv_path,
                    self.current_prompt_set_id,
                    provider,
                    model,
                    selected_fields,
                    selected_handles,
                    progress_callback=self.update_processing_progress,
                    log_callback=self.add_processing_log,
                    cancel_check=None,
                    enable_search=enable_search
                )
                
                # Fermer la connexion du thread
                thread_db.close()
                
                # Finaliser dans le thread principal
                if hasattr(self, 'winfo_exists') and self.winfo_exists():
                    self.after(0, lambda: self.processing_completed(success, output_path, changes_dict))
            
            except Exception as e:
                error_msg = str(e)
                logger.error(f"Erreur lors du traitement: {e}", exc_info=True)
                if hasattr(self, 'winfo_exists') and self.winfo_exists():
                    self.after(0, lambda: self.processing_error(error_msg))
        
        threading.Thread(target=process_thread, daemon=True).start()
    
    def update_processing_progress(self, message: str, current: int, total: int):
        """Met à jour la barre de progression."""
        try:
            if hasattr(self, 'winfo_exists') and self.winfo_exists():
                progress = current / total if total > 0 else 0
                self.processing_progress_bar.set(progress)
                self.processing_progress_label.configure(
                    text=f"{message} ({current}/{total})"
                )
        except Exception:
            pass
    
    def add_processing_log(self, message: str):
        """Ajoute un message dans les logs."""
        try:
            if hasattr(self, 'winfo_exists') and self.winfo_exists():
                self.processing_logs_textbox.configure(state="normal")
                self.processing_logs_textbox.insert("end", f"{message}\n")
                self.processing_logs_textbox.see("end")
                self.processing_logs_textbox.configure(state="disabled")
        except Exception:
            pass
    
    def add_diagnostic_log(self, message: str):
        """Ajoute un message dans les logs du diagnostic."""
        try:
            if hasattr(self, 'winfo_exists') and self.winfo_exists():
                if hasattr(self, 'diagnostic_logs_textbox'):
                    self.diagnostic_logs_textbox.configure(state="normal")
                    self.diagnostic_logs_textbox.insert("end", f"{message}\n")
                    self.diagnostic_logs_textbox.see("end")
                    self.diagnostic_logs_textbox.configure(state="disabled")
        except Exception:
            pass
    
    def processing_completed(self, success: bool, output_path: Optional[str], changes_dict: Dict):
        """Appelé quand le traitement est terminé."""
        try:
            if not hasattr(self, 'winfo_exists') or not self.winfo_exists():
                return
            
            self.start_processing_button.configure(state="normal")
            self.export_csv_button.configure(state="normal")
            
            if success:
                self.processing_progress_bar.set(1.0)
                self.processing_progress_label.configure(
                    text=f"✅ Traitement terminé: {len(changes_dict)} produit(s) modifié(s)",
                    text_color="green"
                )
                self.add_processing_log(f"\n✅ Traitement terminé avec succès!")
                if output_path:
                    self.add_processing_log(f"📄 Fichier généré: {output_path}")
                else:
                    self.add_processing_log(f"💡 Cliquez sur 'Générer CSV' pour exporter le fichier")
            else:
                self.processing_progress_label.configure(
                    text="❌ Le traitement a échoué",
                    text_color="red"
                )
        except Exception as e:
            logger.error(f"Erreur dans processing_completed: {e}")
    
    def processing_error(self, error_msg: str):
        """Appelé en cas d'erreur lors du traitement."""
        try:
            if not hasattr(self, 'winfo_exists') or not self.winfo_exists():
                return
            
            self.start_processing_button.configure(state="normal")
            self.processing_progress_label.configure(
                text="❌ Erreur lors du traitement",
                text_color="red"
            )
            self.add_processing_log(f"\n❌ Erreur: {error_msg}")
        except Exception as e:
            logger.error(f"Erreur dans processing_error: {e}")
    
    def generate_csv(self):
        """Génère le CSV à partir de la table csv_rows."""
        if not self.csv_import_id:
            messagebox.showwarning("Attention", "Aucun fichier CSV chargé")
            return
        
        try:
            # Récupérer le chemin du fichier original
            cursor = self.csv_storage.db.conn.cursor()
            cursor.execute("SELECT original_file_path FROM csv_imports WHERE id = ?", (self.csv_import_id,))
            result = cursor.fetchone()
            
            if not result:
                messagebox.showerror("Erreur", "Import introuvable")
                return
            
            original_path = result[0]
            original_filename = os.path.basename(original_path)
            
            # Extraire le fournisseur et les catégories depuis le nom du fichier original
            # Format: shopify_import_<fournisseur>_<categories>_<timestamp>.csv
            supplier = None
            categories = None
            
            if original_filename.startswith("shopify_import_"):
                # Enlever "shopify_import_" et ".csv"
                name_part = original_filename.replace("shopify_import_", "").replace(".csv", "")
                parts = name_part.split("_")
                
                if len(parts) >= 1:
                    supplier = parts[0]  # artiga, cristel, garnier
                    
                    # Les catégories sont entre le fournisseur et le timestamp (dernières 2 parties: YYYYMMDD_HHMMSS)
                    if len(parts) >= 3:
                        # Vérifier si les 2 dernières parties sont un timestamp
                        if parts[-2].isdigit() and len(parts[-2]) == 8:  # YYYYMMDD
                            categories = "_".join(parts[1:-2])  # Tout sauf fournisseur et timestamp
                        else:
                            categories = "_".join(parts[1:])  # Tout sauf fournisseur
            
            # Générer le timestamp
            from datetime import datetime
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            
            # Construire le nom du fichier
            if supplier and categories:
                default_filename = f"ai_{supplier}_{categories}_{timestamp}.csv"
            elif supplier:
                default_filename = f"ai_{supplier}_{timestamp}.csv"
            else:
                default_filename = f"ai_export_{timestamp}.csv"
            
            # Déterminer le répertoire de sortie (outputs/<supplier>/)
            output_dir = os.path.join(os.getcwd(), "outputs", supplier) if supplier else os.path.join(os.getcwd(), "outputs")
            os.makedirs(output_dir, exist_ok=True)
            
            # Chemin complet par défaut
            default_path = os.path.join(output_dir, default_filename)
            
            # Demander où sauvegarder
            file_path = filedialog.asksaveasfilename(
                title="Sauvegarder le CSV",
                defaultextension=".csv",
                filetypes=[("CSV files", "*.csv"), ("All files", "*.*")],
                initialfile=default_filename,
                initialdir=output_dir
            )
            
            if file_path:
                self.csv_storage.export_csv(self.csv_import_id, file_path)
                messagebox.showinfo("Succès", f"CSV généré avec succès:\n{file_path}")
                self.add_processing_log(f"\n💾 CSV exporté: {file_path}")
        
        except Exception as e:
            logger.error(f"Erreur lors de l'export: {e}", exc_info=True)
            messagebox.showerror("Erreur", f"Erreur lors de la génération:\n{e}")
    
    # ========== ONGLET DIAGNOSTIC ==========
    
    def create_diagnostic_tab(self):
        """Crée l'onglet de diagnostic des erreurs."""
        # Frame scrollable
        diagnostic_scroll = ctk.CTkScrollableFrame(self.tab_diagnostic)
        diagnostic_scroll.pack(fill="both", expand=True, padx=20, pady=20)
        
        # Titre
        title_label = ctk.CTkLabel(
            diagnostic_scroll,
            text="🔍 Diagnostic et retraitement des erreurs",
            font=ctk.CTkFont(size=20, weight="bold")
        )
        title_label.pack(pady=(0, 20))
        
        # Section 1: Résumé des status
        summary_frame = ctk.CTkFrame(diagnostic_scroll)
        summary_frame.pack(fill="x", pady=(0, 20))
        
        summary_title = ctk.CTkLabel(
            summary_frame,
            text="📊 Résumé des status",
            font=ctk.CTkFont(size=16, weight="bold")
        )
        summary_title.pack(anchor="w", padx=20, pady=(20, 10))
        
        # Frame pour afficher les status
        self.status_summary_frame = ctk.CTkFrame(summary_frame)
        self.status_summary_frame.pack(fill="x", padx=20, pady=(0, 20))
        
        # Bouton pour rafraîchir
        refresh_button = ctk.CTkButton(
            summary_frame,
            text="🔄 Rafraîchir le résumé",
            command=self.load_diagnostic_summary
        )
        refresh_button.pack(pady=(0, 20))
        
        # Section 2: Liste des erreurs
        errors_frame = ctk.CTkFrame(diagnostic_scroll)
        errors_frame.pack(fill="both", expand=True, pady=(0, 20))
        
        errors_title = ctk.CTkLabel(
            errors_frame,
            text="⚠️ Produits en erreur",
            font=ctk.CTkFont(size=16, weight="bold")
        )
        errors_title.pack(anchor="w", padx=20, pady=(20, 10))
        
        # Barre d'actions de sélection
        selection_bar = ctk.CTkFrame(errors_frame)
        selection_bar.pack(fill="x", padx=20, pady=(0, 10))
        
        select_all_btn = ctk.CTkButton(
            selection_bar,
            text="✓ Tout sélectionner",
            command=self.select_all_errors,
            width=150
        )
        select_all_btn.pack(side="left", padx=5)
        
        deselect_all_btn = ctk.CTkButton(
            selection_bar,
            text="✗ Tout désélectionner",
            command=self.deselect_all_errors,
            width=150
        )
        deselect_all_btn.pack(side="left", padx=5)
        
        # Compteur de sélection
        self.error_selection_label = ctk.CTkLabel(
            selection_bar,
            text="0 produit(s) sélectionné(s)",
            font=ctk.CTkFont(size=12)
        )
        self.error_selection_label.pack(side="left", padx=20)
        
        # Frame scrollable pour les erreurs
        self.errors_list_frame = ctk.CTkScrollableFrame(errors_frame, height=300)
        self.errors_list_frame.pack(fill="both", expand=True, padx=20, pady=(0, 10))
        
        # Bouton unique de retraitement
        reprocess_button = ctk.CTkButton(
            errors_frame,
            text="🔄 Retraiter les produits sélectionnés (Mode séquentiel)",
            command=self.reprocess_errors_sequential,
            width=400,
            font=ctk.CTkFont(size=14, weight="bold")
        )
        reprocess_button.pack(pady=20)
        
        # Section Logs du retraitement
        logs_section = ctk.CTkFrame(diagnostic_scroll)
        logs_section.pack(fill="both", expand=True, padx=20, pady=(0, 20))
        
        logs_title = ctk.CTkLabel(
            logs_section,
            text="📋 Logs du retraitement",
            font=ctk.CTkFont(size=16, weight="bold")
        )
        logs_title.pack(anchor="w", padx=20, pady=(20, 10))
        
        # Zone de logs (comme dans l'onglet Traitement)
        self.diagnostic_logs_textbox = ctk.CTkTextbox(
            logs_section,
            height=300,
            state="disabled",
            wrap="word"
        )
        self.diagnostic_logs_textbox.pack(fill="both", expand=True, padx=20, pady=(0, 20))
        
        # Charger les données au démarrage
        self.error_checkboxes = {}  # Dictionnaire {handle: checkbox}
        self.load_diagnostic_summary()
    
    def load_diagnostic_summary(self):
        """Charge et affiche le résumé des status."""
        if not hasattr(self, 'csv_import_id') or not self.csv_import_id:
            # Pas de CSV chargé
            for widget in self.status_summary_frame.winfo_children():
                widget.destroy()
            
            no_data_label = ctk.CTkLabel(
                self.status_summary_frame,
                text="Aucun CSV chargé. Importez un CSV dans l'onglet Traitement.",
                font=ctk.CTkFont(size=12),
                text_color="gray"
            )
            no_data_label.pack(pady=20)
            return
        
        try:
            # Récupérer le résumé
            summary = self.csv_storage.get_status_summary(self.csv_import_id)
            
            # Nettoyer le frame
            for widget in self.status_summary_frame.winfo_children():
                widget.destroy()
            
            if not summary:
                no_data_label = ctk.CTkLabel(
                    self.status_summary_frame,
                    text="Aucune donnée disponible",
                    font=ctk.CTkFont(size=12),
                    text_color="gray"
                )
                no_data_label.pack(pady=20)
                return
            
            # Afficher chaque status
            status_icons = {
                'pending': '⏳',
                'processing': '🔄',
                'completed': '✅',
                'error': '❌'
            }
            
            status_colors = {
                'pending': 'gray',
                'processing': 'blue',
                'completed': 'green',
                'error': 'red'
            }
            
            for status, count in summary.items():
                icon = status_icons.get(status, '❓')
                color = status_colors.get(status, 'gray')
                
                status_row = ctk.CTkFrame(self.status_summary_frame)
                status_row.pack(fill="x", padx=10, pady=5)
                
                status_label = ctk.CTkLabel(
                    status_row,
                    text=f"{icon} {status.capitalize()}: {count} produit(s)",
                    font=ctk.CTkFont(size=14),
                    text_color=color
                )
                status_label.pack(side="left", padx=10)
            
            # Charger la liste des erreurs
            self.load_error_list()
            
        except Exception as e:
            logger.error(f"Erreur lors du chargement du résumé: {e}", exc_info=True)
    
    def load_error_list(self):
        """Charge et affiche la liste des produits en erreur."""
        if not hasattr(self, 'csv_import_id') or not self.csv_import_id:
            return
        
        try:
            # Récupérer les lignes en erreur
            error_rows = self.csv_storage.get_rows_by_status(self.csv_import_id, 'error')
            
            # Nettoyer le frame
            for widget in self.errors_list_frame.winfo_children():
                widget.destroy()
            
            self.error_checkboxes = {}
            
            if not error_rows:
                no_errors_label = ctk.CTkLabel(
                    self.errors_list_frame,
                    text="✅ Aucune erreur à afficher",
                    font=ctk.CTkFont(size=14),
                    text_color="green"
                )
                no_errors_label.pack(pady=20)
                return
            
            # Grouper par handle
            errors_by_handle = {}
            for row in error_rows:
                handle = row.get('handle', 'unknown')
                if handle not in errors_by_handle:
                    errors_by_handle[handle] = {
                        'error_message': row.get('error_message', 'Erreur inconnue'),
                        'ai_explanation': row.get('ai_explanation', ''),
                        'row_id': row['id']
                    }
            
            # Afficher chaque erreur
            for handle, error_data in errors_by_handle.items():
                error_frame = ctk.CTkFrame(self.errors_list_frame)
                error_frame.pack(fill="x", padx=5, pady=5)
                
                # Checkbox + Handle
                left_frame = ctk.CTkFrame(error_frame)
                left_frame.pack(side="left", fill="both", expand=True, padx=10, pady=10)
                
                checkbox_var = ctk.BooleanVar(value=True)
                checkbox = ctk.CTkCheckBox(
                    left_frame,
                    text="",
                    variable=checkbox_var,
                    command=self.update_error_selection_count,
                    width=30
                )
                checkbox.pack(side="left", padx=(0, 10))
                
                self.error_checkboxes[handle] = checkbox_var
                
                handle_label = ctk.CTkLabel(
                    left_frame,
                    text=f"🔹 {handle}",
                    font=ctk.CTkFont(size=13, weight="bold")
                )
                handle_label.pack(side="left")
                
                # Erreur
                error_label = ctk.CTkLabel(
                    left_frame,
                    text=f"❌ {error_data['error_message']}",
                    font=ctk.CTkFont(size=11),
                    text_color="red"
                )
                error_label.pack(anchor="w", padx=(40, 0), pady=(5, 0))
                
                # Explication IA (si disponible)
                if error_data['ai_explanation']:
                    explanation_text = error_data['ai_explanation'][:200]
                    if len(error_data['ai_explanation']) > 200:
                        explanation_text += "..."
                    
                    explanation_label = ctk.CTkLabel(
                        left_frame,
                        text=f"💡 {explanation_text}",
                        font=ctk.CTkFont(size=10),
                        text_color="gray",
                        wraplength=600
                    )
                    explanation_label.pack(anchor="w", padx=(40, 0), pady=(2, 0))
            
            logger.info(f"{len(errors_by_handle)} produit(s) en erreur affiché(s)")
            
            # Mettre à jour le compteur de sélection
            self.update_error_selection_count()
            
        except Exception as e:
            logger.error(f"Erreur lors du chargement de la liste d'erreurs: {e}", exc_info=True)
    
    def select_all_errors(self):
        """Coche toutes les checkboxes d'erreurs."""
        for checkbox_var in self.error_checkboxes.values():
            checkbox_var.set(True)
        self.update_error_selection_count()
    
    def deselect_all_errors(self):
        """Décoche toutes les checkboxes d'erreurs."""
        for checkbox_var in self.error_checkboxes.values():
            checkbox_var.set(False)
        self.update_error_selection_count()
    
    def update_error_selection_count(self):
        """Met à jour le compteur de produits sélectionnés."""
        count = sum(1 for var in self.error_checkboxes.values() if var.get())
        self.error_selection_label.configure(
            text=f"{count} produit(s) sélectionné(s)"
        )
    
    def reprocess_errors_sequential(self):
        """
        Retraite les erreurs sélectionnées en mode SÉQUENTIEL uniquement.
        Pas de popup de confirmation.
        """
        selected_handles = [
            handle for handle, var in self.error_checkboxes.items() 
            if var.get()
        ]
        
        if not selected_handles:
            logger.info("Aucun produit sélectionné")
            return
        
        # Forcer le mode séquentiel en mettant batch_size=1
        self.db.save_config('batch_size', 1)
        
        # Effacer les logs du diagnostic
        self.diagnostic_logs_textbox.configure(state="normal")
        self.diagnostic_logs_textbox.delete("1.0", "end")
        self.diagnostic_logs_textbox.configure(state="disabled")
        
        # Lancer le retraitement avec les logs dans le diagnostic
        self.start_reprocessing(selected_handles, use_diagnostic_logs=True)
    
    # ========== ONGLET VISUALISER ==========
    
    def create_visualizer_tab(self):
        """Crée l'onglet de visualisation des résultats de traitement batch."""
        # Frame scrollable
        visualizer_scroll = ctk.CTkScrollableFrame(self.tab_visualizer)
        visualizer_scroll.pack(fill="both", expand=True, padx=20, pady=20)
        
        # Titre
        title_label = ctk.CTkLabel(
            visualizer_scroll,
            text="👁️ Visualiser les résultats du traitement",
            font=ctk.CTkFont(size=20, weight="bold")
        )
        title_label.pack(pady=(0, 20))
        
        # Section 1: Recherche de produit
        search_frame = ctk.CTkFrame(visualizer_scroll)
        search_frame.pack(fill="x", pady=(0, 20))
        
        search_title = ctk.CTkLabel(
            search_frame,
            text="🔍 Rechercher un produit",
            font=ctk.CTkFont(size=16, weight="bold")
        )
        search_title.pack(anchor="w", padx=20, pady=(20, 10))
        
        # Barre de recherche
        search_input_frame = ctk.CTkFrame(search_frame)
        search_input_frame.pack(fill="x", padx=20, pady=(0, 10))
        
        search_label = ctk.CTkLabel(
            search_input_frame,
            text="Handle du produit:",
            width=150
        )
        search_label.pack(side="left", padx=(10, 5))
        
        self.visualizer_search_var = ctk.StringVar()
        self.visualizer_search_var.trace('w', self.on_visualizer_search_changed)
        self.visualizer_search_entry = ctk.CTkEntry(
            search_input_frame,
            textvariable=self.visualizer_search_var,
            placeholder_text="Tapez pour rechercher...",
            width=400
        )
        self.visualizer_search_entry.pack(side="left", padx=10)
        
        # Liste de suggestions (scrollable)
        self.visualizer_suggestions_frame = ctk.CTkScrollableFrame(search_frame, height=200)
        self.visualizer_suggestions_frame.pack(fill="x", padx=20, pady=(0, 20))
        
        # Section 2: Affichage des résultats
        results_frame = ctk.CTkFrame(visualizer_scroll)
        results_frame.pack(fill="both", expand=True, pady=(0, 20))
        
        results_title = ctk.CTkLabel(
            results_frame,
            text="📊 Résultats du traitement",
            font=ctk.CTkFont(size=16, weight="bold")
        )
        results_title.pack(anchor="w", padx=20, pady=(20, 10))
        
        # Frame scrollable pour les résultats
        self.visualizer_results_frame = ctk.CTkScrollableFrame(results_frame, height=600)
        self.visualizer_results_frame.pack(fill="both", expand=True, padx=20, pady=(0, 20))
        
        # Message initial
        self.visualizer_no_selection_label = ctk.CTkLabel(
            self.visualizer_results_frame,
            text="Recherchez un produit pour voir ses résultats de traitement",
            font=ctk.CTkFont(size=12),
            text_color="gray"
        )
        self.visualizer_no_selection_label.pack(pady=50)
    
    def on_visualizer_search_changed(self, *args):
        """Appelé quand le texte de recherche change dans le visualiseur."""
        if not hasattr(self, 'csv_import_id') or not self.csv_import_id:
            return
        
        search_text = self.visualizer_search_var.get().strip().lower()
        
        # Nettoyer les suggestions
        for widget in self.visualizer_suggestions_frame.winfo_children():
            widget.destroy()
        
        if not search_text:
            return
        
        try:
            # Récupérer tous les handles uniques
            handles = self.csv_storage.get_unique_handles(self.csv_import_id)
            
            # Pour chaque handle, récupérer le titre (première ligne du produit)
            products = {}  # {handle: title}
            for handle in handles:
                rows = self.csv_storage.get_csv_rows(self.csv_import_id, {handle})
                if rows:
                    title = rows[0]['data'].get('Title', handle)
                    products[handle] = title
            
            # Filtrer par recherche dans le titre OU le handle
            matching_products = [
                (handle, title) for handle, title in products.items()
                if search_text in title.lower() or search_text in str(handle).lower()
            ][:10]
            
            # Afficher les suggestions
            if matching_products:
                for handle, title in matching_products:
                    # Afficher le titre avec le handle entre parenthèses
                    display_text = f"{title} ({handle})"
                    suggestion_btn = ctk.CTkButton(
                        self.visualizer_suggestions_frame,
                        text=display_text,
                        command=lambda h=handle: self.show_product_results(h),
                        fg_color="transparent",
                        text_color=("gray10", "gray90"),
                        hover_color=("gray70", "gray30"),
                        anchor="w"
                    )
                    suggestion_btn.pack(fill="x", padx=10, pady=2)
            else:
                # Afficher un message si aucun résultat
                no_result_label = ctk.CTkLabel(
                    self.visualizer_suggestions_frame,
                    text=f"Aucun produit trouvé pour '{search_text}'",
                    text_color="gray"
                )
                no_result_label.pack(padx=10, pady=5)
        
        except Exception as e:
            logger.error(f"Erreur lors de la recherche: {e}", exc_info=True)
    
    def show_product_results(self, handle: str):
        """Affiche les résultats de traitement pour un produit."""
        try:
            # Nettoyer le frame
            for widget in self.visualizer_results_frame.winfo_children():
                widget.destroy()
            
            # Récupérer les lignes du produit
            rows = self.csv_storage.get_csv_rows(self.csv_import_id, [handle])
            
            if not rows:
                no_data_label = ctk.CTkLabel(
                    self.visualizer_results_frame,
                    text=f"Aucune donnée trouvée pour: {handle}",
                    font=ctk.CTkFont(size=12),
                    text_color="red"
                )
                no_data_label.pack(pady=50)
                return
            
            # Utiliser la première ligne comme référence
            first_row = rows[0]
            product_data = first_row['data']
            status = first_row.get('status', 'pending')
            error_message = first_row.get('error_message', '')
            ai_explanation = first_row.get('ai_explanation', '')
            
            # En-tête du produit
            header_frame = ctk.CTkFrame(self.visualizer_results_frame)
            header_frame.pack(fill="x", pady=(0, 20))
            
            product_title = ctk.CTkLabel(
                header_frame,
                text=f"Produit: {handle}",
                font=ctk.CTkFont(size=18, weight="bold")
            )
            product_title.pack(anchor="w", padx=20, pady=(20, 5))
            
            # Status
            status_icons = {'pending': '⏳', 'processing': '🔄', 'completed': '✅', 'error': '❌'}
            status_colors = {'pending': 'gray', 'processing': 'blue', 'completed': 'green', 'error': 'red'}
            
            status_label = ctk.CTkLabel(
                header_frame,
                text=f"{status_icons.get(status, '❓')} Status: {status.upper()}",
                font=ctk.CTkFont(size=14, weight="bold"),
                text_color=status_colors.get(status, 'gray')
            )
            status_label.pack(anchor="w", padx=20, pady=(0, 10))
            
            # Nombre de lignes
            lines_label = ctk.CTkLabel(
                header_frame,
                text=f"📄 {len(rows)} ligne(s) dans le CSV (variantes + images)",
                font=ctk.CTkFont(size=12),
                text_color="gray"
            )
            lines_label.pack(anchor="w", padx=20, pady=(0, 20))
            
            # Afficher les erreurs si présentes
            if error_message or ai_explanation:
                error_frame = ctk.CTkFrame(self.visualizer_results_frame)
                error_frame.pack(fill="x", pady=(0, 20))
                
                if error_message:
                    error_title = ctk.CTkLabel(
                        error_frame,
                        text="❌ Message d'erreur:",
                        font=ctk.CTkFont(size=14, weight="bold"),
                        text_color="red"
                    )
                    error_title.pack(anchor="w", padx=20, pady=(20, 5))
                    
                    error_text = ctk.CTkTextbox(error_frame, height=60, wrap="word")
                    error_text.pack(fill="x", padx=20, pady=(0, 10))
                    error_text.insert("1.0", error_message)
                    error_text.configure(state="disabled")
                
                if ai_explanation:
                    explanation_title = ctk.CTkLabel(
                        error_frame,
                        text="💡 Explication de l'IA:",
                        font=ctk.CTkFont(size=14, weight="bold"),
                        text_color="orange"
                    )
                    explanation_title.pack(anchor="w", padx=20, pady=(10, 5))
                    
                    explanation_text = ctk.CTkTextbox(error_frame, height=80, wrap="word")
                    explanation_text.pack(fill="x", padx=20, pady=(0, 20))
                    explanation_text.insert("1.0", ai_explanation)
                    explanation_text.configure(state="disabled")
            
            # Afficher les champs SEO modifiés
            seo_fields = ['SEO Title', 'SEO Description', 'Title', 'Body (HTML)', 'Tags', 'Image Alt Text']
            
            for field_name in seo_fields:
                value = product_data.get(field_name, '')
                if value:  # Afficher seulement si le champ a une valeur
                    field_frame = ctk.CTkFrame(self.visualizer_results_frame)
                    field_frame.pack(fill="x", pady=(0, 15))
                    
                    field_title = ctk.CTkLabel(
                        field_frame,
                        text=f"📝 {field_name}",
                        font=ctk.CTkFont(size=14, weight="bold")
                    )
                    field_title.pack(anchor="w", padx=20, pady=(15, 5))
                    
                    # Calculer la hauteur selon le contenu
                    # Body (HTML) est 3x plus haut que les autres champs
                    if field_name == 'Body (HTML)':
                        height = min(max(180, len(value) // 20), 600)
                    else:
                        height = min(max(60, len(value) // 60), 200)
                    
                    field_text = ctk.CTkTextbox(field_frame, height=height, wrap="word")
                    field_text.pack(fill="x", padx=20, pady=(0, 15))
                    field_text.insert("1.0", value)
                    field_text.configure(state="disabled")
            
            # Afficher Google Shopping Category
            google_cat = product_data.get('Google Shopping / Google Product Category', '')
            if google_cat:
                google_frame = ctk.CTkFrame(self.visualizer_results_frame)
                google_frame.pack(fill="x", pady=(0, 15))
                
                google_title = ctk.CTkLabel(
                    google_frame,
                    text="🛍️ Google Shopping Category",
                    font=ctk.CTkFont(size=14, weight="bold")
                )
                google_title.pack(anchor="w", padx=20, pady=(15, 5))
                
                google_text = ctk.CTkLabel(
                    google_frame,
                    text=google_cat,
                    font=ctk.CTkFont(size=12),
                    text_color="green"
                )
                google_text.pack(anchor="w", padx=20, pady=(0, 15))
        
        except Exception as e:
            logger.error(f"Erreur lors de l'affichage: {e}", exc_info=True)
            error_label = ctk.CTkLabel(
                self.visualizer_results_frame,
                text=f"Erreur: {str(e)}",
                font=ctk.CTkFont(size=12),
                text_color="red"
            )
            error_label.pack(pady=50)
    
    
    def __del__(self):
        """Ferme la connexion à la base de données."""
        if hasattr(self, 'db'):
            self.db.close()
