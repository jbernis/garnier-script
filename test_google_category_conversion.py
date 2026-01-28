#!/usr/bin/env python3
"""
Script de test pour vérifier la conversion des chemins Google Shopping en IDs.
"""

import sys
import os

# Ajouter le répertoire parent au path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from apps.ai_editor.db import AIPromptsDB
import logging

logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)


def test_category_conversion():
    """Teste la conversion de chemins textuels en IDs Google."""
    
    # Initialiser la base de données
    db = AIPromptsDB()
    
    # Exemples de chemins textuels à tester
    test_paths = [
        "Maison et jardin > Linge > Literie",
        "Maison et jardin > Arts de la table > Linge de table",
        "Maison et jardin > Cuisine > Ustensiles de cuisson",
        "Alimentation, boissons et tabac > Boissons > Thé et infusions",
        "Chemin invalide qui n'existe pas",
        "",  # Vide
        "12345",  # Déjà un ID
    ]
    
    logger.info("=" * 70)
    logger.info("TEST: Conversion de chemins Google Shopping en IDs")
    logger.info("=" * 70)
    
    for path in test_paths:
        logger.info(f"\n📝 Test: '{path}'")
        
        if not path:
            logger.info("   → Chemin vide, rien à faire")
            continue
        
        # Vérifier si c'est déjà un ID
        if path.isdigit():
            logger.info(f"   → Déjà un ID numérique: {path}")
            continue
        
        # Vérifier si c'est un chemin (contient " > ")
        if ' > ' in path:
            category_id = db.search_google_category(path)
            if category_id:
                logger.info(f"   ✅ Converti: {path} → ID: {category_id}")
            else:
                logger.warning(f"   ⚠️ ID non trouvé, chemin laissé tel quel: {path}")
        else:
            logger.info(f"   → Format non reconnu (ni ID ni chemin), laissé tel quel: {path}")
    
    logger.info("\n" + "=" * 70)
    logger.info("Test terminé")
    logger.info("=" * 70)
    
    db.close()


if __name__ == "__main__":
    test_category_conversion()
