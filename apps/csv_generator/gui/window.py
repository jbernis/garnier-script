"""
Fenêtre de génération CSV Shopify avec sélection personnalisée des champs.
"""

import customtkinter as ctk
from typing import Optional, List, Set
import os
import sys
import threading
import logging
from pathlib import Path

logger = logging.getLogger(__name__)

# Ajouter le répertoire parent au path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from apps.csv_generator.generator import CSVGenerator
from csv_config import SHOPIFY_ALL_COLUMNS
from gui.progress_window import ProgressWindow


class CSVGeneratorWindow(ctk.CTkToplevel):
    """Fenêtre de génération CSV Shopify."""
    
    def __init__(self, parent):
        super().__init__(parent)
        
        self.title("Générateur CSV Shopify")
        self.geometry("1000x800")
        self.resizable(True, True)
        
        # Configuration CustomTkinter
        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("blue")
        
        # Variables
        self.generator = CSVGenerator()
        self.selected_categories: Set[str] = set()
        self.selected_fields: Set[str] = set()
        self.progress_window: Optional[ProgressWindow] = None
        
        # Frame principal avec scrollbar
        main_frame = ctk.CTkScrollableFrame(self)
        main_frame.pack(fill="both", expand=True, padx=20, pady=20)
        
        # Titre
        title_label = ctk.CTkLabel(
            main_frame,
            text="📄 Générateur CSV Shopify",
            font=ctk.CTkFont(size=24, weight="bold")
        )
        title_label.pack(pady=(0, 30))
        
        # Section 1: Sélection du fournisseur
        self.create_supplier_section(main_frame)
        
        # Section 2: Sélection des catégories
        self.create_categories_section(main_frame)
        
        # Section 3: Sélection des champs CSV
        self.create_fields_section(main_frame)
        
        # Section 4: Options avancées
        self.create_options_section(main_frame)
        
        # Section 5: Génération
        self.create_generation_section(main_frame)
        
        # Centrer la fenêtre
        self.center_window()
        
        # Garder la fenêtre au premier plan
        try:
            self.transient(parent)
        except Exception:
            pass
        self.after(100, self._bring_to_front)
        
        # Charger les fournisseurs disponibles
        self.load_suppliers()
    
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
    
    # ========== Section 1: Sélection du fournisseur ==========
    
    def create_supplier_section(self, parent):
        """Crée la section de sélection du fournisseur."""
        supplier_frame = ctk.CTkFrame(parent)
        supplier_frame.pack(fill="x", pady=(0, 20))
        
        supplier_title = ctk.CTkLabel(
            supplier_frame,
            text="Fournisseur",
            font=ctk.CTkFont(size=16, weight="bold")
        )
        supplier_title.pack(anchor="w", padx=20, pady=(20, 10))
        
        supplier_select_frame = ctk.CTkFrame(supplier_frame)
        supplier_select_frame.pack(fill="x", padx=20, pady=(0, 20))
        
        supplier_label = ctk.CTkLabel(supplier_select_frame, text="Fournisseur:", width=150)
        supplier_label.pack(side="left", padx=10)
        
        self.supplier_var = ctk.StringVar(value="")
        self.supplier_dropdown = ctk.CTkComboBox(
            supplier_select_frame,
            values=[],
            variable=self.supplier_var,
            command=self.on_supplier_changed,
            width=300
        )
        self.supplier_dropdown.pack(side="left", padx=10, fill="x", expand=True)
    
    def load_suppliers(self):
        """Charge la liste des fournisseurs disponibles."""
        suppliers = self.generator.get_available_suppliers()
        
        if suppliers:
            self.supplier_dropdown.configure(values=suppliers)
            self.supplier_dropdown.set(suppliers[0])
            self.on_supplier_changed(suppliers[0])
        else:
            self.supplier_dropdown.configure(values=["Aucun fournisseur disponible"])
            logger.warning("Aucun fournisseur avec base de données disponible")
    
    def on_supplier_changed(self, value):
        """Appelé quand le fournisseur change."""
        if not value or value == "Aucun fournisseur disponible":
            return
        
        # Charger les catégories pour ce fournisseur
        self.load_categories(value)
        
        # Charger les gammes pour ce fournisseur (si Garnier)
        self.load_gammes(value)
        
        # Charger la configuration actuelle pour ce fournisseur
        self.load_current_config(value)
    
    # ========== Section 2: Sélection des catégories ==========
    
    def create_categories_section(self, parent):
        """Crée la section de sélection des catégories."""
        categories_frame = ctk.CTkFrame(parent)
        categories_frame.pack(fill="both", expand=True, pady=(0, 20))
        
        categories_title = ctk.CTkLabel(
            categories_frame,
            text="Catégories",
            font=ctk.CTkFont(size=16, weight="bold")
        )
        categories_title.pack(anchor="w", padx=20, pady=(20, 10))
        
        # Checkbox "Toutes les catégories"
        self.all_categories_var = ctk.BooleanVar(value=True)
        all_categories_checkbox = ctk.CTkCheckBox(
            categories_frame,
            text="Toutes les catégories",
            variable=self.all_categories_var,
            command=self.on_all_categories_changed
        )
        all_categories_checkbox.pack(anchor="w", padx=20, pady=(0, 10))
        
        # Liste scrollable des catégories
        self.categories_scroll_frame = ctk.CTkScrollableFrame(categories_frame)
        self.categories_scroll_frame.pack(fill="both", expand=True, padx=20, pady=(0, 20))
        
        self.category_checkboxes: dict = {}
        
        self.empty_categories_label = ctk.CTkLabel(
            self.categories_scroll_frame,
            text="Sélectionnez un fournisseur pour voir les catégories",
            font=ctk.CTkFont(size=12),
            text_color="gray"
        )
        self.empty_categories_label.pack(pady=20)
    
    def load_categories(self, supplier: str):
        """Charge les catégories pour un fournisseur."""
        # Supprimer les anciens checkboxes
        for widget in self.categories_scroll_frame.winfo_children():
            widget.destroy()
        
        self.category_checkboxes.clear()
        
        try:
            categories = self.generator.get_categories(supplier)
            
            if categories:
                if hasattr(self, 'empty_categories_label'):
                    self.empty_categories_label.destroy()
                
                for category in categories:
                    var = ctk.BooleanVar(value=False)
                    checkbox = ctk.CTkCheckBox(
                        self.categories_scroll_frame,
                        text=category,
                        variable=var
                    )
                    checkbox.pack(anchor="w", pady=2)
                    self.category_checkboxes[category] = (checkbox, var)
            else:
                self.empty_categories_label = ctk.CTkLabel(
                    self.categories_scroll_frame,
                    text="Aucune catégorie trouvée",
                    font=ctk.CTkFont(size=12),
                    text_color="gray"
                )
                self.empty_categories_label.pack(pady=20)
        except Exception as e:
            logger.error(f"Erreur lors du chargement des catégories: {e}", exc_info=True)
    
    def on_all_categories_changed(self):
        """Appelé quand la checkbox 'Toutes les catégories' change."""
        if self.all_categories_var.get():
            # Désactiver tous les checkboxes
            for checkbox, var in self.category_checkboxes.values():
                checkbox.configure(state="disabled")
        else:
            # Activer tous les checkboxes
            for checkbox, var in self.category_checkboxes.values():
                checkbox.configure(state="normal")
    
    def load_gammes(self, supplier: str):
        """Charge les gammes pour un fournisseur."""
        try:
            gammes = self.generator.get_gammes(supplier)
            
            if gammes:
                # Ajouter une option vide au début pour "Toutes les gammes"
                gammes_with_empty = [""] + gammes
                self.gamme_dropdown.configure(values=gammes_with_empty)
                self.gamme_dropdown.set("")  # Par défaut : toutes les gammes
            else:
                self.gamme_dropdown.configure(values=[""])
                self.gamme_dropdown.set("")
        except Exception as e:
            logger.error(f"Erreur lors du chargement des gammes: {e}", exc_info=True)
            self.gamme_dropdown.configure(values=[""])
            self.gamme_dropdown.set("")
    
    # ========== Section 3: Sélection des champs CSV ==========
    
    def create_fields_section(self, parent):
        """Crée la section de sélection des champs CSV."""
        fields_frame = ctk.CTkFrame(parent)
        fields_frame.pack(fill="both", expand=True, pady=(0, 20))
        
        fields_title = ctk.CTkLabel(
            fields_frame,
            text="Champs CSV",
            font=ctk.CTkFont(size=16, weight="bold")
        )
        fields_title.pack(anchor="w", padx=20, pady=(20, 10))
        
        # Boutons de sélection rapide
        buttons_frame = ctk.CTkFrame(fields_frame)
        buttons_frame.pack(fill="x", padx=20, pady=(0, 10))
        
        ctk.CTkButton(buttons_frame, text="Tout sélectionner", command=self.select_all_fields, width=120).pack(side="left", padx=5)
        ctk.CTkButton(buttons_frame, text="Tout désélectionner", command=self.deselect_all_fields, width=120).pack(side="left", padx=5)
        
        # Groupes de champs
        field_groups = {
            "Champs de base": [
                'Handle', 'Title', 'Body (HTML)', 'Vendor', 'Product Category', 
                'Type', 'Tags', 'Published'
            ],
            "Variantes": [
                'Variant SKU', 'Variant Grams', 'Variant Inventory Tracker',
                'Variant Inventory Qty', 'Variant Inventory Policy',
                'Variant Fulfillment Service', 'Variant Price',
                'Variant Compare At Price', 'Variant Requires Shipping',
                'Variant Taxable', 'Variant Barcode', 'Variant Image',
                'Variant Weight Unit', 'Variant Tax Code', 'Cost per item',
                'Option1 Name', 'Option1 Value', 'Option2 Name', 'Option2 Value',
                'Option3 Name', 'Option3 Value'
            ],
            "Images": [
                'Image Src', 'Image Position', 'Image Alt Text'
            ],
            "SEO": [
                'SEO Title', 'SEO Description'
            ],
            "Google Shopping": [
                'Google Shopping / Google Product Category',
                'Google Shopping / Gender', 'Google Shopping / Age Group',
                'Google Shopping / MPN', 'Google Shopping / Condition',
                'Google Shopping / Custom Product',
                'Google Shopping / Custom Label 0', 'Google Shopping / Custom Label 1',
                'Google Shopping / Custom Label 2', 'Google Shopping / Custom Label 3',
                'Google Shopping / Custom Label 4'
            ],
            "Autres": [
                'Gift Card', 'Included / United States', 'Price / United States',
                'Compare At Price / United States', 'Included / International',
                'Price / International', 'Compare At Price / International',
                'Status', 'location', 'On hand (new)', 'On hand (current)'
            ]
        }
        
        # Frame scrollable pour les champs
        fields_scroll_frame = ctk.CTkScrollableFrame(fields_frame)
        fields_scroll_frame.pack(fill="both", expand=True, padx=20, pady=(0, 20))
        
        self.field_checkboxes: dict = {}
        
        # Créer les groupes
        for group_name, fields in field_groups.items():
            # Label du groupe
            group_label = ctk.CTkLabel(
                fields_scroll_frame,
                text=group_name,
                font=ctk.CTkFont(size=14, weight="bold")
            )
            group_label.pack(anchor="w", padx=10, pady=(10, 5))
            
            # Checkboxes pour ce groupe
            for field in fields:
                if field in SHOPIFY_ALL_COLUMNS:
                    var = ctk.BooleanVar(value=True)  # Par défaut sélectionné
                    checkbox = ctk.CTkCheckBox(
                        fields_scroll_frame,
                        text=field,
                        variable=var
                    )
                    checkbox.pack(anchor="w", padx=30, pady=1)
                    self.field_checkboxes[field] = (checkbox, var)
        
        # Ajouter les champs qui ne sont dans aucun groupe
        for field in SHOPIFY_ALL_COLUMNS:
            if field not in self.field_checkboxes:
                var = ctk.BooleanVar(value=True)
                checkbox = ctk.CTkCheckBox(
                    fields_scroll_frame,
                    text=field,
                    variable=var
                )
                checkbox.pack(anchor="w", padx=30, pady=1)
                self.field_checkboxes[field] = (checkbox, var)
    
    def select_all_fields(self):
        """Sélectionne tous les champs."""
        logger.debug(f"Sélection de {len(self.field_checkboxes)} champs")
        for field, (checkbox, var) in self.field_checkboxes.items():
            var.set(True)
    
    def deselect_all_fields(self):
        """Désélectionne tous les champs."""
        logger.debug(f"Désélection de {len(self.field_checkboxes)} champs")
        for field, (checkbox, var) in self.field_checkboxes.items():
            var.set(False)
    
    def load_current_config(self, supplier: str):
        """Charge la configuration actuelle et sélectionne les champs configurés."""
        try:
            config = self.generator.get_current_config(supplier)
            configured_fields = set(config['columns'])
            
            # Sélectionner les champs configurés
            for field, (checkbox, var) in self.field_checkboxes.items():
                var.set(field in configured_fields)
            
            # Mettre à jour handle_source et vendor
            self.handle_source_var.set(config.get('handle_source', 'barcode'))
            self.vendor_var.set(config.get('vendor', supplier.capitalize()))
        except Exception as e:
            logger.error(f"Erreur lors du chargement de la configuration: {e}", exc_info=True)
    
    # ========== Section 4: Options avancées ==========
    
    def create_options_section(self, parent):
        """Crée la section des options avancées."""
        options_frame = ctk.CTkFrame(parent)
        options_frame.pack(fill="x", pady=(0, 20))
        
        options_title = ctk.CTkLabel(
            options_frame,
            text="Options avancées",
            font=ctk.CTkFont(size=16, weight="bold")
        )
        options_title.pack(anchor="w", padx=20, pady=(20, 10))
        
        # Source du Handle
        handle_frame = ctk.CTkFrame(options_frame)
        handle_frame.pack(fill="x", padx=20, pady=(0, 10))
        
        handle_label = ctk.CTkLabel(handle_frame, text="Source du Handle:", width=150)
        handle_label.pack(side="left", padx=10)
        
        self.handle_source_var = ctk.StringVar(value="barcode")
        handle_dropdown = ctk.CTkComboBox(
            handle_frame,
            values=["barcode", "sku", "title", "custom"],
            variable=self.handle_source_var,
            width=200
        )
        handle_dropdown.pack(side="left", padx=10)
        
        # Vendor
        vendor_frame = ctk.CTkFrame(options_frame)
        vendor_frame.pack(fill="x", padx=20, pady=(0, 10))
        
        vendor_label = ctk.CTkLabel(vendor_frame, text="Vendor:", width=150)
        vendor_label.pack(side="left", padx=10)
        
        self.vendor_var = ctk.StringVar(value="")
        vendor_entry = ctk.CTkEntry(vendor_frame, textvariable=self.vendor_var, width=300)
        vendor_entry.pack(side="left", padx=10, fill="x", expand=True)
        
        # Gamme (pour Garnier uniquement)
        self.gamme_frame = ctk.CTkFrame(options_frame)
        self.gamme_frame.pack(fill="x", padx=20, pady=(0, 20))
        
        gamme_label = ctk.CTkLabel(self.gamme_frame, text="Gamme (optionnel):", width=150)
        gamme_label.pack(side="left", padx=10)
        
        self.gamme_var = ctk.StringVar(value="")
        self.gamme_dropdown = ctk.CTkComboBox(
            self.gamme_frame,
            values=[""],
            variable=self.gamme_var,
            width=300
        )
        self.gamme_dropdown.pack(side="left", padx=10, fill="x", expand=True)
    
    # ========== Section 5: Génération ==========
    
    def create_generation_section(self, parent):
        """Crée la section de génération."""
        generation_frame = ctk.CTkFrame(parent)
        generation_frame.pack(fill="x", pady=(0, 20))
        
        generate_button = ctk.CTkButton(
            generation_frame,
            text="▶ Générer le CSV",
            command=self.generate_csv,
            width=200,
            height=40,
            fg_color="green",
            hover_color="darkgreen"
        )
        generate_button.pack(pady=20)
    
    def generate_csv(self):
        """Génère le CSV avec les paramètres sélectionnés."""
        # Validation
        supplier = self.supplier_var.get()
        if not supplier or supplier == "Aucun fournisseur disponible":
            logger.warning("Sélectionnez un fournisseur")
            return
        
        # Récupérer les champs sélectionnés
        selected_fields = [
            field for field, (checkbox, var) in self.field_checkboxes.items()
            if var.get()
        ]
        
        if not selected_fields:
            logger.warning("Sélectionnez au moins un champ CSV")
            return
        
        # Récupérer les catégories sélectionnées
        if self.all_categories_var.get():
            categories = None  # Toutes les catégories
        else:
            categories = [
                category for category, (checkbox, var) in self.category_checkboxes.items()
                if var.get()
            ]
            if not categories:
                logger.warning("Sélectionnez au moins une catégorie ou cochez 'Toutes les catégories'")
                return
        
        # Récupérer les options
        handle_source = self.handle_source_var.get()
        vendor = self.vendor_var.get().strip()
        if not vendor:
            vendor = supplier.capitalize()
        
        gamme = self.gamme_var.get().strip() or None
        
        # Ouvrir la fenêtre de progression
        self.progress_window = ProgressWindow(self, title="Génération CSV")
        self.progress_window.add_log(f"Génération du CSV pour {supplier}...")
        self.progress_window.add_log(f"Catégories: {len(categories) if categories else 'Toutes'}")
        self.progress_window.add_log(f"Champs sélectionnés: {len(selected_fields)}")
        
        def generate_thread():
            try:
                output_path = self.generator.generate_csv(
                    supplier=supplier,
                    categories=categories,
                    selected_fields=selected_fields,
                    handle_source=handle_source,
                    vendor=vendor,
                    gamme=gamme
                )
                
                self.after(0, lambda path=output_path: self.generation_completed(path))
            except Exception as e:
                error_msg = str(e)
                logger.error(f"Erreur lors de la génération: {error_msg}", exc_info=True)
                self.after(0, lambda msg=error_msg: self.generation_error(msg))
        
        threading.Thread(target=generate_thread, daemon=True).start()
    
    def generation_completed(self, output_path: str):
        """Appelé quand la génération est terminée."""
        if self.progress_window and hasattr(self.progress_window, 'winfo_exists') and self.progress_window.winfo_exists():
            self.progress_window.finish(success=True, output_file=output_path)
            logger.info(f"CSV généré avec succès: {output_path}")
    
    def generation_error(self, error_msg: str):
        """Appelé en cas d'erreur lors de la génération."""
        if self.progress_window and hasattr(self.progress_window, 'winfo_exists') and self.progress_window.winfo_exists():
            self.progress_window.finish(success=False, error=error_msg)
            logger.error(f"Erreur lors de la génération: {error_msg}")
