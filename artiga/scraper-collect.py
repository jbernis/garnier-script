#!/usr/bin/env python3
"""
Script pour collecter les produits Artiga et les stocker dans la base de données.
Réutilise les fonctions du scraper-artiga.py existant.
"""

import sys
import os
import argparse
import logging
import time
from dotenv import load_dotenv
from requests.exceptions import RequestException, Timeout, ConnectionError

# Ajouter le répertoire parent au path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.artiga_db import ArtigaDB
from utils.app_config import get_artiga_db_path
from csv_config import get_csv_config

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

BASE_URL = os.getenv("ARTIGA_BASE_URL", "https://www.artiga.fr")


def collect_from_subcategory_url(subcategory_url, category, subcategory_name, output_db='artiga_products.db', headless=True, driver=None, session=None, retry_errors_after=False):
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
    db = ArtigaDB(output_db)
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
        vendor_name = csv_config_manager.get_vendor('artiga')
        
        logger.info(f"\n{'='*60}")
        logger.info(f"Traitement de la sous-catégorie: {subcategory_name}")
        logger.info(f"Catégorie: {category}")
        logger.info(f"URL: {subcategory_url}")
        logger.info(f"{'='*60}")
        
        # Récupérer les produits en erreur pour les retenter (max 3 tentatives)
        cursor = db.conn.cursor()
        cursor.execute('''
            SELECT product_code, base_url 
            FROM products 
            WHERE status = 'error' 
            AND category = ?
            AND subcategory = ?
            AND (retry_count IS NULL OR retry_count < 3)
        ''', (category, subcategory_name))
        error_products = cursor.fetchall()
        
        if error_products:
            logger.info(f"\n🔄 Retraitement de {len(error_products)} produit(s) en erreur...")
            
            for error_product in error_products:
                product_code = error_product['product_code']
                product_url = error_product['base_url']
                
                if not product_url:
                    logger.warning(f"  ✗ Produit {product_code}: Pas d'URL trouvée, retry ignoré")
                    continue
                
                # Vérifier que l'URL retourne 200 avant de retenter
                logger.info(f"  Vérification HTTP 200 pour le produit {product_code} (en erreur) avant retry...")
                url_returns_200 = False
                try:
                    response = session.get(product_url, timeout=10, allow_redirects=True)
                    if response.status_code == 200:
                        url_returns_200 = True
                        logger.info(f"  ✓ Produit {product_code}: URL retourne 200 - Retry autorisé")
                    else:
                        logger.warning(f"  ✗ Produit {product_code}: URL retourne {response.status_code} - Retry ignoré")
                except Exception as check_error:
                    logger.warning(f"  ✗ Produit {product_code}: URL non accessible - Retry ignoré")
                
                # Si l'URL ne retourne pas 200, attendre jusqu'à 2 minutes
                if not url_returns_200:
                    logger.info(f"  Attente que l'URL retourne 200 pour {product_code} (max 2 minutes)...")
                    start_wait = time.time()
                    max_wait_for_error = 120  # 2 minutes maximum
                    url_became_accessible = False
                    
                    while time.time() - start_wait < max_wait_for_error:
                        try:
                            response = session.get(product_url, timeout=10, allow_redirects=True)
                            if response.status_code == 200:
                                url_became_accessible = True
                                logger.info(f"  ✓ Produit {product_code}: URL retourne maintenant 200 après attente")
                                break
                        except Exception:
                            pass
                        time.sleep(10)  # Vérifier toutes les 10 secondes
                    
                    if url_became_accessible:
                        url_returns_200 = True
                    else:
                        logger.warning(f"  ✗ Produit {product_code}: URL toujours inaccessible après {max_wait_for_error}s, ignoré")
                
                # Si l'URL retourne 200, marquer pour retry
                if url_returns_200:
                    cursor.execute('''
                        UPDATE products 
                        SET retry_count = COALESCE(retry_count, 0) + 1,
                            error_message = NULL,
                            updated_at = CURRENT_TIMESTAMP
                        WHERE product_code = ?
                    ''', (product_code,))
                    logger.info(f"  ✓ Produit {product_code} marqué pour retraitement (retry_count incrémenté, status reste 'error')")
                else:
                    logger.warning(f"  ✗ Produit {product_code} ignoré (URL ne retourne pas 200)")
            
            db.conn.commit()
            logger.info(f"✓ Produits vérifiés et marqués pour retraitement\n")
        
        # Récupérer les variants en erreur pour les retenter (max 3 tentatives)
        cursor.execute('''
            SELECT pv.id, pv.code_vl, pv.url, pv.error_message, p.product_code, p.base_url, p.id as product_id
            FROM product_variants pv
            JOIN products p ON pv.product_id = p.id
            WHERE pv.status = 'error'
            AND p.category = ?
            AND p.subcategory = ?
            AND (pv.retry_count IS NULL OR pv.retry_count < 3)
        ''', (category, subcategory_name))
        error_variants = cursor.fetchall()
        
        if error_variants:
            logger.info(f"\n🔄 Retraitement de {len(error_variants)} variant(s) en erreur...")
            
            for error_variant in error_variants:
                variant_id = error_variant['id']
                variant_code = error_variant['code_vl']
                product_url = error_variant['base_url']
                product_id = error_variant['product_id']
                
                if not product_url:
                    logger.warning(f"  ✗ Variant {variant_code}: Pas d'URL produit trouvée, retry ignoré")
                    continue
                
                # Vérifier que l'URL retourne 200 avant de retenter
                logger.info(f"  Vérification HTTP 200 pour le variant {variant_code} (en erreur) avant retry...")
                url_returns_200 = False
                try:
                    response = session.get(product_url, timeout=10, allow_redirects=True)
                    if response.status_code == 200:
                        url_returns_200 = True
                        logger.info(f"  ✓ Variant {variant_code}: URL retourne 200 - Retry autorisé")
                    else:
                        logger.warning(f"  ✗ Variant {variant_code}: URL retourne {response.status_code} - Retry ignoré")
                except Exception as check_error:
                    logger.warning(f"  ✗ Variant {variant_code}: URL non accessible - Retry ignoré")
                
                # Si l'URL ne retourne pas 200, attendre jusqu'à 2 minutes
                if not url_returns_200:
                    logger.info(f"  Attente que l'URL retourne 200 pour {variant_code} (max 2 minutes)...")
                    start_wait = time.time()
                    max_wait_for_error = 120  # 2 minutes maximum
                    url_became_accessible = False
                    
                    while time.time() - start_wait < max_wait_for_error:
                        try:
                            response = session.get(product_url, timeout=10, allow_redirects=True)
                            if response.status_code == 200:
                                url_became_accessible = True
                                logger.info(f"  ✓ Variant {variant_code}: URL retourne maintenant 200 après attente")
                                break
                        except Exception:
                            pass
                        time.sleep(10)  # Vérifier toutes les 10 secondes
                    
                    if url_became_accessible:
                        url_returns_200 = True
                    else:
                        logger.warning(f"  ✗ Variant {variant_code}: URL toujours inaccessible après {max_wait_for_error}s, ignoré")
                
                # Si l'URL retourne 200, retenter l'extraction
                if url_returns_200:
                    try:
                        # Incrémenter retry_count
                        cursor.execute('''
                            UPDATE product_variants 
                            SET retry_count = COALESCE(retry_count, 0) + 1,
                                updated_at = CURRENT_TIMESTAMP
                            WHERE id = ?
                        ''', (variant_id,))
                        db.conn.commit()
                        
                        # Réextraire les données du produit pour obtenir les variants mis à jour
                        logger.info(f"  Retry variant {variant_code}: Réextraction depuis {product_url}")
                        product_name = error_variant['product_code']
                        details, driver, session = scraper_module.get_product_details(
                            driver, session, product_url, product_name, headless=headless
                        )
                        
                        if details and details.get('variants'):
                            # Chercher le variant correspondant dans les détails
                            variant_found = False
                            for variant_info in details.get('variants', []):
                                variant_info_code = variant_info.get('full_code') or variant_info.get('sku') or variant_info.get('code') or ''
                                if variant_info_code == variant_code or variant_info.get('code_vl') == variant_code:
                                    variant_found = True
                                    
                                    # Extraire les données du variant
                                    variant_sku = variant_info.get('sku') or variant_info.get('full_code') or ''
                                    variant_gencode = variant_info.get('gencode') or ''
                                    variant_price_pvc = variant_info.get('pvc') or variant_info.get('price_pvc') or ''
                                    variant_price_pa = variant_info.get('pa') or variant_info.get('price_pa') or None
                                    variant_size = variant_info.get('size') or ''
                                    variant_color = variant_info.get('color') or ''
                                    
                                    # Vérifier si toutes les données sont présentes maintenant
                                    missing_fields = []
                                    if not variant_sku or not variant_sku.strip():
                                        missing_fields.append('SKU')
                                    if not variant_gencode or not variant_gencode.strip():
                                        missing_fields.append('gencode')
                                    if not variant_price_pvc or not variant_price_pvc.strip():
                                        missing_fields.append('prix')
                                    
                                    if missing_fields:
                                        error_msg = f"Champ(s) manquant(s): {', '.join(missing_fields)}"
                                        db.update_variant_data(
                                            variant_id=variant_id,
                                            sku=variant_sku if variant_sku else None,
                                            gencode=variant_gencode if variant_gencode else None,
                                            price_pvc=variant_price_pvc if variant_price_pvc else None,
                                            price_pa=variant_price_pa if variant_price_pa else None,
                                            size=variant_size if variant_size else None,
                                            color=variant_color if variant_color else None,
                                            status='error',
                                            error_message=error_msg
                                        )
                                        logger.warning(f"  ✗ Variant {variant_code} toujours en erreur après retry: {error_msg}")
                                    else:
                                        # Toutes les données sont présentes, marquer comme completed
                                        db.update_variant_data(
                                            variant_id=variant_id,
                                            sku=variant_sku,
                                            gencode=variant_gencode,
                                            price_pvc=variant_price_pvc,
                                            price_pa=variant_price_pa,
                                            size=variant_size if variant_size else None,
                                            color=variant_color if variant_color else None,
                                            status='completed',
                                            error_message=None
                                        )
                                        logger.info(f"  ✓ Variant {variant_code} récupéré avec succès après retry")
                                    
                                    break
                            
                            if not variant_found:
                                logger.warning(f"  ✗ Variant {variant_code} non trouvé dans les détails du produit après retry")
                        else:
                            logger.warning(f"  ✗ Impossible de réextraire les détails du produit pour {variant_code}")
                    except Exception as retry_error:
                        logger.warning(f"  ✗ Erreur lors du retry pour {variant_code}: {retry_error}")
                else:
                    logger.warning(f"  ✗ Variant {variant_code} ignoré (URL ne retourne pas 200)")
            
            logger.info(f"✓ Variants vérifiés et retraités\n")
        
        # Obtenir les produits de cette sous-catégorie
        products = scraper_module.get_products_from_subcategory(
            driver, session, subcategory_url, subcategory_name
        )
        
        logger.info(f"Produits trouvés: {len(products)}")
        
        if not products:
            logger.warning("Aucun produit trouvé dans cette sous-catégorie")
            return (0, driver, session)
        
        total_products_collected = 0
        
        # Traiter chaque produit
        for idx, product_info in enumerate(products, 1):
            product_url = product_info.get('url', '')
            product_name = product_info.get('name', f"Produit {idx}")
            
            logger.info(f"\n  [{idx}/{len(products)}] {product_name}")
            
            try:
                # Extraire les détails complets du produit (comme dans l'ancien script)
                details, driver, session = scraper_module.get_product_details(
                    driver, session, product_url, product_name, headless=headless
                )
                
                if not details:
                    logger.warning(f"    ⚠ Aucun détail trouvé pour {product_name}")
                    # Créer un produit minimal en erreur
                    try:
                        product_id = db.add_product(
                            product_code=f'ARTIGA-{idx}',
                            handle=scraper_module.slugify(product_name),
                            title=product_name,
                            vendor=vendor_name,
                            product_type=category,
                            tags=f"{category}, {subcategory_name}",
                            category=category,
                            subcategory=subcategory_name,
                            base_url=product_url,
                            status='error',
                            error_message='Aucun détail trouvé'
                        )
                    except:
                        pass
                    continue
                
                # Extraire les informations depuis details
                product_code = details.get('code', f'ARTIGA-{idx}')
                title = details.get('name') or details.get('full_name') or product_name
                description = details.get('description', '')
                images = details.get('images', [])
                variants = details.get('variants', [])
                
                # Générer le handle
                handle = scraper_module.slugify(title)
                
                # Ajouter le produit dans la DB (sans is_new car n'existe pas pour Artiga)
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
                
                # Mettre à jour le status du produit à 'pending' (il a des détails)
                db.update_product_status(product_id, status='pending')
                
                # Ajouter les images
                if images:
                    logger.info(f"    {len(images)} image(s) trouvée(s)")
                    for img_idx, image_url in enumerate(images, 1):
                        db.add_image(product_id, image_url, position=img_idx)
                
                # Ajouter les variants avec leurs données complètes
                variants_added = 0
                variants_with_errors = 0
                
                if variants:
                    logger.info(f"    {len(variants)} variant(s) trouvé(s)")
                    for variant_info in variants:
                        variant_code = variant_info.get('full_code') or variant_info.get('sku') or variant_info.get('code') or f"{product_code}-{variants_added+1}"
                        variant_url = variant_info.get('url') or product_url
                        size_text = variant_info.get('size') or variant_info.get('size_text') or ''
                        variant_sku = variant_info.get('sku') or variant_info.get('full_code') or ''
                        variant_gencode = variant_info.get('gencode') or ''
                        variant_price_pvc = variant_info.get('pvc') or variant_info.get('price_pvc') or ''
                        variant_price_pa = variant_info.get('pa') or variant_info.get('price_pa') or None
                        variant_size = variant_info.get('size') or ''
                        variant_color = variant_info.get('color') or ''
                        
                        try:
                            variant_id, is_new = db.add_variant(
                                product_id=product_id,
                                code_vl=variant_code,
                                url=variant_url,
                                size_text=size_text,
                                raise_on_duplicate=False
                            )
                            
                            # Mettre à jour les données complètes du variant (SKU, gencode, prix)
                            # Status sera déterminé selon si SKU/gencode/prix sont présents
                            variant_status = 'pending'
                            variant_error_msg = None
                            
                            # Vérifier si SKU, gencode ET prix sont présents
                            missing_fields = []
                            if not variant_sku or not variant_sku.strip():
                                missing_fields.append('SKU')
                            if not variant_gencode or not variant_gencode.strip():
                                missing_fields.append('gencode')
                            if not variant_price_pvc or not variant_price_pvc.strip():
                                missing_fields.append('prix')
                            
                            if missing_fields:
                                variant_status = 'error'
                                variant_error_msg = f"Champ(s) manquant(s): {', '.join(missing_fields)}"
                                variants_with_errors += 1
                            else:
                                variant_status = 'completed'
                            
                            # Mettre à jour les données du variant
                            db.update_variant_data(
                                variant_id=variant_id,
                                sku=variant_sku if variant_sku else None,
                                gencode=variant_gencode if variant_gencode else None,
                                price_pvc=variant_price_pvc if variant_price_pvc else None,
                                price_pa=variant_price_pa if variant_price_pa else None,
                                size=variant_size if variant_size else None,
                                color=variant_color if variant_color else None,
                                status=variant_status,
                                error_message=variant_error_msg
                            )
                            
                            variants_added += 1
                            if variant_status == 'completed':
                                logger.info(f"      ✓ Variant {variant_code} ajouté/mis à jour (SKU: {variant_sku}, Gencode: {variant_gencode}, Prix: {variant_price_pvc})")
                            else:
                                logger.warning(f"      ⚠ Variant {variant_code} ajouté/mis à jour mais en erreur: {variant_error_msg}")
                        except Exception as variant_error:
                            logger.error(f"      ✗ Erreur variant {variant_code}: {variant_error}")
                            variants_with_errors += 1
                else:
                    logger.warning(f"    ⚠ Aucun variant trouvé pour {product_name}")
                    # Marquer le produit en erreur si aucun variant
                    db.update_product_status(product_id, status='error', error_message='Aucun variant trouvé')
                
                # Mettre à jour le status du produit selon les variants
                db.update_product_status_if_all_variants_processed(product_id)
                
                logger.info(f"    {product_code}: {variants_added} variant(s) collecté(s) ({variants_with_errors} en erreur)")
                total_products_collected += 1
                
                # Petite pause pour ne pas surcharger le serveur
                time.sleep(0.5)
                
            except Exception as e:
                error_msg = str(e)
                logger.warning(f"    Erreur lors de l'extraction pour {product_name}: {error_msg}")
                
                # Retry jusqu'à 3 fois avec vérification HTTP 200 avant chaque tentative
                max_retries = 3
                retry_success = False
                
                for retry_attempt in range(1, max_retries + 1):
                    logger.info(f"    Tentative de retry {retry_attempt}/{max_retries} pour {product_name}...")
                    
                    # Vérifier que l'URL retourne 200 avant chaque retry
                    url_returns_200 = False
                    try:
                        logger.info(f"    Vérification HTTP 200 avant retry {retry_attempt}...")
                        response = session.get(product_url, timeout=10, allow_redirects=True)
                        if response.status_code == 200:
                            url_returns_200 = True
                            logger.info(f"    ✓ URL retourne 200 - Retry {retry_attempt} autorisé")
                        else:
                            logger.warning(f"    ✗ URL retourne {response.status_code} (pas 200)")
                    except (Timeout, ConnectionError, RequestException) as url_error:
                        logger.warning(f"    ✗ URL non accessible: {url_error}")
                    
                    # Si l'URL ne retourne pas 200, attendre jusqu'à 2 minutes
                    if not url_returns_200:
                        logger.info(f"    Attente que l'URL retourne 200 (max 2 minutes)...")
                        start_wait = time.time()
                        max_wait_for_retry = 120  # 2 minutes maximum
                        url_became_accessible = False
                        
                        while time.time() - start_wait < max_wait_for_retry:
                            try:
                                response = session.get(product_url, timeout=10, allow_redirects=True)
                                if response.status_code == 200:
                                    url_became_accessible = True
                                    logger.info(f"    ✓ URL retourne maintenant 200 après attente - Retry {retry_attempt} autorisé")
                                    break
                            except Exception:
                                pass
                            time.sleep(10)  # Vérifier toutes les 10 secondes
                        
                        if url_became_accessible:
                            url_returns_200 = True
                        else:
                            logger.warning(f"    ✗ URL n'est pas devenue accessible après {max_wait_for_retry}s, abandon du retry")
                    
                    # Retry uniquement si l'URL retourne 200
                    if url_returns_200:
                        try:
                            logger.info(f"    Retry {retry_attempt}: Extraction des détails depuis: {product_url}")
                            details, driver, session = scraper_module.get_product_details(
                                driver, session, product_url, product_name, headless=headless
                            )
                            
                            if not details:
                                raise Exception("Aucun détail trouvé après retry")
                            
                            # Extraire les informations depuis details
                            product_code = details.get('code', f'ARTIGA-{idx}')
                            title = details.get('name') or details.get('full_name') or product_name
                            description = details.get('description', '')
                            images = details.get('images', [])
                            variants = details.get('variants', [])
                            
                            # Générer le handle
                            handle = scraper_module.slugify(title)
                            
                            # Ajouter le produit dans la DB (sans is_new)
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
                            
                            # Mettre à jour le status du produit à 'pending'
                            db.update_product_status(product_id, status='pending')
                            
                            # Ajouter les images
                            if images:
                                logger.info(f"    {len(images)} image(s) trouvée(s)")
                                for img_idx, image_url in enumerate(images, 1):
                                    db.add_image(product_id, image_url, position=img_idx)
                            
                            # Ajouter les variants avec leurs données complètes
                            variants_added = 0
                            variants_with_errors = 0
                            
                            if variants:
                                logger.info(f"    {len(variants)} variant(s) trouvé(s)")
                                for variant_info in variants:
                                    variant_code = variant_info.get('full_code') or variant_info.get('sku') or variant_info.get('code') or f"{product_code}-{variants_added+1}"
                                    variant_url = variant_info.get('url') or product_url
                                    size_text = variant_info.get('size') or variant_info.get('size_text') or ''
                                    variant_sku = variant_info.get('sku') or variant_info.get('full_code') or ''
                                    variant_gencode = variant_info.get('gencode') or ''
                                    variant_price_pvc = variant_info.get('pvc') or variant_info.get('price_pvc') or ''
                                    variant_price_pa = variant_info.get('pa') or variant_info.get('price_pa') or None
                                    variant_size = variant_info.get('size') or ''
                                    variant_color = variant_info.get('color') or ''
                                    
                                    variant_id, is_new = db.add_variant(
                                        product_id=product_id,
                                        code_vl=variant_code,
                                        url=variant_url,
                                        size_text=size_text,
                                        raise_on_duplicate=False
                                    )
                                    
                                    # Déterminer le status selon SKU/gencode
                                    variant_status = 'pending'
                                    variant_error_msg = None
                                    
                                    if not variant_sku and not variant_gencode:
                                        variant_status = 'error'
                                        variant_error_msg = 'SKU et gencode manquants'
                                        variants_with_errors += 1
                                    elif not variant_sku:
                                        variant_status = 'error'
                                        variant_error_msg = 'SKU manquant'
                                        variants_with_errors += 1
                                    elif not variant_gencode:
                                        variant_status = 'error'
                                        variant_error_msg = 'Gencode manquant'
                                        variants_with_errors += 1
                                    else:
                                        variant_status = 'completed'
                                    
                                    # Mettre à jour les données du variant
                                    db.update_variant_data(
                                        variant_id=variant_id,
                                        sku=variant_sku if variant_sku else None,
                                        gencode=variant_gencode if variant_gencode else None,
                                        price_pvc=variant_price_pvc if variant_price_pvc else None,
                                        price_pa=variant_price_pa if variant_price_pa else None,
                                        size=variant_size if variant_size else None,
                                        color=variant_color if variant_color else None,
                                        status=variant_status,
                                        error_message=variant_error_msg
                                    )
                                    
                                    variants_added += 1
                            
                            # Mettre à jour le status du produit selon les variants
                            db.update_product_status_if_all_variants_processed(product_id)
                            
                            logger.info(f"    {product_code}: {variants_added} variant(s) collecté(s) ({variants_with_errors} en erreur) (après retry {retry_attempt})")
                            total_products_collected += 1
                            retry_success = True
                            break  # Sortir de la boucle de retry
                            
                        except Exception as retry_error:
                            logger.warning(f"    ✗ Retry {retry_attempt} échoué: {retry_error}")
                            if retry_attempt < max_retries:
                                logger.info(f"    Nouvelle tentative dans 2 secondes...")
                                time.sleep(2)
                            else:
                                logger.error(f"    ✗ Tous les retries ont échoué ({max_retries} tentatives)")
                    else:
                        logger.warning(f"    ✗ Retry {retry_attempt} annulé (URL ne retourne pas 200)")
                        if retry_attempt < max_retries:
                            logger.info(f"    Nouvelle tentative dans 2 secondes...")
                            time.sleep(2)
                
                # Si tous les retries ont échoué, marquer en erreur et continuer
                if not retry_success:
                    error_msg_final = f"Erreur persistante après {max_retries} tentatives: {error_msg}"
                    logger.error(f"    {error_msg_final}")
                    # Marquer le produit en erreur
                    try:
                        cursor.execute('SELECT id FROM products WHERE product_code = ?', (product_info.get('code', f'ARTIGA-{idx}'),))
                        row = cursor.fetchone()
                        if row:
                            product_id = row['id']
                            cursor.execute('''
                                UPDATE products 
                                SET status = 'error', 
                                    error_message = ?,
                                    retry_count = COALESCE(retry_count, 0) + 1,
                                    updated_at = CURRENT_TIMESTAMP
                                WHERE id = ?
                            ''', (error_msg_final[:500], product_id))
                        else:
                            # Créer le produit en erreur
                            handle = scraper_module.slugify(product_name)
                            product_id = db.add_product(
                                product_code=f'ARTIGA-{idx}',
                                handle=handle,
                                title=None,
                                vendor=vendor_name,
                                product_type=category,
                                tags=f"{category}, {subcategory_name}",
                                category=category,
                                subcategory=subcategory_name,
                                base_url=product_url,
                                status='error',
                                error_message=error_msg_final[:500]
                            )
                        
                        # Marquer aussi les variants en erreur s'ils existent
                        cursor.execute('''
                            UPDATE product_variants 
                            SET status = 'error', error_message = ?, updated_at = CURRENT_TIMESTAMP
                            WHERE product_id = ?
                        ''', (error_msg_final[:500], product_id))
                        db.conn.commit()
                        logger.warning(f"    Produit marqué en erreur dans la DB (retry_count incrémenté)")
                    except Exception as db_error:
                        logger.warning(f"    Impossible de marquer le produit en erreur dans la DB: {db_error}")
                    continue
        
        # Afficher les statistiques
        stats = db.get_stats()
        error_count = stats.get('variants_by_status', {}).get('error', 0)
        completed_count = stats.get('variants_by_status', {}).get('completed', 0)
        
        logger.info(f"\n{'='*60}")
        logger.info("Collecte terminée!")
        logger.info(f"Produits collectés: {total_products_collected}")
        logger.info(f"Total produits en DB: {stats['total_products']}")
        logger.info(f"Total variants en DB: {stats['total_variants']}")
        logger.info(f"Variants complétés: {completed_count}")
        logger.info(f"Variants en erreur: {error_count}")
        
        # Avertir si des erreurs sont présentes
        if error_count > 0:
            logger.warning(f"⚠️  ATTENTION: {error_count} variant(s) en erreur dans la base de données")
            logger.warning(f"   Le fichier CSV généré comportera des erreurs")
        
        logger.info(f"{'='*60}")
        
        # Retry automatique si demandé
        if retry_errors_after:
            retry_error_products_and_variants(db, driver, session, category=category, subcategory=subcategory_name, headless=headless)
        
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


