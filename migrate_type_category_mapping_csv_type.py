#!/usr/bin/env python3
"""
Script de migration pour ajouter csv_type à type_category_mapping et modifier la contrainte UNIQUE.
"""

import sqlite3
from pathlib import Path

DB_PATH = "database/ai_prompts.db"

def migrate():
    """Migre le schéma de type_category_mapping pour ajouter csv_type."""
    print("🔄 Migration du schéma de type_category_mapping...")
    print(f"   Base: {DB_PATH}")
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Vérifier si la colonne csv_type existe déjà
    cursor.execute("PRAGMA table_info(type_category_mapping)")
    columns = [column[1] for column in cursor.fetchall()]
    
    if 'csv_type' in columns:
        print("\n✓ Colonne 'csv_type' déjà existante - migration déjà effectuée")
        conn.close()
        return
    
    print("\n1. Sauvegarde des données existantes...")
    # Récupérer toutes les données existantes
    cursor.execute("""
        SELECT id, product_type, category_code, category_path, confidence,
               created_at, updated_at, use_count, created_by, is_active
        FROM type_category_mapping
    """)
    existing_data = cursor.fetchall()
    print(f"   ✓ {len(existing_data)} règle(s) trouvée(s)")
    
    print("\n2. Recréation de la table avec le nouveau schéma...")
    # Supprimer l'ancienne table
    cursor.execute("DROP TABLE IF EXISTS type_category_mapping_old")
    cursor.execute("""
        CREATE TABLE type_category_mapping_old AS
        SELECT * FROM type_category_mapping
    """)
    
    # Supprimer l'ancienne table
    cursor.execute("DROP TABLE type_category_mapping")
    
    # Créer la nouvelle table avec csv_type et contrainte UNIQUE composite
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
            UNIQUE(product_type, csv_type, category_code)
        )
    ''')
    
    print("   ✓ Table recréée avec csv_type et contrainte UNIQUE composite")
    
    print("\n3. Migration des données existantes...")
    # Migrer les données : csv_type = product_type pour les règles existantes
    migrated_count = 0
    for row in existing_data:
        (id_val, product_type, category_code, category_path, confidence,
         created_at, updated_at, use_count, created_by, is_active) = row
        
        # Pour les règles existantes, csv_type = product_type
        csv_type = product_type
        
        cursor.execute('''
            INSERT INTO type_category_mapping 
            (product_type, csv_type, category_code, category_path, confidence,
             created_at, updated_at, use_count, created_by, is_active)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (product_type, csv_type, category_code, category_path, confidence,
              created_at, updated_at, use_count, created_by, is_active))
        migrated_count += 1
    
    print(f"   ✓ {migrated_count} règle(s) migrée(s)")
    
    # Supprimer la table temporaire
    cursor.execute("DROP TABLE type_category_mapping_old")
    
    # Recréer les index
    print("\n4. Recréation des index...")
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_type_mapping_type ON type_category_mapping(product_type)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_type_mapping_csv_type ON type_category_mapping(csv_type)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_type_mapping_active ON type_category_mapping(is_active)')
    print("   ✓ Index recréés")
    
    # Commit et fermeture
    conn.commit()
    conn.close()
    
    print("\n✅ Migration terminée avec succès!")
    print("\nℹ️  Modifications effectuées:")
    print("   - Colonne 'csv_type' ajoutée")
    print("   - Contrainte UNIQUE modifiée: (product_type, csv_type, category_code)")
    print("   - Pour les règles existantes: csv_type = product_type")
    print("\n💡 Les nouvelles règles utiliseront product_type (original CSV) et csv_type (suggéré par SEO).")

if __name__ == "__main__":
    migrate()
