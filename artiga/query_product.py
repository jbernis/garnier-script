#!/usr/bin/env python3
"""
Script pour afficher toutes les informations d'un produit Artiga spécifique.
"""

import sys
import os
import sqlite3
import argparse

# Ajouter le répertoire parent au path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.app_config import get_artiga_db_path


def get_product_info(product_code):
    """Récupère toutes les informations d'un produit."""
    db_path = get_artiga_db_path()
    
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    print("=" * 80)
    print(f"🔍 RECHERCHE DU PRODUIT ARTIGA: {product_code}")
    print("=" * 80)
    
    # 1. Informations du produit
    cursor.execute('''
        SELECT * FROM products WHERE product_code = ?
    ''', (product_code,))
    
    product = cursor.fetchone()
    
    if not product:
        print(f"\n❌ Produit {product_code} non trouvé dans la base de données")
        conn.close()
        return
    
    print("\n📦 INFORMATIONS DU PRODUIT:")
    print("-" * 80)
    print(f"  ID: {product['id']}")
    print(f"  Code produit: {product['product_code']}")
    print(f"  Handle: {product['handle']}")
    print(f"  Titre: {product['title']}")
    print(f"  Description: {product['description'][:100] if product['description'] else 'N/A'}...")
    print(f"  Vendor: {product['vendor']}")
    print(f"  Type: {product['product_type']}")
    print(f"  Tags: {product['tags']}")
    print(f"  Catégorie: {product['category']}")
    print(f"  Sous-catégorie: {product['subcategory']}")
    print(f"  Base URL: {product['base_url']}")
    print(f"  Status: {product['status']}")
    print(f"  Error message: {product['error_message'] or 'N/A'}")
    print(f"  Retry count: {product['retry_count']}")
    print(f"  Is new: {'Oui' if product['is_new'] else 'Non'}")
    print(f"  Créé le: {product['created_at']}")
    print(f"  Mis à jour le: {product['updated_at']}")
    
    # 2. Statistiques des variants
    cursor.execute('''
        SELECT 
            COUNT(*) as total,
            SUM(CASE WHEN status = 'completed' THEN 1 ELSE 0 END) as completed,
            SUM(CASE WHEN status = 'pending' THEN 1 ELSE 0 END) as pending,
            SUM(CASE WHEN status = 'error' THEN 1 ELSE 0 END) as error
        FROM product_variants
        WHERE product_id = ?
    ''', (product['id'],))
    
    stats = cursor.fetchone()
    
    print("\n📊 STATISTIQUES DES VARIANTS:")
    print("-" * 80)
    print(f"  Total: {stats['total']}")
    print(f"  Complétés: {stats['completed']}")
    print(f"  En attente: {stats['pending']}")
    print(f"  En erreur: {stats['error']}")
    
    # 3. Liste des variants
    cursor.execute('''
        SELECT 
            id, code_vl, url, size_text, size, color, material,
            sku, gencode, price_pa, price_pvc, stock,
            status, error_message, created_at, updated_at
        FROM product_variants
        WHERE product_id = ?
        ORDER BY id
    ''', (product['id'],))
    
    variants = cursor.fetchall()
    
    if variants:
        print("\n🔹 VARIANTS:")
        print("-" * 80)
        for idx, variant in enumerate(variants, 1):
            status_icon = "✅" if variant['status'] == 'completed' else "❌" if variant['status'] == 'error' else "⏳"
            print(f"\n  {status_icon} Variant {idx} (ID: {variant['id']}):")
            print(f"    Code VL: {variant['code_vl']}")
            print(f"    URL: {variant['url']}")
            print(f"    Size text: {variant['size_text'] or 'N/A'}")
            print(f"    Size: {variant['size'] or 'N/A'}")
            print(f"    Color: {variant['color'] or 'N/A'}")
            print(f"    Material: {variant['material'] or 'N/A'}")
            print(f"    SKU: {variant['sku'] or 'N/A'}")
            print(f"    Gencode: {variant['gencode'] or 'N/A'}")
            print(f"    Prix PA: {variant['price_pa'] or 'N/A'}")
            print(f"    Prix PVC: {variant['price_pvc'] or 'N/A'}")
            print(f"    Stock: {variant['stock'] or 0}")
            print(f"    Status: {variant['status']}")
            if variant['error_message']:
                print(f"    ⚠️ Erreur: {variant['error_message']}")
            print(f"    Créé le: {variant['created_at']}")
            print(f"    Mis à jour le: {variant['updated_at']}")
    else:
        print("\n⚠️  Aucun variant trouvé pour ce produit")
    
    # 4. Liste des images
    cursor.execute('''
        SELECT id, image_url, image_position, created_at
        FROM product_images
        WHERE product_id = ?
        ORDER BY image_position
    ''', (product['id'],))
    
    images = cursor.fetchall()
    
    if images:
        print("\n🖼️  IMAGES:")
        print("-" * 80)
        for idx, image in enumerate(images, 1):
            print(f"  {idx}. {image['image_url']}")
    else:
        print("\n⚠️  Aucune image trouvée pour ce produit")
    
    print("\n" + "=" * 80)
    
    conn.close()


