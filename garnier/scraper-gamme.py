#!/usr/bin/env python3
"""
Script pour extraire les produits et variantes d'une gamme spécifique Garnier-Thiebaut
en indiquant simplement l'URL de la gamme.
Utilise scraper-garnier-collect.py pour la collecte en base de données.
"""

import sys
import os
import argparse
import logging
from datetime import datetime
from urllib.parse import urlparse, unquote
from dotenv import load_dotenv

# Charger les variables d'environnement depuis .env
load_dotenv()

# Ajouter le répertoire parent au path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Importer la fonction de collecte depuis scraper-collect.py
import importlib.util
collect_path = os.path.join(os.path.dirname(__file__), "scraper-collect.py")
collect_spec = importlib.util.spec_from_file_location("scraper_garnier_collect", collect_path)
collect_module = importlib.util.module_from_spec(collect_spec)
collect_spec.loader.exec_module(collect_module)
collect_from_gamme_url = collect_module.collect_from_gamme_url

# Importer le traitement des variants depuis scraper-process.py
process_path = os.path.join(os.path.dirname(__file__), "scraper-process.py")
process_spec = importlib.util.spec_from_file_location("scraper_garnier_process", process_path)
process_module = importlib.util.module_from_spec(process_spec)
process_spec.loader.exec_module(process_module)
process_urls = process_module.process_urls

# Importer la génération CSV depuis scraper-generate-csv.py
generate_path = os.path.join(os.path.dirname(__file__), "scraper-generate-csv.py")
generate_spec = importlib.util.spec_from_file_location("scraper_garnier_generate_csv", generate_path)
generate_module = importlib.util.module_from_spec(generate_spec)
generate_spec.loader.exec_module(generate_module)
generate_csv_from_db = generate_module.generate_csv_from_db

# Importer la base de données
from utils.garnier_db import GarnierDB
from utils.app_config import get_garnier_db_path

# Configuration du logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Variables d'environnement
OUTPUT_DIR = os.getenv("GARNIER_OUTPUT_DIR", "outputs/garnier")
BASE_URL = os.getenv("BASE_URL_GARNIER", "https://garnier-thiebaut.adsi.me")


def extract_gamme_name_from_url(gamme_url: str) -> str:
    """
    Extrait un nom de gamme à partir de l'URL pour le nom du fichier CSV.
    """
    try:
        parsed = urlparse(gamme_url)
        if 'code_gamme' in parsed.query:
            gamme_name = unquote(parsed.query.split('code_gamme=')[1].split('&')[0])
            gamme_name = gamme_name.replace(' ', '_').replace('-', '_')
            return gamme_name[:50]  # Limiter la longueur
    except Exception:
        pass
    
    return "gamme"


def extract_gamme_name_for_db(gamme_url: str) -> str:
    """
    Extrait et nettoie le nom de la gamme depuis l'URL pour la base de données.
    Utilise le même format que collect_from_gamme_url (en majuscule).
    """
    parsed = urlparse(gamme_url)
    gamme_name = "GAMME SPECIFIQUE"
    if 'code_gamme' in parsed.query:
        gamme_name = unquote(parsed.query.split('code_gamme=')[1].split('&')[0])
        # Nettoyer le nom et mettre en majuscule
        gamme_name = gamme_name.replace('_', ' ').replace('-', ' ').upper()
    return gamme_name


