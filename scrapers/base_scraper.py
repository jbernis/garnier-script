"""
Classe abstraite de base pour tous les scrapers.
"""

from abc import ABC, abstractmethod
from typing import List, Dict, Optional, Callable, Tuple
import logging

logger = logging.getLogger(__name__)


class BaseScraper(ABC):
    """Classe abstraite pour tous les scrapers."""
    
    def __init__(self, name: str, display_name: str):
        """
        Initialise le scraper.
        
        Args:
            name: Nom technique du scraper (ex: "garnier")
            display_name: Nom d'affichage (ex: "Garnier-Thiebaut")
        """
        self.name = name
        self.display_name = display_name
        self.requires_auth = False
        self.supports_subcategories = False
    
    @abstractmethod
    def check_credentials(self) -> Tuple[bool, List[str]]:
        """
        Vérifie si les credentials nécessaires sont configurés.
        
        Returns:
            Tuple (is_valid, list_of_errors)
        """
        pass
    
    @abstractmethod
    def get_categories(self, callback: Optional[Callable[[str], None]] = None) -> List[Dict[str, str]]:
        """
        Récupère la liste des catégories disponibles.
        
        Args:
            callback: Fonction de callback pour les messages de progression
            
        Returns:
            Liste de dictionnaires avec 'name' et 'url'
        """
        pass
    
    def get_subcategories(self, category: Dict[str, str], 
                         callback: Optional[Callable[[str], None]] = None) -> List[Dict[str, str]]:
        """
        Récupère la liste des sous-catégories pour une catégorie donnée.
        
        Par défaut, retourne une liste vide. Les scrapers qui supportent
        les sous-catégories doivent surcharger cette méthode.
        
        Args:
            category: Dictionnaire avec 'name' et 'url' de la catégorie
            callback: Fonction de callback pour les messages de progression
            
        Returns:
            Liste de dictionnaires avec 'name' et 'url'
        """
        return []
    
    @abstractmethod
    def scrape(self, categories: List[Dict[str, str]], 
               subcategories: Optional[List[Dict[str, str]]] = None,
               options: Optional[Dict] = None,
               progress_callback: Optional[Callable[[str, int, int], None]] = None,
               log_callback: Optional[Callable[[str], None]] = None,
               cancel_check: Optional[Callable[[], bool]] = None) -> Tuple[bool, Optional[str], Optional[str]]:
        """
        Lance le scraping des produits.
        
        Args:
            categories: Liste des catégories à scraper
            subcategories: Liste des sous-catégories (optionnel)
            options: Options supplémentaires (limit, output, headless, etc.)
            progress_callback: Callback pour la progression (message, current, total)
            log_callback: Callback pour les logs (message)
            cancel_check: Callback pour vérifier si l'annulation a été demandée (retourne True si annulé)
            
        Returns:
            Tuple (success, output_file_path, error_message)
        """
        pass
    
    def get_display_name(self) -> str:
        """Retourne le nom d'affichage du scraper."""
        return self.display_name
    
    def get_name(self) -> str:
        """Retourne le nom technique du scraper."""
        return self.name
    
    def requires_authentication(self) -> bool:
        """Indique si ce scraper nécessite une authentification."""
        return self.requires_auth
    
    def supports_subcategories(self) -> bool:
        """Indique si ce scraper supporte les sous-catégories."""
        return self.supports_subcategories

    def get_output_dir(self) -> str:
        """
        Retourne le répertoire de sortie automatique basé sur le nom du fournisseur.
        Format: outputs/{nom_du_fournisseur}
        
        Returns:
            Chemin du répertoire de sortie (ex: "outputs/garnier")
        """
        import os
        output_dir = os.path.join("outputs", self.name)
        return output_dir

