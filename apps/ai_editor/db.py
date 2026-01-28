"""
Module de gestion de la base de données SQLite pour l'éditeur IA.
"""

import sqlite3
import json
import logging
import sys
from typing import List, Dict, Optional, Any, Tuple
from datetime import datetime
from pathlib import Path

logger = logging.getLogger(__name__)

# Chemin par défaut de la base de données
def get_default_db_path():
    """Retourne le chemin de la base de données selon le mode (dev/packagé)."""
    if getattr(sys, "frozen", False):
        # Mode packagé : utiliser Application Support
        base_dir = Path.home() / "Library" / "Application Support" / "ScrapersShopify"
        db_path = base_dir / "database" / "ai_prompts.db"
        # Créer le répertoire si nécessaire
        db_path.parent.mkdir(parents=True, exist_ok=True)
        return str(db_path)
    else:
        # Mode développement
        return "database/ai_prompts.db"

DEFAULT_DB_PATH = get_default_db_path()


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
        
        # Table de cache pour les catégorisations Google Shopping
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS product_category_cache (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                product_key TEXT NOT NULL UNIQUE,
                title TEXT NOT NULL,
                product_type TEXT,
                vendor TEXT,
                category_code TEXT NOT NULL,
                category_path TEXT NOT NULL,
                original_category_code TEXT,
                original_category_path TEXT,
                confidence REAL NOT NULL,
                rationale TEXT,
                csv_type TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                last_used_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                use_count INTEGER DEFAULT 1
            )
        ''')
        
        # Table de mapping Type → Catégorie (règles prioritaires)
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS type_category_mapping (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                product_type TEXT NOT NULL,
                csv_type TEXT NOT NULL,
                category_code TEXT NOT NULL,
                category_path TEXT NOT NULL,
                confidence REAL DEFAULT 1.0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                use_count INTEGER DEFAULT 0,
                created_by TEXT DEFAULT 'manual',
                is_active BOOLEAN DEFAULT 1,
                UNIQUE(csv_type)
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
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_product_category_cache_key ON product_category_cache(product_key)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_type_mapping_type ON type_category_mapping(product_type)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_type_mapping_active ON type_category_mapping(is_active)')
        
        # Migration: Ajouter la colonne model_name si elle n'existe pas
        cursor.execute("PRAGMA table_info(ai_credentials)")
        columns = [column[1] for column in cursor.fetchall()]
        if 'model_name' not in columns:
            logger.info("Migration: Ajout de la colonne model_name à ai_credentials")
            cursor.execute('ALTER TABLE ai_credentials ADD COLUMN model_name TEXT')
        
        # Migration: Ajouter csv_type à type_category_mapping si elle n'existe pas
        cursor.execute("PRAGMA table_info(type_category_mapping)")
        mapping_columns = [column[1] for column in cursor.fetchall()]
        if 'csv_type' not in mapping_columns:
            logger.info("Migration: Ajout de la colonne csv_type à type_category_mapping")
            try:
                # Sauvegarder les données existantes
                cursor.execute("""
                    CREATE TABLE type_category_mapping_backup AS
                    SELECT * FROM type_category_mapping
                """)
                
                # Supprimer l'ancienne table
                cursor.execute("DROP TABLE type_category_mapping")
                
                # Recréer avec csv_type
                cursor.execute('''
                    CREATE TABLE type_category_mapping (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        product_type TEXT NOT NULL,
                        csv_type TEXT NOT NULL,
                        category_code TEXT NOT NULL,
                        category_path TEXT NOT NULL,
                        confidence REAL DEFAULT 1.0,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        use_count INTEGER DEFAULT 0,
                        created_by TEXT DEFAULT 'manual',
                        is_active BOOLEAN DEFAULT 1,
                        UNIQUE(csv_type)
                    )
                ''')
                
                # Migrer les données : csv_type = product_type pour les règles existantes
                cursor.execute("""
                    INSERT INTO type_category_mapping 
                    (product_type, csv_type, category_code, category_path, confidence,
                     created_at, updated_at, use_count, created_by, is_active)
                    SELECT product_type, product_type as csv_type, category_code, category_path, confidence,
                           created_at, updated_at, use_count, created_by, is_active
                    FROM type_category_mapping_backup
                """)
                
                # Supprimer la table de backup
                cursor.execute("DROP TABLE type_category_mapping_backup")
                
                logger.info("Migration: Colonne csv_type ajoutée avec succès")
            except Exception as e:
                logger.error(f"Erreur lors de la migration csv_type: {e}")
                # Restaurer la table de backup en cas d'erreur
                try:
                    cursor.execute("DROP TABLE IF EXISTS type_category_mapping")
                    cursor.execute("ALTER TABLE type_category_mapping_backup RENAME TO type_category_mapping")
                except:
                    pass
                raise
        
        # Créer l'index sur csv_type seulement si la colonne existe
        cursor.execute("PRAGMA table_info(type_category_mapping)")
        mapping_columns_after = [column[1] for column in cursor.fetchall()]
        if 'csv_type' in mapping_columns_after:
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_type_mapping_csv_type ON type_category_mapping(csv_type)')
        
        # Migration: Ajouter les nouvelles colonnes à product_category_cache si elles n'existent pas
        cursor.execute("PRAGMA table_info(product_category_cache)")
        cache_columns = [column[1] for column in cursor.fetchall()]
        
        if 'original_category_code' not in cache_columns:
            logger.info("Migration: Ajout de la colonne original_category_code à product_category_cache")
            cursor.execute('ALTER TABLE product_category_cache ADD COLUMN original_category_code TEXT')
        
        if 'original_category_path' not in cache_columns:
            logger.info("Migration: Ajout de la colonne original_category_path à product_category_cache")
            cursor.execute('ALTER TABLE product_category_cache ADD COLUMN original_category_path TEXT')
        
        if 'csv_type' not in cache_columns:
            logger.info("Migration: Ajout de la colonne csv_type à product_category_cache")
            cursor.execute('ALTER TABLE product_category_cache ADD COLUMN csv_type TEXT')
        
        if 'source' not in cache_columns:
            logger.info("Migration: Ajout de la colonne source à product_category_cache")
            cursor.execute('ALTER TABLE product_category_cache ADD COLUMN source TEXT DEFAULT "langgraph"')
        
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
    
    def get_all_csv_imports(self) -> List[Dict]:
        """Récupère tous les imports CSV avec leurs informations de traitement."""
        cursor = self.conn.cursor()
        cursor.execute('''
            SELECT 
                ci.id,
                ci.original_file_path,
                ci.imported_at,
                ci.total_rows,
                COUNT(DISTINCT cr.handle) as unique_products,
                COUNT(DISTINCT cpr.id) as processing_count,
                MAX(cpr.created_at) as last_processed_at
            FROM csv_imports ci
            LEFT JOIN csv_rows cr ON ci.id = cr.csv_import_id
            LEFT JOIN csv_processing_results cpr ON ci.id = cpr.csv_import_id
            GROUP BY ci.id
            ORDER BY ci.imported_at DESC
        ''')
        rows = cursor.fetchall()
        return [dict(row) for row in rows]
    
    def get_processing_results_for_import(self, csv_import_id: int) -> List[Dict]:
        """Récupère tous les résultats de traitement pour un import donné."""
        cursor = self.conn.cursor()
        cursor.execute('''
            SELECT 
                cpr.*,
                ap.name as prompt_set_name
            FROM csv_processing_results cpr
            LEFT JOIN ai_prompts ap ON cpr.prompt_set_id = ap.id
            WHERE cpr.csv_import_id = ?
            ORDER BY cpr.created_at DESC
        ''', (csv_import_id,))
        rows = cursor.fetchall()
        return [dict(row) for row in rows]
    
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
        
        # Vérifier que search_text n'est pas None ou vide
        if not search_text:
            logger.warning(f"search_google_category appelé avec search_text vide ou None")
            return None
        
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
    
    def find_closest_category_fuzzy(self, search_text: str, min_similarity: float = 0.6) -> Optional[Tuple[str, str, float]]:
        """
        Trouve la catégorie la plus proche par similarité de texte (fuzzy matching).
        
        Args:
            search_text: Texte de recherche
            min_similarity: Similarité minimale (0.0 à 1.0), défaut 0.6
            
        Returns:
            Tuple (code, path, similarity_score) ou None si aucune catégorie assez proche
        """
        from difflib import SequenceMatcher
        
        cursor = self.conn.cursor()
        cursor.execute('SELECT code, path FROM google_taxonomy')
        all_categories = cursor.fetchall()
        
        search_lower = search_text.lower()
        best_match = None
        best_score = 0.0
        
        for code, path in all_categories:
            # Calculer la similarité
            path_lower = path.lower()
            similarity = SequenceMatcher(None, search_lower, path_lower).ratio()
            
            # Bonus si les mots principaux correspondent
            search_words = set(search_lower.split(' > ')[-1].split())  # Dernière partie de la catégorie
            path_words = set(path_lower.split(' > ')[-1].split())
            word_overlap = len(search_words & path_words) / max(len(search_words), 1)
            
            # Score combiné (70% similarité texte, 30% mots communs)
            combined_score = (similarity * 0.7) + (word_overlap * 0.3)
            
            if combined_score > best_score:
                best_score = combined_score
                best_match = (code, path, combined_score)
        
        if best_match and best_score >= min_similarity:
            logger.info(f"🔍 Fuzzy match: '{search_text}' → '{best_match[1]}' (score: {best_score:.2f})")
            return best_match
        
        logger.info(f"❌ Aucun fuzzy match trouvé pour '{search_text}' (meilleur score: {best_score:.2f})")
        return None
    
    def get_candidate_categories(self, product_data: Dict[str, Any], max_results: int = 30) -> List[Tuple[str, str]]:
        """
        Extrait des catégories candidates de la taxonomie basées sur les mots-clés du produit.
        
        Args:
            product_data: Données du produit (Title, Type, Vendor, etc.)
            max_results: Nombre maximum de catégories à retourner
            
        Returns:
            Liste de tuples (code, path) des catégories candidates
        """
        # Si keywords enrichis fournis (par LangGraph), les utiliser en priorité
        if '_enriched_keywords' in product_data:
            enriched_keywords = product_data['_enriched_keywords']
            keywords_list = [kw.strip().lower() for kw in enriched_keywords.split() if len(kw.strip()) > 2]
            keywords = set(keywords_list[:8])  # Limiter à 8
            logger.info(f"🔑 Utilisation des keywords enrichis LangGraph: {keywords}")
        else:
            # Extraire les mots-clés du produit de manière standard
            title = product_data.get('Title', '').lower()
            product_type = product_data.get('Type', '').lower()
            
            # Liste de stop words à ignorer (optimisé)
            stop_words = {'pour', 'avec', 'sans', 'tout', 'tous', 'dans', 'cette', 'entre', 'plus'}
            
            # Mots-clés à chercher (filtrer les mots courts, communs et chiffres)
            keywords = set()
            for text in [title, product_type]:
                words = text.split()
                # Filtrer: longueur > 3, pas de chiffres, pas dans stop_words
                keywords.update([
                    w for w in words 
                    if len(w) > 3 
                    and w not in stop_words
                    and not w.replace('cm', '').replace('mm', '').isdigit()  # Ignorer dimensions
                ])
            
            # Limiter à 8 mots-clés max pour optimiser la requête SQL
            if len(keywords) > 8:
                # Prioriser les mots du Type (plus pertinents)
                type_words = set(w for w in product_type.split() if len(w) > 3)
                keywords = type_words.union(list(keywords - type_words)[:8-len(type_words)])
        
        if not keywords:
            logger.warning("Aucun mot-clé extrait du produit pour recherche de catégories")
            return []
        
        cursor = self.conn.cursor()
        
        # Requête pour trouver les catégories contenant ces mots-clés
        # On score chaque catégorie par:
        # - Nombre de mots-clés trouvés * 10
        # - BONUS +100 pour "Maison et jardin" et "Aliments, boissons et tabac" (90% des produits)
        # - BONUS +50 pour spécificité (nombre de niveaux > dans le path)
        # EXCLUSION: Catégories "Entreprise et industrie" + catégories trop générales (< 3 niveaux)
        query = """
            SELECT code, path, 
                   (""" + " + ".join([f"(LOWER(path) LIKE ?) * 10" for _ in keywords]) + """) 
                   + CASE 
                       WHEN LOWER(path) LIKE 'maison et jardin%' THEN 100
                       WHEN LOWER(path) LIKE 'aliments, boissons et tabac%' THEN 100
                       ELSE 0
                   END
                   + (LENGTH(path) - LENGTH(REPLACE(path, '>', ''))) * 5
                   as score
            FROM google_taxonomy
            WHERE (""" + " OR ".join([f"LOWER(path) LIKE ?" for _ in keywords]) + """)
            AND LOWER(path) NOT LIKE 'entreprise et industrie%'
            AND (LENGTH(path) - LENGTH(REPLACE(path, '>', ''))) >= 2
            ORDER BY score DESC, LENGTH(path) DESC
            LIMIT ?
        """
        
        # Préparer les paramètres (%mot% pour chaque mot-clé, deux fois)
        params = []
        for keyword in keywords:
            params.append(f'%{keyword}%')
        for keyword in keywords:
            params.append(f'%{keyword}%')
        params.append(max_results)
        
        cursor.execute(query, params)
        results = cursor.fetchall()
        
        # Retourner seulement code et path (sans score)
        candidates = [(row[0], row[1]) for row in results]
        
        logger.info(f"📋 {len(candidates)} catégories candidates trouvées pour: {', '.join(list(keywords)[:5])}")
        logger.debug(f"Catégories candidates (top 5): {[path for _, path in candidates[:5]]}")
        return candidates
    
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
    
    # ============================================================================
    # CACHE DE CATÉGORISATION GOOGLE SHOPPING
    # ============================================================================
    
    def _generate_product_key(self, product_data: dict) -> str:
        """
        Génère une clé unique pour un produit basée sur Title, Type, Vendor.
        
        Args:
            product_data: Données du produit
            
        Returns:
            Clé unique (hash)
        """
        import hashlib
        
        title = product_data.get('Title', '').strip().lower()
        product_type = product_data.get('Type', '').strip().lower()
        vendor = product_data.get('Vendor', '').strip().lower()
        
        # Créer une clé composite
        key_string = f"{title}|{product_type}|{vendor}"
        
        # Hasher pour avoir une clé courte et unique
        return hashlib.md5(key_string.encode('utf-8')).hexdigest()
    
    def get_cached_category(self, product_data: dict) -> Optional[Dict[str, Any]]:
        """
        Récupère la catégorie depuis le cache si elle existe.
        
        Args:
            product_data: Données du produit
            
        Returns:
            Dict avec category_code, category_path, confidence, rationale ou None
        """
        product_key = self._generate_product_key(product_data)
        
        cursor = self.conn.cursor()
        cursor.execute('''
            SELECT category_code, category_path, confidence, rationale
            FROM product_category_cache
            WHERE product_key = ?
        ''', (product_key,))
        
        result = cursor.fetchone()
        
        if result:
            # Mettre à jour last_used_at et use_count
            cursor.execute('''
                UPDATE product_category_cache
                SET last_used_at = CURRENT_TIMESTAMP,
                    use_count = use_count + 1
                WHERE product_key = ?
            ''', (product_key,))
            self.conn.commit()
            
            logger.info(f"✅ Cache HIT: {product_data.get('Title', 'N/A')[:50]} → {result['category_path']}")
            
            return {
                'category_code': result['category_code'],
                'category_path': result['category_path'],
                'confidence': result['confidence'],
                'rationale': result['rationale']
            }
        
        logger.debug(f"❌ Cache MISS: {product_data.get('Title', 'N/A')[:50]}")
        return None
    
    def save_to_cache(
        self, 
        product_data: dict, 
        category_code: str, 
        category_path: str, 
        confidence: float, 
        rationale: str,
        original_category_code: str = None,
        original_category_path: str = None,
        force_save: bool = False,
        source: str = 'langgraph',
        csv_type: Optional[str] = None
    ) -> bool:
        """
        Sauvegarde une catégorisation dans le cache.
        
        Args:
            product_data: Données du produit
            category_code: Code de la catégorie Google (finale)
            category_path: Chemin complet de la catégorie (finale)
            confidence: Niveau de confiance (0-1)
            rationale: Justification
            original_category_code: Code original du LLM (avant fallback parent)
            original_category_path: Chemin original du LLM (avant fallback parent)
            force_save: Si True, sauvegarde même si confidence basse (défaut: False pour rétrocompatibilité)
            source: Source de la catégorisation ('type_mapping', 'cache', 'langgraph', 'seo')
            csv_type: Type suggéré par SEO (si None, utilise Type du CSV)
            
        Returns:
            True si sauvegardé, False sinon
        """
        product_key = self._generate_product_key(product_data)
        title = product_data.get('Title', '')
        vendor = product_data.get('Vendor', '')
        
        # product_type = Type original du CSV (JAMAIS modifié)
        product_type = product_data.get('Type', '').strip()
        
        # csv_type = Type suggéré par SEO (si fourni), sinon Type du CSV
        if csv_type is None:
            csv_type = product_type
        else:
            csv_type = csv_type.strip()
        
        cursor = self.conn.cursor()
        
        # Vérifier si le produit existe déjà dans le cache
        cursor.execute('SELECT product_type, csv_type FROM product_category_cache WHERE product_key = ?', (product_key,))
        existing = cursor.fetchone()
        
        # IMPORTANT: product_type doit TOUJOURS rester le type original du CSV
        # Si une entrée existe déjà, préserver son product_type original
        if existing and existing['product_type']:
            # Ne jamais modifier product_type, il reste toujours l'original du CSV
            product_type = existing['product_type']
        
        # IMPORTANT: csv_type doit être préservé s'il existe déjà (généré par SEO)
        # Ne pas l'écraser avec product_type si csv_type non fourni en paramètre
        if existing and existing['csv_type'] and csv_type == product_type:
            # Si csv_type existe déjà ET qu'on essaie de le remplacer par product_type (fallback)
            # alors on garde l'existant (csv_type généré par SEO)
            csv_type = existing['csv_type']
        
        try:
            cursor.execute('''
                INSERT OR REPLACE INTO product_category_cache 
                (product_key, title, product_type, vendor, category_code, category_path, 
                 original_category_code, original_category_path, confidence, rationale, csv_type, source)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (product_key, title, product_type, vendor, category_code, category_path, 
                  original_category_code, original_category_path, confidence, rationale, csv_type, source))
            
            self.conn.commit()
            logger.info(f"💾 Taxonomie SAVED: {title[:50]} → {category_path} (conf: {confidence:.2f}, csv_type: {csv_type})")
            return True
            
        except Exception as e:
            logger.error(f"Erreur lors de la sauvegarde dans le cache: {e}")
            return False
    
    def get_parent_category(self, category_path: str) -> Optional[Tuple[str, str]]:
        """
        Obtient la catégorie parente (niveau supérieur) d'une catégorie.
        
        Args:
            category_path: Chemin complet (ex: "Maison et jardin > Linge > Literie > Couvertures")
            
        Returns:
            (code, path) de la catégorie parente, ou None
        """
        # Découper le chemin
        parts = [p.strip() for p in category_path.split('>')]
        
        # Si déjà au niveau racine, retourner None
        if len(parts) <= 1:
            return None
        
        # Construire le chemin parent (enlever le dernier niveau)
        parent_path = ' > '.join(parts[:-1])
        
        # Chercher dans la taxonomie
        cursor = self.conn.cursor()
        cursor.execute('''
            SELECT code, path FROM google_taxonomy
            WHERE path = ?
            LIMIT 1
        ''', (parent_path,))
        
        result = cursor.fetchone()
        
        if result:
            logger.info(f"📊 Catégorie parent: {category_path} → {result['path']}")
            return (result['code'], result['path'])
        
        logger.warning(f"⚠️ Catégorie parent non trouvée pour: {category_path}")
        return None
    
    def get_cache_stats(self) -> Dict[str, int]:
        """
        Obtient des statistiques sur le cache.
        
        Returns:
            Dict avec total_entries, avg_confidence, most_used
        """
        cursor = self.conn.cursor()
        
        cursor.execute('''
            SELECT 
                COUNT(*) as total,
                AVG(confidence) as avg_conf,
                MAX(use_count) as max_uses
            FROM product_category_cache
        ''')
        
        result = cursor.fetchone()
        
        return {
            'total_entries': result['total'] or 0,
            'avg_confidence': result['avg_conf'] or 0.0,
            'max_uses': result['max_uses'] or 0
        }
    
    
    def delete_taxonomy_cache(self, cache_id: int) -> bool:
        """
        Supprime une entrée du cache de taxonomie.
        
        Args:
            cache_id: ID de l'entrée à supprimer
            
        Returns:
            True si succès, False sinon
        """
        cursor = self.conn.cursor()
        
        try:
            cursor.execute('DELETE FROM product_category_cache WHERE id = ?', (cache_id,))
            self.conn.commit()
            logger.info(f"🗑️ Entrée taxonomie supprimée: ID {cache_id}")
            return True
            
        except Exception as e:
            logger.error(f"Erreur lors de la suppression: {e}")
            return False
    
    # ========== Gestion du Type Mapping (règles Type → Catégorie) ==========
    
    def get_type_mapping(self, product_type: str, csv_type: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """
        Récupère la règle de mapping basée uniquement sur csv_type.
        
        Args:
            product_type: Type original du CSV (utilisé pour logging uniquement)
            csv_type: Type suggéré par SEO (ex: "TORCHONS") - CLÉ DE RECHERCHE
            
        Returns:
            Dict avec category_code, category_path, confidence ou None
        """
        if not csv_type or csv_type.strip() == '':
            return None
        
        # Normaliser en UPPERCASE pour éviter les doublons (Thés, THÉS, thés, etc.)
        csv_type_normalized = csv_type.strip().upper()
        
        cursor = self.conn.cursor()
        
        # Chercher uniquement par csv_type (insensible à la casse via UPPER)
        # Prioriser : 1) Plus utilisée (use_count), 2) Plus récente (created_at), 3) Plus confiante
        cursor.execute('''
            SELECT id, category_code, category_path, confidence, use_count, product_type
            FROM type_category_mapping
            WHERE UPPER(csv_type) = ? AND is_active = 1
            AND category_code != '' AND category_path != ''
            ORDER BY use_count DESC, created_at DESC, confidence DESC
            LIMIT 1
        ''', (csv_type_normalized,))
        
        result = cursor.fetchone()
        
        if result:
            # Incrémenter le compteur d'utilisation
            cursor.execute('''
                UPDATE type_category_mapping
                SET use_count = use_count + 1,
                    updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
            ''', (result['id'],))
            self.conn.commit()
            
            logger.info(f"✅ Règle trouvée: {csv_type} → {result['category_path']}")
            
            return {
                'category_code': result['category_code'],
                'category_path': result['category_path'],
                'confidence': result['confidence'],
                'use_count': result['use_count'] + 1
            }
        
        return None
    
    def save_type_mapping(self, product_type: str, csv_type: str, category_code: str, 
                         category_path: str, confidence: float = 1.0,
                         created_by: str = 'manual', force_update: bool = False) -> bool:
        """
        Sauvegarde ou met à jour une règle de mapping.
        Protège les règles à confiance >= seuil configurable contre les modifications automatiques.
        
        Args:
            product_type: Type original du CSV (ex: "table")
            csv_type: Type suggéré par SEO (ex: "NAPPES")
            category_code: Code Google Shopping
            category_path: Chemin complet de la catégorie
            confidence: Niveau de confiance (défaut 1.0 pour règles manuelles)
            created_by: 'manual' ou 'auto_suggestion' ou 'llm_google_shopping'
            force_update: Si True, permet la modification même des règles protégées (pour modifications manuelles)
            
        Returns:
            True si succès, False si protégé ou erreur
        """
        # Récupérer le seuil depuis la configuration (par défaut 90%)
        confidence_threshold_percent = self.get_config_int('confidence_threshold', default=90)
        HIGH_CONFIDENCE_THRESHOLD = confidence_threshold_percent / 100.0  # Convertir en 0.0-1.0
        
        # Normaliser csv_type en UPPERCASE pour éviter les doublons
        csv_type_normalized = csv_type.strip().upper()
        
        cursor = self.conn.cursor()
        
        # Vérifier si une règle existe déjà avec product_type + csv_type
        cursor.execute('''
            SELECT id, confidence FROM type_category_mapping
            WHERE product_type = ? AND UPPER(csv_type) = ? AND category_code = ?
        ''', (product_type.strip(), csv_type_normalized, category_code))
        
        existing = cursor.fetchone()
        
        # Protection: Si règle existe avec confiance >= 0.9, ne pas modifier automatiquement
        if existing and existing['confidence'] >= HIGH_CONFIDENCE_THRESHOLD and not force_update:
            logger.warning(f"🔒 Règle protégée (confiance {existing['confidence']:.2f} >= {HIGH_CONFIDENCE_THRESHOLD}): {product_type} + {csv_type_normalized} → non modifiée")
            return False
        
        try:
            # Créer ou mettre à jour la règle (TOUJOURS en UPPERCASE)
            cursor.execute('''
                INSERT OR REPLACE INTO type_category_mapping 
                (product_type, csv_type, category_code, category_path, confidence, 
                 created_by, updated_at, is_active)
                VALUES (?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP, 1)
            ''', (product_type.strip(), csv_type_normalized, category_code, category_path, confidence, created_by))
            
            self.conn.commit()
            logger.info(f"💾 Type Mapping SAVED: {product_type} + {csv_type_normalized} → {category_path}")
            return True
            
        except Exception as e:
            logger.error(f"Erreur lors de la sauvegarde du mapping: {e}")
            return False
    
    def get_all_type_mappings(self) -> List[Dict[str, Any]]:
        """
        Récupère toutes les règles de mapping actives.
        
        Returns:
            Liste de règles avec tous les champs (incluant product_type et csv_type)
        """
        cursor = self.conn.cursor()
        cursor.execute('''
            SELECT id, product_type, csv_type, category_code, category_path, 
                   confidence, use_count, created_by, created_at, is_active
            FROM type_category_mapping
            ORDER BY use_count DESC, product_type ASC, csv_type ASC
        ''')
        
        return [dict(row) for row in cursor.fetchall()]
    
    def update_type_mapping(self, mapping_id: int, category_code: str, 
                           category_path: str, csv_type: Optional[str] = None, 
                           force_update: bool = False) -> bool:
        """
        Met à jour une règle de mapping existante.
        Protège les règles à confiance >= seuil configurable contre les modifications automatiques.
        
        Args:
            mapping_id: ID de la règle à modifier
            category_code: Nouveau code Google Shopping
            category_path: Nouveau chemin complet de la catégorie
            csv_type: Nouveau csv_type (optionnel)
            force_update: Si True, permet la modification même des règles protégées (pour modifications manuelles)
            
        Returns:
            True si succès, False si protégé ou erreur
        """
        # Récupérer le seuil depuis la configuration (par défaut 90%)
        confidence_threshold_percent = self.get_config_int('confidence_threshold', default=90)
        HIGH_CONFIDENCE_THRESHOLD = confidence_threshold_percent / 100.0  # Convertir en 0.0-1.0
        
        try:
            cursor = self.conn.cursor()
            
            # Vérifier la confiance de la règle existante
            cursor.execute('''
                SELECT confidence, csv_type FROM type_category_mapping
                WHERE id = ?
            ''', (mapping_id,))
            
            existing = cursor.fetchone()
            
            if not existing:
                logger.error(f"Règle ID {mapping_id} non trouvée")
                return False
            
            # Protection: Si confiance >= 0.9, ne pas modifier automatiquement
            if existing['confidence'] >= HIGH_CONFIDENCE_THRESHOLD and not force_update:
                logger.warning(f"🔒 Règle protégée (confiance {existing['confidence']:.2f} >= {HIGH_CONFIDENCE_THRESHOLD}): ID {mapping_id} → non modifiée")
                return False
            
            # Mettre à jour la règle
            if csv_type:
                cursor.execute('''
                    UPDATE type_category_mapping
                    SET csv_type = ?,
                        category_code = ?,
                        category_path = ?,
                        updated_at = CURRENT_TIMESTAMP
                    WHERE id = ?
                ''', (csv_type, category_code, category_path, mapping_id))
            else:
                cursor.execute('''
                    UPDATE type_category_mapping
                    SET category_code = ?,
                        category_path = ?,
                        updated_at = CURRENT_TIMESTAMP
                    WHERE id = ?
                ''', (category_code, category_path, mapping_id))
            
            self.conn.commit()
            logger.info(f"✏️ Type Mapping modifié: ID {mapping_id} → {category_path}")
            return True
            
        except Exception as e:
            logger.error(f"Erreur lors de la modification: {e}")
            return False
    
    def delete_type_mapping(self, mapping_id: int) -> bool:
        """
        Supprime une règle de mapping.
        
        Args:
            mapping_id: ID de la règle à supprimer
            
        Returns:
            True si succès
        """
        try:
            cursor = self.conn.cursor()
            cursor.execute('DELETE FROM type_category_mapping WHERE id = ?', (mapping_id,))
            self.conn.commit()
            logger.info(f"🗑️ Type Mapping supprimé: ID {mapping_id}")
            return True
            
        except Exception as e:
            logger.error(f"Erreur lors de la suppression: {e}")
            return False
    
    def toggle_type_mapping(self, mapping_id: int, is_active: bool) -> bool:
        """
        Active/désactive une règle de mapping.
        
        Args:
            mapping_id: ID de la règle
            is_active: True pour activer, False pour désactiver
            
        Returns:
            True si succès
        """
        try:
            cursor = self.conn.cursor()
            cursor.execute('''
                UPDATE type_category_mapping
                SET is_active = ?, updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
            ''', (1 if is_active else 0, mapping_id))
            self.conn.commit()
            logger.info(f"🔄 Type Mapping {'activé' if is_active else 'désactivé'}: ID {mapping_id}")
            return True
            
        except Exception as e:
            logger.error(f"Erreur lors du toggle: {e}")
            return False
    
    def close(self):
        """Ferme la connexion à la base de données."""
        if self.conn:
            self.conn.close()
            self.conn = None
    
    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
