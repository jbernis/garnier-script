#!/usr/bin/env python3
"""
Script de migration pour nettoyer les noms de gammes dans la base de données.
"""

import sys
import os
import logging
import re

# Ajouter le répertoire parent au path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from utils.garnier_db import GarnierDB
from utils.app_config import get_garnier_db_path


def clean_gamme_name(gamme_name_raw: str) -> str:
    """
    Nettoie le nom de la gamme Garnier.
    
    Format d'entrée: "51469 - LOT H.COUETTE +TAIES ANNABELLE MIMOSAnewPA..."
    Format de sortie: "ANNABELLE MIMOSA"
    
    Args:
        gamme_name_raw: Nom brut de la gamme
        
    Returns:
        Nom nettoyé de la gamme
    """
    if not gamme_name_raw:
        return ""
    
    cleaned = gamme_name_raw.strip()
    
    # Étape 1: Enlever tout avant le premier " - " (code numérique)
    if ' - ' in cleaned:
        cleaned = cleaned.split(' - ', 1)[1]
    
    # Étape 2: Enlever tout à partir de "newPA", "NRPA", ou "PA" (suffixes de prix)
    # Utiliser une regex pour capturer différentes variantes
    cleaned = re.sub(r'(NR|new)?PA.*$', '', cleaned, flags=re.IGNORECASE).strip()
    
    # Étape 3: Enlever les types de produits courants au début
    product_types = [
        r'LOT H\.COUETTE \+TAIES\s+',
        r'HOUSSE DE COUETTE\s+',
        r'LOT DE 2 TAIES\s+',
        r'TAIE D\'OREILLER\s+',
        r'DRAP HOUSSE B\d+\s+',
        r'TORCHON\s+',
        r'CHEMIN DE TABLE\s+',
        r'NAPPE\s+',
        r'SERVIETTE\s+',
        r'SET DE TABLE\s+',
    ]
    
    for ptype in product_types:
        cleaned = re.sub(ptype, '', cleaned, flags=re.IGNORECASE).strip()
    
    # Étape 4: Enlever les espaces multiples
    cleaned = re.sub(r'\s+', ' ', cleaned).strip()
    
    # Étape 5: Enlever les prix résiduels (chiffres suivis de €)
    cleaned = re.sub(r'\s*[\d,.\s]+€.*$', '', cleaned).strip()
    
    return cleaned

# Configuration du logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def migrate_gammes():
    """Nettoie tous les noms de gammes dans la base de données."""
    
    db_path = get_garnier_db_path()
    logger.info(f"Connexion à la base de données: {db_path}")
    
    db = GarnierDB(db_path)
    cursor = db.conn.cursor()
    
    try:
        # Récupérer tous les produits avec leur gamme
        cursor.execute('''
            SELECT id, gamme
            FROM products
            WHERE gamme IS NOT NULL AND gamme != ''
        ''')
        
        products = cursor.fetchall()
        total = len(products)
        logger.info(f"Nombre de produits avec gamme à traiter: {total}")
        
        if total == 0:
            logger.info("Aucun produit avec gamme trouvé")
            return
        
        # Compteurs
        updated = 0
        unchanged = 0
        errors = 0
        
        # Traiter chaque produit
        for idx, product in enumerate(products, 1):
            product_id = product['id']
            old_gamme = product['gamme']
            
            try:
                # Nettoyer le nom de la gamme
                new_gamme = clean_gamme_name(old_gamme)
                
                # Vérifier si le nom a changé
                if new_gamme != old_gamme:
                    # Mettre à jour la base de données
                    cursor.execute('''
                        UPDATE products
                        SET gamme = ?
                        WHERE id = ?
                    ''', (new_gamme, product_id))
                    
                    updated += 1
                    
                    # Afficher les 10 premiers changements pour vérification
                    if updated <= 10:
                        logger.info(f"  [{idx}/{total}] Product ID {product_id}:")
                        logger.info(f"    Ancien: '{old_gamme}'")
                        logger.info(f"    Nouveau: '{new_gamme}'")
                else:
                    unchanged += 1
                
                # Afficher la progression tous les 100 produits
                if idx % 100 == 0:
                    logger.info(f"Progression: {idx}/{total} produits traités")
                    
            except Exception as e:
                errors += 1
                logger.error(f"Erreur pour le produit ID {product_id}: {e}")
        
        # Commit des changements
        db.conn.commit()
        
        # Afficher le résumé
        logger.info(f"\n{'='*60}")
        logger.info("Migration terminée!")
        logger.info(f"{'='*60}")
        logger.info(f"Total de produits traités: {total}")
        logger.info(f"Produits mis à jour: {updated}")
        logger.info(f"Produits inchangés: {unchanged}")
        logger.info(f"Erreurs: {errors}")
        logger.info(f"{'='*60}\n")
        
        # Vérifier les gammes uniques après migration
        cursor.execute('''
            SELECT DISTINCT gamme
            FROM products
            WHERE gamme IS NOT NULL AND gamme != ''
            ORDER BY gamme
        ''')
        
        unique_gammes = cursor.fetchall()
        logger.info(f"Nombre de gammes uniques après migration: {len(unique_gammes)}")
        logger.info("\nGammes nettoyées disponibles:")
        for gamme in unique_gammes[:20]:  # Afficher les 20 premières
            logger.info(f"  - {gamme['gamme']}")
        
        if len(unique_gammes) > 20:
            logger.info(f"  ... et {len(unique_gammes) - 20} autres")
        
    except Exception as e:
        logger.error(f"Erreur lors de la migration: {e}", exc_info=True)
        db.conn.rollback()
        raise
    finally:
        db.close()


if __name__ == '__main__':
    logger.info("Démarrage de la migration des gammes...")
    logger.info("Ce script va nettoyer tous les noms de gammes dans la base de données")
    
    # Demander confirmation
    response = input("\nVoulez-vous continuer? (oui/non): ").strip().lower()
    
    if response in ['oui', 'o', 'yes', 'y']:
        migrate_gammes()
        logger.info("Migration terminée avec succès!")
    else:
        logger.info("Migration annulée par l'utilisateur")
