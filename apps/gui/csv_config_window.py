"""
Fenêtre de configuration des champs CSV Shopify.
"""

import customtkinter as ctk
from typing import List, Dict, Optional
import sys
import os

# Ajouter le répertoire parent au path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from csv_config import get_csv_config, SHOPIFY_ALL_COLUMNS, HANDLE_OPTIONS
import logging

logger = logging.getLogger(__name__)


class CSVConfigWindow(ctk.CTkToplevel):
    """Fenêtre pour configurer les champs CSV Shopify."""
    
    def __init__(self, parent):
        super().__init__(parent)
        
        self.title("Configuration CSV Shopify")
        self.geometry("1000x700")
        self.resizable(True, True)
        
        # Configuration CustomTkinter
        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("blue")
        
        # Variables
        self.config = get_csv_config()
        self.selected_supplier = None
        self.handle_var = None  # Sera créé dans _create_widgets
        self.field_vars = {}  # Sera initialisé dans load_fields
        
        # Créer l'interface
        self._create_widgets()
        
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
    
    def _create_widgets(self):
        """Crée les widgets de l'interface."""
        # Frame principal avec scrollbar
        main_frame = ctk.CTkScrollableFrame(self)
        main_frame.pack(fill="both", expand=True, padx=20, pady=20)
        
        # Titre
        title_label = ctk.CTkLabel(
            main_frame,
            text="Configuration des champs CSV Shopify",
            font=ctk.CTkFont(size=24, weight="bold")
        )
        title_label.pack(pady=(0, 20))
        
        # Sélection du fournisseur
        supplier_frame = ctk.CTkFrame(main_frame)
        supplier_frame.pack(fill="x", pady=(0, 20))
        
        supplier_label = ctk.CTkLabel(
            supplier_frame,
            text="Fournisseur:",
            font=ctk.CTkFont(size=14, weight="bold")
        )
        supplier_label.pack(anchor="w", padx=20, pady=(20, 10))
        
        suppliers = self.config.get_all_suppliers()
        logger.info(f"Fournisseurs disponibles: {suppliers}")
        
        # Créer handle_var AVANT d'appeler on_supplier_selected
        self.handle_var = ctk.StringVar(value="barcode")
        
        self.supplier_var = ctk.StringVar(value=suppliers[0] if suppliers else "")
        self.supplier_dropdown = ctk.CTkComboBox(
            supplier_frame,
            values=suppliers,
            variable=self.supplier_var,
            command=lambda v: self.on_supplier_selected(v),
            width=300
        )
        self.supplier_dropdown.pack(anchor="w", padx=20, pady=(0, 20))
        
        # Frame pour les informations du fournisseur
        self.info_frame = ctk.CTkFrame(main_frame)
        self.info_frame.pack(fill="x", pady=(0, 20))
        
        # Frame pour la configuration des champs
        fields_frame = ctk.CTkFrame(main_frame)
        fields_frame.pack(fill="both", expand=True, pady=(0, 20))
        
        fields_title = ctk.CTkLabel(
            fields_frame,
            text="Champs CSV",
            font=ctk.CTkFont(size=16, weight="bold")
        )
        fields_title.pack(pady=(20, 10))
        
        # Frame pour les boutons de sélection rapide
        quick_select_frame = ctk.CTkFrame(fields_frame)
        quick_select_frame.pack(fill="x", padx=20, pady=(0, 10))
        
        select_all_btn = ctk.CTkButton(
            quick_select_frame,
            text="Tout sélectionner",
            command=self.select_all_fields,
            width=150
        )
        select_all_btn.pack(side="left", padx=5)
        
        deselect_all_btn = ctk.CTkButton(
            quick_select_frame,
            text="Tout désélectionner",
            command=self.deselect_all_fields,
            width=150
        )
        deselect_all_btn.pack(side="left", padx=5)
        
        # Frame scrollable pour les checkboxes des champs
        self.fields_list_frame = ctk.CTkScrollableFrame(fields_frame, height=300)
        self.fields_list_frame.pack(fill="both", expand=True, padx=20, pady=(0, 20))
        
        # Frame pour la configuration du Handle
        handle_frame = ctk.CTkFrame(main_frame)
        handle_frame.pack(fill="x", pady=(0, 20))
        
        handle_title = ctk.CTkLabel(
            handle_frame,
            text="Source du Handle",
            font=ctk.CTkFont(size=16, weight="bold")
        )
        handle_title.pack(pady=(20, 10))
        
        handle_desc = ctk.CTkLabel(
            handle_frame,
            text="Le Handle est l'identifiant unique du produit dans Shopify",
            font=ctk.CTkFont(size=12),
            text_color="gray"
        )
        handle_desc.pack(pady=(0, 10))
        handle_options_frame = ctk.CTkFrame(handle_frame)
        handle_options_frame.pack(fill="x", padx=20, pady=(0, 20))
        
        for key, description in HANDLE_OPTIONS.items():
            radio = ctk.CTkRadioButton(
                handle_options_frame,
                text=f"{key}: {description}",
                variable=self.handle_var,
                value=key,
                command=self.on_handle_source_changed
            )
            radio.pack(anchor="w", padx=20, pady=5)
        
        # Frame pour les boutons d'action
        action_frame = ctk.CTkFrame(main_frame)
        action_frame.pack(fill="x", pady=(0, 20))
        
        reset_supplier_btn = ctk.CTkButton(
            action_frame,
            text="Réinitialiser ce fournisseur",
            command=self.reset_current_supplier,
            width=200,
            fg_color="orange",
            hover_color="darkorange"
        )
        reset_supplier_btn.pack(side="left", padx=10, pady=20)
        
        reset_all_btn = ctk.CTkButton(
            action_frame,
            text="Réinitialiser tout",
            command=self.reset_all,
            width=200,
            fg_color="red",
            hover_color="darkred"
        )
        reset_all_btn.pack(side="left", padx=10, pady=20)
        
        save_btn = ctk.CTkButton(
            action_frame,
            text="Sauvegarder",
            command=self.save_config,
            width=200,
            fg_color="green",
            hover_color="darkgreen"
        )
        save_btn.pack(side="right", padx=10, pady=20)
        
        close_btn = ctk.CTkButton(
            action_frame,
            text="Fermer",
            command=self.destroy,
            width=150
        )
        close_btn.pack(side="right", padx=10, pady=20)
        
        # Charger la configuration du premier fournisseur après avoir créé tous les widgets
        if suppliers:
            self.selected_supplier = suppliers[0]
            self.load_supplier_config()
    
    def on_supplier_selected(self, value=None):
        """Appelé quand un fournisseur est sélectionné."""
        # Récupérer la valeur depuis la variable si elle n'est pas passée
        if value is None:
            value = self.supplier_var.get()
        self.selected_supplier = value
        self.load_supplier_config()
    
    def load_supplier_config(self):
        """Charge la configuration du fournisseur sélectionné."""
        if not self.selected_supplier:
            logger.warning("Aucun fournisseur sélectionné")
            return
        
        try:
            logger.info(f"Chargement de la configuration pour {self.selected_supplier}")
            
            # Mettre à jour les informations du fournisseur
            for widget in self.info_frame.winfo_children():
                widget.destroy()
            
            vendor = self.config.get_vendor(self.selected_supplier)
            handle_source = self.config.get_handle_source(self.selected_supplier)
            columns = self.config.get_columns(self.selected_supplier)
            
            logger.info(f"Vendor: {vendor}, Handle source: {handle_source}, Colonnes: {len(columns)}")
            
            if self.selected_supplier == 'commun':
                info_text = f"Configuration commune\nS'applique à tous les fournisseurs\n\nSource Handle: {handle_source}\nChamps configurés: {len(columns)}"
            else:
                info_text = f"Vendor: {vendor}\nSource Handle: {handle_source}\nChamps configurés: {len(columns)}"
            info_label = ctk.CTkLabel(
                self.info_frame,
                text=info_text,
                font=ctk.CTkFont(size=12)
            )
            info_label.pack(pady=20)
            
            # Mettre à jour la source du Handle (si handle_var existe)
            if self.handle_var:
                self.handle_var.set(handle_source)
            else:
                logger.warning("handle_var n'est pas encore créé")
            
            # Charger les champs
            self.load_fields()
            
            logger.info(f"Configuration chargée avec succès pour {self.selected_supplier}")
        except Exception as e:
            logger.error(f"Erreur lors du chargement de la configuration pour {self.selected_supplier}: {e}")
            import traceback
            traceback.print_exc()
            
            # Afficher un message d'erreur dans l'interface
            error_label = ctk.CTkLabel(
                self.info_frame,
                text=f"Erreur: {str(e)}",
                font=ctk.CTkFont(size=12),
                text_color="red"
            )
            error_label.pack(pady=20)
    
    def load_fields(self):
        """Charge les checkboxes des champs."""
        try:
            # Nettoyer les widgets existants
            for widget in self.fields_list_frame.winfo_children():
                widget.destroy()
            
            if not self.selected_supplier:
                logger.warning("Aucun fournisseur sélectionné pour charger les champs")
                return
            
            current_columns = self.config.get_columns(self.selected_supplier)
            logger.info(f"Chargement de {len(SHOPIFY_ALL_COLUMNS)} champs, {len(current_columns)} sélectionnés")
            
            self.field_vars = {}
            
            # Créer une checkbox pour chaque champ
            for col in SHOPIFY_ALL_COLUMNS:
                var = ctk.BooleanVar(value=col in current_columns)
                checkbox = ctk.CTkCheckBox(
                    self.fields_list_frame,
                    text=col,
                    variable=var,
                    command=lambda c=col: self.on_field_changed(c)  # Sauvegarder automatiquement
                )
                checkbox.pack(anchor="w", padx=10, pady=2)
                self.field_vars[col] = var
            
            logger.info(f"{len(self.field_vars)} checkboxes créées avec succès")
        except Exception as e:
            logger.error(f"Erreur lors du chargement des champs: {e}")
            import traceback
            traceback.print_exc()
    
    def on_field_changed(self, column: str):
        """Appelé quand un champ est modifié - sauvegarde automatique."""
        if not self.selected_supplier:
            return
        
        # Sauvegarder automatiquement les changements
        try:
            selected_columns = [col for col, var in self.field_vars.items() if var.get()]
            self.config.set_columns(self.selected_supplier, selected_columns)
        except Exception as e:
            logger.error(f"Erreur lors de la sauvegarde automatique: {e}")
    
    def select_all_fields(self):
        """Sélectionne tous les champs."""
        for var in self.field_vars.values():
            var.set(True)
    
    def deselect_all_fields(self):
        """Désélectionne tous les champs."""
        for var in self.field_vars.values():
            var.set(False)
    
    def on_handle_source_changed(self):
        """Appelé quand la source du Handle change."""
        if not self.selected_supplier:
            return
        
        handle_source = self.handle_var.get()
        try:
            self.config.set_handle_source(self.selected_supplier, handle_source)
            logger.info(f"Source Handle mise à jour pour {self.selected_supplier}: {handle_source}")
        except Exception as e:
            logger.error(f"Erreur lors de la mise à jour de la source Handle: {e}")
    
    def save_config(self):
        """Sauvegarde la configuration actuelle."""
        if not self.selected_supplier:
            return
        
        try:
            # Récupérer les champs sélectionnés
            selected_columns = [col for col, var in self.field_vars.items() if var.get()]
            
            # Sauvegarder
            self.config.set_columns(self.selected_supplier, selected_columns)
            
            # La source du Handle est déjà sauvegardée automatiquement via on_handle_source_changed
            
            # Afficher un message de confirmation
            messagebox = ctk.CTkToplevel(self)
            messagebox.title("Configuration sauvegardée")
            messagebox.geometry("400x150")
            
            if self.selected_supplier == 'commun':
                label_text = "✓ Configuration commune sauvegardée pour tous les fournisseurs"
            else:
                label_text = f"✓ Configuration sauvegardée pour {self.selected_supplier}"
            
            label = ctk.CTkLabel(
                messagebox,
                text=label_text,
                font=ctk.CTkFont(size=14)
            )
            label.pack(pady=30)
            
            ok_btn = ctk.CTkButton(
                messagebox,
                text="OK",
                command=messagebox.destroy,
                width=100
            )
            ok_btn.pack(pady=10)
            
            # Fermer automatiquement après 2 secondes
            self.after(2000, messagebox.destroy)
        except Exception as e:
            logger.error(f"Erreur lors de la sauvegarde: {e}")
            error_msg = ctk.CTkToplevel(self)
            error_msg.title("Erreur")
            error_msg.geometry("500x150")
            label = ctk.CTkLabel(
                error_msg,
                text=f"✗ Erreur lors de la sauvegarde: {e}",
                font=ctk.CTkFont(size=14),
                text_color="red"
            )
            label.pack(pady=30)
            ok_btn = ctk.CTkButton(error_msg, text="OK", command=error_msg.destroy, width=100)
            ok_btn.pack(pady=10)
    
    def reset_current_supplier(self):
        """Réinitialise la configuration du fournisseur actuel."""
        if not self.selected_supplier:
            return
        
        # Demander confirmation
        confirm = ctk.CTkToplevel(self)
        confirm.title("Confirmation")
        confirm.geometry("500x200")
        
        if self.selected_supplier == 'commun':
            label_text = "⚠️ Réinitialiser la configuration commune pour TOUS les fournisseurs?"
        else:
            label_text = f"⚠️ Réinitialiser la configuration pour {self.selected_supplier}?"
        
        label = ctk.CTkLabel(
            confirm,
            text=label_text,
            font=ctk.CTkFont(size=14)
        )
        label.pack(pady=30)
        
        def do_reset():
            self.config.reset_to_default(self.selected_supplier)
            self.load_supplier_config()
            confirm.destroy()
            
            # Afficher un message de confirmation
            msg = ctk.CTkToplevel(self)
            msg.title("Configuration réinitialisée")
            msg.geometry("400x150")
            
            if self.selected_supplier == 'commun':
                msg_text = "✓ Configuration commune réinitialisée pour tous les fournisseurs"
            else:
                msg_text = f"✓ Configuration réinitialisée pour {self.selected_supplier}"
            
            msg_label = ctk.CTkLabel(
                msg,
                text=msg_text,
                font=ctk.CTkFont(size=14)
            )
            msg_label.pack(pady=30)
            ok_btn = ctk.CTkButton(msg, text="OK", command=msg.destroy, width=100)
            ok_btn.pack(pady=10)
            self.after(2000, msg.destroy)
        
        button_frame = ctk.CTkFrame(confirm)
        button_frame.pack(pady=20)
        
        yes_btn = ctk.CTkButton(
            button_frame,
            text="Oui",
            command=do_reset,
            width=100,
            fg_color="red",
            hover_color="darkred"
        )
        yes_btn.pack(side="left", padx=10)
        
        no_btn = ctk.CTkButton(
            button_frame,
            text="Non",
            command=confirm.destroy,
            width=100
        )
        no_btn.pack(side="left", padx=10)
    
    def reset_all(self):
        """Réinitialise toute la configuration."""
        # Demander confirmation
        confirm = ctk.CTkToplevel(self)
        confirm.title("Confirmation")
        confirm.geometry("500x200")
        
        label = ctk.CTkLabel(
            confirm,
            text="⚠️ Réinitialiser TOUTE la configuration?",
            font=ctk.CTkFont(size=14)
        )
        label.pack(pady=30)
        
        def do_reset_all():
            self.config.reset_to_default()
            self.load_supplier_config()
            confirm.destroy()
            
            # Afficher un message de confirmation
            msg = ctk.CTkToplevel(self)
            msg.title("Configuration réinitialisée")
            msg.geometry("400x150")
            msg_label = ctk.CTkLabel(
                msg,
                text="✓ Toute la configuration a été réinitialisée",
                font=ctk.CTkFont(size=14)
            )
            msg_label.pack(pady=30)
            ok_btn = ctk.CTkButton(msg, text="OK", command=msg.destroy, width=100)
            ok_btn.pack(pady=10)
            self.after(2000, msg.destroy)
        
        button_frame = ctk.CTkFrame(confirm)
        button_frame.pack(pady=20)
        
        yes_btn = ctk.CTkButton(
            button_frame,
            text="Oui",
            command=do_reset_all,
            width=100,
            fg_color="red",
            hover_color="darkred"
        )
        yes_btn.pack(side="left", padx=10)
        
        no_btn = ctk.CTkButton(
            button_frame,
            text="Non",
            command=confirm.destroy,
            width=100
        )
        no_btn.pack(side="left", padx=10)

