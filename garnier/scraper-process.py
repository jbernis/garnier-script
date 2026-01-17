#!/usr/bin/env python3
"""
Script pour traiter les URLs stockées dans la base de données
et extraire les données des variants.
"""

import sys
import os
import argparse
import logging
import time
from dotenv import load_dotenv

# Ajouter le répertoire parent au path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

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


def process_variant(variant_id, code_vl, url, db, driver, session, headless=True):
    """
    Traite un variant individuel et stocke ses données dans la DB.
    Si erreur liée à l'indisponibilité du site, attend que le site redevienne accessible.
    
    Args:
        variant_id: ID du variant dans la DB
        code_vl: Code variant
        url: URL du variant
        db: Instance de GarnierDB
        driver: WebDriver Selenium
        session: Session requests
        headless: Mode headless
    """
    try:
        # Marquer comme en cours de traitement
        db.mark_variant_processing(variant_id)
        logger.info(f"Traitement du variant {code_vl}...")
        
        # Extraire les données du variant (retourne aussi driver et session mis à jour)
        variant_data, driver, session = extract_variant_data_from_url(
            driver, session, url, code_vl, headless=headless
        )
        
        if not variant_data:
            raise Exception("Aucune donnée extraite")
        
        # Log pour déboguer avant stockage
        logger.info(f"  Stockage dans DB - SKU: '{variant_data.get('sku')}', Gencode: '{variant_data.get('gencode')}'")
        
        # Validation des données obligatoires
        sku = variant_data.get('sku')
        gencode = variant_data.get('gencode')
        stock = variant_data.get('stock')
        price_pvc = variant_data.get('price_pvc')
        
        # Vérifier que SKU et gencode ne sont pas vides
        if not sku or not sku.strip():
            raise Exception("SKU manquant ou vide")
        
        if not gencode or not gencode.strip():
            raise Exception("Code-barre (gencode) manquant ou vide")
        
        # Vérifier que stock n'est pas None
        if stock is None:
            raise Exception("Stock manquant")
        
        # Vérifier que price_pvc n'est pas vide
        if not price_pvc or not str(price_pvc).strip():
            raise Exception("Prix PVC manquant ou vide")
        
        # Si validation OK, stocker les données dans la DB
        db.update_variant_data(
            variant_id=variant_id,
            sku=sku,
            gencode=gencode,
            price_pa=variant_data.get('price_pa'),
            price_pvc=price_pvc,
            stock=stock,
            size=variant_data.get('size'),
            color=variant_data.get('color'),
            material=variant_data.get('material'),
            status='completed'
        )
        
        logger.info(f"✓ Variant {code_vl} traité avec succès (SKU: {sku}, Gencode: {gencode}, Stock: {stock}, Prix PVC: {price_pvc})")
        
        # Vérifier si tous les variants du produit sont maintenant traités
        # Si oui, mettre à jour le statut du produit immédiatement
        cursor = db.conn.cursor()
        cursor.execute('SELECT product_id FROM product_variants WHERE id = ?', (variant_id,))
        row = cursor.fetchone()
        if row:
            product_id = row['product_id']
            db.update_product_status_if_all_variants_processed(product_id)
        
        return True, driver, session
        
    except Exception as e:
        error_msg = str(e)
        
        # Détecter les erreurs liées à l'indisponibilité du site
        is_site_unavailable = any(keyword in error_msg.lower() for keyword in [
            'timeout', 'non trouvé après', 'introuvable', 
            'connection', 'unreachable', 'refused', '503', '502', '500',
            'div.tabs.product-tabs introuvable'
        ])
        
        if is_site_unavailable:
            logger.warning(f"Erreur d'accès au site pour le variant {code_vl}: {error_msg}")
            logger.info("Vérification de la disponibilité de l'URL du variant...")
            
            # Attendre que l'URL spécifique du variant soit accessible avant de continuer (vérifie toutes les 30s jusqu'à obtenir 200)
            logger.info(f"Vérification de l'accessibilité de l'URL du variant: {url}")
            wait_for_url_accessible(session, url, check_interval=30, timeout=300)  # 5 minutes
            
            logger.info(f"URL du variant accessible, reprise de l'extraction pour le variant {code_vl}...")
            
            # Réessayer l'extraction maintenant que l'URL du variant est accessible
            try:
                db.mark_variant_processing(variant_id)  # Remettre en traitement
                
                # Extraire les données du variant (retourne aussi driver et session mis à jour)
                variant_data, driver, session = extract_variant_data_from_url(
                    driver, session, url, code_vl, headless=headless
                )
                
                if not variant_data:
                    raise Exception("Aucune donnée extraite")
                    
                # Log pour déboguer avant stockage
                logger.info(f"  Stockage dans DB (retry) - SKU: '{variant_data.get('sku')}', Gencode: '{variant_data.get('gencode')}'")
                
                # Validation des données obligatoires
                sku = variant_data.get('sku')
                gencode = variant_data.get('gencode')
                stock = variant_data.get('stock')
                price_pvc = variant_data.get('price_pvc')
                
                # Vérifier que SKU et gencode ne sont pas vides
                if not sku or not sku.strip():
                    raise Exception("SKU manquant ou vide après retry")
                
                if not gencode or not gencode.strip():
                    raise Exception("Code-barre (gencode) manquant ou vide après retry")
                
                # Vérifier que stock n'est pas None
                if stock is None:
                    raise Exception("Stock manquant après retry")
                
                # Vérifier que price_pvc n'est pas vide
                if not price_pvc or not str(price_pvc).strip():
                    raise Exception("Prix PVC manquant ou vide après retry")
                
                # Si validation OK, stocker les données dans la DB
                db.update_variant_data(
                    variant_id=variant_id,
                    sku=sku,
                    gencode=gencode,
                    price_pa=variant_data.get('price_pa'),
                    price_pvc=price_pvc,
                    stock=stock,
                    size=variant_data.get('size'),
                    color=variant_data.get('color'),
                    material=variant_data.get('material'),
                    status='completed'
                )
                
                logger.info(f"✓ Variant {code_vl} traité avec succès après reprise (SKU: {sku}, Gencode: {gencode}, Stock: {stock}, Prix PVC: {price_pvc})")
                
                # Vérifier si tous les variants du produit sont maintenant traités
                cursor = db.conn.cursor()
                cursor.execute('SELECT product_id FROM product_variants WHERE id = ?', (variant_id,))
                row = cursor.fetchone()
                if row:
                    product_id = row['product_id']
                    db.update_product_status_if_all_variants_processed(product_id)
                
                return True, driver, session
                    
            except Exception as retry_error:
                error_msg = str(retry_error)
                db.mark_variant_error(variant_id, error_msg)
                logger.error(f"✗ Erreur persistante pour le variant {code_vl}: {error_msg}")
            return False, driver, session
        else:
            # Erreur non liée à l'indisponibilité du site
            db.mark_variant_error(variant_id, error_msg)
            logger.error(f"✗ Erreur pour le variant {code_vl}: {error_msg}")
            return False, driver, session


