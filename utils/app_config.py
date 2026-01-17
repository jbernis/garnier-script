"""
Gestion de la configuration de l'application.
"""

import json
import os
import logging

logger = logging.getLogger(__name__)

CONFIG_FILE = "app_config.json"
DEFAULT_CONFIG = {
    "delete_outputs_on_close": False,  # Par défaut, ne pas supprimer
}


def load_config() -> dict:
    """Charge la configuration de l'application."""
    if not os.path.exists(CONFIG_FILE):
        # Créer le fichier avec la configuration par défaut
        save_config(DEFAULT_CONFIG)
        return DEFAULT_CONFIG.copy()
    
    try:
        with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
            config = json.load(f)
        # Fusionner avec la config par défaut pour les nouvelles clés
        merged_config = DEFAULT_CONFIG.copy()
        merged_config.update(config)
        return merged_config
    except Exception as e:
        logger.error(f"Erreur lors du chargement de la configuration: {e}")
        return DEFAULT_CONFIG.copy()


def save_config(config: dict):
    """Sauvegarde la configuration de l'application."""
    try:
        with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
            json.dump(config, f, indent=2, ensure_ascii=False)
        logger.info("Configuration sauvegardée")
    except Exception as e:
        logger.error(f"Erreur lors de la sauvegarde de la configuration: {e}")


def get_config(key: str, default=None):
    """Récupère une valeur de configuration."""
    config = load_config()
    return config.get(key, default)


def set_config(key: str, value):
    """Définit une valeur de configuration."""
    config = load_config()
    config[key] = value
    save_config(config)


def get_supplier_db_path(supplier: str) -> str:
    """Retourne automatiquement le chemin de la base de données pour un fournisseur donné.
    
    Format automatique: database/{supplier}_products.db
    
    Args:
        supplier: Nom du fournisseur ('garnier', 'cristel', 'artiga', etc.)
    
    Returns:
        Chemin de la base de données au format database/{supplier}_products.db
    
    Exemples:
        get_supplier_db_path('garnier') → 'database/garnier_products.db'
        get_supplier_db_path('cristel') → 'database/cristel_products.db'
        get_supplier_db_path('artiga') → 'database/artiga_products.db'
    """
    supplier_lower = supplier.lower().strip()
    return f"database/{supplier_lower}_products.db"


def get_garnier_db_path() -> str:
    """Retourne le chemin de la base de données Garnier.
    
    Format automatique: database/garnier_products.db
    """
    return get_supplier_db_path('garnier')


def get_cristel_db_path() -> str:
    """Retourne le chemin de la base de données Cristel.
    
    Format automatique: database/cristel_products.db
    """
    return get_supplier_db_path('cristel')


def get_artiga_db_path() -> str:
    """Retourne le chemin de la base de données Artiga.
    
    Format automatique: database/artiga_products.db
    """
    return get_supplier_db_path('artiga')

