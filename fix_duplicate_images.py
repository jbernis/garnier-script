#!/usr/bin/env python3
"""
Script pour supprimer les images dupliquées dans la base de données Garnier.
"""

import sys
import os

# Ajouter le répertoire parent au path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from utils.garnier_db import GarnierDB
from utils.app_config import get_garnier_db_path

def fix_duplicate_images():
    """Supprime les images dupliquées dans la base de données."""
    db = GarnierDB(get_garnier_db_path())
    cursor = db.conn.cursor()
    
    print("🔍 Recherche des images dupliquées...")
    
    # Trouver tous les produits
    cursor.execute('SELECT id FROM products')
    products = cursor.fetchall()
    
    total_removed = 0
    products_fixed = 0
    
    for product_row in products:
        product_id = product_row[0]
        
        # Récupérer toutes les images de ce produit
        cursor.execute('''
            SELECT id, image_url, image_position
            FROM product_images
            WHERE product_id = ?
            ORDER BY id
        ''', (product_id,))
        
        images = cursor.fetchall()
        
        if not images:
            continue
        
        # Détecter les doublons (même URL)
        seen_urls = {}
        duplicates = []
        
        for img in images:
            img_id, url, position = img
            if url in seen_urls:
                # C'est un doublon, on le supprime
                duplicates.append(img_id)
            else:
                # Première occurrence, on la garde
                seen_urls[url] = img_id
        
        if duplicates:
            products_fixed += 1
            total_removed += len(duplicates)
            print(f"  Produit {product_id}: {len(duplicates)} doublons trouvés")
            
            # Supprimer les doublons
            for dup_id in duplicates:
                cursor.execute('DELETE FROM product_images WHERE id = ?', (dup_id,))
    
    # Valider les changements
    db.conn.commit()
    
    print(f"\n✅ Nettoyage terminé:")
    print(f"   - Produits corrigés: {products_fixed}")
    print(f"   - Images dupliquées supprimées: {total_removed}")
    
    db.close()

if __name__ == '__main__':
    fix_duplicate_images()