def main():
    """
    Fonction principale pour extraire les produits d'une gamme spécifique.
    """
    parser = argparse.ArgumentParser(
        description='Extrait les produits et variantes d\'une gamme spécifique Garnier-Thiebaut.',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Exemples d'utilisation:
  # Extraire une gamme spécifique
  python scraper-garnier-gamme.py --url "https://garnier-thiebaut.adsi.me/products/?code_gamme=MILLE%20ISAPHIRE%20VERMEIL"
  
  # Extraire avec une catégorie spécifiée
  python scraper-garnier-gamme.py --url "https://..." --category "Linge de table"
  
  # Extraire avec un nom de fichier personnalisé
  python scraper-garnier-gamme.py --url "https://..." --output "ma_gamme.csv"
  
  # Limiter le nombre de produits (pour tester)
  python scraper-garnier-gamme.py --url "https://..." --limit 5
  
  # Voir le navigateur pendant l'extraction (débogage)
  python scraper-garnier-gamme.py --url "https://..." --no-headless
  
  # Afficher un aperçu avant de sauvegarder
  python scraper-garnier-gamme.py --url "https://..." --preview
        """
    )
    
    parser.add_argument(
        '--url', '-u',
        required=True,
        metavar='URL',
        help='URL de la gamme à extraire (ex: https://garnier-thiebaut.adsi.me/products/?code_gamme=...)'
    )
    
    parser.add_argument(
        '--category', '-c',
        required=True,
        metavar='CATEGORIE',
        help='Nom de la catégorie (ex: "Linge de table", "Linge de lit")'
    )
    
    parser.add_argument(
        '--output', '-o',
        metavar='FICHIER',
        default=None,
        help='Nom du fichier CSV de sortie (défaut: généré automatiquement)'
    )
    
    parser.add_argument(
        '--no-headless',
        action='store_true',
        help='Affiche le navigateur pendant l\'extraction (utile pour déboguer)'
    )
    
    parser.add_argument(
        '--preview',
        action='store_true',
        help='Affiche un aperçu des données avant de sauvegarder le CSV'
    )
    
    parser.add_argument(
        '--preview-rows',
        type=int,
        metavar='N',
        default=10,
        help='Nombre de lignes à afficher dans l\'aperçu (défaut: 10)'
    )
    
    parser.add_argument(
        '--limit',
        type=int,
        metavar='N',
        default=None,
        help='Limite le nombre de produits à extraire (utile pour tester rapidement)'
    )
    
    args = parser.parse_args()
    
    gamme_url = args.url.strip()
    
    # Vérifier que l'URL est valide
    if not gamme_url.startswith('http'):
        logger.error(f"URL invalide: {gamme_url}")
        logger.error("L'URL doit commencer par http:// ou https://")
        return 1
    
    # Générer le nom du fichier CSV automatiquement si non spécifié
    if args.output:
        output_csv = args.output
    else:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        gamme_name = extract_gamme_name_from_url(gamme_url)
        output_csv = f"shopify_import_garnier_{gamme_name}_{timestamp}.csv"
    
    # Construire le chemin complet du fichier CSV
    if os.path.isabs(output_csv) or '/' in output_csv or '\\' in output_csv:
        csv_path = output_csv
    else:
        csv_path = os.path.join(OUTPUT_DIR, output_csv)
    
    # Créer le répertoire de sortie s'il n'existe pas
    output_dir = os.path.dirname(csv_path)
    if output_dir and not os.path.exists(output_dir):
        os.makedirs(output_dir, exist_ok=True)
        logger.info(f"Répertoire de sortie créé: {output_dir}")
    
    logger.info("="*80)
    logger.info("Extraction de la gamme Garnier-Thiebaut")
    logger.info("="*80)
    logger.info(f"URL de la gamme: {gamme_url}")
    logger.info(f"Répertoire de sortie: {OUTPUT_DIR}")
    logger.info(f"Fichier CSV de sortie: {csv_path}")
    logger.info("="*80)
    
    try:
        # 1. Collecter les produits dans la base de données
        logger.info("\n📦 Collecte des produits dans la base de données...")
        db_path = get_garnier_db_path()
        
        # Collecter les produits et récupérer le driver/session pour réutilisation
        variants_collected, driver, session = collect_from_gamme_url(
            gamme_url=gamme_url,
            output_db=db_path,
            headless=not args.no_headless,
            category=args.category
        )
        
        if variants_collected == 0:
            logger.warning("⚠️ Aucun produit collecté.")
            # Fermer le driver si créé
            if driver:
                driver.quit()
            return 1
        
        logger.info(f"✅ {variants_collected} variant(s) collecté(s) dans la base de données\n")
        
        # 2. Traiter les variants dans la base de données (nécessaire pour générer le CSV)
        logger.info("🔍 Traitement des variants dans la base de données...")
        logger.info("   (Extraction des détails des variants: prix, SKU, stock, etc.)\n")
        
        # Récupérer les IDs des produits de la gamme collectée
        db = GarnierDB(db_path)
        
        # Extraire le nom de la gamme depuis l'URL pour filtrer (utiliser la fonction centralisée)
        gamme_name = extract_gamme_name_for_db(gamme_url)
        
        logger.info(f"🔍 Recherche des produits pour la gamme: '{gamme_name}' et la catégorie: '{args.category}'")
        
        # Récupérer les produits de cette gamme et catégorie
        cursor = db.conn.cursor()
        cursor.execute('''
            SELECT id, product_code, gamme FROM products 
            WHERE gamme = ? AND category = ?
        ''', (gamme_name, args.category))
        products_found = cursor.fetchall()
        
        logger.info(f"📊 Produits trouvés dans la DB: {len(products_found)}")
        if products_found:
            logger.info(f"   Exemples de noms de gamme dans la DB: {[p['gamme'] for p in products_found[:3]]}")
        
        product_ids = [row['id'] for row in products_found]
        
        if not product_ids:
            logger.warning(f"Aucun produit trouvé pour la gamme '{gamme_name}' et la catégorie '{args.category}'")
            logger.warning("Traitement de tous les variants en attente...")
            # Fallback: traiter tous les variants si aucun produit trouvé
            # Réutiliser le driver/session si disponible
            if driver and session:
                from garnier.scraper_garnier_module import extract_variant_data_from_url
                # Utiliser process_urls mais avec le driver existant serait complexe
                # Pour l'instant, on ferme et on laisse process_urls créer son propre driver
                driver.quit()
            process_urls(
                code_vl=None,
                status='pending',
                limit=None,
                retry_errors=False,
                output_db=db_path,
                headless=not args.no_headless
            )
        else:
            # Récupérer les variants de ces produits uniquement avec leurs informations complètes
            placeholders = ','.join(['?'] * len(product_ids))
            cursor.execute(f'''
                SELECT pv.id, pv.code_vl, pv.url, pv.size_text, p.product_code, p.handle
                FROM product_variants pv
                JOIN products p ON pv.product_id = p.id
                WHERE pv.product_id IN ({placeholders}) AND pv.status = 'pending'
                ORDER BY pv.id
            ''', product_ids)
            variants = [dict(row) for row in cursor.fetchall()]
            
            if variants:
                logger.info(f"Traitement de {len(variants)} variant(s) de la gamme '{gamme_name}'...")
                
                # Traiter tous les variants en une seule session (plus efficace)
                from garnier.scraper_garnier_module import extract_variant_data_from_url, wait_for_url_accessible
                
                # Réutiliser le driver/session de la collecte (pas besoin de ré-authentifier)
                if not driver or not session:
                    # Si le driver n'a pas été retourné, créer une nouvelle authentification
                    from garnier.scraper_garnier_module import authenticate
                    driver, session = authenticate(headless=not args.no_headless)
                    if not driver:
                        logger.error("Impossible de s'authentifier")
                        return 1
                    logger.info("Authentification réussie")
                else:
                    logger.info("Réutilisation du driver et de la session de la collecte")
                
                # Traiter chaque variant
                success_count = 0
                error_count = 0
                
                for idx, variant in enumerate(variants, 1):
                    variant_id = variant['id']
                    code_vl = variant['code_vl']
                    url = variant['url']
                    
                    logger.info(f"\n[{idx}/{len(variants)}] Variant {code_vl}")
                    
                    try:
                        # Marquer comme en cours de traitement
                        db.mark_variant_processing(variant_id)
                        logger.info(f"Traitement du variant {code_vl}...")
                        
                        # Extraire les données du variant
                        variant_data, driver, session = extract_variant_data_from_url(
                            driver, session, url, code_vl, headless=not args.no_headless
                        )
                        
                        if not variant_data:
                            raise Exception("Aucune donnée extraite")
                        
                        # Log pour déboguer avant stockage
                        logger.info(f"  Stockage dans DB - SKU: '{variant_data.get('sku')}', Gencode: '{variant_data.get('gencode')}'")
                        
                        # Validation des données obligatoires
                        sku = variant_data.get('sku')
                        gencode = variant_data.get('gencode')
                        stock = variant_data.get('stock')
                        price_pvc = variant_data.get('price_pvc')
                        
                        # Vérifier que SKU et gencode ne sont pas vides
                        if not sku or not sku.strip():
                            raise Exception("SKU manquant ou vide")
                        
                        if not gencode or not gencode.strip():
                            raise Exception("Code-barre (gencode) manquant ou vide")
                        
                        # Vérifier que stock n'est pas None
                        if stock is None:
                            raise Exception("Stock manquant")
                        
                        # Vérifier que price_pvc n'est pas vide
                        if not price_pvc or not str(price_pvc).strip():
                            raise Exception("Prix PVC manquant ou vide")
                        
                        # Si validation OK, stocker les données dans la DB
                        db.update_variant_data(
                            variant_id=variant_id,
                            sku=sku,
                            gencode=gencode,
                            price_pa=variant_data.get('price_pa'),
                            price_pvc=price_pvc,
                            stock=stock,
                            size=variant_data.get('size'),
                            color=variant_data.get('color'),
                            material=variant_data.get('material'),
                            status='completed'
                        )
                        
                        logger.info(f"✓ Variant {code_vl} traité avec succès (SKU: {sku}, Gencode: {gencode}, Stock: {stock}, Prix PVC: {price_pvc})")
                        success_count += 1
                        
                        # Vérifier si tous les variants du produit sont maintenant traités
                        cursor = db.conn.cursor()
                        cursor.execute('SELECT product_id FROM product_variants WHERE id = ?', (variant_id,))
                        row = cursor.fetchone()
                        if row:
                            product_id = row['product_id']
                            db.update_product_status_if_all_variants_processed(product_id)
                        
                    except Exception as e:
                        error_msg = str(e)
                        
                        # Détecter les erreurs liées à l'indisponibilité du site
                        is_site_unavailable = any(keyword in error_msg.lower() for keyword in [
                            'timeout', 'non trouvé après', 'introuvable', 
                            'connection', 'unreachable', 'refused', '503', '502', '500',
                            'div.tabs.product-tabs introuvable'
                        ])
                        
                        if is_site_unavailable:
                            logger.warning(f"Erreur d'accès au site pour le variant {code_vl}: {error_msg}")
                            logger.info("Vérification de la disponibilité de l'URL du variant...")
                            
                            # Attendre que l'URL du variant soit accessible
                            wait_for_url_accessible(session, url, check_interval=30, timeout=300)  # 5 minutes
                            
                            logger.info(f"URL du variant accessible, reprise de l'extraction pour le variant {code_vl}...")
                            
                            # Réessayer l'extraction
                            try:
                                db.mark_variant_processing(variant_id)
                                variant_data, driver, session = extract_variant_data_from_url(
                                    driver, session, url, code_vl, headless=not args.no_headless
                                )
                                
                                if not variant_data:
                                    raise Exception("Aucune donnée extraite")
                                
                                # Log pour déboguer avant stockage
                                logger.info(f"  Stockage dans DB (retry) - SKU: '{variant_data.get('sku')}', Gencode: '{variant_data.get('gencode')}'")
                                
                                # Validation des données obligatoires
                                sku = variant_data.get('sku')
                                gencode = variant_data.get('gencode')
                                stock = variant_data.get('stock')
                                price_pvc = variant_data.get('price_pvc')
                                
                                # Vérifier que SKU et gencode ne sont pas vides
                                if not sku or not sku.strip():
                                    raise Exception("SKU manquant ou vide après retry")
                                
                                if not gencode or not gencode.strip():
                                    raise Exception("Code-barre (gencode) manquant ou vide après retry")
                                
                                # Vérifier que stock n'est pas None
                                if stock is None:
                                    raise Exception("Stock manquant après retry")
                                
                                # Vérifier que price_pvc n'est pas vide
                                if not price_pvc or not str(price_pvc).strip():
                                    raise Exception("Prix PVC manquant ou vide après retry")
                                
                                # Si validation OK, stocker les données dans la DB
                                db.update_variant_data(
                                    variant_id=variant_id,
                                    sku=sku,
                                    gencode=gencode,
                                    price_pa=variant_data.get('price_pa'),
                                    price_pvc=price_pvc,
                                    stock=stock,
                                    size=variant_data.get('size'),
                                    color=variant_data.get('color'),
                                    material=variant_data.get('material'),
                                    status='completed'
                                )
                                
                                logger.info(f"✓ Variant {code_vl} traité avec succès après reprise (SKU: {sku}, Gencode: {gencode}, Stock: {stock}, Prix PVC: {price_pvc})")
                                success_count += 1
                                
                                # Vérifier si tous les variants du produit sont maintenant traités
                                cursor = db.conn.cursor()
                                cursor.execute('SELECT product_id FROM product_variants WHERE id = ?', (variant_id,))
                                row = cursor.fetchone()
                                if row:
                                    product_id = row['product_id']
                                    db.update_product_status_if_all_variants_processed(product_id)
                                
                            except Exception as retry_error:
                                error_msg = str(retry_error)
                                db.mark_variant_error(variant_id, error_msg)
                                logger.error(f"✗ Erreur persistante pour le variant {code_vl}: {error_msg}")
                                error_count += 1
                        else:
                            # Erreur non liée à l'indisponibilité du site
                            db.mark_variant_error(variant_id, error_msg)
                            logger.error(f"✗ Erreur pour le variant {code_vl}: {error_msg}")
                            error_count += 1
                
                # Fermer le driver
                if driver:
                    try:
                        driver.quit()
                    except:
                        pass
                
                # Mettre à jour le status des produits après traitement
                logger.info("\nMise à jour du status des produits...")
                db.update_products_status_after_processing()
                
                logger.info(f"\n✅ Traitement terminé: {success_count} succès, {error_count} erreurs")
            else:
                logger.info(f"Aucun variant en attente pour la gamme '{gamme_name}'")
                # Fermer le driver si aucun variant à traiter
                if driver:
                    try:
                        driver.quit()
                    except:
                        pass
        
        logger.info("\n✅ Traitement des variants terminé\n")
        
        # 3. Générer le CSV depuis la base de données
        logger.info("📄 Génération du fichier CSV depuis la base de données...")
        
        # Utiliser le même nom de gamme que pour le traitement (fonction centralisée)
        gamme_name_for_csv = extract_gamme_name_for_db(gamme_url)
        
        logger.info(f"🔍 Filtrage CSV par gamme: '{gamme_name_for_csv}' et catégorie: '{args.category}'")
        
        # Générer le CSV depuis la DB (filtré par gamme)
        try:
            generate_csv_from_db(
                output_file=csv_path,
                output_db=db_path,
                supplier='garnier',
                categories=[args.category],  # Filtrer par catégorie
                gamme=gamme_name_for_csv  # Filtrer par gamme
            )
            
            # Vérifier que le fichier a été créé
            if os.path.exists(csv_path):
                logger.info("✅ CSV généré avec succès!")
                logger.info(f"   Fichier: {csv_path}")
            else:
                logger.error("❌ Le fichier CSV n'a pas été créé")
                logger.error("   Vérifiez que les variants ont été collectés et traités")
                return 1
        except Exception as csv_error:
            logger.error(f"❌ Erreur lors de la génération du CSV: {csv_error}")
            import traceback
            logger.error(traceback.format_exc())
            return 1
        
        # Afficher un aperçu si demandé
        if args.preview:
            import pandas as pd
            df = pd.read_csv(csv_path)
            
            pd.set_option('display.max_columns', None)
            pd.set_option('display.max_colwidth', 50)
            pd.set_option('display.width', None)
            pd.set_option('display.max_rows', args.preview_rows)
            
            print("\n" + "="*80)
            print("📊 APERÇU DU CSV SHOPIFY")
            print("="*80)
            
            print(f"\n📈 Informations générales:")
            print(f"   • Total de lignes (variantes): {len(df)}")
            print(f"   • Total de colonnes: {len(df.columns)}")
            print(f"   • Produits uniques: {df['Handle'].nunique()}")
            
            important_cols = [
                'Handle', 'Title', 'Variant SKU', 'Variant Price', 
                'Variant Compare At Price', 'Variant Inventory Qty',
                'Option1 Name', 'Option1 Value', 'Variant Barcode'
            ]
            
            available_cols = [col for col in important_cols if col in df.columns]
            other_cols = [col for col in df.columns if col not in important_cols]
            
            print(f"\n📋 Premières {args.preview_rows} lignes (colonnes principales):")
            print("-"*80)
            preview_df = df[available_cols].head(args.preview_rows)
            print(preview_df.to_string(index=False))
            
            if len(df) > args.preview_rows:
                print(f"\n... ({len(df) - args.preview_rows} lignes supplémentaires)")
            
            if other_cols:
                print(f"\n📋 Autres colonnes disponibles: {', '.join(other_cols)}")
            
            print("\n" + "="*80)
        
        logger.info("="*80)
        logger.info("✅ Terminé avec succès!")
        logger.info(f"   Fichier CSV: {csv_path}")
        logger.info(f"   Base de données: {db_path}")
        logger.info("="*80)
        
        return 0
    
    except KeyboardInterrupt:
        logger.info("\n\n⚠️ Interruption par l'utilisateur.")
        return 1
    except Exception as e:
        logger.error(f"\n❌ Erreur fatale: {e}", exc_info=True)
        return 1


if __name__ == "__main__":
    sys.exit(main())
