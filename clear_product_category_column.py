#!/usr/bin/env python3
"""
Script pour vider la colonne "Product Category" dans tous les CSV stockés dans la base de données.

Ce script met à jour toutes les lignes CSV dans la base de données pour que la colonne
"Product Category" soit vide. La colonne "Google Shopping / Google Product Category"
reste intacte (elle est importante et remplie par l'IA).
"""

import json
import logging
import sys
from pathlib import Path

# Ajouter le répertoire parent au path pour les imports
sys.path.insert(0, str(Path(__file__).parent))

from apps.ai_editor.db import AIPromptsDB

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def clear_product_category_column():
    """Vide uniquement la colonne "Product Category" dans tous les CSV de la base de données.
    
    Note: La colonne "Google Shopping / Google Product Category" reste intacte
    car elle est importante et remplie par l'IA.
    """
    db = AIPromptsDB()
    cursor = db.conn.cursor()
    
    # Colonne à vider (uniquement "Product Category", pas "Google Shopping / Google Product Category")
    product_category_column = 'Product Category'
    
    # Récupérer toutes les lignes CSV
    cursor.execute('SELECT id, data_json FROM csv_rows')
    all_rows = cursor.fetchall()
    
    if not all_rows:
        logger.info("Aucune ligne CSV trouvée dans la base de données")
        return
    
    logger.info(f"Traitement de {len(all_rows)} lignes CSV...")
    
    updated_count = 0
    skipped_count = 0
    
    for row in all_rows:
        row_id = row['id']
        data_json = row['data_json']
        
        try:
            # Décoder le JSON
            data = json.loads(data_json)
            
            # Vérifier si la colonne "Product Category" existe et a une valeur
            has_value = False
            if product_category_column in data:
                if data[product_category_column]:  # Si elle a une valeur non vide
                    has_value = True
                    data[product_category_column] = ''  # Vider la colonne
                else:
                    # Déjà vide, pas besoin de mettre à jour
                    skipped_count += 1
                    continue
            else:
                # La colonne n'existe pas, créer-la vide pour être sûr
                data[product_category_column] = ''
                has_value = True
            
            # Si on a modifié quelque chose, sauvegarder
            if has_value:
                new_data_json = json.dumps(data, ensure_ascii=False)
                cursor.execute('''
                    UPDATE csv_rows 
                    SET data_json = ?, updated_at = CURRENT_TIMESTAMP
                    WHERE id = ?
                ''', (new_data_json, row_id))
                updated_count += 1
            else:
                skipped_count += 1
                
        except json.JSONDecodeError as e:
            logger.error(f"Erreur de décodage JSON pour la ligne {row_id}: {e}")
            skipped_count += 1
        except Exception as e:
            logger.error(f"Erreur lors du traitement de la ligne {row_id}: {e}")
            skipped_count += 1
    
    # Commit toutes les modifications
    db.conn.commit()
    
    logger.info(f"✓ Traitement terminé:")
    logger.info(f"  - {updated_count} lignes mises à jour")
    logger.info(f"  - {skipped_count} lignes ignorées")
    logger.info(f"  - Total: {len(all_rows)} lignes")


if __name__ == '__main__':
    try:
        clear_product_category_column()
        logger.info("✓ Script terminé avec succès")
    except Exception as e:
        logger.error(f"✗ Erreur lors de l'exécution du script: {e}", exc_info=True)
        sys.exit(1)
