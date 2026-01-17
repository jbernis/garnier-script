#!/usr/bin/env python3
"""
Point d'entrée principal de l'application GUI.
"""

import sys
import os
import logging

# Ajouter le répertoire parent au path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Configuration du logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

try:
    import customtkinter as ctk
except ImportError:
    print("Erreur: customtkinter n'est pas installé.")
    print("Installez-le avec: pip install customtkinter")
    sys.exit(1)

from apps.gui.main_window import MainWindow


def main():
    """Fonction principale."""
    try:
        # Créer et lancer l'application
        app = MainWindow()
        app.mainloop()
    
    except KeyboardInterrupt:
        logger.info("Application interrompue par l'utilisateur")
    except Exception as e:
        logger.error(f"Erreur fatale: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()

