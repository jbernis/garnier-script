#!/usr/bin/env python3
"""
Script pour générer le CSV Shopify depuis la base de données Cristel.
"""

import sys
import os
import argparse
import logging
import pandas as pd
from datetime import datetime
from urllib.parse import urljoin

# Ajouter le répertoire parent au path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.cristel_db import CristelDB
from utils.app_config import get_cristel_db_path
from csv_config import get_csv_config

# Importer slugify du scraper existant
import importlib.util
scraper_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "scraper-cristel.py")
spec = importlib.util.spec_from_file_location("scraper_cristel", scraper_path)
scraper_module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(scraper_module)
slugify = scraper_module.slugify

# Configuration du logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

BASE_URL = os.getenv("CRISTEL_BASE_URL", "https://www.cristel.fr")
OUTPUT_DIR = os.getenv("CRISTEL_OUTPUT_DIR", "outputs/cristel")


def generate_csv_from_db(output_file=None, output_db='cristel_products.db', 
                         supplier='cristel', categories=None, subcategory=None):
    """
    Génère le CSV Shopify depuis la base de données Cristel.
    
    Args:
        output_file: Chemin du fichier CSV de sortie (None = auto)
        output_db: Chemin vers la base de données SQLite
        supplier: Nom du fournisseur pour la configuration CSV
        categories: Liste de catégories à inclure (None = toutes)
        subcategory: Nom de la sous-catégorie à filtrer (None = toutes)
    """
    db = CristelDB(output_db)
    
    try:
        # Récupérer la configuration CSV
        csv_config_manager = get_csv_config()
        shopify_columns = csv_config_manager.get_columns(supplier)
        handle_source = csv_config_manager.get_handle_source(supplier)
        vendor_name = csv_config_manager.get_vendor(supplier)
        
        # Récupérer les produits avec leurs variants complétés
        products = db.get_completed_products(categories=categories, subcategory=subcategory)
        
        if categories:
            logger.info(f"Filtrage par catégorie(s): {', '.join(categories)}")
        if subcategory:
            logger.info(f"Filtrage par sous-catégorie: {subcategory}")
        
        if not products:
            logger.warning("Aucun produit complété trouvé dans la base de données")
            return
        
        logger.info(f"Génération du CSV pour {len(products)} produit(s)...")
        
        rows = []
        
        # Parcourir chaque produit
        for product in products:
            product_id = product['id']
            product_code = product['product_code']
            handle = product['handle']
            title = product['title'] or f"Produit {product_code}"
            description = product['description'] or ''
            category = product['category'] or ''
            product_subcategory = product['subcategory'] or ''
            
            # Récupérer tous les variants complétés
            variants = db.get_product_variants(product_id)
            completed_variants = [v for v in variants if v['status'] == 'completed']
            
            if not completed_variants:
                logger.warning(f"Produit {product_code}: aucun variant complété, ignoré")
                continue
            
            # Récupérer les images
            images = db.get_product_images(product_id)
            image_urls = [img['image_url'] for img in images]
            
            # Générer le Handle selon la configuration
            if handle_source == 'barcode':
                first_barcode = None
                for variant in completed_variants:
                    barcode = variant.get('gencode', '')
                    if barcode and str(barcode).strip():
                        first_barcode = str(barcode).strip()
                        break
                
                if first_barcode:
                    handle = first_barcode
                else:
                    logger.error(f"❌ Aucun barcode valide pour le produit {product_code}")
                    handle = f"ERROR_NO_BARCODE_{product_code}"
            elif handle_source == 'sku':
                first_sku = completed_variants[0].get('sku', '') if completed_variants else ''
                handle = first_sku or product_code
            elif handle_source == 'title':
                handle = slugify(title)
            else:
                handle = product_code
            
            # Formater le titre et vendor
            formatted_title = title[0].upper() + title[1:].lower() if len(title) > 1 else title.upper()
            formatted_vendor = vendor_name.upper().replace('-', ' ') if vendor_name else ''
            
            # Récupérer le statut is_new
            is_new = product.get('is_new', 0)
            published_value = 'FALSE' if is_new else 'TRUE'
            
            # Créer une ligne CSV par variant
            for variant in completed_variants:
                variant_sku = variant.get('sku') or variant['code_vl']
                variant_gencode = variant.get('gencode') or ''
                variant_price_pvc = variant.get('price_pvc') or ''
                variant_price_pa = variant.get('price_pa') or ''
                variant_stock = variant.get('stock') or 0
                variant_size = variant.get('size') or variant.get('size_text') or ''
                variant_color = variant.get('color') or ''
                variant_material = variant.get('material') or ''
                
                # Construire les tags
                tags_list = []
                if category:
                    tags_list.append(category)
                if product_subcategory:
                    tags_list.append(product_subcategory)
                tags = ', '.join(tags_list)
                
                # Créer la ligne de base
                base_row = {
                    'Handle': handle,
                    'Title': formatted_title,
                    'Body (HTML)': description,
                    'Vendor': formatted_vendor,
                    'Type': category,
                    'Tags': tags,
                    'Published': published_value,
                    'Option1 Name': 'Taille' if variant_size else '',
                    'Option1 Value': variant_size,
                    'Option2 Name': 'Couleur' if variant_color else '',
                    'Option2 Value': variant_color,
                    'Option3 Name': 'Matière' if variant_material else '',
                    'Option3 Value': variant_material,
                    'Variant SKU': variant_sku,
                    'Variant Grams': '',
                    'Variant Inventory Tracker': 'shopify',
                    'Variant Inventory Policy': 'deny',
                    'Variant Fulfillment Service': 'manual',
                    'Variant Price': variant_price_pvc,
                    'Variant Compare At Price': variant_price_pa,
                    'Variant Requires Shipping': 'TRUE',
                    'Variant Taxable': 'TRUE',
                    'Variant Barcode': variant_gencode,
                    'Image Src': '',
                    'Image Position': '',
                    'Image Alt Text': '',
                    'Gift Card': 'FALSE',
                    'SEO Title': '',
                    'SEO Description': '',
                    'Google Shopping / Google Product Category': '',
                    'Google Shopping / Gender': '',
                    'Google Shopping / Age Group': '',
                    'Google Shopping / MPN': '',
                    'Google Shopping / AdWords Grouping': '',
                    'Google Shopping / AdWords Labels': '',
                    'Google Shopping / Condition': '',
                    'Google Shopping / Custom Product': '',
                    'Google Shopping / Custom Label 0': '',
                    'Google Shopping / Custom Label 1': '',
                    'Google Shopping / Custom Label 2': '',
                    'Google Shopping / Custom Label 3': '',
                    'Google Shopping / Custom Label 4': '',
                    'Variant Image': '',
                    'Variant Weight Unit': 'kg',
                    'Variant Tax Code': '',
                    'Cost per item': '',
                    'Price / International': '',
                    'Compare At Price / International': '',
                    'Status': 'active',
                    'On hand (new)': str(variant_stock),
                    'Variant Inventory Qty': str(variant_stock),
                }
                
                # Ajouter une ligne pour le variant sans image
                rows.append(base_row.copy())
                
                # Ajouter une ligne par image
                if image_urls:
                    for img_idx, image_url in enumerate(image_urls, 1):
                        image_row = base_row.copy()
                        image_row['Image Src'] = image_url
                        image_row['Image Position'] = str(img_idx)
                        image_row['Image Alt Text'] = formatted_title
                        rows.append(image_row)
        
        # Créer le DataFrame
        df = pd.DataFrame(rows)
        
        # Filtrer les colonnes selon la configuration
        available_columns = [col for col in shopify_columns if col in df.columns]
        df = df[available_columns]
        
        # Générer le nom du fichier si non spécifié
        if output_file is None:
            os.makedirs(OUTPUT_DIR, exist_ok=True)
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            
            # Inclure la sous-catégorie dans le nom du fichier si spécifiée
            if subcategory:
                subcategory_slug = slugify(subcategory)
                filename = f"shopify_import_cristel_{subcategory_slug}_{timestamp}.csv"
            elif categories and len(categories) == 1:
                category_slug = slugify(categories[0])
                filename = f"shopify_import_cristel_{category_slug}_{timestamp}.csv"
            else:
                filename = f"shopify_import_cristel_{timestamp}.csv"
            
            output_file = os.path.join(OUTPUT_DIR, filename)
        
        # Sauvegarder le CSV
        df.to_csv(output_file, index=False, encoding='utf-8-sig')
        logger.info(f"\n{'='*60}")
        logger.info(f"✓ CSV généré avec succès: {output_file}")
        logger.info(f"  Produits: {len(products)}")
        logger.info(f"  Lignes CSV: {len(df)}")
        logger.info(f"{'='*60}")
        
    finally:
        db.close()


