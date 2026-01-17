#!/usr/bin/env python3
"""
Script pour vérifier les doublons dans la base de données Garnier.
"""

import sqlite3
import sys
import os

# Ajouter le répertoire parent au path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from utils.garnier_db import GarnierDB
from utils.app_config import get_garnier_db_path

def check_duplicates(db_path):
    """Vérifie les doublons dans la base de données."""
    db = GarnierDB(db_path)
    
    try:
        cursor = db.conn.cursor()
        
        print("=" * 60)
        print("VÉRIFICATION DES DOUBLONS")
        print("=" * 60)
        
        # 1. Vérifier les doublons de code_vl (ne devrait pas être possible avec UNIQUE)
        print("\n1. Vérification des doublons de code_vl:")
        cursor.execute('''
            SELECT code_vl, COUNT(*) as count
            FROM product_variants
            GROUP BY code_vl
            HAVING COUNT(*) > 1
        ''')
        duplicates_code_vl = cursor.fetchall()
        if duplicates_code_vl:
            print(f"   ⚠️  {len(duplicates_code_vl)} code_vl en doublon trouvé(s):")
            for row in duplicates_code_vl:
                print(f"      - code_vl: {row['code_vl']} apparaît {row['count']} fois")
        else:
            print("   ✅ Aucun doublon de code_vl trouvé")
        
        # 2. Vérifier les variants avec le même code_vl mais différents product_id
        # (ce qui pourrait indiquer un problème de logique)
        print("\n2. Vérification des variants avec même code_vl mais différents produits:")
        cursor.execute('''
            SELECT code_vl, COUNT(DISTINCT product_id) as product_count, GROUP_CONCAT(DISTINCT product_id) as product_ids
            FROM product_variants
            GROUP BY code_vl
            HAVING COUNT(DISTINCT product_id) > 1
        ''')
        same_code_different_products = cursor.fetchall()
        if same_code_different_products:
            print(f"   ⚠️  {len(same_code_different_products)} code_vl associé(s) à plusieurs produits:")
            for row in same_code_different_products:
                print(f"      - code_vl: {row['code_vl']} associé aux produits: {row['product_ids']}")
        else:
            print("   ✅ Aucun code_vl associé à plusieurs produits")
        
        # 3. Vérifier les variants avec la même URL mais différents code_vl
        print("\n3. Vérification des variants avec même URL mais différents code_vl:")
        cursor.execute('''
            SELECT url, COUNT(DISTINCT code_vl) as code_count, GROUP_CONCAT(DISTINCT code_vl) as code_vls
            FROM product_variants
            GROUP BY url
            HAVING COUNT(DISTINCT code_vl) > 1
        ''')
        same_url_different_codes = cursor.fetchall()
        if same_url_different_codes:
            print(f"   ⚠️  {len(same_url_different_codes)} URL(s) avec plusieurs code_vl:")
            for row in same_url_different_codes[:10]:  # Limiter à 10 pour l'affichage
                print(f"      - URL: {row['url'][:80]}...")
                print(f"        code_vl: {row['code_vls']}")
        else:
            print("   ✅ Aucune URL avec plusieurs code_vl")
        
        # 4. Vérifier les variants avec le même SKU (si rempli)
        print("\n4. Vérification des variants avec même SKU:")
        cursor.execute('''
            SELECT sku, COUNT(*) as count, GROUP_CONCAT(DISTINCT code_vl) as code_vls
            FROM product_variants
            WHERE sku IS NOT NULL AND sku != ''
            GROUP BY sku
            HAVING COUNT(*) > 1
        ''')
        duplicates_sku = cursor.fetchall()
        if duplicates_sku:
            print(f"   ⚠️  {len(duplicates_sku)} SKU(s) en doublon trouvé(s):")
            for row in duplicates_sku[:10]:  # Limiter à 10
                print(f"      - SKU: {row['sku']} apparaît {row['count']} fois")
                print(f"        code_vl: {row['code_vls']}")
        else:
            print("   ✅ Aucun doublon de SKU trouvé")
        
        # 5. Statistiques générales
        print("\n5. Statistiques générales:")
        cursor.execute('SELECT COUNT(*) FROM product_variants')
        total_variants = cursor.fetchone()[0]
        cursor.execute('SELECT COUNT(DISTINCT code_vl) FROM product_variants')
        unique_code_vl = cursor.fetchone()[0]
        cursor.execute('SELECT COUNT(*) FROM products')
        total_products = cursor.fetchone()[0]
        
        print(f"   - Total variants: {total_variants}")
        print(f"   - code_vl uniques: {unique_code_vl}")
        print(f"   - Total produits: {total_products}")
        
        if total_variants != unique_code_vl:
            print(f"   ⚠️  ATTENTION: Il y a {total_variants - unique_code_vl} variant(s) en doublon!")
        else:
            print("   ✅ Le nombre de variants correspond au nombre de code_vl uniques")
        
        # 6. Vérifier les produits avec plusieurs variants ayant le même code_vl
        print("\n6. Vérification des produits avec variants dupliqués:")
        cursor.execute('''
            SELECT p.product_code, p.handle, COUNT(pv.id) as variant_count, COUNT(DISTINCT pv.code_vl) as unique_code_vl_count
            FROM products p
            JOIN product_variants pv ON p.id = pv.product_id
            GROUP BY p.id
            HAVING COUNT(pv.id) != COUNT(DISTINCT pv.code_vl)
        ''')
        products_with_duplicates = cursor.fetchall()
        if products_with_duplicates:
            print(f"   ⚠️  {len(products_with_duplicates)} produit(s) avec variants dupliqués:")
            for row in products_with_duplicates[:10]:  # Limiter à 10
                print(f"      - Produit {row['product_code']} ({row['handle']}):")
                print(f"        {row['variant_count']} variants, {row['unique_code_vl_count']} code_vl uniques")
        else:
            print("   ✅ Aucun produit avec variants dupliqués")
        
        print("\n" + "=" * 60)
        
    finally:
        db.close()

if __name__ == '__main__':
    import argparse
    
    parser = argparse.ArgumentParser(description='Vérifie les doublons dans la base de données Garnier')
    parser.add_argument(
        '--db', '-d',
        default=None,
        help='Chemin vers la base de données SQLite (défaut: depuis app_config.json)'
    )
    
    args = parser.parse_args()
    
    db_path = args.db if args.db else get_garnier_db_path()
    
    if not os.path.exists(db_path):
        print(f"❌ Erreur: La base de données '{db_path}' n'existe pas")
        sys.exit(1)
    
    check_duplicates(db_path)

