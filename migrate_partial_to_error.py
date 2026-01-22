#!/usr/bin/env python3
"""
Script de migration pour remplacer tous les statuts 'partial' par 'error'
dans la base de données ai_prompts.db (table csv_rows).
"""

import sqlite3
import sys
from pathlib import Path


def migrate_partial_to_error():
    """Migre tous les statuts 'partial' vers 'error' dans la table csv_rows."""
    
    db_path = Path(__file__).parent / "database" / "ai_prompts.db"
    
    if not db_path.exists():
        print(f"❌ Erreur: Base de données introuvable: {db_path}")
        sys.exit(1)
    
    print("=" * 80)
    print("MIGRATION DES STATUTS 'PARTIAL' VERS 'ERROR'")
    print("=" * 80)
    print()
    
    try:
        # Connexion à la base de données
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # 1. Compter les lignes avec statut 'partial' AVANT la migration
        cursor.execute("SELECT COUNT(*) FROM csv_rows WHERE status = 'partial'")
        count_before = cursor.fetchone()[0]
        
        print(f"📊 Lignes avec statut 'partial' avant migration: {count_before}")
        
        if count_before == 0:
            print("✅ Aucune ligne à migrer. La base de données est déjà à jour.")
            conn.close()
            return
        
        print()
        
        # 2. Afficher un aperçu des lignes à migrer
        cursor.execute("""
            SELECT id, handle, error_message 
            FROM csv_rows 
            WHERE status = 'partial' 
            LIMIT 5
        """)
        sample_rows = cursor.fetchall()
        
        print(f"📋 Aperçu des lignes à migrer (max 5):")
        for row_id, handle, error_msg in sample_rows:
            handle_display = handle if handle else "(sans handle)"
            error_display = (error_msg[:50] + "...") if error_msg and len(error_msg) > 50 else (error_msg or "")
            print(f"   • ID {row_id}: {handle_display} | {error_display}")
        
        if count_before > 5:
            print(f"   ... et {count_before - 5} autre(s) ligne(s)")
        
        print()
        
        # 3. Effectuer la migration
        print("🔄 Migration en cours...")
        cursor.execute("""
            UPDATE csv_rows 
            SET status = 'error' 
            WHERE status = 'partial'
        """)
        
        rows_updated = cursor.rowcount
        conn.commit()
        
        print(f"✅ {rows_updated} ligne(s) mise(s) à jour avec succès")
        print()
        
        # 4. Vérifier qu'il n'y a plus de statuts 'partial'
        cursor.execute("SELECT COUNT(*) FROM csv_rows WHERE status = 'partial'")
        count_after = cursor.fetchone()[0]
        
        if count_after > 0:
            print(f"⚠️ ATTENTION: Il reste encore {count_after} ligne(s) avec statut 'partial'")
            conn.close()
            sys.exit(1)
        
        # 5. Afficher la répartition finale des statuts
        cursor.execute("""
            SELECT status, COUNT(*) as count 
            FROM csv_rows 
            GROUP BY status 
            ORDER BY status
        """)
        
        status_distribution = cursor.fetchall()
        
        print("📊 Répartition finale des statuts:")
        for status, count in status_distribution:
            icon = {
                'pending': '⏳',
                'processing': '🔄',
                'completed': '✅',
                'error': '❌'
            }.get(status, '❓')
            
            print(f"   {icon} {status}: {count}")
        
        print()
        print("=" * 80)
        print("✅ MIGRATION TERMINÉE AVEC SUCCÈS")
        print("=" * 80)
        
        conn.close()
        
    except Exception as e:
        print(f"❌ Erreur lors de la migration: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    migrate_partial_to_error()
