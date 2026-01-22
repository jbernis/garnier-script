#!/usr/bin/env python3
"""
Script de test pour vérifier le filtrage des modèles Claude.
Affiche tous les modèles disponibles via l'API et ceux qui sont filtrés.
"""

import os
import sys
from pathlib import Path
from datetime import datetime

# Ajouter le répertoire parent au path pour importer les modules
sys.path.insert(0, str(Path(__file__).parent))

from dotenv import load_dotenv
from utils.ai_providers import ClaudeProvider

# Charger les variables d'environnement
load_dotenv()


def test_claude_models():
    """Teste la récupération et le filtrage des modèles Claude."""
    
    print("=" * 80)
    print("TEST DE RÉCUPÉRATION DES MODÈLES CLAUDE")
    print("=" * 80)
    print()
    
    # Vérifier la clé API
    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        print("❌ ERREUR: ANTHROPIC_API_KEY n'est pas définie dans le fichier .env")
        return
    
    print(f"✅ Clé API trouvée: {api_key[:10]}...")
    print()
    
    try:
        # Créer le provider Claude
        print("🔄 Connexion à l'API Anthropic...")
        import anthropic
        client = anthropic.Anthropic(api_key=api_key)
        
        # Récupérer tous les modèles
        print("🔄 Récupération de tous les modèles...")
        models_response = client.models.list()
        
        print(f"✅ {len(models_response.data)} modèles récupérés depuis l'API")
        print()
        
        # Afficher tous les modèles bruts
        print("=" * 80)
        print("TOUS LES MODÈLES DISPONIBLES (brut)")
        print("=" * 80)
        print()
        
        all_models = []
        for i, model in enumerate(models_response.data, 1):
            created_year = model.created_at.year if hasattr(model.created_at, 'year') else 0
            created_date = model.created_at.strftime("%Y-%m-%d") if hasattr(model.created_at, 'strftime') else str(model.created_at)
            display_name = getattr(model, 'display_name', model.id)
            
            all_models.append({
                'id': model.id,
                'display_name': display_name,
                'created_at': model.created_at,
                'created_year': created_year,
                'created_date': created_date
            })
            
            print(f"{i:3d}. {model.id:45s} | {display_name:45s} | {created_date}")
        
        print()
        print(f"Total: {len(all_models)} modèles")
        print()
        
        # Appliquer le filtre
        print("=" * 80)
        print("FILTRAGE INTELLIGENT")
        print("=" * 80)
        print()
        
        filtered_models = []
        rejected_models = []
        
        for model in all_models:
            is_relevant = ClaudeProvider._is_relevant_claude_model(
                model['id'], 
                model['created_year']
            )
            
            if is_relevant:
                filtered_models.append(model)
            else:
                rejected_models.append(model)
        
        # Afficher les modèles REJETÉS
        print(f"🚫 MODÈLES REJETÉS ({len(rejected_models)} modèles)")
        print("-" * 80)
        for model in rejected_models:
            reason = []
            model_lower = model['id'].lower()
            
            # Déterminer la raison du rejet
            if 'embed' in model_lower:
                reason.append("embedding")
            if 'beta' in model_lower:
                reason.append("beta")
            if 'experimental' in model_lower:
                reason.append("experimental")
            if 'legacy' in model_lower:
                reason.append("legacy")
            if 'test' in model_lower:
                reason.append("test")
            if 'claude-1' in model_lower or 'claude-2' in model_lower:
                reason.append("version < 3")
            if model['created_year'] < 2024:
                reason.append(f"année < 2024 ({model['created_year']})")
            if not model_lower.startswith('claude-'):
                reason.append("ne commence pas par 'claude-'")
            
            reason_str = ", ".join(reason) if reason else "autre"
            print(f"   • {model['id']:45s} | {model['created_date']:12s} | Raison: {reason_str}")
        
        print()
        
        # Afficher les modèles ACCEPTÉS
        print(f"✅ MODÈLES ACCEPTÉS ({len(filtered_models)} modèles)")
        print("-" * 80)
        
        # Trier par date (plus récents en premier)
        filtered_models.sort(key=lambda x: x['created_at'], reverse=True)
        
        for i, model in enumerate(filtered_models, 1):
            print(f"{i:3d}. {model['id']:45s} | {model['display_name']:45s} | {model['created_date']}")
        
        print()
        
        # Statistiques
        print("=" * 80)
        print("STATISTIQUES")
        print("=" * 80)
        print()
        print(f"📊 Total de modèles disponibles via l'API : {len(all_models)}")
        print(f"✅ Modèles acceptés (filtrés)            : {len(filtered_models)}")
        print(f"🚫 Modèles rejetés                        : {len(rejected_models)}")
        print(f"📈 Taux de filtrage                       : {(len(rejected_models) / len(all_models) * 100):.1f}%")
        print()
        
        # Tester avec le ClaudeProvider
        print("=" * 80)
        print("TEST AVEC ClaudeProvider.list_models()")
        print("=" * 80)
        print()
        
        provider = ClaudeProvider(api_key=api_key)
        models_from_provider = provider.list_models()
        
        print(f"✅ Modèles retournés par list_models() : {len(models_from_provider)}")
        print()
        for i, model_id in enumerate(models_from_provider, 1):
            print(f"{i:3d}. {model_id}")
        
        print()
        print("=" * 80)
        print("✅ TEST TERMINÉ AVEC SUCCÈS")
        print("=" * 80)
        
    except Exception as e:
        print()
        print("=" * 80)
        print("❌ ERREUR")
        print("=" * 80)
        print(f"Une erreur s'est produite : {e}")
        print()
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    test_claude_models()