def retry_error_products_and_variants(db, driver, session, category=None, subcategory=None, headless=True):
    """
    Retente automatiquement les produits et variants en erreur après la collecte initiale.
    Pour chaque produit/variant, fait jusqu'à 3 tentatives avec vérification HTTP 200.
    
    Args:
        db: Instance ArtigaDB
        driver: WebDriver Selenium
        session: Session requests
        category: Catégorie à filtrer (optionnel)
        subcategory: Sous-catégorie à filtrer (optionnel)
        headless: Mode headless
    
    Returns:
        Tuple (nombre_produits_corrigés, nombre_variants_corrigés)
    """
    cursor = db.conn.cursor()
    
    # Récupérer les produits en erreur (retry_count < 3)
    if category and subcategory:
        cursor.execute('''
            SELECT product_code, base_url, retry_count, id
            FROM products 
            WHERE status = 'error' 
            AND category = ?
            AND subcategory = ?
            AND (retry_count IS NULL OR retry_count < 3)
        ''', (category, subcategory))
    elif category:
        cursor.execute('''
            SELECT product_code, base_url, retry_count, id
            FROM products 
            WHERE status = 'error' 
            AND category = ?
            AND (retry_count IS NULL OR retry_count < 3)
        ''', (category,))
    elif subcategory:
        cursor.execute('''
            SELECT product_code, base_url, retry_count, id
            FROM products 
            WHERE status = 'error' 
            AND subcategory = ?
            AND (retry_count IS NULL OR retry_count < 3)
        ''', (subcategory,))
    else:
        cursor.execute('''
            SELECT product_code, base_url, retry_count, id
            FROM products 
            WHERE status = 'error'
            AND (retry_count IS NULL OR retry_count < 3)
        ''')
    
    error_products = cursor.fetchall()
    
    # Récupérer les variants en erreur (retry_count < 3)
    if category and subcategory:
        cursor.execute('''
            SELECT pv.id, pv.code_vl, pv.url, pv.error_message, p.product_code, p.base_url, p.id as product_id, pv.retry_count
            FROM product_variants pv
            JOIN products p ON pv.product_id = p.id
            WHERE pv.status = 'error'
            AND p.category = ?
            AND p.subcategory = ?
            AND (pv.retry_count IS NULL OR pv.retry_count < 3)
        ''', (category, subcategory))
    elif category:
        cursor.execute('''
            SELECT pv.id, pv.code_vl, pv.url, pv.error_message, p.product_code, p.base_url, p.id as product_id, pv.retry_count
            FROM product_variants pv
            JOIN products p ON pv.product_id = p.id
            WHERE pv.status = 'error'
            AND p.category = ?
            AND (pv.retry_count IS NULL OR pv.retry_count < 3)
        ''', (category,))
    elif subcategory:
        cursor.execute('''
            SELECT pv.id, pv.code_vl, pv.url, pv.error_message, p.product_code, p.base_url, p.id as product_id, pv.retry_count
            FROM product_variants pv
            JOIN products p ON pv.product_id = p.id
            WHERE pv.status = 'error'
            AND p.subcategory = ?
            AND (pv.retry_count IS NULL OR pv.retry_count < 3)
        ''', (subcategory,))
    else:
        cursor.execute('''
            SELECT pv.id, pv.code_vl, pv.url, pv.error_message, p.product_code, p.base_url, p.id as product_id, pv.retry_count
            FROM product_variants pv
            JOIN products p ON pv.product_id = p.id
            WHERE pv.status = 'error'
            AND (pv.retry_count IS NULL OR pv.retry_count < 3)
        ''')
    
    error_variants = cursor.fetchall()
    
    if not error_products and not error_variants:
        logger.info("✓ Aucun produit ou variant en erreur à retenter")
        return (0, 0)
    
    logger.info(f"\n{'='*60}")
    logger.info(f"🔄 RETRY AUTOMATIQUE DES ERREURS")
    logger.info(f"{'='*60}")
    logger.info(f"Produits en erreur à retenter : {len(error_products)}")
    logger.info(f"Variants en erreur à retenter : {len(error_variants)}")
    
    csv_config_manager = get_csv_config()
    vendor_name = csv_config_manager.get_vendor('artiga')
    
    products_success_count = 0
    
    # Retenter les produits en erreur
    for error_product in error_products:
        product_code = error_product['product_code']
        product_url = error_product['base_url']
        product_id = error_product['id']
        current_retry_count = error_product['retry_count'] or 0
        
        logger.info(f"\n  Retry produit {product_code} (retry_count actuel: {current_retry_count})")
        
        if not product_url:
            logger.warning(f"  ✗ Pas d'URL pour {product_code}, ignoré")
            continue
        
        # Boucle de retry (max 3 tentatives)
        max_retries = 3
        retry_success = False
        
        for retry_attempt in range(1, max_retries + 1):
            logger.info(f"    Tentative {retry_attempt}/{max_retries} pour {product_code}")
            
            # Vérifier que l'URL retourne 200
            url_returns_200 = False
            try:
                logger.info(f"    Vérification HTTP 200 avant retry {retry_attempt}...")
                response = session.get(product_url, timeout=10, allow_redirects=True)
                if response.status_code == 200:
                    url_returns_200 = True
                    logger.info(f"    ✓ URL retourne 200 - Retry {retry_attempt} autorisé")
                else:
                    logger.warning(f"    ✗ URL retourne {response.status_code} (pas 200)")
            except (Timeout, ConnectionError, RequestException) as url_error:
                logger.warning(f"    ✗ URL non accessible: {url_error}")
            
            # Si l'URL ne retourne pas 200, attendre jusqu'à 2 minutes
            if not url_returns_200:
                logger.info(f"    Attente que l'URL retourne 200 (max 2 minutes)...")
                start_wait = time.time()
                max_wait_for_retry = 120  # 2 minutes maximum
                url_became_accessible = False
                
                while time.time() - start_wait < max_wait_for_retry:
                    try:
                        response = session.get(product_url, timeout=10, allow_redirects=True)
                        if response.status_code == 200:
                            url_became_accessible = True
                            logger.info(f"    ✓ URL retourne maintenant 200 après attente - Retry {retry_attempt} autorisé")
                            break
                    except Exception:
                        pass
                    time.sleep(10)  # Vérifier toutes les 10 secondes
                
                if url_became_accessible:
                    url_returns_200 = True
                else:
                    logger.warning(f"    ✗ URL n'est pas devenue accessible après {max_wait_for_retry}s")
            
            # Retry uniquement si l'URL retourne 200
            if url_returns_200:
                try:
                    logger.info(f"    Retry {retry_attempt}: Réextraction depuis: {product_url}")
                    product_name = product_code
                    details, driver, session = scraper_module.get_product_details(
                        driver, session, product_url, product_name, headless=headless
                    )
                    
                    if not details:
                        raise Exception("Aucun détail trouvé après retry")
                    
                    # Extraire les informations depuis details
                    title = details.get('name') or details.get('full_name') or product_name
                    description = details.get('description', '')
                    images = details.get('images', [])
                    variants = details.get('variants', [])
                    
                    # Générer le handle
                    handle = scraper_module.slugify(title)
                    
                    # Mettre à jour le produit dans la DB
                    cursor.execute('''
                        UPDATE products 
                        SET handle = ?, title = ?, description = ?, 
                            status = 'pending', error_message = NULL,
                            retry_count = COALESCE(retry_count, 0) + 1,
                            updated_at = CURRENT_TIMESTAMP
                        WHERE id = ?
                    ''', (handle, title, description, product_id))
                    
                    # Supprimer les anciennes images et ajouter les nouvelles
                    if images:
                        cursor.execute('DELETE FROM product_images WHERE product_id = ?', (product_id,))
                        logger.info(f"    {len(images)} image(s) trouvée(s)")
                        for img_idx, image_url in enumerate(images, 1):
                            db.add_image(product_id, image_url, position=img_idx)
                    
                    # Ajouter/mettre à jour les variants
                    variants_added = 0
                    variants_with_errors = 0
                    
                    if variants:
                        logger.info(f"    {len(variants)} variant(s) trouvé(s)")
                        for variant_info in variants:
                            variant_code = variant_info.get('full_code') or variant_info.get('sku') or variant_info.get('code') or f"{product_code}-{variants_added+1}"
                            variant_url = variant_info.get('url') or product_url
                            size_text = variant_info.get('size') or variant_info.get('size_text') or ''
                            variant_sku = variant_info.get('sku') or variant_info.get('full_code') or ''
                            variant_gencode = variant_info.get('gencode') or ''
                            variant_price_pvc = variant_info.get('pvc') or variant_info.get('price_pvc') or ''
                            variant_price_pa = variant_info.get('pa') or variant_info.get('price_pa') or None
                            variant_size = variant_info.get('size') or ''
                            variant_color = variant_info.get('color') or ''
                            
                            variant_id, is_new = db.add_variant(
                                product_id=product_id,
                                code_vl=variant_code,
                                url=variant_url,
                                size_text=size_text,
                                raise_on_duplicate=False
                            )
                            
                            # Vérifier si toutes les données sont présentes
                            missing_fields = []
                            if not variant_sku or not variant_sku.strip():
                                missing_fields.append('SKU')
                            if not variant_gencode or not variant_gencode.strip():
                                missing_fields.append('gencode')
                            if not variant_price_pvc or not variant_price_pvc.strip():
                                missing_fields.append('prix')
                            
                            if missing_fields:
                                variant_status = 'error'
                                variant_error_msg = f"Champ(s) manquant(s): {', '.join(missing_fields)}"
                                variants_with_errors += 1
                            else:
                                variant_status = 'completed'
                                variant_error_msg = None
                            
                            # Mettre à jour les données du variant
                            db.update_variant_data(
                                variant_id=variant_id,
                                sku=variant_sku if variant_sku else None,
                                gencode=variant_gencode if variant_gencode else None,
                                price_pvc=variant_price_pvc if variant_price_pvc else None,
                                price_pa=variant_price_pa if variant_price_pa else None,
                                size=variant_size if variant_size else None,
                                color=variant_color if variant_color else None,
                                status=variant_status,
                                error_message=variant_error_msg
                            )
                            
                            variants_added += 1
                    else:
                        logger.warning(f"    ⚠ Aucun variant trouvé pour {product_code}")
                    
                    # Mettre à jour le status du produit selon les variants
                    db.update_product_status_if_all_variants_processed(product_id)
                    
                    db.conn.commit()
                    products_success_count += 1
                    retry_success = True
                    logger.info(f"    ✓ Produit {product_code} corrigé avec succès (retry {retry_attempt})")
                    logger.info(f"    {variants_added} variant(s) collecté(s) ({variants_with_errors} en erreur)")
                    break  # Sortir de la boucle de retry
                    
                except Exception as retry_error:
                    logger.warning(f"    ✗ Retry {retry_attempt} échoué: {retry_error}")
                    if retry_attempt < max_retries:
                        logger.info(f"    Nouvelle tentative dans 2 secondes...")
                        time.sleep(2)
                    else:
                        logger.error(f"    ✗ Tous les retries ont échoué ({max_retries} tentatives)")
            else:
                logger.warning(f"    ✗ Retry {retry_attempt} annulé (URL ne retourne pas 200)")
                if retry_attempt < max_retries:
                    logger.info(f"    Nouvelle tentative dans 2 secondes...")
                    time.sleep(2)
        
        # Si tous les retries ont échoué, incrémenter retry_count
        if not retry_success:
            cursor.execute('''
                UPDATE products 
                SET retry_count = COALESCE(retry_count, 0) + 1,
                    updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
            ''', (product_id,))
            db.conn.commit()
            logger.warning(f"  ✗ Produit {product_code} reste en erreur (retry_count incrémenté)")
    
    # Retenter les variants en erreur
    variants_success_count = 0
    
    for error_variant in error_variants:
        variant_id = error_variant['id']
        variant_code = error_variant['code_vl']
        product_url = error_variant['base_url']
        product_id = error_variant['product_id']
        product_code = error_variant['product_code']
        current_retry_count = error_variant['retry_count'] or 0
        
        logger.info(f"\n  Retry variant {variant_code} (retry_count actuel: {current_retry_count})")
        
        if not product_url:
            logger.warning(f"  ✗ Pas d'URL produit pour {variant_code}, ignoré")
            continue
        
        # Boucle de retry (max 3 tentatives)
        max_retries = 3
        retry_success = False
        
        for retry_attempt in range(1, max_retries + 1):
            logger.info(f"    Tentative {retry_attempt}/{max_retries} pour {variant_code}")
            
            # Vérifier que l'URL retourne 200
            url_returns_200 = False
            try:
                logger.info(f"    Vérification HTTP 200 avant retry {retry_attempt}...")
                response = session.get(product_url, timeout=10, allow_redirects=True)
                if response.status_code == 200:
                    url_returns_200 = True
                    logger.info(f"    ✓ URL retourne 200 - Retry {retry_attempt} autorisé")
                else:
                    logger.warning(f"    ✗ URL retourne {response.status_code} (pas 200)")
            except (Timeout, ConnectionError, RequestException) as url_error:
                logger.warning(f"    ✗ URL non accessible: {url_error}")
            
            # Si l'URL ne retourne pas 200, attendre jusqu'à 2 minutes
            if not url_returns_200:
                logger.info(f"    Attente que l'URL retourne 200 (max 2 minutes)...")
                start_wait = time.time()
                max_wait_for_retry = 120  # 2 minutes maximum
                url_became_accessible = False
                
                while time.time() - start_wait < max_wait_for_retry:
                    try:
                        response = session.get(product_url, timeout=10, allow_redirects=True)
                        if response.status_code == 200:
                            url_became_accessible = True
                            logger.info(f"    ✓ URL retourne maintenant 200 après attente - Retry {retry_attempt} autorisé")
                            break
                    except Exception:
                        pass
                    time.sleep(10)  # Vérifier toutes les 10 secondes
                
                if url_became_accessible:
                    url_returns_200 = True
                else:
                    logger.warning(f"    ✗ URL n'est pas devenue accessible après {max_wait_for_retry}s")
            
            # Retry uniquement si l'URL retourne 200
            if url_returns_200:
                try:
                    # Incrémenter retry_count
                    cursor.execute('''
                        UPDATE product_variants 
                        SET retry_count = COALESCE(retry_count, 0) + 1,
                            updated_at = CURRENT_TIMESTAMP
                        WHERE id = ?
                    ''', (variant_id,))
                    db.conn.commit()
                    
                    # Réextraire les données du produit pour obtenir les variants mis à jour
                    logger.info(f"    Retry {retry_attempt}: Réextraction depuis: {product_url}")
                    details, driver, session = scraper_module.get_product_details(
                        driver, session, product_url, product_code, headless=headless
                    )
                    
                    if not details or not details.get('variants'):
                        raise Exception("Impossible de réextraire les détails ou variants manquants")
                    
                    # Chercher le variant correspondant dans les détails
                    variant_found = False
                    for variant_info in details.get('variants', []):
                        variant_info_code = variant_info.get('full_code') or variant_info.get('sku') or variant_info.get('code') or ''
                        if variant_info_code == variant_code or variant_info.get('code_vl') == variant_code:
                            variant_found = True
                            
                            # Extraire les données du variant
                            variant_sku = variant_info.get('sku') or variant_info.get('full_code') or ''
                            variant_gencode = variant_info.get('gencode') or ''
                            variant_price_pvc = variant_info.get('pvc') or variant_info.get('price_pvc') or ''
                            variant_price_pa = variant_info.get('pa') or variant_info.get('price_pa') or None
                            variant_size = variant_info.get('size') or ''
                            variant_color = variant_info.get('color') or ''
                            
                            # Vérifier si toutes les données sont présentes
                            missing_fields = []
                            if not variant_sku or not variant_sku.strip():
                                missing_fields.append('SKU')
                            if not variant_gencode or not variant_gencode.strip():
                                missing_fields.append('gencode')
                            if not variant_price_pvc or not variant_price_pvc.strip():
                                missing_fields.append('prix')
                            
                            if missing_fields:
                                error_msg = f"Champ(s) manquant(s): {', '.join(missing_fields)}"
                                db.update_variant_data(
                                    variant_id=variant_id,
                                    sku=variant_sku if variant_sku else None,
                                    gencode=variant_gencode if variant_gencode else None,
                                    price_pvc=variant_price_pvc if variant_price_pvc else None,
                                    price_pa=variant_price_pa if variant_price_pa else None,
                                    size=variant_size if variant_size else None,
                                    color=variant_color if variant_color else None,
                                    status='error',
                                    error_message=error_msg
                                )
                                logger.warning(f"    ✗ Variant {variant_code} toujours en erreur: {error_msg}")
                            else:
                                # Toutes les données sont présentes, marquer comme completed
                                db.update_variant_data(
                                    variant_id=variant_id,
                                    sku=variant_sku,
                                    gencode=variant_gencode,
                                    price_pvc=variant_price_pvc,
                                    price_pa=variant_price_pa,
                                    size=variant_size if variant_size else None,
                                    color=variant_color if variant_color else None,
                                    status='completed',
                                    error_message=None
                                )
                                
                                # Mettre à jour le status du produit parent si tous les variants sont traités
                                db.update_product_status_if_all_variants_processed(product_id)
                                
                                variants_success_count += 1
                                retry_success = True
                                logger.info(f"    ✓ Variant {variant_code} corrigé avec succès (retry {retry_attempt})")
                                logger.info(f"      SKU: {variant_sku}, Gencode: {variant_gencode}, Prix: {variant_price_pvc}")
                            
                            break
                    
                    if not variant_found:
                        logger.warning(f"    ✗ Variant {variant_code} non trouvé dans les détails du produit après retry")
                        if retry_attempt < max_retries:
                            logger.info(f"    Nouvelle tentative dans 2 secondes...")
                            time.sleep(2)
                        else:
                            logger.error(f"    ✗ Tous les retries ont échoué ({max_retries} tentatives)")
                    elif retry_success:
                        break  # Sortir de la boucle de retry si succès
                    
                except Exception as retry_error:
                    logger.warning(f"    ✗ Retry {retry_attempt} échoué: {retry_error}")
                    if retry_attempt < max_retries:
                        logger.info(f"    Nouvelle tentative dans 2 secondes...")
                        time.sleep(2)
                    else:
                        logger.error(f"    ✗ Tous les retries ont échoué ({max_retries} tentatives)")
            else:
                logger.warning(f"    ✗ Retry {retry_attempt} annulé (URL ne retourne pas 200)")
                if retry_attempt < max_retries:
                    logger.info(f"    Nouvelle tentative dans 2 secondes...")
                    time.sleep(2)
        
        # Si tous les retries ont échoué, incrémenter retry_count
        if not retry_success:
            cursor.execute('''
                UPDATE product_variants 
                SET retry_count = COALESCE(retry_count, 0) + 1,
                    updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
            ''', (variant_id,))
            db.conn.commit()
            logger.warning(f"  ✗ Variant {variant_code} reste en erreur (retry_count incrémenté)")
    
    logger.info(f"\n{'='*60}")
    logger.info(f"✓ Retry automatique terminé :")
    logger.info(f"  Produits corrigés : {products_success_count}/{len(error_products)}")
    logger.info(f"  Variants corrigés : {variants_success_count}/{len(error_variants)}")
    logger.info(f"{'='*60}\n")
    
    return (products_success_count, variants_success_count)


