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
    
    def import_csv(self, csv_path: str, clear_product_category: bool = False, update_existing: bool = True) -> int:
        """
        Charge un CSV Shopify dans la base de données.
        Si update_existing=True (défaut), met à jour l'import existant du même fichier.
        Sinon, crée un nouvel import.
        
        Args:
            csv_path: Chemin vers le fichier CSV à importer
            clear_product_category: Si True, vide la colonne 'Product Category' lors de l'import
            update_existing: Si True, met à jour l'import existant du même fichier (défaut)
            
        Returns:
            csv_import_id: ID de l'import créé ou mis à jour
            
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
        
        # Vider la colonne Product Category si demandé
        if clear_product_category and 'Product Category' in df.columns:
            df['Product Category'] = ''
            logger.info("✓ Colonne 'Product Category' vidée lors de l'import")
        
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
        
        # Vérifier si un import existe déjà pour ce fichier
        cursor = self.db.conn.cursor()
        cursor.execute('SELECT id FROM csv_imports WHERE original_file_path = ?', (csv_path,))
        existing_import = cursor.fetchone()
        
        if existing_import and update_existing:
            # 🔄 MISE À JOUR: Supprimer seulement les lignes de cet import
            csv_import_id = existing_import['id']
            logger.info(f"📝 Mise à jour de l'import existant (ID: {csv_import_id})")
            
            # Supprimer les anciennes lignes (CASCADE supprimera aussi les traitements)
            cursor.execute('DELETE FROM csv_rows WHERE csv_import_id = ?', (csv_import_id,))
            
            # Mettre à jour les infos de l'import
            cursor.execute('''
                UPDATE csv_imports 
                SET imported_at = CURRENT_TIMESTAMP, total_rows = ?
                WHERE id = ?
            ''', (total_rows, csv_import_id))
            
            self.db.conn.commit()
        else:
            # ✨ NOUVEL IMPORT: Créer un nouveau
            logger.info(f"✨ Création d'un nouvel import")
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
        Utilise csv_type depuis product_category_cache pour le champ Type.
        
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
        
        # Mettre à jour le champ Type avec csv_type depuis product_category_cache
        if 'Handle' in df.columns:
            cursor = self.db.conn.cursor()
            for idx, handle in enumerate(df['Handle']):
                if pd.notna(handle) and handle:
                    # Récupérer csv_type depuis product_category_cache
                    product_key = self.db._generate_product_key({'Handle': handle})
                    cursor.execute('''
                        SELECT csv_type FROM product_category_cache
                        WHERE product_key = ?
                    ''', (product_key,))
                    cache_result = cursor.fetchone()
                    
                    if cache_result and cache_result['csv_type']:
                        # Utiliser csv_type si disponible
                        df.at[idx, 'Type'] = cache_result['csv_type']
                        logger.debug(f"Type mis à jour pour {handle}: {cache_result['csv_type']}")
        
        # Exclure les colonnes internes/non Shopify de l'export
        excluded_columns = {
            '_google_category_confidence',
            '_google_category_needs_review',
            '_google_category_rationale',
            'Google Category Confidence',
            'Google Category Needs Review',
            'Google Category Rationale',
        }
        existing_excluded = [col for col in df.columns if col in excluded_columns]
        if existing_excluded:
            df = df.drop(columns=existing_excluded)
            logger.debug(f"Colonnes exclues de l'export: {', '.join(existing_excluded)}")
        
        # Réordonner les colonnes selon SHOPIFY_ALL_COLUMNS si disponible
        try:
            from csv_config import SHOPIFY_ALL_COLUMNS
            # Garder l'ordre des colonnes définies dans SHOPIFY_ALL_COLUMNS
            # Ajouter les colonnes manquantes à la fin (incluant les nouvelles colonnes LangGraph)
            ordered_columns = [col for col in SHOPIFY_ALL_COLUMNS if col in df.columns]
            other_columns = [col for col in df.columns if col not in ordered_columns]
            df = df[ordered_columns + other_columns]
        except ImportError:
            logger.warning("csv_config non disponible, utilisation de l'ordre par défaut")
        
        # S'assurer que la colonne "Google Shopping / Google Product Category" existe dans le DataFrame
        # (même si elle n'existe pas dans toutes les lignes, elle doit être dans le CSV exporté)
        if 'Google Shopping / Google Product Category' not in df.columns:
            df['Google Shopping / Google Product Category'] = ''
            logger.debug("Colonne 'Google Shopping / Google Product Category' créée (vide)")
        else:
            # Remplacer uniquement les NaN par des chaînes vides (garder les valeurs existantes)
            df['Google Shopping / Google Product Category'] = df['Google Shopping / Google Product Category'].fillna('')
            logger.debug(f"Colonne 'Google Shopping / Google Product Category' présente avec {df['Google Shopping / Google Product Category'].notna().sum()} valeurs non vides")
            
            # Convertir les chemins textuels en IDs numériques
            converted_count = 0
            for idx in df.index:
                google_cat = df.at[idx, 'Google Shopping / Google Product Category']
                
                # Si la valeur contient " > ", c'est un chemin textuel, pas un ID
                if google_cat and isinstance(google_cat, str) and ' > ' in google_cat:
                    # Tenter de retrouver l'ID dans la taxonomie
                    category_id = self.db.search_google_category(google_cat)
                    if category_id:
                        df.at[idx, 'Google Shopping / Google Product Category'] = category_id
                        converted_count += 1
                        logger.debug(f"Converti chemin → ID: '{google_cat}' → '{category_id}'")
                    # Si ID non trouvé, on laisse la valeur telle quelle (pas de vidage forcé)
            
            if converted_count > 0:
                logger.info(f"✓ Converti {converted_count} chemin(s) textuel(s) en ID(s) Google")
        
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
