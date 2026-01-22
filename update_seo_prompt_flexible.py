#!/usr/bin/env python3
"""
Script pour rendre le prompt métier SEO plus flexible
"""

import sqlite3
import sys

NOUVEAU_PROMPT_SEO = """🎯 MISSION: Générer les 6 champs SEO et marketing pour ce produit

📊 CHAMPS À GÉNÉRER:

1. seo_title (50-70 caractères)
   - Titre optimisé pour les moteurs de recherche
   - Inclure: nom du produit + mots-clés principaux
   - Style: Accrocheur et professionnel
   - Exemple: "Nappe en Coton Bio 160x200cm - Motif Basque Artiga"

2. seo_description (150-320 caractères)
   - Description complète et vendeuse pour Google
   - Inclure: bénéfices clés, caractéristiques, appel à l'action
   - Style: Persuasif et informatif
   - Exemple: "Découvrez notre nappe en coton bio 160x200cm avec motif basque traditionnel. Qualité Artiga, tissage résistant, facile d'entretien. Parfaite pour vos tables de 4-6 personnes. Livraison gratuite."

3. title
   - Nom du produit pour Shopify
   - Format: [Produit] - [Caractéristique principale] - [Marque si disponible]
   - Style: Clair et professionnel
   - Exemple: "Nappe en Coton Bio 160x200cm - Motif Basque - Artiga"

4. body_html (minimum 200 caractères)
   - Description HTML riche et détaillée pour la fiche produit
   - Structurer avec: introduction, caractéristiques, utilisation, entretien
   - Utiliser: paragraphes <p>, listes <ul>, mots clés en <strong>
   - Ton: Professionnel, informatif, vendeur
   - Exemple de structure:
   
   <p>Paragraphe d'introduction présentant le produit et ses avantages.</p>
   <p><strong>Caractéristiques:</strong></p>
   <ul>
   <li>Matière et composition</li>
   <li>Dimensions et taille</li>
   <li>Style et design</li>
   <li>Qualité et fabrication</li>
   </ul>
   <p>Informations sur l'utilisation et l'entretien.</p>

5. tags (5-10 tags)
   - Tags SEO pertinents pour Shopify
   - Inclure: catégorie, sous-catégorie, matériaux, marque, couleurs, style
   - Format: minuscules, séparés par ", "
   - Exemple: "nappe, linge de table, coton bio, 160x200, artiga, basque, motif traditionnel"

6. image_alt_text
   - Description de l'image pour l'accessibilité et le SEO
   - Format: [Produit] - [Caractéristique visuelle principale]
   - Exemple: "Nappe en coton bio avec motif basque rouge et blanc"

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

📍 CONTEXTE ENTREPRISE (à intégrer naturellement dans tes descriptions):

La Gustothèque est une entreprise familiale qui sélectionne avec soin chaque produit 
pour sa qualité, son authenticité et son savoir-faire. Nous privilégions les fabricants 
reconnus pour leur excellence et leur engagement dans la durabilité.

⚠️ RÈGLE D'OR: 
Génère TOUJOURS du contenu de qualité avec les informations disponibles.
Ne refuse JAMAIS de créer du contenu sous prétexte d'informations manquantes.
Adapte-toi intelligemment aux données disponibles et crée du contenu premium.
Si une information spécifique manque, concentre-toi sur ce qui est disponible.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

✏️ Contraintes éditoriales importantes :
- Ton premium, professionnel, chaleureux et expert
- Jamais marketing excessif, jamais démonstratif
- On doit sentir une vraie sélection, faite avec exigence et connaissance du métier
- Texte fluide, naturel, humain, non détectable comme généré par une IA
- Longueur maîtrisée : clair, lisible, pas trop long
- Optimisé pour la recherche produit (SEO + recherche conversationnelle type ChatGPT)
- Convient à une lecture rapide comme à une lecture attentive

Règles strictes :
- Ne jamais répéter le titre du produit dans le texte
- Ne jamais citer la marque dans le corps du texte (elle est déjà affichée ailleurs)
- Ne jamais inclure de lien externe
- Le texte doit être autonome et directement intégrable dans Shopify

Éléments à intégrer naturellement (dans la mesure du possible selon les données disponibles):

🔴 ESSENTIELS (priorité absolue):
- Description du produit et de son usage réel
- Les bénéfices concrets pour le client (durabilité, confort, précision, plaisir d'usage…)

🟡 RECOMMANDÉS (si les informations sont disponibles):
- Le lieu de fabrication et/ou de conception (pays, région si pertinent)
- Le savoir-faire associé (artisanat, industrie maîtrisée, tradition, innovation…)
- Le contexte d'achat : se faire plaisir et faire plaisir
- Le fait que La Gustothèque sélectionne chaque produit avec soin

Structure attendue (à adapter selon les données disponibles):
1. Un court paragraphe d'introduction incarné, élégant et engageant
2. Une description claire du produit et de son usage
3. Une liste de points clés (4 à 6 maximum) orientés bénéfices clients
4. Une phrase de conclusion qui renforce la confiance et la légitimité
5. Un bloc final intitulé : « Le conseil de La Gustothèque » (optionnel si manque d'info)

Bloc « Le conseil de La Gustothèque » (si pertinent):
- Court (2 à 3 phrases maximum)
- Ton complice et expert
- Apporte un conseil d'usage, d'association ou de contexte (cadeau, moment, intérieur…)
- Renforce la sensation d'accompagnement et de sélection personnalisée

Règles de style :
- Pas d'emojis
- Pas de phrases trop longues
- Pas de superlatifs exagérés
- Vocabulaire précis, élégant, accessible
- Pas de jargon inutile
- Style sobre, confiant, premium

💡 RAPPEL: N'oublie pas de respecter les règles techniques du system prompt!
"""

def main():
    db_path = 'database/ai_prompts.db'
    
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Mettre à jour tous les prompt sets
        cursor.execute('''
            UPDATE ai_prompts 
            SET seo_prompt = ?
        ''', (NOUVEAU_PROMPT_SEO,))
        
        affected_rows = cursor.rowcount
        conn.commit()
        
        print(f"✅ {affected_rows} prompt set(s) mis à jour avec le nouveau prompt métier SEO flexible")
        print("\n📝 Principales modifications:")
        print("  - 'Éléments obligatoires' → 'Éléments recommandés avec priorités'")
        print("  - Ajout d'une RÈGLE D'OR: toujours générer du contenu")
        print("  - Ajout d'un contexte entreprise réutilisable")
        print("  - Classification des éléments: ESSENTIELS / RECOMMANDÉS")
        print("  - Structure plus flexible et adaptable")
        
        conn.close()
        
    except Exception as e:
        print(f"❌ Erreur: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
