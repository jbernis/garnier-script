#!/usr/bin/env python3
"""
Configuration dédiée au générateur CSV Shopify.
Séparée de csv_config.json pour éviter les conflits avec l'import.
"""

import json
import os
from typing import Dict, List, Optional
from pathlib import Path
import sys

# Ajouter le répertoire parent au path pour importer csv_config
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from csv_config import SHOPIFY_ALL_COLUMNS, HANDLE_OPTIONS

# Fichier de configuration du générateur
CONFIG_FILE = Path(__file__).parent / 'csv_generator_config.json'


class CSVGeneratorConfig:
    """Gestionnaire de configuration pour le générateur CSV."""
    
    def __init__(self):
        self.config_file = CONFIG_FILE
        self.config = self._load_config()
    
    def reload_config(self):
        """Recharge la configuration depuis le fichier."""
        self.config = self._load_config()
    
    def _load_config(self) -> Dict:
        """Charge la configuration depuis le fichier JSON."""
        if self.config_file.exists():
            try:
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    config = json.load(f)
                return config
            except Exception as e:
                print(f"Erreur lors du chargement de la configuration générateur: {e}")
                return {}
        else:
            # Fichier n'existe pas encore, retourner une config vide
            return {}
    
    def _save_config(self):
        """Sauvegarde la configuration dans le fichier JSON."""
        try:
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(self.config, f, indent=2, ensure_ascii=False)
        except Exception as e:
            print(f"Erreur lors de la sauvegarde de la configuration générateur: {e}")
    
    def get_columns(self, supplier: str) -> List[str]:
        """
        Retourne la liste des colonnes pour un fournisseur donné.
        Si pas de configuration sauvegardée, retourne toutes les colonnes par défaut.
        """
        supplier = supplier.lower()
        if supplier in self.config and 'columns' in self.config[supplier]:
            return self.config[supplier]['columns'].copy()
        # Par défaut, retourner toutes les colonnes
        return SHOPIFY_ALL_COLUMNS.copy()
    
    def set_columns(self, supplier: str, columns: List[str]):
        """Définit les colonnes pour un fournisseur donné."""
        supplier = supplier.lower()
        if supplier not in self.config:
            self.config[supplier] = {}
        self.config[supplier]['columns'] = columns.copy()
        self._save_config()
    
    def get_handle_source(self, supplier: str) -> str:
        """
        Retourne la source du Handle pour un fournisseur donné.
        Par défaut: 'barcode'
        """
        supplier = supplier.lower()
        if supplier in self.config and 'handle_source' in self.config[supplier]:
            return self.config[supplier]['handle_source']
        return 'barcode'
    
    def set_handle_source(self, supplier: str, handle_source: str):
        """Définit la source du Handle pour un fournisseur donné."""
        supplier = supplier.lower()
        if handle_source not in HANDLE_OPTIONS:
            raise ValueError(f"Source Handle invalide: {handle_source}. Options: {list(HANDLE_OPTIONS.keys())}")
        if supplier not in self.config:
            self.config[supplier] = {}
        self.config[supplier]['handle_source'] = handle_source
        self._save_config()
    
    def get_vendor(self, supplier: str) -> str:
        """
        Retourne le nom du vendor pour un fournisseur donné.
        Par défaut: nom du fournisseur capitalisé
        """
        supplier = supplier.lower()
        if supplier in self.config and 'vendor' in self.config[supplier]:
            return self.config[supplier]['vendor']
        # Par défaut, capitaliser le nom du fournisseur
        return supplier.capitalize()
    
    def set_vendor(self, supplier: str, vendor: str):
        """Définit le nom du vendor pour un fournisseur donné."""
        supplier = supplier.lower()
        if supplier not in self.config:
            self.config[supplier] = {}
        self.config[supplier]['vendor'] = vendor
        self._save_config()
    
    def get_location(self, supplier: str) -> str:
        """
        Retourne l'emplacement (location) pour un fournisseur donné.
        Par défaut: "Dropshipping {Fournisseur}"
        """
        supplier = supplier.lower()
        if supplier in self.config and 'location' in self.config[supplier]:
            return self.config[supplier]['location']
        # Par défaut, "Dropshipping {Fournisseur}"
        return f"Dropshipping {supplier.capitalize()}"
    
    def set_location(self, supplier: str, location: str):
        """Définit l'emplacement (location) pour un fournisseur donné."""
        supplier = supplier.lower()
        if supplier not in self.config:
            self.config[supplier] = {}
        self.config[supplier]['location'] = location
        self._save_config()
    
    def get_categories(self, supplier: str) -> Optional[List[str]]:
        """
        Retourne les catégories sauvegardées pour un fournisseur.
        Retourne None si aucune catégorie n'est sauvegardée.
        """
        supplier = supplier.lower()
        if supplier in self.config and 'categories' in self.config[supplier]:
            return self.config[supplier]['categories'].copy()
        return None
    
    def get_subcategories(self, supplier: str) -> Optional[List[str]]:
        """
        Retourne les sous-catégories sauvegardées pour un fournisseur.
        Retourne None si aucune sous-catégorie n'est sauvegardée.
        """
        supplier = supplier.lower()
        if supplier in self.config and 'subcategories' in self.config[supplier]:
            return self.config[supplier]['subcategories'].copy()
        return None
    
    def set_categories(self, supplier: str, categories: Optional[List[str]], 
                      subcategories: Optional[List[str]] = None):
        """
        Sauvegarde les catégories et sous-catégories pour un fournisseur.
        
        Args:
            supplier: Nom du fournisseur
            categories: Liste des catégories (None = toutes)
            subcategories: Liste des sous-catégories (optionnel, pour Artiga/Cristel)
        """
        supplier = supplier.lower()
        if supplier not in self.config:
            self.config[supplier] = {}
        
        # Sauvegarder None comme null dans le JSON pour "toutes les catégories"
        self.config[supplier]['categories'] = categories
        
        if subcategories is not None:
            self.config[supplier]['subcategories'] = subcategories
        elif 'subcategories' in self.config[supplier]:
            # Supprimer les sous-catégories si None
            del self.config[supplier]['subcategories']
        
        self._save_config()
    
    def save_full_config(self, supplier: str, columns: List[str], 
                        handle_source: str, vendor: str,
                        location: Optional[str] = None,
                        categories: Optional[List[str]] = None,
                        subcategories: Optional[List[str]] = None):
        """
        Sauvegarde une configuration complète pour un fournisseur.
        
        Args:
            supplier: Nom du fournisseur
            columns: Liste des colonnes CSV
            handle_source: Source du handle ('barcode', 'sku', 'title', 'custom')
            vendor: Nom du vendor
            location: Emplacement (location) pour le stock
            categories: Liste des catégories (None = toutes)
            subcategories: Liste des sous-catégories (optionnel)
        """
        supplier = supplier.lower()
        self.config[supplier] = {
            'columns': columns.copy(),
            'handle_source': handle_source,
            'vendor': vendor,
            'location': location if location is not None else f"Dropshipping {supplier.capitalize()}"
        }
        
        if categories is not None:
            self.config[supplier]['categories'] = categories
        
        if subcategories is not None:
            self.config[supplier]['subcategories'] = subcategories
        
        self._save_config()
    
    def has_config(self, supplier: str) -> bool:
        """Vérifie si une configuration existe pour un fournisseur."""
        supplier = supplier.lower()
        return supplier in self.config and bool(self.config[supplier])


# Instance globale de configuration
_csv_generator_config_instance = None

def get_csv_generator_config() -> CSVGeneratorConfig:
    """Retourne l'instance globale de configuration du générateur."""
    global _csv_generator_config_instance
    if _csv_generator_config_instance is None:
        _csv_generator_config_instance = CSVGeneratorConfig()
    return _csv_generator_config_instance
