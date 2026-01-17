#!/usr/bin/env python3
"""
Script de test pour tester le scraper Garnier avec seulement quelques gammes.
Permet de tester rapidement sans scraper toutes les gammes d'une catégorie.

Exemples d'utilisation:
    # Tester 2 gammes avec 3 produits par gamme
    python test-garnier.py --category "Linge de lit" --limit-gammes 2 --limit-products 3
    
    # Tester à partir de la page 18 (pour déboguer un problème spécifique)
    python test-garnier.py --category "Linge de lit" --start-page 18 --limit-gammes 2 --limit-products 3
    
    # Tester avec aperçu
    python test-garnier.py --category "Linge de table" --limit-gammes 1 --limit-products 2 --preview
    
    # Tester avec navigateur visible (débogage)
    python test-garnier.py --category "Linge de lit" --limit-gammes 1 --no-headless
"""

import sys
import os
import importlib.util

# Importer le module garnier_functions
spec = importlib.util.spec_from_file_location(
    "garnier.garnier_functions",
    os.path.join(os.path.dirname(__file__), "garnier", "garnier_functions.py")
)
garnier_functions = importlib.util.module_from_spec(spec)
spec.loader.exec_module(garnier_functions)

# Importer les fonctions nécessaires
authenticate = garnier_functions.authenticate
get_categories = garnier_functions.get_categories
get_gammes_from_category = garnier_functions.get_gammes_from_category
get_products_from_gamme = garnier_functions.get_products_from_gamme
slugify = garnier_functions.slugify
OUTPUT_DIR = garnier_functions.OUTPUT_DIR
import argparse
import logging
import time
from datetime import datetime
import pandas as pd

