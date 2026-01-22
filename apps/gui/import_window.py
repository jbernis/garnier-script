"""
Fenêtre d'import pour sélectionner le fournisseur et les catégories.
"""

import customtkinter as ctk
from typing import List, Dict, Optional, Callable
import threading
import sys
import os
import logging

logger = logging.getLogger(__name__)
# Configurer le niveau de logging pour voir les messages debug
logger.setLevel(logging.DEBUG)

# Ajouter le répertoire parent au path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.scraper_registry import registry
from utils.env_manager import EnvManager
from apps.gui.progress_window import ProgressWindow


class ImportWindow(ctk.CTkToplevel):
    """Fenêtre d'import avec sélection du fournisseur et des catégories."""
    
    def __init__(self, parent):
        super().__init__(parent)
        
        self.title("Import de produits")
        self.geometry("900x800")
        self.resizable(True, True)
        
        # Configuration CustomTkinter
        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("blue")
        
        # Variables
        self.env_manager = EnvManager()
        self.selected_scraper = None
        self.categories = []
        self.subcategories = []
        self.progress_window: Optional[ProgressWindow] = None
        
        # Flag pour éviter les boucles infinies lors des mises à jour programmatiques
        self._updating_checkboxes = False
        
        # Frame principal avec scrollbar
        main_frame = ctk.CTkScrollableFrame(self)
        main_frame.pack(fill="both", expand=True, padx=20, pady=20)
        
        # Titre
        title_label = ctk.CTkLabel(
            main_frame,
            text="Import de produits",
            font=ctk.CTkFont(size=24, weight="bold")
        )
        title_label.pack(pady=(0, 30))
        
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
            values=[""] + [scraper.get_display_name() for scraper in registry.get_all()],
            variable=self.provider_var,
            command=self.on_provider_selected,
            width=400
        )
        self.provider_dropdown.pack(anchor="w", padx=20, pady=(0, 20))

        # Mode de sélection (catégories ou gamme) - uniquement pour Garnier
        self.mode_var = ctk.StringVar(value="categories")
        self.mode_frame = ctk.CTkFrame(main_frame)
        self.mode_frame.pack_forget()  # Caché par défaut
        
        mode_label = ctk.CTkLabel(
            self.mode_frame,
            text="Mode d'import:",
            font=ctk.CTkFont(size=14, weight="bold")
        )
        mode_label.pack(anchor="w", padx=20, pady=(20, 10))
        
        self.mode_categories_radio = ctk.CTkRadioButton(
            self.mode_frame,
            text="Par catégories",
            variable=self.mode_var,
            value="categories",
            command=self.on_mode_changed
        )
        self.mode_categories_radio.pack(anchor="w", padx=20, pady=(0, 10))
        
        self.mode_gamme_radio = ctk.CTkRadioButton(
            self.mode_frame,
            text="Par gamme (URL)",
            variable=self.mode_var,
            value="gamme",
            command=self.on_mode_changed
        )
        self.mode_gamme_radio.pack(anchor="w", padx=20, pady=(0, 20))

        # Frame pour l'option gamme (caché par défaut)
        self.gamme_frame = ctk.CTkFrame(main_frame)
        self.gamme_frame.pack_forget()  # Caché par défaut
        
        # Champ URL de la gamme
        gamme_url_label = ctk.CTkLabel(
            self.gamme_frame,
            text="URL de la gamme:",
            font=ctk.CTkFont(size=12)
        )
        gamme_url_label.pack(anchor="w", padx=20, pady=(20, 5))
        
        self.gamme_url_var = ctk.StringVar(value="")
        self.gamme_url_entry = ctk.CTkEntry(
            self.gamme_frame,
            textvariable=self.gamme_url_var,
            placeholder_text="https://garnier-thiebaut.adsi.me/products/?code_gamme=...",
            width=600
        )
        self.gamme_url_entry.pack(anchor="w", padx=20, pady=(0, 10))
        
        # Bouton pour vérifier l'URL
        self.verify_url_button = ctk.CTkButton(
            self.gamme_frame,
            text="Vérifier l'URL",
            command=self.verify_gamme_url,
            width=150,
            height=30
        )
        self.verify_url_button.pack(anchor="w", padx=20, pady=(0, 10))
        
        # Label de statut de l'URL
        self.url_status_label = ctk.CTkLabel(
            self.gamme_frame,
            text="",
            font=ctk.CTkFont(size=11),
            text_color="gray"
        )
        self.url_status_label.pack(anchor="w", padx=20, pady=(0, 10))
        
        # Dropdown pour la catégorie (rempli après chargement des catégories)
        category_label = ctk.CTkLabel(
            self.gamme_frame,
            text="Catégorie:",
            font=ctk.CTkFont(size=12)
        )
        category_label.pack(anchor="w", padx=20, pady=(10, 5))
        
        self.gamme_category_var = ctk.StringVar(value="")
        self.gamme_category_dropdown = ctk.CTkComboBox(
            self.gamme_frame,
            values=[""],
            variable=self.gamme_category_var,
            width=400
        )
        self.gamme_category_dropdown.pack(anchor="w", padx=20, pady=(0, 20))

        # Garder la fenêtre au premier plan par rapport au parent
        try:
            self.transient(parent)
        except Exception:
            pass
        self.after(100, self._bring_to_front)
        
        # Variable pour stocker les catégories disponibles
        self.available_categories = []
        
        # Frame pour les catégories
        self.categories_frame = ctk.CTkFrame(main_frame)
        self.categories_frame.pack(fill="both", expand=True, pady=(0, 20))
        
        # Header avec label, boutons et spinner
        categories_header = ctk.CTkFrame(self.categories_frame)
        categories_header.pack(fill="x", padx=20, pady=(20, 10))
        
        # Label et boutons de sélection
        categories_left = ctk.CTkFrame(categories_header)
        categories_left.pack(side="left", anchor="w")
        
        self.categories_label = ctk.CTkLabel(
            categories_left,
            text="Catégories:",
            font=ctk.CTkFont(size=14, weight="bold")
        )
        self.categories_label.pack(side="left", anchor="w")
        
        # Boutons Tout sélectionner / Tout désélectionner
        self.select_all_button = ctk.CTkButton(
            categories_left,
            text="Tout sélectionner",
            command=self.select_all_categories,
            width=120,
            height=28,
            font=ctk.CTkFont(size=11)
        )
        self.select_all_button.pack(side="left", padx=(15, 5))
        
        self.deselect_all_button = ctk.CTkButton(
            categories_left,
            text="Tout désélectionner",
            command=self.deselect_all_categories,
            width=120,
            height=28,
            font=ctk.CTkFont(size=11)
        )
        self.deselect_all_button.pack(side="left", padx=5)
        
        # Spinner pour le chargement (jaune clair pour meilleure visibilité)
        self.loading_spinner = ctk.CTkProgressBar(
            categories_header,
            width=200,
            height=20,
            mode="indeterminate",
            fg_color=["#3a3a3a", "#2b2b2b"],  # Couleur de fond sombre
            progress_color="#FFD700"  # Jaune clair (gold)
        )
        self.loading_spinner.pack(side="right", padx=10)
        self.loading_spinner.pack_forget()  # Caché par défaut
        
        # Label de statut de chargement (jaune très très clair)
        self.loading_label = ctk.CTkLabel(
            categories_header,
            text="",
            font=ctk.CTkFont(size=12),
            text_color="#FFFF99"  # Jaune très très clair
        )
        self.loading_label.pack(side="right", padx=10)
        self.loading_label.pack_forget()  # Caché par défaut
        
        self.categories_checkboxes = {}
        self.categories_listbox_frame = ctk.CTkScrollableFrame(self.categories_frame)
        self.categories_listbox_frame.pack(fill="both", expand=True, padx=20, pady=(0, 20))
        
        # Frame pour les sous-catégories (Cristel uniquement)
        self.subcategories_frame = ctk.CTkFrame(main_frame)
        self.subcategories_frame.pack(fill="x", pady=(0, 20))
        self.subcategories_frame.pack_forget()
        
        self.subcategories_label = ctk.CTkLabel(
            self.subcategories_frame,
            text="Sous-catégories:",
            font=ctk.CTkFont(size=14, weight="bold")
        )
        self.subcategories_label.pack(anchor="w", padx=20, pady=(20, 10))
        
        self.subcategories_checkboxes = {}
        self.subcategories_listbox_frame = ctk.CTkScrollableFrame(self.subcategories_frame)
        self.subcategories_listbox_frame.pack(fill="both", expand=True, padx=20, pady=(0, 20))
        
        # Options avancées
        options_frame = ctk.CTkFrame(main_frame)
        options_frame.pack(fill="x", pady=(0, 20))
        
        options_title = ctk.CTkLabel(
            options_frame,
            text="Options avancées:",
            font=ctk.CTkFont(size=14, weight="bold")
        )
        options_title.pack(anchor="w", padx=20, pady=(20, 10))
        
        # Limite de produits
        limit_frame = ctk.CTkFrame(options_frame)
        limit_frame.pack(fill="x", padx=20, pady=(0, 10))
        
        limit_label = ctk.CTkLabel(
            limit_frame,
            text="Limite de produits (pour tests, 0 = tous):",
            width=300
        )
        limit_label.pack(side="left", padx=10)
        
        self.limit_var = ctk.StringVar(value="0")
        limit_entry = ctk.CTkEntry(
            limit_frame,
            textvariable=self.limit_var,
            width=100
        )
        limit_entry.pack(side="left", padx=10)
        
        # Option retry automatique des erreurs
        retry_frame = ctk.CTkFrame(options_frame)
        retry_frame.pack(fill="x", padx=20, pady=(0, 10))
        
        self.retry_errors_var = ctk.BooleanVar(value=False)
        retry_checkbox = ctk.CTkCheckBox(
            retry_frame,
            text="Retenter automatiquement les produits en erreur après la collecte",
            variable=self.retry_errors_var,
            font=ctk.CTkFont(size=12)
        )
        retry_checkbox.pack(anchor="w", padx=10, pady=5)
        
        # Nom de fichier personnalisé
        output_frame = ctk.CTkFrame(options_frame)
        output_frame.pack(fill="x", padx=20, pady=(0, 20))
        
        output_label = ctk.CTkLabel(
            output_frame,
            text="Nom de fichier (optionnel, auto si vide):",
            width=300
        )
        output_label.pack(side="left", padx=10)
        
        self.output_var = ctk.StringVar(value="")
        output_entry = ctk.CTkEntry(
            output_frame,
            textvariable=self.output_var,
            width=300
        )
        output_entry.pack(side="left", padx=10, fill="x", expand=True)
        
        # Frame pour les boutons
        button_frame = ctk.CTkFrame(self)
        button_frame.pack(fill="x", padx=20, pady=20)
        
        # Bouton Diagnostic & Retraitement (Garnier uniquement)
        self.diagnostic_button = ctk.CTkButton(
            button_frame,
            text="🔍 Diagnostic & Retraitement",
            command=self.open_diagnostic_window,
            width=220,
            height=30,
            state="disabled",
            fg_color="orange",
            hover_color="darkorange"
        )
        self.diagnostic_button.pack(side="left", padx=10)
        
        # Bouton Démarrer l'import
        self.start_button = ctk.CTkButton(
            button_frame,
            text="Démarrer l'import",
            command=self.start_import,
            width=200,
            height=30,
            state="disabled",
            fg_color="green",
            hover_color="darkgreen"
        )
        self.start_button.pack(side="right", padx=10)
        
        # Message de statut (jaune très clair)
        self.status_label = ctk.CTkLabel(
            button_frame,
            text="",
            font=ctk.CTkFont(size=12),
            text_color="#FFFF99"  # Jaune très clair
        )
        self.status_label.pack(side="left", padx=20)
        
        # Centrer la fenêtre
        self.center_window()
    
    def safe_configure_label(self, label, **kwargs):
        """Configure un label de manière sécurisée en vérifiant qu'il existe."""
        try:
            if hasattr(self, label) and getattr(self, label).winfo_exists():
                getattr(self, label).configure(**kwargs)
        except Exception:
            # Widget détruit, ignorer silencieusement
            pass
    
    def safe_configure_button(self, button, **kwargs):
        """Configure un bouton de manière sécurisée en vérifiant qu'il existe."""
        try:
            if hasattr(self, button) and getattr(self, button).winfo_exists():
                getattr(self, button).configure(**kwargs)
        except Exception:
            # Widget détruit, ignorer silencieusement
            pass
    
    def center_window(self):
        """Centre la fenêtre sur l'écran."""
        self.update_idletasks()
        width = self.winfo_width()
        height = self.winfo_height()
        x = (self.winfo_screenwidth() // 2) - (width // 2)
        y = (self.winfo_screenheight() // 2) - (height // 2)
        self.geometry(f"{width}x{height}+{x}+{y}")
    
    def on_provider_selected(self, value):
        """Appelé quand un fournisseur est sélectionné."""
        # Désactiver les boutons immédiatement lors du changement de fournisseur
        self.start_button.configure(state="disabled")
        self.diagnostic_button.configure(state="disabled")
        
        if not value:
            self.selected_scraper = None
            # Cacher le mode et le frame gamme
            self.mode_frame.pack_forget()
            self.gamme_frame.pack_forget()
            self.mode_var.set("categories")
            return
        
        # Trouver le scraper correspondant
        for scraper in registry.get_all():
            if scraper.get_display_name() == value:
                self.selected_scraper = scraper
                break
        
        # Afficher/masquer le mode uniquement pour Garnier
        if self.selected_scraper and self.selected_scraper.name == "garnier":
            self.mode_frame.pack(fill="x", pady=(0, 20))
        else:
            self.mode_frame.pack_forget()
            self.gamme_frame.pack_forget()
            self.mode_var.set("categories")
        
        # Activer le bouton diagnostic pour tous les scrapers (tous ont query_product.py maintenant)
        if self.selected_scraper:
            self.diagnostic_button.configure(state="normal")
        
        if self.selected_scraper:
            # Vérifier les credentials
            is_valid, errors = self.selected_scraper.check_credentials()
            if is_valid:
                # Les boutons restent désactivés pendant le chargement
                # Le bouton "Charger les catégories" sera réactivé après le chargement (ou en cas d'erreur)
                # Le bouton "Démarrer l'import" sera activé uniquement après le chargement complet
                # (des catégories pour les scrapers sans sous-catégories, ou des sous-catégories pour les autres)
                self.safe_configure_label('status_label',
                    text="✓ Credentials configurés. Chargement des catégories...",
                    text_color="green"
                )
                # Charger automatiquement les catégories avec un petit délai pour laisser l'UI se mettre à jour
                self.after(300, self.load_categories)
            else:
                self.start_button.configure(state="disabled")
                self.diagnostic_button.configure(state="disabled")
                self.safe_configure_label('status_label',
                    text=f"✗ Credentials manquants: {', '.join(errors)}. Configurez-les dans Configuration.",
                    text_color="red"
                )
                # Réinitialiser les catégories
                self.categories = []
                self.subcategories = []
                self.update_categories_display()
                self.subcategories_frame.pack_forget()
        else:
            self.start_button.configure(state="disabled")
            # Réinitialiser les catégories
            self.categories = []
            self.subcategories = []
            self.update_categories_display()
            self.subcategories_frame.pack_forget()
    
    def load_categories(self):
        """Charge les catégories du fournisseur sélectionné avec affichage progressif."""
        if not self.selected_scraper:
            return
        
        self.safe_configure_label('status_label', text="Chargement des catégories...", text_color="#FFFF99")  # Jaune très clair
        
        # Afficher le spinner et le label de chargement
        self.loading_spinner.pack(side="right", padx=10)
        self.loading_label.pack(side="right", padx=10)
        self.safe_configure_label('loading_label', text="Chargement en cours...", text_color="#FFFF99")  # Jaune très très clair
        self.loading_spinner.start()
        
        # Nettoyer l'affichage précédent
        self.categories = []
        self.categories_checkboxes.clear()
        # Nettoyer les widgets existants
        for widget in self.categories_listbox_frame.winfo_children():
            widget.destroy()
        
        def load_thread():
            try:
                def callback(message):
                    self.after(0, lambda msg=message: (
                        self.safe_configure_label('status_label', text=msg, text_color="#FFFF99"),
                        self.safe_configure_label('loading_label', text=msg, text_color="#FFFF99")
                    ))
                
                # Récupérer toutes les catégories
                categories = self.selected_scraper.get_categories(callback=callback)
                
                # Stocker les catégories disponibles pour le dropdown gamme (Garnier uniquement)
                if self.selected_scraper and self.selected_scraper.name == "garnier":
                    self.available_categories = categories
                    # Mettre à jour le dropdown si on est en mode gamme
                    if self.mode_var.get() == "gamme":
                        category_names = [cat['name'] for cat in categories]
                        self.after(0, lambda names=category_names: self.gamme_category_dropdown.configure(values=[""] + names))
                
                # Afficher les catégories progressivement
                if categories:
                    for idx, category in enumerate(categories):
                        self.after(0, lambda cat=category, index=idx, total=len(categories): self.add_category_display(cat, index, total))
                        # Petite pause pour permettre l'affichage progressif
                        import time
                        time.sleep(0.1)  # 100ms entre chaque catégorie
                
                # Une fois toutes les catégories affichées, finaliser
                self.after(0, lambda cats=categories: self.categories_loaded(cats))
            
            except Exception as e:
                error_msg = f"Erreur lors du chargement: {str(e)}"
                self.after(0, lambda: self.categories_load_error(error_msg))
        
        threading.Thread(target=load_thread, daemon=True).start()
    
    def add_category_display(self, category: Dict[str, str], index: int, total: int):
        """Ajoute une catégorie à l'affichage progressivement."""
        try:
            # Vérifier que la fenêtre existe encore
            if not self.winfo_exists():
                return
        except Exception:
            return
        
        try:
            # Ajouter la catégorie à la liste
            self.categories.append(category)
            
            # Mettre à jour le statut (de manière sécurisée)
            self.safe_configure_label('status_label',
                text=f"Chargement des catégories ({index+1}/{total})...",
                text_color="#FFFF99"
            )
            self.safe_configure_label('loading_label',
                text=f"Catégorie {index+1}/{total}",
                text_color="#FFFF99"
            )
        except Exception:
            return
        
        # Créer le checkbox pour cette catégorie (protégé)
        try:
            if self.selected_scraper and self.selected_scraper.supports_subcategories:
                # Pour Cristel, créer un frame pour la catégorie avec ses sous-catégories
                category_frame = ctk.CTkFrame(self.categories_listbox_frame)
                category_frame.pack(fill="x", padx=10, pady=2)
                
                # Checkbox de la catégorie
                var = ctk.BooleanVar(value=False)
                checkbox = ctk.CTkCheckBox(
                    category_frame,
                    text=category['name'],
                    variable=var
                )
                checkbox.pack(anchor="w", padx=0, pady=2)
                
                # Ajouter un traceur pour gérer la sélection de la catégorie
                var.trace_add('write', lambda *args, cat_name=category['name']: self.on_category_checkbox_changed(cat_name))
                
                self.categories_checkboxes[category['name']] = {
                    'var': var,
                    'category': category,
                    'category_frame': category_frame,
                    'subcategories_frame': None,  # Sera créé seulement si nécessaire
                    'subcategories': {}
                }
            else:
                # Pour les autres fournisseurs, affichage simple
                var = ctk.BooleanVar(value=False)
                checkbox = ctk.CTkCheckBox(
                    self.categories_listbox_frame,
                    text=category['name'],
                    variable=var
                )
                checkbox.pack(anchor="w", padx=10, pady=5)
                self.categories_checkboxes[category['name']] = {
                    'var': var,
                    'category': category
                }
        
            # Activer les boutons si on a au moins une catégorie
            if len(self.categories) == 1:
                self.select_all_button.configure(state="normal")
                self.deselect_all_button.configure(state="normal")
            
            # Forcer la mise à jour de l'interface
            self.update_idletasks()
        except Exception as e:
            # Si une erreur se produit lors de la création des widgets, l'ignorer silencieusement
            # (cela arrive si la fenêtre est fermée pendant le chargement)
            pass
    
    def categories_loaded(self, categories: List[Dict[str, str]]):
        """Appelé quand toutes les catégories sont chargées."""
        self.categories = categories
        
        if categories:
            # Si le scraper supporte les sous-catégories, continuer le spinner pour charger les sous-catégories
            if self.selected_scraper and self.selected_scraper.supports_subcategories:
                self.safe_configure_label('status_label',
                    text=f"✓ {len(categories)} catégorie(s) chargée(s). Chargement des sous-catégories...",
                    text_color="#FFFF99"  # Jaune très clair
                )
                self.safe_configure_label('loading_label',
                    text="Chargement des sous-catégories...",
                    text_color="#FFFF99"
                )
                # Le spinner continue de tourner
                # Les boutons restent grisés jusqu'à la fin du chargement des sous-catégories
                # NE PAS activer les boutons ici - ils seront activés dans subcategories_all_loaded()
                # Démarrer le chargement des sous-catégories
                self.load_all_subcategories_sequentially()
            else:
                # Pour les autres fournisseurs (sans sous-catégories), arrêter le spinner et réactiver les boutons
                self.loading_spinner.stop()
                self.loading_spinner.pack_forget()
                self.loading_label.pack_forget()
                self.safe_configure_label('status_label',
                    text=f"✓ {len(categories)} catégorie(s) chargée(s)",
                    text_color="green"
                )
                # Réactiver le bouton pour les autres fournisseurs (pas de sous-catégories)
                try:
                    if hasattr(self, 'start_button'):
                        self.start_button.configure(state="normal")
                except Exception:
                    pass
        else:
            # Arrêter le spinner si aucune catégorie
            self.loading_spinner.stop()
            self.loading_spinner.pack_forget()
            self.loading_label.pack_forget()
            self.safe_configure_label('status_label',
                text="✗ Aucune catégorie trouvée. Vérifiez vos credentials et votre connexion.",
                text_color="red"
            )
    
    def categories_load_error(self, error_msg: str):
        """Appelé en cas d'erreur lors du chargement des catégories."""
        # Arrêter et cacher le spinner
        self.loading_spinner.stop()
        self.loading_spinner.pack_forget()
        self.loading_label.pack_forget()
        
        self.safe_configure_label('status_label',
            text=f"✗ {error_msg}",
            text_color="red"
        )
        self.categories = []
        self.update_categories_display()
    
    def update_categories_display(self):
        """Met à jour l'affichage des catégories (utilisé pour nettoyer ou réinitialiser)."""
        # Nettoyer les checkboxes existantes
        for widget in self.categories_listbox_frame.winfo_children():
            widget.destroy()
        self.categories_checkboxes.clear()
        
        if not self.categories:
            # Désactiver les boutons
            self.select_all_button.configure(state="disabled")
            self.deselect_all_button.configure(state="disabled")
            # Afficher un message si aucune catégorie
            no_cat_label = ctk.CTkLabel(
                self.categories_listbox_frame,
                text="Aucune catégorie disponible. Cliquez sur 'Charger les catégories'.",
                font=ctk.CTkFont(size=12),
                text_color="gray"
            )
            no_cat_label.pack(pady=20)
            return
        
        # Activer/désactiver les boutons selon l'état
        if self.categories:
            self.select_all_button.configure(state="normal")
            self.deselect_all_button.configure(state="normal")
        else:
            self.select_all_button.configure(state="disabled")
            self.deselect_all_button.configure(state="disabled")
    
    def load_all_subcategories_sequentially(self):
        """Charge toutes les sous-catégories de manière séquentielle (pour les scrapers qui les supportent)."""
        if not self.selected_scraper or not self.categories:
            # Arrêter le spinner si pas de catégories et réactiver les boutons
            self.loading_spinner.stop()
            self.loading_spinner.pack_forget()
            self.loading_label.pack_forget()
            # Réactiver le bouton même si pas de catégories
            self.start_button.configure(state="normal")
            return
        
        def load_thread():
            try:
                total_categories = len(self.categories)
                for idx, category in enumerate(self.categories):
                    # Mettre à jour le label de progression
                    progress_msg = f"Chargement des sous-catégories ({idx+1}/{total_categories})..."
                    self.after(0, lambda msg=progress_msg: (
                        self.safe_configure_label('status_label', text=msg, text_color="#FFFF99"),
                        self.safe_configure_label('loading_label', text=msg, text_color="#FFFF99")
                    ))
                    
                    logger.info(f"Chargement des sous-catégories pour {category['name']} ({idx+1}/{total_categories})...")
                    try:
                        subcategories = self.selected_scraper.get_subcategories(category, callback=None)
                        logger.info(f"Sous-catégories récupérées pour {category['name']}: {len(subcategories)}")
                        if subcategories:
                            logger.info(f"Première sous-catégorie: {subcategories[0]}")
                        # Afficher immédiatement après chargement
                        self.after(0, lambda cat=category, subs=subcategories: self.display_subcategories_under_category(cat, subs))
                        # Petite pause entre chaque catégorie pour ne pas surcharger
                        import time
                        time.sleep(0.5)
                    except Exception as e:
                        logger.error(f"Erreur lors du chargement des sous-catégories pour {category['name']}: {e}", exc_info=True)
                        # Continuer avec la catégorie suivante
                        continue
                
                # Toutes les sous-catégories sont chargées, arrêter le spinner
                logger.info("Toutes les sous-catégories ont été chargées - appel de subcategories_all_loaded()")
                # S'assurer que le bouton est toujours désactivé avant d'appeler subcategories_all_loaded
                self.after(0, lambda: (
                    self.start_button.configure(state="disabled"),
                    self.subcategories_all_loaded()
                ))
            except Exception as e:
                logger.error(f"Erreur lors du chargement des sous-catégories: {e}", exc_info=True)
                # Arrêter le spinner en cas d'erreur et activer les boutons
                self.after(0, lambda: (
                    self.start_button.configure(state="disabled"),
                    self.subcategories_all_loaded()
                ))
        
        threading.Thread(target=load_thread, daemon=True).start()
    
    def subcategories_all_loaded(self):
        """Appelé quand toutes les sous-catégories sont chargées."""
        logger.info("subcategories_all_loaded() appelé - activation des boutons")
        
        # Arrêter et cacher le spinner
        self.loading_spinner.stop()
        self.loading_spinner.pack_forget()
        self.loading_label.pack_forget()
        
        # Compter le total des sous-catégories chargées
        total_subcategories = 0
        for category_name, data in self.categories_checkboxes.items():
            if 'subcategories' in data:
                total_subcategories += len(data['subcategories'])
        
        self.safe_configure_label('status_label',
            text=f"✓ {len(self.categories)} catégorie(s) et {total_subcategories} sous-catégorie(s) chargée(s)",
            text_color="green"
        )
        
        # Réactiver le bouton maintenant que tout est chargé
        # C'est ici que le bouton doit être activé pour les scrapers avec sous-catégories
        logger.info("Activation du bouton après chargement complet des sous-catégories")
        self.start_button.configure(state="normal")
    
    def display_subcategories_under_category(self, category: Dict[str, str], subcategories: List[Dict[str, str]]):
        """Affiche les sous-catégories sous une catégorie avec indentation dans le frame de la catégorie."""
        if category['name'] not in self.categories_checkboxes:
            logger.warning(f"Catégorie {category['name']} non trouvée dans categories_checkboxes")
            return
        
        if not subcategories:
            logger.info(f"Aucune sous-catégorie pour {category['name']} - pas de frame créé")
            # Ne pas créer de frame si pas de sous-catégories
            return
        
        logger.info(f"Affichage de {len(subcategories)} sous-catégories pour {category['name']}")
        
        # Vérifier que la fenêtre existe encore
        try:
            if not self.winfo_exists():
                return
        except Exception:
            return
        
        try:
            category_data = self.categories_checkboxes[category['name']]
            category_frame = category_data.get('category_frame')
            
            if not category_frame:
                logger.warning(f"Frame de catégorie non trouvé pour {category['name']}")
                return
            
            # Créer le frame des sous-catégories seulement maintenant (si on a des sous-catégories)
            subcategories_frame = ctk.CTkFrame(category_frame)
            subcategories_frame.pack(fill="x", padx=20, pady=(0, 2))
            category_data['subcategories_frame'] = subcategories_frame
            
            # Stocker les sous-catégories
            if 'subcategories' not in category_data:
                category_data['subcategories'] = {}
            
            # Créer les checkboxes pour les sous-catégories avec indentation
            # Les ajouter dans le frame des sous-catégories de cette catégorie
            for subcat in subcategories:
                if not isinstance(subcat, dict) or 'name' not in subcat:
                    logger.warning(f"Sous-catégorie invalide: {subcat}")
                    continue
                    
                var = ctk.BooleanVar(value=False)
                checkbox = ctk.CTkCheckBox(
                    subcategories_frame,
                    text=f"└─ {subcat['name']}",  # Indentation visuelle
                    variable=var
                )
                checkbox.pack(anchor="w", padx=0, pady=1)  # Dans le frame déjà indenté
                
                # Ajouter un traceur pour gérer la sélection de la sous-catégorie
                var.trace_add('write', lambda *args, cat_name=category['name'], subcat_name=subcat['name']: 
                             self.on_subcategory_checkbox_changed(cat_name, subcat_name))
                
                category_data['subcategories'][subcat['name']] = {
                    'var': var,
                    'subcategory': subcat
                }
            
            logger.info(f"Sous-catégories affichées pour {category['name']}")
        except Exception as e:
            # Si une erreur se produit lors de la création des widgets, l'ignorer silencieusement
            # (cela arrive si la fenêtre est fermée pendant le chargement)
            logger.debug(f"Erreur lors de l'affichage des sous-catégories pour {category['name']}: {e}")
    
    def on_category_checkbox_changed(self, category_name: str):
        """Appelé quand la checkbox d'une catégorie change."""
        # Éviter les boucles infinies si on est déjà en train de mettre à jour
        if self._updating_checkboxes:
            logger.debug(f"Ignoré on_category_checkbox_changed pour {category_name} (mise à jour en cours)")
            return
        
        try:
            logger.debug(f"on_category_checkbox_changed appelé pour {category_name}")
            if category_name not in self.categories_checkboxes:
                logger.warning(f"Catégorie {category_name} non trouvée dans categories_checkboxes")
                return
            
            category_data = self.categories_checkboxes[category_name]
            is_selected = category_data['var'].get()
            logger.debug(f"Catégorie {category_name} sélectionnée: {is_selected}")
            
            # Si la catégorie est sélectionnée, sélectionner toutes ses sous-catégories
            if is_selected:
                if 'subcategories' in category_data and category_data['subcategories']:
                    logger.debug(f"Sélection de {len(category_data['subcategories'])} sous-catégories pour {category_name}")
                    # Activer le flag pour éviter les boucles
                    self._updating_checkboxes = True
                    try:
                        for subcat_name, subcat_data in category_data['subcategories'].items():
                            # Vérifier si déjà sélectionnée pour éviter les appels inutiles
                            if not subcat_data['var'].get():
                                logger.debug(f"Sélection de la sous-catégorie {subcat_name}")
                                subcat_data['var'].set(True)
                    finally:
                        self._updating_checkboxes = False
            else:
                # Si la catégorie est désélectionnée, désélectionner toutes ses sous-catégories
                if 'subcategories' in category_data and category_data['subcategories']:
                    logger.debug(f"Désélection de {len(category_data['subcategories'])} sous-catégories pour {category_name}")
                    # Activer le flag pour éviter les boucles
                    self._updating_checkboxes = True
                    try:
                        for subcat_name, subcat_data in category_data['subcategories'].items():
                            # Vérifier si déjà désélectionnée pour éviter les appels inutiles
                            if subcat_data['var'].get():
                                logger.debug(f"Désélection de la sous-catégorie {subcat_name}")
                                subcat_data['var'].set(False)
                    finally:
                        self._updating_checkboxes = False
        except Exception as e:
            logger.error(f"Erreur dans on_category_checkbox_changed pour {category_name}: {e}", exc_info=True)
            self._updating_checkboxes = False
    
    def on_subcategory_checkbox_changed(self, category_name: str, subcategory_name: str):
        """Appelé quand la checkbox d'une sous-catégorie change."""
        # Éviter les boucles infinies si on est déjà en train de mettre à jour
        if self._updating_checkboxes:
            logger.debug(f"Ignoré on_subcategory_checkbox_changed pour {category_name} -> {subcategory_name} (mise à jour en cours)")
            return
        
        try:
            logger.debug(f"on_subcategory_checkbox_changed appelé pour {category_name} -> {subcategory_name}")
            if category_name not in self.categories_checkboxes:
                logger.warning(f"Catégorie {category_name} non trouvée dans categories_checkboxes")
                return
            
            category_data = self.categories_checkboxes[category_name]
            if 'subcategories' not in category_data or subcategory_name not in category_data['subcategories']:
                logger.warning(f"Sous-catégorie {subcategory_name} non trouvée pour {category_name}")
                return
            
            subcategory_data = category_data['subcategories'][subcategory_name]
            is_selected = subcategory_data['var'].get()
            logger.debug(f"Sous-catégorie {subcategory_name} sélectionnée: {is_selected}")
            
            # Si la sous-catégorie est sélectionnée, sélectionner aussi la catégorie parente
            if is_selected:
                # Vérifier si la catégorie n'est pas déjà sélectionnée pour éviter les appels inutiles
                if not category_data['var'].get():
                    logger.debug(f"Sélection de la catégorie parente {category_name}")
                    # Activer le flag pour éviter les boucles
                    self._updating_checkboxes = True
                    try:
                        category_data['var'].set(True)
                    finally:
                        self._updating_checkboxes = False
                else:
                    logger.debug(f"Catégorie {category_name} déjà sélectionnée")
            # Si désélectionnée, on ne fait rien (la catégorie reste sélectionnée)
            else:
                logger.debug(f"Sous-catégorie {subcategory_name} désélectionnée, catégorie {category_name} reste sélectionnée")
        except Exception as e:
            logger.error(f"Erreur dans on_subcategory_checkbox_changed pour {category_name} -> {subcategory_name}: {e}", exc_info=True)
            self._updating_checkboxes = False
    
    def select_all_categories(self):
        """Sélectionne toutes les catégories et leurs sous-catégories."""
        # Vérifier que categories_checkboxes existe
        if not hasattr(self, 'categories_checkboxes') or not self.categories_checkboxes:
            return
        
        # Désactiver temporairement les traceurs pour éviter les boucles
        for name, data in self.categories_checkboxes.items():
            # Sélectionner d'abord toutes les sous-catégories
            if 'subcategories' in data:
                for subcat_name, subcat_data in data['subcategories'].items():
                    subcat_data['var'].set(True)
            # Puis sélectionner la catégorie (ce qui déclenchera le traceur mais c'est OK)
            data['var'].set(True)
    
    def deselect_all_categories(self):
        """Désélectionne toutes les catégories et leurs sous-catégories."""
        # Vérifier que categories_checkboxes existe
        if not hasattr(self, 'categories_checkboxes') or not self.categories_checkboxes:
            return
        
        # Activer le flag pour éviter les boucles
        self._updating_checkboxes = True
        try:
            # Désélectionner d'abord les catégories
            for name, data in self.categories_checkboxes.items():
                data['var'].set(False)
                # Puis désélectionner toutes les sous-catégories
                if 'subcategories' in data:
                    for subcat_name, subcat_data in data['subcategories'].items():
                        subcat_data['var'].set(False)
        finally:
            self._updating_checkboxes = False
    
    
    def on_category_selected(self, category: Dict[str, str]):
        """Appelé quand une catégorie est sélectionnée (pour Cristel)."""
        # Cette fonction n'est plus utilisée car les sous-catégories sont maintenant
        # chargées et affichées automatiquement sous chaque catégorie
        pass
    
    def load_subcategories(self, category: Dict[str, str]):
        """Charge les sous-catégories pour une catégorie (ancien système, ne plus utiliser)."""
        # Cette fonction n'est plus utilisée car les sous-catégories sont maintenant
        # chargées automatiquement dans update_categories_display via load_subcategories_for_display
        pass
    
    def subcategories_loaded(self, category: Dict[str, str], subcategories: List[Dict[str, str]]):
        """Appelé quand les sous-catégories sont chargées (ancien système, ne plus utiliser)."""
        # Cette fonction n'est plus utilisée car les sous-catégories sont maintenant
        # affichées directement sous chaque catégorie dans update_categories_display
        # Ne pas afficher le frame séparé
        pass
    
    def update_subcategories_display(self):
        """Met à jour l'affichage des sous-catégories (ancien système, ne plus utiliser)."""
        # Cette fonction n'est plus utilisée car les sous-catégories sont maintenant
        # affichées directement sous chaque catégorie dans update_categories_display
        # S'assurer que le frame séparé n'est jamais affiché
        self.subcategories_frame.pack_forget()
    
    def open_diagnostic_window(self):
        """Ouvre la fenêtre de diagnostic et retraitement."""
        if not self.selected_scraper:
            return
        
        # Import de la fenêtre de retraitement
        from apps.gui.reprocess_window import ReprocessWindow
        
        # Ouvrir la fenêtre
        reprocess_window = ReprocessWindow(self, self.selected_scraper)
    
    def start_import(self):
        """Démarre l'import."""
        if not self.selected_scraper:
            return
        
        # Si mode gamme pour Garnier
        if self.selected_scraper.name == "garnier" and self.mode_var.get() == "gamme":
            gamme_url = self.gamme_url_var.get().strip()
            category = self.gamme_category_var.get()
            
            if not gamme_url:
                self.safe_configure_label('status_label',
                    text="✗ Veuillez entrer une URL de gamme",
                    text_color="red"
                )
                return
            
            if not category:
                self.safe_configure_label('status_label',
                    text="✗ Veuillez sélectionner une catégorie",
                    text_color="red"
                )
                return
            
            # Récupérer les options
            try:
                limit = int(self.limit_var.get()) if self.limit_var.get() else 0
            except ValueError:
                limit = 0
            
            output_file = self.output_var.get().strip() if self.output_var.get() else None
            
            options = {
                'limit': limit if limit > 0 else None,
                'output': output_file,
                'headless': True,
                'gamme_url': gamme_url,
                'category': category,
                'retry_errors_after': self.retry_errors_var.get()
            }
            
            # Ouvrir la fenêtre de progression
            self.progress_window = ProgressWindow(self, f"Import {self.selected_scraper.get_display_name()} - Gamme")
            
            # Démarrer le scraping dans un thread
            def scrape_thread():
                def progress_callback(message, current, total):
                    if self.progress_window and not self.progress_window.is_cancelled:
                        self.progress_window.after(0, lambda: self.progress_window.update_progress(message, current, total))
                
                def log_callback(message):
                    if self.progress_window:
                        msg = message
                        def add_log_message():
                            if self.progress_window:
                                try:
                                    self.progress_window.add_log(msg)
                                except Exception as e:
                                    print(f"Erreur lors de l'ajout du log: {e}")
                        self.progress_window.after(0, add_log_message)
                
                def cancel_check():
                    """Vérifie si l'annulation a été demandée."""
                    return self.progress_window.is_cancelled if self.progress_window else False
                
                success, output_file, error = self.selected_scraper.scrape(
                    [],  # Pas de catégories pour le mode gamme
                    None,  # Pas de sous-catégories
                    options,
                    progress_callback,
                    log_callback,
                    cancel_check
                )
                
                if self.progress_window:
                    if self.progress_window.is_cancelled:
                        self.progress_window.after(0, lambda: self.progress_window.finish(False, None, "Annulation demandée par l'utilisateur"))
                    else:
                        final_success = success
                        final_output_file = output_file
                        final_error = error
                        self.progress_window.after(0, lambda: self.progress_window.finish(final_success, final_output_file, final_error))
            
            threading.Thread(target=scrape_thread, daemon=True).start()
            return
        
        # Mode catégories (code existant)
        # Récupérer les catégories et sous-catégories sélectionnées
        selected_categories = []
        selected_subcategories = []
        
        for name, data in self.categories_checkboxes.items():
            category_selected = data['var'].get()
            
            # Si Cristel avec sous-catégories intégrées
            if self.selected_scraper.supports_subcategories and 'subcategories' in data:
                # Vérifier les sous-catégories sélectionnées
                has_selected_subcategories = False
                for subcat_name, subcat_data in data['subcategories'].items():
                    if subcat_data['var'].get():
                        selected_subcategories.append(subcat_data['subcategory'])
                        has_selected_subcategories = True
                
                # Si la catégorie est sélectionnée mais aucune sous-catégorie, utiliser la catégorie
                if category_selected and not has_selected_subcategories:
                    selected_categories.append(data['category'])
                # Si des sous-catégories sont sélectionnées, ajouter la catégorie parente pour le traitement
                elif has_selected_subcategories:
                    # S'assurer que la catégorie parente est dans la liste pour le traitement
                    if data['category'] not in selected_categories:
                        selected_categories.append(data['category'])
            else:
                # Pour les autres fournisseurs, utiliser la catégorie si sélectionnée
                if category_selected:
                    selected_categories.append(data['category'])
        
        # Vérifier qu'au moins une catégorie ou sous-catégorie est sélectionnée
        if not selected_categories and not selected_subcategories:
            if not self.categories:
                self.safe_configure_label('status_label',
                    text="✗ Aucune catégorie disponible. Chargez d'abord les catégories.",
                    text_color="red"
                )
            else:
                self.safe_configure_label('status_label',
                    text="✗ Veuillez sélectionner au moins une catégorie ou sous-catégorie.",
                    text_color="red"
                )
            return
        
        # Convertir en None si vide pour compatibilité avec l'API
        if not selected_subcategories:
            selected_subcategories = None
        
        # Récupérer les options
        try:
            limit = int(self.limit_var.get()) if self.limit_var.get() else 0
        except ValueError:
            limit = 0
        
        output_file = self.output_var.get().strip() if self.output_var.get() else None
        
        options = {
            'limit': limit if limit > 0 else None,
            'output': output_file,
            'headless': True,
            'retry_errors_after': self.retry_errors_var.get()
        }
        
        # Ouvrir la fenêtre de progression
        self.progress_window = ProgressWindow(self, f"Import {self.selected_scraper.get_display_name()}")
        
        # Démarrer le scraping dans un thread
        def scrape_thread():
            def progress_callback(message, current, total):
                if self.progress_window and not self.progress_window.is_cancelled:
                    self.progress_window.after(0, lambda: self.progress_window.update_progress(message, current, total))
            
            def log_callback(message):
                if self.progress_window:
                    # Créer une closure pour capturer correctement la valeur de message
                    msg = message  # Capturer la valeur dans une variable locale
                    def add_log_message():
                        if self.progress_window:
                            try:
                                self.progress_window.add_log(msg)
                            except Exception as e:
                                print(f"Erreur lors de l'ajout du log: {e}")
                    self.progress_window.after(0, add_log_message)
            
            def cancel_check():
                """Vérifie si l'annulation a été demandée."""
                return self.progress_window.is_cancelled if self.progress_window else False
            
            success, output_file, error = self.selected_scraper.scrape(
                selected_categories,
                selected_subcategories,
                options,
                progress_callback,
                log_callback,
                cancel_check
            )
            
            if self.progress_window:
                # Si annulé, fermer la fenêtre
                if self.progress_window.is_cancelled:
                    self.progress_window.after(0, lambda: self.progress_window.finish(False, None, "Annulation demandée par l'utilisateur"))
                else:
                    # Capturer les variables dans la closure pour éviter les problèmes de scope
                    final_success = success
                    final_output_file = output_file
                    final_error = error
                    self.progress_window.after(0, lambda: self.progress_window.finish(final_success, final_output_file, final_error))
        
        threading.Thread(target=scrape_thread, daemon=True).start()
    
    def on_mode_changed(self):
        """Appelé quand le mode d'import change."""
        if self.mode_var.get() == "gamme":
            # Afficher le frame gamme et cacher les catégories
            self.gamme_frame.pack(fill="x", pady=(0, 20))
            self.categories_frame.pack_forget()
            # Remplir le dropdown des catégories si disponibles
            if self.available_categories:
                category_names = [cat['name'] for cat in self.available_categories]
                self.gamme_category_dropdown.configure(values=[""] + category_names)
            # Réinitialiser les champs
            self.gamme_url_var.set("")
            self.gamme_category_var.set("")
            self.url_status_label.configure(text="", text_color="gray")
        else:
            # Afficher les catégories et cacher le frame gamme
            self.gamme_frame.pack_forget()
            self.categories_frame.pack(fill="both", expand=True, pady=(0, 20))
    
    def verify_gamme_url(self):
        """Vérifie que l'URL de la gamme est valide et accessible."""
        url = self.gamme_url_var.get().strip()
        
        if not url:
            self.url_status_label.configure(text="✗ Veuillez entrer une URL", text_color="red")
            return False
        
        # Vérifier le format de l'URL
        import re
        from urllib.parse import urlparse
        
        if not url.startswith('http://') and not url.startswith('https://'):
            self.url_status_label.configure(text="✗ L'URL doit commencer par http:// ou https://", text_color="red")
            return False
        
        try:
            parsed = urlparse(url)
            if not parsed.netloc or 'garnier-thiebaut.adsi.me' not in parsed.netloc:
                self.url_status_label.configure(text="✗ URL invalide (doit être du domaine garnier-thiebaut.adsi.me)", text_color="red")
                return False
            
            if 'code_gamme' not in parsed.query:
                self.url_status_label.configure(text="✗ L'URL doit contenir le paramètre code_gamme", text_color="red")
                return False
        except Exception as e:
            self.url_status_label.configure(text=f"✗ Erreur de format: {e}", text_color="red")
            return False
        
        # Vérifier l'accessibilité avec requests
        self.url_status_label.configure(text="⏳ Vérification de l'accessibilité...", text_color="yellow")
        self.verify_url_button.configure(state="disabled")
        
        def check_url():
            import requests
            try:
                # Faire une requête HEAD pour vérifier l'accessibilité
                response = requests.head(url, timeout=10, allow_redirects=True)
                if response.status_code == 200:
                    self.after(0, lambda: self.url_status_label.configure(
                        text="✓ URL valide et accessible", 
                        text_color="green"
                    ))
                    self.after(0, lambda: self.verify_url_button.configure(state="normal"))
                    return True
                else:
                    self.after(0, lambda: self.url_status_label.configure(
                        text=f"✗ URL retourne le code {response.status_code}", 
                        text_color="red"
                    ))
                    self.after(0, lambda: self.verify_url_button.configure(state="normal"))
                    return False
            except requests.exceptions.RequestException as e:
                self.after(0, lambda: self.url_status_label.configure(
                    text=f"✗ URL non accessible: {str(e)}", 
                    text_color="red"
                ))
                self.after(0, lambda: self.verify_url_button.configure(state="normal"))
                return False
        
        threading.Thread(target=check_url, daemon=True).start()
        return True

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

