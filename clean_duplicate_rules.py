"""
Script pour nettoyer les doublons de règles dans type_category_mapping.
Normalise tous les csv_type en UPPERCASE et fusionne les doublons en gardant la meilleure règle.
"""

import logging
from apps.ai_editor.db import AIPromptsDB

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def clean_duplicate_rules():
    """Nettoie les doublons de règles en normalisant en uppercase."""
    db = AIPromptsDB()
    cursor = db.conn.cursor()
    
    print("=" * 80)
    print("🧹 NETTOYAGE DES RÈGLES EN DOUBLE")
    print("=" * 80)
    
    # Étape 1: Récupérer toutes les règles
    cursor.execute('SELECT * FROM type_category_mapping ORDER BY csv_type, confidence DESC')
    all_rules = cursor.fetchall()
    
    print(f"\n📊 Nombre total de règles: {len(all_rules)}")
    
    # Étape 2: Grouper par csv_type normalisé (uppercase)
    rules_by_type = {}
    for rule in all_rules:
        csv_type_upper = rule['csv_type'].upper() if rule['csv_type'] else ''
        
        if not csv_type_upper:
            continue
        
        if csv_type_upper not in rules_by_type:
            rules_by_type[csv_type_upper] = []
        
        rules_by_type[csv_type_upper].append(dict(rule))
    
    # Étape 3: Identifier et traiter les doublons
    duplicates_found = 0
    rules_merged = 0
    
    for csv_type_upper, rules in rules_by_type.items():
        if len(rules) == 1:
            # Pas de doublon, juste normaliser le csv_type
            rule = rules[0]
            if rule['csv_type'] != csv_type_upper:
                cursor.execute('''
                    UPDATE type_category_mapping
                    SET csv_type = ?
                    WHERE id = ?
                ''', (csv_type_upper, rule['id']))
                logger.info(f"✓ Normalisé: '{rule['csv_type']}' → '{csv_type_upper}'")
        else:
            # Doublons trouvés !
            duplicates_found += 1
            print(f"\n⚠️ Doublons trouvés pour '{csv_type_upper}': {len(rules)} règles")
            
            for i, rule in enumerate(rules, 1):
                print(f"  {i}. csv_type='{rule['csv_type']}', conf={rule['confidence']:.2f}, "
                      f"use_count={rule['use_count']}, cat={rule['category_code']}")
            
            # Stratégie de fusion : garder la règle avec la meilleure combinaison
            # 1. Priorité: Confidence la plus haute
            # 2. Ensuite: Use count le plus élevé
            # 3. Ensuite: La plus récente
            
            best_rule = max(rules, key=lambda r: (
                r['confidence'],
                r['use_count'],
                r['updated_at'] or r['created_at']
            ))
            
            print(f"  → Règle conservée: conf={best_rule['confidence']:.2f}, "
                  f"use_count={best_rule['use_count']}, cat={best_rule['category_code']}")
            
            # Additionner les use_count des autres règles
            total_use_count = sum(r['use_count'] for r in rules)
            
            # Mettre à jour la meilleure règle
            cursor.execute('''
                UPDATE type_category_mapping
                SET csv_type = ?, use_count = ?
                WHERE id = ?
            ''', (csv_type_upper, total_use_count, best_rule['id']))
            
            # Supprimer les autres
            for rule in rules:
                if rule['id'] != best_rule['id']:
                    cursor.execute('DELETE FROM type_category_mapping WHERE id = ?', (rule['id'],))
                    rules_merged += 1
                    print(f"  ✗ Supprimé: csv_type='{rule['csv_type']}', id={rule['id']}")
    
    # Étape 4: Commit
    db.conn.commit()
    
    # Étape 5: Statistiques finales
    cursor.execute('SELECT COUNT(*) as count FROM type_category_mapping')
    final_count = cursor.fetchone()['count']
    
    print("\n" + "=" * 80)
    print("📊 RÉSULTAT DU NETTOYAGE")
    print("=" * 80)
    print(f"Règles avant nettoyage: {len(all_rules)}")
    print(f"Règles après nettoyage: {final_count}")
    print(f"Groupes de doublons trouvés: {duplicates_found}")
    print(f"Règles fusionnées/supprimées: {rules_merged}")
    print(f"Règles économisées: {len(all_rules) - final_count}")
    print("=" * 80)
    
    return duplicates_found, rules_merged


if __name__ == '__main__':
    clean_duplicate_rules()
