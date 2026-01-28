"""
Graph LangGraph principal pour la catégorisation Google Shopping.
"""

import logging
from langgraph.graph import StateGraph, END
from .state import ProductCategorizationState
from .nodes import (
    extract_context_node,
    product_definition_node,
    sql_candidates_node,
    taxonomy_selection_node,
    validation_node,
    retry_decision_node
)
from .product_agent import ProductSpecialistAgent
from .taxonomy_agent import TaxonomySpecialistAgent
from apps.ai_editor.db import AIPromptsDB

logger = logging.getLogger(__name__)


class GoogleShoppingCategorizationGraph:
    """Graph LangGraph pour la catégorisation Google Shopping."""
    
    def __init__(self, db: AIPromptsDB, gemini_provider):
        """
        Initialise le graph de catégorisation.
        
        Args:
            db: Instance de AIPromptsDB
            gemini_provider: Instance de GeminiProvider
        """
        self.db = db
        self.product_agent = ProductSpecialistAgent(gemini_provider, db)
        self.taxonomy_agent = TaxonomySpecialistAgent(gemini_provider, db)
        
        # Construire le graph
        self.graph = self._build_graph()
    
    def _build_graph(self) -> StateGraph:
        """Construit le graph LangGraph."""
        workflow = StateGraph(ProductCategorizationState)
        
        # Ajouter les nodes
        workflow.add_node("extract_context", extract_context_node)
        workflow.add_node(
            "product_definition",
            lambda state: product_definition_node(state, self.product_agent)
        )
        workflow.add_node(
            "sql_candidates",
            lambda state: sql_candidates_node(state, self.db)
        )
        workflow.add_node(
            "taxonomy_selection",
            lambda state: taxonomy_selection_node(state, self.taxonomy_agent)
        )
        workflow.add_node(
            "validation",
            lambda state: validation_node(state, self.db)
        )
        
        # Définir les edges
        workflow.set_entry_point("extract_context")
        workflow.add_edge("extract_context", "product_definition")
        workflow.add_edge("product_definition", "sql_candidates")
        workflow.add_edge("sql_candidates", "taxonomy_selection")
        workflow.add_edge("taxonomy_selection", "validation")
        
        # Conditional edge après validation
        workflow.add_conditional_edges(
            "validation",
            retry_decision_node,
            {
                "retry": "product_definition",  # Retry from product definition
                "output": END
            }
        )
        
        return workflow.compile()
    
    def categorize(self, product_data: dict) -> dict:
        """
        Catégorise un produit.
        
        Args:
            product_data: Données du produit (dict avec Title, Type, etc.)
        
        Returns:
            {
                'category_code': int,
                'category_path': str,
                'confidence': float,
                'needs_review': bool,
                'rationale': str
            }
        """
        # Initialiser le state
        initial_state: ProductCategorizationState = {
            'product_data': product_data,
            'product_definition': None,
            'candidate_categories': None,
            'selected_category_path': None,
            'selected_category_code': None,
            'is_valid': False,
            'validation_error': None,
            'confidence': 0.0,
            'needs_review': True,
            'rationale': '',
            'retry_count': 0,
            'max_retries': 2
        }
        
        # Exécuter le graph
        logger.info(f"🚀 Début catégorisation LangGraph: {product_data.get('Handle', 'unknown')}")
        final_state = self.graph.invoke(initial_state)
        
        # Retourner le résultat
        return {
            'category_code': final_state.get('selected_category_code'),
            'category_path': final_state.get('selected_category_path'),
            'confidence': final_state.get('confidence', 0.0),
            'needs_review': final_state.get('needs_review', True),
            'rationale': final_state.get('rationale', '')
        }
