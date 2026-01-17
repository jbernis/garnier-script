"""
Module de gestion de la base de données SQLite pour l'éditeur IA.
"""

import sqlite3
import json
import logging
from typing import List, Dict, Optional, Any
from datetime import datetime
from pathlib import Path

logger = logging.getLogger(__name__)

# Chemin par défaut de la base de données
DEFAULT_DB_PATH = "database/ai_prompts.db"


class AIPromptsDB:
    """Gestionnaire de base de données pour les prompts IA et les imports CSV."""
    
    def __init__(self, db_path: str = DEFAULT_DB_PATH):
        """Initialise la connexion à la base de données."""
        self.db_path = db_path
        self.conn = None
        self._init_db()
    
    def _init_db(self):
        """Initialise les tables de la base de données."""
        self.conn = sqlite3.connect(self.db_path)
        self.conn.row_factory = sqlite3.Row  # Permet d'accéder aux colonnes par nom
        cursor = self.conn.cursor()
        
        # Table des ensembles de prompts
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS ai_prompts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                system_prompt TEXT NOT NULL,
                description_prompt TEXT NOT NULL,
                google_category_prompt TEXT NOT NULL,
                seo_prompt TEXT NOT NULL,
                is_default INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Table de l'historique des prompts
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS ai_prompts_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                prompt_set_id INTEGER NOT NULL,
                name TEXT NOT NULL,
                system_prompt TEXT NOT NULL,
                description_prompt TEXT NOT NULL,
                google_category_prompt TEXT NOT NULL,
                seo_prompt TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (prompt_set_id) REFERENCES ai_prompts(id) ON DELETE CASCADE
            )
        ''')
        
        # Table des imports CSV
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS csv_imports (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                original_file_path TEXT NOT NULL,
                imported_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                total_rows INTEGER NOT NULL,
                UNIQUE(original_file_path)
            )
        ''')
        
        # Table des lignes CSV
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS csv_rows (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                csv_import_id INTEGER NOT NULL,
                row_index INTEGER NOT NULL,
                handle TEXT,
                data_json TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (csv_import_id) REFERENCES csv_imports(id) ON DELETE CASCADE,
                UNIQUE(csv_import_id, row_index)
            )
        ''')
        
        # Table des résultats de traitement
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS csv_processing_results (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                csv_import_id INTEGER NOT NULL,
                output_csv_path TEXT NOT NULL,
                prompt_set_id INTEGER NOT NULL,
                provider_name TEXT NOT NULL,
                model_name TEXT NOT NULL,
                processed_handles TEXT,
                fields_processed TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (csv_import_id) REFERENCES csv_imports(id),
                FOREIGN KEY (prompt_set_id) REFERENCES ai_prompts(id)
            )
        ''')
        
        # Table des changements de champs
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS product_field_changes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                processing_result_id INTEGER NOT NULL,
                csv_row_id INTEGER NOT NULL,
                handle TEXT NOT NULL,
                field_name TEXT NOT NULL,
                original_value TEXT,
                new_value TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (processing_result_id) REFERENCES csv_processing_results(id) ON DELETE CASCADE,
                FOREIGN KEY (csv_row_id) REFERENCES csv_rows(id) ON DELETE CASCADE
            )
        ''')
        
        # Table des credentials AI
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS ai_credentials (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                provider_name TEXT NOT NULL UNIQUE,
                api_key TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Index pour améliorer les performances
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_csv_rows_handle ON csv_rows(handle)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_csv_rows_import ON csv_rows(csv_import_id)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_field_changes_handle ON product_field_changes(handle)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_field_changes_result ON product_field_changes(processing_result_id)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_prompts_default ON ai_prompts(is_default)')
        
        self.conn.commit()
        logger.info(f"Base de données initialisée: {self.db_path}")
    
    # ========== Gestion des prompts ==========
    
    def create_prompt_set(self, name: str, system_prompt: str, description_prompt: str,
                          google_category_prompt: str, seo_prompt: str, is_default: bool = False) -> int:
        """Crée un nouvel ensemble de prompts."""
        cursor = self.conn.cursor()
        
        # Si c'est le défaut, désactiver les autres défauts
        if is_default:
            cursor.execute('UPDATE ai_prompts SET is_default = 0')
        
        cursor.execute('''
            INSERT INTO ai_prompts 
            (name, system_prompt, description_prompt, google_category_prompt, seo_prompt, is_default)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (name, system_prompt, description_prompt, google_category_prompt, seo_prompt, 1 if is_default else 0))
        
        self.conn.commit()
        prompt_set_id = cursor.lastrowid
        logger.info(f"Nouvel ensemble de prompts créé: {name} (ID: {prompt_set_id})")
        return prompt_set_id
    
    def update_prompt_set(self, prompt_set_id: int, name: str = None, system_prompt: str = None,
                         description_prompt: str = None, google_category_prompt: str = None,
                         seo_prompt: str = None, is_default: bool = None):
        """Met à jour un ensemble de prompts (sauvegarde automatiquement dans l'historique)."""
        cursor = self.conn.cursor()
        
        # Récupérer la version actuelle pour l'historique
        current = self.get_prompt_set(prompt_set_id)
        if not current:
            raise ValueError(f"Ensemble de prompts {prompt_set_id} introuvable")
        
        # Sauvegarder dans l'historique
        cursor.execute('''
            INSERT INTO ai_prompts_history 
            (prompt_set_id, name, system_prompt, description_prompt, google_category_prompt, seo_prompt)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (prompt_set_id, current['name'], current['system_prompt'], current['description_prompt'],
              current['google_category_prompt'], current['seo_prompt']))
        
        # Si c'est le défaut, désactiver les autres défauts
        if is_default:
            cursor.execute('UPDATE ai_prompts SET is_default = 0 WHERE id != ?', (prompt_set_id,))
        
        # Construire la requête de mise à jour
        updates = []
        params = []
        
        if name is not None:
            updates.append('name = ?')
            params.append(name)
        if system_prompt is not None:
            updates.append('system_prompt = ?')
            params.append(system_prompt)
        if description_prompt is not None:
            updates.append('description_prompt = ?')
            params.append(description_prompt)
        if google_category_prompt is not None:
            updates.append('google_category_prompt = ?')
            params.append(google_category_prompt)
        if seo_prompt is not None:
            updates.append('seo_prompt = ?')
            params.append(seo_prompt)
        if is_default is not None:
            updates.append('is_default = ?')
            params.append(1 if is_default else 0)
        
        updates.append('updated_at = CURRENT_TIMESTAMP')
        params.append(prompt_set_id)
        
        if updates:
            query = f'UPDATE ai_prompts SET {", ".join(updates)} WHERE id = ?'
            cursor.execute(query, params)
            self.conn.commit()
            logger.info(f"Ensemble de prompts {prompt_set_id} mis à jour")
    
    def get_prompt_set(self, prompt_set_id: int) -> Optional[Dict]:
        """Récupère un ensemble de prompts par son ID."""
        cursor = self.conn.cursor()
        cursor.execute('SELECT * FROM ai_prompts WHERE id = ?', (prompt_set_id,))
        row = cursor.fetchone()
        return dict(row) if row else None
    
    def get_default_prompt_set(self) -> Optional[Dict]:
        """Récupère l'ensemble de prompts par défaut."""
        cursor = self.conn.cursor()
        cursor.execute('SELECT * FROM ai_prompts WHERE is_default = 1 LIMIT 1')
        row = cursor.fetchone()
        return dict(row) if row else None
    
    def list_prompt_sets(self) -> List[Dict]:
        """Liste tous les ensembles de prompts."""
        cursor = self.conn.cursor()
        cursor.execute('SELECT * FROM ai_prompts ORDER BY is_default DESC, created_at DESC')
        return [dict(row) for row in cursor.fetchall()]
    
    def delete_prompt_set(self, prompt_set_id: int):
        """Supprime un ensemble de prompts."""
        cursor = self.conn.cursor()
        cursor.execute('DELETE FROM ai_prompts WHERE id = ?', (prompt_set_id,))
        self.conn.commit()
        logger.info(f"Ensemble de prompts {prompt_set_id} supprimé")
    
    def get_prompt_history(self, prompt_set_id: int) -> List[Dict]:
        """Récupère l'historique d'un ensemble de prompts."""
        cursor = self.conn.cursor()
        cursor.execute('''
            SELECT * FROM ai_prompts_history 
            WHERE prompt_set_id = ? 
            ORDER BY created_at DESC
        ''', (prompt_set_id,))
        return [dict(row) for row in cursor.fetchall()]
    
    def restore_prompt_set_from_history(self, history_id: int):
        """Restaure un ensemble de prompts depuis l'historique."""
        cursor = self.conn.cursor()
        
        # Récupérer l'entrée d'historique
        cursor.execute('SELECT * FROM ai_prompts_history WHERE id = ?', (history_id,))
        history_row = cursor.fetchone()
        if not history_row:
            raise ValueError(f"Entrée d'historique {history_id} introuvable")
        
        history = dict(history_row)
        prompt_set_id = history['prompt_set_id']
        
        # Restaurer les valeurs
        self.update_prompt_set(
            prompt_set_id,
            name=history['name'],
            system_prompt=history['system_prompt'],
            description_prompt=history['description_prompt'],
            google_category_prompt=history['google_category_prompt'],
            seo_prompt=history['seo_prompt']
        )
        
        logger.info(f"Ensemble de prompts {prompt_set_id} restauré depuis l'historique {history_id}")
    
    # ========== Gestion des imports CSV ==========
    
    def create_csv_import(self, file_path: str, total_rows: int) -> int:
        """Crée un nouvel import CSV."""
        cursor = self.conn.cursor()
        
        # Vérifier si l'import existe déjà
        cursor.execute('SELECT id FROM csv_imports WHERE original_file_path = ?', (file_path,))
        existing = cursor.fetchone()
        if existing:
            logger.info(f"Import CSV existant trouvé: {file_path} (ID: {existing['id']})")
            return existing['id']
        
        cursor.execute('''
            INSERT INTO csv_imports (original_file_path, total_rows)
            VALUES (?, ?)
        ''', (file_path, total_rows))
        
        self.conn.commit()
        import_id = cursor.lastrowid
        logger.info(f"Nouvel import CSV créé: {file_path} (ID: {import_id}, {total_rows} lignes)")
        return import_id
    
    def get_csv_import(self, import_id: int) -> Optional[Dict]:
        """Récupère un import CSV par son ID."""
        cursor = self.conn.cursor()
        cursor.execute('SELECT * FROM csv_imports WHERE id = ?', (import_id,))
        row = cursor.fetchone()
        return dict(row) if row else None
    
    def get_latest_csv_import(self) -> Optional[Dict]:
        """Récupère le dernier import CSV."""
        cursor = self.conn.cursor()
        cursor.execute('SELECT * FROM csv_imports ORDER BY imported_at DESC LIMIT 1')
        row = cursor.fetchone()
        return dict(row) if row else None
    
    # ========== Gestion des résultats de traitement ==========
    
    def save_processing_result(self, csv_import_id: int, output_path: str, prompt_set_id: int,
                               provider_name: str, model_name: str, handles: List[str],
                               fields: List[str]) -> int:
        """Sauvegarde un résultat de traitement."""
        cursor = self.conn.cursor()
        cursor.execute('''
            INSERT INTO csv_processing_results 
            (csv_import_id, output_csv_path, prompt_set_id, provider_name, model_name, 
             processed_handles, fields_processed)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (csv_import_id, output_path, prompt_set_id, provider_name, model_name,
              json.dumps(handles), json.dumps(fields)))
        
        self.conn.commit()
        result_id = cursor.lastrowid
        logger.info(f"Résultat de traitement sauvegardé (ID: {result_id})")
        return result_id
    
    def save_field_changes(self, processing_result_id: int, csv_row_id: int, handle: str,
                          field_name: str, original_value: str, new_value: str):
        """Sauvegarde un changement de champ."""
        cursor = self.conn.cursor()
        cursor.execute('''
            INSERT INTO product_field_changes 
            (processing_result_id, csv_row_id, handle, field_name, original_value, new_value)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (processing_result_id, csv_row_id, handle, field_name, original_value, new_value))
        self.conn.commit()
    
    def get_product_changes(self, handle: str, processing_result_id: Optional[int] = None) -> List[Dict]:
        """Récupère tous les changements pour un produit."""
        cursor = self.conn.cursor()
        
        if processing_result_id:
            cursor.execute('''
                SELECT * FROM product_field_changes 
                WHERE handle = ? AND processing_result_id = ?
                ORDER BY created_at
            ''', (handle, processing_result_id))
        else:
            cursor.execute('''
                SELECT * FROM product_field_changes 
                WHERE handle = ?
                ORDER BY created_at DESC
            ''', (handle,))
        
        return [dict(row) for row in cursor.fetchall()]
    
    # ========== Gestion des credentials AI ==========
    
    def save_ai_credentials(self, provider_name: str, api_key: str):
        """Sauvegarde ou met à jour les credentials AI."""
        cursor = self.conn.cursor()
        cursor.execute('''
            INSERT INTO ai_credentials (provider_name, api_key)
            VALUES (?, ?)
            ON CONFLICT(provider_name) DO UPDATE SET
                api_key = excluded.api_key,
                updated_at = CURRENT_TIMESTAMP
        ''', (provider_name, api_key))
        self.conn.commit()
        logger.debug(f"Credentials sauvegardés pour {provider_name}")
    
    def get_ai_credentials(self, provider_name: str) -> Optional[str]:
        """Récupère les credentials pour un fournisseur."""
        cursor = self.conn.cursor()
        cursor.execute('SELECT api_key FROM ai_credentials WHERE provider_name = ?', (provider_name,))
        row = cursor.fetchone()
        return row['api_key'] if row else None
    
    def delete_ai_credentials(self, provider_name: str):
        """Supprime les credentials d'un fournisseur."""
        cursor = self.conn.cursor()
        cursor.execute('DELETE FROM ai_credentials WHERE provider_name = ?', (provider_name,))
        self.conn.commit()
        logger.info(f"Credentials supprimés pour {provider_name}")
    
    def close(self):
        """Ferme la connexion à la base de données."""
        if self.conn:
            self.conn.close()
            self.conn = None
    
    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
