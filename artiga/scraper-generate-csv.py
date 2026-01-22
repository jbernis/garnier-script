#!/usr/bin/env python3
"""
Script pour générer le CSV Shopify depuis la base de données Artiga.
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

from utils.artiga_db import ArtigaDB
from utils.app_config import get_artiga_db_path
from csv_config import get_csv_config

# Importer slugify du scraper existant
import importlib.util
scraper_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "scraper-artiga.py")
spec = importlib.util.spec_from_file_location("scraper_artiga", scraper_path)
scraper_module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(scraper_module)
slugify = scraper_module.slugify

# Configuration du logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

BASE_URL = os.getenv("ARTIGA_BASE_URL", "https://www.artiga.fr")
OUTPUT_DIR = os.getenv("ARTIGA_OUTPUT_DIR", "outputs/artiga")


def generate_csv_from_db(output_file=None, output_db='artiga_products.db', 
                         supplier='artiga', categories=None, subcategory=None, max_images=None):
    """
    Génère le CSV Shopify depuis la base de données Artiga.
    
    Args:
        output_file: Chemin du fichier CSV de sortie (None = auto)
        output_db: Chemin vers la base de données SQLite
        supplier: Nom du fournisseur pour la configuration CSV
        categories: Liste de catégories à inclure (None = toutes)
        subcategory: Nom de la sous-catégorie à filtrer (None = toutes)
    """
    # Charger la configuration CSV
    csv_config = get_csv_config()  # SANS argument - retourne un objet CSVConfig
    if not csv_config:
        logger.error(f"Configuration CSV non trouvée")
        return None
    
    configured_columns = csv_config.get_columns(supplier)  # Méthode de l'objet
    vendor_name = csv_config.get_vendor(supplier)  # Méthode de l'objet
    
    db = ArtigaDB(output_db)
    
    try:
        # Récupérer la configuration CSV
        csv_config_manager = get_csv_config()
        shopify_columns = csv_config_manager.get_columns(supplier)
        handle_source = csv_config_manager.get_handle_source(supplier)
        vendor_name = csv_config_manager.get_vendor(supplier)
        location_name = csv_config_manager.get_location(supplier)
        
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
            
            # Limiter le nombre d'images si max_images est spécifié
            if max_images and len(image_urls) > max_images:
                logger.info(f"Limitation des images pour {product_code}: {len(image_urls)} → {max_images}")
                image_urls = image_urls[:max_images]
            
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
            
            # Pour Artiga, is_new n'existe pas, toujours publier
            published_value = 'TRUE'
            
            # Créer une ligne CSV par variant
            for variant_idx, variant in enumerate(completed_variants):
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
                
                # Créer une ligne vide avec toutes les colonnes configurées
                base_row = {col: '' for col in configured_columns}
                
                # Remplir les champs de base (première ligne du produit/variant)
                base_row['Handle'] = handle
                base_row['Title'] = formatted_title
                base_row['Body (HTML)'] = description
                base_row['Vendor'] = formatted_vendor
                base_row['Product Category'] = ''
                base_row['Type'] = category
                base_row['Tags'] = tags
                base_row['Published'] = published_value
                base_row['Option1 Name'] = 'Taille' if variant_size else ''
                base_row['Option1 Value'] = variant_size
                base_row['Option2 Name'] = 'Couleur' if variant_color else ''
                base_row['Option2 Value'] = variant_color
                base_row['Option3 Name'] = 'Matière' if variant_material else ''
                base_row['Option3 Value'] = variant_material
                base_row['Variant SKU'] = variant_sku
                base_row['Variant Grams'] = ''
                base_row['Variant Inventory Tracker'] = 'shopify'
                base_row['Variant Inventory Qty'] = str(variant_stock)
                base_row['Variant Inventory Policy'] = 'deny'
                base_row['Variant Fulfillment Service'] = 'manual'
                base_row['Variant Price'] = variant_price_pvc  # LE PRIX VA ICI
                base_row['Variant Compare At Price'] = variant_price_pa if variant_price_pa else ''
                base_row['Variant Requires Shipping'] = 'TRUE'
                base_row['Variant Taxable'] = 'TRUE'
                base_row['Variant Barcode'] = variant_gencode
                base_row['Gift Card'] = 'FALSE'
                base_row['SEO Title'] = ''
                base_row['SEO Description'] = ''
                base_row['Google Shopping / Google Product Category'] = ''
                base_row['Google Shopping / Gender'] = ''
                base_row['Google Shopping / Age Group'] = ''
                base_row['Google Shopping / MPN'] = ''
                base_row['Google Shopping / Condition'] = ''
                base_row['Google Shopping / Custom Product'] = ''
                base_row['Variant Image'] = ''
                base_row['Variant Weight Unit'] = 'kg'
                base_row['Variant Tax Code'] = ''
                base_row['Cost per item'] = ''
                base_row['Included / United States'] = ''
                base_row['Price / United States'] = ''
                base_row['Compare At Price / United States'] = ''
                base_row['Included / International'] = ''
                base_row['Price / International'] = ''
                base_row['Compare At Price / International'] = ''
                base_row['Status'] = 'active'
                base_row['location'] = location_name  # Emplacement Shopify
                base_row['On hand (new)'] = str(variant_stock)  # Stock (quantité disponible)
                base_row['On hand (current)'] = ''  # Champ vide
                
                # Pour le premier variant seulement, ajouter les images
                if variant_idx == 0:
                    if not image_urls:
                        # Si pas d'images, créer une seule ligne sans images
                        rows.append(base_row.copy())
                    else:
                        # Créer une ligne par image pour le premier variant
                        for img_idx, image_url in enumerate(image_urls, start=1):
                            row = base_row.copy()
                            
                            if img_idx == 1:
                                # Première image : garder toutes les infos produit et variant (déjà dans base_row)
                                pass
                            else:
                                # Images suivantes : Vider TOUS les champs sauf Handle, Image Src, Image Position, Image Alt Text
                                # Shopify associe les images au produit via le Handle uniquement
                                for col in configured_columns:
                                    if col not in ['Handle', 'Image Src', 'Image Position', 'Image Alt Text']:
                                        row[col] = ''
                            
                            # Ajouter les informations de l'image
                            row['Image Src'] = image_url
                            row['Image Position'] = img_idx
                            row['Image Alt Text'] = formatted_title
                            
                            rows.append(row)
                else:
                    # Pour les autres variants, créer une seule ligne sans images (les images sont déjà définies)
                    rows.append(base_row.copy())
        
        # Créer le DataFrame
        df = pd.DataFrame(rows)
        
        # Filtrer les colonnes selon la configuration
        available_columns = [col for col in shopify_columns if col in df.columns]
        df = df[available_columns]
        
        # Générer le nom du fichier si non spécifié
        if output_file is None:
            os.makedirs(OUTPUT_DIR, exist_ok=True)
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            
            # Inclure la catégorie et/ou sous-catégorie dans le nom du fichier
            # Si une sous-catégorie est fournie, extraire aussi la catégorie du premier produit
            if subcategory and products:
                first_product_category = products[0].get('category', '')
                if first_product_category:
                    logger.info(f"Construction du nom avec catégorie-sous-catégorie: {first_product_category} - {subcategory}")
                    category_slug = slugify(first_product_category)
                    subcategory_slug = slugify(subcategory)
                    filename = f"shopify_import_artiga_{category_slug}-{subcategory_slug}_{timestamp}.csv"
                else:
                    logger.info(f"Construction du nom avec sous-catégorie: {subcategory}")
                    subcategory_slug = slugify(subcategory)
                    filename = f"shopify_import_artiga_{subcategory_slug}_{timestamp}.csv"
            elif categories and len(categories) == 1:
                logger.info(f"Construction du nom avec catégorie: {categories[0]}")
                category_slug = slugify(categories[0])
                filename = f"shopify_import_artiga_{category_slug}_{timestamp}.csv"
            else:
                logger.info("Construction du nom générique (toutes les catégories)")
                filename = f"shopify_import_artiga_{timestamp}.csv"
            
            output_file = os.path.join(OUTPUT_DIR, filename)
        
        # Vérifier s'il y a des erreurs dans les produits/variants
        stats = db.get_stats()
        error_variants_count = stats.get('variants_by_status', {}).get('error', 0)
        error_products_count = sum(1 for p in products if p.get('status') == 'error')
        
        # Sauvegarder le CSV
        df.to_csv(output_file, index=False, encoding='utf-8-sig')
        logger.info(f"\n{'='*60}")
        logger.info(f"✓ CSV généré avec succès: {output_file}")
        logger.info(f"  Produits: {len(products)}")
        logger.info(f"  Lignes CSV: {len(df)}")
        
        # Avertir si des erreurs sont présentes
        if error_variants_count > 0 or error_products_count > 0:
            logger.warning(f"\n⚠️  ATTENTION: Le fichier CSV comporte des erreurs:")
            if error_variants_count > 0:
                logger.warning(f"   • {error_variants_count} variant(s) en erreur (non inclus dans le CSV)")
            if error_products_count > 0:
                logger.warning(f"   • {error_products_count} produit(s) en erreur")
            logger.warning(f"   Vérifiez les logs de collecte pour plus de détails.")
        else:
            logger.info(f"  ✓ Aucune erreur détectée")
        
        logger.info(f"{'='*60}")
        
        return output_file  # Retourner le chemin du fichier généré
        
    finally:
        db.close()


if __name__ == '__main__':
    parser = argparse.ArgumentParser(
        description='Génère le CSV Shopify depuis la base de données Artiga'
    )
    parser.add_argument(
        '--output', '-o',
        help='Chemin du fichier CSV de sortie (défaut: auto-généré)'
    )
    parser.add_argument(
        '--db', '-d',
        default=None,
        help='Chemin vers la base de données SQLite (défaut: artiga_products.db)'
    )
    parser.add_argument(
        '--supplier',
        default='artiga',
        help='Nom du fournisseur pour la configuration CSV (défaut: artiga)'
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
        output_db = get_artiga_db_path()
        logger.info(f"Utilisation de la base de données: {output_db}")
    else:
        output_db = args.db
    
    # Lister les catégories si demandé
    if args.list_categories:
        db = ArtigaDB(output_db)
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
