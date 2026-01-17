#!/usr/bin/env python3
"""
Script pour forcer la mise à jour du statut des produits
basé sur le statut de leurs variants.
"""
import sys
from utils.garnier_db import GarnierDB
from utils.app_config import get_garnier_db_path
import logging

logging.basicConfig(level=logging.INFO, format='%(message)s')
logger = logging.getLogger(__name__)

if __name__ == '__main__':
    db_path = get_garnier_db_path()
    logger.info(f"Mise à jour des statuts des produits dans {db_path}")
    logger.info(f"{'='*60}")
    
    db = GarnierDB(db_path)
    
    # Afficher les stats avant
    cursor = db.conn.cursor()
    cursor.execute('''
        SELECT status, COUNT(*) as count
        FROM products
        GROUP BY status
    ''')
    stats_before = dict(cursor.fetchall())
    logger.info(f"Statuts AVANT mise à jour:")
    for status, count in stats_before.items():
        logger.info(f"  - {status}: {count}")
    
    # Mettre à jour les statuts
    logger.info(f"\n{'='*60}")
    db.update_products_status_after_processing()
    
    # Afficher les stats après
    cursor.execute('''
        SELECT status, COUNT(*) as count
        FROM products
        GROUP BY status
    ''')
    stats_after = dict(cursor.fetchall())
    logger.info(f"\nStatuts APRÈS mise à jour:")
    for status, count in stats_after.items():
        logger.info(f"  - {status}: {count}")
    
    db.close()
    
    logger.info(f"{'='*60}")
    logger.info("✓ Mise à jour terminée avec succès !")
