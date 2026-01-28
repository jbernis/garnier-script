"""
Fenêtre de nettoyage de base de données.
"""

import customtkinter as ctk
from typing import Optional
import tkinter.messagebox as messagebox
import sys
import os
import logging

logger = logging.getLogger(__name__)

# Ajouter le répertoire parent au path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.garnier_db import GarnierDB
from utils.artiga_db import ArtigaDB
from utils.cristel_db import CristelDB


class CleanupWindow(ctk.CTkToplevel):
    """Fenêtre de nettoyage de base de données."""
    
    def __init__(self, parent):
        super().__init__(parent)
        
        self.title("Nettoyage de base de données")
        self.geometry("700x800")
        self.resizable(True, True)
        
        # Configuration CustomTkinter
        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("blue")
        
        # Variables
        self.selected_provider = None
        self.db = None
        
        # Frame principal avec scrollbar
        main_frame = ctk.CTkScrollableFrame(self)
        main_frame.pack(fill="both", expand=True, padx=20, pady=20)
        
        # Titre
        title_label = ctk.CTkLabel(
            main_frame,
            text="Nettoyage de base de données",
            font=ctk.CTkFont(size=24, weight="bold")
        )
        title_label.pack(pady=(0, 10))
        
        # Description
        desc_label = ctk.CTkLabel(
            main_frame,
            text="Supprimez des données de manière sélective ou complète",
            font=ctk.CTkFont(size=12),
            text_color="gray"
        )
        desc_label.pack(pady=(0, 30))
        
        # Sélection du fournisseur
        provider_frame = ctk.CTkFrame(main_frame)
        provider_frame.pack(fill="x", pady=(0, 20))
        
        provider_label = ctk.CTkLabel(
            provider_frame,
            text="Fournisseur:",
            font=ctk.CTkFont(size=14, weight="bold")
        )
        provider_label.pack(anchor="w", padx=20, pady=(20, 10))
        
        self.provider_var = ctk.StringVar(value="")
        self.provider_dropdown = ctk.CTkComboBox(
            provider_frame,
            values=["", "Garnier", "Artiga", "Cristel"],
            variable=self.provider_var,
            command=self.on_provider_selected,
            width=400
        )
        self.provider_dropdown.pack(anchor="w", padx=20, pady=(0, 20))
        
        # Frame pour les options de nettoyage (dynamique)
        self.options_frame = ctk.CTkFrame(main_frame)
        self.options_frame.pack(fill="both", expand=True, pady=(0, 20))
        
        # Variables pour les options
        self.cleanup_mode = ctk.StringVar(value="all")
        self.category_var = ctk.StringVar(value="")
        self.gamme_var = ctk.StringVar(value="")
        self.subcategory_var = ctk.StringVar(value="")
        self.title_var = ctk.StringVar(value="")
        self.sku_var = ctk.StringVar(value="")
        
        # Widgets des options (créés dynamiquement)
        self.category_dropdown = None
        self.gamme_dropdown = None
        self.subcategory_dropdown = None
        self.title_entry = None
        self.sku_entry = None
        self.search_results_frame = None
        
        # Variables pour les résultats de recherche
        self.search_results = []  # Liste des produits trouvés
        self.selected_products = {}  # Dict {product_id: BooleanVar}
        self.product_checkboxes = []  # Liste des checkboxes pour faciliter la destruction
        
        # Frame pour les boutons d'action
        action_frame = ctk.CTkFrame(main_frame)
        action_frame.pack(fill="x", pady=(20, 0))
        
        # Bouton de prévisualisation
        self.preview_button = ctk.CTkButton(
            action_frame,
            text="Prévisualiser",
            command=self.preview_deletion,
            width=150,
            state="disabled"
        )
        self.preview_button.pack(side="left", padx=20, pady=20)
        
        # Bouton de suppression
        self.delete_button = ctk.CTkButton(
            action_frame,
            text="Supprimer",
            command=self.confirm_and_delete,
            width=150,
            fg_color="red",
            hover_color="darkred",
            state="disabled"
        )
        self.delete_button.pack(side="left", padx=10, pady=20)
        
        # Zone de log
        log_label = ctk.CTkLabel(
            main_frame,
            text="Logs:",
            font=ctk.CTkFont(size=12, weight="bold")
        )
        log_label.pack(anchor="w", pady=(20, 5))
        
        self.log_text = ctk.CTkTextbox(
            main_frame,
            height=150,
            state="disabled"
        )
        self.log_text.pack(fill="x", pady=(0, 20))
        
        # Centrer la fenêtre
        self.center_window()
        
        # Amener au premier plan
        self.bring_to_front()
    
    def bring_to_front(self):
        """Amène la fenêtre au premier plan."""
        self.update_idletasks()
        self.lift()
        self.focus_force()
        
        try:
            self.attributes('-topmost', True)
            self.after(100, lambda: self.attributes('-topmost', False))
        except:
            pass
    
    def center_window(self):
        """Centre la fenêtre sur l'écran."""
        self.update_idletasks()
        width = self.winfo_width()
        height = self.winfo_height()
        x = (self.winfo_screenwidth() // 2) - (width // 2)
        y = (self.winfo_screenheight() // 2) - (height // 2)
        self.geometry(f"{width}x{height}+{x}+{y}")
    
    def log(self, message: str):
        """Ajoute un message dans la zone de log."""
        self.log_text.configure(state="normal")
        self.log_text.insert("end", f"{message}\n")
        self.log_text.see("end")
        self.log_text.configure(state="disabled")
        logger.info(message)
    
    def on_provider_selected(self, provider_name: str):
        """Appelé quand un fournisseur est sélectionné."""
        if not provider_name or provider_name == "":
            self.selected_provider = None
            self.clear_options()
            self.delete_button.configure(state="disabled")
            self.preview_button.configure(state="disabled")
            return
        
        self.selected_provider = provider_name
        self.log(f"Fournisseur sélectionné: {provider_name}")
        
        # Initialiser la connexion DB
        db_path = f"database/{provider_name.lower()}_products.db"
        
        try:
            if provider_name == "Garnier":
                self.db = GarnierDB(db_path)
            elif provider_name == "Artiga":
                self.db = ArtigaDB(db_path)
            elif provider_name == "Cristel":
                self.db = CristelDB(db_path)
            
            # Créer les options appropriées
            self.create_options()
            
            # Activer les boutons
            self.delete_button.configure(state="normal")
            self.preview_button.configure(state="normal")
            
        except Exception as e:
            self.log(f"Erreur lors de la connexion à la base: {e}")
            messagebox.showerror("Erreur", f"Impossible de se connecter à la base de données:\n{e}")
            self.selected_provider = None
            self.delete_button.configure(state="disabled")
            self.preview_button.configure(state="disabled")
    
    def clear_options(self):
        """Efface toutes les options."""
        for widget in self.options_frame.winfo_children():
            widget.destroy()
        
        self.category_dropdown = None
        self.gamme_dropdown = None
        self.subcategory_dropdown = None
        self.title_entry = None
        self.sku_entry = None
    
    def create_options(self):
        """Crée les options selon le fournisseur sélectionné."""
        self.clear_options()
        
        # Titre de la section
        options_title = ctk.CTkLabel(
            self.options_frame,
            text="Options de nettoyage:",
            font=ctk.CTkFont(size=14, weight="bold")
        )
        options_title.pack(anchor="w", padx=20, pady=(20, 10))
        
        # Option 1: Vider toute la base
        all_radio = ctk.CTkRadioButton(
            self.options_frame,
            text="Vider toute la base de données",
            variable=self.cleanup_mode,
            value="all",
            command=self.on_mode_changed
        )
        all_radio.pack(anchor="w", padx=20, pady=5)
        
        # Option 2: Par catégorie
        category_radio = ctk.CTkRadioButton(
            self.options_frame,
            text="Par catégorie",
            variable=self.cleanup_mode,
            value="category",
            command=self.on_mode_changed
        )
        category_radio.pack(anchor="w", padx=20, pady=5)
        
        # Dropdown catégorie
        self.category_dropdown = ctk.CTkComboBox(
            self.options_frame,
            variable=self.category_var,
            width=400,
            state="disabled"
        )
        self.category_dropdown.pack(anchor="w", padx=40, pady=(0, 10))
        
        if self.selected_provider == "Garnier":
            # Option 3: Par gamme (Garnier uniquement)
            gamme_radio = ctk.CTkRadioButton(
                self.options_frame,
                text="Par gamme",
                variable=self.cleanup_mode,
                value="gamme",
                command=self.on_mode_changed
            )
            gamme_radio.pack(anchor="w", padx=20, pady=5)
            
            # Dropdown gamme
            self.gamme_dropdown = ctk.CTkComboBox(
                self.options_frame,
                variable=self.gamme_var,
                width=400,
                state="disabled"
            )
            self.gamme_dropdown.pack(anchor="w", padx=40, pady=(0, 10))
        
        else:  # Artiga ou Cristel
            # Option 3: Par sous-catégorie
            subcategory_radio = ctk.CTkRadioButton(
                self.options_frame,
                text="Par sous-catégorie",
                variable=self.cleanup_mode,
                value="subcategory",
                command=self.on_mode_changed
            )
            subcategory_radio.pack(anchor="w", padx=20, pady=5)
            
            # Dropdown sous-catégorie
            self.subcategory_dropdown = ctk.CTkComboBox(
                self.options_frame,
                variable=self.subcategory_var,
                width=400,
                state="disabled"
                # Pas de command ici, sinon ça recharge la liste lors de la sélection
            )
            self.subcategory_dropdown.pack(anchor="w", padx=40, pady=(0, 10))
        
        # Option 4: Par article (titre ou SKU)
        article_radio = ctk.CTkRadioButton(
            self.options_frame,
            text="Par article (titre ou SKU)",
            variable=self.cleanup_mode,
            value="article",
            command=self.on_mode_changed
        )
        article_radio.pack(anchor="w", padx=20, pady=5)
        
        # Champ titre avec recherche instantanée
        title_label = ctk.CTkLabel(
            self.options_frame,
            text="Recherche par titre (contient):",
            font=ctk.CTkFont(size=11)
        )
        title_label.pack(anchor="w", padx=40, pady=(5, 2))
        
        self.title_entry = ctk.CTkEntry(
            self.options_frame,
            textvariable=self.title_var,
            width=400,
            state="disabled",
            placeholder_text="Ex: nappe coton"
        )
        self.title_entry.pack(anchor="w", padx=40, pady=(0, 5))
        
        # Lier l'événement de changement de texte pour la recherche instantanée
        self.title_var.trace_add('write', self.on_title_search_changed)
        
        # Frame scrollable pour les résultats de recherche par titre
        self.search_results_frame = ctk.CTkScrollableFrame(
            self.options_frame,
            height=150,
            width=400
        )
        # Ne pas l'afficher par défaut (sera affiché en mode "article")
        
        # Champ SKU
        sku_label = ctk.CTkLabel(
            self.options_frame,
            text="Ou par SKU (exact):",
            font=ctk.CTkFont(size=11)
        )
        sku_label.pack(anchor="w", padx=40, pady=(5, 2))
        
        self.sku_entry = ctk.CTkEntry(
            self.options_frame,
            textvariable=self.sku_var,
            width=400,
            state="disabled",
            placeholder_text="Ex: ARGEN160_1492_160CM"
        )
        self.sku_entry.pack(anchor="w", padx=40, pady=(0, 10))
        
        # Charger les données initiales
        self.load_categories()
        if self.selected_provider == "Garnier":
            self.load_gammes()
        else:
            self.load_subcategories()
    
    def on_mode_changed(self):
        """Appelé quand le mode de nettoyage change."""
        mode = self.cleanup_mode.get()
        
        # Désactiver tous les widgets
        if self.category_dropdown:
            self.category_dropdown.configure(state="disabled")
        if self.gamme_dropdown:
            self.gamme_dropdown.configure(state="disabled")
        if self.subcategory_dropdown:
            self.subcategory_dropdown.configure(state="disabled")
        if self.title_entry:
            self.title_entry.configure(state="disabled")
        if self.sku_entry:
            self.sku_entry.configure(state="disabled")
        if self.search_results_frame:
            self.search_results_frame.pack_forget()
        
        # Activer les widgets appropriés
        if mode == "category" and self.category_dropdown:
            self.category_dropdown.configure(state="normal")
        elif mode == "gamme" and self.gamme_dropdown:
            self.gamme_dropdown.configure(state="normal")
        elif mode == "subcategory" and self.subcategory_dropdown:
            self.subcategory_dropdown.configure(state="normal")
        elif mode == "article":
            if self.title_entry:
                self.title_entry.configure(state="normal")
            if self.sku_entry:
                self.sku_entry.configure(state="normal")
            if self.search_results_frame:
                self.search_results_frame.pack(anchor="w", padx=40, pady=(5, 10))
    
    def on_category_changed(self, category: str):
        """Appelé quand la catégorie change (pour filtrer les sous-catégories)."""
        if self.selected_provider in ["Artiga", "Cristel"]:
            self.load_subcategories(category)
    
    def load_categories(self):
        """Charge les catégories depuis la DB."""
        if not self.db or not self.category_dropdown:
            return
        
        try:
            categories = self.db.get_available_categories()
            if categories:
                self.category_dropdown.configure(values=categories)
                self.category_var.set(categories[0] if categories else "")
            else:
                self.category_dropdown.configure(values=["Aucune catégorie"])
                self.category_var.set("Aucune catégorie")
        except Exception as e:
            self.log(f"Erreur lors du chargement des catégories: {e}")
    
    def load_gammes(self):
        """Charge les gammes depuis la DB (Garnier uniquement)."""
        if not self.db or not self.gamme_dropdown:
            return
        
        try:
            gammes = self.db.get_available_gammes()
            if gammes:
                self.gamme_dropdown.configure(values=gammes)
                self.gamme_var.set(gammes[0] if gammes else "")
            else:
                self.gamme_dropdown.configure(values=["Aucune gamme"])
                self.gamme_var.set("Aucune gamme")
        except Exception as e:
            self.log(f"Erreur lors du chargement des gammes: {e}")
    
    def load_subcategories(self, category: str = None):
        """Charge les sous-catégories depuis la DB (Artiga/Cristel)."""
        if not self.db or not self.subcategory_dropdown:
            return
        
        try:
            self.log(f"DEBUG: load_subcategories appelée avec category='{category}'")
            subcategories = self.db.get_available_subcategories(category)
            self.log(f"DEBUG: Sous-catégories récupérées: {subcategories}")
            
            if subcategories:
                self.subcategory_dropdown.configure(values=subcategories)
                self.subcategory_var.set(subcategories[0] if subcategories else "")
                self.log(f"DEBUG: Liste mise à jour avec {len(subcategories)} sous-catégories")
            else:
                self.subcategory_dropdown.configure(values=["Aucune sous-catégorie"])
                self.subcategory_var.set("Aucune sous-catégorie")
                self.log(f"DEBUG: Aucune sous-catégorie trouvée")
        except Exception as e:
            self.log(f"Erreur lors du chargement des sous-catégories: {e}")
    
    def on_title_search_changed(self, *args):
        """Appelé quand le texte de recherche change (recherche instantanée)."""
        # Ne faire la recherche que si en mode "article" et que le champ est actif
        if self.cleanup_mode.get() != "article" or not self.title_entry:
            return
        
        search_text = self.title_var.get().strip()
        
        # Effacer les résultats précédents
        self.clear_search_results()
        
        # Si moins de 1 caractère, ne pas chercher
        if len(search_text) < 1:
            return
        
        # Chercher dans la DB
        try:
            cursor = self.db.conn.cursor()
            
            # Construire la requête selon le fournisseur
            if self.selected_provider == "Garnier":
                cursor.execute('''
                    SELECT id, product_code, title, category, gamme as sub_info
                    FROM products 
                    WHERE title LIKE ? COLLATE NOCASE
                    ORDER BY title
                    LIMIT 50
                ''', (f'%{search_text}%',))
            else:  # Artiga ou Cristel
                cursor.execute('''
                    SELECT id, product_code, title, category, subcategory as sub_info
                    FROM products 
                    WHERE title LIKE ? COLLATE NOCASE
                    ORDER BY title
                    LIMIT 50
                ''', (f'%{search_text}%',))
            
            results = cursor.fetchall()
            self.search_results = [dict(row) for row in results]
            
            # Afficher les résultats
            if self.search_results:
                for product in self.search_results:
                    var = ctk.BooleanVar(value=False)
                    self.selected_products[product['id']] = var
                    
                    # Créer un frame pour chaque produit
                    product_frame = ctk.CTkFrame(self.search_results_frame)
                    product_frame.pack(fill="x", pady=2)
                    
                    checkbox = ctk.CTkCheckBox(
                        product_frame,
                        text="",
                        variable=var,
                        width=20
                    )
                    checkbox.pack(side="left", padx=(5, 5))
                    
                    # Afficher le titre et la catégorie/gamme
                    sub_info = product.get('sub_info', '')
                    label_text = f"{product['title']}"
                    if sub_info:
                        if self.selected_provider == "Garnier":
                            label_text += f" (Gamme: {sub_info})"
                        else:
                            label_text += f" (Sous-cat: {sub_info})"
                    
                    label = ctk.CTkLabel(
                        product_frame,
                        text=label_text,
                        font=ctk.CTkFont(size=11),
                        anchor="w"
                    )
                    label.pack(side="left", fill="x", expand=True, padx=5)
                    
                    self.product_checkboxes.append((product_frame, checkbox))
                
                # Ajouter un bouton pour tout sélectionner/désélectionner
                button_frame = ctk.CTkFrame(self.search_results_frame)
                button_frame.pack(fill="x", pady=(5, 2))
                
                select_all_btn = ctk.CTkButton(
                    button_frame,
                    text="Tout sélectionner",
                    command=self.select_all_products,
                    width=120,
                    height=28,
                    font=ctk.CTkFont(size=11)
                )
                select_all_btn.pack(side="left", padx=5)
                
                deselect_all_btn = ctk.CTkButton(
                    button_frame,
                    text="Tout désélectionner",
                    command=self.deselect_all_products,
                    width=120,
                    height=28,
                    font=ctk.CTkFont(size=11)
                )
                deselect_all_btn.pack(side="left", padx=5)
                
                self.product_checkboxes.append((button_frame, None))
                
                # Afficher le nombre de résultats
                count_label = ctk.CTkLabel(
                    self.search_results_frame,
                    text=f"{len(self.search_results)} produit(s) trouvé(s)",
                    font=ctk.CTkFont(size=10),
                    text_color="gray"
                )
                count_label.pack(pady=2)
                self.product_checkboxes.append((count_label, None))
            else:
                no_result_label = ctk.CTkLabel(
                    self.search_results_frame,
                    text="Aucun produit trouvé",
                    font=ctk.CTkFont(size=11),
                    text_color="gray"
                )
                no_result_label.pack(pady=10)
                self.product_checkboxes.append((no_result_label, None))
                
        except Exception as e:
            self.log(f"Erreur lors de la recherche: {e}")
    
    def clear_search_results(self):
        """Efface tous les résultats de recherche affichés."""
        for widget, _ in self.product_checkboxes:
            widget.destroy()
        self.product_checkboxes.clear()
        self.selected_products.clear()
        self.search_results.clear()
    
    def select_all_products(self):
        """Sélectionne tous les produits trouvés."""
        for var in self.selected_products.values():
            var.set(True)
    
    def deselect_all_products(self):
        """Désélectionne tous les produits trouvés."""
        for var in self.selected_products.values():
            var.set(False)
    
    def preview_deletion(self):
        """Affiche un aperçu de ce qui sera supprimé."""
        if not self.db:
            return
        
        try:
            mode = self.cleanup_mode.get()
            count = 0
            message = ""
            
            if mode == "all":
                stats = self.db.get_stats()
                count = stats.get('total_products', 0)
                variants = stats.get('total_variants', 0)
                message = f"Toute la base de données sera vidée:\n\n"
                message += f"- {count} produits\n"
                message += f"- {variants} variants\n"
            
            elif mode == "category":
                category = self.category_var.get()
                if not category or category == "Aucune catégorie":
                    messagebox.showwarning("Attention", "Veuillez sélectionner une catégorie")
                    return
                count = self.db.count_products_by_category(category)
                message = f"Suppression par catégorie '{category}':\n\n"
                message += f"- {count} produits seront supprimés\n"
            
            elif mode == "gamme":
                gamme = self.gamme_var.get()
                if not gamme or gamme == "Aucune gamme":
                    messagebox.showwarning("Attention", "Veuillez sélectionner une gamme")
                    return
                count = self.db.count_products_by_gamme(gamme)
                message = f"Suppression par gamme '{gamme}':\n\n"
                message += f"- {count} produits seront supprimés\n"
            
            elif mode == "subcategory":
                subcategory = self.subcategory_var.get()
                if not subcategory or subcategory == "Aucune sous-catégorie":
                    messagebox.showwarning("Attention", "Veuillez sélectionner une sous-catégorie")
                    return
                count = self.db.count_products_by_subcategory(subcategory)
                message = f"Suppression par sous-catégorie '{subcategory}':\n\n"
                message += f"- {count} produits seront supprimés\n"
            
            elif mode == "article":
                title = self.title_var.get().strip()
                sku = self.sku_var.get().strip()
                
                if not title and not sku:
                    messagebox.showwarning("Attention", "Veuillez entrer un titre ou un SKU")
                    return
                
                if title:
                    # Compter uniquement les produits sélectionnés
                    count = sum(1 for pid, var in self.selected_products.items() if var.get())
                    if count == 0:
                        message = "Aucun produit sélectionné.\n\n"
                        message += "Veuillez cocher au moins un produit dans la liste."
                    else:
                        message = f"Suppression de produits sélectionnés:\n\n"
                        message += f"- {count} produits seront supprimés\n"
                else:
                    count = self.db.count_variants_by_sku(sku)
                    message = f"Recherche par SKU '{sku}':\n\n"
                    message += f"- {count} variants seront supprimés\n"
            
            if count == 0:
                message += "\nAucun élément ne sera supprimé."
            
            messagebox.showinfo("Prévisualisation", message)
            
        except Exception as e:
            self.log(f"Erreur lors de la prévisualisation: {e}")
            messagebox.showerror("Erreur", f"Erreur lors de la prévisualisation:\n{e}")
    
    def confirm_and_delete(self):
        """Demande confirmation et exécute la suppression."""
        if not self.db:
            return
        
        try:
            mode = self.cleanup_mode.get()
            count = 0
            confirmation_msg = ""
            
            # Construire le message de confirmation
            if mode == "all":
                stats = self.db.get_stats()
                count = stats.get('total_products', 0)
                variants = stats.get('total_variants', 0)
                confirmation_msg = f"ATTENTION: Vous allez supprimer TOUTE la base de données!\n\n"
                confirmation_msg += f"- {count} produits\n"
                confirmation_msg += f"- {variants} variants\n\n"
                confirmation_msg += "Cette action est IRRÉVERSIBLE!\n\n"
                confirmation_msg += "Êtes-vous sûr de vouloir continuer?"
            
            elif mode == "category":
                category = self.category_var.get()
                if not category or category == "Aucune catégorie":
                    messagebox.showwarning("Attention", "Veuillez sélectionner une catégorie")
                    return
                count = self.db.count_products_by_category(category)
                confirmation_msg = f"Vous allez supprimer tous les produits de la catégorie '{category}'.\n\n"
                confirmation_msg += f"- {count} produits seront supprimés\n\n"
                confirmation_msg += "Cette action est IRRÉVERSIBLE!\n\n"
                confirmation_msg += "Êtes-vous sûr de vouloir continuer?"
            
            elif mode == "gamme":
                gamme = self.gamme_var.get()
                if not gamme or gamme == "Aucune gamme":
                    messagebox.showwarning("Attention", "Veuillez sélectionner une gamme")
                    return
                count = self.db.count_products_by_gamme(gamme)
                confirmation_msg = f"Vous allez supprimer tous les produits de la gamme '{gamme}'.\n\n"
                confirmation_msg += f"- {count} produits seront supprimés\n\n"
                confirmation_msg += "Cette action est IRRÉVERSIBLE!\n\n"
                confirmation_msg += "Êtes-vous sûr de vouloir continuer?"
            
            elif mode == "subcategory":
                subcategory = self.subcategory_var.get()
                if not subcategory or subcategory == "Aucune sous-catégorie":
                    messagebox.showwarning("Attention", "Veuillez sélectionner une sous-catégorie")
                    return
                count = self.db.count_products_by_subcategory(subcategory)
                confirmation_msg = f"Vous allez supprimer tous les produits de la sous-catégorie '{subcategory}'.\n\n"
                confirmation_msg += f"- {count} produits seront supprimés\n\n"
                confirmation_msg += "Cette action est IRRÉVERSIBLE!\n\n"
                confirmation_msg += "Êtes-vous sûr de vouloir continuer?"
            
            elif mode == "article":
                title = self.title_var.get().strip()
                sku = self.sku_var.get().strip()
                
                if not title and not sku:
                    messagebox.showwarning("Attention", "Veuillez entrer un titre ou un SKU")
                    return
                
                if title:
                    # Compter uniquement les produits sélectionnés
                    selected_ids = [pid for pid, var in self.selected_products.items() if var.get()]
                    count = len(selected_ids)
                    
                    if count == 0:
                        messagebox.showwarning("Attention", "Veuillez sélectionner au moins un produit à supprimer")
                        return
                    
                    confirmation_msg = f"Vous allez supprimer les produits sélectionnés:\n\n"
                    confirmation_msg += f"- {count} produits seront supprimés\n\n"
                else:
                    count = self.db.count_variants_by_sku(sku)
                    confirmation_msg = f"Vous allez supprimer les variants avec le SKU '{sku}'.\n\n"
                    confirmation_msg += f"- {count} variants seront supprimés\n\n"
                
                confirmation_msg += "Cette action est IRRÉVERSIBLE!\n\n"
                confirmation_msg += "Êtes-vous sûr de vouloir continuer?"
            
            if count == 0:
                messagebox.showinfo("Information", "Aucun élément à supprimer.")
                return
            
            # Demander confirmation
            if not messagebox.askyesno("Confirmation", confirmation_msg):
                self.log("Suppression annulée par l'utilisateur")
                return
            
            # Exécuter la suppression
            self.execute_cleanup()
            
        except Exception as e:
            self.log(f"Erreur lors de la confirmation: {e}")
            messagebox.showerror("Erreur", f"Erreur:\n{e}")
    
    def execute_cleanup(self):
        """Exécute la suppression selon les options sélectionnées."""
        if not self.db:
            return
        
        try:
            mode = self.cleanup_mode.get()
            deleted_count = 0
            
            self.log(f"Début de la suppression (mode: {mode})...")
            
            if mode == "all":
                deleted_count = self.db.delete_all()
                self.log(f"✓ Base de données vidée complètement ({deleted_count} produits supprimés)")
            
            elif mode == "category":
                category = self.category_var.get()
                deleted_count = self.db.delete_by_category(category)
                self.log(f"✓ Catégorie '{category}' supprimée ({deleted_count} produits)")
            
            elif mode == "gamme":
                gamme = self.gamme_var.get()
                deleted_count = self.db.delete_by_gamme(gamme)
                self.log(f"✓ Gamme '{gamme}' supprimée ({deleted_count} produits)")
            
            elif mode == "subcategory":
                subcategory = self.subcategory_var.get()
                self.log(f"DEBUG: Mode subcategory, valeur = '{subcategory}'")
                
                if not subcategory or subcategory == "Aucune sous-catégorie":
                    self.log(f"✗ ERREUR: Sous-catégorie vide ou invalide: '{subcategory}'")
                    messagebox.showerror("Erreur", "Veuillez sélectionner une sous-catégorie valide")
                    return
                
                self.log(f"Appel de delete_by_subcategory('{subcategory}')...")
                deleted_count = self.db.delete_by_subcategory(subcategory)
                self.log(f"✓ Sous-catégorie '{subcategory}' supprimée ({deleted_count} produits)")
            
            elif mode == "article":
                title = self.title_var.get().strip()
                sku = self.sku_var.get().strip()
                
                if title:
                    # Supprimer uniquement les produits sélectionnés
                    selected_ids = [pid for pid, var in self.selected_products.items() if var.get()]
                    deleted_count = self.db.delete_by_product_ids(selected_ids)
                    self.log(f"✓ Produits sélectionnés supprimés ({deleted_count} produits)")
                    
                    # Effacer les résultats de recherche
                    self.clear_search_results()
                    self.title_var.set("")
                else:
                    deleted_count = self.db.delete_by_sku(sku)
                    self.log(f"✓ Variants avec SKU '{sku}' supprimés ({deleted_count} variants)")
            
            # Rafraîchir les listes
            self.load_categories()
            if self.selected_provider == "Garnier":
                self.load_gammes()
            else:
                self.load_subcategories()
            
            messagebox.showinfo("Succès", f"Suppression terminée!\n\n{deleted_count} éléments supprimés.")
            
        except Exception as e:
            self.log(f"✗ Erreur lors de la suppression: {e}")
            messagebox.showerror("Erreur", f"Erreur lors de la suppression:\n{e}")
