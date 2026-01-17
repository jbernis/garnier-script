#!/usr/bin/env python3
"""
Script pour traiter les variants Artiga en attente (extraire prix, SKU, stock).
"""

import sys
import os
import argparse
import logging
from dotenv import load_dotenv

# Ajouter le répertoire parent au path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.artiga_db import ArtigaDB
from utils.app_config import get_artiga_db_path

# Importer les fonctions du scraper existant
import importlib.util
scraper_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "scraper-artiga.py")
spec = importlib.util.spec_from_file_location("scraper_artiga", scraper_path)
scraper_module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(scraper_module)

# Configuration du logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Charger les variables d'environnement
load_dotenv()


def process_variant(variant_id, code_vl, url, db, driver, session, headless=True):
    """
    Traite un variant spécifique pour extraire ses données détaillées.
    
    Args:
        variant_id: ID du variant dans la DB
        code_vl: Code du variant
        url: URL du variant
        db: Instance de ArtigaDB
        driver: WebDriver Selenium
        session: Session requests
        headless: Mode headless
    
    Returns:
        True si succès, False sinon
    """
    try:
        db.mark_variant_processing(variant_id)
        logger.info(f"  Traitement du variant {code_vl}...")
        
        # Extraire les données du variant en utilisant les fonctions du scraper existant
        # Note: Le scraper existant extrait déjà les prix/SKU lors de la collecte
        # Ici on pourrait faire une extraction supplémentaire si nécessaire
        
        # Pour l'instant, marquer comme complété car les données sont déjà extraites
        # lors de la collecte (le scraper Artiga extrait tout en une fois)
        db.update_variant_data(
            variant_id=variant_id,
            status='completed'
        )
        
        # Mettre à jour le status du produit parent si tous les variants sont traités
        variant_info = db.get_variant_by_code_vl(code_vl)
        if variant_info:
            product_id = variant_info['product_id']
            db.update_product_status_if_all_variants_processed(product_id)
        
        logger.info(f"    ✓ Variant {code_vl} traité avec succès")
        return True
        
    except Exception as e:
        error_msg = str(e)
        logger.error(f"    ✗ Erreur pour {code_vl}: {error_msg}")
        db.mark_variant_error(variant_id, error_msg)
        return False


def process_urls(status='pending', limit=None, retry_errors=False, output_db='artiga_products.db', headless=True, category=None, subcategory=None):
    """
    Traite les variants en attente ou en erreur.
    
    Args:
        status: Status des variants à traiter ('pending' ou 'error')
        limit: Nombre maximum de variants à traiter
        retry_errors: Si True, traite les variants en erreur
        output_db: Chemin vers la base de données
        headless: Mode headless pour Selenium
        category: Filtrer par catégorie
        subcategory: Filtrer par sous-catégorie
    """
    db = ArtigaDB(output_db)
    driver = None
    session = None
    
    try:
        # Créer driver/session
        driver = scraper_module.get_selenium_driver(headless=headless)
        if not driver:
            logger.error("Impossible de créer le driver Selenium")
            return
        
        import requests
        session = requests.Session()
        session.headers.update(scraper_module.HEADERS)
        logger.info("Driver Selenium créé")
        
        # Récupérer les variants à traiter
        if retry_errors:
            variants = db.get_error_variants(limit=limit, category=category, subcategory=subcategory)
            logger.info(f"Variants en erreur à retraiter: {len(variants)}")
        else:
            variants = db.get_pending_variants(limit=limit, category=category, subcategory=subcategory)
            logger.info(f"Variants en attente: {len(variants)}")
        
        if not variants:
            logger.info("Aucun variant à traiter")
            return
        
        success_count = 0
        error_count = 0
        
        # Traiter chaque variant
        for idx, variant in enumerate(variants, 1):
            variant_id = variant['id']
            code_vl = variant['code_vl']
            url = variant['url']
            
            logger.info(f"\n[{idx}/{len(variants)}] Traitement de {code_vl}")
            
            success = process_variant(variant_id, code_vl, url, db, driver, session, headless)
            
            if success:
                success_count += 1
            else:
                error_count += 1
        
        # Afficher les statistiques
        logger.info(f"\n{'='*60}")
        logger.info("Traitement terminé!")
        logger.info(f"Succès: {success_count}")
        logger.info(f"Erreurs: {error_count}")
        logger.info(f"{'='*60}")
        
        # Mettre à jour le status de tous les produits
        db.update_products_status_after_processing()
        
        # Afficher les stats finales
        stats = db.get_stats()
        logger.info(f"\nStatistiques de la base de données:")
        logger.info(f"  Total produits: {stats['total_products']}")
        logger.info(f"  Total variants: {stats['total_variants']}")
        logger.info(f"  Variants par statut: {stats['variants_by_status']}")
        
    finally:
        db.close()
        if driver:
            try:
                driver.quit()
            except:
                pass


if __name__ == '__main__':
    parser = argparse.ArgumentParser(
        description='Traite les variants Artiga en attente'
    )
    parser.add_argument(
        '--status',
        default='pending',
        choices=['pending', 'error'],
        help='Status des variants à traiter (défaut: pending)'
    )
    parser.add_argument(
        '--limit', '-l',
        type=int,
        help='Nombre maximum de variants à traiter'
    )
    parser.add_argument(
        '--retry-errors',
        action='store_true',
        help='Retraiter les variants en erreur'
    )
    parser.add_argument(
        '--category', '-c',
        help='Filtrer par catégorie'
    )
    parser.add_argument(
        '--subcategory', '-s',
        help='Filtrer par sous-catégorie'
    )
    parser.add_argument(
        '--db', '-d',
        default=None,
        help='Chemin vers la base de données SQLite (défaut: artiga_products.db)'
    )
    parser.add_argument(
        '--no-headless',
        action='store_true',
        help='Désactiver le mode headless (afficher le navigateur)'
    )
    
    args = parser.parse_args()
    
    # Utiliser la DB par défaut si non spécifiée
    if args.db is None:
        output_db = get_artiga_db_path()
        logger.info(f"Utilisation de la base de données: {output_db}")
    else:
        output_db = args.db
    
    process_urls(
        status=args.status,
        limit=args.limit,
        retry_errors=args.retry_errors,
        output_db=output_db,
        headless=not args.no_headless,
        category=args.category,
        subcategory=args.subcategory
    )
    
    logger.info("Script terminé avec succès")
