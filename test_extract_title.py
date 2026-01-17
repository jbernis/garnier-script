#!/usr/bin/env python3
"""
Script de test pour extraire et logger le titre d'un produit.
"""

import sys
import os
import time
import logging
from bs4 import BeautifulSoup
from dotenv import load_dotenv

# Ajouter le répertoire parent au path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from garnier.scraper_garnier_module import authenticate

# Configuration du logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Charger les variables d'environnement
load_dotenv()

def extract_title_from_product_page(driver, session, product_url):
    """
    Extrait le titre depuis la page produit.
    Le titre est dans <h3> à l'intérieur de <div class="product-body">
    """
    try:
        logger.info(f"Chargement de la page: {product_url}")
        driver.get(product_url)
        time.sleep(3)
        
        html = driver.page_source
        soup = BeautifulSoup(html, 'html.parser')
        
        # Chercher le h3 dans product-body
        product_body = soup.find('div', class_='product-body')
        if product_body:
            h3_elem = product_body.find('h3')
            if h3_elem:
                title = h3_elem.get_text(strip=True)
                logger.info(f"✓ Titre trouvé: {title}")
                return title
        
        logger.warning("✗ Titre non trouvé dans h3/product-body")
        return None
        
    except Exception as e:
        logger.error(f"✗ Erreur lors de l'extraction: {e}")
        return None

def main():
    product_url = "https://garnier-thiebaut.adsi.me/product-page/18158772357E/?code_vl=49963"
    
    logger.info("=" * 60)
    logger.info("Test d'extraction du titre de produit")
    logger.info("=" * 60)
    
    # Authentification
    logger.info("Authentification en cours...")
    driver, session = authenticate(headless=True)
    
    if not driver:
        logger.error("✗ Impossible de s'authentifier")
        return 1
    
    logger.info("✓ Authentification réussie")
    
    # Extraire le titre
    title = extract_title_from_product_page(driver, session, product_url)
    
    logger.info("=" * 60)
    if title:
        logger.info(f"TITRE EXTRAIT: {title}")
    else:
        logger.error("AUCUN TITRE EXTRAIT")
    logger.info("=" * 60)
    
    # Fermer le navigateur
    if driver:
        driver.quit()
    
    return 0 if title else 1

if __name__ == "__main__":
    sys.exit(main())

