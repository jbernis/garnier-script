#!/usr/bin/env python3
"""
Script de migration pour ajouter les prompts système séparés pour chaque agent.
"""

import sqlite3
from pathlib import Path

DB_PATH = "database/ai_prompts.db"

def migrate():
    """Migre le schéma de la base de données pour supporter les prompts système séparés."""
    print("🔄 Migration du schéma de la base de données...")
    print(f"   Base: {DB_PATH}")
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # 1. Ajouter les nouvelles colonnes si elles n'existent pas
    print("\n1. Ajout des nouvelles colonnes...")
    try:
        cursor.execute("ALTER TABLE ai_prompts ADD COLUMN seo_system_prompt TEXT")
        print("   ✓ Colonne 'seo_system_prompt' ajoutée")
    except sqlite3.OperationalError as e:
        if "duplicate column" in str(e).lower():
            print("   ✓ Colonne 'seo_system_prompt' déjà existante")
        else:
            raise
    
    try:
        cursor.execute("ALTER TABLE ai_prompts ADD COLUMN google_shopping_system_prompt TEXT")
        print("   ✓ Colonne 'google_shopping_system_prompt' ajoutée")
    except sqlite3.OperationalError as e:
        if "duplicate column" in str(e).lower():
            print("   ✓ Colonne 'google_shopping_system_prompt' déjà existante")
        else:
            raise
    
    # 2. Compter les ensembles de prompts à migrer
    cursor.execute("SELECT COUNT(*) FROM ai_prompts WHERE seo_system_prompt IS NULL")
    count_to_migrate = cursor.fetchone()[0]
    
    if count_to_migrate > 0:
        print(f"\n2. Migration des données existantes ({count_to_migrate} ensemble(s))...")
        
        # Migrer les données existantes
        cursor.execute("""
            UPDATE ai_prompts 
            SET seo_system_prompt = system_prompt,
                google_shopping_system_prompt = system_prompt
            WHERE seo_system_prompt IS NULL
        """)
        
        rows_updated = cursor.rowcount
        print(f"   ✓ {rows_updated} ensemble(s) de prompts migré(s)")
    else:
        print("\n2. Migration des données: aucune donnée à migrer")
    
    # 3. Commit et fermeture
    conn.commit()
    conn.close()
    
    print("\n✅ Migration terminée avec succès!")
    print("\nℹ️  Les prompts système ont été dupliqués:")
    print("   - system_prompt → seo_system_prompt")
    print("   - system_prompt → google_shopping_system_prompt")
    print("\n💡 Vous pouvez maintenant personnaliser chaque prompt système dans l'interface.")

if __name__ == "__main__":
    migrate()
