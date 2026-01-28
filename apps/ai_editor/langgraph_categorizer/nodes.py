"""
Nodes du graph LangGraph pour la catégorisation Google Shopping.
"""

import logging
from .state import ProductCategorizationState
from .product_agent import ProductSpecialistAgent
from .taxonomy_agent import TaxonomySpecialistAgent
from apps.ai_editor.db import AIPromptsDB

logger = logging.getLogger(__name__)


def extract_context_node(state: ProductCategorizationState) -> ProductCategorizationState:
    """Node 1: Extraction initiale (optionnel, actuellement minimal)."""
    return state


def product_definition_node(
    state: ProductCategorizationState,
    product_agent: ProductSpecialistAgent
) -> ProductCategorizationState:
    """Node 2: Agent Produit définit le produit."""
    logger.info("🔍 Node: Définition du produit...")
    
    try:
        product_definition = product_agent.analyze_product(state['product_data'])
        
        # Vérifier que le résultat est valide
        if not product_definition or not isinstance(product_definition, dict):
            logger.error(f"❌ Product agent a retourné un résultat invalide: {product_definition}")
            product_definition = {
                'product_type': state['product_data'].get('Title', 'Produit inconnu'),
                'usage': 'Non déterminé',
                'material': 'Non déterminé',
                'search_keywords': []
            }
        
        # Vérifier que les champs essentiels existent
        if 'product_type' not in product_definition:
            product_definition['product_type'] = state['product_data'].get('Title', 'Produit inconnu')
        if 'search_keywords' not in product_definition:
            product_definition['search_keywords'] = []
        
        state['product_definition'] = product_definition
        
        # Logs détaillés de la réponse de l'agent
        logger.info("=" * 80)
        logger.info("📋 AGENT 1 - PRODUCT SPECIALIST - RÉPONSE COMPLÈTE:")
        logger.info(f"  • product_type: {product_definition.get('product_type', 'N/A')}")
        logger.info(f"  • usage: {product_definition.get('usage', 'N/A')}")
        logger.info(f"  • material: {product_definition.get('material', 'N/A')}")
        logger.info(f"  • search_keywords: {', '.join(product_definition.get('search_keywords', []))}")
        logger.info("=" * 80)
        
    except Exception as e:
        logger.error(f"❌ Erreur dans product_definition_node: {e}")
        state['product_definition'] = {
            'product_type': state['product_data'].get('Title', 'Produit inconnu'),
            'usage': 'Erreur analyse',
            'material': 'Non déterminé',
            'search_keywords': []
        }
    
    return state


def sql_candidates_node(
    state: ProductCategorizationState,
    db: AIPromptsDB
) -> ProductCategorizationState:
    """Node 3: Récupération des catégories candidates via SQL enrichi."""
    logger.info("📊 Node: Récupération des candidates SQL...")
    
    # Utiliser les keywords de la définition produit
    enriched_data = state['product_data'].copy()
    keywords_used = []
    if state['product_definition']:
        # Ajouter les keywords à la recherche
        keywords = state['product_definition'].get('search_keywords', [])
        keywords_used = keywords
        enriched_data['_enriched_keywords'] = ' '.join(keywords)
    
    logger.info(f"  🔑 Keywords utilisés pour SQL: {', '.join(keywords_used) if keywords_used else 'aucun (fallback sur titre/type)'}")
    
    # Appeler get_candidate_categories avec les données enrichies
    candidates = db.get_candidate_categories(enriched_data, max_results=15)
    state['candidate_categories'] = candidates
    
    logger.info(f"  ✓ {len(candidates)} catégories candidates trouvées")
    return state