def collect_urls(categories=None, subcategories=None, output_db='artiga_products.db', headless=True):
    """
    Collecte les produits de plusieurs catégories/sous-catégories.
    
    Args:
        categories: Liste de catégories à traiter (None = toutes)
        subcategories: Liste de sous-catégories à traiter (None = toutes)
        output_db: Chemin vers la base de données
        headless: Mode headless pour Selenium
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
        description='Collecte les produits Artiga et les stocke dans la base de données'
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
        help='Chemin vers la base de données SQLite (défaut: artiga_products.db)'
    )
    parser.add_argument(
        '--no-headless',
        action='store_true',
        help='Désactiver le mode headless (afficher le navigateur)'
    )
    parser.add_argument(
        '--retry-errors-only',
        action='store_true',
        help='Retenter UNIQUEMENT les produits en erreur (ne pas collecter de nouveaux produits)'
    )
    
    args = parser.parse_args()
    
    # Utiliser la DB par défaut si non spécifiée
    if args.db is None:
        output_db = get_artiga_db_path()
        logger.info(f"Utilisation de la base de données: {output_db}")
    else:
        output_db = args.db
    
    # Si --retry-errors-only est activé, ne traiter QUE les produits en erreur
    if args.retry_errors_only:
        logger.info("Mode retry-errors-only activé : traitement UNIQUEMENT des produits en erreur")
        
        # Initialiser la connexion DB
        db = ArtigaDB(output_db)
        
        # Créer driver/session
        driver = scraper_module.get_selenium_driver(headless=not args.no_headless)
        if not driver:
            logger.error("Impossible de créer le driver Selenium")
            sys.exit(1)
        
        import requests
        session = requests.Session()
        session.headers.update(scraper_module.HEADERS)
        logger.info("Driver Selenium créé")
        
        try:
            # Déterminer la catégorie et sous-catégorie à filtrer
            category = None
            subcategory = None
            
            # Pour Artiga, --category correspond à une sous-catégorie
            # On doit trouver la catégorie parente depuis la DB
            if args.category and len(args.category) > 0:
                subcategory = args.category[0]
                logger.info(f"Filtrage par sous-catégorie: {subcategory}")
                
                # Récupérer la catégorie parente depuis la DB
                cursor = db.conn.cursor()
                cursor.execute('''
                    SELECT DISTINCT category 
                    FROM products 
                    WHERE subcategory = ?
                    LIMIT 1
                ''', (subcategory,))
                row = cursor.fetchone()
                if row:
                    category = row['category']
                    logger.info(f"Catégorie parente trouvée: {category}")
                else:
                    logger.info(f"Aucune catégorie trouvée pour la sous-catégorie '{subcategory}', filtrage par sous-catégorie uniquement")
            
            # Si une sous-catégorie est spécifiée explicitement, l'utiliser (priorité)
            if args.subcategory and len(args.subcategory) > 0:
                subcategory = args.subcategory[0]
                logger.info(f"Filtrage par sous-catégorie (explicite): {subcategory}")
                
                # Récupérer la catégorie parente depuis la DB si pas déjà trouvée
                if not category:
                    cursor = db.conn.cursor()
                    cursor.execute('''
                        SELECT DISTINCT category 
                        FROM products 
                        WHERE subcategory = ?
                        LIMIT 1
                    ''', (subcategory,))
                    row = cursor.fetchone()
                    if row:
                        category = row['category']
                        logger.info(f"Catégorie parente trouvée: {category}")
            
            # Appeler retry_error_products_and_variants directement
            retry_error_products_and_variants(
                db=db,
                driver=driver,
                session=session,
                category=category,
                subcategory=subcategory,
                headless=not args.no_headless
            )
            
            logger.info("✅ Retraitement des produits en erreur terminé")
            
        except Exception as e:
            logger.error(f"Erreur lors du retraitement: {e}", exc_info=True)
            sys.exit(1)
        finally:
            if driver:
                try:
                    driver.quit()
                except:
                    pass
            db.close()
        
        sys.exit(0)
    
    collect_urls(
        categories=args.category,
        subcategories=args.subcategory,
        output_db=output_db,
        headless=not args.no_headless
    )
    
    logger.info("Script terminé avec succès")
