"""
Tools de recherche Internet pour les agents IA.
"""

import logging
from typing import Optional

logger = logging.getLogger(__name__)


class SearchToolError(Exception):
    """Exception pour les erreurs des tools de recherche."""
    pass


def _is_quota_error(error_message: str) -> bool:
    """
    Détecte si une erreur est liée au quota/tokens insuffisants.
    
    Args:
        error_message: Message d'erreur à analyser
        
    Returns:
        True si c'est une erreur de quota
    """
    quota_keywords = [
        'quota',
        'insufficient',
        'exceeded',
        'rate limit',
        'too many requests',
        'credits',
        'billing',
        'payment',
        'tokens',
        'usage limit',
        '429',  # HTTP status code pour rate limiting
        'over capacity',
        'overloaded'
    ]
    
    error_lower = error_message.lower()
    return any(keyword in error_lower for keyword in quota_keywords)


class PerplexitySearchTool:
    """
    Tool de recherche Internet via Perplexity AI.
    
    Perplexity utilise une API compatible OpenAI avec des modèles spécialisés
    dans la recherche en temps réel sur Internet.
    """
    
    # Modèles Perplexity disponibles (2026)
    AVAILABLE_MODELS = [
        "sonar",                    # Base - Recherche Internet (recommandé)
        "sonar-reasoning",          # Avec capacités de raisonnement
        "sonar-pro",               # Version avancée
        "sonar-reasoning-pro"      # Pro avec raisonnement
    ]
    
    DEFAULT_MODEL = "sonar"
    
    def __init__(self, api_key: str, model: str = None):
        """
        Initialise le tool de recherche Perplexity.
        
        Args:
            api_key: Clé API Perplexity
            model: Modèle à utiliser (défaut: sonar)
        """
        try:
            from openai import OpenAI
            self.OpenAI = OpenAI
        except ImportError:
            raise SearchToolError("La bibliothèque 'openai' n'est pas installée.")
        
        if not api_key:
            raise SearchToolError("PERPLEXITY_API_KEY n'est pas définie.")
        
        # Perplexity utilise une API compatible OpenAI
        self.client = self.OpenAI(
            api_key=api_key,
            base_url="https://api.perplexity.ai"
        )
        
        # Utiliser le modèle spécifié ou le modèle par défaut
        self.model = model if model in self.AVAILABLE_MODELS else self.DEFAULT_MODEL
        
        logger.info(f"Tool Perplexity initialisé avec le modèle {self.model}")
    
    def list_models_from_api(self) -> list[str]:
        """
        Récupère la liste des modèles disponibles depuis l'API Perplexity.
        
        Returns:
            Liste des noms de modèles
            
        Raises:
            SearchToolError: Si la requête échoue
        """
        try:
            logger.info("🔍 Récupération de la liste des modèles Perplexity depuis l'API...")
            
            # L'API Perplexity est compatible OpenAI, donc on peut utiliser models.list()
            models_response = self.client.models.list()
            
            # Filtrer les modèles "sonar" (recherche Internet)
            sonar_models = []
            for model in models_response.data:
                model_id = model.id.lower()
                if 'sonar' in model_id:
                    sonar_models.append(model.id)
            
            if sonar_models:
                logger.info(f"✅ {len(sonar_models)} modèle(s) Perplexity trouvé(s)")
                return sorted(sonar_models)
            else:
                # Fallback sur la liste codée en dur
                logger.warning("⚠️ Aucun modèle trouvé, utilisation de la liste par défaut")
                return self.AVAILABLE_MODELS.copy()
                
        except Exception as e:
            logger.warning(f"⚠️ Impossible de récupérer les modèles depuis l'API: {e}")
            # Retourner la liste par défaut en cas d'erreur
            return self.AVAILABLE_MODELS.copy()
    
    @classmethod
    def list_models(cls) -> list[str]:
        """
        Retourne la liste des modèles Perplexity disponibles (version statique).
        
        Returns:
            Liste des noms de modèles
        """
        return cls.AVAILABLE_MODELS.copy()
    
    def search(self, query: str, max_tokens: int = 800) -> str:
        """
        Effectue une recherche sur Internet et retourne les résultats.
        
        Args:
            query: Question ou recherche à effectuer
            max_tokens: Nombre maximum de tokens pour la réponse
            
        Returns:
            Résultats de recherche avec informations factuelles et sources
            
        Raises:
            SearchToolError: Si la recherche échoue
        """
        try:
            logger.info(f"🔍 Recherche Perplexity: {query}")
            
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": (
                            "Tu es un assistant de recherche expert. "
                            "Fournis des informations factuelles, précises et à jour. "
                            "Cite tes sources quand c'est pertinent. "
                            "Sois concis et direct dans tes réponses."
                        )
                    },
                    {
                        "role": "user",
                        "content": query
                    }
                ],
                max_tokens=max_tokens,
                temperature=0.2,  # Plus bas pour des résultats factuels
            )
            
            result = response.choices[0].message.content.strip()
            logger.info(f"✅ Résultats de recherche reçus ({len(result)} caractères)")
            logger.info(f"📄 Contenu de la réponse Perplexity:\n{'-'*60}\n{result}\n{'-'*60}")
            
            return result
            
        except Exception as e:
            error_msg = str(e)
            logger.error(f"❌ Erreur lors de la recherche Perplexity: {error_msg}")
            
            # Détecter les erreurs de quota/tokens
            if _is_quota_error(error_msg):
                # Importer ici pour éviter les imports circulaires
                from utils.ai_providers import AIQuotaError
                
                raise AIQuotaError(
                    "Perplexity",
                    "❌ Quota Perplexity dépassé ou tokens insuffisants.\n\n"
                    "Solutions :\n"
                    "• Vérifiez votre compte Perplexity : https://www.perplexity.ai/settings/api\n"
                    "• Rechargez des crédits si nécessaire\n"
                    "• Vérifiez les limites de votre plan\n"
                    f"• Erreur : {error_msg}",
                    error_msg
                )
            
            raise SearchToolError(f"Erreur de recherche: {e}")
    
    def get_tool_definition(self) -> dict:
        """
        Retourne la définition du tool pour OpenAI Function Calling.
        
        Returns:
            Dictionnaire de définition du tool au format OpenAI
        """
        return {
            "type": "function",
            "function": {
                "name": "search_web",
                "description": (
                    "Recherche des informations sur Internet pour obtenir des détails "
                    "à jour sur un produit, une marque, un savoir-faire, etc. "
                    "Utilise cette fonction UNIQUEMENT si tu manques d'informations "
                    "factuelles pour générer une description complète et précise."
                ),
                "parameters": {
                    "type": "object",
                    "properties": {
                        "query": {
                            "type": "string",
                            "description": (
                                "Question ou recherche à effectuer en français. "
                                "Exemples: 'nappe artiga adour vert caractéristiques fabrication', "
                                "'marque Garnier-Thiebaut histoire savoir-faire'"
                            )
                        }
                    },
                    "required": ["query"],
                    "additionalProperties": False
                }
            }
        }
    
    def get_tool_definition_claude(self) -> dict:
        """
        Retourne la définition du tool pour Claude (Anthropic) Tool Use.
        
        Returns:
            Dictionnaire de définition du tool au format Claude
        """
        return {
            "name": "search_web",
            "description": (
                "Recherche des informations sur Internet pour obtenir des détails "
                "à jour sur un produit, une marque, un savoir-faire, etc. "
                "Utilise cette fonction UNIQUEMENT si tu manques d'informations "
                "factuelles pour générer une description complète et précise."
            ),
            "input_schema": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": (
                            "Question ou recherche à effectuer en français. "
                            "Exemples: 'nappe artiga adour vert caractéristiques fabrication', "
                            "'marque Garnier-Thiebaut histoire savoir-faire'"
                        )
                    }
                },
                "required": ["query"]
            }
        }