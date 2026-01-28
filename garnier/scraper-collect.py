#!/usr/bin/env python3
"""
Script pour collecter toutes les URLs avec code_vl depuis le site Garnier-Thiebaut
et les stocker dans une base de données SQLite.
"""

import sys
import os
import argparse
import logging
import sqlite3
from dotenv import load_dotenv

# Ajouter le répertoire parent au path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.garnier_db import GarnierDB
from utils.app_config import get_garnier_db_path
from csv_config import get_csv_config
from garnier.scraper_garnier_module import (
    authenticate, get_categories, get_gammes_from_category,
    get_products_from_gamme, extract_variants_from_product_page,
    extract_product_name_and_description, extract_product_images,
    extract_product_is_new, slugify
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
USERNAME = os.getenv("USERNAME", "")
PASSWORD = os.getenv("PASSWORD", "")


def collect_from_gamme_url(gamme_url, output_db='garnier_products.db', headless=True, category=None, driver=None, session=None, retry_errors_after=False):
    """
    Collecte les produits d'une gamme spécifique depuis son URL et les stocke dans la base de données.
    
    Args:
        gamme_url: URL de la gamme à traiter
        output_db: Chemin vers la base de données SQLite
        headless: Mode headless pour Selenium (ignoré si driver/session fournis)
        category: Nom de la catégorie (obligatoire)
        driver: WebDriver Selenium existant (optionnel, créé si None)
        session: Session requests existante (optionnel, créée si None)
    
    Returns:
        Tuple (nombre_de_variants_collectés, driver, session) où driver et session peuvent être réutilisés
    """
    from urllib.parse import urlparse, unquote
    
    db = GarnierDB(output_db)
    driver_created = False
    driver_to_close = None  # Driver à fermer dans le finally
    
    try:
        # Authentification si driver/session non fournis
        if driver is None or session is None:
            driver, session = authenticate(headless=headless)
            if not driver:
                logger.error("Impossible de s'authentifier")
                return (0, None, None)
            driver_created = True
            driver_to_close = driver  # Marquer pour fermeture dans finally
            logger.info("Authentification réussie")
        else:
            logger.info("Réutilisation du driver et de la session existants")
            # Ne pas fermer le driver fourni en paramètre
        
        # Vérifier que la catégorie est fournie
        if not category:
            raise ValueError("Le paramètre 'category' est obligatoire")
        
        # Récupérer le vendor depuis csv_config
        csv_config_manager = get_csv_config()
        vendor_name = csv_config_manager.get_vendor('garnier')
        
        # Extraire le nom de la gamme depuis l'URL
        parsed = urlparse(gamme_url)
        gamme_name = None
        if 'code_gamme' in parsed.query:
            gamme_name = unquote(parsed.query.split('code_gamme=')[1].split('&')[0])
            # Nettoyer le nom et mettre en majuscule
            gamme_name = gamme_name.replace('_', ' ').replace('-', ' ').upper()
        
        # Ajouter ou mettre à jour la gamme dans la DB
        gamme_id = db.add_gamme(url=gamme_url, category=category, name=gamme_name)
        
        # Marquer la gamme comme en cours de traitement
        if gamme_name:  # Seulement si la gamme a un nom (pas en erreur)
            db.update_gamme_status(gamme_id, 'processing')
        
        logger.info(f"\n{'='*60}")
        logger.info(f"Traitement de la gamme: {gamme_name or 'SANS NOM'} (ID: {gamme_id})")
        logger.info(f"Catégorie: {category}")
        logger.info(f"URL: {gamme_url}")
        logger.info(f"Status: {'processing' if gamme_name else 'error'}")
        logger.info(f"{'='*60}")
        
        # Récupérer les produits en erreur pour les retenter (max 3 tentatives)
        cursor = db.conn.cursor()
        cursor.execute('''
            SELECT product_code, base_url 
            FROM products 
            WHERE status = 'error' 
            AND category = ?
            AND (gamme = ? OR gamme LIKE ?)
            AND (retry_count IS NULL OR retry_count < 3)
        ''', (category, gamme_name, f'{gamme_name}%'))
        error_products = cursor.fetchall()
        
        # #region agent log
        import json
        import time
        try:
            with open('/Users/jean-loup/shopify/garnier/.cursor/debug.log', 'a') as f:
                f.write(json.dumps({
                    "sessionId": "debug-session",
                    "runId": "run1",
                    "hypothesisId": "B",
                    "location": "scraper-garnier-collect.py:collect_from_gamme_url:ERROR_PRODUCTS",
                    "message": "Checking error products for retry",
                    "data": {"error_products_count": len(error_products), "category": category, "gamme_name": gamme_name},
                    "timestamp": int(time.time() * 1000)
                }) + "\n")
        except:
            pass
        # #endregion
        
        if error_products:
            logger.info(f"\n🔄 Retraitement de {len(error_products)} produit(s) en erreur...")
            from garnier.scraper_garnier_module import wait_for_url_accessible
            from requests.exceptions import RequestException, Timeout, ConnectionError
            
            for error_product in error_products:
                # #region agent log
                try:
                    with open('/Users/jean-loup/shopify/garnier/.cursor/debug.log', 'a') as f:
                        f.write(json.dumps({
                            "sessionId": "debug-session",
                            "runId": "run1",
                            "hypothesisId": "B",
                            "location": "scraper-garnier-collect.py:collect_from_gamme_url:PROCESSING_ERROR",
                            "message": "Processing error product",
                            "data": {"product_code": error_product['product_code'], "product_url": error_product['base_url']},
                            "timestamp": int(time.time() * 1000)
                        }) + "\n")
                except:
                    pass
                # #endregion
                product_code = error_product['product_code']
                product_url = error_product['base_url']
                
                if not product_url:
                    logger.warning(f"  ✗ Produit {product_code}: Pas d'URL trouvée, retry ignoré")
                    continue
                
                # Vérifier que l'URL retourne 200 avant de retenter (car c'est un retry après erreur)
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
                
                # Si l'URL ne retourne pas 200, utiliser wait_for_url_accessible avec timeout réduit
                # Ne pas attendre trop longtemps pour éviter de bloquer le script
                if not url_returns_200:
                    logger.info(f"  Attente que l'URL retourne 200 avec wait_for_url_accessible pour {product_code} (max 2 minutes)...")
                    # Utiliser un timeout plus court pour les produits en erreur (2 minutes au lieu de 5)
                    # Créer une fonction wrapper avec timeout personnalisé
                    import time as time_module
                    start_wait = time_module.time()
                    max_wait_for_error = 120  # 2 minutes maximum pour les produits en erreur
                    url_became_accessible = False
                    
                    while time_module.time() - start_wait < max_wait_for_error:
                        try:
                            response = session.get(product_url, timeout=10, allow_redirects=True)
                            if response.status_code == 200:
                                url_became_accessible = True
                                logger.info(f"  ✓ Produit {product_code}: URL retourne maintenant 200 après attente")
                                break
                        except Exception:
                            pass
                        time_module.sleep(10)  # Vérifier toutes les 10 secondes
                    
                    if url_became_accessible:
                        url_returns_200 = True
                    else:
                        logger.warning(f"  ✗ Produit {product_code}: URL toujours inaccessible après {max_wait_for_error}s, ignoré")
                
                # Si l'URL retourne 200, marquer pour retry
                if url_returns_200:
                    # Incrémenter retry_count mais garder status='error'
                    # Le status sera changé seulement si la collecte réussit vraiment
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
        
        # Obtenir les produits de cette gamme
        products = get_products_from_gamme(driver, session, gamme_url, headless=headless)
        logger.info(f"Produits trouvés: {len(products)}")
        
        if not products:
            logger.warning("Aucun produit trouvé dans cette gamme")
            return 0
        
        total_variants_collected = 0
        
        # Traiter chaque produit
        for idx, product_info in enumerate(products, 1):
            product_code = product_info.get('code')
            product_url = product_info.get('url')
            product_name = product_info.get('name', f"Produit {product_code}")
            
            if not product_code or not product_url:
                continue
            
            logger.info(f"\n  [{idx}/{len(products)}] {product_name}")
            logger.info(f"    Extraction du titre depuis: {product_url}")
            
            try:
                # Extraire le nom et la description depuis la page produit (h3 dans product-body)
                product_name_from_page, description = extract_product_name_and_description(
                    driver, session, product_url,
                    fallback_name=product_name,
                    headless=headless
                )
                
                # Le titre est maintenant obligatoire (pas de fallback)
                final_product_name = product_name_from_page
                logger.info(f"    ✓ Titre final: {final_product_name}")
                
                # Extraire tous les variants de ce produit
                variants = extract_variants_from_product_page(
                    driver, session, product_url, product_code, headless=headless
                )
                
                if not variants:
                    logger.warning(f"    Aucun variant trouvé pour {product_code}")
                    continue
                
                logger.info(f"    {len(variants)} variant(s) extrait(s) pour {product_code}")
                
                # Extraire le statut "new" du produit
                logger.info(f"    Vérification du label 'new' depuis: {product_url}")
                is_new_product = extract_product_is_new(driver, session, product_url, headless=headless)
                if is_new_product:
                    logger.info(f"    ✓ Produit marqué comme 'new' (Published sera FALSE)")
                
                # Générer le handle Shopify
                handle = slugify(final_product_name)
                
                # Ajouter le produit dans la DB avec le nom et la description
                base_url_without_params = product_url.split('?')[0]
                product_id = db.add_product(
                    product_code=product_code,
                    handle=handle,
                    title=final_product_name,
                    description=description,
                    vendor=vendor_name,
                    product_type=category,
                    tags=category,
                    category=category,
                    gamme=gamme_name,  # Garder pour compatibilité
                    base_url=base_url_without_params,
                    is_new=is_new_product
                )
                
                # Lier le produit à la gamme dans la table gamme_products
                db.link_gamme_to_product(gamme_id, product_id)
                
                # Extraire et ajouter les images du produit depuis la page produit
                # Utiliser l'URL du premier variant pour extraire les images
                if variants:
                    first_variant_code = variants[0]['code']
                    variant_url_for_images = f"{base_url_without_params}?code_vl={first_variant_code}"
                    logger.info(f"    Extraction des images depuis: {variant_url_for_images}")
                    product_images = extract_product_images(driver, session, variant_url_for_images, headless=headless)
                    if product_images:
                        logger.info(f"    {len(product_images)} image(s) trouvée(s)")
                        for img_idx, image_url in enumerate(product_images, 1):
                            db.add_image(product_id, image_url, position=img_idx)
                    else:
                        logger.warning(f"    Aucune image trouvée pour {product_code}")
                
                # Ajouter tous les variants
                variants_added = 0
                for variant_info in variants:
                    variant_code = variant_info['code']
                    variant_url = f"{base_url_without_params}?code_vl={variant_code}"
                    size_text = variant_info.get('size_text', '')
                    
                    try:
                        logger.debug(f"      Ajout du variant {variant_code} pour produit {product_code} (product_id: {product_id})")
                        variant_id, is_new = db.add_variant(
                            product_id=product_id,
                            code_vl=variant_code,
                            url=variant_url,
                            size_text=size_text,
                            raise_on_duplicate=False  # Ne pas lever d'exception si existe déjà
                        )
                        
                        if is_new:
                            variants_added += 1
                            logger.info(f"      ✓ Variant {variant_code} ajouté (ID: {variant_id})")
                        else:
                            # Le variant existe déjà, mettre à jour les champs de base
                            db.update_variant_collect(
                                variant_id=variant_id,
                                url=variant_url,
                                size_text=size_text
                            )
                            variants_added += 1
                            logger.info(f"      ✓ Variant {variant_code} mis à jour (déjà présent, ID: {variant_id})")
                    except Exception as variant_error:
                        logger.error(f"      ✗ Erreur lors de l'ajout du variant {variant_code}: {variant_error}")
                        import traceback
                        logger.error(traceback.format_exc())
                        # Ne pas compter ce variant mais continuer
                
                total_variants_collected += variants_added
                logger.info(f"    {product_code}: {variants_added} variant(s) collecté(s) ou mis à jour")
                
            except Exception as e:
                error_msg = str(e)
                logger.warning(f"    Erreur lors de l'extraction du titre pour {product_code}: {error_msg}")
                
                from garnier.scraper_garnier_module import wait_for_url_accessible
                from requests.exceptions import RequestException, Timeout, ConnectionError
                import time
                
                # Retry jusqu'à 3 fois avec vérification HTTP 200 avant chaque tentative
                max_retries = 3
                retry_success = False
                
                for retry_attempt in range(1, max_retries + 1):
                    logger.info(f"    Tentative de retry {retry_attempt}/{max_retries} pour {product_code}...")
                    
                    # Ré-authentifier au 2ème essai pour rafraîchir la session
                    if retry_attempt == 2:
                        logger.info(f"    🔐 Ré-authentification avant retry {retry_attempt}...")
                        try:
                            driver, session = authenticate(headless=headless)
                            logger.info(f"    ✓ Ré-authentification réussie")
                        except Exception as auth_error:
                            logger.error(f"    ✗ Erreur lors de la ré-authentification: {auth_error}")
                    
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
                    
                    # Si l'URL ne retourne pas 200, utiliser wait_for_url_accessible avec timeout réduit
                    # Ne pas attendre trop longtemps pour éviter de bloquer le script
                    if not url_returns_200:
                        logger.info(f"    Attente que l'URL retourne 200 avec wait_for_url_accessible (max 2 minutes)...")
                        # Utiliser un timeout plus court pour les retries (2 minutes au lieu de 5)
                        import time as time_module
                        start_wait = time_module.time()
                        max_wait_for_retry = 120  # 2 minutes maximum pour les retries
                        url_became_accessible = False
                        
                        while time_module.time() - start_wait < max_wait_for_retry:
                            try:
                                response = session.get(product_url, timeout=10, allow_redirects=True)
                                if response.status_code == 200:
                                    url_became_accessible = True
                                    logger.info(f"    ✓ URL retourne maintenant 200 après attente - Retry {retry_attempt} autorisé")
                                    break
                            except Exception:
                                pass
                            time_module.sleep(10)  # Vérifier toutes les 10 secondes
                        
                        if url_became_accessible:
                            url_returns_200 = True
                        else:
                            logger.warning(f"    ✗ URL n'est pas devenue accessible après {max_wait_for_retry}s, abandon du retry")
                    
                    # Retry uniquement si l'URL retourne 200
                    if url_returns_200:
                        try:
                            logger.info(f"    Retry {retry_attempt}: Extraction du titre depuis: {product_url}")
                            product_name_from_page, description = extract_product_name_and_description(
                                driver, session, product_url,
                                fallback_name=product_name,
                                headless=headless
                            )
                            
                            final_product_name = product_name_from_page
                            logger.info(f"    ✓ Titre final (après retry {retry_attempt}): {final_product_name}")
                            
                            # Si le retry réussit, continuer avec l'extraction des variants
                            variants = extract_variants_from_product_page(
                                driver, session, product_url, product_code, headless=headless
                            )
                            
                            if not variants:
                                logger.warning(f"    Aucun variant trouvé pour {product_code} (après retry {retry_attempt})")
                                continue
                            
                            # Extraire le statut "new" du produit
                            logger.info(f"    Vérification du label 'new' depuis: {product_url}")
                            is_new_product = extract_product_is_new(driver, session, product_url, headless=headless)
                            if is_new_product:
                                logger.info(f"    ✓ Produit marqué comme 'new' (Published sera FALSE)")
                            
                            # Générer le handle et ajouter le produit
                            handle = slugify(final_product_name)
                            base_url_without_params = product_url.split('?')[0]
                            product_id = db.add_product(
                                product_code=product_code,
                                handle=handle,
                                title=final_product_name,
                                description=description,
                                vendor=vendor_name,
                                product_type=category,
                                tags=category,
                                category=category,
                                gamme=gamme_name,
                                base_url=base_url_without_params,
                                is_new=is_new_product
                            )
                            
                            # Extraire et ajouter les images du produit depuis la page produit
                            if variants:
                                first_variant_code = variants[0]['code']
                                variant_url_for_images = f"{base_url_without_params}?code_vl={first_variant_code}"
                                logger.info(f"    Extraction des images depuis: {variant_url_for_images}")
                                product_images = extract_product_images(driver, session, variant_url_for_images, headless=headless)
                                if product_images:
                                    logger.info(f"    {len(product_images)} image(s) trouvée(s)")
                                    for img_idx, image_url in enumerate(product_images, 1):
                                        db.add_image(product_id, image_url, position=img_idx)
                                else:
                                    logger.warning(f"    Aucune image trouvée pour {product_code}")
                            
                            # Ajouter les variants
                            variants_added = 0
                            for variant_info in variants:
                                variant_code = variant_info['code']
                                variant_url = f"{base_url_without_params}?code_vl={variant_code}"
                                size_text = variant_info.get('size_text', '')
                                
                                variant_id, is_new = db.add_variant(
                                    product_id=product_id,
                                    code_vl=variant_code,
                                    url=variant_url,
                                    size_text=size_text,
                                    raise_on_duplicate=False
                                )
                                
                                if is_new:
                                    variants_added += 1
                                else:
                                    db.update_variant_collect(
                                        variant_id=variant_id,
                                        url=variant_url,
                                        size_text=size_text
                                    )
                                    variants_added += 1
                            
                            total_variants_collected += variants_added
                            logger.info(f"    {product_code}: {variants_added} variant(s) collecté(s) ou mis à jour (après retry {retry_attempt})")
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
                    error_msg_final = f"Erreur persistante après {max_retries} tentatives pour {product_code}: {error_msg}"
                    logger.error(f"    {error_msg_final}")
                    # Marquer le produit en erreur et continuer
                    try:
                        cursor = db.conn.cursor()
                        cursor.execute('SELECT id FROM products WHERE product_code = ?', (product_code,))
                        row = cursor.fetchone()
                        if row:
                            product_id = row['id']
                            # Mettre à jour le produit en erreur avec retry_count
                            cursor.execute('''
                                UPDATE products 
                                SET status = 'error', 
                                    error_message = ?,
                                    retry_count = COALESCE(retry_count, 0) + 1,
                                    updated_at = CURRENT_TIMESTAMP
                                WHERE id = ?
                            ''', (error_msg_final[:500], product_id))
                        else:
                            # Créer le produit en erreur (sans titre)
                            handle = slugify(product_code) if product_code else f"produit-{product_code}"
                            base_url_without_params = product_url.split('?')[0] if product_url else None
                            product_id = db.add_product(
                                product_code=product_code,
                                handle=handle,
                                title=None,
                                vendor=vendor_name,
                                product_type=category,
                                tags=category,
                                category=category,
                                gamme=gamme_name,
                                base_url=base_url_without_params,
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
                        logger.warning(f"    Produit {product_code} marqué en erreur dans la DB (retry_count incrémenté)")
                    except Exception as db_error:
                        logger.warning(f"    Impossible de marquer le produit en erreur dans la DB: {db_error}")
                    continue
        
        # Afficher les statistiques
        stats = db.get_stats()
        logger.info(f"\n{'='*60}")
        logger.info("Collecte terminée!")
        logger.info(f"Total produits: {stats['total_products']}")
        logger.info(f"Total variants: {stats['total_variants']}")
        logger.info(f"Variants par statut: {stats['variants_by_status']}")
        logger.info(f"{'='*60}")
        
        # Vérifier et mettre à jour le statut de la gamme
        logger.info(f"\nVérification du statut de la gamme {gamme_id}...")
        db.update_gamme_status_if_all_products_processed(gamme_id)
        
        # Retry automatique si demandé
        if retry_errors_after:
            retry_error_products(db, driver, session, category=category, gamme=gamme_name, headless=headless)
            # Revérifier le statut après le retry
            logger.info(f"\nVérification finale du statut de la gamme {gamme_id} après retry...")
            db.update_gamme_status_if_all_products_processed(gamme_id)
        
        # Fermer la DB avant de retourner
        db.close()
        
        # #region agent log
        import json
        import time
        try:
            with open('/Users/jean-loup/shopify/garnier/.cursor/debug.log', 'a') as f:
                f.write(json.dumps({
                    "sessionId": "debug-session",
                    "runId": "run1",
                    "hypothesisId": "E",
                    "location": "scraper-garnier-collect.py:collect_from_gamme_url:RETURN",
                    "message": "collect_from_gamme_url returning",
                    "data": {"total_variants_collected": total_variants_collected},
                    "timestamp": int(time.time() * 1000)
                }) + "\n")
        except:
            pass
        # #endregion
        
        # Ne pas fermer le driver ici si on le retourne pour réutilisation
        # Le driver sera fermé par l'appelant si nécessaire
        driver_to_close = None  # Ne pas fermer le driver retourné
        return (total_variants_collected, driver, session)
        
    except Exception as e:
        # En cas d'erreur, fermer le driver si on l'a créé
        db.close()
        if driver_to_close:
            try:
                driver_to_close.quit()
            except:
                pass
        raise
    finally:
        db.close()
        # Ne fermer le driver que si on l'a créé ET qu'on ne le retourne pas
        # (cas d'erreur uniquement, car sinon on retourne avant le finally)
        if driver_to_close:
            try:
                driver_to_close.quit()
            except:
                pass


def collect_urls(categories=None, output_db='garnier_products.db', headless=True, retry_errors_after=False, gamme_status_filter=None):
    """
    Collecte toutes les URLs avec code_vl et les stocke dans la base de données.
    
    Args:
        categories: Liste de catégories à traiter (None = toutes)
        output_db: Chemin vers la base de données SQLite
        headless: Mode headless pour Selenium
        retry_errors_after: Retenter automatiquement les produits en erreur après collecte
        gamme_status_filter: Filtrer les gammes par statut ('pending', 'processing', 'error', 'completed')
    """
    db = GarnierDB(output_db)
    
    try:
        # Authentification
        driver, session = authenticate(headless=headless)
        if not driver:
            logger.error("Impossible de s'authentifier")
            return
        
        logger.info("Authentification réussie")
        
        # Récupérer le vendor depuis csv_config
        csv_config_manager = get_csv_config()
        vendor_name = csv_config_manager.get_vendor('garnier')
        
        # Obtenir les catégories
        all_categories = get_categories(driver, session)
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
        
        # Récupérer les produits en erreur pour les retenter (max 3 tentatives)
        cursor = db.conn.cursor()
        category_names = [cat['name'] for cat in category_list] if category_list else None
        if category_names:
            placeholders = ','.join(['?'] * len(category_names))
            cursor.execute(f'''
                SELECT product_code, base_url, category 
                FROM products 
                WHERE status = 'error' 
                AND category IN ({placeholders})
                AND (retry_count IS NULL OR retry_count < 3)
            ''', category_names)
        else:
            cursor.execute('''
                SELECT product_code, base_url, category 
                FROM products 
                WHERE status = 'error' 
                AND (retry_count IS NULL OR retry_count < 3)
            ''')
        error_products = cursor.fetchall()
        
        if error_products:
            logger.info(f"\n🔄 Retraitement de {len(error_products)} produit(s) en erreur...")
            from garnier.scraper_garnier_module import wait_for_url_accessible
            from requests.exceptions import RequestException, Timeout, ConnectionError
            
            for error_product in error_products:
                product_code = error_product['product_code']
                product_url = error_product['base_url']
                product_category = error_product['category']
                
                if not product_url:
                    logger.warning(f"  ✗ Produit {product_code}: Pas d'URL trouvée, retry ignoré")
                    continue
                
                # Vérifier que l'URL retourne 200 avant de retenter (car c'est un retry après erreur)
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
                
                # Si l'URL ne retourne pas 200, utiliser wait_for_url_accessible avec timeout réduit
                # Ne pas attendre trop longtemps pour éviter de bloquer le script
                if not url_returns_200:
                    logger.info(f"  Attente que l'URL retourne 200 avec wait_for_url_accessible pour {product_code} (max 2 minutes)...")
                    # Utiliser un timeout plus court pour les produits en erreur (2 minutes au lieu de 5)
                    import time as time_module
                    start_wait = time_module.time()
                    max_wait_for_error = 120  # 2 minutes maximum pour les produits en erreur
                    url_became_accessible = False
                    
                    while time_module.time() - start_wait < max_wait_for_error:
                        try:
                            response = session.get(product_url, timeout=10, allow_redirects=True)
                            if response.status_code == 200:
                                url_became_accessible = True
                                logger.info(f"  ✓ Produit {product_code}: URL retourne maintenant 200 après attente")
                                break
                        except Exception:
                            pass
                        time_module.sleep(10)  # Vérifier toutes les 10 secondes
                    
                    if url_became_accessible:
                        url_returns_200 = True
                    else:
                        logger.warning(f"  ✗ Produit {product_code}: URL toujours inaccessible après {max_wait_for_error}s, ignoré")
                
                # Si l'URL retourne 200, marquer pour retry
                if url_returns_200:
                    # Incrémenter retry_count mais garder status='error'
                    # Le status sera changé seulement si la collecte réussit vraiment
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
        
        total_variants_collected = 0
        
        # Parcourir chaque catégorie
        for category_info in category_list:
            category_name = category_info['name']
            category_url = category_info['url']
            
            logger.info(f"\n{'='*60}")
            logger.info(f"Traitement de la catégorie: {category_name}")
            logger.info(f"{'='*60}")
            
            # Obtenir les gammes de cette catégorie
            if gamme_status_filter:
                # Filtrer par statut dans la DB (ne pas parser le site)
                logger.info(f"Filtrage des gammes par statut: {gamme_status_filter}")
                gammes = db.get_gammes_by_status(status=gamme_status_filter, category=category_name)
                gamme_ids = [g['id'] for g in gammes]
                logger.info(f"Gammes {gamme_status_filter} trouvées en DB: {len(gamme_ids)}")
            else:
                # Parser le site et écrire dans la DB
                gamme_ids = get_gammes_from_category(
                    driver, 
                    session, 
                    category_url,
                    db=db,
                    category=category_name
                )
                logger.info(f"Gammes trouvées et écrites en DB: {len(gamme_ids)}")
            
            # Parcourir chaque gamme (par ID maintenant)
            for gamme_id in gamme_ids:
                # Récupérer les infos de la gamme depuis la DB
                gamme = db.get_gamme_by_id(gamme_id)
                if not gamme:
                    logger.warning(f"Gamme {gamme_id} introuvable dans la DB, ignorée")
                    continue
                
                gamme_name = gamme.get('name')  # Peut être None
                gamme_url = gamme.get('url')
                gamme_status = gamme.get('status')
                gamme_category = gamme.get('category')
                
                # Vérifier que la gamme appartient bien à la catégorie en cours de traitement
                if gamme_category != category_name:
                    logger.warning(f"Gamme {gamme_id} ({gamme_name}) appartient à la catégorie '{gamme_category}' mais on traite '{category_name}', ignorée")
                    continue
                
                # Marquer la gamme comme en cours de traitement
                if gamme_status != 'error':  # Ne pas traiter les gammes en erreur (sans nom)
                    db.update_gamme_status(gamme_id, 'processing')
                    logger.info(f"\n  Gamme: {gamme_name or 'SANS NOM'} (ID: {gamme_id}) - Status: processing")
                else:
                    logger.info(f"\n  Gamme: {gamme_name or 'SANS NOM'} (ID: {gamme_id}) - Status: error (ignorée)")
                    continue
                
                # Obtenir les produits de cette gamme
                products = get_products_from_gamme(driver, session, gamme_url, headless=headless)
                logger.info(f"  Produits trouvés: {len(products)}")
                
                # Traiter chaque produit
                for idx, product_info in enumerate(products, 1):
                    product_code = product_info.get('code')
                    product_url = product_info.get('url')
                    product_name = product_info.get('name', f"Produit {product_code}")
                    
                    if not product_code or not product_url:
                        continue
                    
                    logger.info(f"\n  [{idx}/{len(products)}] {product_name}")
                    logger.info(f"    Extraction du titre depuis: {product_url}")
                    
                    try:
                        # Extraire le nom et la description depuis la page produit (h3 dans product-body)
                        product_name_from_page, description = extract_product_name_and_description(
                            driver, session, product_url,
                            fallback_name=product_name,
                            headless=headless
                        )
                        
                        # Le titre est maintenant obligatoire (pas de fallback)
                        final_product_name = product_name_from_page
                        logger.info(f"    ✓ Titre final: {final_product_name}")
                        
                        # Extraire tous les variants de ce produit
                        variants = extract_variants_from_product_page(
                            driver, session, product_url, product_code, headless=headless
                        )
                        
                        if not variants:
                            logger.warning(f"    Aucun variant trouvé pour {product_code}")
                            continue
                        
                        logger.info(f"    {len(variants)} variant(s) extrait(s) pour {product_code}")
                        
                        # Extraire le statut "new" du produit
                        logger.info(f"    Vérification du label 'new' depuis: {product_url}")
                        is_new_product = extract_product_is_new(driver, session, product_url, headless=headless)
                        if is_new_product:
                            logger.info(f"    ✓ Produit marqué comme 'new' (Published sera FALSE)")
                        
                        # Générer le handle Shopify
                        handle = slugify(final_product_name)
                        
                        # Ajouter le produit dans la DB avec le nom et la description
                        base_url_without_params = product_url.split('?')[0]
                        product_id = db.add_product(
                            product_code=product_code,
                            handle=handle,
                            title=final_product_name,
                            description=description,
                            vendor=vendor_name,
                            product_type=category_name,
                            tags=category_name,
                            category=category_name,
                            gamme=gamme_name,
                            base_url=base_url_without_params,
                            is_new=is_new_product
                        )
                        
                        # Lier le produit à sa gamme dans la table gamme_products
                        db.link_gamme_to_product(gamme_id, product_id)
                        
                        # Extraire et ajouter les images du produit depuis la page produit
                        # Utiliser l'URL du premier variant pour extraire les images
                        if variants:
                            first_variant_code = variants[0]['code']
                            variant_url_for_images = f"{base_url_without_params}?code_vl={first_variant_code}"
                            logger.info(f"    Extraction des images depuis: {variant_url_for_images}")
                            product_images = extract_product_images(driver, session, variant_url_for_images, headless=headless)
                            if product_images:
                                logger.info(f"    {len(product_images)} image(s) trouvée(s)")
                                for img_idx, image_url in enumerate(product_images, 1):
                                    db.add_image(product_id, image_url, position=img_idx)
                            else:
                                logger.warning(f"    Aucune image trouvée pour {product_code}")
                        
                        # Ajouter tous les variants
                        variants_added = 0
                        for variant_info in variants:
                            variant_code = variant_info['code']
                            variant_url = f"{base_url_without_params}?code_vl={variant_code}"
                            size_text = variant_info.get('size_text', '')
                            
                            try:
                                logger.debug(f"      Ajout du variant {variant_code} pour produit {product_code} (product_id: {product_id})")
                                variant_id, is_new = db.add_variant(
                                    product_id=product_id,
                                    code_vl=variant_code,
                                    url=variant_url,
                                    size_text=size_text,
                                    raise_on_duplicate=False  # Ne pas lever d'exception si existe déjà
                                )
                                
                                if is_new:
                                    variants_added += 1
                                    logger.info(f"      ✓ Variant {variant_code} ajouté (ID: {variant_id})")
                                else:
                                    # Le variant existe déjà, mettre à jour les champs de base
                                    db.update_variant_collect(
                                        variant_id=variant_id,
                                        url=variant_url,
                                        size_text=size_text
                                    )
                                    variants_added += 1
                                    logger.info(f"      ✓ Variant {variant_code} mis à jour (déjà présent, ID: {variant_id})")
                            except Exception as variant_error:
                                logger.error(f"      ✗ Erreur lors de l'ajout du variant {variant_code}: {variant_error}")
                                import traceback
                                logger.error(traceback.format_exc())
                                # Ne pas compter ce variant mais continuer
                        
                        total_variants_collected += variants_added
                        logger.info(f"    {product_code}: {variants_added} variant(s) collecté(s) ou mis à jour")
                        
                    except Exception as e:
                        error_msg = str(e)
                        logger.warning(f"    Erreur lors de l'extraction du titre pour {product_code}: {error_msg}")
                        
                        from garnier.scraper_garnier_module import wait_for_url_accessible
                        from requests.exceptions import RequestException, Timeout, ConnectionError
                        import time
                        
                        # Retry jusqu'à 3 fois avec vérification HTTP 200 avant chaque tentative
                        max_retries = 3
                        retry_success = False
                        
                        for retry_attempt in range(1, max_retries + 1):
                            logger.info(f"    Tentative de retry {retry_attempt}/{max_retries} pour {product_code}...")
                            
                            # Ré-authentifier au 2ème essai pour rafraîchir la session
                            if retry_attempt == 2:
                                logger.info(f"    🔐 Ré-authentification avant retry {retry_attempt}...")
                                try:
                                    driver, session = authenticate(headless=headless)
                                    logger.info(f"    ✓ Ré-authentification réussie")
                                except Exception as auth_error:
                                    logger.error(f"    ✗ Erreur lors de la ré-authentification: {auth_error}")
                            
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
                            
                            # Si l'URL ne retourne pas 200, utiliser wait_for_url_accessible
                            if not url_returns_200:
                                logger.info(f"    Attente que l'URL retourne 200 avec wait_for_url_accessible (max 2 minutes)...")
                                # Utiliser un timeout plus court pour les retries (2 minutes au lieu de 5)
                                import time as time_module
                                start_wait = time_module.time()
                                max_wait_for_retry = 120  # 2 minutes maximum pour les retries
                                url_became_accessible = False
                                
                                while time_module.time() - start_wait < max_wait_for_retry:
                                    try:
                                        response = session.get(product_url, timeout=10, allow_redirects=True)
                                        if response.status_code == 200:
                                            url_became_accessible = True
                                            logger.info(f"    ✓ URL retourne maintenant 200 après attente - Retry {retry_attempt} autorisé")
                                            break
                                    except Exception:
                                        pass
                                    time_module.sleep(10)  # Vérifier toutes les 10 secondes
                                
                                if url_became_accessible:
                                    url_returns_200 = True
                                else:
                                    logger.warning(f"    ✗ URL n'est pas devenue accessible après {max_wait_for_retry}s, abandon du retry")
                            
                            # Retry uniquement si l'URL retourne 200
                            if url_returns_200:
                                try:
                                    logger.info(f"    Retry {retry_attempt}: Extraction du titre depuis: {product_url}")
                                    product_name_from_page, description = extract_product_name_and_description(
                                        driver, session, product_url,
                                        fallback_name=product_name,
                                        headless=headless
                                    )
                                    
                                    final_product_name = product_name_from_page
                                    logger.info(f"    ✓ Titre final (après retry {retry_attempt}): {final_product_name}")
                                    
                                    # Si le retry réussit, continuer avec l'extraction des variants
                                    variants = extract_variants_from_product_page(
                                        driver, session, product_url, product_code, headless=headless
                                    )
                                    
                                    if not variants:
                                        logger.warning(f"    Aucun variant trouvé pour {product_code} (après retry {retry_attempt})")
                                        continue
                                    
                                    # Extraire le statut "new" du produit
                                    logger.info(f"    Vérification du label 'new' depuis: {product_url}")
                                    is_new_product = extract_product_is_new(driver, session, product_url, headless=headless)
                                    if is_new_product:
                                        logger.info(f"    ✓ Produit marqué comme 'new' (Published sera FALSE)")
                                    
                                    # Générer le handle et ajouter le produit
                                    handle = slugify(final_product_name)
                                    base_url_without_params = product_url.split('?')[0]
                                    product_id = db.add_product(
                                        product_code=product_code,
                                        handle=handle,
                                        title=final_product_name,
                                        description=description,
                                        vendor=vendor_name,
                                        product_type=category_name,
                                        tags=category_name,
                                        category=category_name,
                                        gamme=gamme_name,
                                        base_url=base_url_without_params,
                                        is_new=is_new_product
                                    )
                                    
                                    # Lier le produit à sa gamme dans la table gamme_products
                                    db.link_gamme_to_product(gamme_id, product_id)
                                    
                                    # Extraire et ajouter les images du produit depuis la page produit
                                    if variants:
                                        first_variant_code = variants[0]['code']
                                        variant_url_for_images = f"{base_url_without_params}?code_vl={first_variant_code}"
                                        logger.info(f"    Extraction des images depuis: {variant_url_for_images}")
                                        product_images = extract_product_images(driver, session, variant_url_for_images, headless=headless)
                                        if product_images:
                                            logger.info(f"    {len(product_images)} image(s) trouvée(s)")
                                            for img_idx, image_url in enumerate(product_images, 1):
                                                db.add_image(product_id, image_url, position=img_idx)
                                        else:
                                            logger.warning(f"    Aucune image trouvée pour {product_code}")
                                    
                                    # Ajouter les variants
                                    variants_added = 0
                                    for variant_info in variants:
                                        variant_code = variant_info['code']
                                        variant_url = f"{base_url_without_params}?code_vl={variant_code}"
                                        size_text = variant_info.get('size_text', '')
                                        
                                        variant_id, is_new = db.add_variant(
                                            product_id=product_id,
                                            code_vl=variant_code,
                                            url=variant_url,
                                            size_text=size_text,
                                            raise_on_duplicate=False
                                        )
                                        
                                        if is_new:
                                            variants_added += 1
                                        else:
                                            db.update_variant_collect(
                                                variant_id=variant_id,
                                                url=variant_url,
                                                size_text=size_text
                                            )
                                            variants_added += 1
                                    
                                    total_variants_collected += variants_added
                                    logger.info(f"    {product_code}: {variants_added} variant(s) collecté(s) ou mis à jour (après retry {retry_attempt})")
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
                            error_msg_final = f"Erreur persistante après {max_retries} tentatives pour {product_code}: {error_msg}"
                            logger.error(f"    {error_msg_final}")
                            # Marquer le produit en erreur et continuer
                            try:
                                cursor = db.conn.cursor()
                                cursor.execute('SELECT id FROM products WHERE product_code = ?', (product_code,))
                                row = cursor.fetchone()
                                if row:
                                    product_id = row['id']
                                    # Mettre à jour le produit en erreur avec retry_count
                                    cursor.execute('''
                                        UPDATE products 
                                        SET status = 'error', 
                                            error_message = ?,
                                            retry_count = COALESCE(retry_count, 0) + 1,
                                            updated_at = CURRENT_TIMESTAMP
                                        WHERE id = ?
                                    ''', (error_msg_final[:500], product_id))
                                else:
                                    # Créer le produit en erreur (sans titre)
                                    handle = slugify(product_code) if product_code else f"produit-{product_code}"
                                    base_url_without_params = product_url.split('?')[0] if product_url else None
                                    product_id = db.add_product(
                                        product_code=product_code,
                                        handle=handle,
                                        title=None,
                                        vendor=vendor_name,
                                        product_type=category_name,
                                        tags=category_name,
                                        category=category_name,
                                        gamme=gamme_name,
                                        base_url=base_url_without_params,
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
                                logger.warning(f"    Produit {product_code} marqué en erreur dans la DB (retry_count incrémenté)")
                            except Exception as db_error:
                                logger.warning(f"    Impossible de marquer le produit en erreur dans la DB: {db_error}")
                        continue
                
                # Fin du traitement de tous les produits de cette gamme
                # Vérifier et mettre à jour le statut de la gamme
                logger.info(f"\n  Vérification du statut de la gamme {gamme_id}...")
                db.update_gamme_status_if_all_products_processed(gamme_id)
        
        # Afficher les statistiques
        stats = db.get_stats()
        logger.info(f"\n{'='*60}")
        logger.info("Collecte terminée!")
        logger.info(f"Total produits: {stats['total_products']}")
        logger.info(f"Total variants: {stats['total_variants']}")
        logger.info(f"Variants par statut: {stats['variants_by_status']}")
        logger.info(f"{'='*60}")
        
        # Retry automatique si demandé
        if retry_errors_after:
            retry_error_products(db, driver, session, headless=headless)
        
    finally:
        db.close()
        if driver:
            driver.quit()


def slugify(text: str) -> str:
    """Convertit un texte en slug pour le Handle Shopify."""
    import unicodedata
    import re
    
    text = unicodedata.normalize('NFKD', text)
    text = text.encode('ascii', 'ignore').decode('ascii')
    text = re.sub(r'[^\w\s-]', '', text.lower())
    text = re.sub(r'[-\s]+', '-', text)
    return text.strip('-')


def retry_error_products(db, driver, session, category=None, gamme=None, headless=True):
    """
    Retente automatiquement les produits en erreur après la collecte initiale.
    Pour chaque produit, fait jusqu'à 3 tentatives avec wait_for_url_accessible (5 min).
    
    Args:
        db: Instance GarnierDB
        driver: WebDriver Selenium
        session: Session requests
        category: Catégorie à filtrer (optionnel)
        gamme: Gamme à filtrer (optionnel)
        headless: Mode headless
    
    Returns:
        Nombre de produits corrigés avec succès
    """
    from garnier.scraper_garnier_module import (
        extract_product_name_and_description,
        extract_variants_from_product_page,
        extract_product_is_new,
        extract_product_images,
        slugify,
        wait_for_url_accessible
    )
    from csv_config import get_csv_config
    from requests.exceptions import RequestException, Timeout, ConnectionError
    import time
    
    cursor = db.conn.cursor()
    
    # Récupérer les produits en erreur (retry_count < 3)
    if category and gamme:
        cursor.execute('''
            SELECT product_code, base_url, retry_count
            FROM products 
            WHERE status = 'error' 
            AND category = ?
            AND (gamme = ? OR gamme LIKE ?)
            AND (retry_count IS NULL OR retry_count < 3)
        ''', (category, gamme, f'{gamme}%'))
    elif category:
        cursor.execute('''
            SELECT product_code, base_url, retry_count
            FROM products 
            WHERE status = 'error' 
            AND category = ?
            AND (retry_count IS NULL OR retry_count < 3)
        ''', (category,))
    else:
        cursor.execute('''
            SELECT product_code, base_url, retry_count
            FROM products 
            WHERE status = 'error'
            AND (retry_count IS NULL OR retry_count < 3)
        ''')
    
    error_products = cursor.fetchall()
    
    if not error_products:
        logger.info("✓ Aucun produit en erreur à retenter")
        return 0
    
    logger.info(f"\n{'='*60}")
    logger.info(f"🔄 RETRY AUTOMATIQUE DES ERREURS")
    logger.info(f"{'='*60}")
    logger.info(f"Produits en erreur à retenter : {len(error_products)}")
    
    success_count = 0
    csv_config_manager = get_csv_config()
    vendor_name = csv_config_manager.get_vendor('garnier')
    
    for error_product in error_products:
        product_code = error_product['product_code']
        product_url = error_product['base_url']
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
            
            # Ré-authentifier au 2ème essai pour rafraîchir la session
            if retry_attempt == 2:
                logger.info(f"    🔐 Ré-authentification avant retry {retry_attempt}...")
                try:
                    driver, session = authenticate(headless=headless)
                    logger.info(f"    ✓ Ré-authentification réussie")
                except Exception as auth_error:
                    logger.error(f"    ✗ Erreur lors de la ré-authentification: {auth_error}")
            
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
            
            # Si l'URL ne retourne pas 200, utiliser wait_for_url_accessible (5 min max)
            if not url_returns_200:
                logger.info(f"    Attente que l'URL retourne 200 (max 5 minutes avec wait_for_url_accessible)...")
                try:
                    # check_interval=30s, timeout=10s par requête, max 5 min total
                    url_became_accessible = wait_for_url_accessible(session, product_url, check_interval=30, timeout=10)
                    
                    if url_became_accessible:
                        url_returns_200 = True
                        logger.info(f"    ✓ URL retourne maintenant 200 après attente - Retry {retry_attempt} autorisé")
                    else:
                        logger.warning(f"    ✗ URL n'est pas devenue accessible après 5 minutes")
                except Exception as wait_error:
                    logger.warning(f"    ✗ Erreur lors de l'attente: {wait_error}")
            
            # Retry uniquement si l'URL retourne 200
            if url_returns_200:
                try:
                    logger.info(f"    Retry {retry_attempt}: Extraction du titre depuis: {product_url}")
                    
                    # Extraire le nom et la description
                    product_name_from_page, description = extract_product_name_and_description(
                        driver, session, product_url,
                        fallback_name=f"Produit {product_code}",
                        headless=headless
                    )
                    
                    if not product_name_from_page or not product_name_from_page.strip():
                        raise Exception("Titre toujours manquant")
                    
                    logger.info(f"    ✓ Titre extrait (retry {retry_attempt}): {product_name_from_page}")
                    
                    # Extraire les variants
                    variants = extract_variants_from_product_page(
                        driver, session, product_url, product_code, headless=headless
                    )
                    
                    if not variants:
                        logger.warning(f"    Aucun variant trouvé (retry {retry_attempt})")
                        raise Exception("Aucun variant trouvé")
                    
                    logger.info(f"    {len(variants)} variant(s) extrait(s)")
                    
                    # Extraire is_new
                    is_new_product = extract_product_is_new(driver, session, product_url, headless=headless)
                    
                    # Mettre à jour le produit dans la DB
                    handle = slugify(product_name_from_page)
                    base_url_without_params = product_url.split('?')[0]
                    
                    # Récupérer l'ID du produit existant
                    cursor.execute('SELECT id FROM products WHERE product_code = ?', (product_code,))
                    row = cursor.fetchone()
                    product_id = row['id'] if row else None
                    
                    if product_id:
                        # Mettre à jour le produit avec les nouvelles données
                        cursor.execute('''
                            UPDATE products 
                            SET handle = ?, title = ?, description = ?, 
                                status = 'pending', error_message = NULL,
                                retry_count = COALESCE(retry_count, 0) + 1,
                                is_new = ?, updated_at = CURRENT_TIMESTAMP
                            WHERE id = ?
                        ''', (handle, product_name_from_page, description, 1 if is_new_product else 0, product_id))
                        
                        # Extraire et ajouter les images
                        first_variant_code = variants[0]['code']
                        variant_url_for_images = f"{base_url_without_params}?code_vl={first_variant_code}"
                        logger.info(f"    Extraction des images depuis: {variant_url_for_images}")
                        product_images = extract_product_images(driver, session, variant_url_for_images, headless=headless)
                        
                        if product_images:
                            logger.info(f"    {len(product_images)} image(s) trouvée(s)")
                            # Supprimer les anciennes images
                            cursor.execute('DELETE FROM product_images WHERE product_id = ?', (product_id,))
                            # Ajouter les nouvelles
                            for img_idx, image_url in enumerate(product_images, 1):
                                db.add_image(product_id, image_url, position=img_idx)
                        
                        # Ajouter/mettre à jour les variants
                        variants_added = 0
                        for variant_info in variants:
                            variant_code = variant_info['code']
                            variant_url = f"{base_url_without_params}?code_vl={variant_code}"
                            size_text = variant_info.get('size_text', '')
                            
                            variant_id, is_new_variant = db.add_variant(
                                product_id=product_id,
                                code_vl=variant_code,
                                url=variant_url,
                                size_text=size_text,
                                raise_on_duplicate=False
                            )
                            
                            if is_new_variant:
                                variants_added += 1
                            else:
                                db.update_variant_collect(
                                    variant_id=variant_id,
                                    url=variant_url,
                                    size_text=size_text
                                )
                                variants_added += 1
                        
                        db.conn.commit()
                        success_count += 1
                        retry_success = True
                        logger.info(f"    ✓ Produit {product_code} corrigé avec succès (retry {retry_attempt})")
                        logger.info(f"    {variants_added} variant(s) collecté(s) ou mis à jour")
                        break  # Sortir de la boucle de retry
                    else:
                        logger.warning(f"    ✗ Produit {product_code} introuvable dans la DB")
                        break
                        
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
                WHERE product_code = ?
            ''', (product_code,))
            db.conn.commit()
            logger.warning(f"  ✗ Produit {product_code} reste en erreur (retry_count incrémenté)")
    
    logger.info(f"\n{'='*60}")
    logger.info(f"✓ Retry automatique terminé : {success_count}/{len(error_products)} produits corrigés")
    logger.info(f"{'='*60}\n")
    
    return success_count


if __name__ == '__main__':
    parser = argparse.ArgumentParser(
        description='Collecte les URLs avec code_vl depuis le site Garnier-Thiebaut'
    )
    parser.add_argument(
        '--category', '-c',
        action='append',
        help='Catégorie(s) à traiter (peut être répété plusieurs fois)'
    )
    
    parser.add_argument(
        '--gamme-url', '-g',
        help='URL directe d\'une gamme spécifique à traiter (prioritaire sur --category)'
    )
    
    parser.add_argument(
        '--gamme-status',
        choices=['pending', 'processing', 'error', 'completed'],
        help='Filtrer les gammes par statut (pending, processing, error, completed)'
    )
    
    parser.add_argument(
        '--db', '-d',
        default=None,  # None = valeur par défaut depuis app_config.json
        help='Chemin vers la base de données SQLite (défaut: garnier_products.db depuis app_config.json)'
    )
    parser.add_argument(
        '--no-headless',
        action='store_true',
        help='Désactiver le mode headless (afficher le navigateur)'
    )
    
    parser.add_argument(
        '--retry-errors-after',
        action='store_true',
        help='Après la collecte, retenter automatiquement les produits en erreur (max 3 fois total)'
    )
    
    parser.add_argument(
        '--retry-errors-only',
        action='store_true',
        help='Retenter UNIQUEMENT les produits en erreur (ne pas collecter de nouveaux produits)'
    )
    
    args = parser.parse_args()
    
    # Utiliser la DB par défaut depuis app_config.json si non spécifiée
    if args.db is None:
        output_db = get_garnier_db_path()
        logger.info(f"Utilisation de la base de données: {output_db}")
    else:
        output_db = args.db
    
    # Si --retry-errors-only est activé, ne traiter QUE les produits en erreur
    if args.retry_errors_only:
        logger.info("Mode retry-errors-only activé : traitement UNIQUEMENT des produits en erreur")
        
        # Initialiser la connexion DB
        db = GarnierDB(output_db)
        
        # Authentification
        driver, session = authenticate(headless=not args.no_headless)
        if not driver:
            logger.error("Impossible de s'authentifier")
            sys.exit(1)
        
        try:
            # Déterminer la catégorie à filtrer
            category = None
            if args.category and len(args.category) > 0:
                category = args.category[0]
                logger.info(f"Filtrage par catégorie: {category}")
            
            # Appeler retry_error_products directement
            retry_error_products(
                db=db,
                driver=driver,
                session=session,
                category=category,
                gamme=None,
                headless=not args.no_headless
            )
            
            logger.info("✅ Retraitement des produits en erreur terminé")
            
        finally:
            if driver:
                driver.quit()
            db.close()
        
        sys.exit(0)
    
    # Si une URL de gamme est fournie, utiliser collect_from_gamme_url
    if args.gamme_url:
        # Récupérer la catégorie si fournie (obligatoire pour gamme)
        category = None
        if args.category and len(args.category) > 0:
            category = args.category[0]  # Prendre la première catégorie
        
        if not category:
            logger.error("L'option --category est obligatoire avec --gamme-url")
            sys.exit(1)
        
        variants_collected, driver, session = collect_from_gamme_url(
            gamme_url=args.gamme_url,
            output_db=output_db,
            headless=not args.no_headless,
            category=category,
            retry_errors_after=args.retry_errors_after
        )
        # Fermer le driver après la collecte (pour le mode CLI)
        if driver:
            driver.quit()
        
        # #region agent log
        import json
        import time
        try:
            with open('/Users/jean-loup/shopify/garnier/.cursor/debug.log', 'a') as f:
                f.write(json.dumps({
                    "sessionId": "debug-session",
                    "runId": "run1",
                    "hypothesisId": "E",
                    "location": "scraper-garnier-collect.py:__main__:GAMME_COMPLETE",
                    "message": "collect_from_gamme_url completed, script ending",
                    "data": {"variants_collected": variants_collected},
                    "timestamp": int(time.time() * 1000)
                }) + "\n")
        except:
            pass
        # #endregion
        
        logger.info("Script terminé avec succès")
    else:
        collect_urls(
            categories=args.category,
            output_db=output_db,
            headless=not args.no_headless,
            retry_errors_after=args.retry_errors_after,
            gamme_status_filter=args.gamme_status
        )
        
        # #region agent log
        import json
        import time
        try:
            with open('/Users/jean-loup/shopify/garnier/.cursor/debug.log', 'a') as f:
                f.write(json.dumps({
                    "sessionId": "debug-session",
                    "runId": "run1",
                    "hypothesisId": "E",
                    "location": "scraper-garnier-collect.py:__main__:COLLECT_COMPLETE",
                    "message": "collect_urls completed, script ending",
                    "data": {},
                    "timestamp": int(time.time() * 1000)
                }) + "\n")
        except:
            pass
        # #endregion
        
        logger.info("Script terminé avec succès")

