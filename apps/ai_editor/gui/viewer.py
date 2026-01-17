"""
Fenêtre de visualisation des résultats de traitement IA.
"""

import customtkinter as ctk
from tkinter import messagebox
from typing import Optional, Dict, List
import logging
import os
import sys

logger = logging.getLogger(__name__)

# Ajouter le répertoire parent au path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from apps.ai_editor.db import AIPromptsDB
from apps.ai_editor.csv_storage import CSVStorage


class AIResultsViewer(ctk.CTkToplevel):
    """Fenêtre de visualisation des résultats de traitement IA."""
    
    def __init__(self, parent, db: AIPromptsDB, csv_import_id: int):
        super().__init__(parent)
        
        self.title("Visualisation des résultats IA")
        self.geometry("1000x700")
        self.resizable(True, True)
        
        # Configuration CustomTkinter
        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("blue")
        
        # Variables
        self.db = db
        self.csv_storage = CSVStorage(db)
        self.csv_import_id = csv_import_id
        self.current_handle: Optional[str] = None
        
        # Frame principal avec scrollbar
        main_frame = ctk.CTkScrollableFrame(self)
        main_frame.pack(fill="both", expand=True, padx=20, pady=20)
        
        # Titre
        title_label = ctk.CTkLabel(
            main_frame,
            text="📊 Résultats du traitement IA",
            font=ctk.CTkFont(size=20, weight="bold")
        )
        title_label.pack(pady=(0, 20))
        
        # Section 1: Sélection du produit
        self.create_product_selection_section(main_frame)
        
        # Section 2: Affichage des changements
        self.create_changes_section(main_frame)
        
        # Section 3: Informations de traitement
        self.create_info_section(main_frame)
        
        # Centrer la fenêtre
        self.center_window()
        
        # Charger les produits disponibles
        self.load_products()
    
    def center_window(self):
        """Centre la fenêtre sur l'écran."""
        self.update_idletasks()
        width = self.winfo_width()
        height = self.winfo_height()
        x = (self.winfo_screenwidth() // 2) - (width // 2)
        y = (self.winfo_screenheight() // 2) - (height // 2)
        self.geometry(f"{width}x{height}+{x}+{y}")
    
    def create_product_selection_section(self, parent):
        """Crée la section de sélection du produit."""
        selection_frame = ctk.CTkFrame(parent)
        selection_frame.pack(fill="x", pady=(0, 20))
        
        selection_title = ctk.CTkLabel(
            selection_frame,
            text="Sélection du produit",
            font=ctk.CTkFont(size=16, weight="bold")
        )
        selection_title.pack(anchor="w", padx=20, pady=(20, 10))
        
        product_frame = ctk.CTkFrame(selection_frame)
        product_frame.pack(fill="x", padx=20, pady=(0, 20))
        
        product_label = ctk.CTkLabel(product_frame, text="Produit:", width=100)
        product_label.pack(side="left", padx=10)
        
        self.product_var = ctk.StringVar(value="")
        self.product_dropdown = ctk.CTkComboBox(
            product_frame,
            values=[],
            variable=self.product_var,
            command=self.on_product_selected,
            width=400
        )
        self.product_dropdown.pack(side="left", padx=10, fill="x", expand=True)
    
    def create_changes_section(self, parent):
        """Crée la section d'affichage des changements."""
        changes_frame = ctk.CTkFrame(parent)
        changes_frame.pack(fill="both", expand=True, pady=(0, 20))
        
        changes_title = ctk.CTkLabel(
            changes_frame,
            text="Champs modifiés",
            font=ctk.CTkFont(size=16, weight="bold")
        )
        changes_title.pack(anchor="w", padx=20, pady=(20, 10))
        
        # Frame scrollable pour les changements
        self.changes_scroll_frame = ctk.CTkScrollableFrame(changes_frame)
        self.changes_scroll_frame.pack(fill="both", expand=True, padx=20, pady=(0, 20))
        
        self.empty_changes_label = ctk.CTkLabel(
            self.changes_scroll_frame,
            text="Sélectionnez un produit pour voir les changements",
            font=ctk.CTkFont(size=12),
            text_color="gray"
        )
        self.empty_changes_label.pack(pady=20)
    
    def create_info_section(self, parent):
        """Crée la section d'informations de traitement."""
        info_frame = ctk.CTkFrame(parent)
        info_frame.pack(fill="x", pady=(0, 20))
        
        info_title = ctk.CTkLabel(
            info_frame,
            text="Informations de traitement",
            font=ctk.CTkFont(size=16, weight="bold")
        )
        info_title.pack(anchor="w", padx=20, pady=(20, 10))
        
        self.info_label = ctk.CTkLabel(
            info_frame,
            text="",
            font=ctk.CTkFont(size=11),
            text_color="gray",
            justify="left"
        )
        self.info_label.pack(anchor="w", padx=20, pady=(0, 20))
    
    def load_products(self):
        """Charge la liste des produits disponibles."""
        try:
            handles = self.csv_storage.get_unique_handles(self.csv_import_id)
            
            if handles:
                # Récupérer les informations supplémentaires pour chaque produit
                products_info = []
                rows = self.csv_storage.get_csv_rows(self.csv_import_id)
                
                for handle in handles:
                    # Trouver la première ligne avec ce handle
                    product_row = next((r for r in rows if r['data'].get('Handle') == handle), None)
                    if product_row:
                        data = product_row['data']
                        title = data.get('Title', handle)
                        vendor = data.get('Vendor', '')
                        display_text = f"{handle} - {title}"
                        if vendor:
                            display_text += f" ({vendor})"
                        products_info.append((handle, display_text))
                    else:
                        products_info.append((handle, handle))
                
                # Trier par handle
                products_info.sort(key=lambda x: x[0])
                
                self.product_dropdown.configure(values=[info[1] for info in products_info])
                self.product_handles = {info[1]: info[0] for info in products_info}
            else:
                self.product_dropdown.configure(values=["Aucun produit"])
        except Exception as e:
            logger.error(f"Erreur lors du chargement des produits: {e}", exc_info=True)
            messagebox.showerror("Erreur", f"Erreur lors du chargement des produits: {e}")
    
    def on_product_selected(self, value):
        """Appelé quand un produit est sélectionné."""
        if not value or value == "Aucun produit":
            return
        
        # Extraire le handle depuis le texte sélectionné
        handle = self.product_handles.get(value)
        if not handle:
            return
        
        self.current_handle = handle
        self.load_changes(handle)
        self.load_info(handle)
    
    def load_changes(self, handle: str):
        """Charge les changements pour un produit."""
        # Supprimer les anciens widgets
        for widget in self.changes_scroll_frame.winfo_children():
            widget.destroy()
        
        try:
            # Récupérer les changements depuis la base de données
            # Pour l'instant, on récupère depuis le dernier traitement
            # TODO: Permettre de sélectionner un traitement spécifique
            
            # Récupérer les lignes du produit
            rows = self.csv_storage.get_csv_rows(self.csv_import_id, handles={handle})
            
            if not rows:
                self.empty_changes_label = ctk.CTkLabel(
                    self.changes_scroll_frame,
                    text="Aucune donnée trouvée pour ce produit",
                    font=ctk.CTkFont(size=12),
                    text_color="gray"
                )
                self.empty_changes_label.pack(pady=20)
                return
            
            # Récupérer les changements depuis product_field_changes
            # Pour l'instant, on affiche les données actuelles
            # TODO: Comparer avec les valeurs originales stockées dans product_field_changes
            
            product_data = rows[0]['data']
            
            # Afficher les champs modifiables
            fields_to_show = [
                ('Body (HTML)', 'Body (HTML)', True),  # (nom_affichage, nom_champ, is_html)
                ('SEO Title', 'SEO Title', False),
                ('SEO Description', 'SEO Description', False),
                ('Google Shopping / Google Product Category', 'Google Shopping / Google Product Category', False),
                ('Image Alt Text', 'Image Alt Text', False)
            ]
            
            for display_name, field_name, is_html in fields_to_show:
                if field_name in product_data:
                    value = product_data[field_name]
                    if value:  # Afficher seulement si non vide
                        self.create_field_display(display_name, value, is_html)
        except Exception as e:
            logger.error(f"Erreur lors du chargement des changements: {e}", exc_info=True)
            error_label = ctk.CTkLabel(
                self.changes_scroll_frame,
                text=f"Erreur: {e}",
                font=ctk.CTkFont(size=12),
                text_color="red"
            )
            error_label.pack(pady=20)
    
    def create_field_display(self, field_name: str, value: str, is_html: bool = False):
        """Crée l'affichage d'un champ modifié."""
        field_frame = ctk.CTkFrame(self.changes_scroll_frame)
        field_frame.pack(fill="x", pady=10, padx=10)
        
        # Nom du champ
        field_label = ctk.CTkLabel(
            field_frame,
            text=field_name,
            font=ctk.CTkFont(size=14, weight="bold")
        )
        field_label.pack(anchor="w", padx=10, pady=(10, 5))
        
        if is_html:
            # Pour HTML, créer des onglets Texte/Aperçu
            tabview = ctk.CTkTabview(field_frame)
            tabview.pack(fill="both", expand=True, padx=10, pady=(0, 10))
            
            # Onglet Texte
            text_tab = tabview.add("Texte")
            text_textbox = ctk.CTkTextbox(text_tab, height=200)
            text_textbox.pack(fill="both", expand=True, padx=10, pady=10)
            text_textbox.insert("1.0", value)
            text_textbox.configure(state="disabled")
            
            # Onglet Aperçu
            preview_tab = tabview.add("Aperçu")
            # Essayer d'utiliser tkinterweb pour le rendu HTML
            try:
                import tkinterweb
                html_frame = tkinterweb.HtmlFrame(preview_tab, messages_enabled=False)
                html_frame.pack(fill="both", expand=True, padx=10, pady=10)
                html_frame.load_html(value)
            except ImportError:
                # Fallback: afficher un message
                preview_label = ctk.CTkLabel(
                    preview_tab,
                    text="Le rendu HTML nécessite tkinterweb.\nInstallez-le avec: pip install tkinterweb",
                    font=ctk.CTkFont(size=12),
                    text_color="orange"
                )
                preview_label.pack(pady=20)
        else:
            # Pour les champs texte simples
            value_textbox = ctk.CTkTextbox(field_frame, height=100)
            value_textbox.pack(fill="x", padx=10, pady=(0, 10))
            value_textbox.insert("1.0", value)
            value_textbox.configure(state="disabled")
    
    def load_info(self, handle: str):
        """Charge les informations de traitement."""
        try:
            # Récupérer le dernier résultat de traitement pour ce CSV
            # TODO: Récupérer les informations complètes depuis csv_processing_results
            
            info_text = f"Produit: {handle}\n"
            info_text += "Informations de traitement disponibles après le traitement."
            
            self.info_label.configure(text=info_text)
        except Exception as e:
            logger.error(f"Erreur lors du chargement des informations: {e}", exc_info=True)
