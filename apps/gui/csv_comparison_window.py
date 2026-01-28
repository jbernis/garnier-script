"""
Fenêtre de comparaison de deux fichiers CSV Shopify.
Permet de comparer les fichiers par Handle, sélectionner des colonnes et exporter.
"""

import customtkinter as ctk
from tkinter import ttk, filedialog
import tkinter as tk
from typing import Optional, Set, Dict, List
import pandas as pd
import os
import sys
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

# Ajouter le répertoire parent au path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class CSVComparisonWindow(ctk.CTkToplevel):
    """Fenêtre pour comparer deux fichiers CSV Shopify."""
    
    def __init__(self, parent):
        super().__init__(parent)
        
        self.title("Comparateur CSV Shopify")
        self.geometry("1600x900")
        self.resizable(True, True)
        
        # Configuration CustomTkinter
        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("blue")
        
        # Variables pour les DataFrames
        self.df_a: Optional[pd.DataFrame] = None
        self.df_b: Optional[pd.DataFrame] = None
        self.matched_df_a: Optional[pd.DataFrame] = None
        self.matched_df_b: Optional[pd.DataFrame] = None
        
        # Variables pour les sélections
        self.selected_cols_a: Set[str] = set()
        self.selected_cols_b: Set[str] = set()
        self.selected_rows_a: Set[str] = set()  # Set de Handles
        self.selected_rows_b: Set[str] = set()  # Set de Handles
        
        # Variables pour les widgets
        self.column_checkboxes_a: Dict[str, ctk.BooleanVar] = {}
        self.column_checkboxes_b: Dict[str, ctk.BooleanVar] = {}
        self.hidden_cols_a: Set[str] = set()
        self.hidden_cols_b: Set[str] = set()
        self.column_widths_a: Dict[str, int] = {}
        self.column_widths_b: Dict[str, int] = {}
        self.column_widths_shared: Dict[str, int] = {}
        self.row_base_tag_a: Dict[str, str] = {}
        self.row_base_tag_b: Dict[str, str] = {}
        
        # Tooltips pour colonnes spécifiques
        self._tooltip = None
        self._tooltip_textbox = None
        self._tooltip_after_id = None
        self._tooltip_columns = ['Body (HTML)', 'Tags', 'Image Alt Text']
        
        # Variables pour la synchronisation du scroll
        self._scrolling_a = False
        self._scrolling_b = False
        self._syncing_columns = False
        self._syncing_column_scroll = False
        
        # Créer l'interface
        self._create_widgets()
        
        # Centrer la fenêtre
        self.center_window()
        
        # Garder la fenêtre au premier plan
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
    
    def _create_widgets(self):
        """Crée les widgets de l'interface."""
        # Frame principal
        main_frame = ctk.CTkFrame(self)
        main_frame.pack(fill="both", expand=True, padx=10, pady=10)
        
        # Header avec boutons de chargement
        header_frame = ctk.CTkFrame(main_frame)
        header_frame.pack(fill="x", pady=(0, 10))
        
        # Titre
        title_label = ctk.CTkLabel(
            header_frame,
            text="🔀 Comparateur CSV Shopify",
            font=ctk.CTkFont(size=24, weight="bold")
        )
        title_label.pack(side="left", padx=20, pady=15)
        
        # Boutons de chargement
        buttons_frame = ctk.CTkFrame(header_frame, fg_color="transparent")
        buttons_frame.pack(side="left", expand=True, padx=20, pady=15)
        
        self.load_a_button = ctk.CTkButton(
            buttons_frame,
            text="📁 Charger Fichier A (Modèle)",
            command=self._load_file_a,
            width=200,
            height=30,
            font=ctk.CTkFont(size=12),
            fg_color="#1e3a5f",
            hover_color="#2b4a6b"
        )
        self.load_a_button.pack(side="left", padx=5)
        
        self.load_b_button = ctk.CTkButton(
            buttons_frame,
            text="📁 Charger Fichier B",
            command=self._load_file_b,
            width=200,
            height=30,
            font=ctk.CTkFont(size=12),
            fg_color="#1e5f3a",
            hover_color="#2b6b4a"
        )
        self.load_b_button.pack(side="left", padx=5)
        
        # Frame pour le contenu principal (panneaux colonnes + tableaux)
        content_frame = ctk.CTkFrame(main_frame)
        content_frame.pack(fill="both", expand=True, pady=(0, 10))
        content_frame.grid_columnconfigure(0, weight=0)
        content_frame.grid_columnconfigure(1, weight=1)
        content_frame.grid_columnconfigure(2, weight=0)
        content_frame.grid_rowconfigure(0, weight=1)
        
        # Panneau gauche : Colonnes de A
        left_panel = ctk.CTkFrame(content_frame, width=200)
        left_panel.grid(row=0, column=0, sticky="ns", padx=(10, 5), pady=10)
        left_panel.grid_propagate(False)
        
        left_label = ctk.CTkLabel(
            left_panel,
            text="Colonnes A",
            font=ctk.CTkFont(size=14, weight="bold"),
            text_color="#5dade2"
        )
        left_label.pack(pady=(10, 5))
        
        columns_row_a = ctk.CTkFrame(left_panel, fg_color="transparent")
        columns_row_a.pack(fill="both", expand=True, padx=10, pady=5)
        columns_row_a.grid_columnconfigure(0, weight=1)
        columns_row_a.grid_columnconfigure(1, weight=0)
        columns_row_a.grid_rowconfigure(0, weight=1)
        
        # CTkScrollableFrame pour le contenu
        self.columns_scroll_a = ctk.CTkScrollableFrame(columns_row_a)
        self.columns_scroll_a.grid(row=0, column=0, sticky="nsew")
        
        # Masquer la scrollbar interne
        if hasattr(self.columns_scroll_a, "_scrollbar"):
            self.columns_scroll_a._scrollbar.grid_remove()
        
        # Scrollbar externe courte
        scrollbar_container_a = ctk.CTkFrame(columns_row_a, width=16, height=120, fg_color="transparent")
        scrollbar_container_a.grid(row=0, column=1, sticky="n", padx=(2, 0), pady=(10, 0))
        scrollbar_container_a.grid_propagate(False)
        
        self.columns_scrollbar_a = ctk.CTkScrollbar(
            scrollbar_container_a,
            orientation="vertical"
        )
        self.columns_scrollbar_a.pack(fill="both", expand=True)
        
        # Connecter la scrollbar au canvas interne
        if hasattr(self.columns_scroll_a, "_parent_canvas"):
            self.columns_scrollbar_a.configure(command=self.columns_scroll_a._parent_canvas.yview)
            self.columns_scroll_a._parent_canvas.configure(yscrollcommand=self.columns_scrollbar_a.set)
        
        # Bindings pour le scroll
        self.columns_scroll_a.bind("<MouseWheel>", lambda e: self._sync_column_scroll(e, "a"))
        self.columns_scroll_a.bind("<Button-4>", lambda e: self._sync_column_scroll(e, "a"))
        self.columns_scroll_a.bind("<Button-5>", lambda e: self._sync_column_scroll(e, "a"))
        
        # Zone centrale : Tableaux (B en dessous de A, largeur identique)
        center_frame = ctk.CTkFrame(content_frame, width=700)
        center_frame.grid(row=0, column=1, sticky="nsew", padx=5, pady=10)
        center_frame.grid_propagate(False)
        center_frame.grid_columnconfigure(0, weight=1)
        center_frame.grid_rowconfigure(0, weight=1)
        center_frame.grid_rowconfigure(1, weight=1)
        
        # Tableau A
        table_a_frame = ctk.CTkFrame(center_frame, height=300)
        table_a_frame.grid(row=0, column=0, sticky="nsew", padx=0, pady=(0, 5))
        table_a_frame.grid_propagate(False)
        
        table_a_label = ctk.CTkLabel(
            table_a_frame,
            text="Fichier A (Modèle)",
            font=ctk.CTkFont(size=14, weight="bold"),
            text_color="#5dade2"
        )
        table_a_label.pack(pady=(5, 5))
        
        # Frame pour Treeview A avec scrollbars
        tree_a_container = ctk.CTkFrame(table_a_frame, fg_color="transparent")
        tree_a_container.pack(fill="both", expand=True, padx=5, pady=5)
        
        # Scrollbars pour A
        scrollbar_a_v = ctk.CTkScrollbar(tree_a_container, orientation="vertical")
        scrollbar_a_h = ctk.CTkScrollbar(tree_a_container, orientation="horizontal")
        
        # Treeview A
        self.tree_a = ttk.Treeview(
            tree_a_container,
            yscrollcommand=scrollbar_a_v.set,
            xscrollcommand=scrollbar_a_h.set,
            show="headings"
        )
        scrollbar_a_v.configure(command=lambda *args: self._sync_scroll_vertical_cmd("a", *args))
        scrollbar_a_h.configure(command=self.tree_a.xview)
        
        # Pack scrollbars et treeview
        scrollbar_a_v.pack(side="right", fill="y")
        scrollbar_a_h.pack(side="bottom", fill="x")
        self.tree_a.pack(side="left", fill="both", expand=True)
        
        # Bind scroll events pour synchronisation
        self.tree_a.bind("<MouseWheel>", lambda e: self._sync_scroll_vertical(e, "a"))
        self.tree_a.bind("<Button-4>", lambda e: self._sync_scroll_vertical(e, "a"))
        self.tree_a.bind("<Button-5>", lambda e: self._sync_scroll_vertical(e, "a"))
        scrollbar_a_v.bind("<B1-Motion>", lambda e: self._sync_scroll_vertical(e, "a"))
        scrollbar_a_h.bind("<B1-Motion>", lambda e: self._sync_scroll_horizontal(e, "a"))
        scrollbar_a_h.bind("<Button-1>", lambda e: self._sync_scroll_horizontal(e, "a"))
        self.tree_a.bind("<Shift-MouseWheel>", lambda e: self._sync_scroll_horizontal(e, "a"))
        self.tree_a.bind("<ButtonRelease-1>", lambda e: self._sync_column_widths("a"))
        
        # Tableau B
        table_b_frame = ctk.CTkFrame(center_frame, height=300)
        table_b_frame.grid(row=1, column=0, sticky="nsew", padx=0, pady=(5, 0))
        table_b_frame.grid_propagate(False)
        
        table_b_label = ctk.CTkLabel(
            table_b_frame,
            text="Fichier B",
            font=ctk.CTkFont(size=14, weight="bold"),
            text_color="#52c97a"
        )
        table_b_label.pack(pady=(5, 5))
        
        # Frame pour Treeview B avec scrollbars
        tree_b_container = ctk.CTkFrame(table_b_frame, fg_color="transparent")
        tree_b_container.pack(fill="both", expand=True, padx=5, pady=5)
        
        # Scrollbars pour B
        scrollbar_b_v = ctk.CTkScrollbar(tree_b_container, orientation="vertical")
        scrollbar_b_h = ctk.CTkScrollbar(tree_b_container, orientation="horizontal")
        
        # Treeview B
        self.tree_b = ttk.Treeview(
            tree_b_container,
            yscrollcommand=scrollbar_b_v.set,
            xscrollcommand=scrollbar_b_h.set,
            show="headings"
        )
        scrollbar_b_v.configure(command=lambda *args: self._sync_scroll_vertical_cmd("b", *args))
        scrollbar_b_h.configure(command=self.tree_b.xview)
        
        # Pack scrollbars et treeview
        scrollbar_b_v.pack(side="right", fill="y")
        scrollbar_b_h.pack(side="bottom", fill="x")
        self.tree_b.pack(side="left", fill="both", expand=True)
        
        # Bind scroll events pour synchronisation
        self.tree_b.bind("<MouseWheel>", lambda e: self._sync_scroll_vertical(e, "b"))
        self.tree_b.bind("<Button-4>", lambda e: self._sync_scroll_vertical(e, "b"))
        self.tree_b.bind("<Button-5>", lambda e: self._sync_scroll_vertical(e, "b"))
        scrollbar_b_v.bind("<B1-Motion>", lambda e: self._sync_scroll_vertical(e, "b"))
        scrollbar_b_h.bind("<B1-Motion>", lambda e: self._sync_scroll_horizontal(e, "b"))
        scrollbar_b_h.bind("<Button-1>", lambda e: self._sync_scroll_horizontal(e, "b"))
        self.tree_b.bind("<Shift-MouseWheel>", lambda e: self._sync_scroll_horizontal(e, "b"))
        self.tree_b.bind("<ButtonRelease-1>", lambda e: self._sync_column_widths("b"))
        
        # Panneau droit : Colonnes de B
        right_panel = ctk.CTkFrame(content_frame, width=200)
        right_panel.grid(row=0, column=2, sticky="ns", padx=(5, 10), pady=10)
        right_panel.grid_propagate(False)
        
        right_label = ctk.CTkLabel(
            right_panel,
            text="Colonnes B",
            font=ctk.CTkFont(size=14, weight="bold"),
            text_color="#52c97a"
        )
        right_label.pack(pady=(10, 5))
        
        columns_row_b = ctk.CTkFrame(right_panel, fg_color="transparent")
        columns_row_b.pack(fill="both", expand=True, padx=10, pady=5)
        columns_row_b.grid_columnconfigure(0, weight=1)
        columns_row_b.grid_columnconfigure(1, weight=0)
        columns_row_b.grid_rowconfigure(0, weight=1)
        
        # CTkScrollableFrame pour le contenu
        self.columns_scroll_b = ctk.CTkScrollableFrame(columns_row_b)
        self.columns_scroll_b.grid(row=0, column=0, sticky="nsew")
        
        # Masquer la scrollbar interne
        if hasattr(self.columns_scroll_b, "_scrollbar"):
            self.columns_scroll_b._scrollbar.grid_remove()
        
        # Scrollbar externe courte
        scrollbar_container_b = ctk.CTkFrame(columns_row_b, width=16, height=120, fg_color="transparent")
        scrollbar_container_b.grid(row=0, column=1, sticky="n", padx=(2, 0), pady=(10, 0))
        scrollbar_container_b.grid_propagate(False)
        
        self.columns_scrollbar_b = ctk.CTkScrollbar(
            scrollbar_container_b,
            orientation="vertical"
        )
        self.columns_scrollbar_b.pack(fill="both", expand=True)
        
        # Connecter la scrollbar au canvas interne
        if hasattr(self.columns_scroll_b, "_parent_canvas"):
            self.columns_scrollbar_b.configure(command=self.columns_scroll_b._parent_canvas.yview)
            self.columns_scroll_b._parent_canvas.configure(yscrollcommand=self.columns_scrollbar_b.set)
        
        # Bindings pour le scroll
        self.columns_scroll_b.bind("<MouseWheel>", lambda e: self._sync_column_scroll(e, "b"))
        self.columns_scroll_b.bind("<Button-4>", lambda e: self._sync_column_scroll(e, "b"))
        self.columns_scroll_b.bind("<Button-5>", lambda e: self._sync_column_scroll(e, "b"))
        
        self._setup_column_scroll_sync()
        
        # Frame pour les boutons d'action
        action_frame = ctk.CTkFrame(main_frame)
        action_frame.pack(fill="x", pady=(0, 10))
        
        # Label de statut
        self.status_label = ctk.CTkLabel(
            action_frame,
            text="Chargez les fichiers A et B pour commencer",
            font=ctk.CTkFont(size=12),
            text_color="gray"
        )
        self.status_label.pack(side="left", padx=20, pady=10)
        
        # Boutons centrés
        buttons_container = ctk.CTkFrame(action_frame, fg_color="transparent")
        buttons_container.pack(side="left", expand=True, pady=10)
        
        self.reset_columns_button = ctk.CTkButton(
            buttons_container,
            text="Réinitialiser colonnes",
            command=self._reset_columns,
            width=180,
            height=30,
            font=ctk.CTkFont(size=12),
            fg_color="#3b3b3b",
            hover_color="#4a4a4a"
        )
        self.reset_columns_button.pack(side="left", padx=10)
        
        # Bouton exporter
        self.export_button = ctk.CTkButton(
            buttons_container,
            text="💾 Exporter CSV",
            command=self._export_csv,
            width=200,
            height=30,
            font=ctk.CTkFont(size=14),
            state="disabled",
            fg_color="green",
            hover_color="darkgreen"
        )
        self.export_button.pack(side="left", padx=10)
    
    def _load_file_a(self):
        """Charge le fichier CSV A."""
        file_path = filedialog.askopenfilename(
            title="Sélectionner le fichier CSV A (Modèle)",
            filetypes=[("Fichiers CSV", "*.csv"), ("Tous les fichiers", "*.*")]
        )
        
        if not file_path:
            return
        
        try:
            self.df_a = pd.read_csv(file_path, encoding='utf-8', dtype=str, keep_default_na=False)
            
            # Vérifier la colonne Handle
            if 'Handle' not in self.df_a.columns:
                messagebox.showerror(
                    "Erreur",
                    "Le fichier CSV A ne contient pas la colonne 'Handle' requise."
                )
                self.df_a = None
                return
            
            # Mettre à jour le bouton
            self.load_a_button.configure(
                text=f"✓ {os.path.basename(file_path)}",
                fg_color="#5dade2",
                hover_color="#4aa3d4"
            )
            
            # Si les deux fichiers sont chargés, faire le matching
            if self.df_b is not None:
                self._match_by_handle()
            
            logger.info(f"Fichier A chargé: {len(self.df_a)} lignes, {len(self.df_a.columns)} colonnes")
            
        except Exception as e:
            messagebox.showerror(
                "Erreur",
                f"Erreur lors du chargement du fichier A:\n{str(e)}"
            )
            logger.error(f"Erreur chargement fichier A: {e}", exc_info=True)
    
    def _load_file_b(self):
        """Charge le fichier CSV B."""
        file_path = filedialog.askopenfilename(
            title="Sélectionner le fichier CSV B",
            filetypes=[("Fichiers CSV", "*.csv"), ("Tous les fichiers", "*.*")]
        )
        
        if not file_path:
            return
        
        try:
            self.df_b = pd.read_csv(file_path, encoding='utf-8', dtype=str, keep_default_na=False)
            
            # Vérifier la colonne Handle
            if 'Handle' not in self.df_b.columns:
                messagebox.showerror(
                    "Erreur",
                    "Le fichier CSV B ne contient pas la colonne 'Handle' requise."
                )
                self.df_b = None
                return
            
            # Mettre à jour le bouton
            self.load_b_button.configure(
                text=f"✓ {os.path.basename(file_path)}",
                fg_color="#5dade2",
                hover_color="#4aa3d4"
            )
            
            # Si les deux fichiers sont chargés, faire le matching
            if self.df_a is not None:
                self._match_by_handle()
            
            logger.info(f"Fichier B chargé: {len(self.df_b)} lignes, {len(self.df_b.columns)} colonnes")
            
        except Exception as e:
            messagebox.showerror(
                "Erreur",
                f"Erreur lors du chargement du fichier B:\n{str(e)}"
            )
            logger.error(f"Erreur chargement fichier B: {e}", exc_info=True)
    
    def _match_by_handle(self):
        """Fait le matching des fichiers par Handle."""
        if self.df_a is None or self.df_b is None:
            return
        
        try:
            # Récupérer les Handles uniques de A (modèle)
            handles_a = set(self.df_a['Handle'].unique())
            handles_a.discard('')  # Enlever les Handles vides
            
            if not handles_a:
                messagebox.showwarning(
                    "Avertissement",
                    "Le fichier A ne contient aucun Handle valide."
                )
                return
            
            # Filtrer A pour ne garder que les Handles uniques (première occurrence)
            self.matched_df_a = self.df_a.drop_duplicates(subset=['Handle'], keep='first').copy()
            self.matched_df_a = self.matched_df_a[self.matched_df_a['Handle'].isin(handles_a)].copy()
            
            # Filtrer B pour ne garder que les Handles présents dans A
            self.matched_df_b = self.df_b.drop_duplicates(subset=['Handle'], keep='first').copy()
            self.matched_df_b = self.matched_df_b[self.matched_df_b['Handle'].isin(handles_a)].copy()
            
            # Trier par Handle pour avoir le même ordre
            self.matched_df_a = self.matched_df_a.sort_values('Handle').reset_index(drop=True)
            self.matched_df_b = self.matched_df_b.sort_values('Handle').reset_index(drop=True)
            
            # Ajouter les Handles manquants dans B avec des valeurs vides
            handles_in_b = set(self.matched_df_b['Handle'].unique())
            missing_handles = handles_a - handles_in_b
            
            if missing_handles:
                # Créer des lignes vides pour les Handles manquants dans B
                missing_rows = []
                for handle in missing_handles:
                    row = {'Handle': handle}
                    for col in self.matched_df_b.columns:
                        if col != 'Handle':
                            row[col] = ''
                    missing_rows.append(row)
                
                if missing_rows:
                    missing_df = pd.DataFrame(missing_rows)
                    self.matched_df_b = pd.concat([self.matched_df_b, missing_df], ignore_index=True)
                    self.matched_df_b = self.matched_df_b.sort_values('Handle').reset_index(drop=True)
            
            # Afficher les tableaux
            self._display_tables()
            
            # Créer les panneaux de colonnes
            self._create_column_panels()
            
            # Activer le bouton d'export
            self.export_button.configure(state="normal")
            
            # Mettre à jour le statut
            matched_count = len(self.matched_df_a)
            total_a = len(self.df_a)
            total_b = len(self.df_b)
            
            self.status_label.configure(
                text=f"✓ {matched_count} Handle(s) correspondant(s) | A: {total_a} lignes | B: {total_b} lignes",
                text_color="green"
            )
            
            logger.info(f"Matching terminé: {matched_count} Handles correspondants")
            
        except Exception as e:
            messagebox.showerror(
                "Erreur",
                f"Erreur lors du matching par Handle:\n{str(e)}"
            )
            logger.error(f"Erreur matching: {e}", exc_info=True)
    
    def _display_tables(self):
        """Affiche les tableaux A et B."""
        if self.matched_df_a is None or self.matched_df_b is None:
            return
        
        # Nettoyer les tableaux existants
        for item in self.tree_a.get_children():
            self.tree_a.delete(item)
        for item in self.tree_b.get_children():
            self.tree_b.delete(item)
        
        # Colonnes pour A/B (communes d'abord, uniques à la fin)
        cols_a = list(self.matched_df_a.columns)
        cols_b = list(self.matched_df_b.columns)
        common_cols = [col for col in cols_a if col in cols_b]
        unique_a = [col for col in cols_a if col not in cols_b]
        unique_b = [col for col in cols_b if col not in cols_a]
        display_cols_a = common_cols + unique_a
        display_cols_b = common_cols + unique_b
        
        # Colonnes sans checkbox pour coller les handles à gauche
        self.tree_a['columns'] = display_cols_a
        self.tree_a['show'] = 'headings'
        
        self.tree_b['columns'] = display_cols_b
        self.tree_b['show'] = 'headings'
        
        # Réinitialiser l'état des colonnes masquées et largeurs
        self.hidden_cols_a.clear()
        self.hidden_cols_b.clear()
        default_width = 150
        self.column_widths_a = {col: self.column_widths_shared.get(col, default_width) for col in display_cols_a}
        self.column_widths_b = {col: self.column_widths_shared.get(col, default_width) for col in display_cols_b}
        for col in set(display_cols_a + display_cols_b):
            if col not in self.column_widths_shared:
                self.column_widths_shared[col] = default_width
        
        # Ajuster la largeur minimale selon le titre
        try:
            from tkinter import font as tkfont
            header_font = tkfont.Font(font=("TkDefaultFont", 11))
        except Exception:
            header_font = None
        for col in set(display_cols_a + display_cols_b):
            if header_font:
                title_width = header_font.measure(str(col)) + 24
                self.column_widths_shared[col] = max(self.column_widths_shared.get(col, default_width), title_width)

        # Configurer les en-têtes
        for col in display_cols_a:
            self.tree_a.heading(col, text=col, command=lambda c=col: self._toggle_column_visibility("a", c))
            width = self.column_widths_shared.get(col, default_width)
            self.tree_a.column(col, width=width, minwidth=80, stretch=False)
        
        for col in display_cols_b:
            self.tree_b.heading(col, text=col, command=lambda c=col: self._toggle_column_visibility("b", c))
            width = self.column_widths_shared.get(col, default_width)
            self.tree_b.column(col, width=width, minwidth=80, stretch=False)
        
        # Réinitialiser les sélections de rangées
        self.selected_rows_a.clear()
        self.selected_rows_b.clear()
        
        # Insérer les données
        self.row_base_tag_a.clear()
        self.row_base_tag_b.clear()
        for idx, row_a in self.matched_df_a.iterrows():
            handle = str(row_a['Handle'])
            
            # Valeurs pour A
            values_a = [str(row_a.get(col, '')) for col in display_cols_a]
            # Couleur alternée pour A
            tag_a = 'row_a_even' if idx % 2 == 0 else 'row_a_odd'
            self.row_base_tag_a[handle] = tag_a
            self.tree_a.insert('', 'end', values=values_a, tags=(handle, tag_a))
            
            # Trouver la rangée correspondante dans B
            row_b = self.matched_df_b[self.matched_df_b['Handle'] == handle]
            if not row_b.empty:
                row_b = row_b.iloc[0]
                values_b_data = [str(row_b.get(col, '')) for col in display_cols_b]
            else:
                values_b_data = [''] * len(display_cols_b)
            
            values_b = values_b_data
            # Couleur alternée pour B
            tag_b = 'row_b_even' if idx % 2 == 0 else 'row_b_odd'
            self.row_base_tag_b[handle] = tag_b
            self.tree_b.insert('', 'end', values=values_b, tags=(handle, tag_b))
        
        # Configurer les tags pour les couleurs (alternance)
        self.tree_a.tag_configure('row_a_even', background='#1e3a5f', foreground='white')
        self.tree_a.tag_configure('row_a_odd', background='#2b4a6b', foreground='white')
        self.tree_b.tag_configure('row_b_even', background='#1e5f3a', foreground='white')
        self.tree_b.tag_configure('row_b_odd', background='#2b6b4a', foreground='white')
        self.tree_a.tag_configure('row_a_selected', background='#2f5f8f', foreground='white')
        self.tree_b.tag_configure('row_b_selected', background='#2d7b53', foreground='white')
        
        # Bind les événements de clic sur les lignes
        self.tree_a.bind('<Button-1>', self._on_tree_a_click)
        self.tree_b.bind('<Button-1>', self._on_tree_b_click)
        self._apply_shared_column_widths()
    
    def _create_column_panels(self):
        """Crée les panneaux de sélection de colonnes."""
        if self.matched_df_a is None or self.matched_df_b is None:
            return
        
        # Nettoyer les panneaux existants
        for widget in self.columns_scroll_a.winfo_children():
            widget.destroy()
        for widget in self.columns_scroll_b.winfo_children():
            widget.destroy()
        
        self.column_checkboxes_a.clear()
        self.column_checkboxes_b.clear()
        self.selected_cols_a.clear()
        self.selected_cols_b.clear()
        
        # Colonnes de A (communes d'abord, uniques à la fin)
        cols_a = list(self.matched_df_a.columns)
        cols_b = list(self.matched_df_b.columns)
        common_cols = [col for col in cols_a if col in cols_b]
        unique_a = [col for col in cols_a if col not in cols_b]
        unique_b = [col for col in cols_b if col not in cols_a]
        display_cols_a = common_cols + unique_a
        display_cols_b = common_cols + unique_b
        for col in display_cols_a:
            var = ctk.BooleanVar(value=True)  # Par défaut, toutes A sélectionnées
            checkbox = ctk.CTkCheckBox(
                self.columns_scroll_a,
                text=col,
                variable=var,
                command=lambda c=col, v=var: self._update_column_selection(c, 'a', v.get()),
                font=ctk.CTkFont(size=11),
                height=28
            )
            checkbox.pack(anchor="w", padx=5, pady=2)
            self.column_checkboxes_a[col] = var
            self.selected_cols_a.add(col)
        
        # Colonnes de B
        for col in display_cols_b:
            var = ctk.BooleanVar(value=False)  # Par défaut, toutes B non sélectionnées
            checkbox = ctk.CTkCheckBox(
                self.columns_scroll_b,
                text=col,
                variable=var,
                command=lambda c=col, v=var: self._update_column_selection(c, 'b', v.get()),
                font=ctk.CTkFont(size=11),
                height=28
            )
            checkbox.pack(anchor="w", padx=5, pady=2)
            self.column_checkboxes_b[col] = var
    
    def _sync_scroll_vertical(self, event, source):
        """Synchronise le défilement vertical entre les deux tableaux."""
        if source == 'a' and not self._scrolling_b:
            self._scrolling_a = True
            try:
                if hasattr(event, "delta") and event.delta:
                    self.tree_a.yview_scroll(int(-1 * (event.delta / 120)), "units")
                elif hasattr(event, "num") and event.num in (4, 5):
                    self.tree_a.yview_scroll(-1 if event.num == 4 else 1, "units")
                top, _ = self.tree_a.yview()
                self.tree_b.yview_moveto(top)
            finally:
                self._scrolling_a = False
        elif source == 'b' and not self._scrolling_a:
            self._scrolling_b = True
            try:
                if hasattr(event, "delta") and event.delta:
                    self.tree_b.yview_scroll(int(-1 * (event.delta / 120)), "units")
                elif hasattr(event, "num") and event.num in (4, 5):
                    self.tree_b.yview_scroll(-1 if event.num == 4 else 1, "units")
                top, _ = self.tree_b.yview()
                self.tree_a.yview_moveto(top)
            finally:
                self._scrolling_b = False

    def _sync_scroll_vertical_cmd(self, source, *args):
        """Synchronise le défilement vertical via la scrollbar."""
        if source == 'a' and not self._scrolling_b:
            self._scrolling_a = True
            try:
                self.tree_a.yview(*args)
                top, _ = self.tree_a.yview()
                self.tree_b.yview_moveto(top)
            finally:
                self._scrolling_a = False
        elif source == 'b' and not self._scrolling_a:
            self._scrolling_b = True
            try:
                self.tree_b.yview(*args)
                top, _ = self.tree_b.yview()
                self.tree_a.yview_moveto(top)
            finally:
                self._scrolling_b = False
    
    def _sync_scroll_horizontal(self, event, source):
        """Synchronise le défilement horizontal entre les deux tableaux."""
        if source == 'a' and not self._scrolling_b:
            self._scrolling_a = True
            try:
                # Obtenir la position de scroll de A
                left, right = self.tree_a.xview()
                # Appliquer à B
                self.tree_b.xview_moveto(left)
            except:
                pass
            finally:
                self._scrolling_a = False
        elif source == 'b' and not self._scrolling_a:
            self._scrolling_b = True
            try:
                # Obtenir la position de scroll de B
                left, right = self.tree_b.xview()
                # Appliquer à A
                self.tree_a.xview_moveto(left)
            except:
                pass
            finally:
                self._scrolling_b = False
    
    def _update_column_selection(self, col_name: str, source: str, selected: bool):
        """Met à jour la sélection de colonnes."""
        if source == 'a':
            if selected:
                self.selected_cols_a.add(col_name)
                # Désélectionner B si présent
                b_var = self.column_checkboxes_b.get(col_name)
                if b_var and b_var.get():
                    b_var.set(False)
                    self.selected_cols_b.discard(col_name)
            else:
                # Forcer la sélection de B si disponible
                b_var = self.column_checkboxes_b.get(col_name)
                if b_var:
                    b_var.set(True)
                    self.selected_cols_b.add(col_name)
                    self.selected_cols_a.discard(col_name)
                else:
                    # Pas d'équivalent côté B, garder A sélectionné
                    a_var = self.column_checkboxes_a.get(col_name)
                    if a_var:
                        a_var.set(True)
                    self.selected_cols_a.add(col_name)
        else:  # source == 'b'
            if selected:
                self.selected_cols_b.add(col_name)
                # Désélectionner A si présent
                a_var = self.column_checkboxes_a.get(col_name)
                if a_var and a_var.get():
                    a_var.set(False)
                    self.selected_cols_a.discard(col_name)
            else:
                # Forcer la sélection de A si disponible
                a_var = self.column_checkboxes_a.get(col_name)
                if a_var:
                    a_var.set(True)
                    self.selected_cols_a.add(col_name)
                    self.selected_cols_b.discard(col_name)
                else:
                    # Pas d'équivalent côté A, garder B sélectionné
                    b_var = self.column_checkboxes_b.get(col_name)
                    if b_var:
                        b_var.set(True)
                    self.selected_cols_b.add(col_name)
    
    def _toggle_column_visibility(self, source: str, column: str):
        """Masque/affiche une colonne au clic sur l'en-tête."""
        if source == 'a':
            tree = self.tree_a
            hidden_cols = self.hidden_cols_a
            widths = self.column_widths_a
        else:
            tree = self.tree_b
            hidden_cols = self.hidden_cols_b
            widths = self.column_widths_b
        
        if column in hidden_cols:
            width = widths.get(column, 150)
            tree.column(column, width=width, minwidth=80, stretch=False)
            hidden_cols.discard(column)
        else:
            widths[column] = tree.column(column, 'width')
            self.column_widths_shared[column] = widths[column]
            tree.column(column, width=0, minwidth=0, stretch=False)
            hidden_cols.add(column)
    
    def _reset_columns(self):
        """Réaffiche toutes les colonnes masquées."""
        if self.matched_df_a is not None:
            for col in self.matched_df_a.columns:
                if col == '✓':
                    continue
                width = self.column_widths_shared.get(col, self.column_widths_a.get(col, 150))
                self.tree_a.column(col, width=width, minwidth=80, stretch=False)
            self.hidden_cols_a.clear()
        
        if self.matched_df_b is not None:
            for col in self.matched_df_b.columns:
                if col == '✓':
                    continue
                width = self.column_widths_shared.get(col, self.column_widths_b.get(col, 150))
                self.tree_b.column(col, width=width, minwidth=80, stretch=False)
            self.hidden_cols_b.clear()
    
    def _sync_column_widths(self, source: str):
        """Synchronise la largeur des colonnes entre A et B."""
        if self._syncing_columns:
            return
        
        if self.matched_df_a is None or self.matched_df_b is None:
            return
        
        if source == 'a':
            tree_src = self.tree_a
            tree_dst = self.tree_b
            widths_src = self.column_widths_a
            widths_dst = self.column_widths_b
            hidden_dst = self.hidden_cols_b
            cols_src = list(self.matched_df_a.columns)
        else:
            tree_src = self.tree_b
            tree_dst = self.tree_a
            widths_src = self.column_widths_b
            widths_dst = self.column_widths_a
            hidden_dst = self.hidden_cols_a
            cols_src = list(self.matched_df_b.columns)
        
        self._syncing_columns = True
        try:
            for col in cols_src:
                if col == '✓':
                    continue
                current_width = tree_src.column(col, 'width')
                if widths_src.get(col) != current_width:
                    widths_src[col] = current_width
                    self.column_widths_shared[col] = current_width
                    if col in tree_dst['columns'] and col not in hidden_dst:
                        tree_dst.column(col, width=current_width, minwidth=80, stretch=False)
                        widths_dst[col] = current_width
        finally:
            self._syncing_columns = False
    
    def _sync_column_scroll(self, event, source: str):
        """Synchronise le défilement des colonnes A/B."""
        if self._syncing_column_scroll:
            return
        src_scroll = self.columns_scroll_a if source == "a" else self.columns_scroll_b
        dst_scroll = self.columns_scroll_b if source == "a" else self.columns_scroll_a
        
        if not hasattr(src_scroll, "_parent_canvas") or not hasattr(dst_scroll, "_parent_canvas"):
            return
        
        src = src_scroll._parent_canvas
        dst = dst_scroll._parent_canvas
        
        self._syncing_column_scroll = True
        try:
            # Scroll source
            if hasattr(event, "delta") and event.delta:
                src.yview_scroll(int(-1 * (event.delta / 120)), "units")
            elif hasattr(event, "num") and event.num in (4, 5):
                src.yview_scroll(-1 if event.num == 4 else 1, "units")
            # Sync destination
            top, _ = src.yview()
            dst.yview_moveto(top)
        finally:
            self._syncing_column_scroll = False

    def _setup_column_scroll_sync(self):
        """Synchronise les barres de défilement internes des colonnes A/B."""
        if not hasattr(self.columns_scroll_a, "_parent_canvas") or not hasattr(self.columns_scroll_b, "_parent_canvas"):
            return
        canvas_a = self.columns_scroll_a._parent_canvas
        canvas_b = self.columns_scroll_b._parent_canvas

        # Stocker les yscrollcommand originaux
        original_yscroll_a = self.columns_scrollbar_a.set
        original_yscroll_b = self.columns_scrollbar_b.set

        def on_yview_a(*args):
            original_yscroll_a(*args)
            if self._syncing_column_scroll:
                return
            self._syncing_column_scroll = True
            try:
                if args:
                    canvas_b.yview_moveto(args[0])
            finally:
                self._syncing_column_scroll = False

        def on_yview_b(*args):
            original_yscroll_b(*args)
            if self._syncing_column_scroll:
                return
            self._syncing_column_scroll = True
            try:
                if args:
                    canvas_a.yview_moveto(args[0])
            finally:
                self._syncing_column_scroll = False

        canvas_a.configure(yscrollcommand=on_yview_a)
        canvas_b.configure(yscrollcommand=on_yview_b)
    
    def _on_tree_click_tooltip(self, event, source: str):
        """Toggle la bulle au clic pour les colonnes HTML, Tags et Image Alt Text."""
        tree = self.tree_a if source == "a" else self.tree_b
        region = tree.identify_region(event.x, event.y)
        
        if region != "cell":
            self._hide_tooltip()
            return
        
        row_id = tree.identify_row(event.y)
        column_id = tree.identify_column(event.x)
        
        if not row_id or not column_id:
            self._hide_tooltip()
            return
        
        # Identifier le nom de la colonne
        try:
            col_index = int(column_id.replace("#", "")) - 1
            columns = tree['columns']
            if col_index < 0 or col_index >= len(columns):
                self._hide_tooltip()
                return
            
            col_name = columns[col_index]
            
            # Vérifier si c'est une colonne qui nécessite un tooltip
            if col_name not in self._tooltip_columns:
                # Si on clique ailleurs, masquer la bulle
                self._hide_tooltip()
                return
            
            # Récupérer la valeur
            values = tree.item(row_id, "values")
            if col_index < 0 or col_index >= len(values):
                self._hide_tooltip()
                return
            
            value = str(values[col_index])
            
            # Toggle: si déjà visible, masquer, sinon afficher
            if self._tooltip is not None and self._tooltip.winfo_exists() and self._tooltip.winfo_viewable():
                self._hide_tooltip()
            else:
                self._show_tooltip(event.x_root + 10, event.y_root + 10, value)
            
        except Exception:
            self._hide_tooltip()
    
    def _show_tooltip(self, x: int, y: int, text: str):
        """Affiche une bulle d'information avec scrollbar."""
        if self._tooltip_after_id:
            self.after_cancel(self._tooltip_after_id)
            self._tooltip_after_id = None
        
        # Créer ou réutiliser la bulle
        if self._tooltip is None or not self._tooltip.winfo_exists():
            self._tooltip = ctk.CTkToplevel(self)
            self._tooltip.overrideredirect(True)
            self._tooltip.attributes("-topmost", True)
            
            container = ctk.CTkFrame(self._tooltip, fg_color="#2b2b2b")
            container.pack(fill="both", expand=True)
            
            self._tooltip_textbox = ctk.CTkTextbox(
                container,
                width=400,
                height=200,
                wrap="word",
                font=ctk.CTkFont(size=11),
                fg_color="#2b2b2b",
                text_color="white"
            )
            self._tooltip_textbox.pack(fill="both", expand=True, padx=2, pady=2)
        
        # Mettre à jour le contenu
        if self._tooltip_textbox is not None:
            self._tooltip_textbox.configure(state="normal")
            self._tooltip_textbox.delete("1.0", "end")
            self._tooltip_textbox.insert("1.0", text)
            self._tooltip_textbox.configure(state="disabled")
        
        # Positionner et afficher
        self._tooltip.geometry(f"+{x}+{y}")
        self._tooltip.deiconify()
    
    def _hide_tooltip(self):
        """Masque la bulle d'information."""
        if self._tooltip_after_id:
            self.after_cancel(self._tooltip_after_id)
            self._tooltip_after_id = None
        
        if self._tooltip is not None and self._tooltip.winfo_exists():
            self._tooltip.withdraw()
    
    def _apply_row_tag(self, tree: ttk.Treeview, handle: str, selected: bool, base_tag: Optional[str]):
        """Applique le tag sélectionné ou la couleur de base."""
        items = tree.tag_has(handle)
        if not items:
            return
        tags = [handle]
        if base_tag:
            tags.append(base_tag)
        if selected:
            tags.append('row_a_selected' if tree == self.tree_a else 'row_b_selected')
        tree.item(items[0], tags=tuple(tags))

    def _apply_shared_column_widths(self):
        """Force la même largeur de colonnes entre A et B."""
        if self.matched_df_a is None or self.matched_df_b is None:
            return
        for col in set(self.matched_df_a.columns) & set(self.matched_df_b.columns):
            shared = self.column_widths_shared.get(col, 150)
            self.column_widths_shared[col] = shared
            if col in self.tree_a['columns'] and col not in self.hidden_cols_a:
                self.tree_a.column(col, width=shared, minwidth=80, stretch=False)
            if col in self.tree_b['columns'] and col not in self.hidden_cols_b:
                self.tree_b.column(col, width=shared, minwidth=80, stretch=False)
    
    def _on_tree_a_click(self, event):
        """Gère les clics sur le tableau A."""
        region = self.tree_a.identify_region(event.x, event.y)
        if region == 'cell':
            # Vérifier si on clique sur une colonne avec tooltip
            try:
                column_id = self.tree_a.identify_column(event.x)
                col_index = int(column_id.replace("#", "")) - 1
                columns = self.tree_a['columns']
                if 0 <= col_index < len(columns):
                    col_name = columns[col_index]
                    if col_name in self._tooltip_columns:
                        # Afficher/masquer le tooltip
                        self._on_tree_click_tooltip(event, "a")
                        return  # Ne pas gérer la sélection de rangée
            except Exception:
                pass
            
            column = self.tree_a.identify_column(event.x)
            item = self.tree_a.identify_row(event.y)
            if not item:
                return
            tags = self.tree_a.item(item, 'tags')
            if tags:
                handle = tags[0]
                # Toggle la sélection
                if handle in self.selected_rows_a:
                    self.selected_rows_a.discard(handle)
                    self._apply_row_tag(self.tree_a, handle, selected=False, base_tag=self.row_base_tag_a.get(handle))
                else:
                    self.selected_rows_a.add(handle)
                    self._apply_row_tag(self.tree_a, handle, selected=True, base_tag=self.row_base_tag_a.get(handle))
                    if handle in self.selected_rows_b:
                        self.selected_rows_b.discard(handle)
                        self._apply_row_tag(self.tree_b, handle, selected=False, base_tag=self.row_base_tag_b.get(handle))
    
    def _on_tree_b_click(self, event):
        """Gère les clics sur le tableau B."""
        region = self.tree_b.identify_region(event.x, event.y)
        if region == 'cell':
            # Vérifier si on clique sur une colonne avec tooltip
            try:
                column_id = self.tree_b.identify_column(event.x)
                col_index = int(column_id.replace("#", "")) - 1
                columns = self.tree_b['columns']
                if 0 <= col_index < len(columns):
                    col_name = columns[col_index]
                    if col_name in self._tooltip_columns:
                        # Afficher/masquer le tooltip
                        self._on_tree_click_tooltip(event, "b")
                        return  # Ne pas gérer la sélection de rangée
            except Exception:
                pass
            
            column = self.tree_b.identify_column(event.x)
            item = self.tree_b.identify_row(event.y)
            if not item:
                return
            tags = self.tree_b.item(item, 'tags')
            if tags:
                handle = tags[0]
                # Toggle la sélection
                if handle in self.selected_rows_b:
                    self.selected_rows_b.discard(handle)
                    self._apply_row_tag(self.tree_b, handle, selected=False, base_tag=self.row_base_tag_b.get(handle))
                else:
                    self.selected_rows_b.add(handle)
                    self._apply_row_tag(self.tree_b, handle, selected=True, base_tag=self.row_base_tag_b.get(handle))
                    if handle in self.selected_rows_a:
                        self.selected_rows_a.discard(handle)
                        self._apply_row_tag(self.tree_a, handle, selected=False, base_tag=self.row_base_tag_a.get(handle))
    
    def _update_row_selection(self, handle: str, source: str, selected: Optional[bool]):
        """Met à jour la sélection de rangées."""
        # Cette méthode n'est plus utilisée directement mais conservée pour compatibilité
        pass
    
    def _export_csv(self):
        """Exporte le CSV avec les colonnes sélectionnées."""
        if not self.selected_cols_a and not self.selected_cols_b:
            self.status_label.configure(
                text="⚠️ Veuillez sélectionner au moins une colonne à exporter",
                text_color="orange"
            )
            return
        
        # Exporter TOUTES les rangées avec les colonnes sélectionnées
        if self.matched_df_a is None or self.matched_df_a.empty:
            self.status_label.configure(
                text="⚠️ Aucune donnée à exporter",
                text_color="orange"
            )
            return
        
        # Récupérer tous les handles
        all_handles = self.matched_df_a['Handle'].tolist()
        
        # Construire le DataFrame d'export
        export_rows = []
        
        for handle in all_handles:
            row_data = {}
            
            # Pour chaque colonne, prendre de A si checkbox A est sélectionnée, sinon de B
            all_columns = set(self.selected_cols_a) | set(self.selected_cols_b)
            
            for col in all_columns:
                # Vérifier si la colonne est sélectionnée dans A ou B
                col_from_a = col in self.selected_cols_a
                col_from_b = col in self.selected_cols_b
                
                if col_from_a and not col_from_b:
                    # Prendre de A
                    if self.matched_df_a is not None:
                        row_a = self.matched_df_a[self.matched_df_a['Handle'] == handle]
                        if not row_a.empty and col in row_a.columns:
                            row_data[col] = row_a.iloc[0][col]
                        else:
                            row_data[col] = ""
                    else:
                        row_data[col] = ""
                        
                elif col_from_b and not col_from_a:
                    # Prendre de B
                    if self.matched_df_b is not None:
                        row_b = self.matched_df_b[self.matched_df_b['Handle'] == handle]
                        if not row_b.empty and col in row_b.columns:
                            row_data[col] = row_b.iloc[0][col]
                        else:
                            row_data[col] = ""
                    else:
                        row_data[col] = ""
                        
                elif col_from_a and col_from_b:
                    # Les deux sont sélectionnées : exporter les deux avec suffixes
                    if self.matched_df_a is not None:
                        row_a = self.matched_df_a[self.matched_df_a['Handle'] == handle]
                        if not row_a.empty and col in row_a.columns:
                            row_data[f"{col}_A"] = row_a.iloc[0][col]
                        else:
                            row_data[f"{col}_A"] = ""
                    
                    if self.matched_df_b is not None:
                        row_b = self.matched_df_b[self.matched_df_b['Handle'] == handle]
                        if not row_b.empty and col in row_b.columns:
                            row_data[f"{col}_B"] = row_b.iloc[0][col]
                        else:
                            row_data[f"{col}_B"] = ""
            
            export_rows.append(row_data)
        
        if not export_rows:
            self.status_label.configure(
                text="⚠️ Aucune donnée à exporter",
                text_color="orange"
            )
            return
        
        # Créer le DataFrame d'export avec colonnes ordonnées
        # Ordre: colonnes communes, colonnes uniques A, colonnes uniques B
        cols_a = list(self.matched_df_a.columns)
        cols_b = list(self.matched_df_b.columns) if self.matched_df_b is not None else []
        common_cols = [col for col in cols_a if col in cols_b]
        unique_a = [col for col in cols_a if col not in cols_b]
        unique_b = [col for col in cols_b if col not in cols_a]
        
        # Construire l'ordre des colonnes pour l'export
        ordered_columns = []
        
        # Colonnes communes d'abord
        for col in common_cols:
            col_from_a = col in self.selected_cols_a
            col_from_b = col in self.selected_cols_b
            if col_from_a and col_from_b:
                ordered_columns.append(f"{col}_A")
                ordered_columns.append(f"{col}_B")
            elif col_from_a:
                ordered_columns.append(col)
            elif col_from_b:
                ordered_columns.append(col)
        
        # Colonnes uniques à A
        for col in unique_a:
            if col in self.selected_cols_a:
                ordered_columns.append(col)
        
        # Colonnes uniques à B
        for col in unique_b:
            if col in self.selected_cols_b:
                ordered_columns.append(col)
        
        # Créer le DataFrame avec les colonnes ordonnées
        export_df = pd.DataFrame(export_rows)
        
        # Réordonner les colonnes (ne garder que celles qui existent)
        existing_cols = [col for col in ordered_columns if col in export_df.columns]
        export_df = export_df[existing_cols]
        
        # Proposer un nom de fichier par défaut
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        default_filename = f"csv_comparison_export_{timestamp}.csv"
        
        # Demander où sauvegarder
        file_path = filedialog.asksaveasfilename(
            title="Enregistrer le CSV exporté",
            defaultextension=".csv",
            filetypes=[("Fichiers CSV", "*.csv"), ("Tous les fichiers", "*.*")],
            initialfile=default_filename
        )
        
        if not file_path:
            return
        
        try:
            # Sauvegarder
            export_df.to_csv(file_path, index=False, encoding='utf-8')
            
            self.status_label.configure(
                text=f"✅ CSV exporté: {len(export_rows)} rangées, {len(export_df.columns)} colonnes",
                text_color="green"
            )
            
            logger.info(f"CSV exporté: {file_path} ({len(export_rows)} rangées, {len(export_df.columns)} colonnes)")
            
        except Exception as e:
            self.status_label.configure(
                text=f"❌ Erreur lors de l'export: {str(e)}",
                text_color="red"
            )
            logger.error(f"Erreur export CSV: {e}", exc_info=True)
