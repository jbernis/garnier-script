#!/usr/bin/env python3
"""
Script pour lister tous les modèles Gemini disponibles via l'API et filtrer les plus pertinents.
"""

import os
import requests
from dotenv import load_dotenv

# Charger les variables d'environnement
load_dotenv()

def list_all_gemini_models():
    """Liste tous les modèles Gemini disponibles."""
    api_key = os.getenv('GEMINI_API_KEY')
    
    # Si pas dans .env, essayer de récupérer depuis la base de données
    if not api_key:
        try:
            import sqlite3
            conn = sqlite3.connect('database/ai_prompts.db')
            cursor = conn.cursor()
            cursor.execute("SELECT api_key FROM ai_credentials WHERE provider_name = 'gemini'")
            row = cursor.fetchone()
            if row:
                api_key = row[0]
                print(f"   ✓ Clé API récupérée depuis la base de données")
            conn.close()
        except Exception as e:
            print(f"   ⚠️  Erreur lors de la lecture de la base: {e}")
    
    if not api_key:
        print("❌ Erreur: GEMINI_API_KEY non trouvée")
        print("   Vérifiez:")
        print("   1. Fichier .env avec GEMINI_API_KEY=...")
        print("   2. Configuration dans l'interface GUI (onglet IA)")
        exit(1)
    
    print("🔍 Récupération de la liste des modèles Gemini...")
    print(f"   Clé API: {api_key[:8]}...{api_key[-4:]}")
    print()
    
    try:
        # Utiliser l'API REST pour lister les modèles
        url = f"https://generativelanguage.googleapis.com/v1beta/models?key={api_key}"
        response = requests.get(url)
        response.raise_for_status()
        
        data = response.json()
        models_data = data.get('models', [])
        
        print(f"📦 {len(models_data)} modèle(s) trouvé(s) au total")
        print()
        
        # Organiser par catégorie
        text_generation = []
        embedding_models = []
        vision_models = []
        other_models = []
        
        for model in models_data:
            model_name = model.get('name', '').replace('models/', '')
            
            # Filtrer par type
            if 'embed' in model_name.lower():
                embedding_models.append(model_name)
            elif 'vision' in model_name.lower() or 'imagen' in model_name.lower():
                vision_models.append(model_name)
            elif 'gemini' in model_name.lower():
                # Modèles de génération de texte
                text_generation.append(model_name)
            else:
                other_models.append(model_name)
        
        # Afficher les catégories
        print("=" * 80)
        print("📝 MODÈLES DE GÉNÉRATION DE TEXTE (Pertinents pour nous)")
        print("=" * 80)
        for model_name in sorted(text_generation):
            print(f"  ✓ {model_name}")
        
        print()
        print("=" * 80)
        print("🚫 MODÈLES D'EMBEDDING (À retirer)")
        print("=" * 80)
        for model_name in sorted(embedding_models):
            print(f"  ✗ {model_name}")
        
        print()
        print("=" * 80)
        print("🚫 MODÈLES VISION/IMAGE (À retirer)")
        print("=" * 80)
        for model_name in sorted(vision_models):
            print(f"  ✗ {model_name}")
        
        if other_models:
            print()
            print("=" * 80)
            print("❓ AUTRES MODÈLES")
            print("=" * 80)
            for model_name in sorted(other_models):
                print(f"  ? {model_name}")
        
        print()
        print("=" * 80)
        print("🎯 MODÈLES RECOMMANDÉS POUR NOUS")
        print("=" * 80)
        
        # Filtrer les modèles recommandés
        recommended = []
        for model_name in text_generation:
            model_lower = model_name.lower()
            # Garder uniquement les modèles récents et pertinents
            if any(version in model_lower for version in ['2.0', '2.5', '3.0', '1.5']):
                if 'flash' in model_lower or 'pro' in model_lower:
                    # Exclure les variantes spéciales non pertinentes
                    if not any(exclude in model_lower for exclude in ['thinking', 'code', 'vision']):
                        recommended.append(model_name)
        
        # Trier par version (plus récent en premier)
        def sort_key(name):
            import re
            match = re.search(r'gemini-(\d+)\.(\d+)', name.lower())
            if match:
                major, minor = int(match.group(1)), int(match.group(2))
                # Privilégier flash sur pro
                is_flash = 'flash' in name.lower()
                return (major, minor, 0 if is_flash else 1)
            return (0, 0, 0)
        
        recommended.sort(key=sort_key, reverse=True)
        
        for i, model_name in enumerate(recommended, 1):
            marker = "⭐" if i == 1 else "✓"
            default_text = " (DÉFAUT RECOMMANDÉ)" if i == 1 else ""
            print(f"  {marker} {model_name}{default_text}")
        
        print()
        print("=" * 80)
        print("📋 RÉSUMÉ")
        print("=" * 80)
        print(f"  Total modèles: {len(models_data)}")
        print(f"  Génération texte: {len(text_generation)}")
        print(f"  Embedding (à retirer): {len(embedding_models)}")
        print(f"  Vision/Image (à retirer): {len(vision_models)}")
        print(f"  Recommandés: {len(recommended)}")
        
        print()
        print("=" * 80)
        print("💾 CONFIGURATION POUR ai_config.json")
        print("=" * 80)
        print('"gemini": {')
        print(f'  "default": "{recommended[0]}",')
        print('  "available": [')
        for i, model_name in enumerate(recommended):
            comma = "," if i < len(recommended) - 1 else ""
            print(f'    "{model_name}"{comma}')
        print('  ]')
        print('}')
        
        return recommended
        
    except Exception as e:
        print(f"❌ Erreur lors de la récupération des modèles: {e}")
        import traceback
        traceback.print_exc()
        exit(1)

if __name__ == "__main__":
    list_all_gemini_models()