def show_stats():
    """Affiche les statistiques globales de la base de données."""
    db_path = get_artiga_db_path()
    
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    print("=" * 80)
    print("📊 STATISTIQUES GLOBALES - ARTIGA")
    print("=" * 80)
    
    # Produits
    cursor.execute('SELECT COUNT(*) as total FROM products')
    total_products = cursor.fetchone()['total']
    
    cursor.execute('''
        SELECT status, COUNT(*) as count 
        FROM products 
        GROUP BY status
    ''')
    products_by_status = cursor.fetchall()
    
    print("\n📦 PRODUITS:")
    print("-" * 80)
    print(f"  Total: {total_products}")
    for row in products_by_status:
        print(f"  {row['status']}: {row['count']}")
    
    # Produits retriables
    cursor.execute('''
        SELECT COUNT(*) as count 
        FROM products 
        WHERE status = 'error' AND retry_count < 3
    ''')
    retriable = cursor.fetchone()['count']
    print(f"  Erreurs retriables (retry_count < 3): {retriable}")
    
    # Variants
    cursor.execute('SELECT COUNT(*) as total FROM product_variants')
    total_variants = cursor.fetchone()['total']
    
    cursor.execute('''
        SELECT status, COUNT(*) as count 
        FROM product_variants 
        GROUP BY status
    ''')
    variants_by_status = cursor.fetchall()
    
    print("\n🔹 VARIANTS:")
    print("-" * 80)
    print(f"  Total: {total_variants}")
    for row in variants_by_status:
        print(f"  {row['status']}: {row['count']}")
    
    # Catégories
    cursor.execute('''
        SELECT DISTINCT category 
        FROM products 
        WHERE category IS NOT NULL 
        ORDER BY category
    ''')
    categories = cursor.fetchall()
    
    print("\n📂 CATÉGORIES:")
    print("-" * 80)
    for cat in categories:
        print(f"  - {cat['category']}")
    
    # Sous-catégories
    cursor.execute('''
        SELECT DISTINCT subcategory 
        FROM products 
        WHERE subcategory IS NOT NULL 
        ORDER BY subcategory
    ''')
    subcategories = cursor.fetchall()
    
    print("\n📁 SOUS-CATÉGORIES:")
    print("-" * 80)
    for subcat in subcategories:
        print(f"  - {subcat['subcategory']}")
    
    print("\n" + "=" * 80)
    
    conn.close()


if __name__ == '__main__':
    parser = argparse.ArgumentParser(
        description='Affiche les informations d\'un produit Artiga ou les statistiques globales'
    )
    parser.add_argument(
        'product_code',
        nargs='?',
        help='Code du produit à afficher'
    )
    parser.add_argument(
        '--stats',
        action='store_true',
        help='Afficher les statistiques globales'
    )
    
    args = parser.parse_args()
    
    if args.stats:
        show_stats()
    elif args.product_code:
        get_product_info(args.product_code)
    else:
        parser.print_help()
