"""
Wrapper pour le scraper Artiga.
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

# Importer les fonctions du scraper-artiga.py
import importlib.util
artiga_path = resource_path("scraper-artiga.py")
spec = importlib.util.spec_from_file_location("scraper_artiga", artiga_path)
artiga_module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(artiga_module)

logger = logging.getLogger(__name__)


class ArtigaScraper(BaseScraper):
    """Wrapper pour le scraper Artiga."""
    
    def __init__(self):
        super().__init__("artiga", "Artiga")
        self.requires_auth = False
        self.supports_subcategories = True
        self.env_manager = EnvManager()
        self.driver = None
        self.session = None
    
    def check_credentials(self) -> Tuple[bool, List[str]]:
        """Vérifie si les credentials Artiga sont configurés."""
        return self.env_manager.validate_credentials("artiga")
    
    def get_categories(self, callback: Optional[Callable[[str], None]] = None) -> List[Dict[str, str]]:
        """Récupère la liste des catégories disponibles."""
        try:
            if callback:
                callback("Connexion au site Artiga...")
            
            # Initialiser le driver
            import requests
            self.driver = artiga_module.get_selenium_driver(headless=True)
            self.session = requests.Session()
            self.session.headers.update(artiga_module.HEADERS)
            
            if callback:
                callback("Récupération des catégories...")
            
            # Récupérer les catégories
            categories = artiga_module.get_categories(self.driver, self.session)
            
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
                self.driver = artiga_module.get_selenium_driver(headless=True)
                self.session = requests.Session()
                self.session.headers.update(artiga_module.HEADERS)
            
            # Récupérer les sous-catégories
            subcategories = artiga_module.get_subcategories(
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
        """Lance le scraping des produits."""
        # Vérifier l'annulation avant de commencer
        if cancel_check and cancel_check():
            if log_callback:
                log_callback("Annulation demandée par l'utilisateur...")
            logger.info("Annulation demandée par l'utilisateur")
            return False, None, "Annulation demandée par l'utilisateur"
        return self._scrape_impl(categories, subcategories, options, progress_callback, log_callback, cancel_check)
    
    def _scrape_impl(self, categories: List[Dict[str, str]], 
               subcategories: Optional[List[Dict[str, str]]] = None,
               options: Optional[Dict] = None,
               progress_callback: Optional[Callable[[str, int, int], None]] = None,
               log_callback: Optional[Callable[[str], None]] = None,
               cancel_check: Optional[Callable[[], bool]] = None) -> Tuple[bool, Optional[str], Optional[str]]:
        """
        Lance le scraping des produits avec les nouveaux scripts modulaires :
        artiga/scraper-subcategory.py (collect → process → generate-csv)
        """
        import subprocess
        import glob
        
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
                log_callback("Démarrage du scraping Artiga avec les scripts modulaires...")
            
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
                cmd = [
                    sys.executable,
                    'artiga/scraper-subcategory.py',
                    '--url', subcategory_url,
                    '--category', category_name,
                    '--subcategory', subcategory_name
                ]
                
                if limit:
                    cmd.extend(['--limit', str(limit)])
                
                if not headless:
                    cmd.append('--no-headless')
                
                if options.get('retry_errors_after'):
                    cmd.append('--retry-errors-after')
                
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
                        # Afficher dans le terminal
                        print(line_stripped)
                        
                        # Envoyer aussi à l'UI
                        if log_callback:
                            log_callback(line_stripped)
                
                process.wait()
                
                if process.returncode != 0:
                    error_msg = f"Le script a échoué pour {subcategory_name} (code: {process.returncode})"
                    if log_callback:
                        log_callback(f"❌ {error_msg}")
                    # Continuer avec les autres sous-catégories
                    continue
            
            # Chercher les fichiers CSV générés créés après le début du scraping
            csv_pattern = "outputs/artiga/shopify_import_artiga_*.csv"
            all_csv_files = glob.glob(csv_pattern)
            
            # Filtrer uniquement les fichiers créés après le début du scraping
            csv_files = [
                f for f in all_csv_files 
                if os.path.getmtime(f) >= start_time
            ]
            
            if csv_files:
                # Trier par date de modification (plus récent en premier)
                csv_files.sort(key=lambda x: os.path.getmtime(x), reverse=True)
                latest_csv = csv_files[0]
                
                if log_callback:
                    log_callback(f"\n✅ Scraping terminé avec succès !")
                    log_callback(f"📄 Fichier CSV généré : {latest_csv}")
                
                return True, latest_csv, None
            else:
                # Si aucun fichier créé pendant cette session, chercher le plus récent de tous
                if all_csv_files:
                    all_csv_files.sort(key=lambda x: os.path.getmtime(x), reverse=True)
                    latest_csv = all_csv_files[0]
                    logger.warning(f"Aucun fichier créé pendant cette session, utilisation du plus récent: {latest_csv}")
                    if log_callback:
                        log_callback(f"\n✅ Scraping terminé avec succès !")
                        log_callback(f"📄 Fichier CSV généré : {latest_csv}")
                    return True, latest_csv, None
                else:
                    if log_callback:
                        log_callback("\n⚠️  Aucun fichier CSV n'a été généré")
                    return False, None, "Aucun fichier CSV généré"
        
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

