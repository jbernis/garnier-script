#!/usr/bin/env python3
"""
Script pour ajouter les colonnes status et error_message à la table csv_rows
"""

import sqlite3
import sys

def main():
    db_path = 'database/ai_prompts.db'
    
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Vérifier si les colonnes existent déjà
        cursor.execute("PRAGMA table_info(csv_rows)")
        columns = [col[1] for col in cursor.fetchall()]
        
        # Ajouter la colonne status si elle n'existe pas
        if 'status' not in columns:
            cursor.execute('''
                ALTER TABLE csv_rows 
                ADD COLUMN status TEXT DEFAULT 'pending'
            ''')
            print("✅ Colonne 'status' ajoutée à csv_rows")
        else:
            print("ℹ️  Colonne 'status' existe déjà")
        
        # Ajouter la colonne error_message si elle n'existe pas
        if 'error_message' not in columns:
            cursor.execute('''
                ALTER TABLE csv_rows 
                ADD COLUMN error_message TEXT
            ''')
            print("✅ Colonne 'error_message' ajoutée à csv_rows")
        else:
            print("ℹ️  Colonne 'error_message' existe déjà")
        
        # Ajouter la colonne ai_explanation si elle n'existe pas (pour stocker l'explication complète)
        if 'ai_explanation' not in columns:
            cursor.execute('''
                ALTER TABLE csv_rows 
                ADD COLUMN ai_explanation TEXT
            ''')
            print("✅ Colonne 'ai_explanation' ajoutée à csv_rows")
        else:
            print("ℹ️  Colonne 'ai_explanation' existe déjà")
        
        conn.commit()
        
        print("\n📝 Valeurs possibles pour 'status':")
        print("  - 'pending': En attente de traitement")
        print("  - 'processing': En cours de traitement")
        print("  - 'completed': Traitement réussi")
        print("  - 'error': Erreur lors du traitement")
        
        conn.close()
        
    except Exception as e:
        print(f"❌ Erreur: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
