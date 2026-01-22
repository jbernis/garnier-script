#!/usr/bin/env python3
"""
Script ponctuel pour corriger le statut des gammes après traitement des variants.
"""

import sys
import os

# Ajouter le répertoire parent au path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from utils.garnier_db import GarnierDB
from utils.app_config import get_garnier_db_path

def main():
    db_path = get_garnier_db_path()
    print(f"Base de données : {db_path}")
    
    db = GarnierDB(db_path)
    
    print("\n" + "="*60)
    print("Mise à jour du statut des gammes...")
    print("="*60)
    
    # Mettre à jour toutes les gammes
    affected_gammes = db.update_all_gammes_status()
    
    print(f"\n✓ {affected_gammes} gamme(s) mise(s) à jour")
    
    # Afficher le résultat
    print("\n" + "="*60)
    print("Statut final des gammes :")
    print("="*60)
    
    cursor = db.conn.cursor()
    cursor.execute('''
        SELECT status, COUNT(*) as count 
        FROM gammes 
        GROUP BY status 
        ORDER BY 
            CASE status
                WHEN 'completed' THEN 1
                WHEN 'processing' THEN 2
                WHEN 'pending' THEN 3
                WHEN 'error' THEN 4
                ELSE 5
            END
    ''')
    
    for row in cursor.fetchall():
        status = row['status'] or 'NULL'
        count = row['count']
        emoji = {'completed': '✅', 'processing': '🔄', 'pending': '⏳', 'error': '❌'}.get(status, '❓')
        print(f"  {emoji} {status:12} : {count:4}")
    
    db.close()
    print("\n✓ Terminé !")

if __name__ == '__main__':
    main()
