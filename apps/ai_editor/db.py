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
        
        # IMPORTANT: Activer les foreign keys (désactivées par défaut dans SQLite)
        self.conn.execute('PRAGMA foreign_keys = ON')
        
        cursor = self.conn.cursor()
        
        # Table des ensembles de prompts
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS ai_prompts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                system_prompt TEXT NOT NULL,
                seo_prompt TEXT NOT NULL,
                google_category_prompt TEXT NOT NULL,
                seo_system_prompt TEXT,
                google_shopping_system_prompt TEXT,
                is_default INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                last_used_at TIMESTAMP
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
                model_name TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Table de la taxonomie Google Shopping
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS google_taxonomy (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                code TEXT NOT NULL UNIQUE,
                path TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Table de configuration de l'application
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS app_config (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Index pour améliorer les performances
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_csv_rows_handle ON csv_rows(handle)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_csv_rows_import ON csv_rows(csv_import_id)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_field_changes_handle ON product_field_changes(handle)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_field_changes_result ON product_field_changes(processing_result_id)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_prompts_default ON ai_prompts(is_default)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_google_taxonomy_path ON google_taxonomy(path)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_google_taxonomy_code ON google_taxonomy(code)')
        
        # Migration: Ajouter la colonne model_name si elle n'existe pas
        cursor.execute("PRAGMA table_info(ai_credentials)")
        columns = [column[1] for column in cursor.fetchall()]
        if 'model_name' not in columns:
            logger.info("Migration: Ajout de la colonne model_name à ai_credentials")
            cursor.execute('ALTER TABLE ai_credentials ADD COLUMN model_name TEXT')
        
        self.conn.commit()
        logger.info(f"Base de données initialisée: {self.db_path}")
    
    # ========== Gestion des prompts ==========
    
    def create_prompt_set(self, name: str, system_prompt: str,
                          seo_prompt: str, google_category_prompt: str, 
                          seo_system_prompt: str = None, google_shopping_system_prompt: str = None,
                          is_default: bool = False) -> int:
        """Crée un nouvel ensemble de prompts avec prompts système séparés."""
        cursor = self.conn.cursor()
        
        # Si les prompts système séparés ne sont pas fournis, utiliser le system_prompt global
        if seo_system_prompt is None:
            seo_system_prompt = system_prompt
        if google_shopping_system_prompt is None:
            google_shopping_system_prompt = system_prompt
        
        # Si c'est le défaut, désactiver les autres défauts
        if is_default:
            cursor.execute('UPDATE ai_prompts SET is_default = 0')
        
        # Vérifier si la colonne description_prompt existe encore (ancienne structure)
        cursor.execute("PRAGMA table_info(ai_prompts)")
        columns = [column[1] for column in cursor.fetchall()]
        has_description_prompt = 'description_prompt' in columns
        
        if has_description_prompt:
            # Ancienne structure : inclure description_prompt avec une valeur vide
            cursor.execute('''
                INSERT INTO ai_prompts 
                (name, system_prompt, description_prompt, seo_prompt, google_category_prompt, 
                 seo_system_prompt, google_shopping_system_prompt, is_default)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ''', (name, system_prompt, '', seo_prompt, google_category_prompt, 
                  seo_system_prompt, google_shopping_system_prompt, 1 if is_default else 0))
        else:
            # Nouvelle structure : sans description_prompt
            cursor.execute('''
                INSERT INTO ai_prompts 
                (name, system_prompt, seo_prompt, google_category_prompt, 
                 seo_system_prompt, google_shopping_system_prompt, is_default)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (name, system_prompt, seo_prompt, google_category_prompt,
                  seo_system_prompt, google_shopping_system_prompt, 1 if is_default else 0))
        
        self.conn.commit()
        prompt_set_id = cursor.lastrowid
        logger.info(f"Nouvel ensemble de prompts créé: {name} (ID: {prompt_set_id})")
        return prompt_set_id
    
    def update_prompt_set(self, prompt_set_id: int, name: str = None, system_prompt: str = None,
                         seo_prompt: str = None, google_category_prompt: str = None,
                         seo_system_prompt: str = None, google_shopping_system_prompt: str = None,
                         is_default: bool = None):
        """Met à jour un ensemble de prompts avec prompts système séparés."""
        cursor = self.conn.cursor()
        
        # Récupérer la version actuelle pour l'historique
        current = self.get_prompt_set(prompt_set_id)
        if not current:
            raise ValueError(f"Ensemble de prompts {prompt_set_id} introuvable")
        
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
        if seo_prompt is not None:
            updates.append('seo_prompt = ?')
            params.append(seo_prompt)
        if google_category_prompt is not None:
            updates.append('google_category_prompt = ?')
            params.append(google_category_prompt)
        if seo_system_prompt is not None:
            updates.append('seo_system_prompt = ?')
            params.append(seo_system_prompt)
        if google_shopping_system_prompt is not None:
            updates.append('google_shopping_system_prompt = ?')
            params.append(google_shopping_system_prompt)
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
    
    def clear_all_imports(self):
        """
        Supprime tous les imports CSV et toutes les données associées.
        Cela inclut : csv_rows, csv_processing_results, product_field_changes, csv_imports.
        """
        cursor = self.conn.cursor()
        
        # Compter les imports existants
        cursor.execute('SELECT COUNT(*) as count FROM csv_imports')
        count = cursor.fetchone()['count']
        
        if count > 0:
            logger.info(f"Suppression de tous les imports CSV ({count} imports)...")
            
            # IMPORTANT: Supprimer dans l'ordre inverse des dépendances pour éviter les erreurs de foreign key
            # 1. Supprimer les changements de champs (dépend de csv_processing_results)
            cursor.execute('DELETE FROM product_field_changes')
            
            # 2. Supprimer les résultats de traitement (dépend de csv_imports)
            cursor.execute('DELETE FROM csv_processing_results')
            
            # 3. Supprimer les lignes CSV (dépend de csv_imports)
            cursor.execute('DELETE FROM csv_rows')
            
            # 4. Enfin, supprimer les imports
            cursor.execute('DELETE FROM csv_imports')
            
            self.conn.commit()
            logger.info("✅ Tous les imports et données associées ont été supprimés")
        else:
            logger.info("Aucun import à supprimer")
    
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
    
    def save_ai_credentials(self, provider_name: str, api_key: str, model_name: str = None):
        """Sauvegarde ou met à jour les credentials AI."""
        cursor = self.conn.cursor()
        cursor.execute('''
            INSERT INTO ai_credentials (provider_name, api_key, model_name)
            VALUES (?, ?, ?)
            ON CONFLICT(provider_name) DO UPDATE SET
                api_key = excluded.api_key,
                model_name = excluded.model_name,
                updated_at = CURRENT_TIMESTAMP
        ''', (provider_name, api_key, model_name))
        self.conn.commit()
        logger.debug(f"Credentials sauvegardés pour {provider_name}")
    
    def get_ai_credentials(self, provider_name: str) -> Optional[str]:
        """Récupère la clé API pour un fournisseur."""
        cursor = self.conn.cursor()
        cursor.execute('SELECT api_key FROM ai_credentials WHERE provider_name = ?', (provider_name,))
        row = cursor.fetchone()
        return row['api_key'] if row else None
    
    def get_ai_model(self, provider_name: str) -> Optional[str]:
        """Récupère le modèle sauvegardé pour un fournisseur."""
        cursor = self.conn.cursor()
        cursor.execute('SELECT model_name FROM ai_credentials WHERE provider_name = ?', (provider_name,))
        row = cursor.fetchone()
        return row['model_name'] if row else None
    
    def save_ai_model(self, provider_name: str, model_name: str):
        """Sauvegarde le modèle pour un fournisseur (crée l'entrée si nécessaire)."""
        cursor = self.conn.cursor()
        cursor.execute('''
            INSERT INTO ai_credentials (provider_name, api_key, model_name)
            VALUES (?, '', ?)
            ON CONFLICT(provider_name) DO UPDATE SET
                model_name = excluded.model_name,
                updated_at = CURRENT_TIMESTAMP
        ''', (provider_name, model_name))
        self.conn.commit()
        logger.debug(f"Modèle sauvegardé pour {provider_name}: {model_name}")
    
    def delete_ai_credentials(self, provider_name: str):
        """Supprime les credentials d'un fournisseur."""
        cursor = self.conn.cursor()
        cursor.execute('DELETE FROM ai_credentials WHERE provider_name = ?', (provider_name,))
        self.conn.commit()
        logger.info(f"Credentials supprimés pour {provider_name}")
    
    def get_last_used_provider(self) -> Optional[str]:
        """
        Récupère le nom du dernier provider utilisé (basé sur updated_at).
        
        Returns:
            Nom du provider (ex: "openai", "gemini", "claude") ou None si aucun
        """
        cursor = self.conn.cursor()
        cursor.execute('''
            SELECT provider_name FROM ai_credentials 
            WHERE api_key != ''
            ORDER BY updated_at DESC 
            LIMIT 1
        ''')
        row = cursor.fetchone()
        return row['provider_name'] if row else None
    
    def save_last_used_prompt_set(self, prompt_set_id: int):
        """
        Enregistre le dernier prompt set utilisé en mettant à jour last_used_at.
        
        Args:
            prompt_set_id: ID du prompt set utilisé
        """
        cursor = self.conn.cursor()
        
        # Ajouter la colonne si elle n'existe pas (migration automatique)
        try:
            cursor.execute('SELECT last_used_at FROM ai_prompts LIMIT 1')
        except sqlite3.OperationalError:
            cursor.execute('ALTER TABLE ai_prompts ADD COLUMN last_used_at TIMESTAMP')
            self.conn.commit()
            logger.info("Colonne last_used_at ajoutée à la table ai_prompts")
        
        # Mettre à jour le timestamp pour ce prompt set
        cursor.execute('''
            UPDATE ai_prompts 
            SET last_used_at = CURRENT_TIMESTAMP 
            WHERE id = ?
        ''', (prompt_set_id,))
        self.conn.commit()
        logger.debug(f"Prompt set {prompt_set_id} marqué comme dernier utilisé")
    
    def get_last_used_prompt_set(self) -> Optional[Dict]:
        """
        Récupère le dernier prompt set utilisé (basé sur last_used_at).
        
        Returns:
            Dict avec les données du prompt set ou None si aucun
        """
        cursor = self.conn.cursor()
        
        # Ajouter la colonne si elle n'existe pas (migration automatique)
        try:
            cursor.execute('''
                SELECT * FROM ai_prompts 
                WHERE last_used_at IS NOT NULL 
                ORDER BY last_used_at DESC 
                LIMIT 1
            ''')
            row = cursor.fetchone()
            return dict(row) if row else None
        except sqlite3.OperationalError:
            # Colonne n'existe pas encore, retourner None
            return None
    
    # ========== Gestion de la taxonomie Google Shopping ==========
    
    def import_google_taxonomy(self, file_path: str) -> int:
        """
        Importe la taxonomie Google Shopping depuis un fichier texte.
        
        Args:
            file_path: Chemin vers le fichier de taxonomie
            
        Returns:
            Nombre de catégories importées
        """
        cursor = self.conn.cursor()
        
        # Vider la table existante
        cursor.execute('DELETE FROM google_taxonomy')
        
        # Lire et importer le fichier
        count = 0
        with open(file_path, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                
                # Ignorer les commentaires et lignes vides
                if not line or line.startswith('#'):
                    continue
                
                # Format: "CODE - PATH"
                if ' - ' in line:
                    code, path = line.split(' - ', 1)
                    code = code.strip()
                    path = path.strip()
                    
                    cursor.execute('''
                        INSERT OR IGNORE INTO google_taxonomy (code, path)
                        VALUES (?, ?)
                    ''', (code, path))
                    count += 1
        
        self.conn.commit()
        logger.info(f"Taxonomie Google Shopping importée: {count} catégories")
        return count
    
    def search_google_category(self, search_text: str) -> Optional[str]:
        """
        Recherche un code de catégorie Google Shopping par texte.
        
        Stratégies de recherche (dans cet ordre):
        1. Correspondance exacte du chemin
        2. Correspondance partielle (LIKE)
        3. Recherche par mots-clés
        
        Args:
            search_text: Texte de recherche (chemin ou mots-clés)
            
        Returns:
            Code de la catégorie trouvée, ou None si non trouvé
        """
        cursor = self.conn.cursor()
        
        # Nettoyer le texte de recherche
        search_text = search_text.strip()
        
        # 1. Correspondance exacte
        cursor.execute('''
            SELECT code FROM google_taxonomy 
            WHERE path = ?
            LIMIT 1
        ''', (search_text,))
        result = cursor.fetchone()
        if result:
            logger.debug(f"Correspondance exacte trouvée pour '{search_text}': {result[0]}")
            return result[0]
        
        # 2. Correspondance partielle (LIKE)
        cursor.execute('''
            SELECT code, path FROM google_taxonomy 
            WHERE path LIKE ?
            ORDER BY LENGTH(path) ASC
            LIMIT 1
        ''', (f'%{search_text}%',))
        result = cursor.fetchone()
        if result:
            logger.debug(f"Correspondance partielle trouvée pour '{search_text}': {result[0]} ({result[1]})")
            return result[0]
        
        # 3. Recherche par mots-clés (tous les mots doivent être présents)
        words = search_text.lower().split()
        if words:
            query = "SELECT code, path FROM google_taxonomy WHERE "
            conditions = []
            params = []
            
            for word in words:
                if len(word) > 2:  # Ignorer les mots trop courts
                    conditions.append("LOWER(path) LIKE ?")
                    params.append(f'%{word}%')
            
            if conditions:
                query += " AND ".join(conditions)
                query += " ORDER BY LENGTH(path) ASC LIMIT 1"
                
                cursor.execute(query, params)
                result = cursor.fetchone()
                if result:
                    logger.debug(f"Correspondance par mots-clés trouvée pour '{search_text}': {result[0]} ({result[1]})")
                    return result[0]
        
        logger.warning(f"Aucune catégorie Google Shopping trouvée pour '{search_text}'")
        return None
    
    def get_taxonomy_count(self) -> int:
        """Retourne le nombre de catégories dans la taxonomie."""
        cursor = self.conn.cursor()
        cursor.execute('SELECT COUNT(*) FROM google_taxonomy')
        return cursor.fetchone()[0]
    
    # ========== Gestion de la configuration ==========
    
    def save_config(self, key: str, value: Any):
        """
        Sauvegarde une valeur de configuration.
        
        Args:
            key: Clé de configuration (ex: 'batch_size')
            value: Valeur à sauvegarder (sera convertie en string)
        """
        cursor = self.conn.cursor()
        value_str = str(value)
        
        cursor.execute('''
            INSERT INTO app_config (key, value, updated_at)
            VALUES (?, ?, CURRENT_TIMESTAMP)
            ON CONFLICT(key) DO UPDATE SET
                value = excluded.value,
                updated_at = CURRENT_TIMESTAMP
        ''', (key, value_str))
        
        self.conn.commit()
        logger.info(f"Configuration sauvegardée: {key} = {value}")
    
    def get_config(self, key: str, default: Any = None) -> Any:
        """
        Récupère une valeur de configuration.
        
        Args:
            key: Clé de configuration
            default: Valeur par défaut si la clé n'existe pas
            
        Returns:
            Valeur de configuration (string) ou default si non trouvée
        """
        cursor = self.conn.cursor()
        cursor.execute('SELECT value FROM app_config WHERE key = ?', (key,))
        result = cursor.fetchone()
        
        if result:
            return result[0]
        return default
    
    def get_config_int(self, key: str, default: int = 0) -> int:
        """
        Récupère une valeur de configuration et la convertit en int.
        
        Args:
            key: Clé de configuration
            default: Valeur par défaut si la clé n'existe pas
            
        Returns:
            Valeur de configuration en int
        """
        value = self.get_config(key)
        if value is None:
            return default
        
        try:
            return int(value)
        except (ValueError, TypeError):
            logger.warning(f"Impossible de convertir '{value}' en int pour {key}, utilisation de {default}")
            return default
    
    def get_config_bool(self, key: str, default: bool = False) -> bool:
        """
        Récupère une valeur de configuration et la convertit en bool.
        
        Args:
            key: Clé de configuration
            default: Valeur par défaut si la clé n'existe pas
            
        Returns:
            Valeur de configuration en bool
        """
        value = self.get_config(key)
        if value is None:
            return default
        
        return value.lower() in ('true', '1', 'yes', 'on')
    
    def close(self):
        """Ferme la connexion à la base de données."""
        if self.conn:
            self.conn.close()
            self.conn = None
    
    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
