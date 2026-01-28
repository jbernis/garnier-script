"""
Wrapper pour le scraper Garnier-Thiebaut.
"""

import sys
import os
from typing import List, Dict, Optional, Callable, Tuple
import logging
from datetime import datetime
import threading
import time
import warnings

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

# Importer les fonctions du garnier_functions.py
import importlib.util
garnier_path = resource_path("garnier", "garnier_functions.py")

if not os.path.exists(garnier_path):
    raise FileNotFoundError(f"Fichier garnier_functions.py introuvable: {garnier_path}")

spec = importlib.util.spec_from_file_location("garnier.garnier_functions", garnier_path)
if spec is None or spec.loader is None:
    raise ImportError(f"Impossible de charger le module garnier_functions depuis {garnier_path}")

garnier_module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(garnier_module)

logger = logging.getLogger(__name__)


class CancellationException(Exception):
    """Exception levée lorsque l'annulation est demandée."""
    pass


class GarnierScraper(BaseScraper):
    """Wrapper pour le scraper Garnier-Thiebaut."""
    
    def __init__(self):
        super().__init__("garnier", "Garnier-Thiebaut")
        self.requires_auth = True
        self.supports_subcategories = False
        self.env_manager = EnvManager()
        self.driver = None
        self.session = None
        self.cancel_check = None  # Callback pour vérifier l'annulation
    
    def check_credentials(self) -> Tuple[bool, List[str]]:
        """Vérifie si les credentials Garnier sont configurés."""
        return self.env_manager.validate_credentials("garnier")
    
    def get_categories(self, callback: Optional[Callable[[str], None]] = None) -> List[Dict[str, str]]:
        """Récupère la liste des catégories disponibles."""
        try:
            # Désactiver temporairement la propagation du logger pour éviter les doublons dans le terminal
            original_propagate = logger.propagate
            logger.propagate = False
            
            try:
                if callback:
                    callback("Connexion au site Garnier-Thiebaut...")
                
                # Ne pas logger ici car le module garnier le fait déjà
                # logger.info("Authentification sur Garnier-Thiebaut...")
                # Authentifier
                self.driver, self.session = garnier_module.authenticate(headless=True)
                
                if not self.driver:
                    error_msg = "Impossible de créer le driver Selenium. Vérifiez que Chrome est installé."
                    # logger.error(error_msg)  # Ne pas logger ici
                    if callback:
                        callback(f"Erreur: {error_msg}")
                    return []
                
                if callback:
                    callback("Récupération des catégories...")
                
                # Ne pas logger ici car le module garnier le fait déjà
                # logger.info("Récupération des catégories...")
                # Récupérer les catégories
                categories = garnier_module.get_categories(self.driver, self.session)
                
                # logger.info(f"Catégories récupérées: {len(categories)}")  # Ne pas logger ici
                if callback:
                    callback(f"{len(categories)} catégorie(s) trouvée(s)")
            finally:
                # Réactiver la propagation
                logger.propagate = original_propagate
            
            return categories
        
        except Exception as e:
            error_msg = f"Erreur lors de la récupération des catégories: {e}"
            logger.error(error_msg, exc_info=True)
            if callback:
                callback(f"Erreur: {str(e)}")
            return []
    
    def scrape(self, categories: List[Dict[str, str]], 
               subcategories: Optional[List[Dict[str, str]]] = None,
               options: Optional[Dict] = None,
               progress_callback: Optional[Callable[[str, int, int], None]] = None,
               log_callback: Optional[Callable[[str], None]] = None,
               cancel_check: Optional[Callable[[], bool]] = None) -> Tuple[bool, Optional[str], Optional[str]]:
        """
        Lance le scraping des produits avec les nouveaux scripts en 3 étapes :
        1. Collecte des URLs (scraper-garnier-collect.py)
        2. Traitement des variants (scraper-garnier-process.py)
        3. Génération du CSV (scraper-garnier-generate-csv.py)
        
        Vérifie la disponibilité du site à partir de l'étape 2 en cas d'erreur.
        """
        import subprocess
        import glob
        import requests
        from utils.app_config import get_garnier_db_path
        from garnier.scraper_garnier_module import check_site_accessible, wait_for_site_accessible
        
        try:
            options = options or {}
            limit = options.get('limit')
            output_file = options.get('output')
            headless = options.get('headless', True)
            gamme_url = options.get('gamme_url')
            gamme_category = options.get('category')
            
            # Base de données pérenne
            db_path = get_garnier_db_path()
            
            # Récupérer BASE_URL depuis les variables d'environnement
            base_url = self.env_manager.get_by_provider("garnier").get("BASE_URL_GARNIER", "https://garnier-thiebaut.adsi.me")
            
            # Créer une session pour la vérification de disponibilité
            session = requests.Session()
            
            def check_and_wait_if_needed(error_msg: str = None):
                """Vérifie la disponibilité du site et attend si nécessaire."""
                nonlocal session  # Permettre la mise à jour de la session du scope parent
                
                if error_msg:
                    msg = f"⚠️  Erreur détectée: {error_msg}"
                    print(msg)
                    if log_callback:
                        log_callback(msg)
                
                msg = "Vérification de la disponibilité du site..."
                print(msg)
                if log_callback:
                    log_callback(msg)
                
                if not check_site_accessible(session, base_url, timeout=10):
                    msg = "Site non accessible, attente de la réaccessibilité..."
                    print(msg)
                    if log_callback:
                        log_callback(msg)
                    
                    # Vérifier l'annulation avant d'attendre
                    if cancel_check and cancel_check():
                        return False
                    
                    # Attendre que le site redevienne accessible
                    if wait_for_site_accessible(session, base_url, check_interval=30, timeout=10):
                        msg = "✓ Site redevenu accessible (code 200 détecté), ré-authentification avant reprise..."
                        print(msg)
                        if log_callback:
                            log_callback(msg)
                        
                        # Ré-authentifier avant de reprendre (2ème retry)
                        # car un code 200 peut être retourné même sans authentification
                        try:
                            msg = "Ré-authentification en cours..."
                            print(msg)
                            if log_callback:
                                log_callback(msg)
                            
                            from garnier.scraper_garnier_module import authenticate
                            driver, authenticated_session = authenticate(headless=headless)
                            
                            # Mettre à jour la session avec la session authentifiée pour les vérifications suivantes
                            session = authenticated_session
                            
                            msg = "✓ Ré-authentification réussie"
                            print(msg)
                            if log_callback:
                                log_callback(msg)
                            
                            # Note: Les scripts appelés via subprocess géreront leur propre authentification,
                            # mais cette authentification permet de vérifier la connexion et d'afficher
                            # des messages de diagnostic dans l'UI, et de réutiliser la session pour les vérifications suivantes
                            
                        except Exception as auth_error:
                            msg = f"✗ Erreur lors de la ré-authentification: {auth_error}"
                            print(msg)
                            if log_callback:
                                log_callback(msg)
                            return False
                        
                        return True
                    else:
                        msg = "✗ Site toujours inaccessible après attente"
                        print(msg)
                        if log_callback:
                            log_callback(msg)
                        return False
                else:
                    msg = "✓ Site accessible"
                    print(msg)
                    if log_callback:
                        log_callback(msg)
                    return True
            
            def run_script(cmd, step_name, step_num, total_steps):
                """Lance un script et capture ses logs."""
                step_header = f"ÉTAPE {step_num}/{total_steps} : {step_name}"
                print("")
                print("=" * 60)
                print(step_header)
                print("=" * 60)
                if log_callback:
                    log_callback("")
                    log_callback("=" * 60)
                    log_callback(step_header)
                    log_callback("=" * 60)
                
                if progress_callback:
                    progress_callback(f"{step_name}...", step_num - 1, total_steps)
                
                # Vérifier l'annulation
                if cancel_check and cancel_check():
                    return False, None, "Annulation demandée par l'utilisateur"
                
                # Lancer le script avec capture des logs
                process = subprocess.Popen(
                    cmd,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                    text=True,
                    bufsize=1,
                    universal_newlines=True
                )
                
                error_lines = []
                
                # Lire les logs en temps réel
                for line in iter(process.stdout.readline, ''):
                    if cancel_check and cancel_check():
                        process.terminate()
                        return False, None, "Annulation demandée par l'utilisateur"
                    
                    line_stripped = line.strip()
                    if line_stripped:
                        # Afficher dans le terminal
                        print(line_stripped)
                        
                        # Envoyer aussi à l'UI
                        if log_callback:
                            log_callback(line_stripped)
                    
                    # Détecter les erreurs dans les logs
                    if any(keyword in line_stripped.lower() for keyword in ['error', 'erreur', 'timeout', 'introuvable', 'non accessible']):
                        error_lines.append(line_stripped)
                
                process.wait()
                
                return process.returncode, error_lines, None
            
            # Étape 1 : Collecte des URLs (pas de vérification avant car authentification nécessaire)
            if gamme_url:
                msg = "Démarrage du scraping Garnier-Thiebaut par gamme..."
            else:
                msg = "Démarrage du scraping Garnier-Thiebaut avec les nouveaux scripts..."
            print(msg)
            if log_callback:
                log_callback(msg)
            
            # Construire la commande pour scraper-garnier-collect.py
            collect_cmd = [
                sys.executable,
                resource_path("garnier", "scraper-collect.py"),
                "--db", db_path
            ]
            
            # Mode gamme ou mode catégories
            if gamme_url and gamme_category:
                # Mode gamme
                collect_cmd.extend(["--gamme-url", gamme_url])
                collect_cmd.extend(["--category", gamme_category])
            else:
                # Mode catégories
                for category in categories:
                    collect_cmd.extend(["--category", category['name']])
            
            if not headless:
                collect_cmd.append("--no-headless")
            
            if options.get('retry_errors_after'):
                collect_cmd.append("--retry-errors-after")
            
            returncode, error_lines, _ = run_script(collect_cmd, "Collecte des URLs", 1, 3)
            
            if returncode is False:  # Annulation
                return False, None, "Annulation demandée par l'utilisateur"
            
            # Vérifier la disponibilité du site si erreur détectée (seulement après étape 1)
            if returncode != 0:
                error_msg = f"Erreur lors de la collecte (code {returncode})"
                if not check_and_wait_if_needed(error_msg):
                    session.close()
                    return False, None, "Site non accessible après erreur de collecte"
                
                # Réessayer une fois après vérification, mais seulement les erreurs
                msg = "Réessai de la collecte (produits en erreur uniquement)..."
                print(msg)
                if log_callback:
                    log_callback(msg)
                
                # Créer une nouvelle commande avec --retry-errors-only
                collect_cmd_retry = collect_cmd + ["--retry-errors-only"]
                returncode, error_lines, _ = run_script(collect_cmd_retry, "Collecte des URLs (erreurs uniquement)", 1, 3)
                
                if returncode is False:  # Annulation
                    session.close()
                    return False, None, "Annulation demandée par l'utilisateur"
                
                if returncode != 0:
                    session.close()
                    return False, None, f"Erreur persistante lors de la collecte (code {returncode})"
            
            # Étape 2 : Traitement des variants (vérification avant car nécessite accès au site)
            if cancel_check and cancel_check():
                session.close()
                return False, None, "Annulation demandée par l'utilisateur"
            
            # Vérifier la disponibilité du site avant le traitement
            if not check_and_wait_if_needed():
                session.close()
                return False, None, "Site non accessible avant traitement"
            
            # Construire la commande pour scraper-garnier-process.py
            process_cmd = [
                sys.executable,
                resource_path("garnier", "scraper-process.py"),
                "--db", db_path
            ]
            
            # Ajouter les filtres si mode gamme
            if gamme_url and gamme_category:
                # Extraire le nom de la gamme depuis l'URL pour le filtre
                from urllib.parse import urlparse, unquote
                parsed = urlparse(gamme_url)
                gamme_name = "GAMME SPECIFIQUE"
                if 'code_gamme' in parsed.query:
                    gamme_name = unquote(parsed.query.split('code_gamme=')[1].split('&')[0])
                    gamme_name = gamme_name.replace('_', ' ').replace('-', ' ').upper()
                
                process_cmd.extend(["--category", gamme_category])
                process_cmd.extend(["--gamme", gamme_name])
            elif categories:
                # Mode catégories : filtrer par toutes les catégories sélectionnées
                for category in categories:
                    process_cmd.extend(["--category", category['name']])
            
            if not headless:
                process_cmd.append("--no-headless")
            
            returncode, error_lines, _ = run_script(process_cmd, "Traitement des variants", 2, 3)
            
            if returncode is False:  # Annulation
                session.close()
                return False, None, "Annulation demandée par l'utilisateur"
            
            # Vérifier la disponibilité du site si erreur détectée
            if returncode != 0:
                error_msg = f"Erreur lors du traitement (code {returncode})"
                if not check_and_wait_if_needed(error_msg):
                    session.close()
                    return False, None, "Site non accessible après erreur de traitement"
                
                # Réessayer une fois après vérification, mais seulement les erreurs
                msg = "Réessai du traitement (variants en erreur uniquement)..."
                print(msg)
                if log_callback:
                    log_callback(msg)
                
                # Créer une nouvelle commande avec --retry-errors
                process_cmd_retry = process_cmd + ["--retry-errors"]
                returncode, error_lines, _ = run_script(process_cmd_retry, "Traitement des variants (erreurs uniquement)", 2, 3)
                
                if returncode is False:  # Annulation
                    session.close()
                    return False, None, "Annulation demandée par l'utilisateur"
                
                if returncode != 0:
                    session.close()
                    return False, None, f"Erreur persistante lors du traitement (code {returncode})"
            
            # Étape 3 : Génération du CSV (pas besoin de vérification car pas d'accès au site)
            if cancel_check and cancel_check():
                session.close()
                return False, None, "Annulation demandée par l'utilisateur"
            
            # Construire la commande pour scraper-garnier-generate-csv.py
            generate_cmd = [
                sys.executable,
                resource_path("garnier", "scraper-generate-csv.py"),
                "--db", db_path
            ]
            
            # Mode catégories : filtrer uniquement par catégories sélectionnées
            if categories and not gamme_url:
                for category in categories:
                    generate_cmd.extend(["--category", category['name']])
            
            # Mode gamme : filtrer par gamme ET catégorie
            if gamme_url and gamme_category:
                # Extraire le nom de la gamme depuis l'URL pour le filtre
                from urllib.parse import urlparse, unquote
                parsed = urlparse(gamme_url)
                gamme_name = "GAMME SPECIFIQUE"
                if 'code_gamme' in parsed.query:
                    gamme_name = unquote(parsed.query.split('code_gamme=')[1].split('&')[0])
                    gamme_name = gamme_name.replace('_', ' ').replace('-', ' ').upper()
                
                # Ajouter le filtre par catégorie
                generate_cmd.extend(["--category", gamme_category])
                # Ajouter le filtre par gamme
                generate_cmd.extend(["--gamme", gamme_name])
            
            # Ajouter le fichier de sortie si spécifié
            if output_file:
                generate_cmd.extend(["--output", output_file])
            
            returncode, error_lines, _ = run_script(generate_cmd, "Génération du CSV", 3, 3)
            
            if returncode is False:  # Annulation
                session.close()
                return False, None, "Annulation demandée par l'utilisateur"
            
            if returncode != 0:
                session.close()
                return False, None, f"Erreur lors de la génération du CSV (code {returncode})"
            
            # Récupérer le fichier CSV généré
            if not output_file:
                # Le script génère automatiquement un nom de fichier
                output_dir = self.get_output_dir()
                csv_files = glob.glob(os.path.join(output_dir, "shopify_import_garnier_*.csv"))
                if csv_files:
                    output_file = max(csv_files, key=os.path.getctime)
                    output_file = os.path.abspath(output_file)
            
            if progress_callback:
                progress_callback("Terminé !", 3, 3)
            
            success_msg = "✓ Import terminé avec succès !"
            print("")
            print("=" * 60)
            print(success_msg)
            if output_file:
                print(f"Fichier CSV : {output_file}")
            print("=" * 60)
            if log_callback:
                log_callback("")
                log_callback("=" * 60)
                log_callback(success_msg)
                if output_file:
                    log_callback(f"Fichier CSV : {output_file}")
                log_callback("=" * 60)
            
            session.close()
            return True, output_file, None
        
        except CancellationException as e:
            # Annulation demandée - ne pas traiter comme une erreur
            error_msg = "Annulation demandée par l'utilisateur"
            logger.info(error_msg)
            if log_callback:
                log_callback(error_msg)
            if 'session' in locals():
                session.close()
            return False, None, error_msg
        except Exception as e:
            error_msg = f"Erreur lors du scraping: {e}"
            logger.error(error_msg, exc_info=True)
            if log_callback:
                log_callback(error_msg)
            if 'session' in locals():
                session.close()
            return False, None, error_msg
        finally:
            # Nettoyage (plus besoin des handlers de logging car on utilise subprocess)
            if 'session' in locals():
                try:
                    session.close()
                except:
                    pass
            
            # Fermer le driver si ouvert (au cas où)
            if self.driver:
                urllib3_logger = logging.getLogger("urllib3")
                urllib3_logger.setLevel(logging.ERROR)
                try:
                    self.driver.quit()
                except:
                    pass
                self.driver = None
    
    def _call_with_cancellation_check(self, func: Callable, args: tuple, 
                                      cancel_check: Optional[Callable[[], bool]],
                                      log_callback: Optional[Callable[[str], None]],
                                      operation_name: str) -> Optional:
        """
        Appelle une fonction dans un thread avec vérification périodique de l'annulation.
        Si l'annulation est détectée, force l'arrêt du driver Selenium et retourne None.
        
        Args:
            func: Fonction à appeler
            args: Arguments à passer à la fonction
            cancel_check: Callback pour vérifier l'annulation
            log_callback: Callback pour les logs
            operation_name: Nom de l'opération pour les logs
            
        Returns:
            Résultat de la fonction ou None si annulé
        """
        if not cancel_check:
            # Si pas de vérification d'annulation, appeler directement
            return func(*args)
        
        result = [None]  # Utiliser une liste pour permettre la modification depuis le thread
        exception = [None]
        finished = threading.Event()
        
        def target():
            try:
                result[0] = func(*args)
            except CancellationException as e:
                # Si c'est une CancellationException, la stocker et arrêter immédiatement
                exception[0] = e
                finished.set()
                return
            except Exception as e:
                exception[0] = e
            finally:
                finished.set()
        
        # Démarrer le thread
        thread = threading.Thread(target=target, daemon=True)
        thread.start()
        
        # Vérifier périodiquement l'annulation
        check_interval = 0.1  # Vérifier toutes les 0.1 secondes (plus fréquent pour détecter plus vite)
        while not finished.is_set():
            if cancel_check and cancel_check():
                # Annulation demandée - forcer l'arrêt du driver Selenium
                if log_callback:
                    log_callback(f"Annulation demandée pendant {operation_name}...")
                logger.info(f"Annulation demandée pendant {operation_name}")
                
                # Forcer l'arrêt du driver si disponible
                if self.driver:
                    # Supprimer les warnings urllib3 lors de la fermeture forcée du driver
                    # Ces warnings sont normaux après la fermeture du driver
                    urllib3_logger = logging.getLogger("urllib3")
                    urllib3_logger.setLevel(logging.ERROR)  # Ne montrer que les erreurs, pas les warnings
                    try:
                        # Fermer le navigateur de force
                        self.driver.quit()
                    except:
                        pass
                    try:
                        # Essayer aussi de tuer le processus ChromeDriver si possible
                        if hasattr(self.driver, 'service') and hasattr(self.driver.service, 'process'):
                            import signal
                            try:
                                os.kill(self.driver.service.process.pid, signal.SIGTERM)
                            except:
                                pass
                    except:
                        pass
                    self.driver = None
                
                # Attendre un peu pour que le thread se termine proprement
                thread.join(timeout=0.5)  # Réduire le timeout
                
                # Vérifier immédiatement s'il y a une exception CancellationException
                if exception[0] and isinstance(exception[0], CancellationException):
                    raise exception[0]
                
                # Si le thread n'est pas terminé mais qu'on a demandé l'annulation, vérifier à nouveau
                if not finished.is_set() and cancel_check and cancel_check():
                    # Attendre encore un peu pour voir si une exception est levée
                    thread.join(timeout=0.2)
                    if exception[0] and isinstance(exception[0], CancellationException):
                        raise exception[0]
                
                return None
            
            time.sleep(check_interval)
        
        # Attendre que le thread se termine
        thread.join()
        
        # Si une exception s'est produite, la relancer
        if exception[0]:
            # Si c'est une CancellationException, la relancer immédiatement
            if isinstance(exception[0], CancellationException):
                raise exception[0]
            # Pour les autres exceptions, les relancer aussi
            raise exception[0]
        
        return result[0]

