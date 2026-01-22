"""
Vérification des prérequis pour l'application.
"""

import sys
import os
import subprocess
import shutil
import platform
from typing import Dict, Tuple, Optional
import logging

logger = logging.getLogger(__name__)


class SetupChecker:
    """Vérifie les prérequis nécessaires pour l'application."""
    
    def __init__(self):
        self.checks = {}
    
    def check_python_version(self) -> Tuple[bool, str]:
        """Vérifie que Python 3.8+ est installé."""
        try:
            version = sys.version_info
            version_str = f"{version.major}.{version.minor}.{version.micro}"
            
            if version.major >= 3 and version.minor >= 8:
                return True, f"Python {version_str} installé (OK)"
            else:
                return False, f"Python 3.8+ requis (version actuelle: {version.major}.{version.minor}.{version.micro}) - Installez ou mettez à jour Python"
        except Exception as e:
            return False, f"Erreur lors de la vérification de Python: {e}"
    
    def check_pip(self) -> Tuple[bool, str]:
        """Vérifie que pip est installé."""
        if getattr(sys, "frozen", False):
            # Dans l'app packagée, sys.executable relance l'app : éviter la récursivité.
            return False, "pip n'est pas disponible dans l'application packagée"
        try:
            result = subprocess.run(
                [sys.executable, "-m", "pip", "--version"],
                capture_output=True,
                text=True,
                timeout=5
            )
            if result.returncode == 0:
                version = result.stdout.strip().split()[1] if result.stdout else "installé"
                return True, f"pip {version} disponible"
            else:
                return False, "pip n'est pas disponible"
        except FileNotFoundError:
            return False, "pip n'est pas installé"
        except Exception as e:
            return False, f"Erreur lors de la vérification de pip: {e}"
    
    def check_chrome(self) -> Tuple[bool, str]:
        """Vérifie que Chrome/Chromium est installé."""
        system = platform.system()
        
        # Pour macOS, vérifier directement les .app dans /Applications
        if system == "Darwin":
            chrome_apps = [
                "/Applications/Google Chrome.app",
                "/Applications/Chromium.app",
                "/Applications/Google Chrome Canary.app",
            ]
            
            for app_path in chrome_apps:
                if os.path.exists(app_path):
                    # Extraire le nom de l'app pour le message
                    app_name = os.path.basename(app_path).replace(".app", "")
                    return True, f"Chrome trouvé: {app_name}"
            
            # Vérifier aussi le binaire exécutable à l'intérieur
            chrome_binaries = [
                "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
                "/Applications/Chromium.app/Contents/MacOS/Chromium",
            ]
            
            for binary_path in chrome_binaries:
                if os.path.exists(binary_path):
                    return True, "Chrome/Chromium trouvé"
        
        # Pour Windows
        elif system == "Windows":
            chrome_paths = [
                r"C:\Program Files\Google\Chrome\Application\chrome.exe",
                r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
            ]
            
            for path in chrome_paths:
                if os.path.exists(path):
                    return True, "Chrome trouvé"
        
        # Pour Linux et autres
        else:
            chrome_paths = [
                "/usr/bin/google-chrome",
                "/usr/bin/chromium-browser",
                "/usr/bin/chromium",
            ]
            
            for path in chrome_paths:
                if os.path.exists(path) or shutil.which(path):
                    return True, f"Chrome/Chromium trouvé: {path}"
        
        # Essayer avec which/where comme fallback
        chrome_names = ["google-chrome", "chromium-browser", "chromium", "chrome"]
        for name in chrome_names:
            chrome_path = shutil.which(name)
            if chrome_path:
                return True, f"Chrome/Chromium trouvé ({name}): {chrome_path}"
        
        return False, "Chrome/Chromium n'est pas installé ou introuvable"
    
    def check_venv(self) -> Tuple[bool, str]:
        """Vérifie si un environnement virtuel est actif."""
        if hasattr(sys, 'real_prefix') or (hasattr(sys, 'base_prefix') and sys.base_prefix != sys.prefix):
            return True, "Environnement virtuel actif"
        else:
            return False, "Aucun environnement virtuel détecté (recommandé mais optionnel)"
    
    def check_network(self) -> Tuple[bool, str]:
        """Vérifie l'accès réseau pour télécharger les packages."""
        try:
            import socket
            socket.create_connection(("8.8.8.8", 53), timeout=3)
            return True, "Accès réseau disponible"
        except OSError:
            return False, "Pas d'accès réseau détecté"
        except Exception as e:
            return False, f"Erreur lors de la vérification réseau: {e}"
    
    def check_tkinterweb(self) -> Tuple[bool, str]:
        """Vérifie que tkinterweb est installé (nécessaire pour le visualiseur CSV)."""
        try:
            import tkinterweb
            # Essayer d'obtenir la version si possible
            try:
                version = tkinterweb.__version__ if hasattr(tkinterweb, '__version__') else "installé"
                return True, f"tkinterweb {version} installé"
            except:
                return True, "tkinterweb installé"
        except ImportError:
            return False, "tkinterweb n'est pas installé (nécessaire pour le visualiseur CSV)"
        except Exception as e:
            return False, f"Erreur lors de la vérification de tkinterweb: {e}"
    
    def check_packages(self, requirements_files: Optional[list] = None) -> Tuple[bool, str, list]:
        """Vérifie si les packages requis sont installés depuis requirements.txt et requirements-gui.txt."""
        try:
            # Utiliser importlib.metadata (moderne) au lieu de pkg_resources (déprécié)
            use_importlib_metadata = False
            try:
                from importlib.metadata import version, PackageNotFoundError
                use_importlib_metadata = True
            except ImportError:
                # Fallback pour Python < 3.8
                try:
                    from importlib_metadata import version, PackageNotFoundError
                    use_importlib_metadata = True
                except ImportError:
                    # Dernier recours: utiliser pkg_resources avec warning supprimé
                    import warnings
                    warnings.filterwarnings("ignore", category=UserWarning, module="pkg_resources")
                    import pkg_resources
                    PackageNotFoundError = pkg_resources.DistributionNotFound
                    use_importlib_metadata = False
            
            # Par défaut, vérifier les deux fichiers requirements
            if requirements_files is None:
                requirements_files = ["requirements.txt", "requirements-gui.txt"]
            
            all_requirements = []
            missing_packages = []
            installed_packages = []
            
            # Lire tous les fichiers requirements
            for requirements_file in requirements_files:
                try:
                    if os.path.exists(requirements_file):
                        with open(requirements_file, 'r', encoding='utf-8') as f:
                            all_requirements.extend(f.readlines())
                    else:
                        logger.warning(f"Fichier {requirements_file} introuvable, ignoré")
                except Exception as e:
                    logger.warning(f"Erreur lors de la lecture de {requirements_file}: {e}")
            
            # Collecter tous les packages uniques
            packages_to_check = set()
            for line in all_requirements:
                line = line.strip()
                if not line or line.startswith('#'):
                    continue
                
                # Extraire le nom du package (avant >=, ==, etc.)
                package_name = line.split('>=')[0].split('==')[0].split('<=')[0].split('>')[0].split('<')[0].strip()
                if package_name:
                    packages_to_check.add(package_name)
            
            # Vérifier chaque package individuellement
            for package_name in packages_to_check:
                try:
                    if use_importlib_metadata:
                        # Utiliser importlib.metadata.version() pour vérifier si le package est installé
                        try:
                            version(package_name)
                            installed_packages.append(package_name)
                        except PackageNotFoundError:
                            # Essayer avec des variations du nom (remplacer - par _ et vice versa)
                            package_variations = [
                                package_name,
                                package_name.replace('-', '_'),
                                package_name.replace('_', '-'),
                            ]
                            found = False
                            for var in package_variations:
                                try:
                                    version(var)
                                    installed_packages.append(package_name)
                                    found = True
                                    break
                                except PackageNotFoundError:
                                    continue
                            if not found:
                                missing_packages.append(package_name)
                    else:
                        # Utiliser pkg_resources (fallback)
                        try:
                            pkg_resources.get_distribution(package_name)
                            installed_packages.append(package_name)
                        except (pkg_resources.DistributionNotFound, pkg_resources.RequirementParseError):
                            missing_packages.append(package_name)
                except Exception as e:
                    logger.warning(f"Erreur lors de la vérification du package {package_name}: {e}")
                    missing_packages.append(package_name)
            
            if missing_packages:
                return False, f"{len(missing_packages)} package(s) manquant(s)", sorted(missing_packages)
            else:
                return True, f"Tous les packages requis sont installés ({len(installed_packages)} packages)", []
        
        except Exception as e:
            logger.error(f"Erreur lors de la vérification des packages: {e}", exc_info=True)
            return False, f"Erreur lors de la vérification des packages: {e}", []
    
    def run_all_checks(self) -> Dict[str, Tuple[bool, str]]:
        """Exécute toutes les vérifications."""
        results = {
            "Python": self.check_python_version(),
            "pip": self.check_pip(),
            "Chrome": self.check_chrome(),
            "Réseau": self.check_network(),
        }
        
        # Vérifier les packages si pip est disponible
        pip_ok, _ = self.check_pip()
        if pip_ok:
            # Vérifier les packages depuis requirements.txt et requirements-gui.txt
            packages_ok, packages_msg, missing = self.check_packages()
            results["Packages"] = (packages_ok, packages_msg)
            if missing:
                # Limiter l'affichage à 10 packages pour ne pas surcharger l'interface
                if len(missing) > 10:
                    display_missing = missing[:10] + [f"... et {len(missing) - 10} autre(s)"]
                else:
                    display_missing = missing
                results["Packages manquants"] = (False, ", ".join(display_missing))
            
            # Vérification spécifique pour tkinterweb (important pour le visualiseur CSV)
            tkinterweb_ok, tkinterweb_msg = self.check_tkinterweb()
            results["tkinterweb"] = (tkinterweb_ok, tkinterweb_msg)
        
        return results
    
    def install_packages(self, requirements_files: Optional[list] = None, 
                        callback=None) -> Tuple[bool, str]:
        """Installe les packages depuis requirements.txt et requirements-gui.txt."""
        if getattr(sys, "frozen", False):
            return False, "Installation de packages indisponible dans l'application packagée"
        try:
            pip_ok, pip_msg = self.check_pip()
            if not pip_ok:
                return False, f"pip n'est pas disponible: {pip_msg}"
            
            # Par défaut, installer depuis les deux fichiers requirements
            if requirements_files is None:
                requirements_files = ["requirements.txt", "requirements-gui.txt"]
            
            if callback:
                callback("Mise à jour de pip...")
            
            # Mettre à jour pip d'abord
            pip_update = subprocess.run(
                [sys.executable, "-m", "pip", "install", "--upgrade", "pip"],
                capture_output=True,
                text=True,
                timeout=60
            )
            
            if pip_update.returncode != 0:
                logger.warning(f"Erreur lors de la mise à jour de pip: {pip_update.stderr}")
            
            # Installer les packages depuis chaque fichier requirements
            installed_files = []
            failed_files = []
            
            for requirements_file in requirements_files:
                if not os.path.exists(requirements_file):
                    logger.warning(f"Fichier {requirements_file} introuvable, ignoré")
                    continue
                
                if callback:
                    callback(f"Installation des packages depuis {requirements_file}...")
                
                # Installer les packages
                result = subprocess.run(
                    [sys.executable, "-m", "pip", "install", "-r", requirements_file],
                    capture_output=True,
                    text=True,
                    timeout=600  # Augmenté à 10 minutes pour les gros packages
                )
                
                if result.returncode == 0:
                    installed_files.append(requirements_file)
                    logger.info(f"Packages installés depuis {requirements_file}")
                else:
                    failed_files.append(requirements_file)
                    error_msg = result.stderr if result.stderr else result.stdout
                    logger.error(f"Erreur lors de l'installation depuis {requirements_file}: {error_msg}")
            
            if failed_files:
                if installed_files:
                    return False, f"Installation partielle: {len(installed_files)} fichier(s) réussi(s), {len(failed_files)} échec(s)"
                else:
                    return False, f"Échec de l'installation depuis: {', '.join(failed_files)}"
            else:
                return True, f"Installation réussie depuis {len(installed_files)} fichier(s)"
        
        except subprocess.TimeoutExpired:
            return False, "Timeout lors de l'installation (trop long)"
        except Exception as e:
            logger.error(f"Erreur lors de l'installation: {e}", exc_info=True)
            return False, f"Erreur: {e}"

