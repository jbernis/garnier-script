#!/usr/bin/env python3
"""
Script de test pour vérifier le comportement avec les erreurs 502.
Teste deux URLs : une qui retourne 502 et une qui fonctionne.
"""

import sys
import os
import logging
import time
from dotenv import load_dotenv

# Ajouter le répertoire parent au path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from utils.garnier_db import GarnierDB
from utils.app_config import get_garnier_db_path
from garnier.scraper_garnier_module import (
    authenticate, extract_variant_data_from_url,
    wait_for_url_accessible
)

# Configuration du logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Charger les variables d'environnement
load_dotenv()

BASE_URL = os.getenv("BASE_URL_GARNIER", "https://garnier-thiebaut.adsi.me")


def test_variant_extraction(url, code_vl, description):
    """
    Teste l'extraction d'un variant et log le status qui serait inséré.
    
    Args:
        url: URL du variant à tester
        code_vl: Code variant
        description: Description du test
    """
    logger.info(f"\n{'='*80}")
    logger.info(f"TEST: {description}")
    logger.info(f"URL: {url}")
    logger.info(f"Code VL: {code_vl}")
    logger.info(f"{'='*80}\n")
    
    driver = None
    session = None
    
    try:
        # Authentification
        logger.info("Authentification en cours...")
        start_auth = time.time()
        driver, session = authenticate(headless=True)
        auth_time = time.time() - start_auth
        logger.info(f"✓ Authentification réussie en {auth_time:.2f}s")
        
        # Test de l'extraction
        logger.info(f"Début de l'extraction pour {code_vl}...")
        start_extract = time.time()
        
        try:
            result = extract_variant_data_from_url(
                driver, session, url, code_vl, headless=True
            )
            extract_time = time.time() - start_extract
            
            # Gérer les différents cas de retour
            if isinstance(result, tuple) and len(result) == 3:
                variant_data, driver, session = result
            elif isinstance(result, dict):
                variant_data = result
            else:
                variant_data = None
            
            if variant_data:
                logger.info(f"✓ Extraction réussie en {extract_time:.2f}s")
                logger.info(f"  Données extraites:")
                logger.info(f"    - SKU: {variant_data.get('sku', 'N/A')}")
                logger.info(f"    - Gencode: {variant_data.get('gencode', 'N/A')}")
                logger.info(f"    - Prix PA: {variant_data.get('price_pa', 'N/A')}")
                logger.info(f"    - Prix PVC: {variant_data.get('price_pvc', 'N/A')}")
                logger.info(f"    - Stock: {variant_data.get('stock', 'N/A')}")
                logger.info(f"    - Taille: {variant_data.get('size', 'N/A')}")
                logger.info(f"    - Couleur: {variant_data.get('color', 'N/A')}")
                
                # Déterminer le status qui serait inséré
                sku = variant_data.get('sku', '').strip()
                gencode = variant_data.get('gencode', '').strip()
                stock = variant_data.get('stock')
                price_pvc = variant_data.get('price_pvc', '').strip()
                
                if sku and gencode and stock is not None and price_pvc:
                    status = 'completed'
                    logger.info(f"\n✅ STATUS QUI SERAIT INSÉRÉ EN BASE: '{status}'")
                else:
                    status = 'error'
                    error_msg = []
                    if not sku:
                        error_msg.append("SKU manquant")
                    if not gencode:
                        error_msg.append("Gencode manquant")
                    if stock is None:
                        error_msg.append("Stock manquant")
                    if not price_pvc:
                        error_msg.append("Prix PVC manquant")
                    logger.warning(f"\n❌ STATUS QUI SERAIT INSÉRÉ EN BASE: '{status}'")
                    logger.warning(f"   Raison: {', '.join(error_msg)}")
            else:
                extract_time = time.time() - start_extract
                logger.error(f"✗ Extraction échouée en {extract_time:.2f}s - Aucune donnée retournée")
                logger.error(f"\n❌ STATUS QUI SERAIT INSÉRÉ EN BASE: 'error'")
                
        except Exception as e:
            extract_time = time.time() - start_extract
            logger.error(f"✗ Erreur lors de l'extraction en {extract_time:.2f}s: {e}")
            logger.error(f"\n❌ STATUS QUI SERAIT INSÉRÉ EN BASE: 'error'")
            logger.error(f"   Message d'erreur: {str(e)}")
        
        logger.info(f"\n⏱️  Temps total pour {code_vl}: {extract_time:.2f}s")
        
    except Exception as e:
        logger.error(f"✗ Erreur lors du test: {e}", exc_info=True)
    finally:
        # Fermer le driver
        if driver:
            try:
                driver.quit()
            except Exception:
                pass


