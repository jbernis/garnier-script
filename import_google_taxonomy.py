#!/usr/bin/env python3
"""
Script pour importer la taxonomie Google Shopping dans la base de données.
"""

import sys
import os

# Ajouter le répertoire courant au path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from apps.ai_editor.db import AIPromptsDB

def main():
    """Importe la taxonomie Google Shopping."""
    taxonomy_file = "google_taxonomy.txt"
    
    if not os.path.exists(taxonomy_file):
        print(f"❌ Fichier {taxonomy_file} introuvable")
        print("Téléchargez-le depuis: https://www.google.com/basepages/producttype/taxonomy-with-ids.fr-FR.txt")
        return 1
    
    print("📥 Import de la taxonomie Google Shopping...")
    
    # Initialiser la base de données
    db = AIPromptsDB()
    
    # Importer la taxonomie
    count = db.import_google_taxonomy(taxonomy_file)
    
    # Vérifier l'import
    total = db.get_taxonomy_count()
    
    print(f"✅ Import terminé: {count} catégories importées")
    print(f"📊 Total dans la base: {total} catégories")
    
    # Tester la recherche
    print("\n🔍 Test de recherche:")
    test_queries = [
        "Maison et jardin > Linge > Linge de table > Nappes",
        "Nappes",
        "linge de table nappe"
    ]
    
    for query in test_queries:
        code = db.search_google_category(query)
        if code:
            print(f"  '{query}' → {code}")
        else:
            print(f"  '{query}' → Non trouvé")
    
    db.close()
    return 0

if __name__ == "__main__":
    sys.exit(main())
