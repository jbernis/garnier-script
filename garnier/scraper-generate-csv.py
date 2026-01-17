#!/usr/bin/env python3
"""
Script pour générer le CSV Shopify depuis la base de données.
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

from utils.garnier_db import GarnierDB
from utils.app_config import get_garnier_db_path
from csv_config import get_csv_config
from garnier.scraper_garnier_module import slugify

# Configuration du logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

BASE_URL = os.getenv("BASE_URL_GARNIER", "https://garnier-thiebaut.adsi.me")
# Répertoire de sortie automatique (peut être surchargé avec GARNIER_OUTPUT_DIR)
OUTPUT_DIR = os.getenv("GARNIER_OUTPUT_DIR", "outputs/garnier")


def generate_csv_from_db(output_file=None, output_db='garnier_products.db', 
                         supplier='garnier', categories=None, gamme=None):
    """
    Génère le CSV Shopify depuis la base de données.
    
    Args:
        output_file: Chemin du fichier CSV de sortie (None = auto)
        output_db: Chemin vers la base de données SQLite
        supplier: Nom du fournisseur pour la configuration CSV
        categories: Liste de catégories à inclure (None = toutes)
        gamme: Nom de la gamme à filtrer (None = toutes les gammes)
    """
    db = GarnierDB(output_db)
    
    try:
        # Récupérer la configuration CSV
        csv_config_manager = get_csv_config()
        shopify_columns = csv_config_manager.get_columns(supplier)
        handle_source = csv_config_manager.get_handle_source(supplier)
        vendor_name = csv_config_manager.get_vendor(supplier)
        
        # Récupérer les produits avec leurs variants complétés (filtrés par catégorie/gamme si spécifié)
        products = db.get_completed_products(categories=categories, gamme=gamme)
        
        if categories:
            logger.info(f"Filtrage par catégorie(s): {', '.join(categories)}")
        if gamme:
            logger.info(f"Filtrage par gamme: {gamme}")
        
        if not products:
            logger.warning("Aucun produit complété trouvé dans la base de données")
            if categories:
                logger.warning(f"  Filtré par catégorie(s): {', '.join(categories)}")
            if gamme:
                logger.warning(f"  Filtré par gamme: {gamme}")
            logger.warning("  Vérifiez que les variants ont été collectés et traités (status='completed')")
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
            product_gamme = product['gamme'] or ''
            
            # Récupérer tous les variants complétés de ce produit
            variants = db.get_product_variants(product_id)
            completed_variants = [v for v in variants if v['status'] == 'completed']
            
            if not completed_variants:
                logger.warning(f"Produit {product_code}: aucun variant complété, ignoré")
                continue
            
            # Récupérer les images
            images = db.get_product_images(product_id)
            image_urls = [img['image_url'] for img in images]
            
            # Si pas d'images dans la DB, essayer de les extraire depuis le produit
            if not image_urls:
                # Les images devraient être collectées lors de la collecte
                # Pour l'instant, on continue sans images
                pass
            
            # Générer le Handle selon la configuration
            if handle_source == 'barcode':
                # Utiliser le barcode du premier variant qui en a un
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
                # Utiliser le SKU du premier variant
                first_sku = completed_variants[0].get('sku', '') if completed_variants else ''
                handle = first_sku or product_code
            elif handle_source == 'title':
                handle = slugify(title)
            else:
                handle = product_code
            
            # Formater le titre et vendor
            formatted_title = title[0].upper() + title[1:].lower() if len(title) > 1 else title.upper()
            formatted_vendor = vendor_name.upper().replace('-', ' ') if vendor_name else ''
            
            # Récupérer le statut is_new du produit (0 ou 1 depuis SQLite)
            is_new = product.get('is_new', 0)  # 0 par défaut si non défini
            published_value = 'FALSE' if is_new else 'TRUE'  # FALSE si is_new, sinon TRUE
            
            # Créer une ligne CSV par variant (SANS supprimer les doublons)
            for variant in completed_variants:
                variant_sku = variant.get('sku') or variant['code_vl']
                variant_gencode = variant.get('gencode') or ''
                variant_price_pvc = variant.get('price_pvc') or ''
                variant_price_pa = variant.get('price_pa') or ''
                variant_stock = variant.get('stock') or 0
                variant_size = variant.get('size') or variant.get('size_text') or ''
                variant_color = variant.get('color') or ''
                variant_material = variant.get('material') or ''
                
                # Créer la ligne de base avec tous les champs Shopify
                # Construire les tags avec catégorie et gamme si disponible
                tags_list = []
                if category:
                    tags_list.append(category)
                if product_gamme:
                    tags_list.append(product_gamme)
                tags_value = ', '.join(tags_list) if tags_list else category
                
                base_row = {
                    'Handle': handle or '',
                    'Title': formatted_title,
                    'Body (HTML)': description or '',
                    'Vendor': formatted_vendor,
                    'Product Category': product_gamme if product_gamme else '',  # Utiliser la gamme pour Product Category si disponible
                    'Type': category,
                    'Tags': tags_value,  # Tags avec catégorie et gamme
                    'Published': published_value,  # FALSE si is_new, sinon TRUE
                    'Option1 Name': 'Taille' if variant_size else '',
                    'Option1 Value': variant_size,
                    'Option2 Name': '',
                    'Option2 Value': '',
                    'Option3 Name': '',
                    'Option3 Value': '',
                    'Variant SKU': variant_sku or '',
                    'Variant Grams': '',
                    'Variant Inventory Tracker': 'shopify',
                    'Variant Inventory Qty': '',
                    'Variant Inventory Policy': 'deny',
                    'Variant Fulfillment Service': 'manual',
                    'Variant Price': variant_price_pvc,
                    'Variant Compare At Price': variant_price_pa,
                    'Variant Requires Shipping': 'TRUE',
                    'Variant Taxable': 'TRUE',
                    'Variant Barcode': variant_gencode or '',
                    'Variant Image': '',
                    'Variant Weight Unit': 'kg',
                    'Variant Tax Code': '',
                    'Cost per item': '',
                    # Champs Shopify standard ajoutés pour s'assurer qu'ils sont toujours présents
                    'Gift Card': 'FALSE',
                    'SEO Title': '',
                    'SEO Description': '',
                    'Google Shopping / Google Product Category': '',
                    'Google Shopping / Gender': '',
                    'Google Shopping / Age Group': '',
                    'Google Shopping / MPN': '',
                    'Google Shopping / Condition': '',
                    'Google Shopping / Custom Product': '',
                    'Included / United States': '',
                    'Price / United States': '',
                    'Compare At Price / United States': '',
                    'Included / International': '',
                    'Price / International': '',
                    'Compare At Price / International': '',
                    'Status': 'active',
                    'location': 'Dropshipping Garnier Thiebaut',
                    'On hand (new)': variant_stock,
                    'On hand (current)': '',
                }
                
                # Toujours ajouter les colonnes d'images (même si vides) pour compatibilité Shopify
                base_row['Image Src'] = ''
                base_row['Image Position'] = ''
                base_row['Image Alt Text'] = ''
                
                # Ajouter les colonnes optionnelles selon la configuration
                if 'Option2 Name' in shopify_columns and variant_color:
                    base_row['Option2 Name'] = 'Couleur'
                    base_row['Option2 Value'] = variant_color
                
                if 'Option3 Name' in shopify_columns and variant_material:
                    base_row['Option3 Name'] = 'Matière'
                    base_row['Option3 Value'] = variant_material
                
                # Créer une ligne par image
                if image_urls:
                    for img_idx, image_url in enumerate(image_urls, 1):
                        row = base_row.copy()
                        row['Image Src'] = image_url
                        row['Image Position'] = img_idx
                        row['Image Alt Text'] = title
                        rows.append(row)
                else:
                    # Pas d'images, une seule ligne
                    rows.append(base_row)
        
        if not rows:
            logger.warning("Aucune ligne générée")
            return
        
        # Créer le DataFrame
        df = pd.DataFrame(rows)
        
        # Filtrer les colonnes selon la configuration
        if shopify_columns:
            # Ne garder QUE les colonnes sélectionnées dans l'ordre
            final_columns_order = [col for col in shopify_columns if col in df.columns]
            df = df[final_columns_order]
            logger.info(f"Colonnes filtrées: {len(final_columns_order)} colonnes retenues sur {len(shopify_columns)} demandées")
        
        # Déterminer le nom du fichier de sortie
        if not output_file:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            from garnier.scraper_garnier_module import slugify
            
            # Construire le nom du fichier avec catégorie et/ou gamme
            name_parts = []
            
            # Si une gamme est spécifiée en paramètre, l'inclure en priorité
            if gamme:
                gamme_slug = slugify(gamme)
                name_parts.append(gamme_slug)
            else:
                # Sinon, détecter automatiquement les gammes présentes dans les produits exportés
                import re
                unique_gammes = set()
                for product in products:
                    product_gamme = product.get('gamme')
                    if product_gamme and product_gamme.strip():
                        # Nettoyer la gamme (enlever les parties malformées)
                        cleaned_gamme = product_gamme.strip()
                        original_gamme = cleaned_gamme  # Pour debug
                        
                        # Format typique: "33545 - HOUSSE DE COUETTE AVA UNI LINPA 107,10 €"
                        # Étape 1: Enlever le code numérique au début
                        cleaned_gamme = re.sub(r'^\d+\s*-\s*', '', cleaned_gamme)
                        
                        # Étape 2: Enlever les types de produits courants
                        product_types = [
                            'HOUSSE DE COUETTE', 'LOT H\\.COUETTE \\+TAIES', 'LOT DE 2 TAIES',
                            'TAIE D\'OREILLER', r'DRAP HOUSSE B\d+', 'TORCHON', 'CHEMIN DE TABLE',
                            'NAPPE', 'SERVIETTE', 'SET DE TABLE'
                        ]
                        for ptype in product_types:
                            cleaned_gamme = re.sub(rf'\b{ptype}\b', '', cleaned_gamme, flags=re.IGNORECASE).strip()
                        
                        # Étape 3: Enlever les suffixes de prix (NR/new)PA (avec ou sans chiffres/€)
                        # Match : "newPA", "NRPA", "PA 123,45 €", etc.
                        cleaned_gamme = re.sub(r'(NR|new)?PA(\s*[\d,.\s€]+)?$', '', cleaned_gamme).strip()
                        
                        # Étape 4: Enlever les espaces multiples
                        cleaned_gamme = re.sub(r'\s+', ' ', cleaned_gamme).strip()
                        
                        # Debug: afficher le nettoyage
                        logger.debug(f"Gamme originale: '{original_gamme}' -> nettoyée: '{cleaned_gamme}'")
                        
                        # Étape 5: Si quelque chose reste et ce n'est pas juste des chiffres, c'est la gamme
                        if cleaned_gamme and not re.match(r'^\d+$', cleaned_gamme) and len(cleaned_gamme) > 2:
                            unique_gammes.add(cleaned_gamme)
                
                logger.info(f"Gammes uniques détectées: {unique_gammes}")
                
                # Si une seule gamme détectée, l'ajouter au nom
                if len(unique_gammes) == 1:
                    gamme_slug = slugify(list(unique_gammes)[0])
                    name_parts.append(gamme_slug)
                    logger.info(f"Une seule gamme détectée, ajout au nom: '{gamme_slug}'")
            
            # Ajouter les catégories si spécifiées
            if categories and len(categories) > 0:
                category_slugs = [slugify(cat) for cat in categories]
                # Si on a déjà une gamme, ajouter les catégories après
                if name_parts:
                    name_parts.extend(category_slugs)
                else:
                    name_parts = category_slugs
            
            # Construire le nom final
            if name_parts:
                name_str = '_'.join(name_parts)
                output_file = os.path.join(OUTPUT_DIR, f"shopify_import_garnier_{name_str}_{timestamp}.csv")
            else:
                output_file = os.path.join(OUTPUT_DIR, f"shopify_import_garnier_{timestamp}.csv")
        
        # Créer le répertoire si nécessaire
        output_dir = os.path.dirname(output_file)
        if output_dir and not os.path.exists(output_dir):
            os.makedirs(output_dir, exist_ok=True)
        
        # Sauvegarder le CSV
        df.to_csv(output_file, index=False, encoding='utf-8')
        logger.info(f"\n{'='*60}")
        logger.info("CSV généré avec succès!")
        logger.info(f"Fichier: {output_file}")
        logger.info(f"Produits: {len(products)}")
        logger.info(f"Variants: {len([v for p in products for v in db.get_product_variants(p['id']) if v['status'] == 'completed'])}")
        logger.info(f"Lignes CSV: {len(df)}")
        logger.info(f"{'='*60}")
        
    finally:
        db.close()


if __name__ == '__main__':
    parser = argparse.ArgumentParser(
        description='Génère le CSV Shopify depuis la base de données'
    )
    parser.add_argument(
        '--output', '-o',
        help='Chemin du fichier CSV de sortie (défaut: auto-généré)'
    )
    # Lire la configuration pour la valeur par défaut
    default_db = get_garnier_db_path()
    
    parser.add_argument(
        '--db', '-d',
        default=default_db,
        help=f'Chemin vers la base de données SQLite (défaut: {default_db})'
    )
    parser.add_argument(
        '--supplier', '-s',
        default='garnier',
        help='Nom du fournisseur pour la configuration CSV (défaut: garnier)'
    )
    parser.add_argument(
        '--category', '-c',
        action='append',
        help='Catégorie(s) à inclure dans le CSV (peut être répété plusieurs fois). Si non spécifié, toutes les catégories sont incluses.'
    )
    parser.add_argument(
        '--gamme', '-g',
        help='Nom de la gamme à filtrer dans le CSV. Si non spécifié, toutes les gammes sont incluses.'
    )
    parser.add_argument(
        '--list-categories', '-l',
        action='store_true',
        help='Affiche la liste des catégories disponibles dans la base de données et quitte'
    )
    
    args = parser.parse_args()
    
    # Si list-categories, afficher et quitter
    if args.list_categories:
        db = GarnierDB(args.db)
        try:
            categories = db.get_available_categories()
            if categories:
                logger.info(f"\n{'='*60}")
                logger.info("Catégories disponibles dans la base de données:")
                logger.info(f"{'='*60}")
                for cat in categories:
                    logger.info(f"  - {cat}")
                logger.info(f"{'='*60}")
                logger.info(f"Total: {len(categories)} catégorie(s)")
            else:
                logger.warning("Aucune catégorie trouvée dans la base de données")
        finally:
            db.close()
    else:
        generate_csv_from_db(
            output_file=args.output,
            output_db=args.db,
            supplier=args.supplier,
            categories=args.category,
            gamme=args.gamme
        )

