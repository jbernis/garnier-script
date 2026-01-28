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
        
        # Variables pour les checkboxes
        # Par défaut, SEULE l'action principale est cochée
        self.reprocess_error_gammes = ctk.BooleanVar(value=False)  # Décoché par défaut
        self.reprocess_error_products = ctk.BooleanVar(value=False)  # Décoché par défaut
        self.reprocess_pending_variants = ctk.BooleanVar(value=True)  # ✅ ACTION PRINCIPALE - Coché par défaut
        self.reprocess_error_variants = ctk.BooleanVar(value=False)  # Décoché par défaut
        
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
        select_frame.pack(fill="x", padx=10, pady=(0, 5))
        
        ctk.CTkLabel(select_frame, text="Catégorie:").pack(side="left", padx=5)
        
        self.category_combo = ctk.CTkComboBox(
            select_frame,
            values=["Chargement..."],
            width=580,
            command=self._on_category_selected
        )
        self.category_combo.pack(side="left", padx=5)
        
        # Bouton Rafraîchir en dessous
        refresh_frame = ctk.CTkFrame(section1)
        refresh_frame.pack(fill="x", padx=10, pady=(0, 10))
        
        refresh_btn = ctk.CTkButton(
            refresh_frame,
            text="🔄 Rafraîchir les statistiques",
            command=self._refresh_stats,
            width=200,
            height=32
        )
        refresh_btn.pack(side="left", padx=5)
        
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
        
        # Checkbox pour les gammes (uniquement pour Garnier)
        if self.scraper.name.lower() == 'garnier':
            # Label explicatif
            info_label = ctk.CTkLabel(
                options_frame,
                text="⚠️ Les gammes pending/processing ont déjà leurs produits collectés.\n   → Utilisez plutôt 'Retraiter les variants pending' pour les traiter.",
                font=ctk.CTkFont(size=11),
                text_color=("orange", "orange"),
                justify="left"
            )
            info_label.pack(anchor="w", padx=10, pady=(5, 10))
            
            self.error_gammes_check = ctk.CTkCheckBox(
                options_frame,
                text="0️⃣ Re-collecter les gammes en ERREUR (0) - Force une nouvelle collecte",
                variable=self.reprocess_error_gammes
            )
            self.error_gammes_check.pack(anchor="w", padx=10, pady=5)
            
            # Séparateur visuel
            separator = ctk.CTkLabel(
                options_frame,
                text="─" * 60,
                font=ctk.CTkFont(size=10),
                text_color=("gray50", "gray50")
            )
            separator.pack(anchor="w", padx=10, pady=(10, 5))
        
        self.error_products_check = ctk.CTkCheckBox(
            options_frame,
            text="1️⃣ Re-collecter les produits en ERREUR (0) - Force une nouvelle collecte",
            variable=self.reprocess_error_products
        )
        self.error_products_check.pack(anchor="w", padx=10, pady=5)
        
        # Label pour les variants (principal)
        variants_label = ctk.CTkLabel(
            options_frame,
            text="💡 RECOMMANDÉ : Traiter les détails des variants",
            font=ctk.CTkFont(size=12, weight="bold"),
            text_color=("green", "lightgreen"),
            justify="left"
        )
        variants_label.pack(anchor="w", padx=10, pady=(15, 5))
        
        self.pending_variants_check = ctk.CTkCheckBox(
            options_frame,
            text="2️⃣ Traiter les variants PENDING (0) - Extrait nom, description, prix, images",
            variable=self.reprocess_pending_variants,
            font=ctk.CTkFont(size=13, weight="bold")
        )
        self.pending_variants_check.pack(anchor="w", padx=10, pady=5)
        
        self.error_variants_check = ctk.CTkCheckBox(
            options_frame,
            text="3️⃣ Re-traiter les variants en ERREUR (0) - Nouvelle tentative",
            variable=self.reprocess_error_variants
        )
        self.error_variants_check.pack(anchor="w", padx=10, pady=5)
        
        order_text = "Gammes → Produits → Variants erreur → Variants pending" if self.scraper.name.lower() == 'garnier' else "Produits → Variants erreur → Variants pending"
        info_label = ctk.CTkLabel(
            options_frame,
            text=f"💡 Ordre d'exécution : {order_text}",
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
            height=30
        )
        self.start_btn.pack(side="left", padx=5, expand=True, fill="x")
        
        cancel_btn = ctk.CTkButton(
            buttons_frame,
            text="Fermer",
            command=self.destroy,
            fg_color="gray",
            hover_color="darkgray",
            height=30
        )
        cancel_btn.pack(side="left", padx=5)
        
        # [4] Export CSV
        section4 = ctk.CTkFrame(main_frame)
        section4.pack(fill="x", padx=20, pady=(10, 20))
        
        ctk.CTkLabel(
            section4,
            text="[4] Export CSV",
            font=ctk.CTkFont(size=14, weight="bold")
        ).pack(anchor="w", padx=10, pady=(10, 5))
        
        export_frame = ctk.CTkFrame(section4)
        export_frame.pack(fill="x", padx=10, pady=(0, 10))
        
        # Checkbox pour exclure les erreurs
        self.exclude_errors_var = ctk.BooleanVar(value=False)  # Décoché par défaut
        exclude_errors_check = ctk.CTkCheckBox(
            export_frame,
            text="Exclure les produits en erreur du CSV",
            variable=self.exclude_errors_var,
            command=self._on_exclude_errors_changed
        )
        exclude_errors_check.pack(anchor="w", padx=10, pady=5)
        
        # Bouton d'export
        export_buttons_frame = ctk.CTkFrame(export_frame)
        export_buttons_frame.pack(fill="x", padx=10, pady=(5, 10))
        
        self.export_csv_btn = ctk.CTkButton(
            export_buttons_frame,
            text="📥 Exporter CSV",
            command=self._export_csv,
            state="disabled",
            height=30,
            fg_color="green",
            hover_color="darkgreen"
        )
        self.export_csv_btn.pack(side="left", padx=5)
    
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
    
    def _refresh_stats(self):
        """Rafraîchit les statistiques de la catégorie actuelle."""
        if self.current_category:
            logger.info(f"Rafraîchissement des statistiques pour: {self.current_category}")
            self._load_stats()
    
    def _load_stats(self):
        """Charge et affiche les statistiques de la catégorie."""
        if not self.current_category or self.current_category in ["Aucune catégorie", "Erreur", "Chargement..."]:
            return
        
        try:
            db_path = get_supplier_db_path(self.scraper.name.lower())
            db = self.db_class(db_path)
            self.stats = db.get_category_stats(self.current_category)
            
            # Récupérer les stats des gammes si Garnier
            gammes_stats = None
            if self.scraper.name.lower() == 'garnier' and hasattr(db, 'get_category_gamme_stats'):
                gammes_stats = db.get_category_gamme_stats(self.current_category)
            
            db.close()
            
            # Formater l'affichage
            products = self.stats['products']
            variants = self.stats['variants']
            
            # Calcul du pourcentage de complétion
            prod_pct = (products['completed'] / products['total'] * 100) if products['total'] > 0 else 0
            var_pct = (variants['completed'] / variants['total'] * 100) if variants['total'] > 0 else 0
            
            text = ""
            
            # Ajouter les stats des gammes si disponibles (Garnier uniquement)
            if gammes_stats:
                gamme_pct = (gammes_stats['completed'] / gammes_stats['total'] * 100) if gammes_stats['total'] > 0 else 0
                processing_count = gammes_stats.get('processing', 0)  # Peut ne pas exister dans anciennes bases
                text += f"""
🎯 GAMMES ({gamme_pct:.1f}% complété)
   • Completed:  {gammes_stats['completed']:>4}  ✅
   • Processing: {processing_count:>4}  🔄
   • Pending:    {gammes_stats['pending']:>4}  ⏳
   • Error:      {gammes_stats['error']:>4}  ❌
   {'─' * 30}
   Total:        {gammes_stats['total']:>4}

"""
            
            text += f"""
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
            
            # Configurer le label des stats (protégé)
            try:
                if hasattr(self, 'stats_label'):
                    self.stats_label.configure(
                        text=text,
                        font=ctk.CTkFont(size=13, family="Monaco")
                    )
            except Exception:
                pass
            
            # Activer le bouton de retraitement seulement s'il y a du travail
            has_work = (variants['error'] + variants['pending'] + products['error']) > 0
            if gammes_stats:
                has_work = has_work or gammes_stats['error'] > 0 or gammes_stats['pending'] > 0 or gammes_stats.get('processing', 0) > 0
            
            try:
                if hasattr(self, 'start_btn'):
                    self.start_btn.configure(state="normal" if has_work else "disabled")
            except Exception:
                pass
            
            # Gérer l'état du bouton d'export CSV
            # Le bouton est activé si :
            # - Il y a des produits complétés ET (pas d'erreurs OU checkbox cochée)
            has_completed = products['completed'] > 0
            has_errors = products['error'] > 0 or variants['error'] > 0
            checkbox_checked = self.exclude_errors_var.get() if hasattr(self, 'exclude_errors_var') else False
            
            # Activer le bouton si : produits complétés ET (pas d'erreurs OU checkbox cochée)
            should_enable = has_completed and (not has_errors or checkbox_checked)
            
            try:
                if hasattr(self, 'export_csv_btn'):
                    self.export_csv_btn.configure(state="normal" if should_enable else "disabled")
            except Exception:
                pass
            
            # Mettre à jour le texte des checkboxes (dans l'ordre d'exécution) - Protégé
            try:
                if self.scraper.name.lower() == 'garnier' and gammes_stats:
                    logger.info(f"Stats gammes pour {self.current_category}: {gammes_stats}")
                    if hasattr(self, 'error_gammes_check'):
                        error_count = gammes_stats['error']
                        logger.info(f"Gammes en erreur: {error_count}")
                        self.error_gammes_check.configure(
                            text=f"0️⃣ Re-collecter les gammes en ERREUR ({error_count}) - Force une nouvelle collecte",
                            state="normal" if error_count > 0 else "disabled"
                        )
                        logger.info(f"Checkbox gammes erreur: état={'normal' if error_count > 0 else 'disabled'}")
            except Exception as e:
                logger.error(f"Erreur lors de la configuration de la checkbox gammes: {e}", exc_info=True)
            
            try:
                if hasattr(self, 'error_products_check'):
                    self.error_products_check.configure(
                        text=f"1️⃣ Re-collecter les produits en ERREUR ({products['error']}) - Force une nouvelle collecte",
                        state="normal" if products['error'] > 0 else "disabled"
                    )
            except Exception:
                pass
            
            try:
                if hasattr(self, 'pending_variants_check'):
                    self.pending_variants_check.configure(
                        text=f"2️⃣ Traiter les variants PENDING ({variants['pending']}) - Extrait nom, description, prix, images",
                        state="normal" if variants['pending'] > 0 else "disabled",
                        font=ctk.CTkFont(size=13, weight="bold") if variants['pending'] > 0 else ctk.CTkFont(size=13)
                    )
            except Exception:
                pass
            
            try:
                if hasattr(self, 'error_variants_check'):
                    self.error_variants_check.configure(
                        text=f"3️⃣ Re-traiter les variants en ERREUR ({variants['error']}) - Nouvelle tentative",
                        state="normal" if variants['error'] > 0 else "disabled"
                    )
            except Exception:
                pass
            
        except Exception as e:
            logger.error(f"Erreur lors du chargement des stats: {e}")
            # Ne PAS essayer de configurer le label ici, il peut être détruit
            try:
                if hasattr(self, 'stats_label'):
                    self.stats_label.configure(text=f"Erreur: {e}")
            except Exception:
                pass  # Ignorer silencieusement si le widget est détruit
    
    def _start_reprocessing(self):
        """Lance le retraitement selon les options sélectionnées."""
        if not self.current_category or not self.stats:
            return
        
        # Déterminer quelles actions sont nécessaires
        # IMPORTANT : Ordre d'exécution : Gammes → Produits → Variants erreur → Variants pending
        actions = []
        
        # 0. Re-collecter les gammes en erreur (si sélectionné et Garnier)
        if (self.scraper.name.lower() == 'garnier' and 
            hasattr(self, 'reprocess_error_gammes') and 
            self.reprocess_error_gammes.get()):
            # Récupérer les stats des gammes
            db_path = get_supplier_db_path(self.scraper.name.lower())
            db = self.db_class(db_path)
            if hasattr(db, 'get_category_gamme_stats'):
                gammes_stats = db.get_category_gamme_stats(self.current_category)
                db.close()
                if gammes_stats and gammes_stats['error'] > 0:
                    actions.append(('recollect_error_gammes', 'Re-collecte des gammes en erreur'))
            else:
                db.close()
        
        # 1. Re-collecter les produits en erreur (si sélectionné)
        if self.reprocess_error_products.get() and self.stats['products']['error'] > 0:
            actions.append(('recollect_error_products', 'Re-collecte des produits en erreur'))
        
        # 2. Traiter les variants pending (si sélectionné) - ACTION PRINCIPALE
        if self.reprocess_pending_variants.get() and self.stats['variants']['pending'] > 0:
            actions.append(('process_pending_variants', 'Traitement des variants pending'))
        
        # 3. Re-traiter les variants en erreur (si sélectionné)
        if self.reprocess_error_variants.get() and self.stats['variants']['error'] > 0:
            actions.append(('process_error_variants', 'Re-traitement des variants en erreur'))
        
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
                # Liste des actions initiales
                initial_actions = actions.copy()
                
                for action_type, action_label in initial_actions:
                    progress_window.add_log(f"\n{'='*50}")
                    progress_window.add_log(f"▶ {action_label}...")
                    progress_window.add_log(f"{'='*50}\n")
                    
                    if action_type == 'recollect_error_gammes':
                        self._recollect_gammes(progress_window, status='error')
                        
                        # Après avoir recollecté les gammes, vérifier s'il y a maintenant des variants pending à traiter
                        if self.reprocess_pending_variants.get():
                            # Recharger les stats pour voir combien de variants pending il y a maintenant
                            db_path = get_supplier_db_path(self.scraper.name.lower())
                            db = self.db_class(db_path)
                            fresh_stats = db.get_category_stats(self.current_category)
                            db.close()
                            
                            if fresh_stats['variants']['pending'] > 0:
                                # Ajouter l'action si elle n'est pas déjà dans la liste
                                if ('process_pending_variants', 'Traitement des variants pending') not in initial_actions:
                                    progress_window.add_log(f"\n💡 {fresh_stats['variants']['pending']} variant(s) pending détecté(s) après recollecte des gammes")
                                    progress_window.add_log("   → Ajout automatique du traitement des variants pending\n")
                                    
                                    # Exécuter immédiatement le traitement des variants pending
                                    progress_window.add_log(f"\n{'='*50}")
                                    progress_window.add_log(f"▶ Traitement des variants pending...")
                                    progress_window.add_log(f"{'='*50}\n")
                                    self._process_variants(progress_window, 'pending')
                        
                    elif action_type == 'process_error_variants':
                        self._process_variants(progress_window, 'error')
                    elif action_type == 'process_pending_variants':
                        self._process_variants(progress_window, 'pending')
                    elif action_type == 'recollect_error_products':
                        self._recollect_products(progress_window)
                        
                        # Après avoir recollecté les produits, même logique pour les variants
                        if self.reprocess_pending_variants.get():
                            db_path = get_supplier_db_path(self.scraper.name.lower())
                            db = self.db_class(db_path)
                            fresh_stats = db.get_category_stats(self.current_category)
                            db.close()
                            
                            if fresh_stats['variants']['pending'] > 0:
                                if ('process_pending_variants', 'Traitement des variants pending') not in initial_actions:
                                    progress_window.add_log(f"\n💡 {fresh_stats['variants']['pending']} variant(s) pending détecté(s) après recollecte des produits")
                                    progress_window.add_log("   → Ajout automatique du traitement des variants pending\n")
                                    
                                    progress_window.add_log(f"\n{'='*50}")
                                    progress_window.add_log(f"▶ Traitement des variants pending...")
                                    progress_window.add_log(f"{'='*50}\n")
                                    self._process_variants(progress_window, 'pending')
                
                progress_window.add_log("\n✅ Retraitement terminé avec succès !")
                progress_window.finish(success=True)
                
                # Actualiser les stats après un délai plus long
                progress_window.add_log("\n💡 Rafraîchissement des statistiques dans 2 secondes...")
                self.after(2000, self._load_stats)
                
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
    
    def _recollect_gammes(self, progress_window, status='error'):
        """Lance le script de re-collecte des gammes selon leur statut.
        
        Cette fonction effectue 2 étapes automatiquement :
        1. Recollecte les noms des gammes en erreur (les met en "pending")
        2. Collecte les produits et variants de ces gammes "pending"
        
        Args:
            progress_window: Fenêtre de progression
            status: 'error', 'processing' ou 'pending'
        """
        import subprocess
        import sys
        import os
        
        # Obtenir le répertoire du projet (où se trouve le script)
        project_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        supplier_dir = self.scraper.name.lower()
        
        # ÉTAPE 1: Recollecte les noms des gammes en erreur
        progress_window.add_log("=" * 50)
        progress_window.add_log("ÉTAPE 1/2 : Recollecte des noms de gammes")
        progress_window.add_log("=" * 50 + "\n")
        
        cmd1 = [
            sys.executable,
            os.path.join(supplier_dir, 'scraper-collect-gammes.py'),
            '--category', self.current_category,
            '--retry-errors-only'
        ]
        
        progress_window.add_log(f"Répertoire: {project_dir}")
        progress_window.add_log(f"Commande: {' '.join(cmd1)}\n")
        
        process = subprocess.Popen(
            cmd1,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1,
            universal_newlines=True,
            cwd=project_dir
        )
        
        for line in iter(process.stdout.readline, ''):
            if line:
                progress_window.add_log(line.rstrip())
        
        process.wait()
        
        if process.returncode != 0:
            progress_window.add_log(f"\n❌ Étape 1 échouée avec le code {process.returncode}")
            raise Exception(f"Le script a retourné le code d'erreur {process.returncode}")
        
        progress_window.add_log("\n✅ Étape 1 terminée : Noms de gammes recollectés\n")
        
        # ÉTAPE 2: Collecte les produits et variants des gammes qui viennent d'être recollectées
        progress_window.add_log("=" * 50)
        progress_window.add_log("ÉTAPE 2/2 : Collecte des produits et variants")
        progress_window.add_log("=" * 50 + "\n")
        
        # Récupérer les gammes en "pending" pour cette catégorie (celles qu'on vient de recollecter)
        db_path = get_supplier_db_path(self.scraper.name.lower())
        db = self.db_class(db_path)
        gammes_pending = db.get_gammes_by_status(status='pending', category=self.current_category)
        
        # IMPORTANT: Nettoyer les produits orphelins (sans variants) pour éviter les doublons
        if gammes_pending:
            progress_window.add_log("🧹 Nettoyage des produits orphelins avant recollecte...\n")
            cleaned_total = 0
            
            for gamme in gammes_pending:
                gamme_name = gamme.get('name', 'SANS NOM')
                
                # Supprimer uniquement les produits SANS variants (orphelins)
                cursor = db.conn.cursor()
                cursor.execute('''
                    SELECT p.id, p.title 
                    FROM products p 
                    LEFT JOIN product_variants pv ON p.id = pv.product_id 
                    WHERE p.gamme = ? AND pv.id IS NULL
                ''', (gamme_name,))
                orphans = cursor.fetchall()
                
                if orphans:
                    orphan_ids = [row[0] for row in orphans]
                    placeholders = ','.join('?' * len(orphan_ids))
                    cursor.execute(f'DELETE FROM products WHERE id IN ({placeholders})', orphan_ids)
                    db.conn.commit()
                    
                    progress_window.add_log(f"  • Gamme '{gamme_name}': {len(orphans)} produit(s) orphelin(s) supprimé(s)")
                    cleaned_total += len(orphans)
            
            if cleaned_total > 0:
                progress_window.add_log(f"\n  ✓ Total: {cleaned_total} produit(s) orphelin(s) nettoyé(s)\n")
            else:
                progress_window.add_log("  ✓ Aucun produit orphelin à nettoyer\n")
        
        db.close()
        
        if not gammes_pending:
            progress_window.add_log("⚠️ Aucune gamme en 'pending' trouvée pour collecter les produits")
            return
        
        progress_window.add_log(f"Gammes à traiter: {len(gammes_pending)}\n")
        
        # Pour chaque gamme en pending, collecter ses produits avec --gamme-url
        for idx, gamme in enumerate(gammes_pending, 1):
            gamme_url = gamme.get('url')
            gamme_name = gamme.get('name', 'SANS NOM')
            
            progress_window.add_log(f"\n[{idx}/{len(gammes_pending)}] Collecte de la gamme: {gamme_name}")
            progress_window.add_log(f"URL: {gamme_url}\n")
            
            cmd2 = [
                sys.executable,
                os.path.join(supplier_dir, 'scraper-collect.py'),
                '--gamme-url', gamme_url,
                '--category', self.current_category
            ]
            
            progress_window.add_log(f"Commande: {' '.join(cmd2)}\n")
            
            process = subprocess.Popen(
                cmd2,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1,
                universal_newlines=True,
                cwd=project_dir
            )
            
            for line in iter(process.stdout.readline, ''):
                if line:
                    progress_window.add_log(line.rstrip())
            
            process.wait()
            
            if process.returncode != 0:
                progress_window.add_log(f"\n⚠️ Erreur pour la gamme {gamme_name} (code {process.returncode})")
                # On continue avec les autres gammes même si une échoue
            else:
                progress_window.add_log(f"\n✓ Gamme {gamme_name} traitée avec succès")
        
        progress_window.add_log("\n" + "=" * 50)
        progress_window.add_log("✅ Étape 2 terminée : Produits et variants collectés")
        progress_window.add_log("💡 Vous pouvez maintenant cocher 'Traiter les variants PENDING' pour extraire leurs détails")
    
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
    
    def _on_exclude_errors_changed(self):
        """Appelé quand la checkbox d'exclusion des erreurs change."""
        # Recharger les stats pour mettre à jour l'état du bouton
        if self.current_category:
            self._load_stats()
    
    def _export_csv(self):
        """Exporte le CSV avec option de filtrer les erreurs."""
        if not self.current_category or not self.stats:
            return
        
        try:
            from tkinter import filedialog
            from datetime import datetime
            import os
            
            # Générer un nom de fichier par défaut
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            supplier_name = self.scraper.name.lower()
            category_slug = self.current_category.replace(" ", "_").replace("/", "_")
            default_filename = f"shopify_export_{supplier_name}_{category_slug}_{timestamp}.csv"
            
            # Demander où sauvegarder le fichier
            filename = filedialog.asksaveasfilename(
                title="Enregistrer le CSV",
                defaultextension=".csv",
                filetypes=[("Fichiers CSV", "*.csv"), ("Tous les fichiers", "*.*")],
                initialfile=default_filename
            )
            
            if not filename:
                return  # L'utilisateur a annulé
            
            # Ouvrir une fenêtre de progression pour l'export
            progress_window = ProgressWindow(
                self,
                title="Export CSV en cours"
            )
            
            # Lancer l'export dans un thread
            def run_export():
                try:
                    from apps.csv_generator.generator import CSVGenerator
                    
                    exclude_errors = self.exclude_errors_var.get()
                    
                    progress_window.add_log(f"Export CSV pour la catégorie: {self.current_category}")
                    progress_window.add_log(f"Exclure les erreurs: {'Oui' if exclude_errors else 'Non'}\n")
                    
                    generator = CSVGenerator()
                    
                    # Déterminer les paramètres selon le scraper
                    supplier = supplier_name
                    categories = [self.current_category]
                    
                    # Pour Garnier, on peut avoir besoin de la gamme
                    gamme = None
                    if supplier == 'garnier':
                        # Essayer de récupérer la gamme depuis les stats si disponible
                        # Pour l'instant, on laisse None pour exporter toutes les gammes de la catégorie
                        pass
                    
                    # Récupérer les champs par défaut depuis la config
                    from csv_config import get_csv_config
                    csv_config = get_csv_config()
                    selected_fields = csv_config.get_columns(supplier)
                    
                    # Générer le CSV avec le filtre d'erreurs
                    output_file = generator.generate_csv(
                        supplier=supplier,
                        categories=categories,
                        subcategories=None,
                        selected_fields=selected_fields,
                        handle_source='sku',  # Par défaut
                        vendor=supplier.title(),
                        gamme=gamme,
                        output_file=filename,
                        exclude_errors=exclude_errors  # Nouveau paramètre
                    )
                    
                    progress_window.add_log(f"\n✅ CSV exporté avec succès: {output_file}")
                    progress_window.finish(success=True)
                    
                except Exception as e:
                    import logging
                    logger.error(f"Erreur lors de l'export CSV: {e}", exc_info=True)
                    progress_window.add_log(f"\n❌ Erreur lors de l'export: {e}")
                    progress_window.finish(success=False, error=str(e))
            
            import threading
            thread = threading.Thread(target=run_export, daemon=True)
            thread.start()
            
        except Exception as e:
            import logging
            logger.error(f"Erreur lors de l'export CSV: {e}", exc_info=True)
            import tkinter.messagebox as messagebox
            messagebox.showerror("Erreur", f"Erreur lors de l'export CSV:\n{e}")
