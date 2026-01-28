"""
Fenêtre de gestion de la taxonomie Google Shopping.
Permet de rechercher, visualiser et modifier les catégorisations.
Structure inspirée de l'onglet Test (apps/ai_editor/gui/window.py).
"""

import customtkinter as ctk
import logging
from apps.ai_editor.db import AIPromptsDB

logger = logging.getLogger(__name__)


class TaxonomyWindow(ctk.CTkFrame):
    """Fenêtre de gestion de la taxonomie."""
    
    def __init__(self, parent):
        super().__init__(parent)
        self.db = AIPromptsDB()
        
        self.setup_ui()
    
    def setup_ui(self):
        """Configure l'interface utilisateur."""
        
        # Titre principal
        title = ctk.CTkLabel(
            self,
            text="📊 Gestion de la Taxonomie Google Shopping",
            font=ctk.CTkFont(size=24, weight="bold")
        )
        title.pack(pady=(20, 10))
        
        # Créer directement l'onglet Règles (plus besoin d'onglets)
        self.create_rules_tab()
    
    def _force_uppercase_type(self, event=None):
        """Convertit automatiquement le texte du champ de type en majuscules."""
        widget = event.widget if event else None
        if widget:
            current_pos = widget.index("insert")
            current_text = widget.get()
            uppercase_text = current_text.upper()
            if current_text != uppercase_text:
                widget.delete(0, "end")
                widget.insert(0, uppercase_text)
                # Restaurer la position du curseur
                widget.icursor(min(current_pos, len(uppercase_text)))
    
    # ========== GESTION DES RÈGLES TYPES ==========
    
    def create_rules_tab(self):
        """Crée l'interface de gestion des règles Type → Catégorie."""
        
        # Frame scrollable
        rules_scroll = ctk.CTkScrollableFrame(self)
        rules_scroll.pack(fill="both", expand=True, padx=10, pady=10)
        
        # ===== SECTION RÈGLES ACTIVES =====
        rules_frame = ctk.CTkFrame(rules_scroll)
        rules_frame.pack(fill="both", expand=True, padx=20, pady=(0, 20))
        
        # En-tête avec titre et filtre
        header_frame = ctk.CTkFrame(rules_frame)
        header_frame.pack(fill="x", padx=20, pady=(10, 5))
        
        rules_title = ctk.CTkLabel(
            header_frame,
            text="📋 Règles Actives",
            font=ctk.CTkFont(size=14, weight="bold")
        )
        rules_title.pack(side="left", padx=(0, 20))
        
        # Filtre par coefficient de confiance
        filter_frame = ctk.CTkFrame(header_frame)
        filter_frame.pack(side="right", padx=10)
        
        filter_label = ctk.CTkLabel(
            filter_frame,
            text="Filtrer par confidence <",
            font=ctk.CTkFont(size=11)
        )
        filter_label.pack(side="left", padx=(0, 5))
        
        # Dropdown pour le coefficient (0 à 100 avec écart de 10)
        self.confidence_filter_var = ctk.StringVar(value="100")
        confidence_values = [str(i) for i in range(0, 101, 10)]  # 0, 10, 20, ..., 100
        self.confidence_filter_dropdown = ctk.CTkComboBox(
            filter_frame,
            values=confidence_values,
            variable=self.confidence_filter_var,
            command=self.on_confidence_filter_changed,
            width=80
        )
        self.confidence_filter_dropdown.pack(side="left", padx=5)
        
        percent_label = ctk.CTkLabel(
            filter_frame,
            text="%",
            font=ctk.CTkFont(size=11)
        )
        percent_label.pack(side="left", padx=(5, 0))
        
        # Liste des règles
        self.rules_list_frame = ctk.CTkScrollableFrame(rules_frame, height=300)
        self.rules_list_frame.pack(fill="both", expand=True, padx=20, pady=(10, 15))
        
        # Boutons d'action
        button_frame = ctk.CTkFrame(rules_frame)
        button_frame.pack(fill="x", padx=20, pady=(0, 15))
        
        self.add_rule_button = ctk.CTkButton(
            button_frame,
            text="➕ Ajouter une Règle",
            command=self.add_new_rule,
            width=200,
            height=40
        )
        self.add_rule_button.pack(side="left", padx=(0, 10))
        
        self.refresh_rules_button = ctk.CTkButton(
            button_frame,
            text="🔄 Rafraîchir",
            command=self.refresh_rules,
            width=150,
            height=40
        )
        self.refresh_rules_button.pack(side="left", padx=10)
        
        # Label de statut pour les règles
        self.rules_status_label = ctk.CTkLabel(
            rules_frame,
            text="",
            font=ctk.CTkFont(size=12)
        )
        self.rules_status_label.pack(padx=20, pady=(10, 15))
        
        # Charger les règles existantes
        self.refresh_rules()
    
    def refresh_rules(self):
        """Rafraîchit la liste des règles."""
        try:
            # Effacer les anciennes règles
            for widget in self.rules_list_frame.winfo_children():
                widget.destroy()
            
            # Récupérer toutes les règles
            all_rules = self.db.get_all_type_mappings()
            
            if not all_rules:
                no_rules_label = ctk.CTkLabel(
                    self.rules_list_frame,
                    text="Aucune règle définie. Les règles seront créées automatiquement lors du traitement ou cliquez sur 'Ajouter une Règle'",
                    text_color="gray"
                )
                no_rules_label.pack(pady=20)
                return
            
            # Appliquer le filtre de confidence si défini
            filtered_rules = all_rules
            if hasattr(self, 'confidence_filter_var'):
                try:
                    confidence_threshold_percent = float(self.confidence_filter_var.get())
                    confidence_threshold = confidence_threshold_percent / 100.0  # Convertir en 0.0-1.0
                    # Filtrer les règles avec confidence < seuil
                    filtered_rules = [
                        rule for rule in all_rules 
                        if rule.get('confidence', 1.0) < confidence_threshold
                    ]
                except (ValueError, AttributeError):
                    # Si erreur, afficher toutes les règles
                    filtered_rules = all_rules
            
            if not filtered_rules:
                no_rules_label = ctk.CTkLabel(
                    self.rules_list_frame,
                    text=f"Aucune règle avec confidence < {self.confidence_filter_var.get()}%",
                    text_color="gray"
                )
                no_rules_label.pack(pady=20)
                self.rules_status_label.configure(
                    text=f"📊 {len(filtered_rules)}/{len(all_rules)} règle(s) affichée(s)",
                    text_color="orange"
                )
                return
            
            # Afficher chaque règle filtrée
            for rule in filtered_rules:
                self.create_rule_card(rule)
            
            self.rules_status_label.configure(
                text=f"📊 {len(filtered_rules)}/{len(all_rules)} règle(s) affichée(s)",
                text_color="green" if len(filtered_rules) == len(all_rules) else "orange"
            )
            
        except Exception as e:
            logger.error(f"Erreur lors du rafraîchissement: {e}", exc_info=True)
            self.rules_status_label.configure(
                text=f"❌ Erreur: {e}",
                text_color="red"
            )
    
    def on_confidence_filter_changed(self, value=None):
        """Appelé quand le filtre de confidence change."""
        self.refresh_rules()
    
    def create_rule_card(self, rule):
        """Crée une carte pour afficher une règle."""
        card = ctk.CTkFrame(self.rules_list_frame)
        card.pack(fill="x", pady=5, padx=10)
        
        # Info de la règle
        info_frame = ctk.CTkFrame(card)
        info_frame.pack(fill="x", padx=10, pady=10)
        
        # Afficher csv_type (principal) et product_type (informatif)
        csv_type = rule.get('csv_type', 'N/A')
        product_type = rule.get('product_type', '')
        
        type_label = ctk.CTkLabel(
            info_frame,
            text=f"Type: {csv_type}",
            font=ctk.CTkFont(size=13, weight="bold")
        )
        type_label.pack(anchor="w", padx=10, pady=2)
        
        # Product type informatif (grisé)
        if product_type:
            product_type_label = ctk.CTkLabel(
                info_frame,
                text=f"(Type original: {product_type})",
                font=ctk.CTkFont(size=9),
                text_color="gray"
            )
            product_type_label.pack(anchor="w", padx=10, pady=0)
        
        category_label = ctk.CTkLabel(
            info_frame,
            text=f"→ {rule['category_path']}",
            font=ctk.CTkFont(size=11),
            wraplength=600,
            anchor="w"
        )
        category_label.pack(anchor="w", padx=10, pady=2)
        
        code_label = ctk.CTkLabel(
            info_frame,
            text=f"Code: {rule['category_code']} | Confidence: {rule['confidence']:.0%}",
            font=ctk.CTkFont(size=10),
            text_color="gray",
            anchor="w"
        )
        code_label.pack(anchor="w", padx=10, pady=2)
        
        stats_label = ctk.CTkLabel(
            info_frame,
            text=f"📊 Utilisé {rule['use_count']} fois | Créé: {rule['created_by']} | Actif: {'Oui' if rule['is_active'] else 'Non'}",
            font=ctk.CTkFont(size=10),
            text_color="gray",
            anchor="w"
        )
        stats_label.pack(anchor="w", padx=10, pady=2)
        
        # Boutons d'action
        button_frame = ctk.CTkFrame(card)
        button_frame.pack(fill="x", padx=10, pady=(0, 10))
        
        # Bouton Modifier (capturer rule_id pour éviter le late binding)
        rule_id = rule['id']
        csv_type_display = rule.get('csv_type', 'N/A')
        logger.debug(f"Création bouton Modifier pour règle ID={rule_id}, Type={csv_type_display}")
        
        edit_btn = ctk.CTkButton(
            button_frame,
            text="✏️ Modifier",
            command=lambda rid=rule_id: self.edit_rule_by_id(rid),
            width=120,
            height=30,
            fg_color="orange",
            hover_color="darkorange"
        )
        edit_btn.pack(side="left", padx=10)
        
        # Bouton Activer/Désactiver (capturer les valeurs au lieu de la variable)
        toggle_text = "❌ Désactiver" if rule['is_active'] else "✅ Activer"
        rule_id = rule['id']
        is_active = rule['is_active']
        toggle_btn = ctk.CTkButton(
            button_frame,
            text=toggle_text,
            command=lambda rid=rule_id, active=is_active: self.toggle_rule(rid, not active),
            width=120,
            height=30
        )
        toggle_btn.pack(side="left", padx=10)
        
        # Bouton Supprimer (capturer l'ID au lieu de la variable rule)
        delete_btn = ctk.CTkButton(
            button_frame,
            text="🗑️ Supprimer",
            command=lambda rid=rule_id: self.delete_rule(rid),
            width=120,
            height=30,
            fg_color="red",
            hover_color="darkred"
        )
        delete_btn.pack(side="left", padx=10)
    
    def add_new_rule(self):
        """Ouvre un formulaire pour ajouter une nouvelle règle."""
        # Effacer les anciens widgets du formulaire si existant
        if hasattr(self, 'add_rule_form') and self.add_rule_form.winfo_exists():
            self.add_rule_form.destroy()
        
        # Créer le formulaire dans rules_scroll
        self.add_rule_form = ctk.CTkFrame(self.rules_list_frame)
        self.add_rule_form.pack(fill="x", pady=10, padx=10)
        
        form_title = ctk.CTkLabel(
            self.add_rule_form,
            text="➕ Nouvelle Règle",
            font=ctk.CTkFont(size=13, weight="bold")
        )
        form_title.pack(anchor="w", padx=20, pady=(10, 10))
        
        # Champ Type
        type_frame = ctk.CTkFrame(self.add_rule_form)
        type_frame.pack(fill="x", padx=20, pady=5)
        
        ctk.CTkLabel(type_frame, text="Type de produit:", width=150).pack(side="left", padx=10)
        self.new_rule_type_entry = ctk.CTkEntry(type_frame, width=300, placeholder_text="Ex: NAPPES, SERVIETTES")
        self.new_rule_type_entry.pack(side="left", padx=10)
        self.new_rule_type_entry.bind("<KeyRelease>", self._force_uppercase_type)
        
        # Champ Code
        code_frame = ctk.CTkFrame(self.add_rule_form)
        code_frame.pack(fill="x", padx=20, pady=5)
        
        ctk.CTkLabel(code_frame, text="Code Google:", width=150).pack(side="left", padx=10)
        self.new_rule_code_entry = ctk.CTkEntry(code_frame, width=150, placeholder_text="Ex: 4143")
        self.new_rule_code_entry.pack(side="left", padx=10)
        self.new_rule_code_entry.bind("<KeyRelease>", self.validate_new_rule_code)
        
        # Label de validation
        self.new_rule_validation = ctk.CTkLabel(
            code_frame,
            text="",
            font=ctk.CTkFont(size=11),
            wraplength=400,
            anchor="w"
        )
        self.new_rule_validation.pack(side="left", padx=10)
        
        # Boutons
        action_frame = ctk.CTkFrame(self.add_rule_form)
        action_frame.pack(fill="x", padx=20, pady=(10, 15))
        
        save_btn = ctk.CTkButton(
            action_frame,
            text="💾 Créer Règle",
            command=self.save_new_rule,
            width=150,
            height=35,
            fg_color="green",
            hover_color="darkgreen"
        )
        save_btn.pack(side="left", padx=10)
        
        cancel_btn = ctk.CTkButton(
            action_frame,
            text="❌ Annuler",
            command=self.add_rule_form.destroy,
            width=100,
            height=35,
            fg_color="gray"
        )
        cancel_btn.pack(side="left", padx=10)
    
    def validate_new_rule_code(self, event=None):
        """Valide le code Google Shopping en temps réel."""
        code = self.new_rule_code_entry.get().strip()
        
        if not code:
            self.new_rule_validation.configure(text="")
            return
        
        try:
            cursor = self.db.conn.cursor()
            cursor.execute('SELECT path FROM google_taxonomy WHERE code = ?', (code,))
            result = cursor.fetchone()
            
            if result:
                self.new_rule_validation.configure(
                    text=f"✅ {result['path'][:50]}...",
                    text_color="green"
                )
            else:
                self.new_rule_validation.configure(
                    text="❌ Code non trouvé",
                    text_color="red"
                )
        except Exception as e:
            self.new_rule_validation.configure(
                text=f"❌ Erreur: {e}",
                text_color="red"
            )
    
    def save_new_rule(self):
        """Sauvegarde la nouvelle règle."""
        product_type = self.new_rule_type_entry.get().strip()
        code = self.new_rule_code_entry.get().strip()
        
        if not product_type:
            self.rules_status_label.configure(
                text="❌ Le type ne peut pas être vide",
                text_color="red"
            )
            return
        
        if not code:
            self.rules_status_label.configure(
                text="❌ Le code ne peut pas être vide",
                text_color="red"
            )
            return
        
        try:
            # Vérifier que le code existe
            cursor = self.db.conn.cursor()
            cursor.execute('SELECT path FROM google_taxonomy WHERE code = ?', (code,))
            result = cursor.fetchone()
            
            if not result:
                self.rules_status_label.configure(
                    text="❌ Code non trouvé dans la taxonomie",
                    text_color="red"
                )
                return
            
            # Créer la règle (csv_type = product_type par défaut pour nouvelles règles manuelles)
            csv_type = product_type  # Par défaut, csv_type = product_type pour nouvelles règles
            success = self.db.save_type_mapping(
                product_type,
                csv_type,
                code,
                result['path'],
                confidence=1.0,
                created_by='manual',
                force_update=True  # Modifications manuelles via UI
            )
            
            if success:
                self.rules_status_label.configure(
                    text=f"✅ Règle créée: {product_type} → {code}",
                    text_color="green"
                )
                self.add_rule_form.destroy()
                self.refresh_rules()
            else:
                self.rules_status_label.configure(
                    text="❌ Échec création règle",
                    text_color="red"
                )
                
        except Exception as e:
            logger.error(f"Erreur lors de la création: {e}", exc_info=True)
            self.rules_status_label.configure(
                text=f"❌ Erreur: {e}",
                text_color="red"
            )
    
    def edit_rule_by_id(self, rule_id):
        """Récupère la règle par son ID et ouvre le formulaire d'édition."""
        try:
            logger.info(f"🔍 Ouverture formulaire édition pour règle ID: {rule_id}")
            cursor = self.db.conn.cursor()
            cursor.execute('SELECT * FROM type_category_mapping WHERE id = ?', (rule_id,))
            rule = cursor.fetchone()
            
            if rule:
                rule_dict = dict(rule)
                logger.info(f"✏️ Règle trouvée: ID={rule_dict['id']}, Type={rule_dict.get('csv_type', 'N/A')}, Code={rule_dict.get('category_code', 'N/A')}")
                self.edit_rule(rule_dict)
            else:
                logger.error(f"❌ Règle {rule_id} non trouvée")
        except Exception as e:
            logger.error(f"❌ Erreur lors de la récupération de la règle: {e}", exc_info=True)
    
    def edit_rule(self, rule):
        """Ouvre une fenêtre popup pour modifier une règle existante."""
        # Créer une fenêtre popup
        edit_window = ctk.CTkToplevel(self)
        edit_window.title(f"Modifier la Règle: {rule.get('csv_type', rule['product_type'])}")
        
        # Taille de la fenêtre
        window_width = 800
        window_height = 450
        
        # Centrer la fenêtre sur l'écran
        screen_width = edit_window.winfo_screenwidth()
        screen_height = edit_window.winfo_screenheight()
        center_x = int(screen_width/2 - window_width/2)
        center_y = int(screen_height/2 - window_height/2)
        edit_window.geometry(f'{window_width}x{window_height}+{center_x}+{center_y}')
        
        # Forcer la fenêtre au premier plan
        edit_window.lift()
        edit_window.focus_force()
        edit_window.attributes('-topmost', True)
        edit_window.after(100, lambda: edit_window.attributes('-topmost', False))
        
        # Frame principal
        main_frame = ctk.CTkFrame(edit_window)
        main_frame.pack(fill="both", expand=True, padx=20, pady=20)
        
        form_title = ctk.CTkLabel(
            main_frame,
            text=f"✏️ Modifier la Règle",
            font=ctk.CTkFont(size=18, weight="bold")
        )
        form_title.pack(pady=(0, 20))
        
        # Champ CSV Type (modifiable)
        type_frame = ctk.CTkFrame(main_frame)
        type_frame.pack(fill="x", pady=10)
        
        ctk.CTkLabel(type_frame, text="Type:", width=150).pack(side="left", padx=10)
        self.edit_rule_type_entry = ctk.CTkEntry(type_frame, width=200, placeholder_text="Ex: TORCHONS")
        self.edit_rule_type_entry.pack(side="left", padx=10)
        self.edit_rule_type_entry.insert(0, rule.get('csv_type', rule['product_type']))
        self.edit_rule_type_entry.bind("<KeyRelease>", self._force_uppercase_type)
        
        # Info sur product_type original
        if rule.get('product_type'):
            ctk.CTkLabel(
                type_frame,
                text=f"(Type original: {rule['product_type']})",
                font=ctk.CTkFont(size=9),
                text_color="gray"
            ).pack(side="left", padx=10)
        
        # Champ Code (modifiable)
        code_frame = ctk.CTkFrame(main_frame)
        code_frame.pack(fill="x", pady=10)
        
        code_input_frame = ctk.CTkFrame(code_frame)
        code_input_frame.pack(fill="x")
        
        ctk.CTkLabel(code_input_frame, text="Code Google:", width=150).pack(side="left", padx=10)
        self.edit_rule_code_entry = ctk.CTkEntry(code_input_frame, width=150)
        self.edit_rule_code_entry.pack(side="left", padx=10)
        self.edit_rule_code_entry.insert(0, rule['category_code'])
        self.edit_rule_code_entry.bind("<KeyRelease>", self.validate_edit_rule_code)
        
        # Label de validation (chemin complet sous le code)
        validation_frame = ctk.CTkFrame(code_frame)
        validation_frame.pack(fill="x", padx=(170, 10), pady=(5, 0))
        
        self.edit_rule_validation = ctk.CTkLabel(
            validation_frame,
            text=f"✅ {rule['category_path']}",
            font=ctk.CTkFont(size=11),
            text_color="green",
            anchor="w",
            justify="left"
        )
        self.edit_rule_validation.pack(fill="x")
        
        # Champ Confidence (modifiable)
        confidence_frame = ctk.CTkFrame(main_frame)
        confidence_frame.pack(fill="x", pady=10)
        
        ctk.CTkLabel(confidence_frame, text="Confiance:", width=150).pack(side="left", padx=10)
        
        # Dropdown pour la confidence (50% à 100% par pas de 5%)
        current_confidence = int(rule.get('confidence', 0.9) * 100)
        confidence_values = [str(i) for i in range(50, 105, 5)]
        
        self.edit_rule_confidence_dropdown = ctk.CTkComboBox(
            confidence_frame,
            values=confidence_values,
            width=100,
            state="readonly"
        )
        self.edit_rule_confidence_dropdown.set(str(current_confidence))
        self.edit_rule_confidence_dropdown.pack(side="left", padx=10)
        
        ctk.CTkLabel(
            confidence_frame,
            text="%  (protection contre modification auto)",
            font=ctk.CTkFont(size=11),
            text_color="gray"
        ).pack(side="left", padx=10)
        
        # Stocker l'ID de la règle et la fenêtre
        self.edit_rule_id = rule['id']
        self.edit_window = edit_window
        
        # Boutons
        action_frame = ctk.CTkFrame(main_frame)
        action_frame.pack(fill="x", pady=(20, 0))
        
        save_btn = ctk.CTkButton(
            action_frame,
            text="💾 Sauvegarder",
            command=lambda: self.save_edited_rule_and_close(edit_window),
            width=150,
            height=35,
            fg_color="green",
            hover_color="darkgreen"
        )
        save_btn.pack(side="left", padx=10, expand=True)
        
        cancel_btn = ctk.CTkButton(
            action_frame,
            text="❌ Annuler",
            command=edit_window.destroy,
            width=100,
            height=35,
            fg_color="gray"
        )
        cancel_btn.pack(side="left", padx=10, expand=True)
    
    def validate_edit_rule_code(self, event=None):
        """Valide le code Google Shopping en temps réel (pour édition)."""
        code = self.edit_rule_code_entry.get().strip()
        
        if not code:
            self.edit_rule_validation.configure(text="")
            return
        
        try:
            cursor = self.db.conn.cursor()
            cursor.execute('SELECT path FROM google_taxonomy WHERE code = ?', (code,))
            result = cursor.fetchone()
            
            if result:
                self.edit_rule_validation.configure(
                    text=f"✅ {result['path'][:50]}...",
                    text_color="green"
                )
            else:
                self.edit_rule_validation.configure(
                    text="❌ Code non trouvé",
                    text_color="red"
                )
        except Exception as e:
            self.edit_rule_validation.configure(
                text=f"❌ Erreur: {e}",
                text_color="red"
            )
    
    def save_edited_rule_and_close(self, window):
        """Sauvegarde la règle modifiée et ferme la fenêtre."""
        success = self.save_edited_rule()
        if success:
            window.destroy()
    
    def save_edited_rule(self):
        """Sauvegarde la règle modifiée.
        
        Returns:
            bool: True si succès, False sinon
        """
        code = self.edit_rule_code_entry.get().strip()
        csv_type = self.edit_rule_type_entry.get().strip().upper()
        confidence_percent = int(self.edit_rule_confidence_dropdown.get())
        confidence = confidence_percent / 100.0  # Convertir en 0.0-1.0
        
        if not code:
            self.rules_status_label.configure(
                text="❌ Le code ne peut pas être vide",
                text_color="red"
            )
            return False
        
        if not csv_type:
            self.rules_status_label.configure(
                text="❌ Le type ne peut pas être vide",
                text_color="red"
            )
            return False
        
        try:
            # Vérifier que le code existe
            cursor = self.db.conn.cursor()
            cursor.execute('SELECT path FROM google_taxonomy WHERE code = ?', (code,))
            result = cursor.fetchone()
            
            if not result:
                self.rules_status_label.configure(
                    text="❌ Code non trouvé dans la taxonomie",
                    text_color="red"
                )
                return False
            
            # Mettre à jour la règle
            success = self.db.update_type_mapping(
                self.edit_rule_id,
                code,
                result['path'],
                csv_type=csv_type,
                confidence=confidence,
                force_update=True  # Modifications manuelles via UI
            )
            
            if success:
                self.rules_status_label.configure(
                    text=f"✅ Règle modifiée: {code} → {result['path'][:30]}...",
                    text_color="green"
                )
                self.refresh_rules()
                return True
            else:
                self.rules_status_label.configure(
                    text="❌ Échec modification règle",
                    text_color="red"
                )
                return False
                
        except Exception as e:
            logger.error(f"Erreur lors de la modification: {e}", exc_info=True)
            self.rules_status_label.configure(
                text=f"❌ Erreur: {e}",
                text_color="red"
            )
            return False
    
    def toggle_rule(self, rule_id, is_active):
        """Active/désactive une règle."""
        try:
            success = self.db.toggle_type_mapping(rule_id, is_active)
            
            if success:
                self.rules_status_label.configure(
                    text=f"✅ Règle {'activée' if is_active else 'désactivée'}",
                    text_color="green"
                )
                self.refresh_rules()
            else:
                self.rules_status_label.configure(
                    text="❌ Échec modification",
                    text_color="red"
                )
                
        except Exception as e:
            logger.error(f"Erreur lors du toggle: {e}", exc_info=True)
            self.rules_status_label.configure(
                text=f"❌ Erreur: {e}",
                text_color="red"
            )
    
    def delete_rule(self, rule_id):
        """Supprime une règle."""
        try:
            success = self.db.delete_type_mapping(rule_id)
            
            if success:
                self.rules_status_label.configure(
                    text="✅ Règle supprimée",
                    text_color="green"
                )
                self.refresh_rules()
            else:
                self.rules_status_label.configure(
                    text="❌ Échec suppression",
                    text_color="red"
                )
                
        except Exception as e:
            logger.error(f"Erreur lors de la suppression: {e}", exc_info=True)
            self.rules_status_label.configure(
                text=f"❌ Erreur: {e}",
                text_color="red"
            )
