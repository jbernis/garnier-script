#!/usr/bin/env python3
"""
Migration: Changer contrainte UNIQUE de type_category_mapping
De: UNIQUE(product_type, csv_type, category_code)
À: UNIQUE(product_type, csv_type)

Cela permet de mettre à jour la catégorie pour une même paire (product_type, csv_type).
"""

import sqlite3
import sys

def migrate_database(db_path: str):
    """Migrer la base de données."""
    print(f"Migration de {db_path}...")
    
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    try:
        # 1. Sauvegarder les données existantes
        print("1. Sauvegarde des données...")
        cursor.execute("SELECT * FROM type_category_mapping")
        existing_rules = cursor.fetchall()
        print(f"   {len(existing_rules)} règles à migrer")
        
        # 2. Supprimer l'ancienne table
        print("2. Suppression de l'ancienne table...")
        cursor.execute("DROP TABLE IF EXISTS type_category_mapping")
        
        # 3. Recréer avec nouvelle contrainte
        print("3. Création de la nouvelle table...")
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
                UNIQUE(product_type, csv_type)
            )
        ''')
        
        # 4. Restaurer les données (peut réduire le nombre si duplicatas)
        print("4. Restauration des données...")
        restored = 0
        skipped = 0
        
        for rule in existing_rules:
            try:
                cursor.execute('''
                    INSERT OR REPLACE INTO type_category_mapping
                    (product_type, csv_type, category_code, category_path, confidence, 
                     created_at, updated_at, use_count, created_by, is_active)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    rule['product_type'],
                    rule['csv_type'],
                    rule['category_code'],
                    rule['category_path'],
                    rule['confidence'],
                    rule['created_at'],
                    rule['updated_at'],
                    rule['use_count'],
                    rule['created_by'],
                    rule['is_active']
                ))
                restored += 1
            except Exception as e:
                print(f"   Erreur pour règle {rule['product_type']} + {rule['csv_type']}: {e}")
                skipped += 1
        
        conn.commit()
        print(f"   {restored} règles restaurées, {skipped} ignorées")
        print("✅ Migration terminée avec succès!")
        
    except Exception as e:
        conn.rollback()
        print(f"❌ Erreur lors de la migration: {e}")
        sys.exit(1)
    finally:
        conn.close()

if __name__ == '__main__':
    db_path = 'database/ai_prompts.db'
    migrate_database(db_path)
