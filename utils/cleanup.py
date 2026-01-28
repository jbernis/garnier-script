"""
Utilitaires pour le nettoyage des fichiers générés.
"""

import os
import sys
import shutil
import logging
from pathlib import Path

logger = logging.getLogger(__name__)


def remove_outputs_directory(outputs_dir: str = "outputs") -> bool:
    """
    Supprime le répertoire outputs s'il existe.
    En mode packagé, utilise ~/Library/Application Support/ScrapersShopify/outputs
    
    Args:
        outputs_dir: Chemin vers le répertoire outputs (défaut: "outputs")
    
    Returns:
        True si le répertoire a été supprimé avec succès, False sinon
    """
    try:
        # Convertir en chemin absolu si c'est un chemin relatif
        if not os.path.isabs(outputs_dir):
            if getattr(sys, "frozen", False):
                # Mode packagé : utiliser Application Support
                outputs_dir = str(Path.home() / "Library" / "Application Support" / "ScrapersShopify" / outputs_dir)
            else:
                # Mode développement : utiliser le répertoire courant
                current_dir = os.getcwd()
                outputs_dir = os.path.join(current_dir, outputs_dir)
        
        # Vérifier si le répertoire existe
        if os.path.exists(outputs_dir) and os.path.isdir(outputs_dir):
            # Supprimer récursivement le répertoire et tout son contenu
            shutil.rmtree(outputs_dir)
            logger.info(f"Répertoire '{outputs_dir}' supprimé avec succès")
            return True
        else:
            logger.debug(f"Le répertoire '{outputs_dir}' n'existe pas, rien à supprimer")
            return False
    except PermissionError as e:
        logger.error(f"Permission refusée lors de la suppression de '{outputs_dir}': {e}")
        return False
    except Exception as e:
        logger.error(f"Erreur lors de la suppression de '{outputs_dir}': {e}", exc_info=True)
        return False

