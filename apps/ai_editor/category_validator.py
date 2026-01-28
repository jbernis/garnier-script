"""
Helper pour suggérer des catégories Google Shopping alternatives via LLM.

Simplifié (optimisé): Ne fait plus de validation par règles (obsolète).
Garde uniquement la suggestion LLM pour les cas où aucune catégorie n'est trouvée.
"""

import logging
from typing import Dict, Optional, Any, List, Tuple

logger = logging.getLogger(__name__)


class CategoryValidator:
    """Helper pour suggérer des catégories Google Shopping alternatives via LLM."""
    
    def __init__(self, db, ai_provider=None):
        """
        Initialise le helper.
        
        Args:
            db: Instance de AIPromptsDB
            ai_provider: Provider IA pour suggestion LLM
        """
        self.db = db
        self.ai_provider = ai_provider
    
    def suggest_alternative_category(
        self, 
        product_data: Dict[str, Any], 
        failed_category: str, 
        similar_categories: List[Tuple[str, str, float]] = None
    ) -> Optional[str]:
        """
        Demande au LLM de proposer une catégorie alternative de la taxonomie Google.
        
        Cette méthode est appelée uniquement quand:
        1. La catégorie suggérée par Gemini n'existe pas dans la taxonomie
        2. Le fuzzy matching n'a pas trouvé d'alternative valide
        
        Args:
            product_data: Données du produit (Title, Type, Vendor, etc.)
            failed_category: Catégorie qui n'a pas été trouvée dans la taxonomie
            similar_categories: Liste de (code, path, score) de catégories similaires (optionnel)
            
        Returns:
            Path complet de la catégorie suggérée, ou None si échec
        """
        logger.info(f"🤖 Demande au LLM de suggérer une alternative pour: '{failed_category}'")
        
        if not self.ai_provider:
            logger.warning("⚠️ Provider LLM non disponible pour suggestion")
            return None
        
        try:
            # Construire la liste des suggestions similaires (si disponibles)
            suggestions_text = ""
            if similar_categories and len(similar_categories) > 0:
                suggestions_text = "\n\nCATÉGORIES SIMILAIRES DISPONIBLES:\n"
                for i, (code, path, score) in enumerate(similar_categories[:5], 1):
                    suggestions_text += f"{i}. {path} (similarité: {score:.2f})\n"
            
            # Construire le prompt pour le LLM
            prompt = f"""La catégorie suivante n'existe PAS dans la taxonomie Google Shopping:
"{failed_category}"

PRODUIT À CATÉGORISER:
- Titre: {product_data.get('Title', 'N/A')}
- Type: {product_data.get('Type', 'N/A')}
- Vendor: {product_data.get('Vendor', 'N/A')}
{suggestions_text}

QUESTION: Quelle catégorie SPÉCIFIQUE de la taxonomie Google Shopping serait la PLUS APPROPRIÉE pour ce produit?

⚠️ RÈGLES IMPORTANTES:
1. Choisis la catégorie la PLUS SPÉCIFIQUE possible (pas juste "Maison et jardin", mais "Maison et jardin > Cuisine > Ustensiles > Poêles")
2. La catégorie doit être un chemin COMPLET avec plusieurs niveaux (minimum 3 niveaux)
3. Si tu vois des suggestions ci-dessus, choisis-en une ou inspire-toi de leur structure
4. La catégorie doit EXISTER dans la taxonomie Google Shopping française

Réponds UNIQUEMENT avec le chemin complet de la catégorie (ex: "Maison et jardin > Arts de la table > Ustensiles de cuisson > Poêles").
Ne mets AUCUN texte supplémentaire, juste le chemin COMPLET de la catégorie.
"""
            
            # Récupérer max_tokens depuis la configuration (par défaut 5000, mais on limite à 1000 ici car c'est juste un chemin)
            max_tokens = 1000
            if self.db:
                configured_max = self.db.get_config_int('max_tokens', default=5000)
                # Pour ce cas d'usage (juste un chemin), on limite à 1000 même si la config est plus haute
                max_tokens = min(configured_max, 1000)
            
            # Appeler le LLM
            response = self.ai_provider.generate(prompt, max_tokens=max_tokens)
            suggested_category = response.strip().strip('"\'')
            
            logger.info(f"💡 LLM suggère: '{suggested_category}'")
            return suggested_category
        
        except Exception as e:
            logger.error(f"❌ Erreur lors de la suggestion LLM: {e}", exc_info=True)
            return None
