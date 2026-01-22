#!/usr/bin/env python3
"""
Script pour collecter toutes les gammes depuis le site Garnier-Thiebaut
et les stocker dans une base de données SQLite avec mécanisme de retry.
"""

import sys
import os
import argparse
import logging
from dotenv import load_dotenv

# Ajouter le répertoire parent au path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.garnier_db import GarnierDB
from utils.app_config import get_garnier_db_path
from garnier.scraper_garnier_module import (
    authenticate, get_categories, get_gammes_from_category,
    wait_for_url_accessible, check_site_accessible
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


def collect_gamme_with_retry(gamme_info, category_name, db, driver, session, headless=True, max_retries=3):
    """
    Collecte une gamme avec mécanisme de retry et ré-authentification.
    Cette fonction ajoute simplement la gamme en DB, le retry concerne l'extraction des gammes
    qui se fait avant dans collect_gammes_from_category.
    
    Args:
        gamme_info: Dict avec 'name' et 'url' de la gamme
        category_name: Nom de la catégorie
        db: Instance de GarnierDB
        driver: WebDriver Selenium (non utilisé ici mais retourné pour compatibilité)
        session: Session requests (non utilisé ici mais retourné pour compatibilité)
        headless: Mode headless
        max_retries: Nombre maximum de tentatives (non utilisé ici, pour compatibilité)
    
    Returns:
        Tuple (success: bool, driver, session)
    """
    gamme_url = gamme_info['url']
    gamme_name = gamme_info.get('name')  # Peut être None
    
    try:
        # Ajouter ou mettre à jour la gamme dans la DB
        # Si name est None, add_gamme() mettra automatiquement status='error'
        gamme_id = db.add_gamme(url=gamme_url, category=category_name, name=gamme_name)
        
        # Si on a réussi à obtenir un nom, mettre à jour le status
        if gamme_name:
            db.update_gamme_status(gamme_id, 'pending')
            logger.info(f"✓ Gamme collectée: {gamme_name} (ID: {gamme_id})")
        else:
            logger.warning(f"⚠ Gamme sans nom collectée: {gamme_url} (ID: {gamme_id}, status=error)")
        
        return True, driver, session
        
    except Exception as e:
        error_msg = str(e)
        logger.error(f"Erreur lors de la collecte de la gamme {gamme_url}: {error_msg}")
        
        # Marquer en erreur
        try:
            gamme_id = db.add_gamme(url=gamme_url, category=category_name, name=None)
            db.mark_gamme_error(gamme_id)
            logger.error(f"✗ Gamme marquée en erreur: {gamme_url}")
        except Exception as db_error:
            logger.error(f"Erreur lors de la mise à jour de la DB: {db_error}")
        
        return False, driver, session


def collect_gammes_from_category(category_name, category_url, db, driver, session, headless=True, retry_errors_only=False):
    """
    Collecte toutes les gammes d'une catégorie.
    
    Args:
        category_name: Nom de la catégorie
        category_url: URL de la catégorie
        db: Instance de GarnierDB
        driver: WebDriver Selenium
        session: Session requests
        headless: Mode headless
        retry_errors_only: Si True, ne collecte que les gammes en erreur
    
    Returns:
        Tuple (nombre_gammes_collectées, driver, session)
    """
    logger.info(f"\n{'='*60}")
    logger.info(f"Traitement de la catégorie: {category_name}")
    logger.info(f"{'='*60}")
    
    # Si retry_errors_only, récupérer uniquement les gammes en erreur depuis la DB
    if retry_errors_only:
        error_gammes = db.get_error_gammes(category=category_name)
        if not error_gammes:
            logger.info(f"Aucune gamme en erreur pour la catégorie '{category_name}'")
            return 0, driver, session
        
        logger.info(f"{len(error_gammes)} gamme(s) en erreur à retraiter")
        # Pour les gammes en erreur, on doit réessayer l'extraction depuis le site
        # On va utiliser les URLs des gammes en erreur pour réessayer
        gammes_to_collect = []
        for error_gamme in error_gammes:
            gamme_url = error_gamme['url']
            logger.info(f"Re-tentative d'extraction pour la gamme: {gamme_url}")
            
            # Réessayer l'extraction avec retry et ré-authentification
            for retry_attempt in range(1, 4):  # 3 tentatives max
                try:
                    if retry_attempt > 1:
                        logger.info(f"Tentative {retry_attempt}/3 pour la gamme {gamme_url}")
                        
                        # Ré-authentification au 2ème retry et suivants
                        if retry_attempt >= 2:
                            logger.info("Ré-authentification en cours...")
                            try:
                                if driver:
                                    driver.quit()
                                driver, session = authenticate(headless=headless)
                                if not driver:
                                    raise Exception("Impossible de s'authentifier")
                                logger.info("✓ Ré-authentification réussie")
                            except Exception as auth_error:
                                logger.error(f"Erreur lors de la ré-authentification: {auth_error}")
                                if retry_attempt < 3:
                                    continue
                                else:
                                    break
                        
                        # Attendre que l'URL soit accessible
                        logger.info(f"Vérification de l'accessibilité de l'URL: {gamme_url}")
                        if not wait_for_url_accessible(session, gamme_url, check_interval=30, timeout=300):
                            logger.error(f"URL toujours inaccessible après timeout pour {gamme_url}")
                            if retry_attempt < 3:
                                continue
                            else:
                                break
                    
                    # Essayer d'extraire le nom depuis l'URL directement
                    from urllib.parse import urlparse, unquote
                    parsed = urlparse(gamme_url)
                    gamme_name = None
                    if 'code_gamme' in parsed.query:
                        gamme_name = unquote(parsed.query.split('code_gamme=')[1].split('&')[0])
                        gamme_name = gamme_name.replace('_', ' ').replace('-', ' ').strip().upper()
                    
                    if gamme_name:
                        gammes_to_collect.append({'name': gamme_name, 'url': gamme_url})
                        logger.info(f"✓ Nom extrait depuis l'URL: {gamme_name}")
                        break
                    else:
                        logger.warning(f"⚠ Impossible d'extraire le nom depuis l'URL: {gamme_url}")
                        if retry_attempt < 3:
                            continue
                        else:
                            # Dernière tentative, ajouter quand même avec name=None
                            gammes_to_collect.append({'name': None, 'url': gamme_url})
                            break
                            
                except Exception as e:
                    logger.error(f"Erreur lors de la tentative {retry_attempt}: {e}")
                    if retry_attempt < 3:
                        continue
                    else:
                        # Dernière tentative échouée, ajouter avec name=None
                        gammes_to_collect.append({'name': None, 'url': gamme_url})
                        break
    else:
        # Récupérer toutes les gammes de la catégorie
        logger.info("Extraction des gammes (avec pagination automatique)...")
        gammes_to_collect = get_gammes_from_category(driver, session, category_url)
        logger.info(f"Gammes trouvées: {len(gammes_to_collect)}")
    
    collected_count = 0
    error_count = 0
    
    for idx, gamme_info in enumerate(gammes_to_collect, 1):
        gamme_name = gamme_info.get('name', 'SANS NOM')
        gamme_url = gamme_info['url']
        
        logger.info(f"\n[{idx}/{len(gammes_to_collect)}] Gamme: {gamme_name}")
        logger.info(f"  URL: {gamme_url}")
        
        success, driver, session = collect_gamme_with_retry(
            gamme_info, category_name, db, driver, session, headless=headless
        )
        
        if success:
            collected_count += 1
        else:
            error_count += 1
    
    logger.info(f"\n{'='*60}")
    logger.info(f"Résumé pour la catégorie '{category_name}':")
    logger.info(f"  ✓ Collectées: {collected_count}")
    logger.info(f"  ✗ En erreur: {error_count}")
    logger.info(f"{'='*60}\n")
    
    return collected_count, driver, session


def main(output_db=None, category_name=None, headless=True, retry_errors_only=False):
    """
    Fonction principale de collecte des gammes.
    
    Args:
        output_db: Chemin vers la base de données (None = utiliser la config)
        category_name: Nom de la catégorie à traiter (None = toutes)
        headless: Mode headless
        retry_errors_only: Si True, ne collecte que les gammes en erreur
    """
    if output_db is None:
        output_db = get_garnier_db_path()
    
    db = GarnierDB(output_db)
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
        
        # Collecter les gammes pour chaque catégorie
        total_collected = 0
        total_errors = 0
        
        for category_info in category_list:
            cat_name = category_info['name']
            cat_url = category_info['url']
            
            collected, driver, session = collect_gammes_from_category(
                cat_name, cat_url, db, driver, session,
                headless=headless, retry_errors_only=retry_errors_only
            )
            
            total_collected += collected
        
        logger.info(f"\n{'='*60}")
        logger.info(f"RÉSUMÉ GLOBAL")
        logger.info(f"  ✓ Gammes collectées: {total_collected}")
        logger.info(f"{'='*60}\n")
        
    except Exception as e:
        logger.error(f"Erreur lors de la collecte: {e}", exc_info=True)
    finally:
        if driver:
            driver.quit()
        db.close()


if __name__ == '__main__':
    parser = argparse.ArgumentParser(
        description='Collecte des gammes depuis le site Garnier-Thiebaut'
    )
    parser.add_argument(
        '--category', '-c',
        help='Nom de la catégorie à traiter (optionnel, par défaut toutes les catégories)'
    )
    parser.add_argument(
        '--output-db', '-o',
        help='Chemin vers la base de données (optionnel, utilise la config par défaut)'
    )
    parser.add_argument(
        '--no-headless',
        action='store_true',
        help='Désactiver le mode headless (afficher le navigateur)'
    )
    parser.add_argument(
        '--retry-errors-only',
        action='store_true',
        help='Ne collecter que les gammes en erreur'
    )
    
    args = parser.parse_args()
    
    main(
        output_db=args.output_db,
        category_name=args.category,
        headless=not args.no_headless,
        retry_errors_only=args.retry_errors_only
    )
