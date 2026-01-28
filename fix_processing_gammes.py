#!/usr/bin/env python3
"""
Script pour mettre à jour le statut des gammes en "processing" qui ont tous leurs produits/variants complétés.
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from utils.garnier_db import GarnierDB
from utils.app_config import get_garnier_db_path

def fix_processing_gammes(category=None):
    """Met à jour le statut des gammes en processing qui devraient être completed."""
    db = GarnierDB(get_garnier_db_path())
    
    try:
        # Récupérer les gammes en processing
        if category:
            gammes = db.get_gammes_by_status(status='processing', category=category)
        else:
            gammes = db.get_gammes_by_status(status='processing')
        
        print(f"Trouvé {len(gammes)} gamme(s) en statut 'processing'")
        
        updated_count = 0
        for gamme in gammes:
            gamme_id = gamme['id']
            gamme_name = gamme['name']
            gamme_category = gamme['category']
            
            print(f"\nVérification de la gamme {gamme_id} ({gamme_name}) - Catégorie: {gamme_category}")
            
            # Appeler la fonction de mise à jour
            result = db.update_gamme_status_if_all_products_processed(gamme_id)
            
            if result:
                updated_count += 1
                print(f"  ✓ Statut mis à jour")
            else:
                print(f"  ✗ Statut non changé (produits/variants pas tous complétés)")
        
        print(f"\n{'='*60}")
        print(f"Total: {updated_count} gamme(s) mise(s) à jour")
        print(f"{'='*60}")
        
    finally:
        db.close()

if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(description='Met à jour le statut des gammes en processing')
    parser.add_argument('--category', '-c', help='Catégorie spécifique (optionnel)')
    args = parser.parse_args()
    
    fix_processing_gammes(category=args.category)