if __name__ == '__main__':
    parser = argparse.ArgumentParser(
        description='Génère le CSV Shopify depuis la base de données Cristel'
    )
    parser.add_argument(
        '--output', '-o',
        help='Chemin du fichier CSV de sortie (défaut: auto-généré)'
    )
    parser.add_argument(
        '--db', '-d',
        default=None,
        help='Chemin vers la base de données SQLite (défaut: cristel_products.db)'
    )
    parser.add_argument(
        '--supplier',
        default='cristel',
        help='Nom du fournisseur pour la configuration CSV (défaut: cristel)'
    )
    parser.add_argument(
        '--category', '-c',
        action='append',
        help='Catégorie(s) à inclure (peut être répété plusieurs fois)'
    )
    parser.add_argument(
        '--subcategory', '-s',
        help='Sous-catégorie à filtrer'
    )
    parser.add_argument(
        '--list-categories',
        action='store_true',
        help='Lister les catégories disponibles'
    )
    
    args = parser.parse_args()
    
    # Utiliser la DB par défaut si non spécifiée
    if args.db is None:
        output_db = get_cristel_db_path()
        logger.info(f"Utilisation de la base de données: {output_db}")
    else:
        output_db = args.db
    
    # Lister les catégories si demandé
    if args.list_categories:
        db = CristelDB(output_db)
        categories = db.get_available_categories()
        logger.info(f"\nCatégories disponibles ({len(categories)}):")
        for cat in categories:
            logger.info(f"  - {cat}")
        db.close()
        sys.exit(0)
    
    generate_csv_from_db(
        output_file=args.output,
        output_db=output_db,
        supplier=args.supplier,
        categories=args.category,
        subcategory=args.subcategory
    )
    
    logger.info("Script terminé avec succès")