def process_urls(code_vl=None, status='pending', limit=None, retry_errors=False,
                output_db='garnier_products.db', headless=True, category=None, gamme=None):
    """
    Traite les URLs depuis la base de données.
    
    Args:
        code_vl: Traiter un code_vl spécifique (None = tous)
        status: Statut à traiter ('pending', 'error', etc.)
        limit: Limiter le nombre d'URLs à traiter
        retry_errors: Réessayer les URLs en erreur
        output_db: Chemin vers la base de données
        headless: Mode headless pour Selenium
        category: Filtrer par catégorie (optionnel)
        gamme: Filtrer par gamme (optionnel)
    """
    db = GarnierDB(output_db)
    driver = None
    session = None
    
    try:
        # Authentification
        driver, session = authenticate(headless=headless)
        if not driver:
            logger.error("Impossible de s'authentifier")
            return
        
        logger.info("Authentification réussie")
        
        # Déterminer le statut à traiter
        if retry_errors:
            status = 'error'
            logger.info("Mode réessai des erreurs activé")
        
        # Récupérer les variants à traiter
        if code_vl:
            variant = db.get_variant_by_code_vl(code_vl)
            if not variant:
                logger.error(f"Variant {code_vl} non trouvé dans la base de données")
                return
            variants = [variant]
        else:
            # Filtrer par catégorie/gamme si spécifié
            if status == 'pending':
                variants = db.get_pending_variants(limit=limit, category=category, gamme=gamme)
            else:
                variants = db.get_error_variants(limit=limit, category=category, gamme=gamme)
            
            # Logger les filtres appliqués
            if category or gamme:
                filter_msg = "Filtrage appliqué: "
                if category:
                    filter_msg += f"catégorie={category} "
                if gamme:
                    filter_msg += f"gamme={gamme}"
                logger.info(filter_msg)
        
        if not variants:
            logger.info(f"Aucun variant avec le statut '{status}' à traiter")
            return
        
        logger.info(f"Traitement de {len(variants)} variant(s)...")
        
        # Traiter chaque variant
        success_count = 0
        error_count = 0
        
        for idx, variant in enumerate(variants, 1):
            variant_id = variant['id']
            code_vl = variant['code_vl']
            url = variant['url']
            
            logger.info(f"\n[{idx}/{len(variants)}] Variant {code_vl}")
            
            # Traiter le variant (retourne aussi driver et session mis à jour)
            success, driver, session = process_variant(
                variant_id, code_vl, url, db, driver, session, headless=headless
            )
            
            if success:
                success_count += 1
            else:
                error_count += 1
            
            # Petite pause entre les variants pour éviter de surcharger le serveur
            if idx < len(variants):
                time.sleep(1)
        
        # Mettre à jour le status des produits après traitement
        logger.info("\nMise à jour du status des produits...")
        db.update_products_status_after_processing()
        
        # Afficher les statistiques
        stats = db.get_stats()
        logger.info(f"\n{'='*60}")
        logger.info("Traitement terminé!")
        logger.info(f"Succès: {success_count}")
        logger.info(f"Erreurs: {error_count}")
        logger.info(f"\nStatistiques globales:")
        logger.info(f"  Total produits: {stats['total_products']}")
        logger.info(f"  Total variants: {stats['total_variants']}")
        logger.info(f"  Variants par statut: {stats['variants_by_status']}")
        logger.info(f"{'='*60}")
        
    finally:
        db.close()
        if driver:
            driver.quit()


