#!/usr/bin/env python3
"""
Script pour nettoyer les entrées orphelines dans gamme_products
qui pointent vers des produits qui n'existent plus.
"""

import sys
import os
import logging

# Ajouter le répertoire parent au path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from utils.garnier_db import GarnierDB
from utils.app_config import get_garnier_db_path

# Configuration du logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def clean_orphaned_gamme_products(db_path=None):
    """
    Nettoie les entrées orphelines dans gamme_products.
    
    Args:
        db_path: Chemin vers la base de données (optionnel)
    """
    if db_path is None:
        db_path = get_garnier_db_path()
    
    db = GarnierDB(db_path)
    cursor = db.conn.cursor()
    
    try:
        # Compter les entrées orphelines avant nettoyage
        cursor.execute('''
            SELECT COUNT(*) as count
            FROM gamme_products gp
            LEFT JOIN products p ON gp.product_id = p.id
            WHERE p.id IS NULL
        ''')
        orphaned_count = cursor.fetchone()['count']
        
        if orphaned_count == 0:
            logger.info("Aucune entrée orpheline trouvée dans gamme_products")
            return 0
        
        logger.info(f"Trouvé {orphaned_count} entrée(s) orpheline(s) dans gamme_products")
        
        # Compter les gammes affectées
        cursor.execute('''
            SELECT COUNT(DISTINCT gamme_id) as count
            FROM gamme_products gp
            LEFT JOIN products p ON gp.product_id = p.id
            WHERE p.id IS NULL
        ''')
        affected_gammes = cursor.fetchone()['count']
        logger.info(f"Gammes affectées: {affected_gammes}")
        
        # Supprimer les entrées orphelines
        cursor.execute('''
            DELETE FROM gamme_products
            WHERE product_id NOT IN (SELECT id FROM products)
        ''')
        deleted_count = cursor.rowcount
        db.conn.commit()
        
        logger.info(f"✓ {deleted_count} entrée(s) orpheline(s) supprimée(s)")
        
        # Mettre à jour les statuts des gammes qui étaient en 'processing'
        # et qui n'ont plus de produits valides
        cursor.execute('''
            SELECT DISTINCT g.id, g.name, g.status
            FROM gammes g
            LEFT JOIN gamme_products gp ON g.id = gp.gamme_id
            WHERE g.status = 'processing'
            AND gp.gamme_id IS NULL
        ''')
        empty_processing_gammes = cursor.fetchall()
        
        if empty_processing_gammes:
            logger.info(f"\nTrouvé {len(empty_processing_gammes)} gamme(s) en 'processing' sans produits valides")
            for gamme in empty_processing_gammes:
                gamme_id = gamme['id']
                gamme_name = gamme['name'] or 'SANS NOM'
                db.update_gamme_status(gamme_id, 'error')
                logger.info(f"  ✓ Gamme {gamme_id} ({gamme_name}) passée à 'error'")
        
        return deleted_count
        
    finally:
        db.close()


if __name__ == '__main__':
    import argparse
    
    parser = argparse.ArgumentParser(
        description='Nettoie les entrées orphelines dans gamme_products'
    )
    parser.add_argument(
        '--db', '-d',
        help='Chemin vers la base de données SQLite'
    )
    
    args = parser.parse_args()
    
    deleted = clean_orphaned_gamme_products(args.db)
    print(f"\n{'='*60}")
    print(f"Nettoyage terminé: {deleted} entrée(s) supprimée(s)")
    print(f"{'='*60}")
