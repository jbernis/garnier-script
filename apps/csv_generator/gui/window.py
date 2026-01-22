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
from apps.csv_generator.csv_generator_config import get_csv_generator_config
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
        self.generator_config = get_csv_generator_config()
        self.selected_categories: Set[str] = set()
        self.selected_subcategories: Set[str] = set()
        self.selected_fields: Set[str] = set()
        self.progress_window: Optional[ProgressWindow] = None
        
        # Structures pour les catégories et sous-catégories (comme import_window)
        self.categories_data = {}  # {category_name: {var, category, subcategories_frame, subcategories}}
        self.current_supplier_supports_subcategories = False
        
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
        
        # Déterminer si le fournisseur supporte les sous-catégories
        self.current_supplier_supports_subcategories = value in ['artiga', 'cristel']
        
        # Charger les catégories pour ce fournisseur
        self.load_categories(value)
        
        # Afficher/masquer les gammes selon le fournisseur
        if value == 'garnier':
            self.gamme_frame.pack(fill="x", padx=20, pady=(0, 10))
            self.load_gammes(value)
        else:
            self.gamme_frame.pack_forget()
        
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
        
        # Flag pour éviter les boucles infinies lors des mises à jour programmatiques
        self._updating_checkboxes = False
        
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
        self.categories_data.clear()
        
        try:
            categories = self.generator.get_categories(supplier)
            
            if categories:
                if hasattr(self, 'empty_categories_label'):
                    try:
                        self.empty_categories_label.destroy()
                    except:
                        pass
                
                # Si le fournisseur supporte les sous-catégories (Artiga/Cristel)
                if self.current_supplier_supports_subcategories:
                    for category in categories:
                        # Créer un frame pour la catégorie avec ses sous-catégories
                        category_frame = ctk.CTkFrame(self.categories_scroll_frame)
                        category_frame.pack(fill="x", padx=10, pady=2)
                        
                        # Checkbox de la catégorie
                        var = ctk.BooleanVar(value=False)
                        checkbox = ctk.CTkCheckBox(
                            category_frame,
                            text=category,
                            variable=var
                        )
                        checkbox.pack(anchor="w", padx=0, pady=2)
                        
                        # Ajouter un traceur pour gérer la sélection de la catégorie
                        var.trace_add('write', lambda *args, cat_name=category: self.on_category_checkbox_changed(cat_name))
                        
                        # Stocker les données de la catégorie
                        self.categories_data[category] = {
                            'var': var,
                            'category': category,
                            'category_frame': category_frame,
                            'subcategories_frame': None,
                            'subcategories': {}
                        }
                        self.category_checkboxes[category] = (checkbox, var)
                        
                        # Charger les sous-catégories immédiatement
                        self.load_subcategories_for_category(supplier, category)
                else:
                    # Affichage simple pour Garnier (pas de sous-catégories)
                    for category in categories:
                        var = ctk.BooleanVar(value=False)
                        checkbox = ctk.CTkCheckBox(
                            self.categories_scroll_frame,
                            text=category,
                            variable=var
                        )
                        checkbox.pack(anchor="w", padx=10, pady=5)
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
    
    def load_subcategories_for_category(self, supplier: str, category: str):
        """Charge et affiche les sous-catégories pour une catégorie donnée."""
        if category not in self.categories_data:
            logger.warning(f"Catégorie {category} non trouvée dans categories_data")
            return
        
        try:
            subcategories = self.generator.get_subcategories(supplier, category)
            
            if not subcategories:
                logger.info(f"Aucune sous-catégorie pour {category}")
                return
            
            logger.info(f"Chargement de {len(subcategories)} sous-catégories pour {category}")
            
            category_data = self.categories_data[category]
            category_frame = category_data['category_frame']
            
            # Créer le frame des sous-catégories
            subcategories_frame = ctk.CTkFrame(category_frame)
            subcategories_frame.pack(fill="x", padx=20, pady=(0, 2))
            category_data['subcategories_frame'] = subcategories_frame
            
            # Créer les checkboxes pour les sous-catégories
            for subcat in subcategories:
                var = ctk.BooleanVar(value=False)
                checkbox = ctk.CTkCheckBox(
                    subcategories_frame,
                    text=f"└─ {subcat}",
                    variable=var
                )
                checkbox.pack(anchor="w", padx=0, pady=1)
                
                # Ajouter un traceur pour gérer la sélection de la sous-catégorie
                var.trace_add('write', lambda *args, cat_name=category, subcat_name=subcat: 
                             self.on_subcategory_checkbox_changed(cat_name, subcat_name))
                
                category_data['subcategories'][subcat] = {
                    'var': var,
                    'subcategory': subcat
                }
            
            logger.info(f"Sous-catégories affichées pour {category}")
            
        except Exception as e:
            logger.error(f"Erreur lors du chargement des sous-catégories pour {category}: {e}", exc_info=True)
    
    def on_category_checkbox_changed(self, category_name: str):
        """Appelé quand la checkbox d'une catégorie change."""
        if self._updating_checkboxes:
            return
        
        try:
            if category_name not in self.categories_data:
                return
            
            category_data = self.categories_data[category_name]
            is_selected = category_data['var'].get()
            
            # Si la catégorie est sélectionnée, sélectionner toutes ses sous-catégories
            if is_selected:
                if 'subcategories' in category_data and category_data['subcategories']:
                    self._updating_checkboxes = True
                    try:
                        for subcat_name, subcat_data in category_data['subcategories'].items():
                            if not subcat_data['var'].get():
                                subcat_data['var'].set(True)
                    finally:
                        self._updating_checkboxes = False
            else:
                # Si la catégorie est désélectionnée, désélectionner toutes ses sous-catégories
                if 'subcategories' in category_data and category_data['subcategories']:
                    self._updating_checkboxes = True
                    try:
                        for subcat_name, subcat_data in category_data['subcategories'].items():
                            if subcat_data['var'].get():
                                subcat_data['var'].set(False)
                    finally:
                        self._updating_checkboxes = False
        except Exception as e:
            logger.error(f"Erreur dans on_category_checkbox_changed pour {category_name}: {e}", exc_info=True)
            self._updating_checkboxes = False
    
    def on_subcategory_checkbox_changed(self, category_name: str, subcategory_name: str):
        """Appelé quand la checkbox d'une sous-catégorie change."""
        if self._updating_checkboxes:
            return
        
        try:
            if category_name not in self.categories_data:
                return
            
            category_data = self.categories_data[category_name]
            if 'subcategories' not in category_data or subcategory_name not in category_data['subcategories']:
                return
            
            subcategory_data = category_data['subcategories'][subcategory_name]
            is_selected = subcategory_data['var'].get()
            
            # Si la sous-catégorie est sélectionnée, sélectionner aussi la catégorie parente
            if is_selected:
                if not category_data['var'].get():
                    self._updating_checkboxes = True
                    try:
                        category_data['var'].set(True)
                    finally:
                        self._updating_checkboxes = False
        except Exception as e:
            logger.error(f"Erreur dans on_subcategory_checkbox_changed pour {category_name} -> {subcategory_name}: {e}", exc_info=True)
            self._updating_checkboxes = False
    
    def on_all_categories_changed(self):
        """Appelé quand la checkbox 'Toutes les catégories' change."""
        if self.all_categories_var.get():
            # Désactiver tous les checkboxes (catégories et sous-catégories)
            if self.current_supplier_supports_subcategories:
                for category_name, category_data in self.categories_data.items():
                    # Trouver le checkbox correspondant
                    if category_name in self.category_checkboxes:
                        checkbox, var = self.category_checkboxes[category_name]
                        checkbox.configure(state="disabled")
                    # Désactiver aussi les sous-catégories
                    if 'subcategories' in category_data:
                        for subcat_name, subcat_data in category_data['subcategories'].items():
                            # Les checkboxes des sous-catégories sont créés mais pas stockés dans category_checkboxes
                            # On ne peut pas les désactiver directement, mais ce n'est pas grave
                            pass
            else:
                for checkbox, var in self.category_checkboxes.values():
                    checkbox.configure(state="disabled")
        else:
            # Activer tous les checkboxes
            if self.current_supplier_supports_subcategories:
                for category_name, category_data in self.categories_data.items():
                    if category_name in self.category_checkboxes:
                        checkbox, var = self.category_checkboxes[category_name]
                        checkbox.configure(state="normal")
            else:
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
        
        # Boutons de sélection rapide et sauvegarde
        buttons_frame = ctk.CTkFrame(fields_frame)
        buttons_frame.pack(fill="x", padx=20, pady=(0, 10))
        
        ctk.CTkButton(buttons_frame, text="Tout sélectionner", command=self.select_all_fields, width=120).pack(side="left", padx=5)
        ctk.CTkButton(buttons_frame, text="Tout désélectionner", command=self.deselect_all_fields, width=120).pack(side="left", padx=5)
        
        # Bouton de sauvegarde de la configuration
        self.save_config_button = ctk.CTkButton(
            buttons_frame, 
            text="💾 Sauvegarder cette configuration", 
            command=self.save_field_configuration,
            width=200,
            fg_color="green",
            hover_color="darkgreen"
        )
        self.save_config_button.pack(side="right", padx=5)
        
        # Label de confirmation de sauvegarde
        self.save_status_label = ctk.CTkLabel(
            buttons_frame,
            text="",
            font=ctk.CTkFont(size=11),
            text_color="green"
        )
        self.save_status_label.pack(side="right", padx=10)
        
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
            
            # Mettre à jour handle_source et location
            self.handle_source_var.set(config.get('handle_source', 'barcode'))
            self.location_var.set(config.get('location', f"Dropshipping {supplier.capitalize()}"))
            
            # TODO: Restaurer les catégories/sous-catégories sauvegardées si disponibles
            # saved_categories = config.get('categories')
            # saved_subcategories = config.get('subcategories')
            
        except Exception as e:
            logger.error(f"Erreur lors du chargement de la configuration: {e}", exc_info=True)
    
    def save_field_configuration(self):
        """Sauvegarde la configuration actuelle pour le fournisseur."""
        supplier = self.supplier_var.get()
        if not supplier or supplier == "Aucun fournisseur disponible":
            logger.warning("Aucun fournisseur sélectionné")
            return
        
        try:
            # Récupérer les champs sélectionnés
            selected_fields = [
                field for field, (checkbox, var) in self.field_checkboxes.items()
                if var.get()
            ]
            
            if not selected_fields:
                logger.warning("Aucun champ sélectionné")
                self.show_save_status("✗ Aucun champ sélectionné", "red")
                return
            
            # Récupérer les options
            handle_source = self.handle_source_var.get()
            location = self.location_var.get().strip()
            # Permettre de sauvegarder une valeur vide si l'utilisateur le souhaite
            
            # Le vendor est toujours le nom du fournisseur capitalisé
            vendor = supplier.capitalize()
            
            # TODO: Récupérer les catégories/sous-catégories sélectionnées
            # categories = None
            # subcategories = None
            
            # Sauvegarder la configuration
            self.generator_config.save_full_config(
                supplier=supplier,
                columns=selected_fields,
                handle_source=handle_source,
                vendor=vendor,
                location=location
            )
            
            logger.info(f"Configuration sauvegardée pour {supplier}")
            self.show_save_status(f"✓ Configuration sauvegardée pour {supplier.capitalize()}", "green")
            
        except Exception as e:
            logger.error(f"Erreur lors de la sauvegarde de la configuration: {e}", exc_info=True)
            self.show_save_status(f"✗ Erreur: {str(e)}", "red")
    
    def show_save_status(self, message: str, color: str):
        """Affiche un message de statut de sauvegarde temporaire."""
        try:
            if hasattr(self, 'save_status_label') and hasattr(self.save_status_label, 'winfo_exists') and self.save_status_label.winfo_exists():
                self.save_status_label.configure(text=message, text_color=color)
                # Faire disparaître le message après 3 secondes
                self.after(3000, lambda: self._clear_save_status())
        except Exception as e:
            logger.error(f"Erreur dans show_save_status: {e}")
    
    def _clear_save_status(self):
        """Efface le message de statut de sauvegarde."""
        try:
            if hasattr(self, 'save_status_label') and hasattr(self.save_status_label, 'winfo_exists') and self.save_status_label.winfo_exists():
                self.save_status_label.configure(text="")
        except Exception:
            pass  # Fenêtre fermée, ignorer
    
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
        
        # Emplacement (Location)
        location_frame = ctk.CTkFrame(options_frame)
        location_frame.pack(fill="x", padx=20, pady=(0, 10))
        
        location_label = ctk.CTkLabel(location_frame, text="Emplacement:", width=150)
        location_label.pack(side="left", padx=10)
        
        self.location_var = ctk.StringVar(value="")
        location_entry = ctk.CTkEntry(location_frame, textvariable=self.location_var, width=300)
        location_entry.pack(side="left", padx=10, fill="x", expand=True)
        
        # Gamme (pour Garnier uniquement) - Caché par défaut
        self.gamme_frame = ctk.CTkFrame(options_frame)
        # Ne pas afficher par défaut, sera affiché uniquement pour Garnier
        # self.gamme_frame.pack(fill="x", padx=20, pady=(0, 20))
        
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
        
        # Option pour limiter le nombre d'images
        max_images_frame = ctk.CTkFrame(generation_frame)
        max_images_frame.pack(fill="x", padx=20, pady=(20, 10))
        
        max_images_label = ctk.CTkLabel(
            max_images_frame,
            text="Nombre max d'images par produit:",
            font=ctk.CTkFont(size=12)
        )
        max_images_label.pack(side="left", padx=(10, 10))
        
        self.max_images_var = ctk.StringVar(value="")  # Vide = toutes les images
        max_images_entry = ctk.CTkEntry(
            max_images_frame,
            textvariable=self.max_images_var,
            width=100,
            placeholder_text="Toutes"
        )
        max_images_entry.pack(side="left", padx=(0, 10))
        
        max_images_info = ctk.CTkLabel(
            max_images_frame,
            text="(vide = toutes, sinon nombre ex: 3)",
            font=ctk.CTkFont(size=10),
            text_color="gray"
        )
        max_images_info.pack(side="left")
        
        generate_button = ctk.CTkButton(
            generation_frame,
            text="▶ Générer le CSV",
            command=self.generate_csv,
            width=200,
            height=30,
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
        
        # Récupérer les catégories et sous-catégories sélectionnées
        categories = None
        subcategories = None
        
        # Pour les fournisseurs avec sous-catégories, vérifier d'abord si des sous-catégories sont cochées
        if self.current_supplier_supports_subcategories:
            selected_categories = []
            selected_subcategories = []
            
            for category_name, category_data in self.categories_data.items():
                category_selected = category_data['var'].get()
                
                # Vérifier les sous-catégories sélectionnées
                has_selected_subcategories = False
                if 'subcategories' in category_data:
                    for subcat_name, subcat_data in category_data['subcategories'].items():
                        if subcat_data['var'].get():
                            selected_subcategories.append(subcat_name)
                            has_selected_subcategories = True
                
                # Si la catégorie est sélectionnée mais aucune sous-catégorie, utiliser la catégorie
                if category_selected and not has_selected_subcategories:
                    selected_categories.append(category_name)
            
            # PRIORITÉ : Si des sous-catégories sont sélectionnées, les utiliser (ignore "Toutes les catégories")
            if selected_subcategories:
                subcategories = selected_subcategories
                categories = None
                logger.info(f"Sous-catégories sélectionnées: {selected_subcategories}")
            elif selected_categories:
                categories = selected_categories
                subcategories = None
                logger.info(f"Catégories sélectionnées: {selected_categories}")
            elif self.all_categories_var.get():
                # Seulement si rien n'est coché, utiliser "Toutes les catégories"
                categories = None
                subcategories = None
                logger.info("Toutes les catégories sélectionnées")
            else:
                logger.warning("Sélectionnez au moins une catégorie ou sous-catégorie")
                return
        else:
            # Pour Garnier (pas de sous-catégories)
            if not self.all_categories_var.get():
                categories = [
                    category for category, (checkbox, var) in self.category_checkboxes.items()
                    if var.get()
                ]
                if not categories:
                    logger.warning("Sélectionnez au moins une catégorie ou cochez 'Toutes les catégories'")
                    return
            else:
                categories = None  # Toutes les catégories
        
        # Récupérer les options        
        handle_source = self.handle_source_var.get()
        location = self.location_var.get().strip()
        # Permettre une valeur vide si configurée ainsi
        
        # Le vendor est toujours le nom du fournisseur capitalisé
        vendor = supplier.capitalize()
        
        gamme = self.gamme_var.get().strip() or None
        
        # Récupérer le nombre max d'images
        max_images_str = self.max_images_var.get().strip()
        max_images = None
        if max_images_str:
            try:
                max_images = int(max_images_str)
                if max_images <= 0:
                    logger.warning("Le nombre d'images doit être supérieur à 0")
                    return
                logger.info(f"Limitation à {max_images} image(s) par produit")
            except ValueError:
                logger.warning("Le nombre d'images doit être un nombre entier")
                return
        
        # Ouvrir la fenêtre de progression
        self.progress_window = ProgressWindow(self, title="Génération CSV")
        self.progress_window.add_log(f"Génération du CSV pour {supplier}...")
        if subcategories:
            self.progress_window.add_log(f"Sous-catégories: {len(subcategories)}")
        else:
            self.progress_window.add_log(f"Catégories: {len(categories) if categories else 'Toutes'}")
        self.progress_window.add_log(f"Champs sélectionnés: {len(selected_fields)}")
        
        def generate_thread():
            try:
                output_path = self.generator.generate_csv(
                    supplier=supplier,
                    categories=categories,
                    subcategories=subcategories,
                    selected_fields=selected_fields,
                    handle_source=handle_source,
                    vendor=vendor,
                    location=location,
                    gamme=gamme,
                    max_images=max_images
                )
                
                # Vérifier que la fenêtre existe toujours avant de mettre à jour
                try:
                    if hasattr(self, 'winfo_exists') and self.winfo_exists():
                        self.after(0, lambda path=output_path: self.generation_completed(path))
                except Exception:
                    pass  # Fenêtre fermée, ignorer
            except Exception as e:
                error_msg = str(e)
                logger.error(f"Erreur lors de la génération: {error_msg}", exc_info=True)
                # Vérifier que la fenêtre existe toujours avant de mettre à jour
                try:
                    if hasattr(self, 'winfo_exists') and self.winfo_exists():
                        self.after(0, lambda msg=error_msg: self.generation_error(msg))
                except Exception:
                    pass  # Fenêtre fermée, ignorer
        
        threading.Thread(target=generate_thread, daemon=True).start()
    
    def generation_completed(self, output_path: str):
        """Appelé quand la génération est terminée."""
        try:
            if self.progress_window and hasattr(self.progress_window, 'winfo_exists') and self.progress_window.winfo_exists():
                self.progress_window.finish(success=True, output_file=output_path)
                logger.info(f"CSV généré avec succès: {output_path}")
        except Exception as e:
            logger.error(f"Erreur dans generation_completed: {e}")
    
    def generation_error(self, error_msg: str):
        """Appelé en cas d'erreur lors de la génération."""
        try:
            if self.progress_window and hasattr(self.progress_window, 'winfo_exists') and self.progress_window.winfo_exists():
                self.progress_window.finish(success=False, error=error_msg)
                logger.error(f"Erreur lors de la génération: {error_msg}")
        except Exception as e:
            logger.error(f"Erreur dans generation_error: {e}")