if __name__ == '__main__':
    parser = argparse.ArgumentParser(
        description='Traite les URLs stockées dans la base de données'
    )
    parser.add_argument(
        '--code-vl',
        help='Traiter un code_vl spécifique'
    )
    parser.add_argument(
        '--status',
        default='pending',
        help='Statut à traiter (défaut: pending)'
    )
    parser.add_argument(
        '--limit',
        type=int,
        help='Limiter le nombre d\'URLs à traiter'
    )
    parser.add_argument(
        '--retry-errors',
        action='store_true',
        help='Réessayer les URLs en erreur'
    )
    # Lire la configuration pour la valeur par défaut
    default_db = get_garnier_db_path()
    
    parser.add_argument(
        '--db', '-d',
        default=default_db,
        help=f'Chemin vers la base de données SQLite (défaut: {default_db})'
    )
    parser.add_argument(
        '--no-headless',
        action='store_true',
        help='Désactiver le mode headless (afficher le navigateur)'
    )
    parser.add_argument(
        '--category', '-c',
        help='Filtrer par catégorie (optionnel)'
    )
    parser.add_argument(
        '--gamme', '-g',
        help='Filtrer par gamme (optionnel)'
    )
    
    args = parser.parse_args()
    
    process_urls(
        code_vl=args.code_vl,
        status=args.status,
        limit=args.limit,
        retry_errors=args.retry_errors,
        output_db=args.db,
        headless=not args.no_headless,
        category=args.category,
        gamme=args.gamme
    )

