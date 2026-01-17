#!/usr/bin/env python3
"""
Script pour lancer l'interface graphique avec logs défilantes dans le terminal.
"""

import sys
import os
import logging
from datetime import datetime

# Créer un handler pour afficher dans le terminal avec couleurs
class ColoredFormatter(logging.Formatter):
    """Formatter avec couleurs pour les logs."""
    
    COLORS = {
        'DEBUG': '\033[36m',      # Cyan
        'INFO': '\033[32m',       # Vert
        'WARNING': '\033[33m',    # Jaune
        'ERROR': '\033[31m',      # Rouge
        'CRITICAL': '\033[35m',   # Magenta
    }
    RESET = '\033[0m'
    
    def format(self, record):
        log_color = self.COLORS.get(record.levelname, self.RESET)
        record.levelname = f"{log_color}{record.levelname}{self.RESET}"
        return super().format(record)


# Configuration du logging avec format détaillé et couleurs
# Ne pas utiliser basicConfig pour éviter les handlers multiples
root_logger = logging.getLogger()
root_logger.setLevel(logging.INFO)

# Supprimer les handlers existants pour éviter les doublons
for handler in root_logger.handlers[:]:
    root_logger.removeHandler(handler)

# Ajouter uniquement notre handler avec couleurs
console_handler = logging.StreamHandler(sys.stdout)
console_handler.setFormatter(ColoredFormatter('%(asctime)s [%(levelname)s] %(message)s', datefmt='%H:%M:%S'))
root_logger.addHandler(console_handler)

# Logger pour ce module
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

# Ajouter le répertoire parent au path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


def print_banner():
    """Affiche une bannière au démarrage."""
    banner = """
    ╔═══════════════════════════════════════════════════════════╗
    ║     Scrapers Shopify - Interface Graphique               ║
    ║     Version 1.0.0                                        ║
    ╚═══════════════════════════════════════════════════════════╝
    """
    print(banner)
    logger.info("Démarrage de l'application...")


def check_dependencies():
    """Vérifie les dépendances nécessaires."""
    logger.info("Vérification des dépendances...")
    
    missing = []
    critical_missing = []
    
    # Vérifier customtkinter (critique pour l'interface)
    try:
        import customtkinter
        logger.info("✓ customtkinter installé")
    except ImportError:
        missing.append("customtkinter")
        critical_missing.append("customtkinter")
        logger.error("✗ customtkinter manquant (CRITIQUE - nécessaire pour l'interface)")
    
    # Vérifier les autres dépendances (non critiques pour démarrer l'interface)
    try:
        import selenium
        logger.info("✓ selenium installé")
    except ImportError:
        missing.append("selenium")
        logger.warning("✗ selenium manquant (nécessaire pour le scraping)")
    
    try:
        import pandas
        logger.info("✓ pandas installé")
    except ImportError:
        missing.append("pandas")
        logger.warning("✗ pandas manquant (nécessaire pour le scraping)")
    
    try:
        import bs4
        logger.info("✓ beautifulsoup4 installé")
    except ImportError:
        missing.append("beautifulsoup4")
        logger.warning("✗ beautifulsoup4 manquant (nécessaire pour le scraping)")
    
    try:
        from PIL import Image
        logger.info("✓ Pillow installé")
    except ImportError:
        missing.append("Pillow")
        logger.warning("✗ Pillow manquant (nécessaire pour certaines fonctionnalités)")
    
    try:
        import tkinterweb
        logger.info("✓ tkinterweb installé")
    except ImportError:
        missing.append("tkinterweb")
        logger.warning("✗ tkinterweb manquant (nécessaire pour le visualiseur CSV)")
    
    # Vérifier les dépendances IA (optionnelles pour démarrer l'interface)
    try:
        import openai
        logger.info("✓ openai installé")
    except ImportError:
        missing.append("openai")
        logger.warning("✗ openai manquant (nécessaire pour l'éditeur IA avec OpenAI)")
    
    try:
        import anthropic
        logger.info("✓ anthropic installé")
    except ImportError:
        missing.append("anthropic")
        logger.warning("✗ anthropic manquant (nécessaire pour l'éditeur IA avec Claude)")
    
    try:
        import google.genai
        logger.info("✓ google-genai installé")
    except ImportError:
        missing.append("google-genai")
        logger.warning("✗ google-genai manquant (nécessaire pour l'éditeur IA avec Gemini)")
        logger.warning("  Note: L'ancien package 'google-generativeai' est déprécié et n'est plus supporté.")
    
    if critical_missing:
        logger.error(f"Dépendances CRITIQUES manquantes: {', '.join(critical_missing)}")
        logger.error("Impossible de démarrer l'interface graphique")
        return False
    
    if missing:
        logger.warning(f"Dépendances manquantes: {', '.join(missing)}")
        logger.info("L'application va démarrer, mais certaines fonctionnalités ne seront pas disponibles")
        logger.info("Utilisez la fenêtre Setup pour installer automatiquement tous les packages")
        return True  # Permettre le démarrage même avec des dépendances manquantes
    
    logger.info("✓ Toutes les dépendances sont installées")
    return True


