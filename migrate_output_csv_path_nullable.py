#!/usr/bin/env python3
"""
Migration pour rendre output_csv_path nullable dans csv_processing_results
"""

import sqlite3
import sys
from pathlib import Path


def migrate():
    db_path = Path(__file__).parent / "database" / "ai_prompts.db"
    
    if not db_path.exists():
        print(f"❌ Erreur: Base de données introuvable: {db_path}")
        sys.exit(1)
    
    print("Migration: Rendre output_csv_path nullable")
    
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # 1. Créer la nouvelle table avec output_csv_path nullable
        cursor.execute('''
            CREATE TABLE csv_processing_results_new (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                csv_import_id INTEGER NOT NULL,
                output_csv_path TEXT,
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
        
        # 2. Copier les données
        cursor.execute('''
            INSERT INTO csv_processing_results_new 
            SELECT * FROM csv_processing_results
        ''')
        
        # 3. Supprimer l'ancienne table
        cursor.execute('DROP TABLE csv_processing_results')
        
        # 4. Renommer la nouvelle table
        cursor.execute('ALTER TABLE csv_processing_results_new RENAME TO csv_processing_results')
        
        conn.commit()
        print("✅ Migration terminée")
        
        conn.close()
        
    except Exception as e:
        print(f"❌ Erreur lors de la migration: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    migrate()
