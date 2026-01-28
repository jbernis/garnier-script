"""
Script de test pour la catégorisation LangGraph avec le produit plaid problématique.
"""

import sys
import logging

# Configurer le logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

from apps.ai_editor.db import AIPromptsDB
from apps.ai_editor.langgraph_categorizer.graph import GoogleShoppingCategorizationGraph
from utils.ai_providers import get_provider

def test_plaid_categorization():
    """Test de catégorisation du produit plaid problématique."""
    print("="*80)
    print("TEST LANGGRAPH: Catégorisation du plaid problématique")
    print("="*80)
    
    # Initialiser la base de données
    db = AIPromptsDB()
    
    # Récupérer les credentials Gemini
    gemini_key = db.get_ai_credentials('gemini')
    if not gemini_key:
        print("❌ Credentials Gemini non trouvés dans la base de données")
        print("   Configurez-les dans l'interface GUI avant de lancer ce test")
        return False
    
    # Récupérer le modèle Gemini
    gemini_model = db.get_ai_model('gemini') or 'gemini-2.0-flash-exp'
    print(f"🤖 Utilisation de Gemini: {gemini_model}")
    
    # Créer le provider Gemini
    gemini_provider = get_provider('gemini', api_key=gemini_key, model=gemini_model)
    
    # Créer le graph LangGraph
    print("🔧 Création du graph LangGraph...")
    graph = GoogleShoppingCategorizationGraph(db, gemini_provider)
    
    # Produit de test: le plaid problématique
    product = {
        'Handle': 'test-plaid-dive',
        'Title': 'DIVE PLAID BIFACE - PLAID EN COTON',
        'Type': 'Plaid',
        'Vendor': 'Garnier-Thiebaut',
        'Tags': 'Lagustothèque'
    }
    
    print("\n📦 PRODUIT À TESTER:")
    print(f"   Handle: {product['Handle']}")
    print(f"   Title: {product['Title']}")
    print(f"   Type: {product['Type']}")
    print(f"   Vendor: {product['Vendor']}")
    
    print("\n🚀 Lancement de la catégorisation LangGraph...\n")
    
    # Catégoriser
    result = graph.categorize(product)
    
    # Afficher les résultats
    print("\n" + "="*80)
    print("RÉSULTATS DE LA CATÉGORISATION")
    print("="*80)
    print(f"Catégorie code: {result['category_code']}")
    print(f"Catégorie path: {result['category_path']}")
    print(f"Confidence: {result['confidence']:.2%}")
    print(f"Needs review: {result['needs_review']}")
    print(f"Rationale: {result['rationale']}")
    
    # Vérifier le résultat
    print("\n" + "="*80)
    print("VALIDATION")
    print("="*80)
    
    success = True
    
    if result['category_code']:
        # Vérifier que ce n'est PAS une catégorie de rideaux
        if 'rideau' in result['category_path'].lower() or 'embrasse' in result['category_path'].lower():
            print("❌ ÉCHEC: Le plaid a été catégorisé comme un accessoire de rideau!")
            print(f"   Catégorie incorrecte: {result['category_path']}")
            success = False
        else:
            print("✅ SUCCÈS: Le plaid n'a PAS été catégorisé comme un rideau")
            
            # Vérifier qu'il contient "couverture" ou "literie" ou "lit"
            path_lower = result['category_path'].lower()
            if 'couverture' in path_lower or 'literie' in path_lower or 'lit' in path_lower or 'linge de lit' in path_lower:
                print(f"✅ EXCELLENT: Catégorie appropriée pour un plaid: {result['category_path']}")
            else:
                print(f"⚠️  ATTENTION: Catégorie valide mais pas optimale: {result['category_path']}")
                print("   (devrait idéalement contenir 'couverture', 'literie' ou 'lit')")
    else:
        print("❌ ÉCHEC: Aucune catégorie n'a été trouvée")
        success = False
    
    # Vérifier la confidence
    if result['confidence'] >= 0.8:
        print(f"✅ Confidence élevée: {result['confidence']:.0%}")
    else:
        print(f"⚠️  Confidence moyenne/faible: {result['confidence']:.0%}")
    
    print("\n" + "="*80)
    if success:
        print("✅ TEST RÉUSSI")
    else:
        print("❌ TEST ÉCHOUÉ")
    print("="*80)
    
    return success


if __name__ == '__main__':
    try:
        success = test_plaid_categorization()
        sys.exit(0 if success else 1)
    except Exception as e:
        print(f"\n❌ ERREUR: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