# Configuration du logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def main():
    parser = argparse.ArgumentParser(
        description='Script de test pour scraper Garnier avec quelques gammes seulement'
    )
    parser.add_argument(
        '--category', '-c',
        type=str,
        required=True,
        help='Nom de la catégorie à tester (ex: "Linge de lit")'
    )
    parser.add_argument(
        '--limit-gammes', '-g',
        type=int,
        default=2,
        help='Nombre maximum de gammes à tester (défaut: 2)'
    )
    parser.add_argument(
        '--start-page', '-s',
        type=int,
        default=1,
        help='Page de départ pour l\'extraction des gammes (défaut: 1). Utile pour tester une page spécifique où un problème se produit.'
    )
    parser.add_argument(
        '--limit-products', '-p',
        type=int,
        default=3,
        help='Nombre maximum de produits par gamme à tester (défaut: 3)'
    )
    parser.add_argument(
        '--output', '-o',
        type=str,
        default=None,
        help='Nom du fichier CSV de sortie (défaut: auto-généré)'
    )
    parser.add_argument(
        '--preview',
        action='store_true',
        help='Afficher un aperçu du CSV avant sauvegarde'
    )
    parser.add_argument(
        '--preview-rows',
        type=int,
        default=10,
        help='Nombre de lignes à afficher dans l\'aperçu (défaut: 10)'
    )
    parser.add_argument(
        '--no-headless',
        action='store_true',
        help='Désactiver le mode headless (afficher le navigateur)'
    )
    
    args = parser.parse_args()
    
    # Générer le nom du fichier CSV automatiquement si non spécifié
    if args.output is None:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        category_slug = slugify(args.category)
        args.output = f"test_garnier_{category_slug}_{timestamp}.csv"
    
    # Construire le chemin complet du fichier CSV
    if os.path.isabs(args.output) or '/' in args.output or '\\' in args.output:
        csv_path = args.output
    else:
        csv_path = os.path.join(OUTPUT_DIR, args.output)
    
    logger.info("="*80)
    logger.info("SCRIPT DE TEST GARNIER")
    logger.info("="*80)
    logger.info(f"Catégorie: {args.category}")
    logger.info(f"Page de départ: {args.start_page}")
    logger.info(f"Limite gammes: {args.limit_gammes}")
    logger.info(f"Limite produits par gamme: {args.limit_products}")
    logger.info(f"Fichier CSV de sortie: {csv_path}")
    logger.info("="*80)
    
    driver = None
    
    try:
        # 1. Authentification
        logger.info("Authentification en cours...")
        driver, session = authenticate(headless=not args.no_headless)
        
        # 2. Trouver la catégorie
        logger.info("Recherche de la catégorie...")
        all_categories = get_categories(driver, session)
        category = None
        for cat in all_categories:
            if cat['name'].lower() == args.category.lower():
                category = cat
                break
        
        if not category:
            logger.error(f"Catégorie '{args.category}' non trouvée.")
            logger.info("Catégories disponibles:")
            for cat in all_categories:
                logger.info(f"  - {cat['name']}")
            return
        
        logger.info(f"Catégorie trouvée: {category['name']}")
        
        # 3. Extraire les gammes (limitées)
        # Si start_page > 1, naviguer jusqu'à cette page avant d'extraire
        if args.start_page > 1:
            logger.info(f"Navigation jusqu'à la page {args.start_page}...")
            driver.get(category['url'])
            time.sleep(5)  # Attendre le chargement
            
            # Importer get_next_page_info depuis le scraper
            get_next_page_info = garnier_functions.get_next_page_info
            
            current_page = 1
            while current_page < args.start_page:
                next_page_num, next_element = get_next_page_info(driver)
                if next_element is not None and next_page_num:
                    try:
                        driver.execute_script("arguments[0].scrollIntoView(true);", next_element)
                        time.sleep(0.5)
                        next_element.click()
                        time.sleep(3)
                        current_page = next_page_num
                        logger.info(f"Navigation vers la page {current_page}")
                    except Exception as e:
                        logger.error(f"Erreur lors de la navigation vers la page {args.start_page}: {e}")
                        break
                else:
                    logger.warning(f"Impossible d'atteindre la page {args.start_page}, page actuelle: {current_page}")
                    break
            
            if current_page < args.start_page:
                logger.error(f"Impossible d'atteindre la page {args.start_page}, arrêt à la page {current_page}")
                return
        
        logger.info(f"Extraction des gammes (limite: {args.limit_gammes}, à partir de la page {args.start_page})...")
        all_gammes = get_gammes_from_category(driver, session, category['url'], start_page=args.start_page)
        
        if not all_gammes:
            logger.warning("Aucune gamme trouvée dans cette catégorie.")
            return
        
        # Limiter le nombre de gammes dès maintenant pour éviter de traiter trop de données
        gammes_to_test = all_gammes[:args.limit_gammes]
        logger.info(f"Test de {len(gammes_to_test)} gamme(s) sur {len(all_gammes)} trouvée(s)")
        
        # 4. Extraire les produits (limités)
        all_products_data = []
        
        for gamme_idx, gamme in enumerate(gammes_to_test, 1):
            logger.info(f"\n{'='*80}")
            logger.info(f"Gamme {gamme_idx}/{len(gammes_to_test)}: {gamme['name']}")
            logger.info(f"{'='*80}")
            
            # Extraire les produits (on limite déjà le nombre de gammes, donc pas besoin de tout extraire)
            products = get_products_from_gamme(driver, session, gamme['url'], headless=not args.no_headless)
            
            if not products:
                logger.warning(f"Aucun produit trouvé dans la gamme {gamme['name']}")
                continue
            
            # Limiter le nombre de produits par gamme dès maintenant
            products_to_process = products[:args.limit_products]
            logger.info(f"Traitement de {len(products_to_process)} produit(s) sur {len(products)} trouvé(s)")
            
            for product_idx, product in enumerate(products_to_process, 1):
                logger.info(f"\n  Produit {product_idx}/{len(products_to_process)}: {product['name']}")
                
                # Extraire les détails
                details, driver, session = get_product_details(
                    driver, session, product['url'], product['name'],
                    headless=not args.no_headless
                )
                
                if details:
                    all_products_data.append({
                        'category': category['name'],
                        'image_url': product.get('image_url'),
                        'details': details,
                        'session': session,
                        'driver': driver
                    })
                    logger.info(f"    ✓ {len(details.get('variants', []))} variante(s) extraite(s)")
                else:
                    logger.warning(f"    ✗ Échec de l'extraction des détails")
                
                # Pas de sleep pour les tests - on veut que ce soit rapide
                # time.sleep(0.5)  # Désactivé pour accélérer les tests
        
        # 5. Générer le CSV
        if all_products_data:
            logger.info(f"\n{'='*80}")
            logger.info(f"Génération du CSV avec {len(all_products_data)} produit(s)...")
            logger.info(f"{'='*80}")
            
            df = generate_shopify_csv(all_products_data)
            
            # Afficher un aperçu si demandé
            if args.preview:
                pd.set_option('display.max_columns', None)
                pd.set_option('display.max_colwidth', 50)
                pd.set_option('display.width', None)
                pd.set_option('display.max_rows', args.preview_rows)
                
                print("\n" + "="*80)
                print("📊 APERÇU DU CSV")
                print("="*80)
                print(f"\nTotal de lignes: {len(df)}")
                print(f"Total de colonnes: {len(df.columns)}")
                print(f"Produits uniques: {df['Handle'].nunique()}")
                
                important_cols = ['Handle', 'Title', 'Variant SKU', 'Variant Price', 
                                 'Option1 Name', 'Option1 Value', 'Variant Barcode']
                available_cols = [col for col in important_cols if col in df.columns]
                
                print(f"\nPremières {args.preview_rows} lignes:")
                print("-"*80)
                print(df[available_cols].head(args.preview_rows).to_string(index=False))
                print("="*80)
            
            # Sauvegarder le CSV
            csv_dir = os.path.dirname(csv_path)
            if csv_dir and not os.path.exists(csv_dir):
                os.makedirs(csv_dir, exist_ok=True)
                logger.info(f"Répertoire créé: {csv_dir}")
            
            df.to_csv(csv_path, index=False, encoding='utf-8')
            logger.info(f"\n✅ Fichier CSV généré: {csv_path}")
            logger.info(f"Total: {len(df)} lignes (variantes de produits)")
        else:
            logger.warning("Aucun produit trouvé. Aucun fichier CSV généré.")
        
        logger.info("\n" + "="*80)
        logger.info("Test terminé avec succès!")
        logger.info("="*80)
        
    except Exception as e:
        logger.error(f"Erreur fatale: {e}", exc_info=True)
    finally:
        if driver:
            try:
                driver.quit()
            except:
                pass

if __name__ == "__main__":
    main()

