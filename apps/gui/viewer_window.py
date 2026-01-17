"""
Fenêtre de visualisation et sélection de produits depuis un fichier CSV Shopify.
Version optimisée avec WebView (tkinterweb) pour de meilleures performances.
"""

import customtkinter as ctk
from typing import Dict, List, Optional
import pandas as pd
import os
import sys
import json
from datetime import datetime
from tkinter import filedialog, messagebox
import logging
import threading

logger = logging.getLogger(__name__)

# Ajouter le répertoire parent au path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Importer tkinterweb de manière optionnelle
try:
    import tkinterweb
    WEBVIEW_AVAILABLE = True
except ImportError:
    WEBVIEW_AVAILABLE = False
    tkinterweb = None
    logger.warning("tkinterweb non disponible. Installez-le avec: pip install tkinterweb")

# Template HTML pour le visualiseur avec DataTables
HTML_TEMPLATE = """<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>Visualiseur CSV Shopify</title>
    <link rel="stylesheet" href="https://cdn.datatables.net/1.13.7/css/jquery.dataTables.min.css">
    <style>
        * {{
            box-sizing: border-box;
        }}
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
            background: #212121;
            color: #ffffff;
            margin: 0;
            padding: 20px;
        }}
        .controls {{
            margin-bottom: 20px;
            display: flex;
            gap: 15px;
            align-items: center;
            flex-wrap: wrap;
        }}
        .controls input[type="text"] {{
            padding: 10px 15px;
            border: 1px solid #555;
            border-radius: 6px;
            background: #2b2b2b;
            color: #fff;
            font-size: 14px;
            min-width: 300px;
        }}
        .controls input[type="text"]:focus {{
            outline: none;
            border-color: #1f538d;
        }}
        .controls button {{
            padding: 10px 20px;
            border: none;
            border-radius: 6px;
            background: #1f538d;
            color: #fff;
            cursor: pointer;
            font-size: 14px;
            font-weight: 500;
            transition: background 0.2s;
        }}
        .controls button:hover {{
            background: #2563eb;
        }}
        .controls button:active {{
            background: #1e40af;
        }}
        #selectionCount {{
            padding: 10px 15px;
            background: #2b2b2b;
            border-radius: 6px;
            font-size: 14px;
            color: #4ade80;
            font-weight: 500;
        }}
        #productTable {{
            background: #2b2b2b;
            border-collapse: collapse;
            width: 100%;
        }}
        #productTable thead th {{
            background: #1f538d;
            color: #fff;
            padding: 12px 15px;
            text-align: left;
            font-weight: 600;
            border-bottom: 2px solid #2563eb;
        }}
        #productTable tbody td {{
            padding: 12px 15px;
            border-bottom: 1px solid #444;
            vertical-align: middle;
        }}
        #productTable tbody tr {{
            transition: background 0.2s;
        }}
        #productTable tbody tr:hover {{
            background: #333;
        }}
        #productTable tbody tr.selected {{
            background: #1f538d40;
        }}
        .product-image {{
            width: 80px;
            height: 80px;
            object-fit: cover;
            border-radius: 6px;
            border: 2px solid #444;
        }}
        .product-image:hover {{
            border-color: #1f538d;
            cursor: pointer;
        }}
        .checkbox-cell {{
            text-align: center;
            width: 50px;
        }}
        .checkbox-cell input[type="checkbox"] {{
            width: 18px;
            height: 18px;
            cursor: pointer;
        }}
        .no-image {{
            width: 80px;
            height: 80px;
            background: #333;
            border-radius: 6px;
            display: flex;
            align-items: center;
            justify-content: center;
            color: #999;
            font-size: 11px;
            text-align: center;
        }}
        .dataTables_wrapper {{
            color: #fff;
        }}
        .dataTables_filter input {{
            background: #2b2b2b;
            border: 1px solid #555;
            color: #fff;
            padding: 8px;
            border-radius: 4px;
        }}
        .dataTables_length select {{
            background: #2b2b2b;
            border: 1px solid #555;
            color: #fff;
            padding: 6px;
            border-radius: 4px;
        }}
        .dataTables_paginate .paginate_button {{
            color: #fff !important;
            background: #2b2b2b !important;
            border: 1px solid #555 !important;
        }}
        .dataTables_paginate .paginate_button:hover {{
            background: #1f538d !important;
            border-color: #1f538d !important;
        }}
        .dataTables_paginate .paginate_button.current {{
            background: #1f538d !important;
            border-color: #1f538d !important;
        }}
        .dataTables_info {{
            color: #ccc;
        }}
    </style>
</head>
<body>
    <div class="controls">
        <input type="text" id="searchInput" placeholder="Rechercher par titre, vendor, SKU...">
        <button onclick="selectAll()">✓ Tout sélectionner</button>
        <button onclick="deselectAll()">✗ Tout désélectionner</button>
        <span id="selectionCount">0 produit(s) sélectionné(s)</span>
    </div>
    <table id="productTable" class="display" style="width:100%">
        <thead>
            <tr>
                <th class="checkbox-cell"><input type="checkbox" id="selectAllCheckbox"></th>
                <th>Image</th>
                <th>Titre</th>
                <th>Vendor</th>
                <th>Type</th>
                <th>Prix</th>
                <th>SKU</th>
                <th>Variantes</th>
            </tr>
        </thead>
        <tbody id="productTableBody">
        </tbody>
    </table>
    
    <script>
        (function() {{
            console.log('Début du script');
            let selectedHandles = new Set();
            let productsData = {products_json};
            
            console.log('Produits chargés:', Object.keys(productsData).length);
            
            // Afficher immédiatement un message de test
            document.body.insertAdjacentHTML('afterbegin', '<div style="padding:20px;background:#333;margin-bottom:20px;"><strong>Test:</strong> ' + Object.keys(productsData).length + ' produits chargés</div>');
        
        // Fonction pour échapper les caractères HTML
        function escapeHtml(text) {{
            if (!text) return '';
            const map = {{
                '&': '&amp;',
                '<': '&lt;',
                '>': '&gt;',
                '"': '&quot;',
                "'": '&#039;'
            }};
            return String(text).replace(/[&<>"']/g, m => map[m]);
        }}
        
        // Fonction pour formater le prix
        function formatPrice(price) {{
            if (!price) return '';
            try {{
                const num = parseFloat(price);
                return isNaN(num) ? price : num.toFixed(2) + ' €';
            }} catch {{
                return price;
            }}
        }}
        
        // Fonction pour afficher les produits sans DataTables (fallback)
        function displayProductsSimple() {{
            const tbody = document.getElementById('productTableBody');
            if (!tbody) {{
                console.error('tbody non trouvé');
                return;
            }}
            
            tbody.innerHTML = '';
            const products = Object.values(productsData);
            console.log('Affichage de', products.length, 'produits');
            
            products.forEach((product, index) => {{
                const firstVariant = product.variants && product.variants.length > 0 ? product.variants[0] : null;
                const imageUrl = product.images && product.images.length > 0 ? product.images[0] : null;
                
                const tr = document.createElement('tr');
                tr.innerHTML = `
                    <td class="checkbox-cell">
                        <input type="checkbox" class="product-checkbox" data-handle="${{escapeHtml(product.handle)}}">
                    </td>
                    <td>${{imageUrl ? `<img src="${{escapeHtml(imageUrl)}}" class="product-image" onerror="this.parentElement.innerHTML='<div class=\\'no-image\\'>Pas d\\'image</div>'">` : '<div class="no-image">Pas d\'image</div>'}}</td>
                    <td>${{escapeHtml(product.title || '')}}</td>
                    <td>${{escapeHtml(product.vendor || '')}}</td>
                    <td>${{escapeHtml(product.type || '')}}</td>
                    <td>${{formatPrice(firstVariant ? firstVariant.price : '')}}</td>
                    <td>${{escapeHtml(firstVariant ? firstVariant.sku : '')}}</td>
                    <td>${{product.variants ? product.variants.length : 0}}</td>
                `;
                tbody.appendChild(tr);
            }});
            
            // Ajouter les event listeners pour les checkboxes
            document.querySelectorAll('.product-checkbox').forEach(checkbox => {{
                checkbox.addEventListener('change', function() {{
                    const handle = this.getAttribute('data-handle');
                    const row = this.closest('tr');
                    if (this.checked) {{
                        selectedHandles.add(handle);
                        row.classList.add('selected');
                    }} else {{
                        selectedHandles.delete(handle);
                        row.classList.remove('selected');
                    }}
                    updateSelectionCount();
                }});
            }});
            
            // Recherche simple
            const searchInput = document.getElementById('searchInput');
            if (searchInput) {{
                searchInput.addEventListener('keyup', function() {{
                    const filter = this.value.toLowerCase();
                    const rows = tbody.querySelectorAll('tr');
                    rows.forEach(row => {{
                        const text = row.textContent.toLowerCase();
                        row.style.display = text.includes(filter) ? '' : 'none';
                    }});
                }});
            }}
            
            console.log('Produits affichés:', products.length);
        }}
        
        // Essayer d'utiliser jQuery/DataTables si disponible, sinon fallback
        if (typeof jQuery !== 'undefined' && typeof jQuery.fn.dataTable !== 'undefined') {{
            $(document).ready(function() {{
                console.log('jQuery et DataTables disponibles, utilisation de DataTables');
                // Préparer les données pour DataTables
                const tableData = Object.values(productsData).map(product => {{
                    const firstVariant = product.variants && product.variants.length > 0 ? product.variants[0] : null;
                    const imageUrl = product.images && product.images.length > 0 ? product.images[0] : null;
                    
                    return [
                        `<input type="checkbox" class="product-checkbox" data-handle="${{escapeHtml(product.handle)}}">`,
                        imageUrl 
                            ? `<img src="${{escapeHtml(imageUrl)}}" class="product-image" onerror="this.parentElement.innerHTML='<div class=\\'no-image\\'>Pas d\\'image</div>'">`
                            : '<div class="no-image">Pas d\'image</div>',
                        escapeHtml(product.title || ''),
                        escapeHtml(product.vendor || ''),
                        escapeHtml(product.type || ''),
                        formatPrice(firstVariant ? firstVariant.price : ''),
                        escapeHtml(firstVariant ? firstVariant.sku : ''),
                        product.variants ? product.variants.length : 0
                    ];
                }});
                
                try {{
                    table = $('#productTable').DataTable({{
                        data: tableData,
                        pageLength: 50,
                        lengthMenu: [[25, 50, 100, 200, -1], [25, 50, 100, 200, "Tous"]],
                        order: [[2, 'asc']],
                        columnDefs: [
                            {{ orderable: false, targets: [0, 1] }}
                        ],
                        drawCallback: function() {{
                            $('.product-checkbox').each(function() {{
                                const handle = $(this).data('handle');
                                $(this).prop('checked', selectedHandles.has(handle));
                                const row = $(this).closest('tr');
                                if (selectedHandles.has(handle)) {{
                                    row.addClass('selected');
                                }} else {{
                                    row.removeClass('selected');
                                }}
                            }});
                        }}
                    }});
                    
                    $('#searchInput').on('keyup', function() {{
                        table.search(this.value).draw();
                    }});
                    
                    $(document).on('change', '.product-checkbox', function() {{
                        const handle = $(this).data('handle');
                        const row = $(this).closest('tr');
                        if ($(this).is(':checked')) {{
                            selectedHandles.add(handle);
                            row.addClass('selected');
                        }} else {{
                            selectedHandles.delete(handle);
                            row.removeClass('selected');
                        }}
                        updateSelectionCount();
                    }});
                }} catch (error) {{
                    console.error('Erreur DataTables:', error);
                    displayProductsSimple();
                }}
            }});
        }} else {{
            console.log('jQuery/DataTables non disponibles, utilisation du mode simple');
            // Attendre que le DOM soit prêt
            if (document.readyState === 'loading') {{
                document.addEventListener('DOMContentLoaded', displayProductsSimple);
            }} else {{
                displayProductsSimple();
            }}
        }}
            
            // Recherche dans DataTables
            $('#searchInput').on('keyup', function() {{
                table.search(this.value).draw();
            }});
            
            // Gestion des checkboxes individuelles
            $(document).on('change', '.product-checkbox', function() {{
                const handle = $(this).data('handle');
                const row = $(this).closest('tr');
                
                if ($(this).is(':checked')) {{
                    selectedHandles.add(handle);
                    row.addClass('selected');
                }} else {{
                    selectedHandles.delete(handle);
                    row.removeClass('selected');
                }}
                
                updateSelectionCount();
                notifyPython('selection_changed', Array.from(selectedHandles));
            }});
            
            // Checkbox "Tout sélectionner"
            $('#selectAllCheckbox').on('change', function() {{
                const isChecked = $(this).is(':checked');
                $('.product-checkbox').each(function() {{
                    $(this).prop('checked', isChecked);
                    const handle = $(this).data('handle');
                    const row = $(this).closest('tr');
                    
                    if (isChecked) {{
                        selectedHandles.add(handle);
                        row.addClass('selected');
                    }} else {{
                        selectedHandles.delete(handle);
                        row.removeClass('selected');
                    }}
                }});
                updateSelectionCount();
                notifyPython('selection_changed', Array.from(selectedHandles));
            }});
            
            function selectAll() {{
                $('.product-checkbox').prop('checked', true).trigger('change');
                $('#selectAllCheckbox').prop('checked', true);
            }}
            
            function deselectAll() {{
                $('.product-checkbox').prop('checked', false).trigger('change');
                $('#selectAllCheckbox').prop('checked', false);
            }}
            
            function updateSelectionCount() {{
                const count = selectedHandles.size;
                $('#selectionCount').text(`${{count}} produit(s) sélectionné(s)`);
            }}
            
            // Fonction pour communiquer avec Python via tkinterweb
            function notifyPython(event, data) {{
                try {{
                    // tkinterweb permet d'exécuter du JavaScript depuis Python
                    // On utilise une variable globale que Python peut lire
                    if (typeof window.pythonCallback === 'function') {{
                        window.pythonCallback(event, data);
                    }}
                }} catch (e) {{
                    console.error('Erreur communication Python:', e);
                }}
            }}
            
            // Exposer les fonctions globalement pour que Python puisse les appeler
            window.selectAllProducts = selectAll;
            window.deselectAllProducts = deselectAll;
            window.getSelectedHandles = function() {{
                return Array.from(selectedHandles);
            }};
        }});
    </script>
</body>
</html>
"""


