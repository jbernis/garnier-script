"""
Fenêtre de gestion des imports CSV.
Permet de visualiser l'historique des imports et de supprimer des imports en cascade.
"""

import customtkinter as ctk
import logging
from datetime import datetime
from apps.ai_editor.db import AIPromptsDB

logger = logging.getLogger(__name__)


class ImportsManagerWindow(ctk.CTkToplevel):
    """Fenêtre de gestion des imports CSV."""
    
    def __init__(self, parent):
        super().__init__(parent)
        
        self.title("Gestion des Imports CSV")
        self.geometry("1000x600")
        
        # Centrer la fenêtre
        self.update_idletasks()
        width = self.winfo_width()
        height = self.winfo_height()
        x = (self.winfo_screenwidth() // 2) - (width // 2)
        y = (self.winfo_screenheight() // 2) - (height // 2)
        self.geometry(f'{width}x{height}+{x}+{y}')
        
        self.db = AIPromptsDB()
        
        # Variables pour les checkboxes
        self.import_checkboxes = {}  # {import_id: checkbox_var}
        
        self.setup_ui()
        self.load_imports()
    
    def setup_ui(self):
        """Configure l'interface utilisateur."""
        
        # Titre principal
        title = ctk.CTkLabel(
            self,
            text="📂 Gestion des Imports CSV",
            font=ctk.CTkFont(size=24, weight="bold")
        )
        title.pack(pady=(20, 10))
        
        # Description
        desc = ctk.CTkLabel(
            self,
            text="Visualisez et gérez l'historique de vos imports CSV",
            font=ctk.CTkFont(size=12),
            text_color="gray"
        )
        desc.pack(pady=(0, 20))
        
        # Frame scrollable pour la liste des imports
        self.imports_frame = ctk.CTkScrollableFrame(self, height=400)
        self.imports_frame.pack(fill="both", expand=True, padx=20, pady=(0, 10))
        
        # Frame pour les boutons d'action
        buttons_frame = ctk.CTkFrame(self)
        buttons_frame.pack(pady=(10, 10))
        
        # Boutons de sélection
        select_all_btn = ctk.CTkButton(
            buttons_frame,
            text="☑️ Tout sélectionner",
            command=self.select_all,
            width=150,
            fg_color="#2b8a3e",
            hover_color="#2f9e44"
        )
        select_all_btn.pack(side="left", padx=5)
        
        deselect_all_btn = ctk.CTkButton(
            buttons_frame,
            text="☐ Tout désélectionner",
            command=self.deselect_all,
            width=150,
            fg_color="gray",
            hover_color="darkgray"
        )
        deselect_all_btn.pack(side="left", padx=5)
        
        # Bouton supprimer la sélection
        delete_selected_btn = ctk.CTkButton(
            buttons_frame,
            text="🗑️ Supprimer la sélection",
            command=self.delete_selected,
            width=180,
            fg_color="red",
            hover_color="darkred"
        )
        delete_selected_btn.pack(side="left", padx=5)
        
        # Bouton rafraîchir
        refresh_btn = ctk.CTkButton(
            buttons_frame,
            text="🔄 Rafraîchir",
            command=self.load_imports,
            width=120
        )
        refresh_btn.pack(side="left", padx=5)
        
        # Label de statut
        self.status_label = ctk.CTkLabel(
            self,
            text="",
            font=ctk.CTkFont(size=12)
        )
        self.status_label.pack(pady=(0, 20))
    
    def load_imports(self):
        """Charge la liste des imports."""
        try:
            # Effacer les anciens widgets
            for widget in self.imports_frame.winfo_children():
                widget.destroy()
            
            # Réinitialiser les checkboxes
            self.import_checkboxes = {}
            
            # Récupérer tous les imports
            cursor = self.db.conn.cursor()
            cursor.execute('''
                SELECT 
                    ci.id,
                    ci.original_file_path,
                    ci.imported_at,
                    ci.total_rows,
                    COUNT(DISTINCT cr.handle) as unique_products,
                    COUNT(pr.id) as processing_count
                FROM csv_imports ci
                LEFT JOIN csv_rows cr ON ci.id = cr.csv_import_id
                LEFT JOIN csv_processing_results pr ON ci.id = pr.csv_import_id
                GROUP BY ci.id
                ORDER BY ci.imported_at DESC
            ''')
            
            imports = cursor.fetchall()
            
            if not imports:
                no_imports_label = ctk.CTkLabel(
                    self.imports_frame,
                    text="Aucun import trouvé",
                    text_color="gray",
                    font=ctk.CTkFont(size=14)
                )
                no_imports_label.pack(pady=50)
                return
            
            # Afficher chaque import
            for imp in imports:
                self.create_import_card(imp)
            
            self.status_label.configure(
                text=f"📊 {len(imports)} import(s) trouvé(s)",
                text_color="green"
            )
            
        except Exception as e:
            logger.error(f"Erreur lors du chargement des imports: {e}", exc_info=True)
            self.status_label.configure(
                text=f"❌ Erreur: {e}",
                text_color="red"
            )
    
    def create_import_card(self, imp):
        """Crée une carte pour afficher un import."""
        card = ctk.CTkFrame(self.imports_frame)
        card.pack(fill="x", pady=5, padx=10)
        
        # Frame principal avec checkbox à gauche
        main_frame = ctk.CTkFrame(card)
        main_frame.pack(fill="x", padx=15, pady=15)
        
        # Checkbox de sélection
        checkbox_var = ctk.BooleanVar(value=False)
        checkbox = ctk.CTkCheckBox(
            main_frame,
            text="",
            variable=checkbox_var,
            width=30
        )
        checkbox.pack(side="left", padx=(5, 10))
        
        # Sauvegarder la référence
        self.import_checkboxes[imp['id']] = checkbox_var
        
        # Info frame
        info_frame = ctk.CTkFrame(main_frame)
        info_frame.pack(side="left", fill="x", expand=True)
        
        # Nom du fichier
        file_name = imp['original_file_path'].split('/')[-1]
        file_label = ctk.CTkLabel(
            info_frame,
            text=f"📄 {file_name}",
            font=ctk.CTkFont(size=14, weight="bold"),
            anchor="w"
        )
        file_label.pack(anchor="w", padx=10, pady=(5, 2))
        
        # Chemin complet (grisé)
        path_label = ctk.CTkLabel(
            info_frame,
            text=f"Chemin: {imp['original_file_path']}",
            font=ctk.CTkFont(size=10),
            text_color="gray",
            anchor="w"
        )
        path_label.pack(anchor="w", padx=10, pady=2)
        
        # Date d'import
        try:
            import_date = datetime.fromisoformat(imp['imported_at'])
            date_str = import_date.strftime("%d/%m/%Y à %H:%M")
        except:
            date_str = imp['imported_at']
        
        date_label = ctk.CTkLabel(
            info_frame,
            text=f"📅 Importé le: {date_str}",
            font=ctk.CTkFont(size=11),
            text_color="gray",
            anchor="w"
        )
        date_label.pack(anchor="w", padx=10, pady=2)
        
        # Statistiques
        stats_label = ctk.CTkLabel(
            info_frame,
            text=f"📊 {imp['total_rows']} ligne(s) | {imp['unique_products']} produit(s) unique(s) | {imp['processing_count']} traitement(s)",
            font=ctk.CTkFont(size=11),
            text_color="#1f6aa5",
            anchor="w"
        )
        stats_label.pack(anchor="w", padx=10, pady=2)
    
    def select_all(self):
        """Sélectionne tous les imports."""
        for checkbox_var in self.import_checkboxes.values():
            checkbox_var.set(True)
        self.status_label.configure(
            text=f"✅ {len(self.import_checkboxes)} import(s) sélectionné(s)",
            text_color="green"
        )
    
    def deselect_all(self):
        """Désélectionne tous les imports."""
        for checkbox_var in self.import_checkboxes.values():
            checkbox_var.set(False)
        self.status_label.configure(
            text="ℹ️ Tous les imports désélectionnés",
            text_color="gray"
        )
    
    def delete_selected(self):
        """Supprime tous les imports sélectionnés."""
        # Récupérer les IDs sélectionnés
        selected_ids = [
            import_id 
            for import_id, checkbox_var in self.import_checkboxes.items() 
            if checkbox_var.get()
        ]
        
        if not selected_ids:
            self.status_label.configure(
                text="⚠️ Aucun import sélectionné",
                text_color="orange"
            )
            return
        
        # Demander confirmation
        from tkinter import messagebox
        
        confirm = messagebox.askyesno(
            "Confirmation de suppression multiple",
            f"Êtes-vous sûr de vouloir supprimer {len(selected_ids)} import(s) ?\n\n"
            f"⚠️ Cette action supprimera pour chaque import :\n"
            f"• Toutes les lignes CSV\n"
            f"• Tous les traitements associés\n"
            f"• Tous les changements de champs\n\n"
            f"Cette action est IRRÉVERSIBLE !",
            icon='warning'
        )
        
        if not confirm:
            return
        
        try:
            cursor = self.db.conn.cursor()
            
            # Supprimer tous les imports sélectionnés
            for import_id in selected_ids:
                cursor.execute('DELETE FROM csv_imports WHERE id = ?', (import_id,))
            
            self.db.conn.commit()
            
            logger.info(f"✅ {len(selected_ids)} import(s) supprimé(s) avec succès")
            
            self.status_label.configure(
                text=f"✅ {len(selected_ids)} import(s) supprimé(s) avec succès",
                text_color="green"
            )
            
            # Rafraîchir la liste
            self.load_imports()
            
        except Exception as e:
            logger.error(f"Erreur lors de la suppression des imports: {e}", exc_info=True)
            self.status_label.configure(
                text=f"❌ Erreur lors de la suppression: {e}",
                text_color="red"
            )
    
