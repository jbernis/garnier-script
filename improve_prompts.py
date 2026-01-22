#!/usr/bin/env python3
"""
Script pour améliorer les prompts de l'agent IA avec des instructions strictes
pour éviter les champs vides.
"""

import sqlite3
import sys

def improve_prompts():
    """Améliore les prompts dans la base de données."""
    
    db_path = "database/ai_prompts.db"
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    # Récupérer tous les prompts existants
    cursor.execute("SELECT id, name, system_prompt, seo_prompt, google_category_prompt FROM ai_prompts")
    prompts = cursor.fetchall()
    
    if not prompts:
        print("❌ Aucun prompt trouvé dans la base de données")
        return
    
    print(f"✅ {len(prompts)} ensemble(s) de prompts trouvé(s)\n")
    
    # Améliorer chaque ensemble de prompts
    for prompt in prompts:
        prompt_id = prompt['id']
        name = prompt['name']
        
        print(f"📝 Amélioration de l'ensemble: {name} (ID: {prompt_id})")
        
        # Améliorer le system_prompt
        improved_system_prompt = """Tu es un expert en optimisation de fiches produits pour le e-commerce et le SEO.

🎯 RÈGLES ABSOLUES - À RESPECTER IMPÉRATIVEMENT:

1. ❌ JAMAIS DE CHAMPS VIDES
   - Tous les champs demandés DOIVENT être remplis
   - Un champ vide est considéré comme une erreur GRAVE
   - Si tu manques d'informations, utilise ta créativité et tes connaissances

2. ✅ QUALITÉ DU CONTENU
   - Body (HTML): Minimum 200 caractères, utilise des balises HTML valides
   - SEO Title: 50-70 caractères optimisés
   - SEO Description: 150-320 caractères attractifs
   - Tags: Au moins 5-10 tags pertinents séparés par des virgules
   - Image Alt Text: Description claire et accessible de l'image

3. 🔍 UTILISATION DE LA RECHERCHE INTERNET
   - Si tu as accès à Perplexity, UTILISE-LE pour enrichir le contenu
   - Recherche des informations sur le produit, la marque, les caractéristiques
   - Ne te limite JAMAIS aux seules données fournies

4. 📋 FORMAT DE RÉPONSE
   - Répondre UNIQUEMENT en JSON valide
   - Structure exacte:
   {
     "seo_title": "...",
     "seo_description": "...",
     "title": "...",
     "body_html": "<p>...</p>",
     "tags": "tag1, tag2, tag3, ...",
     "image_alt_text": "..."
   }

⚠️ RAPPEL: Un champ vide = échec de la mission. TOUS les champs doivent être remplis."""
        
        # Améliorer le seo_prompt
        improved_seo_prompt = """🎯 MISSION: Générer TOUS les champs SEO et marketing pour ce produit

📊 CHAMPS À GÉNÉRER (TOUS OBLIGATOIRES):

1. seo_title (50-70 caractères)
   - Inclure le nom du produit et mots-clés principaux
   - Optimisé pour les moteurs de recherche
   - Attractif et accrocheur

2. seo_description (150-320 caractères)
   - Description complète et vendeuse
   - Inclure les bénéfices clés du produit
   - Appel à l'action si pertinent

3. title
   - Nom du produit clair et précis
   - Inclure la marque si disponible
   - Format professionnel

4. body_html (MINIMUM 200 caractères)
   - Description HTML riche et détaillée
   - Utiliser des balises: <p>, <ul>, <li>, <strong>, <br>
   - Structurer en paragraphes lisibles
   - Inclure: caractéristiques, matériaux, dimensions, utilisation, entretien
   - Si tu as accès à internet, enrichis avec des informations trouvées en ligne

5. tags (minimum 5-10 tags)
   - Tags pertinents séparés par des virgules
   - Inclure: catégorie, marque, matériaux, couleurs, caractéristiques
   - Exemple: "nappe, linge de table, coton, 160cm, artiga, basque"

6. image_alt_text
   - Description claire de l'image pour l'accessibilité
   - Format: "Produit - Caractéristique principale"

⚠️ INSTRUCTIONS CRITIQUES:
- NE JAMAIS laisser un champ vide
- Si les données sont limitées, utilise tes connaissances et ta créativité
- Si tu as accès à Perplexity, recherche des informations sur le produit
- Le body_html DOIT contenir du HTML valide et être riche en contenu

✅ FORMAT DE RÉPONSE: JSON valide avec TOUS les champs remplis

📋 STRUCTURE JSON EXACTE À RESPECTER:

{
  "seo_title": "Votre titre SEO de 50-70 caractères ici",
  "seo_description": "Votre description SEO de 150-320 caractères ici. Elle doit être attractive et inciter au clic.",
  "title": "Nom du produit clair et professionnel",
  "body_html": "<p>Description HTML riche du produit.</p><ul><li>Caractéristique 1</li><li>Caractéristique 2</li></ul><p>Informations complémentaires.</p>",
  "tags": "tag1, tag2, tag3, tag4, tag5, tag6",
  "image_alt_text": "Description de l'image pour l'accessibilité"
}

⚠️ IMPORTANT: Répondre UNIQUEMENT avec ce JSON, sans texte avant ni après."""
        
        # Améliorer le google_category_prompt
        improved_google_category_prompt = """🎯 MISSION: Identifier la catégorie Google Shopping la plus précise pour ce produit

⚠️ IMPORTANT: Tu N'AS PAS BESOIN d'accès à internet pour cette tâche.
Les catégories pertinentes te seront fournies dans le contexte si disponibles.

🇫🇷 LANGUE: La taxonomie Google Shopping est en FRANÇAIS. Tu DOIS répondre en FRANÇAIS.

📊 INSTRUCTIONS:

1. Analyser attentivement:
   - Type de produit
   - Caractéristiques principales
   - Catégorie mentionnée
   - Usage du produit
   - Les catégories pertinentes listées dans le contexte (EN FRANÇAIS)

2. Choisir le chemin de catégorie le PLUS SPÉCIFIQUE possible
   - Si des catégories pertinentes sont listées, CHOISIS parmi celles-ci
   - Ne pas se limiter aux catégories générales
   - Descendre dans l'arborescence au maximum
   - Privilégier la précision

3. Exemples de chemins valides (EN FRANÇAIS):
   - "Maison et jardin > Linge > Linge de table > Nappes"
   - "Vêtements et accessoires > Vêtements > Hauts > Chemises"
   - "Maison et jardin > Arts de la table et arts culinaires > Arts de la table > Assiettes"

⚠️ RÈGLES STRICTES:
- Répondre UNIQUEMENT avec le chemin complet EN FRANÇAIS
- NE PAS inclure de code ou numéro, juste le chemin textuel
- Utiliser le format exact avec les chevrons " > "
- Si des catégories pertinentes sont listées (en français), privilégie-les EXACTEMENT
- Si tu hésites entre plusieurs catégories, choisis la plus spécifique
- NE JAMAIS traduire en anglais, toujours répondre EN FRANÇAIS

✅ RÉPONDRE UNIQUEMENT AVEC LE CHEMIN DE CATÉGORIE EN FRANÇAIS (pas de JSON, pas d'explication, pas de code)"""
        
        # Mettre à jour dans la base de données
        cursor.execute("""
            UPDATE ai_prompts
            SET system_prompt = ?,
                seo_prompt = ?,
                google_category_prompt = ?,
                updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
        """, (improved_system_prompt, improved_seo_prompt, improved_google_category_prompt, prompt_id))
        
        print(f"  ✅ System prompt amélioré")
        print(f"  ✅ SEO prompt amélioré")
        print(f"  ✅ Google category prompt amélioré\n")
    
    conn.commit()
    conn.close()
    
    print("=" * 60)
    print("✅ Tous les prompts ont été améliorés avec succès!")
    print("=" * 60)
    print("\n📝 Améliorations apportées:")
    print("  1. Instructions strictes pour éviter les champs vides")
    print("  2. Consignes sur l'utilisation de la recherche internet")
    print("  3. Règles de qualité pour chaque champ")
    print("  4. Format de réponse clarifié (JSON)")
    print("  5. Longueurs minimales spécifiées")
    print("\n🎯 Le système d'agent IA est maintenant plus robuste!")


if __name__ == "__main__":
    try:
        improve_prompts()
    except Exception as e:
        print(f"❌ Erreur: {e}")
        sys.exit(1)