class ViewerWindow(ctk.CTkToplevel):
    """Fenêtre pour visualiser et sélectionner des produits depuis un CSV Shopify avec WebView."""
    
    def __init__(self, parent):
        super().__init__(parent)
        
        self.title("Visualiseur CSV Shopify")
        self.geometry("1400x900")
        self.resizable(True, True)
        
        # Configuration CustomTkinter
        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("blue")
        
        # Variables
        self.df: Optional[pd.DataFrame] = None
        self.products: Dict[str, Dict] = {}
        self.selected_handles: set = set()
        self.html_frame = None
        
        # Variables pour la pagination et recherche
        self.current_page = 1
        self.items_per_page = 50
        self.search_filter = ""
        
        # Créer l'interface
        self._create_widgets()
        
        # Centrer la fenêtre
        self.center_window()

        # Garder la fenêtre au premier plan par rapport au parent
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
            self.update_idletasks()
            self.lift()
            self.focus_force()
            self.attributes('-topmost', True)
            self.after(150, lambda: self.attributes('-topmost', False))
        except Exception:
            pass
    
    def _create_widgets(self):
        """Crée les widgets de l'interface."""
        # Frame principal
        main_frame = ctk.CTkFrame(self)
        main_frame.pack(fill="both", expand=True, padx=20, pady=20)
        
        # Header avec bouton de chargement
        header_frame = ctk.CTkFrame(main_frame)
        header_frame.pack(fill="x", pady=(0, 20))
        
        # Titre
        title_label = ctk.CTkLabel(
            header_frame,
            text="Visualiseur CSV Shopify",
            font=ctk.CTkFont(size=24, weight="bold")
        )
        title_label.pack(side="left", padx=20, pady=15)
        
        # Bouton charger fichier
        self.load_button = ctk.CTkButton(
            header_frame,
            text="📁 Charger un fichier CSV",
            command=self._load_csv_file,
            width=200,
            height=40,
            font=ctk.CTkFont(size=14)
        )
        self.load_button.pack(side="right", padx=20, pady=15)
        
        # Contrôles de recherche et pagination (au-dessus du WebView)
        controls_webview_frame = ctk.CTkFrame(main_frame)
        controls_webview_frame.pack(fill="x", pady=(0, 10))
        
        # Recherche
        search_webview_frame = ctk.CTkFrame(controls_webview_frame, fg_color="transparent")
        search_webview_frame.pack(side="left", fill="x", expand=True, padx=10, pady=10)
        
        search_label_webview = ctk.CTkLabel(search_webview_frame, text="Rechercher:", font=ctk.CTkFont(size=12))
        search_label_webview.pack(side="left", padx=(0, 10))
        
        self.search_var_webview = ctk.StringVar(value="")
        self.search_entry_webview = ctk.CTkEntry(
            search_webview_frame,
            textvariable=self.search_var_webview,
            width=300,
            placeholder_text="Titre, Vendor, SKU..."
        )
        self.search_entry_webview.pack(side="left", padx=10)
        self.search_entry_webview.bind("<KeyRelease>", lambda e: self._on_search_webview())
        
        # Boutons de sélection
        selection_webview_frame = ctk.CTkFrame(controls_webview_frame, fg_color="transparent")
        selection_webview_frame.pack(side="right", padx=10, pady=10)
        
        self.select_all_webview_button = ctk.CTkButton(
            selection_webview_frame,
            text="✓ Tout sélectionner",
            command=self._select_all_webview,
            width=120,
            height=30,
            font=ctk.CTkFont(size=11)
        )
        self.select_all_webview_button.pack(side="left", padx=5)
        
        self.deselect_all_webview_button = ctk.CTkButton(
            selection_webview_frame,
            text="✗ Tout désélectionner",
            command=self._deselect_all_webview,
            width=120,
            height=30,
            font=ctk.CTkFont(size=11)
        )
        self.deselect_all_webview_button.pack(side="left", padx=5)
        
        # Compteur de sélection
        self.selection_counter_webview = ctk.CTkLabel(
            controls_webview_frame,
            text="0 produit(s) sélectionné(s)",
            font=ctk.CTkFont(size=12),
            text_color="gray"
        )
        self.selection_counter_webview.pack(side="right", padx=20)
        
        # Pagination
        pagination_frame = ctk.CTkFrame(main_frame, fg_color="transparent")
        pagination_frame.pack(fill="x", pady=(0, 10))
        
        self.prev_button = ctk.CTkButton(
            pagination_frame,
            text="← Précédent",
            command=self._prev_page,
            width=100,
            height=30,
            font=ctk.CTkFont(size=11),
            state="disabled"
        )
        self.prev_button.pack(side="left", padx=10)
        
        self.page_info_label = ctk.CTkLabel(
            pagination_frame,
            text="Page 1 sur 1",
            font=ctk.CTkFont(size=12)
        )
        self.page_info_label.pack(side="left", padx=20)
        
        self.next_button = ctk.CTkButton(
            pagination_frame,
            text="Suivant →",
            command=self._next_page,
            width=100,
            height=30,
            font=ctk.CTkFont(size=11),
            state="disabled"
        )
        self.next_button.pack(side="left", padx=10)
        
        # Zone WebView
        if WEBVIEW_AVAILABLE:
            # Créer un frame Tkinter natif (pas CTkFrame) pour éviter les conflits de scroll avec CustomTkinter
            from tkinter import Frame
            webview_frame = Frame(main_frame, bg="#212121")
            webview_frame.pack(fill="both", expand=True, pady=(0, 20))
            
            try:
                # Créer le widget HtmlFrame de tkinterweb
                # Note: messages_enabled=True peut être nécessaire pour certaines fonctionnalités
                self.html_frame = tkinterweb.HtmlFrame(webview_frame, messages_enabled=True)
                self.html_frame.pack(fill="both", expand=True)
                
                # Désactiver les bindings de scroll de CustomTkinter sur ce frame pour éviter les conflits
                # Le HtmlFrame gère son propre scroll
                try:
                    webview_frame.unbind_all("<MouseWheel>")
                    webview_frame.unbind_all("<Button-4>")
                    webview_frame.unbind_all("<Button-5>")
                except:
                    pass
        
        # Message initial
                initial_html = """<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <style>
        body {
            background: #212121;
            color: #fff;
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            padding: 50px;
            text-align: center;
        }
        h2 {
            color: #ccc;
            font-weight: 300;
        }
    </style>
</head>
<body>
    <h2>Cliquez sur 'Charger un fichier CSV' pour commencer</h2>
</body>
</html>"""
                self.html_frame.load_html(initial_html)
                logger.info("WebView initialisé avec succès")
            except Exception as e:
                logger.error(f"Erreur lors de la création du WebView: {e}", exc_info=True)
                error_label = ctk.CTkLabel(
                    webview_frame,
                    text=f"Erreur lors de l'initialisation du WebView:\n{str(e)}",
                    font=ctk.CTkFont(size=12),
                    text_color="red"
                )
                error_label.pack(pady=50)
        else:
            # Fallback si tkinterweb n'est pas disponible
            error_label = ctk.CTkLabel(
                main_frame,
                text="tkinterweb n'est pas installé.\n\nInstallez-le avec:\npip install tkinterweb\n\nPuis redémarrez l'application.",
            font=ctk.CTkFont(size=14),
                text_color="orange",
                justify="left"
        )
            error_label.pack(pady=50)
        
        # Frame pour les boutons d'action
        self.action_frame = ctk.CTkFrame(main_frame)
        self.action_frame.pack(fill="x")
        
        # Bouton exporter
        self.export_button = ctk.CTkButton(
            self.action_frame,
            text="💾 Exporter CSV",
            command=self._export_csv,
            width=200,
            height=40,
            font=ctk.CTkFont(size=14),
            state="disabled",
            fg_color="green",
            hover_color="darkgreen"
        )
        self.export_button.pack(side="right", padx=20, pady=10)
    
    def _load_csv_file(self):
        """Ouvre un dialogue pour charger un fichier CSV."""
        file_path = filedialog.askopenfilename(
            title="Sélectionner un fichier CSV Shopify",
            filetypes=[("Fichiers CSV", "*.csv"), ("Tous les fichiers", "*.*")]
        )
        
        if file_path:
            self._parse_csv(file_path)
    
    def _parse_csv(self, file_path: str):
        """Parse le fichier CSV et groupe les produits par Handle."""
        try:
            # Charger le CSV
            self.df = pd.read_csv(file_path, encoding='utf-8', dtype=str, keep_default_na=False)
            
            # Valider le format Shopify
            if 'Handle' not in self.df.columns:
                messagebox.showerror(
                    "Erreur",
                    "Le fichier CSV ne semble pas être au format Shopify.\n"
                    "La colonne 'Handle' est manquante."
                )
                return
            
            # Grouper par Handle
            self.products = {}
            for handle in self.df['Handle'].unique():
                if pd.isna(handle) or handle == '':
                    continue
                
                handle_rows = self.df[self.df['Handle'] == handle]
                first_row = handle_rows.iloc[0]
                
                product = {
                    'handle': str(handle),
                    'title': first_row.get('Title', ''),
                    'description': first_row.get('Body (HTML)', ''),
                    'vendor': first_row.get('Vendor', ''),
                    'type': first_row.get('Type', ''),
                    'tags': first_row.get('Tags', ''),
                    'variants': [],
                    'images': []
                }
                
                # Collecter les variantes
                for _, row in handle_rows.iterrows():
                    variant_sku = row.get('Variant SKU', '') if 'Variant SKU' in row else ''
                    if variant_sku and variant_sku not in [v.get('sku') for v in product['variants']]:
                        variant = {
                            'sku': variant_sku,
                            'price': row.get('Variant Price', '') if 'Variant Price' in row else '',
                            'compare_at_price': row.get('Variant Compare At Price', '') if 'Variant Compare At Price' in row else '',
                            'barcode': row.get('Variant Barcode', '') if 'Variant Barcode' in row else '',
                            'inventory_qty': row.get('Variant Inventory Qty', 0) if 'Variant Inventory Qty' in row else 0,
                            'option1_name': row.get('Option1 Name', '') if 'Option1 Name' in row else '',
                            'option1_value': row.get('Option1 Value', '') if 'Option1 Value' in row else '',
                            'cost_per_item': row.get('Cost per item', '') if 'Cost per item' in row else '',
                        }
                        product['variants'].append(variant)
                
                # Published
                published_value = first_row.get('Published', 'TRUE') if 'Published' in first_row else 'TRUE'
                product['published'] = published_value.upper() == 'TRUE' if isinstance(published_value, str) else bool(published_value)
                
                # Collecter les images
                if 'Image Src' in handle_rows.columns:
                    image_srcs = handle_rows['Image Src'].dropna().unique()
                    for img_src in image_srcs:
                        if img_src and img_src not in product['images']:
                            product['images'].append(str(img_src))
                
                self.products[str(handle)] = product
            
            # Réinitialiser les sélections
            self.selected_handles.clear()
            
            # Afficher dans le WebView
            self._display_products_in_webview()
            
            # Activer le bouton d'export
            self.export_button.configure(state="normal")
            
            logger.info(f"CSV chargé: {len(self.products)} produits trouvés")
            
        except Exception as e:
            messagebox.showerror(
                "Erreur",
                f"Erreur lors du chargement du CSV:\n{str(e)}"
            )
            logger.error(f"Erreur lors du parsing CSV: {e}", exc_info=True)
    
    def _get_filtered_products(self):
        """Retourne les produits filtrés selon la recherche."""
        if not self.search_filter:
            return list(self.products.items())
        
        search_lower = self.search_filter.lower()
        filtered = []
        for handle, product in self.products.items():
            title = (product.get('title', '') or '').lower()
            vendor = (product.get('vendor', '') or '').lower()
            first_variant = product.get('variants', [{}])[0] if product.get('variants') else {}
            sku = (first_variant.get('sku', '') or '').lower()
            
            if search_lower in title or search_lower in vendor or search_lower in sku:
                filtered.append((handle, product))
        return filtered
    
    def _display_products_in_webview(self):
        """Affiche les produits dans le WebView avec pagination Python."""
        if not WEBVIEW_AVAILABLE or not self.html_frame:
            logger.error("WebView non disponible ou html_frame non initialisé")
            return
        
        try:
            # Obtenir les produits filtrés
            filtered_products = self._get_filtered_products()
            total_products = len(filtered_products)
            total_pages = max(1, (total_products + self.items_per_page - 1) // self.items_per_page)
            
            # Ajuster la page courante si nécessaire
            if self.current_page > total_pages:
                self.current_page = max(1, total_pages)
            
            # Calculer la plage de produits à afficher
            start_idx = (self.current_page - 1) * self.items_per_page
            end_idx = start_idx + self.items_per_page
            products_to_display = filtered_products[start_idx:end_idx]
            
            logger.info(f"Affichage page {self.current_page}/{total_pages}: produits {start_idx+1}-{min(end_idx, total_products)} sur {total_products}")
            
            # Générer les lignes HTML pour la page courante
            def esc(s):
                if not s:
                    return ''
                s = str(s)
                return s.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;').replace('"', '&quot;').replace("'", '&#039;')
            
            html_rows = []
            for handle, product in products_to_display:
                first_variant = product.get('variants', [{}])[0] if product.get('variants') else {}
                image_url = product.get('images', [''])[0] if product.get('images') else ''
                is_selected = handle in self.selected_handles
                
                image_html = f'<img src="{esc(image_url)}" class="product-image" onerror="this.style.display=\'none\'">' if image_url else '<div class="no-image">Pas d\'image</div>'
                checked_attr = 'checked' if is_selected else ''
                selected_class = 'selected' if is_selected else ''
                
                html_rows.append(f'''
                <tr class="{selected_class}" data-handle="{esc(handle)}">
                    <td class="checkbox-cell"><input type="checkbox" class="product-checkbox" data-handle="{esc(handle)}" {checked_attr}></td>
                    <td>{image_html}</td>
                    <td>{esc(product.get('title', ''))}</td>
                    <td>{esc(product.get('vendor', ''))}</td>
                    <td>{esc(product.get('type', ''))}</td>
                    <td>{esc(first_variant.get('price', ''))}</td>
                    <td>{esc(first_variant.get('sku', ''))}</td>
                    <td>{len(product.get('variants', []))}</td>
                </tr>
                ''')
            
            # Créer le HTML simplifié (sans JavaScript complexe, juste l'affichage)
            html_content = f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>Visualiseur CSV Shopify</title>
    <style>
        * {{ box-sizing: border-box; }}
        body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; background: #212121; color: #fff; padding: 20px; margin: 0; }}
        #productTable {{ width: 100%; border-collapse: collapse; background: #2b2b2b; }}
        #productTable thead th {{ background: #1f538d; padding: 12px; text-align: left; font-weight: 600; border-bottom: 2px solid #2563eb; }}
        #productTable tbody td {{ padding: 10px; border-bottom: 1px solid #444; vertical-align: middle; }}
        #productTable tbody tr:hover {{ background: #333; }}
        #productTable tbody tr.selected {{ background: #1f538d40; }}
        .product-image {{ width: 80px; height: 80px; object-fit: cover; border-radius: 6px; border: 2px solid #444; }}
        .no-image {{ width: 80px; height: 80px; background: #333; border-radius: 6px; display: flex; align-items: center; justify-content: center; color: #999; font-size: 11px; }}
        .checkbox-cell {{ text-align: center; width: 50px; }}
    </style>
</head>
<body>
    <h2>Page {self.current_page} sur {total_pages} - Produits {start_idx+1} à {min(end_idx, total_products)} sur {total_products} (filtre: {len(filtered_products)} produits)</h2>
    
    <table id="productTable">
        <thead>
            <tr>
                <th class="checkbox-cell">✓</th>
                <th>Image</th>
                <th>Titre</th>
                <th>Vendor</th>
                <th>Type</th>
                <th>Prix</th>
                <th>SKU</th>
                <th>Variantes</th>
            </tr>
        </thead>
        <tbody id="productTableBody">
            {''.join(html_rows)}
        </tbody>
    </table>
    
    <script>
        // Script simple pour récupérer les sélections depuis les checkboxes
        window.getSelectedHandles = function() {{
            const checkboxes = document.querySelectorAll('.product-checkbox:checked');
            const handles = [];
            checkboxes.forEach(cb => {{
                handles.push(cb.getAttribute('data-handle'));
            }});
            return handles;
        }};
    </script>
</body>
</html>"""
            
            logger.info(f"HTML généré: {len(html_content)} caractères avec {len(products_to_display)} produits")
            
            # Mettre à jour les contrôles de pagination
            self._update_pagination_controls(total_products, total_pages)
            
            # Mettre à jour le compteur de sélection
            self._update_selection_counter()
            
            # Créer un fichier HTML temporaire (tkinterweb fonctionne mieux avec des fichiers)
            import tempfile
            temp_file = tempfile.NamedTemporaryFile(mode='w', suffix='.html', delete=False, encoding='utf-8')
            temp_file.write(html_content)
            temp_file.close()
            temp_file_path = temp_file.name
            
            # Stocker le chemin pour nettoyage ultérieur
            if not hasattr(self, '_temp_html_files'):
                self._temp_html_files = []
            self._temp_html_files.append(temp_file_path)
            
            # Charger le fichier HTML dans le WebView
            logger.info(f"Chargement du fichier HTML dans le WebView: {temp_file_path}")
            self.html_frame.load_file(temp_file_path)
            
            # Forcer la mise à jour de l'affichage après un court délai
            self.after(100, lambda: (
                self.html_frame.update() if self.html_frame else None,
            self.update_idletasks()
            ))
            
            logger.info(f"HTML chargé dans le WebView pour {len(products_to_display)} produits")
            
            # Démarrer le moniteur de sélection après le chargement
            self._start_selection_monitor()
            
        except Exception as e:
            logger.error(f"Erreur lors de l'affichage dans le WebView: {e}", exc_info=True)
            import traceback
            traceback.print_exc()
            messagebox.showerror(
                "Erreur",
                f"Erreur lors de l'affichage des produits:\n{str(e)}\n\nVérifiez les logs pour plus de détails."
            )
    
    def _update_pagination_controls(self, total_products: int, total_pages: int):
        """Met à jour les contrôles de pagination."""
        if not hasattr(self, 'page_info_label'):
            return
        
        self.page_info_label.configure(
            text=f"Page {self.current_page} sur {total_pages} ({total_products} produits)"
        )
        
        self.prev_button.configure(state="normal" if self.current_page > 1 else "disabled")
        self.next_button.configure(state="normal" if self.current_page < total_pages else "disabled")
    
    def _update_selection_counter(self):
        """Met à jour le compteur de sélection."""
        if hasattr(self, 'selection_counter_webview'):
            count = len(self.selected_handles)
            total = len(self.products)
            self.selection_counter_webview.configure(
                text=f"{count} produit(s) sélectionné(s) sur {total}",
                text_color="white" if count > 0 else "gray"
            )
    
    def _on_search_webview(self):
        """Appelé quand la recherche change."""
        self.search_filter = self.search_var_webview.get()
        self.current_page = 1
        self._display_products_in_webview()
    
    def _prev_page(self):
        """Page précédente."""
        if self.current_page > 1:
            # Récupérer les sélections depuis le WebView avant de changer de page
            self._update_selections_from_webview()
            self.current_page -= 1
            self._display_products_in_webview()
    
    def _next_page(self):
        """Page suivante."""
        filtered_products = self._get_filtered_products()
        total_pages = max(1, (len(filtered_products) + self.items_per_page - 1) // self.items_per_page)
        if self.current_page < total_pages:
            # Récupérer les sélections depuis le WebView avant de changer de page
            self._update_selections_from_webview()
            self.current_page += 1
            self._display_products_in_webview()
    
    def _select_all_webview(self):
        """Sélectionne tous les produits de la page courante."""
        filtered_products = self._get_filtered_products()
        start_idx = (self.current_page - 1) * self.items_per_page
        end_idx = start_idx + self.items_per_page
        products_to_select = filtered_products[start_idx:end_idx]
        
        for handle, _ in products_to_select:
            self.selected_handles.add(handle)
        
        self._display_products_in_webview()
    
    def _deselect_all_webview(self):
        """Désélectionne tous les produits."""
        self.selected_handles.clear()
        self._display_products_in_webview()
    
    def _update_selections_from_webview(self):
        """Met à jour les sélections depuis les checkboxes du WebView."""
        if not self.html_frame:
            return
        
        try:
            js_code = "window.getSelectedHandles ? JSON.stringify(window.getSelectedHandles()) : '[]'"
            result = self.html_frame.run_javascript(js_code)
            if result:
                try:
                    if isinstance(result, str):
                        handles = json.loads(result)
                    else:
                        handles = result if isinstance(result, list) else []
                    
                    # Mettre à jour les sélections pour les produits de la page courante
                    filtered_products = self._get_filtered_products()
                    start_idx = (self.current_page - 1) * self.items_per_page
                    end_idx = start_idx + self.items_per_page
                    page_handles = {handle for handle, _ in filtered_products[start_idx:end_idx]}
                    
                    # Retirer les sélections de la page courante
                    self.selected_handles -= page_handles
                    # Ajouter les nouvelles sélections
                    for handle in handles:
                        if handle in page_handles:
                            self.selected_handles.add(handle)
                    
                except json.JSONDecodeError:
                    pass
                except Exception as e:
                    logger.debug(f"Erreur lors de la récupération des sélections: {e}")
        except Exception as e:
            logger.debug(f"Erreur lors de l'exécution du JavaScript: {e}")
    
    def _start_selection_monitor(self):
        """Démarre un moniteur pour vérifier les sélections depuis JavaScript."""
        def check_selections():
            if not self.html_frame or not self.winfo_exists():
                return
            
            try:
                js_code = """
                (function() {
                    if (typeof window.getSelectedHandles === 'function') {
                        var handles = window.getSelectedHandles();
                        return JSON.stringify(handles);
                    }
                    return '[]';
                })();
                """
                result = self.html_frame.run_javascript(js_code)
                
                if result:
                    try:
                        if isinstance(result, str):
                            handles = json.loads(result)
                        else:
                            handles = result if isinstance(result, list) else []
                        
                        # Mettre à jour les sélections seulement pour la page courante
                        filtered_products = self._get_filtered_products()
                        start_idx = (self.current_page - 1) * self.items_per_page
                        end_idx = start_idx + self.items_per_page
                        page_handles = {handle for handle, _ in filtered_products[start_idx:end_idx]}
                        
                        # Retirer les sélections de la page courante
                        self.selected_handles -= page_handles
                        # Ajouter les nouvelles sélections
                        for handle in handles:
                            if handle in page_handles:
                                self.selected_handles.add(handle)
                        
                        self._update_selection_counter()
                        
                    except json.JSONDecodeError:
                        if isinstance(result, list):
                            # Mettre à jour pour la page courante
                            filtered_products = self._get_filtered_products()
                            start_idx = (self.current_page - 1) * self.items_per_page
                            end_idx = start_idx + self.items_per_page
                            page_handles = {handle for handle, _ in filtered_products[start_idx:end_idx]}
                            self.selected_handles -= page_handles
                            for handle in result:
                                if handle in page_handles:
                                    self.selected_handles.add(handle)
                            self._update_selection_counter()
            except Exception as e:
                # Ignorer les erreurs silencieusement (le WebView peut ne pas être prêt)
                logger.debug(f"Erreur lors de la récupération des sélections: {e}")
        
        # Vérifier toutes les 500ms pour mettre à jour les sélections
        def monitor():
            if self.winfo_exists():
                check_selections()
                self.after(500, monitor)
        
        self.after(1000, monitor)  # Démarrer après 1 seconde pour laisser le temps au WebView de charger
    
    def _export_csv(self):
        """Exporte le CSV avec uniquement les produits sélectionnés."""
        # Récupérer les sélections depuis JavaScript
        if self.html_frame:
            try:
                js_code = "window.getSelectedHandles ? JSON.stringify(window.getSelectedHandles()) : '[]'"
                result = self.html_frame.run_javascript(js_code)
                if result:
                    try:
                        if isinstance(result, str):
                            handles = json.loads(result)
                        else:
                            handles = result if isinstance(result, list) else []
                        self.selected_handles = set(handles) if handles else set()
                        logger.info(f"Sélections récupérées depuis JavaScript: {len(self.selected_handles)} produits")
                    except json.JSONDecodeError as e:
                        logger.warning(f"Erreur parsing JSON des sélections: {e}, résultat: {result}")
                        if isinstance(result, list):
                            self.selected_handles = set(result)
            except Exception as e:
                logger.warning(f"Impossible de récupérer les sélections depuis JavaScript: {e}")
                # Continuer avec les sélections actuelles en mémoire
        
        if not self.selected_handles or self.df is None:
            messagebox.showwarning(
                "Avertissement",
                "Veuillez sélectionner au moins un produit."
            )
            return
        
        # Proposer un nom de fichier par défaut
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        default_filename = f"shopify_export_{timestamp}.csv"
        
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
            # Filtrer le DataFrame pour ne garder que les Handles sélectionnés
            filtered_df = self.df[self.df['Handle'].isin(self.selected_handles)].copy()
            
            # Sauvegarder
            filtered_df.to_csv(file_path, index=False, encoding='utf-8')
            
            messagebox.showinfo(
                "Succès",
                f"CSV exporté avec succès!\n\n"
                f"Fichier: {file_path}\n"
                f"Produits: {len(self.selected_handles)}\n"
                f"Lignes: {len(filtered_df)}"
            )
            
            logger.info(f"CSV exporté: {file_path} ({len(filtered_df)} lignes)")
            
        except Exception as e:
            messagebox.showerror(
                "Erreur",
                f"Erreur lors de l'export:\n{str(e)}"
            )
            logger.error(f"Erreur lors de l'export CSV: {e}", exc_info=True)

    def destroy(self):
        """Nettoie les ressources lors de la fermeture."""
        # Nettoyer les fichiers temporaires HTML
        if hasattr(self, '_temp_html_files'):
            for temp_file in self._temp_html_files:
                try:
                    if os.path.exists(temp_file):
                        os.unlink(temp_file)
                except Exception as e:
                    logger.warning(f"Impossible de supprimer le fichier temporaire {temp_file}: {e}")
        super().destroy()
