#!/usr/bin/env python3
"""
Configuration centralisée pour les champs CSV Shopify.
Permet de configurer les champs à inclure/exclure pour chaque fournisseur.
"""

import json
import os
from typing import Dict, List, Optional
from pathlib import Path

# Tous les champs Shopify disponibles
SHOPIFY_ALL_COLUMNS = [
    'Handle',
    'Title',
    'Body (HTML)',
    'Vendor',
    'Product Category',
    'Type',
    'Tags',
    'Published',
    'Option1 Name',
    'Option1 Value',
    'Option2 Name',
    'Option2 Value',
    'Option3 Name',
    'Option3 Value',
    'Variant SKU',
    'Variant Grams',
    'Variant Inventory Tracker',
    'Variant Inventory Qty',
    'Variant Inventory Policy',
    'Variant Fulfillment Service',
    'Variant Price',
    'Variant Compare At Price',
    'Variant Requires Shipping',
    'Variant Taxable',
    'Variant Barcode',
    'Image Src',
    'Image Position',
    'Image Alt Text',
    'Gift Card',
    'SEO Title',
    'SEO Description',
    'Google Shopping / Google Product Category',
    'Google Shopping / Gender',
    'Google Shopping / Age Group',
    'Google Shopping / MPN',
    'Google Shopping / Condition',
    'Google Shopping / Custom Product',
    'Variant Image',
    'Variant Weight Unit',
    'Variant Tax Code',
    'Cost per item',
    'Included / United States',
    'Price / United States',
    'Compare At Price / United States',
    'Included / International',
    'Price / International',
    'Compare At Price / International',
    'Status',
    'location',
    'On hand (new)',
    'On hand (current)',
]

# Options pour le Handle
HANDLE_OPTIONS = {
    'barcode': 'Utiliser le Variant Barcode comme Handle',
    'title': 'Utiliser le Title slugifié comme Handle',
    'sku': 'Utiliser le Variant SKU comme Handle',
    'custom': 'Utiliser une fonction personnalisée',
}

# Configuration par défaut pour chaque fournisseur
DEFAULT_CONFIG = {
    'garnier': {
        'columns': SHOPIFY_ALL_COLUMNS.copy(),  # Tous les champs par défaut
        'handle_source': 'barcode',  # Par défaut: barcode
        'vendor': 'Garnier-Thiebaut',
    },
    'artiga': {
        'columns': SHOPIFY_ALL_COLUMNS.copy(),
        'handle_source': 'barcode',
        'vendor': 'Artiga',
    },
    'cristel': {
        'columns': SHOPIFY_ALL_COLUMNS.copy(),
        'handle_source': 'barcode',
        'vendor': 'Cristel',
    },
}

CONFIG_FILE = Path(__file__).parent / 'csv_config.json'


