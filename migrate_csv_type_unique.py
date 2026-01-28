#!/usr/bin/env python3
"""
Migration: Changer contrainte UNIQUE de type_category_mapping
De: UNIQUE(product_type, csv_type)
À: UNIQUE(csv_type)

Cela permet d'avoir une seule règle par csv_type, indépendamment du product_type.
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
                UNIQUE(csv_type)
            )
        ''')
        
        # 4. Restaurer les données (peut réduire si duplicatas csv_type)
        print("4. Restauration des données...")
        restored = 0
        skipped = 0
        
        # Grouper par csv_type et garder celle avec le plus de use_count
        csv_type_rules = {}
        for rule in existing_rules:
            csv_type = rule['csv_type']
            if csv_type not in csv_type_rules or rule['use_count'] > csv_type_rules[csv_type]['use_count']:
                csv_type_rules[csv_type] = rule
        
        print(f"   {len(csv_type_rules)} règles uniques par csv_type (sur {len(existing_rules)})")
        
        for csv_type, rule in csv_type_rules.items():
            try:
                cursor.execute('''
                    INSERT INTO type_category_mapping
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
                print(f"   Erreur pour règle {csv_type}: {e}")
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
