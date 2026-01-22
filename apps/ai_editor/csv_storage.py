"""
Module de stockage CSV pour charger et exporter les fichiers CSV Shopify depuis/vers la base de données.
"""

import pandas as pd
import json
import logging
from typing import List, Dict, Optional, Set
from pathlib import Path

logger = logging.getLogger(__name__)

# Colonne obligatoire Shopify
REQUIRED_SHOPIFY_COLUMN = 'Handle'

# Colonnes Shopify typiques (au moins quelques-unes doivent être présentes)
TYPICAL_SHOPIFY_COLUMNS = [
    'Title',
    'Body (HTML)',
    'Vendor',
    'Type',
    'Tags',
    'Variant SKU',
    'Variant Price',
    'Variant Compare At Price',
    'Variant Inventory Qty',
    'Image Src',
    'Image Position',
    'SEO Title',
    'SEO Description',
    'Google Shopping / Google Product Category'
]


class CSVStorage:
    """Gestionnaire de stockage CSV dans la base de données."""
    
    def __init__(self, db):
        """
        Initialise le gestionnaire de stockage CSV.
        
        Args:
            db: Instance de AIPromptsDB
        """
        self.db = db
    
    def import_csv(self, csv_path: str) -> int:
        """
        Charge un CSV Shopify dans la base de données.
        ATTENTION: Supprime TOUS les imports existants avant d'importer le nouveau fichier.
        
        Args:
            csv_path: Chemin vers le fichier CSV à importer
            
        Returns:
            csv_import_id: ID de l'import créé
            
        Raises:
            ValueError: Si le fichier n'est pas au format Shopify
        """
        logger.info(f"Import du CSV: {csv_path}")
        
        # Lire le CSV
        try:
            df = pd.read_csv(csv_path, dtype=str, keep_default_na=False)
        except Exception as e:
            logger.error(f"Erreur lors de la lecture du CSV: {e}")
            raise
        
        # VALIDATION 1: Vérifier que Handle existe (obligatoire)
        if REQUIRED_SHOPIFY_COLUMN not in df.columns:
            error_msg = (
                "Le fichier n'est pas au format Shopify.\n"
                f"La colonne '{REQUIRED_SHOPIFY_COLUMN}' est obligatoire."
            )
            logger.error(error_msg)
            raise ValueError(error_msg)
        
        # VALIDATION 2: Vérifier qu'au moins quelques colonnes Shopify typiques existent
        present_columns = [col for col in TYPICAL_SHOPIFY_COLUMNS if col in df.columns]
        if len(present_columns) < 2:
            error_msg = (
                "Le fichier ne semble pas être au format Shopify.\n"
                "Aucune colonne Shopify typique détectée.\n"
                f"Colonnes présentes: {', '.join(df.columns[:10])}"
            )
            logger.error(error_msg)
            raise ValueError(error_msg)
        
        total_rows = len(df)
        logger.info(f"CSV validé: {total_rows} lignes, {len(df.columns)} colonnes")
        logger.info(f"Colonnes Shopify détectées: {', '.join(present_columns)}")
        
        # 🗑️ SUPPRIMER TOUS LES IMPORTS EXISTANTS avant d'importer le nouveau
        self.db.clear_all_imports()
        
        # Créer le nouvel import dans la base de données
        csv_import_id = self.db.create_csv_import(csv_path, total_rows)
        
        # Insérer chaque ligne dans csv_rows
        cursor = self.db.conn.cursor()
        
        for idx, row in df.iterrows():
            # Convertir la ligne en dictionnaire
            row_dict = row.to_dict()
            
            # Extraire le handle pour indexation rapide
            handle = row_dict.get('Handle', '')
            
            # Stocker toutes les colonnes en JSON
            data_json = json.dumps(row_dict, ensure_ascii=False)
            
            cursor.execute('''
                INSERT OR REPLACE INTO csv_rows 
                (csv_import_id, row_index, handle, data_json)
                VALUES (?, ?, ?, ?)
            ''', (csv_import_id, int(idx), handle, data_json))
        
        self.db.conn.commit()
        logger.info(f"Import terminé: {total_rows} lignes stockées dans la base de données")
        
        return csv_import_id
    
    def get_csv_rows(self, csv_import_id: int, handles: Optional[Set[str]] = None) -> List[Dict]:
        """
        Récupère les lignes CSV depuis la base de données.
        
        Args:
            csv_import_id: ID de l'import CSV
            handles: Set de handles à filtrer (optionnel, None = toutes les lignes)
            
        Returns:
            Liste de dictionnaires contenant les données des lignes
        """
        cursor = self.db.conn.cursor()
        
        if handles:
            # Filtrer par handles
            placeholders = ','.join(['?'] * len(handles))
            cursor.execute(f'''
                SELECT * FROM csv_rows 
                WHERE csv_import_id = ? AND handle IN ({placeholders})
                ORDER BY row_index
            ''', (csv_import_id, *handles))
        else:
            # Toutes les lignes
            cursor.execute('''
                SELECT * FROM csv_rows 
                WHERE csv_import_id = ?
                ORDER BY row_index
            ''', (csv_import_id,))
        
        rows = []
        for row in cursor.fetchall():
            row_dict = dict(row)
            # Décoder le JSON
            row_dict['data'] = json.loads(row_dict['data_json'])
            rows.append(row_dict)
        
        return rows
    
    def get_unique_handles(self, csv_import_id: int) -> List[str]:
        """
        Récupère la liste des handles uniques pour un import CSV.
        
        Args:
            csv_import_id: ID de l'import CSV
            
        Returns:
            Liste des handles uniques (triés)
        """
        cursor = self.db.conn.cursor()
        cursor.execute('''
            SELECT DISTINCT handle FROM csv_rows 
            WHERE csv_import_id = ? AND handle IS NOT NULL AND handle != ''
            ORDER BY handle
        ''', (csv_import_id,))
        
        return [row['handle'] for row in cursor.fetchall()]
    
    def update_csv_row(self, csv_row_id: int, field_updates: Dict[str, str]):
        """
        Met à jour des champs spécifiques d'une ligne CSV.
        
        Args:
            csv_row_id: ID de la ligne à mettre à jour
            field_updates: Dictionnaire {field_name: new_value}
        """
        cursor = self.db.conn.cursor()
        
        # Récupérer la ligne actuelle
        cursor.execute('SELECT data_json FROM csv_rows WHERE id = ?', (csv_row_id,))
        row = cursor.fetchone()
        if not row:
            raise ValueError(f"Ligne CSV {csv_row_id} introuvable")
        
        # Décoder le JSON
        data = json.loads(row['data_json'])
        
        # Mettre à jour les champs
        for field_name, new_value in field_updates.items():
            data[field_name] = new_value
        
        # Encoder et sauvegarder
        data_json = json.dumps(data, ensure_ascii=False)
        cursor.execute('''
            UPDATE csv_rows 
            SET data_json = ?, updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
        ''', (data_json, csv_row_id))
        
        self.db.conn.commit()
        logger.debug(f"Ligne CSV {csv_row_id} mise à jour: {list(field_updates.keys())}")
    
    def update_csv_row_status(self, csv_row_id: int, status: str, error_message: str = None, ai_explanation: str = None):
        """
        Met à jour le status, error_message et ai_explanation d'une ligne CSV.
        
        Args:
            csv_row_id: ID de la ligne à mettre à jour
            status: Nouveau status ('pending', 'processing', 'completed', 'error')
            error_message: Message d'erreur court (optionnel)
            ai_explanation: Explication complète de l'IA (optionnel)
        """
        cursor = self.db.conn.cursor()
        
        cursor.execute('''
            UPDATE csv_rows 
            SET status = ?, 
                error_message = ?, 
                ai_explanation = ?,
                updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
        ''', (status, error_message, ai_explanation, csv_row_id))
        
        self.db.conn.commit()
        logger.debug(f"Ligne CSV {csv_row_id} - Status: {status}")
    
    def get_row_by_id(self, csv_row_id: int) -> Optional[Dict]:
        """
        Récupère une ligne CSV par son ID.
        
        Args:
            csv_row_id: ID de la ligne
            
        Returns:
            Dictionnaire avec les données de la ligne (None si introuvable)
        """
        cursor = self.db.conn.cursor()
        cursor.execute('SELECT * FROM csv_rows WHERE id = ?', (csv_row_id,))
        row = cursor.fetchone()
        
        if not row:
            return None
        
        row_dict = dict(row)
        row_dict['data'] = json.loads(row_dict['data_json'])
        return row_dict
    
    def get_row_id_by_handle(self, csv_import_id: int, handle: str) -> Optional[int]:
        """
        Récupère l'ID d'une ligne CSV par son handle.
        
        Args:
            csv_import_id: ID de l'import CSV
            handle: Handle du produit
            
        Returns:
            ID de la ligne (None si introuvable)
        """
        cursor = self.db.conn.cursor()
        cursor.execute('''
            SELECT id FROM csv_rows 
            WHERE csv_import_id = ? AND handle = ?
            LIMIT 1
        ''', (csv_import_id, handle))
        row = cursor.fetchone()
        
        return row['id'] if row else None
    
    def get_rows_by_status(self, csv_import_id: int, status: str) -> List[Dict]:
        """
        Récupère les lignes CSV par status.
        
        Args:
            csv_import_id: ID de l'import CSV
            status: Status à filtrer ('pending', 'processing', 'completed', 'error')
            
        Returns:
            Liste de dictionnaires contenant les données des lignes
        """
        cursor = self.db.conn.cursor()
        cursor.execute('''
            SELECT * FROM csv_rows 
            WHERE csv_import_id = ? AND status = ?
            ORDER BY row_index
        ''', (csv_import_id, status))
        
        rows = []
        for row in cursor.fetchall():
            row_dict = dict(row)
            row_dict['data'] = json.loads(row_dict['data_json'])
            rows.append(row_dict)
        
        return rows
    
    def get_status_summary(self, csv_import_id: int) -> Dict[str, int]:
        """
        Récupère le résumé des status pour un import CSV (compte les produits uniques, pas les lignes).
        
        Args:
            csv_import_id: ID de l'import CSV
            
        Returns:
            Dictionnaire {status: count} où count = nombre de produits uniques (handles)
        """
        cursor = self.db.conn.cursor()
        cursor.execute('''
            SELECT status, COUNT(DISTINCT handle) as count 
            FROM csv_rows 
            WHERE csv_import_id = ?
            GROUP BY status
        ''', (csv_import_id,))
        
        summary = {}
        for row in cursor.fetchall():
            status = row['status'] if row['status'] else 'pending'
            summary[status] = row['count']
        
        return summary
    
    def export_csv(self, csv_import_id: int, output_path: str):
        """
        Exporte le CSV depuis la base de données vers un fichier.
        
        Args:
            csv_import_id: ID de l'import CSV
            output_path: Chemin du fichier CSV de sortie
        """
        logger.info(f"Export du CSV vers: {output_path}")
        
        # Récupérer toutes les lignes
        rows = self.get_csv_rows(csv_import_id)
        
        if not rows:
            raise ValueError(f"Aucune ligne trouvée pour l'import {csv_import_id}")
        
        # Reconstruire le DataFrame
        data_list = [row['data'] for row in rows]
        df = pd.DataFrame(data_list)
        
        # Réordonner les colonnes selon SHOPIFY_ALL_COLUMNS si disponible
        try:
            from csv_config import SHOPIFY_ALL_COLUMNS
            # Garder l'ordre des colonnes définies dans SHOPIFY_ALL_COLUMNS
            # Ajouter les colonnes manquantes à la fin
            ordered_columns = [col for col in SHOPIFY_ALL_COLUMNS if col in df.columns]
            other_columns = [col for col in df.columns if col not in ordered_columns]
            df = df[ordered_columns + other_columns]
        except ImportError:
            logger.warning("csv_config non disponible, utilisation de l'ordre par défaut")
        
        # Sauvegarder le CSV
        output_file = Path(output_path)
        output_file.parent.mkdir(parents=True, exist_ok=True)
        
        df.to_csv(output_path, index=False, encoding='utf-8')
        logger.info(f"CSV exporté: {len(df)} lignes, {len(df.columns)} colonnes")
        
        return output_path
    
    def get_last_import(self) -> Optional[Dict]:
        """
        Récupère le dernier import CSV de la base de données.
        
        Returns:
            Dict avec les clés: id, original_file_path, imported_at, total_rows
            None si aucun import trouvé
        """
        cursor = self.db.conn.cursor()
        cursor.execute("""
            SELECT id, original_file_path, imported_at, total_rows
            FROM csv_imports
            ORDER BY imported_at DESC
            LIMIT 1
        """)
        
        result = cursor.fetchone()
        
        if not result:
            return None
        
        return {
            'id': result[0],
            'original_file_path': result[1],
            'imported_at': result[2],
            'total_rows': result[3]
        }
