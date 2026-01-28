"""
Fenêtre de visualisation des erreurs de scraping.
Affiche les gammes, produits et variants en erreur depuis les bases de données des scrapers.
"""

import customtkinter as ctk
import sys
import os
import logging
import webbrowser

# Ajouter le répertoire parent au path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.garnier_db import GarnierDB
from utils.artiga_db import ArtigaDB
from utils.cristel_db import CristelDB

logger = logging.getLogger(__name__)


class ErrorsViewerWindow(ctk.CTkToplevel):
    """Fenêtre de visualisation des erreurs de scraping."""
    
    def __init__(self, parent):
        super().__init__(parent)
        
        self.title("Visualisation des Erreurs de Scraping")
        self.geometry("1200x800")
        
        # Variables
        self.current_supplier = "garnier"
        self.db = None
        
        # Créer l'interface
        self.create_ui()
        
        # Charger les données initiales
        self.load_supplier_data()
    
    def create_ui(self):
        """Crée l'interface utilisateur."""
        # Frame principal
        main_frame = ctk.CTkFrame(self)
        main_frame.pack(fill="both", expand=True, padx=20, pady=20)
        
        # Titre
        title_label = ctk.CTkLabel(
            main_frame,
            text="🔍 Visualisation des Erreurs de Scraping",
            font=ctk.CTkFont(size=24, weight="bold")
        )
        title_label.pack(pady=(0, 20))
        
        # Frame de sélection du fournisseur
        supplier_frame = ctk.CTkFrame(main_frame)
        supplier_frame.pack(fill="x", pady=(0, 20))
        
        supplier_label = ctk.CTkLabel(
            supplier_frame,
            text="Fournisseur:",
            font=ctk.CTkFont(size=14, weight="bold")
        )
        supplier_label.pack(side="left", padx=20)
        
        self.supplier_var = ctk.StringVar(value="garnier")
        
        suppliers = [
            ("Garnier-Thiebaut", "garnier"),
            ("Artiga", "artiga"),
            ("Cristel", "cristel")
        ]
        
        for text, value in suppliers:
            radio = ctk.CTkRadioButton(
                supplier_frame,
                text=text,
                variable=self.supplier_var,
                value=value,
                command=self.on_supplier_changed,
                font=ctk.CTkFont(size=13)
            )
            radio.pack(side="left", padx=10)
        
        # Frame de statistiques
        self.stats_frame = ctk.CTkFrame(main_frame)
        self.stats_frame.pack(fill="x", pady=(0, 20))
        
        stats_title = ctk.CTkLabel(
            self.stats_frame,
            text="📊 Statistiques",
            font=ctk.CTkFont(size=16, weight="bold")
        )
        stats_title.pack(anchor="w", padx=20, pady=(10, 5))
        
        self.stats_content = ctk.CTkFrame(self.stats_frame)
        self.stats_content.pack(fill="x", padx=20, pady=(0, 10))
        
        # Boutons d'action
        actions_frame = ctk.CTkFrame(main_frame)
        actions_frame.pack(fill="x", pady=(0, 10))
        
        refresh_btn = ctk.CTkButton(
            actions_frame,
            text="🔄 Rafraîchir",
            command=self.load_supplier_data,
            width=150
        )
        refresh_btn.pack(side="left", padx=20)
        
        copy_btn = ctk.CTkButton(
            actions_frame,
            text="📋 Copier tout",
            command=self.copy_current_tab,
            width=150
        )
        copy_btn.pack(side="left", padx=10)
        
        # TabView pour les différents types d'erreurs
        self.tabview = ctk.CTkTabview(main_frame)
        self.tabview.pack(fill="both", expand=True)
        
        # Créer les onglets (gammes seulement pour Garnier - créé par défaut car Garnier est le fournisseur initial)
        self.tab_gammes = self.tabview.add("Gammes")
        self.tab_products = self.tabview.add("Produits")
        self.tab_variants = self.tabview.add("Variants")
        
        # TextBox pour chaque onglet (sélectionnable)
        self.gammes_textbox = ctk.CTkTextbox(
            self.tab_gammes,
            wrap="word",
            font=ctk.CTkFont(family="Courier", size=12)
        )
        self.gammes_textbox.pack(fill="both", expand=True, padx=10, pady=10)
        self._setup_url_tags(self.gammes_textbox)
        
        self.products_textbox = ctk.CTkTextbox(
            self.tab_products,
            wrap="word",
            font=ctk.CTkFont(family="Courier", size=12)
        )
        self.products_textbox.pack(fill="both", expand=True, padx=10, pady=10)
        self._setup_url_tags(self.products_textbox)
        
        self.variants_textbox = ctk.CTkTextbox(
            self.tab_variants,
            wrap="word",
            font=ctk.CTkFont(family="Courier", size=12)
        )
        self.variants_textbox.pack(fill="both", expand=True, padx=10, pady=10)
        self._setup_url_tags(self.variants_textbox)
    
    def _setup_url_tags(self, textbox):
        """Configure les tags pour rendre les URLs cliquables."""
        # Tag pour les URLs
        textbox.tag_config("url", foreground="#3498db", underline=True)
        textbox.tag_bind("url", "<Button-1>", self._open_url)
        textbox.tag_bind("url", "<Enter>", lambda e: textbox.configure(cursor="hand2"))
        textbox.tag_bind("url", "<Leave>", lambda e: textbox.configure(cursor="xterm"))
    
    def _open_url(self, event):
        """Ouvre l'URL cliquée dans le navigateur."""
        textbox = event.widget
        # Récupérer l'URL sous le curseur
        index = textbox.index(f"@{event.x},{event.y}")
        # Récupérer tous les tags à cet index
        tags = textbox.tag_names(index)
        if "url" in tags:
            # Trouver le début et la fin de l'URL
            range_start = textbox.tag_prevrange("url", index + "+1c")
            if range_start:
                url = textbox.get(*range_start).strip()
                webbrowser.open(url)
                logger.info(f"Ouverture de l'URL: {url}")
    
    def _insert_with_url(self, textbox, text, url=None):
        """Insère du texte avec une URL cliquable si fournie."""
        if url:
            # Insérer le label
            textbox.insert("end", text)
            # Insérer l'URL avec le tag
            start_index = textbox.index("end-1c")
            textbox.insert("end", url)
            end_index = textbox.index("end-1c")
            textbox.tag_add("url", start_index, end_index)
            textbox.insert("end", "\n")
        else:
            textbox.insert("end", text)
    
    def on_supplier_changed(self):
        """Appelé quand le fournisseur change."""
        new_supplier = self.supplier_var.get()
        
        # Si on passe de Garnier à autre chose, retirer l'onglet gammes
        if self.current_supplier == "garnier" and new_supplier != "garnier":
            if self.tab_gammes:
                self.tabview.delete("Gammes")
                self.tab_gammes = None
        
        # Si on passe à Garnier, ajouter l'onglet gammes
        if self.current_supplier != "garnier" and new_supplier == "garnier":
            self.tab_gammes = self.tabview.insert(0, "Gammes")
            self.gammes_textbox = ctk.CTkTextbox(
                self.tab_gammes,
                wrap="word",
                font=ctk.CTkFont(family="Courier", size=12)
            )
            self.gammes_textbox.pack(fill="both", expand=True, padx=10, pady=10)
        
        self.current_supplier = new_supplier
        self.load_supplier_data()
    
    def load_supplier_data(self):
        """Charge les données du fournisseur sélectionné."""
        try:
            # Fermer la connexion précédente
            if self.db:
                self.db.close()
            
            # Ouvrir la nouvelle connexion
            supplier = self.supplier_var.get()
            
            if supplier == "garnier":
                self.db = GarnierDB("database/garnier_products.db")
                self.load_garnier_errors()
            elif supplier == "artiga":
                self.db = ArtigaDB("database/artiga_products.db")
                self.load_artiga_errors()
            elif supplier == "cristel":
                self.db = CristelDB("database/cristel_products.db")
                self.load_cristel_errors()
            
        except Exception as e:
            logger.error(f"Erreur lors du chargement des données: {e}", exc_info=True)
            self.show_error(f"Erreur: {e}")
    
    def load_garnier_errors(self):
        """Charge les erreurs pour Garnier."""
        cursor = self.db.conn.cursor()
        
        # Statistiques
        cursor.execute("SELECT COUNT(*) FROM gammes WHERE status IN ('error', 'partial')")
        gammes_count = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM products WHERE status = 'error'")
        products_count = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM product_variants WHERE status = 'error'")
        variants_count = cursor.fetchone()[0]
        
        self.update_stats(gammes_count, products_count, variants_count)
        
        # Gammes en erreur
        if self.tab_gammes:
            cursor.execute('''
                SELECT name, url, status, category,
                       CASE 
                           WHEN name IS NULL OR name = '' THEN 'Nom de gamme non trouvé'
                           ELSE NULL
                       END as error_reason
                FROM gammes 
                WHERE status IN ('error', 'partial') OR name IS NULL OR name = ''
                ORDER BY category, name
            ''')
            gammes = cursor.fetchall()
            self.display_gammes(gammes)
        
        # Produits en erreur
        cursor.execute('''
            SELECT title, base_url, status, error_message, gamme 
            FROM products 
            WHERE status = 'error'
            ORDER BY title
        ''')
        products = cursor.fetchall()
        self.display_products(products, has_gamme=True)
        
        # Variants en erreur
        cursor.execute('''
            SELECT pv.code_vl, pv.url, pv.status, pv.error_message, p.title as product_title
            FROM product_variants pv
            JOIN products p ON pv.product_id = p.id
            WHERE pv.status = 'error'
            ORDER BY p.title, pv.code_vl
        ''')
        variants = cursor.fetchall()
        self.display_variants(variants)
    
    def load_artiga_errors(self):
        """Charge les erreurs pour Artiga."""
        cursor = self.db.conn.cursor()
        
        # Statistiques
        cursor.execute("SELECT COUNT(*) FROM products WHERE status = 'error'")
        products_count = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM product_variants WHERE status = 'error'")
        variants_count = cursor.fetchone()[0]
        
        self.update_stats(0, products_count, variants_count)
        
        # Produits en erreur
        cursor.execute('''
            SELECT title, base_url, status, error_message, category, subcategory
            FROM products 
            WHERE status = 'error'
            ORDER BY title
        ''')
        products = cursor.fetchall()
        self.display_products(products, has_gamme=False, has_category=True)
        
        # Variants en erreur
        cursor.execute('''
            SELECT pv.code_vl, pv.url, pv.status, pv.error_message, p.title as product_title
            FROM product_variants pv
            JOIN products p ON pv.product_id = p.id
            WHERE pv.status = 'error'
            ORDER BY p.title, pv.code_vl
        ''')
        variants = cursor.fetchall()
        self.display_variants(variants)
    
    def load_cristel_errors(self):
        """Charge les erreurs pour Cristel."""
        cursor = self.db.conn.cursor()
        
        # Statistiques
        cursor.execute("SELECT COUNT(*) FROM products WHERE status = 'error'")
        products_count = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM product_variants WHERE status = 'error'")
        variants_count = cursor.fetchone()[0]
        
        self.update_stats(0, products_count, variants_count)
        
        # Produits en erreur
        cursor.execute('''
            SELECT title, base_url, status, error_message, category, subcategory
            FROM products 
            WHERE status = 'error'
            ORDER BY title
        ''')
        products = cursor.fetchall()
        self.display_products(products, has_gamme=False, has_category=True)
        
        # Variants en erreur
        cursor.execute('''
            SELECT pv.code_vl, pv.url, pv.status, pv.error_message, p.title as product_title
            FROM product_variants pv
            JOIN products p ON pv.product_id = p.id
            WHERE pv.status = 'error'
            ORDER BY p.title, pv.code_vl
        ''')
        variants = cursor.fetchall()
        self.display_variants(variants)
    
    def update_stats(self, gammes_count, products_count, variants_count):
        """Met à jour l'affichage des statistiques."""
        # Nettoyer
        for widget in self.stats_content.winfo_children():
            widget.destroy()
        
        # Afficher
        stats_text = []
        if self.current_supplier == "garnier":
            stats_text.append(f"❌ Gammes en erreur: {gammes_count}")
        stats_text.append(f"❌ Produits en erreur: {products_count}")
        stats_text.append(f"❌ Variants en erreur: {variants_count}")
        
        for i, text in enumerate(stats_text):
            label = ctk.CTkLabel(
                self.stats_content,
                text=text,
                font=ctk.CTkFont(size=14),
                text_color="red"
            )
            label.grid(row=0, column=i, padx=20, pady=10)
    
    def display_gammes(self, gammes):
        """Affiche les gammes en erreur."""
        if not hasattr(self, 'gammes_textbox'):
            return
        
        self.gammes_textbox.delete("1.0", "end")
        
        if not gammes:
            self.gammes_textbox.insert("end", "✅ Aucune gamme en erreur\n")
            return
        
        self.gammes_textbox.insert("end", f"Total: {len(gammes)} gamme(s) en erreur\n\n")
        
        for name, url, status, category, error_reason in gammes:
            self.gammes_textbox.insert("end", "━" * 100 + "\n")
            self.gammes_textbox.insert("end", f"GAMME: {name if name else '❌ (nom non trouvé)'}\n")
            self._insert_with_url(self.gammes_textbox, "URL: ", url)
            self.gammes_textbox.insert("end", f"Catégorie: {category}\n")
            self.gammes_textbox.insert("end", f"Status: {status}\n")
            if error_reason:
                self.gammes_textbox.insert("end", f"Raison: {error_reason}\n")
            self.gammes_textbox.insert("end", "\n")
    
    def display_products(self, products, has_gamme=False, has_category=False):
        """Affiche les produits en erreur."""
        self.products_textbox.delete("1.0", "end")
        
        if not products:
            self.products_textbox.insert("end", "✅ Aucun produit en erreur\n")
            return
        
        self.products_textbox.insert("end", f"Total: {len(products)} produit(s) en erreur\n\n")
        
        for row in products:
            if has_gamme:
                title, base_url, status, error_message, gamme = row
            elif has_category:
                title, base_url, status, error_message, category, subcategory = row
            else:
                title, base_url, status, error_message = row[:4]
            
            self.products_textbox.insert("end", "━" * 100 + "\n")
            self.products_textbox.insert("end", f"PRODUIT: {title or '(sans titre)'}\n")
            self._insert_with_url(self.products_textbox, "URL: ", base_url)
            self.products_textbox.insert("end", f"Status: {status}\n")
            
            if error_message:
                self.products_textbox.insert("end", f"Erreur: {error_message}\n")
            
            if has_gamme and gamme:
                self.products_textbox.insert("end", f"Gamme: {gamme}\n")
            elif has_category:
                if category:
                    self.products_textbox.insert("end", f"Catégorie: {category}\n")
                if subcategory:
                    self.products_textbox.insert("end", f"Sous-catégorie: {subcategory}\n")
            
            self.products_textbox.insert("end", "\n")
    
    def display_variants(self, variants):
        """Affiche les variants en erreur."""
        self.variants_textbox.delete("1.0", "end")
        
        if not variants:
            self.variants_textbox.insert("end", "✅ Aucun variant en erreur\n")
            return
        
        self.variants_textbox.insert("end", f"Total: {len(variants)} variant(s) en erreur\n\n")
        
        for code_vl, url, status, error_message, product_title in variants:
            self.variants_textbox.insert("end", "━" * 100 + "\n")
            self.variants_textbox.insert("end", f"VARIANT: {code_vl}\n")
            self.variants_textbox.insert("end", f"Produit: {product_title or '(sans titre)'}\n")
            self._insert_with_url(self.variants_textbox, "URL: ", url)
            self.variants_textbox.insert("end", f"Status: {status}\n")
            
            if error_message:
                self.variants_textbox.insert("end", f"Erreur: {error_message}\n")
            
            self.variants_textbox.insert("end", "\n")
    
    def copy_current_tab(self):
        """Copie le contenu de l'onglet actuel dans le presse-papier."""
        current_tab = self.tabview.get()
        
        text = ""
        if current_tab == "Gammes" and hasattr(self, 'gammes_textbox'):
            text = self.gammes_textbox.get("1.0", "end-1c")
        elif current_tab == "Produits":
            text = self.products_textbox.get("1.0", "end-1c")
        elif current_tab == "Variants":
            text = self.variants_textbox.get("1.0", "end-1c")
        
        if text:
            self.clipboard_clear()
            self.clipboard_append(text)
            logger.info(f"Contenu de l'onglet '{current_tab}' copié dans le presse-papier")
    
    def show_error(self, message):
        """Affiche un message d'erreur."""
        for widget in self.stats_content.winfo_children():
            widget.destroy()
        
        error_label = ctk.CTkLabel(
            self.stats_content,
            text=f"❌ {message}",
            font=ctk.CTkFont(size=14),
            text_color="red"
        )
        error_label.pack(pady=20)
    
    def destroy(self):
        """Ferme la fenêtre et nettoie les ressources."""
        if self.db:
            self.db.close()
        super().destroy()
