"""
Widget pour afficher une carte produit dans le visualiseur CSV.
"""

import customtkinter as ctk
from typing import Dict, List, Optional, Callable
import requests
from io import BytesIO
import threading
from bs4 import BeautifulSoup
import pandas as pd

# Importer PIL de manière optionnelle
try:
    from PIL import Image
    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False
    Image = None


class ProductCard(ctk.CTkFrame):
    """Carte pour afficher un produit avec image, description et checkbox."""
    
    def __init__(self, parent, product_data: Dict, on_selection_changed: Optional[Callable] = None, lazy_load_image: bool = False):
        super().__init__(parent)
        
        self.product_data = product_data
        self.on_selection_changed = on_selection_changed
        self.handle = product_data.get('handle', '')
        
        # Variables pour l'image
        self.image_cache = {}
        self.current_image = None
        self.thumbnail_size = (150, 150)  # Taille originale restaurée
        self.zoom_size = (400, 400)
        self.lazy_load_image = lazy_load_image or True  # Par défaut, chargement différé activé
        self.image_loaded = False
        self.image_loading = False  # Pour éviter les chargements multiples simultanés
        
        # Variable pour la checkbox
        self.selected_var = ctk.BooleanVar(value=False)
        self.selected_var.trace_add('write', self._on_checkbox_changed)
        
        # Créer l'interface
        self._create_widgets()
        
        # Toujours utiliser le chargement différé pour optimiser les performances
        # L'image sera chargée seulement quand la carte devient visible
        self.after(100, self._check_visibility_and_load)
    
    def _create_widgets(self):
        """Crée les widgets de la carte."""
        # Frame principal horizontal
        main_frame = ctk.CTkFrame(self)
        main_frame.pack(fill="both", expand=True, padx=10, pady=10)
        
        # Frame pour l'image (gauche)
        image_frame = ctk.CTkFrame(main_frame, width=160)
        image_frame.pack(side="left", padx=(0, 15), pady=10)
        image_frame.pack_propagate(False)
        
        # Label pour l'image (sera remplacé par l'image chargée)
        self.image_label = ctk.CTkLabel(
            image_frame,
            text="Chargement...",
            width=150,
            height=150
        )
        self.image_label.pack(pady=10)
        
        # Indicateur du nombre d'images si plusieurs
        images = self.product_data.get('images', [])
        if len(images) > 1:
            self.image_count_label = ctk.CTkLabel(
                image_frame,
                text=f"{len(images)} images",
                font=ctk.CTkFont(size=10),
                text_color="gray"
            )
            self.image_count_label.pack(pady=(0, 10))
        
        # Frame pour les informations (centre)
        info_frame = ctk.CTkFrame(main_frame)
        info_frame.pack(side="left", fill="both", expand=True, padx=10, pady=10)
        
        # Titre
        title = self.product_data.get('title', 'Sans titre')
        self.title_label = ctk.CTkLabel(
            info_frame,
            text=title,
            font=ctk.CTkFont(size=16, weight="bold"),
            anchor="w",
            wraplength=400
        )
        self.title_label.pack(anchor="w", pady=(0, 5))
        
        # Informations produit
        info_text = self._get_product_info_text()
        self.info_label = ctk.CTkLabel(
            info_frame,
            text=info_text,
            font=ctk.CTkFont(size=12),
            anchor="w",
            justify="left",
            wraplength=400
        )
        self.info_label.pack(anchor="w", pady=(0, 5))
        
        # Description tronquée
        description = self.product_data.get('description', '')
        truncated_desc = self._truncate_html(description, max_length=100)
        self.desc_label = ctk.CTkLabel(
            info_frame,
            text=truncated_desc,
            font=ctk.CTkFont(size=11),
            anchor="w",
            justify="left",
            text_color="gray",
            wraplength=400
        )
        self.desc_label.pack(anchor="w", pady=(0, 5))
        
        # Ajouter le tooltip pour la description complète
        if description:
            self._setup_description_tooltip(description)
        
        # Frame pour Published et Cost per item
        edit_frame = ctk.CTkFrame(info_frame, fg_color="transparent")
        edit_frame.pack(anchor="w", pady=(5, 0), fill="x")
        
        # Published avec dropdown TRUE/FALSE
        published_frame = ctk.CTkFrame(edit_frame, fg_color="transparent")
        published_frame.pack(side="left", padx=(0, 20), pady=5)
        
        published_label = ctk.CTkLabel(
            published_frame,
            text="Published:",
            font=ctk.CTkFont(size=11)
        )
        published_label.pack(side="left", padx=(0, 5))
        
        self.published_var = ctk.StringVar(value="TRUE" if self.product_data.get('published', True) else "FALSE")
        published_dropdown = ctk.CTkComboBox(
            published_frame,
            values=["TRUE", "FALSE"],
            variable=self.published_var,
            width=80,
            height=25,
            font=ctk.CTkFont(size=11),
            command=self._on_published_changed
        )
        published_dropdown.pack(side="left")
        
        # Cost per item éditable
        cost_frame = ctk.CTkFrame(edit_frame, fg_color="transparent")
        cost_frame.pack(side="left", padx=(0, 10), pady=5)
        
        cost_label = ctk.CTkLabel(
            cost_frame,
            text="Cost per item:",
            font=ctk.CTkFont(size=11)
        )
        cost_label.pack(side="left", padx=(0, 5))
        
        variants = self.product_data.get('variants', [])
        cost_value = variants[0].get('cost_per_item', '') if variants else ''
        self.cost_var = ctk.StringVar(value=str(cost_value) if cost_value else '')
        cost_entry = ctk.CTkEntry(
            cost_frame,
            textvariable=self.cost_var,
            width=100,
            height=25,
            font=ctk.CTkFont(size=11)
        )
        cost_entry.pack(side="left")
        cost_entry.bind("<FocusOut>", self._on_cost_changed)
        cost_entry.bind("<Return>", self._on_cost_changed)
        
        # Frame pour la checkbox (droite)
        checkbox_frame = ctk.CTkFrame(main_frame, width=120)
        checkbox_frame.pack(side="right", padx=10, pady=10)
        checkbox_frame.pack_propagate(False)
        
        # Checkbox de sélection
        self.checkbox = ctk.CTkCheckBox(
            checkbox_frame,
            text="Sélectionner",
            variable=self.selected_var,
            font=ctk.CTkFont(size=12)
        )
        self.checkbox.pack(pady=20)
    
    def _get_product_info_text(self) -> str:
        """Génère le texte d'information du produit."""
        lines = []
        
        # Vendor
        vendor = self.product_data.get('vendor', '')
        if vendor:
            lines.append(f"Vendor: {vendor}")
        
        # Type
        product_type = self.product_data.get('type', '')
        if product_type:
            lines.append(f"Type: {product_type}")
        
        # Prix
        variants = self.product_data.get('variants', [])
        if variants:
            prices = []
            for variant in variants:
                price = variant.get('price', '')
                if price:
                    try:
                        prices.append(float(price))
                    except (ValueError, TypeError):
                        pass
            
            if prices:
                min_price = min(prices)
                max_price = max(prices)
                if min_price == max_price:
                    lines.append(f"Prix: {min_price:.2f} €")
                else:
                    lines.append(f"Prix: {min_price:.2f} - {max_price:.2f} €")
        
        # Nombre de variantes
        if len(variants) > 1:
            lines.append(f"{len(variants)} variantes")
        
        # SKU principal
        if variants:
            sku = variants[0].get('sku', '')
            if sku:
                lines.append(f"SKU: {sku}")
            
            # Barcode variant en dessous du SKU
            barcode = variants[0].get('barcode', '')
            if barcode:
                lines.append(f"Barcode variant: {barcode}")
        
        # Published
        published = self.product_data.get('published', True)
        lines.append(f"Published: {'TRUE' if published else 'FALSE'}")
        
        return "\n".join(lines) if lines else "Aucune information"
    
    def _truncate_html(self, html_text: str, max_length: int = 100) -> str:
        """Tronque le texte HTML en extrayant d'abord le texte brut."""
        # Gérer les cas où html_text pourrait être NaN, None ou un float
        if html_text is None or (isinstance(html_text, float) and pd.isna(html_text)):
            return ''
        
        # Convertir en string si ce n'est pas déjà le cas
        html_text = str(html_text) if html_text else ''
        
        if not html_text:
            return ""
        
        try:
            # Extraire le texte brut du HTML
            soup = BeautifulSoup(html_text, 'html.parser')
            text = soup.get_text(separator=' ', strip=True)
            
            # Tronquer si nécessaire
            if len(text) > max_length:
                return text[:max_length] + "..."
            return text
        except Exception:
            # En cas d'erreur, retourner le texte brut tronqué
            text = html_text.replace('<', '&lt;').replace('>', '&gt;')
            if len(text) > max_length:
                return text[:max_length] + "..."
            return text
    
    def _setup_description_tooltip(self, description: str):
        """Configure le tooltip pour afficher la description HTML complète."""
        # Créer une fenêtre tooltip qui s'affiche au survol
        tooltip_window = None
        
        def show_tooltip(event):
            nonlocal tooltip_window
            
            # Créer la fenêtre tooltip
            tooltip_window = ctk.CTkToplevel(self)
            tooltip_window.overrideredirect(True)
            tooltip_window.geometry("400x300")
            
            # Positionner près du curseur
            x = event.x_root + 20
            y = event.y_root + 20
            tooltip_window.geometry(f"+{x}+{y}")
            
            # Frame avec scrollbar pour le contenu HTML
            scroll_frame = ctk.CTkScrollableFrame(tooltip_window)
            scroll_frame.pack(fill="both", expand=True, padx=10, pady=10)
            
            # Convertir HTML en texte formaté
            try:
                soup = BeautifulSoup(description, 'html.parser')
                # Extraire le texte avec préservation de la structure
                text = soup.get_text(separator='\n', strip=True)
            except Exception:
                text = description
            
            # Label avec le texte
            desc_label = ctk.CTkLabel(
                scroll_frame,
                text=text,
                font=ctk.CTkFont(size=11),
                anchor="w",
                justify="left",
                wraplength=380
            )
            desc_label.pack(fill="both", expand=True, padx=10, pady=10)
        
        def hide_tooltip(event):
            nonlocal tooltip_window
            if tooltip_window:
                tooltip_window.destroy()
                tooltip_window = None
        
        # Lier les événements de survol
        self.desc_label.bind("<Enter>", show_tooltip)
        self.desc_label.bind("<Leave>", hide_tooltip)
    
    def _check_visibility_and_load(self):
        """Vérifie si la carte est visible et charge l'image si nécessaire."""
        if self.image_loaded or self.image_loading:
            return
        
        try:
            # Vérifier si le widget existe toujours
            if not self.winfo_exists():
                return
            
            # Vérifier si le widget est visible dans la fenêtre
            if self.winfo_viewable():
                # Vérifier la position réelle dans le canvas parent pour un chargement vraiment différé
                try:
                    # Obtenir la position de la carte
                    card_y = self.winfo_y()
                    card_height = self.winfo_height()
                    
                    # Chercher le canvas parent (products_canvas)
                    parent = self.master
                    canvas = None
                    while parent:
                        if hasattr(parent, 'products_canvas'):
                            canvas = parent.products_canvas
                            break
                        parent = getattr(parent, 'master', None)
                    
                    if canvas:
                        # Obtenir la zone visible du canvas
                        scroll_y = abs(int(canvas.canvasy(0))) if canvas.canvasy(0) else 0
                        visible_height = canvas.winfo_height()
                        scroll_bottom = scroll_y + visible_height
                        
                        # Vérifier si la carte est dans la zone visible (avec une marge de 300px)
                        card_top = card_y
                        card_bottom = card_top + card_height
                        
                        if card_bottom >= scroll_y - 300 and card_top <= scroll_bottom + 300:
                            # La carte est visible, charger l'image
                            self._load_image_async()
                            self.image_loaded = True
                            return
                    else:
                        # Si pas de canvas trouvé, charger si visible
                        self._load_image_async()
                        self.image_loaded = True
                        return
                except Exception:
                    # En cas d'erreur de calcul, charger quand même si visible
                    self._load_image_async()
                    self.image_loaded = True
                    return
            
            # Si pas visible, réessayer plus tard (mais pas trop souvent)
            if not hasattr(self, '_visibility_check_count'):
                self._visibility_check_count = 0
            self._visibility_check_count += 1
            if self._visibility_check_count < 20:  # Limiter à 20 tentatives
                self.after(500, self._check_visibility_and_load)
        except Exception:
            # En cas d'erreur, charger quand même l'image après un délai
            if not self.image_loaded and not self.image_loading:
                self.after(1000, lambda: self._load_image_async() if not self.image_loaded else None)
                self.image_loaded = True
    
    def _is_card_visible(self):
        """Vérifie si la carte est actuellement visible dans la zone de scroll."""
        try:
            if not self.winfo_exists() or not self.winfo_viewable():
                return False
            
            # Chercher le canvas parent (products_canvas)
            parent = self.master
            canvas = None
            while parent:
                if hasattr(parent, 'products_canvas'):
                    canvas = parent.products_canvas
                    break
                parent = getattr(parent, 'master', None)
            
            if canvas:
                # Obtenir la position de la carte
                card_y = self.winfo_y()
                card_height = self.winfo_height()
                
                # Obtenir la zone visible du canvas
                scroll_y = abs(int(canvas.canvasy(0))) if canvas.canvasy(0) else 0
                visible_height = canvas.winfo_height()
                scroll_bottom = scroll_y + visible_height
                
                # Vérifier si la carte est dans la zone visible (avec une marge de 300px)
                card_top = card_y
                card_bottom = card_top + card_height
                
                return card_bottom >= scroll_y - 300 and card_top <= scroll_bottom + 300
            
            # Si pas de canvas, considérer comme visible si le widget est viewable
            return True
        except Exception:
            return False
    
    def _load_image_async(self):
        """Charge l'image de manière asynchrone."""
        if not PIL_AVAILABLE:
            self.image_label.configure(text="Pillow requis\npour les images")
            return
        
        # Éviter les chargements multiples simultanés
        if self.image_loading:
            return
        
        # Vérifier la visibilité avant de commencer le chargement
        if not self._is_card_visible():
            # Si pas visible, réessayer plus tard
            if not hasattr(self, '_visibility_check_count'):
                self._visibility_check_count = 0
            self._visibility_check_count += 1
            if self._visibility_check_count < 20:
                self.after(500, self._check_visibility_and_load)
            return
        
        images = self.product_data.get('images', [])
        if not images:
            self.image_label.configure(text="Pas d'image")
            return
        
        # Prendre la première image
        image_url = images[0]
        
        # Éviter les chargements multiples de la même image
        if image_url in self.image_cache:
            cached_image = self.image_cache[image_url]
            # Vérifier la visibilité avant d'afficher
            if self._is_card_visible():
                self._display_image(cached_image, image_url)
            return
        
        self.image_loading = True
        
        def load_image():
            try:
                # Vérifier la visibilité avant de télécharger
                if not self._is_card_visible():
                    self.after(0, lambda: setattr(self, 'image_loading', False))
                    return
                
                # Télécharger l'image avec un timeout plus court et des headers pour optimiser
                headers = {
                    'User-Agent': 'Mozilla/5.0 (compatible; ImageLoader/1.0)',
                    'Accept': 'image/webp,image/*,*/*;q=0.8'
                }
                response = requests.get(image_url, timeout=5, headers=headers, stream=True)
                response.raise_for_status()
                
                # Vérifier à nouveau la visibilité après le téléchargement
                if not self._is_card_visible():
                    self.after(0, lambda: setattr(self, 'image_loading', False))
                    return
                
                # Charger avec PIL
                img = Image.open(BytesIO(response.content))
                
                # Vérifier encore une fois avant le traitement (pour un scroll très rapide)
                if not self._is_card_visible():
                    self.after(0, lambda: setattr(self, 'image_loading', False))
                    return
                
                # Convertir en RGB si nécessaire (pour réduire la taille)
                if img.mode in ('RGBA', 'LA', 'P'):
                    # Créer un fond blanc pour les images transparentes
                    rgb_img = Image.new('RGB', img.size, (255, 255, 255))
                    if img.mode == 'P':
                        img = img.convert('RGBA')
                    rgb_img.paste(img, mask=img.split()[-1] if img.mode == 'RGBA' else None)
                    img = rgb_img
                elif img.mode != 'RGB':
                    img = img.convert('RGB')
                
                # Créer le thumbnail avec une qualité réduite pour un chargement plus rapide
                img.thumbnail(self.thumbnail_size, Image.Resampling.LANCZOS)
                
                # Obtenir la taille réelle après thumbnail
                actual_size = img.size
                
                # Convertir en CTkImage pour CustomTkinter
                ctk_image = ctk.CTkImage(light_image=img, dark_image=img, size=actual_size)
                
                # Mettre en cache
                self.image_cache[image_url] = ctk_image
                
                # Vérifier une dernière fois avant d'afficher
                def display_if_visible():
                    if self._is_card_visible():
                        self._display_image(ctk_image, image_url)
                    self.image_loading = False
                
                # Mettre à jour l'interface dans le thread principal
                self.after(0, display_if_visible)
                
            except Exception as e:
                # En cas d'erreur, afficher un message seulement si visible
                def handle_error():
                    if self._is_card_visible():
                        error_msg = str(e)[:20]
                        self.image_label.configure(text=f"Erreur\n{error_msg}")
                    self.image_loading = False
                self.after(0, handle_error)
        
        # Lancer dans un thread séparé
        threading.Thread(target=load_image, daemon=True).start()
    
    def _display_image(self, ctk_image, image_url: str):
        """Affiche l'image dans le label."""
        self.image_label.configure(image=ctk_image, text="")
        self.current_image = ctk_image  # Garder une référence
        
        # Configurer le zoom au survol
        self._setup_image_zoom(image_url)
    
    def _setup_image_zoom(self, image_url: str):
        """Configure le zoom de l'image au survol."""
        if not PIL_AVAILABLE:
            return  # Désactiver le zoom si PIL n'est pas disponible
        
        zoom_window = None
        
        def show_zoom(event):
            nonlocal zoom_window
            
            # Créer la fenêtre de zoom
            zoom_window = ctk.CTkToplevel(self)
            zoom_window.overrideredirect(True)
            zoom_window.geometry(f"{self.zoom_size[0]}x{self.zoom_size[1]}")
            
            # Positionner près du curseur
            x = event.x_root + 20
            y = event.y_root + 20
            zoom_window.geometry(f"+{x}+{y}")
            
            # Charger l'image en grand
            def load_zoom_image():
                try:
                    response = requests.get(image_url, timeout=10)
                    response.raise_for_status()
                    img = Image.open(BytesIO(response.content))
                    img.thumbnail(self.zoom_size, Image.Resampling.LANCZOS)
                    
                    # Obtenir la taille réelle après thumbnail
                    actual_size = img.size
                    
                    # Convertir en CTkImage pour CustomTkinter
                    ctk_image = ctk.CTkImage(light_image=img, dark_image=img, size=actual_size)
                    
                    zoom_label = ctk.CTkLabel(zoom_window, image=ctk_image, text="")
                    zoom_label.pack(fill="both", expand=True, padx=5, pady=5)
                    zoom_label.image = ctk_image  # Garder une référence
                except Exception:
                    zoom_label = ctk.CTkLabel(zoom_window, text="Erreur de chargement")
                    zoom_label.pack(fill="both", expand=True, padx=5, pady=5)
            
            threading.Thread(target=load_zoom_image, daemon=True).start()
        
        def hide_zoom(event):
            nonlocal zoom_window
            if zoom_window:
                zoom_window.destroy()
                zoom_window = None
        
        # Lier les événements
        self.image_label.bind("<Enter>", show_zoom)
        self.image_label.bind("<Leave>", hide_zoom)
    
    def _on_checkbox_changed(self, *args):
        """Appelé quand la checkbox change."""
        if self.on_selection_changed:
            self.on_selection_changed(self.handle, self.selected_var.get())
    
    def is_selected(self) -> bool:
        """Retourne True si le produit est sélectionné."""
        return self.selected_var.get()
    
    def set_selected(self, selected: bool):
        """Définit l'état de sélection."""
        self.selected_var.set(selected)
    
    def _on_published_changed(self, value: str):
        """Appelé quand Published change."""
        self.product_data['published'] = value.upper() == 'TRUE'
    
    def _on_cost_changed(self, event=None):
        """Appelé quand Cost per item change."""
        cost_value = self.cost_var.get().strip()
        variants = self.product_data.get('variants', [])
        if variants:
            variants[0]['cost_per_item'] = cost_value
    
    def get_product_data(self) -> Dict:
        """Retourne les données du produit avec les modifications."""
        return self.product_data

