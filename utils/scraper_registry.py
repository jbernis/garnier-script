"""
Registre des scrapers disponibles.
"""

from typing import Dict, List, Optional
import logging

logger = logging.getLogger(__name__)


class ScraperRegistry:
    """Registre centralisé des scrapers disponibles."""
    
    _instance = None
    _scrapers: Dict[str, 'BaseScraper'] = {}
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self):
        if not hasattr(self, '_initialized'):
            self._initialized = True
            self._load_scrapers()
    
    def _load_scrapers(self):
        """Charge tous les scrapers disponibles."""
        try:
            from scrapers.garnier_scraper import GarnierScraper
            self.register(GarnierScraper())
        except Exception as e:
            logger.warning(f"Impossible de charger GarnierScraper: {e}")
        
        try:
            from scrapers.artiga_scraper import ArtigaScraper
            self.register(ArtigaScraper())
        except Exception as e:
            logger.warning(f"Impossible de charger ArtigaScraper: {e}")
        
        try:
            from scrapers.cristel_scraper import CristelScraper
            self.register(CristelScraper())
        except Exception as e:
            logger.warning(f"Impossible de charger CristelScraper: {e}")
    
    def register(self, scraper: 'BaseScraper'):
        """Enregistre un scraper."""
        self._scrapers[scraper.get_name()] = scraper
        logger.info(f"Scraper enregistré: {scraper.get_display_name()}")
    
    def get(self, name: str) -> Optional['BaseScraper']:
        """Récupère un scraper par son nom."""
        return self._scrapers.get(name)
    
    def get_all(self) -> List['BaseScraper']:
        """Récupère tous les scrapers enregistrés."""
        return list(self._scrapers.values())
    
    def get_names(self) -> List[str]:
        """Récupère les noms de tous les scrapers."""
        return list(self._scrapers.keys())
    
    def get_display_names(self) -> Dict[str, str]:
        """Récupère un dictionnaire {nom_technique: nom_affichage}."""
        return {name: scraper.get_display_name() for name, scraper in self._scrapers.items()}


# Instance globale
registry = ScraperRegistry()

