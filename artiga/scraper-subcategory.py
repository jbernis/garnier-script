#!/usr/bin/env python3
"""
Script orchestrateur pour traiter une sous-catégorie Artiga complète.
Exécute séquentiellement: collect → process → generate-csv
"""

import sys
import os
import argparse
import logging
from datetime import datetime

# Ajouter le répertoire parent au path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.artiga_db import ArtigaDB
from utils.app_config import get_artiga_db_path

# Importer les fonctions des scripts modulaires
import importlib.util

# Charger scraper-collect.py
collect_path = os.path.join(os.path.dirname(__file__), "scraper-collect.py")
spec = importlib.util.spec_from_file_location("artiga_collect", collect_path)
collect_module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(collect_module)

# Charger scraper-process.py
process_path = os.path.join(os.path.dirname(__file__), "scraper-process.py")
spec = importlib.util.spec_from_file_location("artiga_process", process_path)
process_module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(process_module)

# Charger scraper-generate-csv.py
generate_path = os.path.join(os.path.dirname(__file__), "scraper-generate-csv.py")
spec = importlib.util.spec_from_file_location("artiga_generate", generate_path)
generate_module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(generate_module)

# Récupérer les fonctions
collect_from_subcategory_url = collect_module.collect_from_subcategory_url
process_urls = process_module.process_urls
generate_csv_from_db = generate_module.generate_csv_from_db

# Configuration du logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def main():
    parser = argparse.ArgumentParser(
        description='Traite une sous-catégorie Artiga complète (collect → process → generate-csv)'
    )
    parser.add_argument(
        '--url', '-u',
        required=True,
        help='URL de la sous-catégorie à traiter'
    )
    parser.add_argument(
        '--category', '-c',
        required=True,
        help='Nom de la catégorie parent'
    )
    parser.add_argument(
        '--subcategory', '-s',
        required=True,
        help='Nom de la sous-catégorie'
    )
    parser.add_argument(
        '--db', '-d',
        default=None,
        help='Chemin vers la base de données SQLite (défaut: artiga_products.db)'
    )
    parser.add_argument(
        '--output', '-o',
        help='Chemin du fichier CSV de sortie (défaut: auto-généré)'
    )
    parser.add_argument(
        '--no-headless',
        action='store_true',
        help='Désactiver le mode headless (afficher le navigateur)'
    )
    parser.add_argument(
        '--skip-collect',
        action='store_true',
        help='Ignorer l\'étape de collecte'
    )
    parser.add_argument(
        '--skip-process',
        action='store_true',
        help='Ignorer l\'étape de traitement'
    )
    parser.add_argument(
        '--skip-csv',
        action='store_true',
        help='Ignorer l\'étape de génération CSV'
    )
    
    args = parser.parse_args()
    
    # Utiliser la DB par défaut si non spécifiée
    if args.db is None:
        output_db = get_artiga_db_path()
        logger.info(f"Utilisation de la base de données: {output_db}")
    else:
        output_db = args.db
    
    start_time = datetime.now()
    
    logger.info(f"\n{'='*80}")
    logger.info(f"TRAITEMENT DE LA SOUS-CATÉGORIE: {args.subcategory}")
    logger.info(f"Catégorie: {args.category}")
    logger.info(f"URL: {args.url}")
    logger.info(f"Base de données: {output_db}")
    logger.info(f"{'='*80}\n")
    
    # ÉTAPE 1: Collecte
    if not args.skip_collect:
        logger.info(f"\n{'='*80}")
        logger.info("ÉTAPE 1/3: COLLECTE DES PRODUITS")
        logger.info(f"{'='*80}\n")
        
        try:
            variants_collected, driver, session = collect_from_subcategory_url(
                subcategory_url=args.url,
                category=args.category,
                subcategory_name=args.subcategory,
                output_db=output_db,
                headless=not args.no_headless
            )
            
            logger.info(f"\n✓ Collecte terminée: {variants_collected} produit(s) collecté(s)")
            
            # Fermer le driver
            if driver:
                try:
                    driver.quit()
                except:
                    pass
            
        except Exception as e:
            logger.error(f"\n✗ Erreur lors de la collecte: {e}")
            return
    else:
        logger.info("\n⊘ Étape de collecte ignorée (--skip-collect)")
    
    # ÉTAPE 2: Traitement
    if not args.skip_process:
        logger.info(f"\n{'='*80}")
        logger.info("ÉTAPE 2/3: TRAITEMENT DES VARIANTS")
        logger.info(f"{'='*80}\n")
        
        try:
            process_urls(
                status='pending',
                output_db=output_db,
                headless=not args.no_headless,
                category=args.category,
                subcategory=args.subcategory
            )
            
            logger.info("\n✓ Traitement terminé")
            
        except Exception as e:
            logger.error(f"\n✗ Erreur lors du traitement: {e}")
            return
    else:
        logger.info("\n⊘ Étape de traitement ignorée (--skip-process)")
    
    # ÉTAPE 3: Génération CSV
    if not args.skip_csv:
        logger.info(f"\n{'='*80}")
        logger.info("ÉTAPE 3/3: GÉNÉRATION DU CSV SHOPIFY")
        logger.info(f"{'='*80}\n")
        
        try:
            generate_csv_from_db(
                output_file=args.output,
                output_db=output_db,
                supplier='artiga',
                categories=[args.category],
                subcategory=args.subcategory
            )
            
            logger.info("\n✓ CSV généré avec succès")
            
        except Exception as e:
            logger.error(f"\n✗ Erreur lors de la génération du CSV: {e}")
            return
    else:
        logger.info("\n⊘ Étape de génération CSV ignorée (--skip-csv)")
    
    # Afficher les statistiques finales
    db = ArtigaDB(output_db)
    stats = db.get_stats()
    db.close()
    
    end_time = datetime.now()
    duration = end_time - start_time
    
    logger.info(f"\n{'='*80}")
    logger.info("TRAITEMENT TERMINÉ AVEC SUCCÈS")
    logger.info(f"{'='*80}")
    logger.info(f"Sous-catégorie: {args.subcategory}")
    logger.info(f"Durée totale: {duration}")
    logger.info(f"\nStatistiques de la base de données:")
    logger.info(f"  Total produits: {stats['total_products']}")
    logger.info(f"  Total variants: {stats['total_variants']}")
    logger.info(f"  Variants par statut: {stats['variants_by_status']}")
    logger.info(f"{'='*80}\n")


if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        logger.info("\n\nInterruption par l'utilisateur")
        sys.exit(1)
    except Exception as e:
        logger.error(f"\n\nErreur fatale: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
