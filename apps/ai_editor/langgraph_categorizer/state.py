"""
Définition du State pour le graph LangGraph de catégorisation.
"""

from typing import TypedDict, Optional, List, Tuple


class ProductCategorizationState(TypedDict):
    """State pour le processus de catégorisation."""
    # Input
    product_data: dict
    
    # Étape 1: Définition produit (Agent Produit)
    product_definition: Optional[dict]  # {type, usage, material, keywords}
    
    # Étape 2: Candidates SQL
    candidate_categories: Optional[List[Tuple[int, str]]]  # [(code, path), ...]
    
    # Étape 3: Sélection (Agent Taxonomy)
    selected_category_path: Optional[str]
    selected_category_code: Optional[int]
    
    # Étape 4: Validation
    is_valid: bool
    validation_error: Optional[str]
    
    # Métriques et output
    confidence: float  # 0.0 à 1.0
    needs_review: bool
    rationale: str  # Explication de la décision
    
    # Retry control
    retry_count: int
    max_retries: int
