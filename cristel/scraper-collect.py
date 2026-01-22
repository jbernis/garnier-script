#!/usr/bin/env python3
"""
Script pour collecter les produits Cristel et les stocker dans la base de données.
Réutilise les fonctions du scraper-cristel.py existant.
"""

import sys
import os
import argparse
import logging
from dotenv import load_dotenv

# Ajouter le répertoire parent au path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.cristel_db import CristelDB
from utils.app_config import get_cristel_db_path
from csv_config import get_csv_config

# Importer les fonctions du scraper existant
import importlib.util
scraper_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "scraper-cristel.py")
spec = importlib.util.spec_from_file_location("scraper_cristel", scraper_path)
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

BASE_URL = os.getenv("CRISTEL_BASE_URL", "https://www.cristel.fr")


def collect_from_subcategory_url(subcategory_url, category, subcategory_name, output_db='cristel_products.db', headless=True, driver=None, session=None):
    """
    Collecte les produits d'une sous-catégorie spécifique et les stocke dans la base de données.
    
    Args:
        subcategory_url: URL de la sous-catégorie
        category: Nom de la catégorie parent
        subcategory_name: Nom de la sous-catégorie
        output_db: Chemin vers la base de données
        headless: Mode headless pour Selenium
        driver: WebDriver existant (optionnel)
        session: Session requests existante (optionnel)
    
    Returns:
        Tuple (nombre_de_produits_collectés, driver, session)
    """
    db = CristelDB(output_db)
    driver_created = False
    
    try:
        # Créer driver/session si nécessaire
        if driver is None or session is None:
            driver = scraper_module.get_selenium_driver(headless=headless)
            if not driver:
                logger.error("Impossible de créer le driver Selenium")
                return (0, None, None)
            
            import requests
            session = requests.Session()
            session.headers.update(scraper_module.HEADERS)
            driver_created = True
            logger.info("Driver Selenium créé")
        
        # Récupérer le vendor depuis csv_config
        csv_config_manager = get_csv_config()
        vendor_name = csv_config_manager.get_vendor('cristel')
        
        logger.info(f"\n{'='*60}")
        logger.info(f"Traitement de la sous-catégorie: {subcategory_name}")
        logger.info(f"Catégorie: {category}")
        logger.info(f"URL: {subcategory_url}")
        logger.info(f"{'='*60}")
        
        # Obtenir les produits de cette sous-catégorie
        # Pour Cristel, on passe l'URL de la sous-catégorie comme "category_url"
        # et la fonction se chargera d'extraire les produits directement
        # On crée un objet args vide pour éviter les erreurs
        class Args:
            subcategories = None
        
        products = scraper_module.get_products_from_category(
            driver, session, subcategory_url, subcategory_name, Args(), is_subcategory=True
        )
        
        logger.info(f"Produits trouvés: {len(products)}")
        
        if not products:
            logger.warning("Aucun produit trouvé dans cette sous-catégorie")
            return (0, driver, session)
        
        total_products_collected = 0
        
        # Traiter chaque produit
        for idx, product_info in enumerate(products, 1):
            product_code = product_info.get('code', f'CRISTEL-{idx}')
            product_url = product_info.get('url', '')
            product_name = product_info.get('name', f"Produit {product_code}")
            
            logger.info(f"\n  [{idx}/{len(products)}] {product_name}")
            
            try:
                # Extraire les détails complets du produit (y compris les variants)
                logger.info(f"    Extraction des détails depuis {product_url}")
                details, driver, session = scraper_module.get_product_details(
                    driver, session, product_url, product_name, headless=headless
                )
                
                if not details:
                    logger.warning(f"    Impossible d'extraire les détails pour {product_code}")
                    raise Exception("Détails non trouvés")
                
                title = details.get('name') or details.get('full_name') or product_name
                description = details.get('description', '')
                images = details.get('images', [])
                variants = details.get('variants', [])
                
                # Générer le handle
                handle = scraper_module.slugify(title)
                
                # Ajouter le produit dans la DB
                product_id = db.add_product(
                    product_code=product_code,
                    handle=handle,
                    title=title,
                    description=description,
                    vendor=vendor_name,
                    product_type=category,
                    tags=f"{category}, {subcategory_name}",
                    category=category,
                    subcategory=subcategory_name,
                    base_url=product_url
                )
                
                # Ajouter les images
                if images:
                    logger.info(f"    {len(images)} image(s) trouvée(s)")
                    for img_idx, image_url in enumerate(images, 1):
                        db.add_image(product_id, image_url, position=img_idx)
                
                # Ajouter les variants
                variants_added = 0
                if variants:
                    for variant_info in variants:
                        variant_code = variant_info.get('full_code') or variant_info.get('sku') or f"{product_code}-{variants_added+1}"
                        variant_url = variant_info.get('url') or product_url
                        size_text = variant_info.get('size') or variant_info.get('size_text') or ''
                        
                        # Extraire les données du variant si disponibles
                        variant_sku = variant_info.get('sku') or variant_info.get('full_code') or ''
                        variant_gencode = variant_info.get('gencode') or variant_info.get('gtin') or ''
                        variant_price_pvc = variant_info.get('pvc') or variant_info.get('price_pvc') or variant_info.get('price') or ''
                        variant_price_pa = variant_info.get('pa') or variant_info.get('price_pa') or None
                        variant_size = variant_info.get('size') or variant_info.get('size_text') or ''
                        variant_color = variant_info.get('color') or ''
                        variant_stock = variant_info.get('stock') or variant_info.get('inventory') or None
                        
                        try:
                            variant_id, is_new = db.add_variant(
                                product_id=product_id,
                                code_vl=variant_code,
                                url=variant_url,
                                size_text=size_text,
                                raise_on_duplicate=False
                            )
                            
                            # Si les données essentielles sont disponibles, les stocker directement
                            if variant_sku and variant_price_pvc:
                                # Marquer comme completed si toutes les données sont présentes
                                db.update_variant_data(
                                    variant_id=variant_id,
                                    sku=variant_sku,
                                    gencode=variant_gencode if variant_gencode else None,
                                    price_pvc=variant_price_pvc,
                                    price_pa=variant_price_pa if variant_price_pa else None,
                                    stock=variant_stock if variant_stock is not None else None,
                                    size=variant_size if variant_size else None,
                                    color=variant_color if variant_color else None,
                                    status='completed',
                                    error_message=None
                                )
                                variants_added += 1
                                logger.info(f"      ✓ Variant {variant_code} ajouté avec données complètes")
                            else:
                                # Sinon, mettre à jour seulement les champs de base et laisser en pending
                                if not is_new:
                                    db.update_variant_collect(
                                        variant_id=variant_id,
                                        url=variant_url,
                                        size_text=size_text
                                    )
                                variants_added += 1
                                logger.info(f"      ✓ Variant {variant_code} ajouté (données à compléter)")
                        except Exception as variant_error:
                            logger.error(f"      ✗ Erreur variant {variant_code}: {variant_error}")
                
                logger.info(f"    {product_code}: {variants_added} variant(s) collecté(s)")
                
                # Mettre à jour le status du produit si tous les variants sont traités
                db.update_product_status_if_all_variants_processed(product_id)
                
                total_products_collected += 1
                
            except Exception as e:
                error_msg = str(e)
                logger.error(f"    ✗ Erreur pour {product_code}: {error_msg}")
                # Marquer le produit en erreur
                try:
                    product_id = db.add_product(
                        product_code=product_code,
                        handle=scraper_module.slugify(product_code),
                        title=None,
                        vendor=vendor_name,
                        product_type=category,
                        tags=f"{category}, {subcategory_name}",
                        category=category,
                        subcategory=subcategory_name,
                        base_url=product_url,
                        status='error',
                        error_message=error_msg[:500]
                    )
                except:
                    pass
                continue
        
        # Afficher les statistiques
        stats = db.get_stats()
        logger.info(f"\n{'='*60}")
        logger.info("Collecte terminée!")
        logger.info(f"Produits collectés: {total_products_collected}")
        logger.info(f"Total produits en DB: {stats['total_products']}")
        logger.info(f"Total variants en DB: {stats['total_variants']}")
        logger.info(f"{'='*60}")
        
        db.close()
        return (total_products_collected, driver, session)
        
    except Exception as e:
        logger.error(f"Erreur fatale: {e}")
        db.close()
        if driver_created and driver:
            try:
                driver.quit()
            except:
                pass
        raise


