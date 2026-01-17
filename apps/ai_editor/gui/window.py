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
from apps.ai_editor.processor import CSVAIProcessor
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
        
        # Variables pour l'obfuscation de la clé API
        self.api_key_actual = ""
        self.is_obfuscated = False
        
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
        
        # Section 1: Configuration IA
        self.create_config_section(main_frame)
        
        # Section 2: Gestion des prompts
        self.create_prompts_section(main_frame)
        
        # Section 3: Chargement CSV
        self.create_csv_section(main_frame)
        
        # Section 4: Sélection des produits
        self.create_selection_section(main_frame)
        
        # Section 5: Sélection des champs à traiter
        self.create_fields_section(main_frame)
        
        # Section 6: Boutons d'action
        self.create_action_section(main_frame)
        
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
        self.load_models_button.pack(side="left", padx=10)
        
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
    
    def on_provider_changed(self, value=None):
        """Appelé quand le fournisseur IA change."""
        self.load_api_key_from_db()
        self.load_default_model()
    
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
                # Sauvegarder dans la base de données
                provider = self.provider_var.get()
                self.db.save_ai_credentials(provider, current_value)
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
            messagebox.showerror("Erreur", "Veuillez entrer une clé API valide")
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
        
        ctk.CTkButton(buttons_frame, text="Nouveau", command=self.create_new_prompt_set, width=80).pack(side="left", padx=2)
        ctk.CTkButton(buttons_frame, text="Modifier", command=self.edit_prompt_set, width=80).pack(side="left", padx=2)
        ctk.CTkButton(buttons_frame, text="Dupliquer", command=self.duplicate_prompt_set, width=80).pack(side="left", padx=2)
        ctk.CTkButton(buttons_frame, text="Historique", command=self.show_prompt_history, width=80).pack(side="left", padx=2)
        
        # Champs de prompts
        prompts_fields_frame = ctk.CTkFrame(prompts_frame)
        prompts_fields_frame.pack(fill="both", expand=True, padx=20, pady=(0, 10))
        
        # Prompt système
        system_label = ctk.CTkLabel(prompts_fields_frame, text="Prompt système (global):", anchor="w")
        system_label.pack(fill="x", padx=10, pady=(10, 5))
        self.system_prompt_text = ctk.CTkTextbox(prompts_fields_frame, height=80)
        self.system_prompt_text.pack(fill="x", padx=10, pady=(0, 10))
        
        # Prompt Description
        desc_label = ctk.CTkLabel(prompts_fields_frame, text="Prompt Description (Body HTML):", anchor="w")
        desc_label.pack(fill="x", padx=10, pady=(0, 5))
        self.description_prompt_text = ctk.CTkTextbox(prompts_fields_frame, height=80)
        self.description_prompt_text.pack(fill="x", padx=10, pady=(0, 10))
        
        # Prompt Google Shopping
        google_label = ctk.CTkLabel(prompts_fields_frame, text="Prompt Google Shopping Category:", anchor="w")
        google_label.pack(fill="x", padx=10, pady=(0, 5))
        self.google_category_prompt_text = ctk.CTkTextbox(prompts_fields_frame, height=80)
        self.google_category_prompt_text.pack(fill="x", padx=10, pady=(0, 10))
        
        # Prompt SEO
        seo_label = ctk.CTkLabel(prompts_fields_frame, text="Prompt SEO (Title, Description, Alt Text):", anchor="w")
        seo_label.pack(fill="x", padx=10, pady=(0, 5))
        self.seo_prompt_text = ctk.CTkTextbox(prompts_fields_frame, height=80)
        self.seo_prompt_text.pack(fill="x", padx=10, pady=(0, 10))
        
        # Bouton Sauvegarder
        save_button = ctk.CTkButton(
            prompts_frame,
            text="💾 Sauvegarder",
            command=self.save_prompt_set,
            width=150,
            height=35
        )
        save_button.pack(pady=(0, 20))
    
    def load_prompt_sets(self):
        """Charge la liste des ensembles de prompts."""
        prompt_sets = self.db.list_prompt_sets()
        
        if prompt_sets:
            names = [f"{ps['name']} (ID: {ps['id']})" for ps in prompt_sets]
            self.prompt_set_dropdown.configure(values=names)
            
            # Sélectionner le défaut ou le premier
            default_set = next((ps for ps in prompt_sets if ps['is_default']), None)
            if default_set:
                idx = prompt_sets.index(default_set)
                self.prompt_set_dropdown.set(names[idx])
                self.on_prompt_set_selected(names[idx])
            else:
                self.prompt_set_dropdown.set(names[0])
                self.on_prompt_set_selected(names[0])
        else:
            self.prompt_set_dropdown.configure(values=["Aucun prompt"])
    
    def on_prompt_set_selected(self, value):
        """Appelé quand un ensemble de prompts est sélectionné."""
        if not value or value == "Aucun prompt":
            return
        
        # Extraire l'ID depuis le nom
        try:
            prompt_set_id = int(value.split("(ID: ")[1].split(")")[0])
            prompt_set = self.db.get_prompt_set(prompt_set_id)
            
            if prompt_set:
                self.current_prompt_set_id = prompt_set_id
                self.system_prompt_text.delete("1.0", "end")
                self.system_prompt_text.insert("1.0", prompt_set['system_prompt'])
                self.description_prompt_text.delete("1.0", "end")
                self.description_prompt_text.insert("1.0", prompt_set['description_prompt'])
                self.google_category_prompt_text.delete("1.0", "end")
                self.google_category_prompt_text.insert("1.0", prompt_set['google_category_prompt'])
                self.seo_prompt_text.delete("1.0", "end")
                self.seo_prompt_text.insert("1.0", prompt_set['seo_prompt'])
        except Exception as e:
            logger.error(f"Erreur lors du chargement du prompt set: {e}")
    
    def create_new_prompt_set(self):
        """Crée un nouvel ensemble de prompts."""
        dialog = ctk.CTkInputDialog(text="Nom de l'ensemble de prompts:", title="Nouvel ensemble")
        name = dialog.get_input()
        
        if name:
            prompt_set_id = self.db.create_prompt_set(
                name,
                self.system_prompt_text.get("1.0", "end-1c"),
                self.description_prompt_text.get("1.0", "end-1c"),
                self.google_category_prompt_text.get("1.0", "end-1c"),
                self.seo_prompt_text.get("1.0", "end-1c"),
                is_default=False
            )
            self.load_prompt_sets()
            messagebox.showinfo("Succès", f"Ensemble de prompts '{name}' créé")
    
    def edit_prompt_set(self):
        """Modifie l'ensemble de prompts sélectionné."""
        if not self.current_prompt_set_id:
            messagebox.showwarning("Attention", "Sélectionnez d'abord un ensemble de prompts")
            return
        
        self.save_prompt_set()
    
    def duplicate_prompt_set(self):
        """Duplique l'ensemble de prompts sélectionné."""
        if not self.current_prompt_set_id:
            messagebox.showwarning("Attention", "Sélectionnez d'abord un ensemble de prompts")
            return
        
        prompt_set = self.db.get_prompt_set(self.current_prompt_set_id)
        if prompt_set:
            dialog = ctk.CTkInputDialog(text="Nom du nouvel ensemble:", title="Dupliquer")
            name = dialog.get_input()
            
            if name:
                self.db.create_prompt_set(
                    name,
                    prompt_set['system_prompt'],
                    prompt_set['description_prompt'],
                    prompt_set['google_category_prompt'],
                    prompt_set['seo_prompt'],
                    is_default=False
                )
                self.load_prompt_sets()
                messagebox.showinfo("Succès", f"Ensemble de prompts '{name}' créé")
    
    def show_prompt_history(self):
        """Affiche l'historique des prompts."""
        if not self.current_prompt_set_id:
            messagebox.showwarning("Attention", "Sélectionnez d'abord un ensemble de prompts")
            return
        
        history = self.db.get_prompt_history(self.current_prompt_set_id)
        if not history:
            messagebox.showinfo("Historique", "Aucun historique disponible")
            return
        
        # Créer une fenêtre pour afficher l'historique
        history_window = ctk.CTkToplevel(self)
        history_window.title("Historique des prompts")
        history_window.geometry("800x600")
        
        # TODO: Implémenter l'affichage de l'historique avec possibilité de restauration
        messagebox.showinfo("Historique", f"{len(history)} version(s) dans l'historique")
    
    def save_prompt_set(self):
        """Sauvegarde l'ensemble de prompts."""
        if not self.current_prompt_set_id:
            messagebox.showwarning("Attention", "Sélectionnez d'abord un ensemble de prompts")
            return
        
        self.db.update_prompt_set(
            self.current_prompt_set_id,
            system_prompt=self.system_prompt_text.get("1.0", "end-1c"),
            description_prompt=self.description_prompt_text.get("1.0", "end-1c"),
            google_category_prompt=self.google_category_prompt_text.get("1.0", "end-1c"),
            seo_prompt=self.seo_prompt_text.get("1.0", "end-1c")
        )
        messagebox.showinfo("Succès", "Ensemble de prompts sauvegardé")
    
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
            height=40
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
                
                # Mettre à jour la liste des produits
                self.update_products_list(handles)
                
            except Exception as e:
                logger.error(f"Erreur lors du chargement du CSV: {e}", exc_info=True)
                messagebox.showerror("Erreur", f"Erreur lors du chargement du CSV: {e}")
    
    # ========== Section 4: Sélection des produits ==========
    
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
        
        self.process_all_var = ctk.BooleanVar(value=True)
        process_all_checkbox = ctk.CTkCheckBox(
            selection_frame,
            text="Traiter tous les produits",
            variable=self.process_all_var,
            command=self.on_process_all_changed
        )
        process_all_checkbox.pack(anchor="w", padx=20, pady=(0, 10))
        
        self.products_listbox_frame = ctk.CTkScrollableFrame(selection_frame)
        self.products_listbox_frame.pack(fill="both", expand=True, padx=20, pady=(0, 20))
        
        self.product_checkboxes: Dict[str, ctk.CTkCheckBox] = {}
        
        self.empty_products_label = ctk.CTkLabel(
            self.products_listbox_frame,
            text="Chargez un fichier CSV pour voir les produits",
            font=ctk.CTkFont(size=12),
            text_color="gray"
        )
        self.empty_products_label.pack(pady=20)
    
    def update_products_list(self, handles: list[str]):
        """Met à jour la liste des produits."""
        # Supprimer les anciens checkboxes
        for widget in self.products_listbox_frame.winfo_children():
            widget.destroy()
        
        self.product_checkboxes.clear()
        
        if handles:
            self.empty_products_label.destroy()
            for handle in handles:
                var = ctk.BooleanVar(value=False)
                checkbox = ctk.CTkCheckBox(
                    self.products_listbox_frame,
                    text=handle,
                    variable=var
                )
                checkbox.pack(anchor="w", pady=2)
                self.product_checkboxes[handle] = (checkbox, var)
        else:
            self.empty_products_label = ctk.CTkLabel(
                self.products_listbox_frame,
                text="Aucun produit trouvé",
                font=ctk.CTkFont(size=12),
                text_color="gray"
            )
            self.empty_products_label.pack(pady=20)
    
    def on_process_all_changed(self):
        """Appelé quand la checkbox 'Traiter tous' change."""
        if self.process_all_var.get():
            for checkbox, var in self.product_checkboxes.values():
                checkbox.configure(state="disabled")
        else:
            for checkbox, var in self.product_checkboxes.values():
                checkbox.configure(state="normal")
    
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
        
        self.description_field_var = ctk.BooleanVar(value=True)
        description_checkbox = ctk.CTkCheckBox(
            fields_frame,
            text="Modifier les descriptions (Body HTML)",
            variable=self.description_field_var
        )
        description_checkbox.pack(anchor="w", padx=20, pady=5)
        
        self.google_category_field_var = ctk.BooleanVar(value=True)
        google_checkbox = ctk.CTkCheckBox(
            fields_frame,
            text="Optimiser Google Shopping Category",
            variable=self.google_category_field_var
        )
        google_checkbox.pack(anchor="w", padx=20, pady=5)
        
        self.seo_field_var = ctk.BooleanVar(value=True)
        seo_checkbox = ctk.CTkCheckBox(
            fields_frame,
            text="Optimiser SEO (Title, Description, Alt Text)",
            variable=self.seo_field_var
        )
        seo_checkbox.pack(anchor="w", padx=20, pady=5)
    
    # ========== Section 6: Boutons d'action ==========
    
    def create_action_section(self, parent):
        """Crée la section des boutons d'action."""
        action_frame = ctk.CTkFrame(parent)
        action_frame.pack(fill="x", pady=(0, 20))
        
        button_frame = ctk.CTkFrame(action_frame)
        button_frame.pack(pady=20)
        
        start_button = ctk.CTkButton(
            button_frame,
            text="▶ Démarrer le traitement",
            command=self.start_processing,
            width=200,
            height=40,
            fg_color="green",
            hover_color="darkgreen"
        )
        start_button.pack(side="left", padx=10)
        
        export_button = ctk.CTkButton(
            button_frame,
            text="💾 Exporter CSV",
            command=self.export_csv,
            width=150,
            height=40
        )
        export_button.pack(side="left", padx=10)
        
        viewer_button = ctk.CTkButton(
            button_frame,
            text="👁 Visualiser les résultats",
            command=self.view_results,
            width=180,
            height=40
        )
        viewer_button.pack(side="left", padx=10)
    
    def start_processing(self):
        """Démarre le traitement."""
        if not self.csv_import_id:
            messagebox.showwarning("Attention", "Chargez d'abord un fichier CSV")
            return
        
        if not self.current_prompt_set_id:
            messagebox.showwarning("Attention", "Sélectionnez un ensemble de prompts")
            return
        
        provider = self.provider_var.get()
        model = self.model_var.get()
        
        if not model:
            messagebox.showerror("Erreur", "Sélectionnez un modèle")
            return
        
        # Récupérer les handles sélectionnés
        if self.process_all_var.get():
            selected_handles = None
        else:
            selected_handles = {
                handle for handle, (checkbox, var) in self.product_checkboxes.items()
                if var.get()
            }
            if not selected_handles:
                messagebox.showwarning("Attention", "Sélectionnez au moins un produit")
                return
        
        # Récupérer les champs sélectionnés
        selected_fields = {
            'description': self.description_field_var.get(),
            'google_category': self.google_category_field_var.get(),
            'seo': self.seo_field_var.get()
        }
        
        if not any(selected_fields.values()):
            messagebox.showwarning("Attention", "Sélectionnez au moins un champ à traiter")
            return
        
        # Ouvrir la fenêtre de progression
        self.progress_window = ProgressWindow(self, title="Traitement IA")
        
        def process_thread():
            processor = CSVAIProcessor(self.db)
            success, output_path, changes_dict, processing_result_id = processor.process_csv(
                self.csv_path,
                self.current_prompt_set_id,
                provider,
                model,
                selected_fields,
                selected_handles,
                progress_callback=lambda msg, curr, total: self.progress_window.update_progress(
                    curr / total if total > 0 else 0, msg
                ),
                log_callback=lambda msg: self.progress_window.add_log(msg),
                cancel_check=lambda: self.progress_window.is_cancelled
            )
            
            self.after(0, lambda: self.processing_completed(success, output_path, changes_dict))
        
        threading.Thread(target=process_thread, daemon=True).start()
    
    def processing_completed(self, success: bool, output_path: Optional[str], changes_dict: Dict):
        """Appelé quand le traitement est terminé."""
        if success:
            self.progress_window.set_output_file(output_path)
            self.progress_window.add_log(f"✓ Traitement terminé: {len(changes_dict)} produit(s) modifié(s)")
            messagebox.showinfo("Succès", f"Traitement terminé!\n{len(changes_dict)} produit(s) modifié(s)")
        else:
            messagebox.showerror("Erreur", "Le traitement a échoué. Consultez les logs.")
    
    def export_csv(self):
        """Exporte le CSV depuis la base de données."""
        if not self.csv_import_id:
            messagebox.showwarning("Attention", "Aucun CSV chargé")
            return
        
        file_path = filedialog.asksaveasfilename(
            title="Exporter le CSV",
            defaultextension=".csv",
            filetypes=[("CSV files", "*.csv"), ("All files", "*.*")]
        )
        
        if file_path:
            try:
                self.csv_storage.export_csv(self.csv_import_id, file_path)
                messagebox.showinfo("Succès", f"CSV exporté vers {file_path}")
            except Exception as e:
                logger.error(f"Erreur lors de l'export: {e}", exc_info=True)
                messagebox.showerror("Erreur", f"Erreur lors de l'export: {e}")
    
    def view_results(self):
        """Ouvre la fenêtre de visualisation des résultats."""
        if not self.csv_import_id:
            messagebox.showwarning("Attention", "Aucun CSV chargé")
            return
        
        try:
            from apps.ai_editor.gui.viewer import AIResultsViewer
            viewer = AIResultsViewer(self, self.db, self.csv_import_id)
        except ImportError:
            messagebox.showwarning("Attention", "La fenêtre de visualisation n'est pas encore disponible")
    
    def __del__(self):
        """Ferme la connexion à la base de données."""
        if hasattr(self, 'db'):
            self.db.close()
