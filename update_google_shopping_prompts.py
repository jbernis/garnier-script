#!/usr/bin/env python3
"""
Script pour mettre à jour les prompts Google Shopping avec des versions optimisées pour Gemini.
"""

import sqlite3
from pathlib import Path

DB_PATH = "database/ai_prompts.db"

# Prompt système pour Google Shopping (comportement global de l'agent)
GOOGLE_SHOPPING_SYSTEM_PROMPT = """Tu es un expert en catégorisation de produits pour Google Shopping.

Ta mission est de choisir LA MEILLEURE catégorie de la taxonomie Google Shopping pour chaque produit.

RÈGLES STRICTES:
1. Tu DOIS choisir une catégorie qui existe dans la taxonomie fournie
2. Tu DOIS répondre avec le chemin complet en français (ex: "Maison et jardin > Linge de maison > Linge de lit > Draps")
3. Si plusieurs catégories semblent appropriées, choisis la PLUS SPÉCIFIQUE
4. Si aucune catégorie n'est parfaite, choisis la PLUS PROCHE
5. Tu dois TOUJOURS donner UNE réponse (pas de "je ne sais pas")

CONTEXTE:
- Les catégories sont organisées hiérarchiquement (parent > enfant > petit-enfant)
- Plus la catégorie est spécifique, meilleure est la catégorisation
- Google Shopping utilise ces catégories pour mieux référencer les produits

FORMAT DE RÉPONSE:
- Réponds UNIQUEMENT avec le chemin complet de la catégorie
- PAS d'explication, PAS de justification
- JUSTE la catégorie (ex: "Arts et divertissement > Loisirs > Activités artistiques et artisanales > Arts créatifs > Fournitures de bijouterie")

QUALITÉ:
- Lis attentivement le titre, la description et les métadonnées du produit
- Utilise le contexte (marque, matériaux, usage) pour affiner ton choix
- Pense comme un client qui cherche ce produit sur Google Shopping"""

# Prompt métier pour Google Shopping (instructions spécifiques à la tâche)
GOOGLE_CATEGORY_PROMPT = """Analyse ce produit et choisis LA catégorie Google Shopping la plus appropriée.

DONNÉES DU PRODUIT:
- Handle: {handle}
- Titre: {title}
- Description: {body_html}
- Type: {product_type}
- Vendor: {vendor}
- Tags: {tags}

CATÉGORIES PERTINENTES DISPONIBLES:
{relevant_categories}

INSTRUCTIONS:
1. Lis attentivement toutes les informations du produit
2. Identifie le type de produit principal (ex: nappe, serviette, drap, etc.)
3. Identifie les caractéristiques importantes (matériau, usage, public cible)
4. Compare avec les catégories disponibles ci-dessus
5. Choisis la catégorie LA PLUS SPÉCIFIQUE qui correspond au produit

EXEMPLES DE CATÉGORISATION:

Produit: "Nappe en coton 160x200cm"
→ "Maison et jardin > Linge de maison > Linge de table > Nappes"

Produit: "Serviette de table en lin brodée"
→ "Maison et jardin > Linge de maison > Linge de table > Serviettes de table"

Produit: "Drap housse en percale de coton 90x190cm"
→ "Maison et jardin > Linge de maison > Linge de lit > Draps housses"

Produit: "Torchon de cuisine en coton bio"
→ "Maison et jardin > Linge de maison > Linge de cuisine > Torchons"

Produit: "Housse de couette 240x220cm en lin lavé"
→ "Maison et jardin > Linge de maison > Linge de lit > Housses de couette"

ATTENTION:
- Ne choisis PAS une catégorie trop générique (ex: "Maison et jardin" seul)
- Ne choisis PAS une catégorie qui ne correspond pas au produit
- Si le produit a plusieurs usages, choisis l'usage PRINCIPAL

RÉPONSE ATTENDUE:
Réponds UNIQUEMENT avec le chemin complet de la catégorie en français, sans guillemets, sans explication.

Exemple de réponse valide:
Maison et jardin > Linge de maison > Linge de table > Nappes"""

def update_prompts():
    """Met à jour les prompts Google Shopping dans la base de données."""
    print("🔄 Mise à jour des prompts Google Shopping...")
    print(f"   Base: {DB_PATH}")
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Vérifier que les colonnes existent
    cursor.execute("PRAGMA table_info(ai_prompts)")
    columns = [column[1] for column in cursor.fetchall()]
    
    if 'google_shopping_system_prompt' not in columns:
        print("\n⚠️  Erreur: La colonne 'google_shopping_system_prompt' n'existe pas!")
        print("   Exécutez d'abord: python migrate_prompts_schema.py")
        conn.close()
        return
    
    # Récupérer tous les ensembles de prompts
    cursor.execute("SELECT id, name FROM ai_prompts")
    prompt_sets = cursor.fetchall()
    
    if not prompt_sets:
        print("\n⚠️  Aucun ensemble de prompts trouvé!")
        conn.close()
        return
    
    print(f"\n📦 {len(prompt_sets)} ensemble(s) de prompts trouvé(s):")
    for ps_id, ps_name in prompt_sets:
        print(f"   - {ps_name} (ID: {ps_id})")
    
    # Mettre à jour tous les ensembles
    print("\n📝 Mise à jour des prompts...")
    cursor.execute("""
        UPDATE ai_prompts 
        SET google_shopping_system_prompt = ?,
            google_category_prompt = ?
    """, (GOOGLE_SHOPPING_SYSTEM_PROMPT, GOOGLE_CATEGORY_PROMPT))
    
    rows_updated = cursor.rowcount
    conn.commit()
    conn.close()
    
    print(f"   ✓ {rows_updated} ensemble(s) mis à jour")
    
    print("\n✅ Prompts Google Shopping mis à jour avec succès!")
    print("\n📋 Résumé:")
    print("   - Prompt système: Optimisé pour Gemini et la catégorisation")
    print("   - Prompt métier: Instructions détaillées avec exemples")
    print("   - Format: Réponse simple (juste la catégorie)")
    print("   - Langue: Français (taxonomie française)")
    
    print("\n💡 Les nouveaux prompts:")
    print("   - Sont optimisés pour un seul champ (catégorie)")
    print("   - Utilisent le contexte du produit (titre, description, tags)")
    print("   - Incluent des exemples concrets")
    print("   - Forcent une réponse spécifique (pas de généralités)")
    
    print("\n🔄 Redémarrez l'application pour voir les changements:")
    print("   Ctrl+C puis ./run_gui.sh")

if __name__ == "__main__":
    update_prompts()