def setup_logging_for_modules():
    """Configure le logging pour les modules de l'application."""
    # Ne pas ajouter de handlers supplémentaires car le root logger a déjà un handler
    # Les loggers enfants propagent automatiquement vers le root logger
    # Ajouter des handlers ici causerait des doublons
    
    # Configurer les niveaux de logging pour les modules
    scraper_logger = logging.getLogger('scrapers')
    scraper_logger.setLevel(logging.INFO)
    scraper_logger.propagate = True  # Propager vers le root logger
    
    utils_logger = logging.getLogger('utils')
    utils_logger.setLevel(logging.INFO)
    utils_logger.propagate = True
    
    gui_logger = logging.getLogger('gui')
    gui_logger.setLevel(logging.INFO)
    gui_logger.propagate = True


def main():
    """Fonction principale."""
    print_banner()
    
    # Vérifier les dépendances (mais ne pas bloquer le démarrage)
    dependencies_ok = check_dependencies()
    if not dependencies_ok:
        logger.warning("⚠ Certaines dépendances manquent, mais l'application va démarrer")
        logger.warning("⚠ Utilisez la fenêtre Setup pour installer automatiquement les packages manquants")
        logger.info("─" * 60)
    
    # Configurer le logging pour les modules
    setup_logging_for_modules()
    
    logger.info("Chargement de l'interface graphique...")
    
    try:
        from apps.gui.main_window import MainWindow
        import customtkinter as ctk
        
        logger.info("✓ Interface graphique chargée")
        logger.info("Ouverture de la fenêtre principale...")
        
        # Créer et lancer l'application
        app = MainWindow()
        
        # Forcer la fenêtre au premier plan immédiatement après création
        app.update_idletasks()
        app.bring_to_front()
        
        logger.info("✓ Application démarrée avec succès")
        logger.info("─" * 60)
        logger.info("L'interface graphique est maintenant ouverte.")
        if not dependencies_ok:
            logger.info("⚠ Ouvrez la fenêtre Setup pour installer les packages manquants")
        logger.info("Les logs continueront à s'afficher ici pendant l'utilisation.")
        logger.info("─" * 60)
        
        # Lancer l'application directement dans le thread principal
        # (Tkinter/CustomTkinter doit être exécuté dans le thread principal)
        try:
            app.mainloop()
        except KeyboardInterrupt:
            logger.info("Application interrompue par l'utilisateur")
        except Exception as e:
            logger.error(f"Erreur dans l'application: {e}", exc_info=True)
        
        logger.info("Application fermée")
    
    except KeyboardInterrupt:
        logger.info("Interruption par l'utilisateur")
        sys.exit(0)
    except ImportError as e:
        logger.error(f"Erreur d'import: {e}")
        logger.error("Assurez-vous que toutes les dépendances sont installées")
        logger.error("Ou utilisez la fenêtre Setup pour installer automatiquement les packages")
        # Essayer quand même de démarrer pour permettre l'installation via Setup
        try:
            from apps.gui.main_window import MainWindow
            import customtkinter as ctk
            app = MainWindow()
            app.mainloop()
        except:
            sys.exit(1)
    except Exception as e:
        logger.error(f"Erreur fatale: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()