class CSVConfig:
    """Gestionnaire de configuration pour les champs CSV."""
    
    def __init__(self):
        self.config_file = CONFIG_FILE
        self.config = self._load_config()
    
    def reload_config(self):
        """Recharge la configuration depuis le fichier."""
        self.config = self._load_config()
    
    def _load_config(self) -> Dict:
        """Charge la configuration depuis le fichier JSON ou utilise les valeurs par défaut."""
        if self.config_file.exists():
            try:
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    config = json.load(f)
                # S'assurer que tous les fournisseurs ont une configuration
                for supplier in DEFAULT_CONFIG.keys():
                    if supplier not in config:
                        config[supplier] = DEFAULT_CONFIG[supplier].copy()
                    # S'assurer que les colonnes sont présentes
                    if 'columns' not in config[supplier]:
                        config[supplier]['columns'] = SHOPIFY_ALL_COLUMNS.copy()
                    # S'assurer que handle_source est présent
                    if 'handle_source' not in config[supplier]:
                        config[supplier]['handle_source'] = 'barcode'
                # S'assurer que "commun" existe (mais ne pas l'initialiser si pas présent)
                # "commun" sera créé quand l'utilisateur le configure
                return config
            except Exception as e:
                print(f"Erreur lors du chargement de la configuration: {e}")
                print("Utilisation de la configuration par défaut.")
                return DEFAULT_CONFIG.copy()
        else:
            # Créer le fichier avec les valeurs par défaut
            self._save_config(DEFAULT_CONFIG.copy())
            return DEFAULT_CONFIG.copy()
    
    def _save_config(self, config: Dict):
        """Sauvegarde la configuration dans le fichier JSON."""
        try:
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(config, f, indent=2, ensure_ascii=False)
        except Exception as e:
            print(f"Erreur lors de la sauvegarde de la configuration: {e}")
    
    def get_all_suppliers(self) -> List[str]:
        """Retourne la liste de tous les fournisseurs configurés."""
        suppliers = list(self.config.keys())
        # Ajouter "commun" en premier si pas déjà présent
        if 'commun' not in suppliers:
            suppliers.insert(0, 'commun')
        return suppliers
    
    def _get_effective_config(self, supplier: str) -> Dict:
        """Retourne la configuration effective pour un fournisseur (spécifique ou commun)."""
        supplier = supplier.lower()
        # Si le fournisseur a sa propre configuration, l'utiliser
        if supplier in self.config and supplier != 'commun':
            return {
                'columns': self.config[supplier].get('columns', SHOPIFY_ALL_COLUMNS.copy()),
                'handle_source': self.config[supplier].get('handle_source', 'barcode'),
                'vendor': self.config[supplier].get('vendor', supplier.capitalize())
            }
        # Sinon, utiliser "commun" s'il existe
        if 'commun' in self.config:
            return {
                'columns': self.config['commun'].get('columns', SHOPIFY_ALL_COLUMNS.copy()),
                'handle_source': self.config['commun'].get('handle_source', 'barcode'),
                'vendor': 'Commun'
            }
        # Sinon, utiliser la configuration par défaut
        if supplier in DEFAULT_CONFIG:
            return DEFAULT_CONFIG[supplier].copy()
        return {
            'columns': SHOPIFY_ALL_COLUMNS.copy(),
            'handle_source': 'barcode',
            'vendor': supplier.capitalize()
        }
    
    def get_columns(self, supplier: str) -> List[str]:
        """Retourne la liste des colonnes pour un fournisseur donné."""
        supplier = supplier.lower()
        if supplier == 'commun':
            # Retourner la configuration "commun" si elle existe, sinon intersection actuelle
            if 'commun' in self.config:
                return self.config['commun'].get('columns', SHOPIFY_ALL_COLUMNS.copy())
            # Si "commun" n'existe pas encore, retourner l'intersection actuelle pour affichage
            return self._get_common_intersection()['columns']
        # Pour un fournisseur spécifique, utiliser sa config ou "commun" ou défaut
        return self._get_effective_config(supplier)['columns']
    
    def _get_common_intersection(self) -> Dict:
        """Calcule l'intersection des configurations effectives de tous les fournisseurs."""
        suppliers = list(DEFAULT_CONFIG.keys())
        if not suppliers:
            return {
                'columns': SHOPIFY_ALL_COLUMNS.copy(),
                'handle_source': 'barcode'
            }
        
        # Intersection des colonnes
        common_columns = set(self._get_effective_config(suppliers[0])['columns'])
        for supplier in suppliers[1:]:
            common_columns &= set(self._get_effective_config(supplier)['columns'])
        
        # Source Handle commune
        handle_sources = [self._get_effective_config(s)['handle_source'] for s in suppliers]
        common_handle = handle_sources[0] if len(set(handle_sources)) == 1 else 'barcode'
        
        # Trier les colonnes
        sorted_columns = sorted(
            list(common_columns),
            key=lambda x: SHOPIFY_ALL_COLUMNS.index(x) if x in SHOPIFY_ALL_COLUMNS else 999
        )
        
        return {
            'columns': sorted_columns,
            'handle_source': common_handle
        }
    
    def set_columns(self, supplier: str, columns: List[str]):
        """Définit les colonnes pour un fournisseur donné."""
        supplier = supplier.lower()
        if supplier == 'commun':
            # Sauvegarder "commun" dans le JSON
            if 'commun' not in self.config:
                self.config['commun'] = {}
            self.config['commun']['columns'] = columns.copy()
            self._save_config(self.config)
            return
        # Pour un fournisseur spécifique, sauvegarder sa configuration (elle prend priorité sur "commun")
        if supplier not in self.config:
            self.config[supplier] = DEFAULT_CONFIG.get(supplier, {}).copy()
        self.config[supplier]['columns'] = columns.copy()
        self._save_config(self.config)
    
    def add_column(self, supplier: str, column: str):
        """Ajoute une colonne pour un fournisseur donné."""
        columns = self.get_columns(supplier)
        if column not in columns:
            columns.append(column)
            self.set_columns(supplier, columns)
    
    def remove_column(self, supplier: str, column: str):
        """Retire une colonne pour un fournisseur donné."""
        columns = self.get_columns(supplier)
        if column in columns:
            columns.remove(column)
            self.set_columns(supplier, columns)
    
    def get_handle_source(self, supplier: str) -> str:
        """Retourne la source du Handle pour un fournisseur donné."""
        supplier = supplier.lower()
        if supplier == 'commun':
            # Retourner la configuration "commun" si elle existe
            if 'commun' in self.config:
                return self.config['commun'].get('handle_source', 'barcode')
            # Sinon, retourner l'intersection
            return self._get_common_intersection()['handle_source']
        # Pour un fournisseur spécifique, utiliser sa config ou "commun" ou défaut
        return self._get_effective_config(supplier)['handle_source']
    
    def set_handle_source(self, supplier: str, handle_source: str):
        """Définit la source du Handle pour un fournisseur donné."""
        supplier = supplier.lower()
        if handle_source not in HANDLE_OPTIONS:
            raise ValueError(f"Source Handle invalide: {handle_source}. Options: {list(HANDLE_OPTIONS.keys())}")
        if supplier == 'commun':
            # Sauvegarder "commun" dans le JSON
            if 'commun' not in self.config:
                self.config['commun'] = {}
            self.config['commun']['handle_source'] = handle_source
            self._save_config(self.config)
            return
        # Pour un fournisseur spécifique, sauvegarder sa configuration (elle prend priorité sur "commun")
        if supplier not in self.config:
            self.config[supplier] = DEFAULT_CONFIG.get(supplier, {}).copy()
        self.config[supplier]['handle_source'] = handle_source
        self._save_config(self.config)
    
    def get_vendor(self, supplier: str) -> str:
        """Retourne le nom du vendor pour un fournisseur donné."""
        supplier = supplier.lower()
        if supplier == 'commun':
            return 'Commun (s\'applique à tous les fournisseurs)'
        return self._get_effective_config(supplier)['vendor']
    
    def reset_to_default(self, supplier: Optional[str] = None):
        """Réinitialise la configuration à ses valeurs par défaut."""
        if supplier:
            supplier = supplier.lower()
            if supplier == 'commun':
                # Réinitialiser "commun" = appliquer DEFAULT_CONFIG à tous les fournisseurs
                # Supprimer "commun" du JSON
                if 'commun' in self.config:
                    del self.config['commun']
                # Appliquer DEFAULT_CONFIG à tous les fournisseurs
                for s in DEFAULT_CONFIG.keys():
                    self.config[s] = DEFAULT_CONFIG[s].copy()
                self._save_config(self.config)
            elif supplier in DEFAULT_CONFIG:
                self.config[supplier] = DEFAULT_CONFIG[supplier].copy()
                self._save_config(self.config)
            else:
                self.config[supplier] = {
                    'columns': SHOPIFY_ALL_COLUMNS.copy(),
                    'handle_source': 'barcode',
                    'vendor': supplier.capitalize(),
                }
                self._save_config(self.config)
        else:
            self.config = DEFAULT_CONFIG.copy()
            # Supprimer "commun" si présent
            if 'commun' in self.config:
                del self.config['commun']
        self._save_config(self.config)


# Instance globale de configuration
_csv_config_instance = None

def get_csv_config() -> CSVConfig:
    """Retourne l'instance globale de configuration."""
    global _csv_config_instance
    if _csv_config_instance is None:
        _csv_config_instance = CSVConfig()
    return _csv_config_instance