def test_wait_for_url_accessible(url, code_vl, description):
    """
    Teste la fonction wait_for_url_accessible pour vérifier le timeout.
    
    Args:
        url: URL à tester
        code_vl: Code variant
        description: Description du test
    """
    logger.info(f"\n{'='*80}")
    logger.info(f"TEST wait_for_url_accessible: {description}")
    logger.info(f"URL: {url}")
    logger.info(f"Code VL: {code_vl}")
    logger.info(f"{'='*80}\n")
    
    driver = None
    session = None
    
    try:
        # Authentification
        logger.info("Authentification en cours...")
        driver, session = authenticate(headless=True)
        logger.info("✓ Authentification réussie")
        
        # Test de wait_for_url_accessible avec timeout de 2 minutes
        logger.info(f"Test de wait_for_url_accessible avec timeout de 2 minutes...")
        start_time = time.time()
        
        result = wait_for_url_accessible(session, url, check_interval=30, timeout=10, max_wait_time=120)
        
        elapsed_time = time.time() - start_time
        
        if result:
            logger.info(f"✓ URL accessible après {elapsed_time:.2f}s")
        else:
            logger.warning(f"✗ URL non accessible après {elapsed_time:.2f}s (timeout de 2 minutes)")
        
        logger.info(f"\n⏱️  Temps total pour wait_for_url_accessible: {elapsed_time:.2f}s")
        
    except Exception as e:
        logger.error(f"✗ Erreur lors du test: {e}", exc_info=True)
    finally:
        # Fermer le driver
        if driver:
            try:
                driver.quit()
            except Exception:
                pass


def main():
    """Fonction principale."""
    logger.info("="*80)
    logger.info("SCRIPT DE TEST - Vérification du comportement avec erreurs 502")
    logger.info("="*80)
    
    # Test 1: URL qui retourne 502
    url_502 = "https://garnier-thiebaut.adsi.me/product-page/18750922244C/?code_vl=49378"
    code_vl_502 = "49378"
    
    # Test 2: URL qui fonctionne
    url_ok = "https://garnier-thiebaut.adsi.me/product-page/3465258918C/?code_vl=44834"
    code_vl_ok = "44834"
    
    # Test 1: Extraction avec URL qui retourne 502
    logger.info("\n\n🔴 TEST 1: URL qui retourne 502")
    test_variant_extraction(url_502, code_vl_502, "URL avec erreur 502")
    
    # Petite pause entre les tests
    logger.info("\n\n⏸️  Pause de 2 secondes entre les tests...")
    time.sleep(2)
    
    # Test 2: Extraction avec URL qui fonctionne
    logger.info("\n\n🟢 TEST 2: URL qui fonctionne")
    test_variant_extraction(url_ok, code_vl_ok, "URL fonctionnelle")
    
    # Test 3: Test de wait_for_url_accessible avec l'URL 502
    logger.info("\n\n🔴 TEST 3: wait_for_url_accessible avec URL 502")
    test_wait_for_url_accessible(url_502, code_vl_502, "Test timeout avec URL 502")
    
    logger.info("\n\n" + "="*80)
    logger.info("TESTS TERMINÉS")
    logger.info("="*80)


if __name__ == "__main__":
    main()
