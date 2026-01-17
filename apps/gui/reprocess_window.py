"""
Fenêtre de diagnostic et retraitement ciblé par catégorie.
"""

import customtkinter as ctk
from typing import Optional
from utils.garnier_db import GarnierDB
from utils.artiga_db import ArtigaDB
from utils.cristel_db import CristelDB
from utils.app_config import get_supplier_db_path
import logging
import threading
from apps.gui.progress_window import ProgressWindow

logger = logging.getLogger(__name__)


class ReprocessWindow(ctk.CTkToplevel):
    """Fenêtre de diagnostic et retraitement ciblé par catégorie."""
    
    def __init__(self, parent, scraper):
        super().__init__(parent)
        
        self.scraper = scraper
        self.current_category = None
        self.stats = None
        
        # Choisir la classe DB en fonction du scraper
        supplier_name = scraper.name.lower()
        if supplier_name == "garnier":
            self.db_class = GarnierDB
        elif supplier_name == "artiga":
            self.db_class = ArtigaDB
        elif supplier_name == "cristel":
            self.db_class = CristelDB
        else:
            raise ValueError(f"Scraper non supporté: {supplier_name}")
        
        # Configuration de la fenêtre
        self.title(f"Diagnostic & Retraitement - {scraper.name.title()}")
        self.geometry("700x800")
        self.resizable(True, True)
        
        # Forcer la fenêtre au premier plan
        self.lift()
        self.focus_force()
        self.attributes('-topmost', True)
        self.after(100, lambda: self.attributes('-topmost', False))
        
        # Variables pour les checkboxes (par défaut toutes cochées)
        self.reprocess_error_products = ctk.BooleanVar(value=True)
        self.reprocess_error_variants = ctk.BooleanVar(value=True)
        self.reprocess_pending_variants = ctk.BooleanVar(value=True)
        
        self._create_widgets()
        self._load_categories()
    
    def _create_widgets(self):
        """Crée les widgets de la fenêtre."""
        
        # Frame principal scrollable
        main_frame = ctk.CTkScrollableFrame(self)
        main_frame.pack(fill="both", expand=True, padx=10, pady=10)
        
        # Titre principal
        header = ctk.CTkLabel(
            main_frame,
            text="🔍 Diagnostic & Retraitement",
            font=ctk.CTkFont(size=20, weight="bold")
        )
        header.pack(pady=(10, 10))
        
        # [1] Sélection de la catégorie
        section1 = ctk.CTkFrame(main_frame)
        section1.pack(fill="x", padx=20, pady=(10, 10))
        
        ctk.CTkLabel(
            section1,
            text="[1] Sélection de la catégorie",
            font=ctk.CTkFont(size=14, weight="bold")
        ).pack(anchor="w", padx=10, pady=(10, 5))
        
        select_frame = ctk.CTkFrame(section1)
        select_frame.pack(fill="x", padx=10, pady=(0, 10))
        
        ctk.CTkLabel(select_frame, text="Catégorie:").pack(side="left", padx=5)
        
        self.category_combo = ctk.CTkComboBox(
            select_frame,
            values=["Chargement..."],
            width=580,
            command=self._on_category_selected
        )
        self.category_combo.pack(side="left", padx=5)
        
        # [2] Statistiques
        section2 = ctk.CTkFrame(main_frame)
        section2.pack(fill="x", padx=20, pady=10)
        
        ctk.CTkLabel(
            section2,
            text="[2] Statistiques de la catégorie",
            font=ctk.CTkFont(size=14, weight="bold")
        ).pack(anchor="w", padx=10, pady=(10, 5))
        
        # Frame pour les stats
        self.stats_frame = ctk.CTkFrame(section2, fg_color=("gray90", "gray20"))
        self.stats_frame.pack(fill="x", padx=10, pady=(0, 10))
        
        self.stats_label = ctk.CTkLabel(
            self.stats_frame,
            text="Sélectionnez une catégorie pour voir les statistiques",
            font=ctk.CTkFont(size=13),
            justify="left"
        )
        self.stats_label.pack(padx=20, pady=20)
        
        # [3] Actions
        section3 = ctk.CTkFrame(main_frame)
        section3.pack(fill="x", padx=20, pady=(10, 20))
        
        ctk.CTkLabel(
            section3,
            text="[3] Actions de retraitement",
            font=ctk.CTkFont(size=14, weight="bold")
        ).pack(anchor="w", padx=10, pady=(10, 5))
        
        options_frame = ctk.CTkFrame(section3)
        options_frame.pack(fill="x", padx=10, pady=(0, 10))
        
        self.error_products_check = ctk.CTkCheckBox(
            options_frame,
            text="1️⃣ Re-collecter les produits en erreur (0)",
            variable=self.reprocess_error_products
        )
        self.error_products_check.pack(anchor="w", padx=10, pady=5)
        
        self.error_variants_check = ctk.CTkCheckBox(
            options_frame,
            text="2️⃣ Retraiter les variants en erreur (0)",
            variable=self.reprocess_error_variants
        )
        self.error_variants_check.pack(anchor="w", padx=10, pady=5)
        
        self.pending_variants_check = ctk.CTkCheckBox(
            options_frame,
            text="3️⃣ Retraiter les variants pending (0)",
            variable=self.reprocess_pending_variants
        )
        self.pending_variants_check.pack(anchor="w", padx=10, pady=5)
        
        info_label = ctk.CTkLabel(
            options_frame,
            text="💡 Ordre d'exécution : Produits → Variants erreur → Variants pending",
            font=ctk.CTkFont(size=11),
            text_color=("gray50", "gray60")
        )
        info_label.pack(anchor="w", padx=10, pady=(5, 10))
        
        # Boutons d'action
        buttons_frame = ctk.CTkFrame(section3)
        buttons_frame.pack(fill="x", padx=10, pady=(10, 10))
        
        self.start_btn = ctk.CTkButton(
            buttons_frame,
            text="🔄 Lancer le retraitement",
            command=self._start_reprocessing,
            state="disabled",
            height=40
        )
        self.start_btn.pack(side="left", padx=5, expand=True, fill="x")
        
        cancel_btn = ctk.CTkButton(
            buttons_frame,
            text="Fermer",
            command=self.destroy,
            fg_color="gray",
            hover_color="darkgray",
            height=40
        )
        cancel_btn.pack(side="left", padx=5)
    
    def _load_categories(self):
        """Charge les catégories disponibles depuis la DB."""
        try:
            db_path = get_supplier_db_path(self.scraper.name.lower())
            db = self.db_class(db_path)
            
            # Pour Artiga et Cristel, on utilise les sous-catégories
            # Pour Garnier, on utilise les catégories (gammes)
            if self.scraper.name.lower() in ['artiga', 'cristel']:
                categories = db.get_available_subcategories()
            else:
                categories = db.get_available_categories()
            
            db.close()
            
            if categories:
                self.category_combo.configure(values=categories)
                self.category_combo.set(categories[0])
                self._on_category_selected(categories[0])
            else:
                label = "sous-catégorie" if self.scraper.name.lower() in ['artiga', 'cristel'] else "catégorie"
                self.category_combo.configure(values=[f"Aucune {label}"])
                self.category_combo.set(f"Aucune {label}")
                self.stats_label.configure(text=f"Aucune {label} trouvée dans la base de données")
        except Exception as e:
            logger.error(f"Erreur lors du chargement des catégories: {e}", exc_info=True)
            self.category_combo.configure(values=["Erreur"])
            self.stats_label.configure(text=f"Erreur lors du chargement: {e}")
    
    def _on_category_selected(self, category: str):
        """Appelé quand une catégorie est sélectionnée."""
        self.current_category = category
        self._load_stats()
    
    def _load_stats(self):
        """Charge et affiche les statistiques de la catégorie."""
        if not self.current_category or self.current_category in ["Aucune catégorie", "Erreur", "Chargement..."]:
            return
        
        try:
            db_path = get_supplier_db_path(self.scraper.name.lower())
            db = self.db_class(db_path)
            self.stats = db.get_category_stats(self.current_category)
            db.close()
            
            # Formater l'affichage
            products = self.stats['products']
            variants = self.stats['variants']
            
            # Calcul du pourcentage de complétion
            prod_pct = (products['completed'] / products['total'] * 100) if products['total'] > 0 else 0
            var_pct = (variants['completed'] / variants['total'] * 100) if variants['total'] > 0 else 0
            
            text = f"""
📦 PRODUITS ({prod_pct:.1f}% complété)
   • Completed: {products['completed']:>4}  ✅
   • Pending:   {products['pending']:>4}  ⏳
   • Error:     {products['error']:>4}  ❌
   {'─' * 30}
   Total:       {products['total']:>4}

🔖 VARIANTS ({var_pct:.1f}% complété)
   • Completed: {variants['completed']:>4}  ✅
   • Pending:   {variants['pending']:>4}  ⏳
   • Error:     {variants['error']:>4}  ❌
   {'─' * 30}
   Total:       {variants['total']:>4}
"""
            
            self.stats_label.configure(
                text=text,
                font=ctk.CTkFont(size=13, family="Monaco")
            )
            
            # Activer le bouton de retraitement seulement s'il y a du travail
            has_work = (variants['error'] + variants['pending'] + products['error']) > 0
            self.start_btn.configure(state="normal" if has_work else "disabled")
            
            # Mettre à jour le texte des checkboxes (dans l'ordre d'exécution)
            self.error_products_check.configure(
                text=f"1️⃣ Re-collecter les produits en erreur ({products['error']})",
                state="normal" if products['error'] > 0 else "disabled"
            )
            self.error_variants_check.configure(
                text=f"2️⃣ Retraiter les variants en erreur ({variants['error']})",
                state="normal" if variants['error'] > 0 else "disabled"
            )
            self.pending_variants_check.configure(
                text=f"3️⃣ Retraiter les variants pending ({variants['pending']})",
                state="normal" if variants['pending'] > 0 else "disabled"
            )
            
        except Exception as e:
            logger.error(f"Erreur lors du chargement des stats: {e}")
            self.stats_label.configure(text=f"Erreur: {e}")
    
    def _start_reprocessing(self):
        """Lance le retraitement selon les options sélectionnées."""
        if not self.current_category or not self.stats:
            return
        
        # Déterminer quelles actions sont nécessaires
        # IMPORTANT : Les produits doivent être retraités EN PREMIER
        actions = []
        
        # 1. Re-collecter les produits en erreur (si sélectionné)
        if self.reprocess_error_products.get() and self.stats['products']['error'] > 0:
            actions.append(('recollect_error_products', 'Re-collecte des produits en erreur'))
        
        # 2. Retraiter les variants en erreur (si sélectionné)
        if self.reprocess_error_variants.get() and self.stats['variants']['error'] > 0:
            actions.append(('process_error_variants', 'Retraitement des variants en erreur'))
        
        # 3. Retraiter les variants pending (si sélectionné)
        if self.reprocess_pending_variants.get() and self.stats['variants']['pending'] > 0:
            actions.append(('process_pending_variants', 'Retraitement des variants pending'))
        
        if not actions:
            logger.warning("Aucune action sélectionnée pour le retraitement")
            return
        
        # Ouvrir la fenêtre de progression
        progress_window = ProgressWindow(
            self,
            title="Retraitement en cours"
        )
        
        # Lancer le retraitement dans un thread
        def run_reprocessing():
            try:
                for action_type, action_label in actions:
                    progress_window.add_log(f"\n{'='*50}")
                    progress_window.add_log(f"▶ {action_label}...")
                    progress_window.add_log(f"{'='*50}\n")
                    
                    if action_type == 'process_error_variants':
                        self._process_variants(progress_window, 'error')
                    elif action_type == 'process_pending_variants':
                        self._process_variants(progress_window, 'pending')
                    elif action_type == 'recollect_error_products':
                        self._recollect_products(progress_window)
                
                progress_window.add_log("\n✅ Retraitement terminé avec succès !")
                progress_window.finish(success=True)
                
                # Actualiser les stats
                self.after(500, self._load_stats)
                
            except Exception as e:
                logger.error(f"Erreur lors du retraitement: {e}", exc_info=True)
                progress_window.add_log(f"\n❌ Erreur lors du retraitement: {e}")
                progress_window.finish(success=False, error=str(e))
        
        thread = threading.Thread(target=run_reprocessing, daemon=True)
        thread.start()
    
    def _process_variants(self, progress_window, status: str):
        """Lance le script de traitement des variants."""
        import subprocess
        import sys
        import os
        
        # Obtenir le répertoire du projet (où se trouve le script)
        project_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        supplier_dir = self.scraper.name.lower()
        
        cmd = [
            sys.executable,
            os.path.join(supplier_dir, 'scraper-process.py'),
            '--category', self.current_category,
            '--status', status
        ]
        
        progress_window.add_log(f"Répertoire: {project_dir}")
        progress_window.add_log(f"Commande: {' '.join(cmd)}\n")
        
        # Exécuter le processus avec affichage en temps réel
        process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1,
            universal_newlines=True,
            cwd=project_dir
        )
        
        # Lire et afficher les logs en temps réel
        for line in iter(process.stdout.readline, ''):
            if line:
                progress_window.add_log(line.rstrip())
        
        process.wait()
        
        if process.returncode != 0:
            progress_window.add_log(f"\n❌ Le script a échoué avec le code {process.returncode}")
            raise Exception(f"Le script a retourné le code d'erreur {process.returncode}")
    
    def _recollect_products(self, progress_window):
        """Lance le script de re-collecte des produits en erreur."""
        import subprocess
        import sys
        import os
        
        # Obtenir le répertoire du projet (où se trouve le script)
        project_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        supplier_dir = self.scraper.name.lower()
        
        cmd = [
            sys.executable,
            os.path.join(supplier_dir, 'scraper-collect.py'),
            '--category', self.current_category,
            '--retry-errors-only'
        ]
        
        progress_window.add_log(f"Répertoire: {project_dir}")
        progress_window.add_log(f"Commande: {' '.join(cmd)}\n")
        
        # Exécuter le processus avec affichage en temps réel
        process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1,
            universal_newlines=True,
            cwd=project_dir
        )
        
        # Lire et afficher les logs en temps réel
        for line in iter(process.stdout.readline, ''):
            if line:
                progress_window.add_log(line.rstrip())
        
        process.wait()
        
        if process.returncode != 0:
            progress_window.add_log(f"\n❌ Le script a échoué avec le code {process.returncode}")
            raise Exception(f"Le script a retourné le code d'erreur {process.returncode}")
