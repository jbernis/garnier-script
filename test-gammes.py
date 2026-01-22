#!/usr/bin/env python3
"""
Script de test pour récupérer uniquement les gammes depuis le site Garnier-Thiebaut.
Basé sur le code du script général.
"""

import sys
import os
import argparse
import logging

# Essayer de charger dotenv si disponible
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass  # dotenv non disponible, continuer sans

# Ajouter le répertoire parent au path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from garnier.scraper_garnier_module import (
    authenticate, get_categories, get_gammes_from_category
)

# Configuration du logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def test_gammes(category_name=None, headless=True):
    """
    Teste la récupération des gammes.
    
    Args:
        category_name: Nom de la catégorie à tester (None = toutes les catégories)
        headless: Mode headless pour Selenium
    """
    driver = None
    
    try:
        # Authentification
        logger.info("🔐 Authentification en cours...")
        driver, session = authenticate(headless=headless)
        if not driver:
            logger.error("✗ Impossible de s'authentifier")
            return
        
        logger.info("✓ Authentification réussie\n")
        
        # Récupérer les catégories
        logger.info("Récupération des catégories...")
        all_categories = get_categories(driver, session)
        logger.info(f"✓ {len(all_categories)} catégorie(s) trouvée(s)\n")
        
        # Filtrer les catégories si spécifiées
        if category_name:
            category_list = []
            for cat in all_categories:
                if cat['name'] == category_name:
                    category_list.append(cat)
                    break
            if not category_list:
                logger.error(f"Catégorie '{category_name}' non trouvée")
                logger.info(f"Catégories disponibles: {[cat['name'] for cat in all_categories]}")
                return
        else:
            category_list = all_categories
        
        # Parcourir chaque catégorie
        total_gammes = 0
        for category_info in category_list:
            category_name = category_info['name']
            category_url = category_info['url']
            
            logger.info(f"\n{'='*60}")
            logger.info(f"Catégorie: {category_name}")
            logger.info(f"URL: {category_url}")
            logger.info(f"{'='*60}")
            
            # Récupérer les gammes de cette catégorie (avec pagination automatique)
            logger.info("Extraction des gammes (avec pagination automatique)...")
            gammes = get_gammes_from_category(driver, session, category_url)
            
            logger.info(f"\n✓ {len(gammes)} gamme(s) trouvée(s) dans la catégorie '{category_name}' (toutes pages confondues):\n")
            
            # Afficher les gammes
            for idx, gamme in enumerate(gammes, 1):
                logger.info(f"  {idx}. {gamme['name']}")
                logger.info(f"     URL: {gamme['url']}")
            
            total_gammes += len(gammes)
        
        logger.info(f"\n{'='*60}")
        logger.info(f"Total: {total_gammes} gamme(s) trouvée(s)")
        logger.info(f"{'='*60}\n")
        
    except Exception as e:
        logger.error(f"Erreur lors du test: {e}", exc_info=True)
    finally:
        if driver:
            driver.quit()


if __name__ == '__main__':
    parser = argparse.ArgumentParser(
        description='Test de récupération des gammes depuis le site Garnier-Thiebaut'
    )
    parser.add_argument(
        '--category', '-c',
        help='Nom de la catégorie à tester (optionnel, par défaut toutes les catégories)'
    )
    parser.add_argument(
        '--no-headless',
        action='store_true',
        help='Désactiver le mode headless (afficher le navigateur)'
    )
    
    args = parser.parse_args()
    
    test_gammes(
        category_name=args.category,
        headless=not args.no_headless
    )
