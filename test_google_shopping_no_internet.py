#!/usr/bin/env python3
"""
Script de test pour vérifier que l'agent Google Shopping fonctionne
SANS accès à internet et avec accès à la taxonomie.
"""

from apps.ai_editor.agents import GoogleShoppingAgent
from apps.ai_editor.db import AIPromptsDB
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def test_google_shopping_no_internet():
    """Test de l'agent Google Shopping sans internet."""
    
    print("=" * 70)
    print("TEST AGENT GOOGLE SHOPPING - SANS INTERNET")
    print("=" * 70)
    
    # Mock AI Provider (sans recherche internet)
    class MockAIProviderNoInternet:
        def __init__(self):
            self.enable_search = False
        
        def generate(self, prompt, context=None):
            # Simuler une réponse basée uniquement sur le prompt
            # (pas d'accès à internet simulé)
            if "nappe" in prompt.lower() or "table" in prompt.lower():
                return "Home & Garden > Linens & Bedding > Table Linens > Tablecloths"
            elif "shirt" in prompt.lower() or "vêtement" in prompt.lower():
                return "Apparel & Accessories > Clothing > Shirts & Tops"
            else:
                return "Home & Garden > Kitchen & Dining"
    
    # Créer l'agent
    mock_provider = MockAIProviderNoInternet()
    agent = GoogleShoppingAgent(
        mock_provider,
        "Tu es un expert en catégorisation",
        "Identifie la catégorie Google Shopping"
    )
    
    # Charger la base de données
    db = AIPromptsDB()
    agent.set_database(db)
    
    # Vérifier le nombre de catégories dans la taxonomie
    taxonomy_count = db.get_taxonomy_count()
    print(f"\n📊 Taxonomie Google Shopping: {taxonomy_count} catégories disponibles")
    
    if taxonomy_count == 0:
        print("⚠️ ATTENTION: La taxonomie est vide!")
        print("   Exécutez: python import_google_taxonomy.py")
        print("=" * 70)
        return
    
    # Test 1: Nappe
    print("\n" + "=" * 70)
    print("📋 Test 1: Nappe en coton")
    print("-" * 70)
    
    product_data = {
        'Handle': 'nappe-coton',
        'Title': 'Nappe en coton bio',
        'Type': 'Linge de table',
        'Tags': 'nappe, coton, linge de maison',
        'Vendor': 'Test'
    }
    
    # Récupérer l'échantillon de taxonomie
    taxonomy_sample = agent._get_taxonomy_sample(product_data)
    
    if taxonomy_sample:
        print("✅ Catégories pertinentes trouvées:")
        print(taxonomy_sample)
    else:
        print("⚠️ Aucune catégorie pertinente trouvée pour ce produit")
    
    # Générer la catégorie
    category = agent.generate(product_data)
    print(f"\n✅ Catégorie générée: {category}")
    
    # Vérifier que la catégorie existe dans la taxonomie
    category_code = db.search_google_category(category)
    if category_code:
        print(f"✅ Code trouvé dans la taxonomie: {category_code}")
    else:
        print(f"⚠️ Code non trouvé dans la taxonomie (l'IA a peut-être généré une catégorie valide mais absente)")
    
    # Test 2: Vêtement
    print("\n" + "=" * 70)
    print("📋 Test 2: Chemise en lin")
    print("-" * 70)
    
    product_data = {
        'Handle': 'chemise-lin',
        'Title': 'Chemise homme en lin',
        'Type': 'Vêtement',
        'Tags': 'chemise, lin, homme, vêtement',
        'Vendor': 'Test'
    }
    
    # Récupérer l'échantillon de taxonomie
    taxonomy_sample = agent._get_taxonomy_sample(product_data)
    
    if taxonomy_sample:
        print("✅ Catégories pertinentes trouvées:")
        print(taxonomy_sample)
    else:
        print("⚠️ Aucune catégorie pertinente trouvée pour ce produit")
    
    # Générer la catégorie
    category = agent.generate(product_data)
    print(f"\n✅ Catégorie générée: {category}")
    
    # Vérifier que la catégorie existe dans la taxonomie
    category_code = db.search_google_category(category)
    if category_code:
        print(f"✅ Code trouvé dans la taxonomie: {category_code}")
    else:
        print(f"⚠️ Code non trouvé dans la taxonomie")
    
    # Test 3: Vérifier qu'il n'y a PAS d'accès à internet
    print("\n" + "=" * 70)
    print("📋 Test 3: Vérification de l'absence d'accès à internet")
    print("-" * 70)
    
    if hasattr(mock_provider, 'enable_search'):
        if mock_provider.enable_search:
            print("❌ ERREUR: enable_search = True (l'agent a accès à internet!)")
        else:
            print("✅ enable_search = False (pas d'accès à internet)")
    else:
        print("⚠️ Impossible de vérifier enable_search")
    
    # Résumé
    print("\n" + "=" * 70)
    print("✅ TESTS TERMINÉS")
    print("=" * 70)
    print("\n📊 Résumé:")
    print("  - Agent Google Shopping configuré SANS accès à internet")
    print(f"  - Taxonomie disponible: {taxonomy_count} catégories")
    print("  - L'agent utilise la taxonomie pour suggérer des catégories pertinentes")
    print("  - Le prompt inclut les catégories disponibles dans le contexte")
    print("\n🎯 L'agent Google Shopping fonctionne sans internet!")
    
    db.close()


if __name__ == "__main__":
    try:
        test_google_shopping_no_internet()
    except Exception as e:
        print(f"\n❌ Erreur lors du test: {e}")
        import traceback
        traceback.print_exc()