def taxonomy_selection_node(
    state: ProductCategorizationState,
    taxonomy_agent: TaxonomySpecialistAgent
) -> ProductCategorizationState:
    """Node 4: Agent Taxonomy choisit la catégorie."""
    logger.info("🎯 Node: Sélection de la catégorie...")
    
    # Log des candidats disponibles
    logger.info("=" * 80)
    logger.info(f"📊 CANDIDATES DISPONIBLES ({len(state['candidate_categories'])} catégories):")
    for i, (code, path) in enumerate(state['candidate_categories'][:10], 1):  # Top 10
        logger.info(f"  {i}. [{code}] {path}")
    if len(state['candidate_categories']) > 10:
        logger.info(f"  ... et {len(state['candidate_categories']) - 10} autres")
    logger.info("=" * 80)
    
    try:
        result = taxonomy_agent.select_category(
            state['product_definition'],
            state['candidate_categories']
        )
        
        # Vérifier que le résultat est valide
        if not result or len(result) != 3:
            logger.error(f"❌ Taxonomy agent a retourné un résultat invalide: {result}")
            category_path = "Maison et jardin"
            confidence = 0.05
            rationale = "Erreur: Résultat agent invalide"
        else:
            category_path, confidence, rationale = result
            
            # Vérifier et convertir confidence en float
            try:
                confidence = float(confidence)
                # Si 0 ou négatif, utiliser le défaut
                if confidence <= 0:
                    logger.warning(f"⚠️ Confidence invalide ({confidence}), utilisation de 0.5 par défaut")
                    confidence = 0.5
            except (ValueError, TypeError):
                logger.warning(f"⚠️ Confidence invalide '{confidence}', utilisation de 0.5 par défaut")
                confidence = 0.5
            
            # Vérifier que category_path n'est pas None ou vide
            if not category_path:
                logger.error(f"❌ Taxonomy agent a retourné une catégorie vide")
                category_path = "Maison et jardin"
                confidence = 0.05
                rationale = "Erreur: Catégorie vide"
        
        state['selected_category_path'] = category_path
        state['confidence'] = float(confidence)  # Garantir que c'est un float
        state['rationale'] = rationale
        
    except Exception as e:
        logger.error(f"❌ Erreur dans taxonomy_selection_node: {e}")
        state['selected_category_path'] = "Maison et jardin"
        state['confidence'] = 0.05
        state['rationale'] = f"Erreur: {str(e)}"
    
    # Logs détaillés de la réponse de l'agent
    logger.info("=" * 80)
    logger.info("🎯 AGENT 2 - TAXONOMY SPECIALIST - RÉPONSE COMPLÈTE:")
    logger.info(f"  • chosen_category: {category_path}")
    logger.info(f"  • confidence: {confidence:.2f} ({int(confidence*100)}%)")
    logger.info(f"  • rationale: {rationale}")
    logger.info("=" * 80)
    
    return state


def validation_node(
    state: ProductCategorizationState,
    db: AIPromptsDB
) -> ProductCategorizationState:
    """Node 5: Validation de la catégorie choisie."""
    logger.info("✅ Node: Validation...")
    
    # Vérifier que selected_category_path n'est pas None ou vide
    if not state.get('selected_category_path'):
        state['is_valid'] = False
        state['validation_error'] = "Aucune catégorie retournée par l'Agent Taxonomy (None ou vide)"
        logger.error(f"⚠ Validation KO: selected_category_path est None ou vide")
        return state
    
    # Vérifier que la catégorie existe dans la taxonomie
    category_code = db.search_google_category(state['selected_category_path'])
    
    if category_code:
        # Vérifier que la catégorie est suffisamment spécifique (au moins 3 niveaux)
        path_levels = state['selected_category_path'].count('>') + 1
        
        if path_levels < 3:
            # Catégorie trop générale (ex: "Maison et jardin" ou "Maison et jardin > Linge")
            state['is_valid'] = False
            state['validation_error'] = f"Catégorie trop générale ({path_levels} niveau(x)): {state['selected_category_path']} - Nécessite au moins 3 niveaux"
            logger.warning(f"⚠ Validation KO: Catégorie trop générale ({path_levels} niveaux)")
        else:
            state['selected_category_code'] = category_code
            state['is_valid'] = True
            state['needs_review'] = state['confidence'] < 0.8  # Threshold
            logger.info(f"✓ Validation OK: {category_code} - {state['selected_category_path']} ({path_levels} niveaux)")
    else:
        state['is_valid'] = False
        state['validation_error'] = f"Catégorie non trouvée: {state['selected_category_path']}"
        logger.warning(f"⚠ Validation KO: Catégorie non trouvée")
    
    return state


def retry_decision_node(state: ProductCategorizationState) -> str:
    """Décide si on retry ou pas."""
    if state['is_valid']:
        return "output"
    
    if state['retry_count'] < state['max_retries']:
        state['retry_count'] += 1
        logger.info(f"🔄 Retry {state['retry_count']}/{state['max_retries']}")
        return "retry"
    
    # Max retries atteint
    state['needs_review'] = True
    state['confidence'] = 0.0
    logger.warning("❌ Max retries atteint, flagging for review")
    return "output"