def collect_urls(categories=None, subcategories=None, output_db='cristel_products.db', headless=True):
    """
    Collecte les produits de plusieurs catégories/sous-catégories.
    
    Args:
        categories: Liste de catégories à traiter (None = toutes)
        subcategories: Liste de sous-catégories à traiter (None = toutes)
        output_db: Chemin vers la base de données
        headless: Mode headless pour Selenium
    """
    db = CristelDB(output_db)
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
        
        # Obtenir les catégories
        all_categories = scraper_module.get_categories(driver, session)
        logger.info(f"Catégories disponibles: {[cat['name'] for cat in all_categories]}")
        
        # Filtrer les catégories si spécifiées
        if categories:
            category_list = []
            for cat_name in categories:
                for cat in all_categories:
                    if cat['name'] == cat_name:
                        category_list.append(cat)
                        break
                else:
                    logger.warning(f"Catégorie '{cat_name}' non trouvée, ignorée")
        else:
            category_list = all_categories
        
        total_products_collected = 0
        
        # Parcourir chaque catégorie
        for category_info in category_list:
            category_name = category_info['name']
            category_url = category_info['url']
            
            logger.info(f"\n{'='*60}")
            logger.info(f"Traitement de la catégorie: {category_name}")
            logger.info(f"{'='*60}")
            
            # Obtenir les sous-catégories
            all_subcategories = scraper_module.get_subcategories(driver, session, category_url, category_name)
            logger.info(f"Sous-catégories trouvées: {len(all_subcategories)}")
            
            # Filtrer les sous-catégories si spécifiées
            if subcategories:
                subcat_list = []
                for subcat_name in subcategories:
                    for subcat in all_subcategories:
                        if subcat['name'] == subcat_name:
                            subcat_list.append(subcat)
                            break
                    else:
                        logger.warning(f"Sous-catégorie '{subcat_name}' non trouvée")
            else:
                subcat_list = all_subcategories
            
            # Parcourir chaque sous-catégorie
            for subcat_info in subcat_list:
                subcat_name = subcat_info['name']
                subcat_url = subcat_info['url']
                
                count, driver, session = collect_from_subcategory_url(
                    subcat_url, category_name, subcat_name, output_db, headless, driver, session
                )
                total_products_collected += count
        
        logger.info(f"\n{'='*60}")
        logger.info(f"Collecte totale terminée: {total_products_collected} produits")
        logger.info(f"{'='*60}")
        
    finally:
        db.close()
        if driver:
            try:
                driver.quit()
            except:
                pass


if __name__ == '__main__':
    parser = argparse.ArgumentParser(
        description='Collecte les produits Cristel et les stocke dans la base de données'
    )
    parser.add_argument(
        '--category', '-c',
        action='append',
        help='Catégorie(s) à traiter (peut être répété plusieurs fois)'
    )
    parser.add_argument(
        '--subcategory', '-s',
        action='append',
        help='Sous-catégorie(s) à traiter (peut être répété plusieurs fois)'
    )
    parser.add_argument(
        '--db', '-d',
        default=None,
        help='Chemin vers la base de données SQLite (défaut: cristel_products.db)'
    )
    parser.add_argument(
        '--no-headless',
        action='store_true',
        help='Désactiver le mode headless (afficher le navigateur)'
    )
    
    args = parser.parse_args()
    
    # Utiliser la DB par défaut si non spécifiée
    if args.db is None:
        output_db = get_cristel_db_path()
        logger.info(f"Utilisation de la base de données: {output_db}")
    else:
        output_db = args.db
    
    collect_urls(
        categories=args.category,
        subcategories=args.subcategory,
        output_db=output_db,
        headless=not args.no_headless
    )
    
    logger.info("Script terminé avec succès")
