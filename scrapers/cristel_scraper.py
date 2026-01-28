"""
Wrapper pour le scraper Cristel.
"""

import sys
import os
from typing import List, Dict, Optional, Callable, Tuple
import logging
from datetime import datetime

# Ajouter le répertoire parent au path pour importer les modules
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from scrapers.base_scraper import BaseScraper
from utils.env_manager import EnvManager

# Résolution de chemins compatible PyInstaller
def resource_path(*parts):
    if getattr(sys, "frozen", False):
        base_path = sys._MEIPASS
    else:
        base_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(base_path, *parts)

# Importer les fonctions du scraper-cristel.py
import importlib.util
cristel_path = resource_path("scraper-cristel.py")
spec = importlib.util.spec_from_file_location("scraper_cristel", cristel_path)
cristel_module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(cristel_module)

logger = logging.getLogger(__name__)


class CristelScraper(BaseScraper):
    """Wrapper pour le scraper Cristel."""
    
    def __init__(self):
        super().__init__("cristel", "Cristel")
        self.requires_auth = False
        self.supports_subcategories = True
        self.env_manager = EnvManager()
        self.driver = None
        self.session = None
    
    def check_credentials(self) -> Tuple[bool, List[str]]:
        """Vérifie si les credentials Cristel sont configurés."""
        return self.env_manager.validate_credentials("cristel")
    
    def get_categories(self, callback: Optional[Callable[[str], None]] = None) -> List[Dict[str, str]]:
        """Récupère la liste des catégories principales disponibles."""
        try:
            if callback:
                callback("Connexion au site Cristel...")
            
            # Initialiser le driver
            import requests
            self.driver = cristel_module.get_selenium_driver(headless=True)
            self.session = requests.Session()
            self.session.headers.update(cristel_module.HEADERS)
            
            if callback:
                callback("Récupération des catégories...")
            
            # Récupérer les catégories principales
            categories = cristel_module.get_categories(self.driver, self.session)
            
            if callback:
                callback(f"{len(categories)} catégorie(s) trouvée(s)")
            
            return categories
        
        except Exception as e:
            logger.error(f"Erreur lors de la récupération des catégories: {e}")
            if callback:
                callback(f"Erreur: {e}")
            return []
    
    def get_subcategories(self, category: Dict[str, str], 
                         callback: Optional[Callable[[str], None]] = None) -> List[Dict[str, str]]:
        """Récupère la liste des sous-catégories pour une catégorie donnée."""
        try:
            if callback:
                callback(f"Récupération des sous-catégories pour {category['name']}...")
            
            # Initialiser le driver si nécessaire
            if not self.driver:
                import requests
                self.driver = cristel_module.get_selenium_driver(headless=True)
                self.session = requests.Session()
                self.session.headers.update(cristel_module.HEADERS)
            
            # Récupérer les sous-catégories
            subcategories = cristel_module.get_subcategories(
                self.driver, self.session, category['url'], category['name']
            )
            
            if callback:
                callback(f"{len(subcategories)} sous-catégorie(s) trouvée(s)")
            
            return subcategories
        
        except Exception as e:
            logger.error(f"Erreur lors de la récupération des sous-catégories: {e}")
            if callback:
                callback(f"Erreur: {e}")
            return []
    
    def scrape(self, categories: List[Dict[str, str]], 
               subcategories: Optional[List[Dict[str, str]]] = None,
               options: Optional[Dict] = None,
               progress_callback: Optional[Callable[[str, int, int], None]] = None,
               log_callback: Optional[Callable[[str], None]] = None,
               cancel_check: Optional[Callable[[], bool]] = None) -> Tuple[bool, Optional[str], Optional[str]]:
        """
        Lance le scraping des produits avec les nouveaux scripts modulaires :
        cristel/scraper-subcategory.py (collect → process → generate-csv)
        """
        import subprocess
        import glob
        
        # Vérifier l'annulation avant de commencer
        if cancel_check and cancel_check():
            if log_callback:
                log_callback("Annulation demandée par l'utilisateur...")
            logger.info("Annulation demandée par l'utilisateur")
            return False, None, "Annulation demandée par l'utilisateur"
        
        try:
            from datetime import datetime
            import time
            
            options = options or {}
            limit = options.get('limit')
            output_file = options.get('output')
            headless = options.get('headless', True)
            
            # Enregistrer l'heure de début pour ne chercher que les fichiers créés après
            start_time = time.time()
            
            if log_callback:
                log_callback("Démarrage du scraping Cristel avec les scripts modulaires...")
            
            # Traiter chaque sous-catégorie sélectionnée
            if not subcategories:
                if log_callback:
                    log_callback("Aucune sous-catégorie sélectionnée")
                return False, None, "Aucune sous-catégorie sélectionnée"
            
            total_subcategories = len(subcategories)
            csv_files = []
            
            for idx, subcategory in enumerate(subcategories, 1):
                # Vérifier l'annulation
                if cancel_check and cancel_check():
                    if log_callback:
                        log_callback("Annulation demandée par l'utilisateur...")
                    return False, None, "Annulation demandée par l'utilisateur"
                
                # Debug : afficher la structure de la sous-catégorie
                logger.info(f"Sous-catégorie reçue: {subcategory}")
                
                subcategory_name = subcategory.get('name', '')
                subcategory_url = subcategory.get('url', '')
                # Essayer 'parent' au lieu de 'category'
                category_name = subcategory.get('parent', subcategory.get('category', ''))
                
                # Vérifier que l'URL est présente
                if not subcategory_url:
                    error_msg = f"URL manquante pour la sous-catégorie {subcategory_name}"
                    logger.error(error_msg)
                    if log_callback:
                        log_callback(f"❌ {error_msg}")
                        log_callback(f"Structure reçue: {subcategory}")
                    continue
                
                if log_callback:
                    log_callback(f"\n{'='*60}")
                    log_callback(f"Sous-catégorie {idx}/{total_subcategories}: {subcategory_name}")
                    log_callback(f"URL: {subcategory_url}")
                    log_callback(f"{'='*60}\n")
                
                if progress_callback:
                    progress_callback(f"Sous-catégorie: {subcategory_name}", idx - 1, total_subcategories)
                
                # Construire la commande pour scraper-subcategory.py
                # Ne pas générer de CSV pour chaque sous-catégorie, on le fera à la fin
                cmd = [
                    sys.executable,
                    'cristel/scraper-subcategory.py',
                    '--url', subcategory_url,
                    '--category', category_name,
                    '--subcategory', subcategory_name,
                    '--skip-csv'  # Ne pas générer de CSV maintenant, on le fera à la fin
                ]
                
                if limit:
                    cmd.extend(['--limit', str(limit)])
                
                if not headless:
                    cmd.append('--no-headless')
                
                # Exécuter le script avec capture des logs
                process = subprocess.Popen(
                    cmd,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                    text=True,
                    bufsize=1,
                    universal_newlines=True
                )
                
                # Lire les logs en temps réel
                for line in iter(process.stdout.readline, ''):
                    if cancel_check and cancel_check():
                        process.terminate()
                        if log_callback:
                            log_callback("Annulation demandée par l'utilisateur...")
                        return False, None, "Annulation demandée par l'utilisateur"
                    
                    line_stripped = line.strip()
                    if line_stripped:
                        if log_callback:
                            log_callback(line_stripped)
                
                process.wait()
                
                if process.returncode != 0:
                    error_msg = f"Le script a échoué pour {subcategory_name} (code: {process.returncode})"
                    if log_callback:
                        log_callback(f"❌ {error_msg}")
                    # Continuer avec les autres sous-catégories
                    continue
            
            # Après avoir traité toutes les sous-catégories, générer un seul CSV avec toutes
            if log_callback:
                log_callback(f"\n{'='*60}")
                log_callback(f"Génération du CSV final avec toutes les sous-catégories...")
                log_callback(f"{'='*60}\n")
            
            try:
                # Importer le module de génération CSV
                generate_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "cristel", "scraper-generate-csv.py")
                generate_spec = importlib.util.spec_from_file_location("cristel_generate_csv", generate_path)
                generate_module = importlib.util.module_from_spec(generate_spec)
                generate_spec.loader.exec_module(generate_module)
                generate_csv_from_db = generate_module.generate_csv_from_db
                
                from utils.app_config import get_cristel_db_path
                db_path = get_cristel_db_path()
                
                # Récupérer toutes les sous-catégories sélectionnées
                selected_subcategories = [subcat.get('name', '') for subcat in subcategories if subcat.get('name')]
                
                # Générer le CSV avec toutes les sous-catégories
                output_file = generate_csv_from_db(
                    output_file=None,  # Laisser le script générer le nom
                    output_db=db_path,
                    supplier='cristel',
                    categories=None,  # Pas de filtrage par catégorie principale
                    subcategories=selected_subcategories if len(selected_subcategories) > 1 else None,
                    subcategory=selected_subcategories[0] if len(selected_subcategories) == 1 else None
                )
                
                if output_file and os.path.exists(output_file):
                    if log_callback:
                        log_callback(f"\n✅ Scraping terminé avec succès !")
                        log_callback(f"📄 Fichier CSV généré : {output_file}")
                    return True, output_file, None
                else:
                    if log_callback:
                        log_callback("\n⚠️  Aucun fichier CSV n'a été généré")
                    return False, None, "Aucun fichier CSV généré"
                    
            except Exception as e:
                error_msg = f"Erreur lors de la génération du CSV final: {e}"
                logger.error(error_msg, exc_info=True)
                if log_callback:
                    log_callback(f"\n❌ {error_msg}")
                return False, None, error_msg
        
        except Exception as e:
            error_msg = f"Erreur lors du scraping: {e}"
            logger.error(error_msg, exc_info=True)
            if log_callback:
                log_callback(f"\n❌ {error_msg}")
            return False, None, error_msg
        
        finally:
            # Nettoyer le driver si nécessaire
            if hasattr(self, 'driver') and self.driver:
                try:
                    self.driver.quit()
                except:
                    pass
                self.driver = None

