"""
Agent spécialiste pour la définition des produits textiles français.
"""

import json
import logging

logger = logging.getLogger(__name__)


class ProductSpecialistAgent:
    """Expert des produits textiles français."""
    
    def __init__(self, gemini_provider, db=None):
        """
        Initialise l'agent spécialiste produit.
        
        Args:
            gemini_provider: Instance de GeminiProvider
            db: Instance de AIPromptsDB (optionnel, pour configuration)
        """
        self.provider = gemini_provider
        self.db = db
    
    def analyze_product(self, product_data: dict) -> dict:
        """
        Analyse le produit et retourne une définition structurée.
        
        Args:
            product_data: Données du produit (Title, Type, Vendor, Tags, etc.)
        
        Returns:
            {
                "product_type": "plaid|nappe|serviette|...",
                "usage": "literie|table|salle_de_bain|...",
                "material": "coton|lin|...",
                "search_keywords": ["couverture", "lit", ...]
            }
        """
        prompt = f"""Analyse ce produit et réponds avec un JSON valide (une seule ligne).

PRODUIT: {product_data.get('Title', '')}
TYPE: {product_data.get('Type', '')}

CONTEXTE: 90% des produits sont dans "Maison et jardin" (textile, vaisselle, décoration, ustensiles) ou "Aliments, boissons et tabac" (thé, café, épices, biscuits).

RÈGLES:
- PLAID/COUVERTURE → usage="literie", keywords=["couverture","lit","literie"]
- NAPPE/SERVIETTE DE TABLE → usage="table", keywords=["nappe","linge de table"]
- RIDEAU → usage="fenetre", keywords=["rideau","fenetre"]
- THÉ/CAFÉ/ÉPICES → usage="boisson" ou "aliment", keywords appropriés
- VAISSELLE/TASSE/MUG → usage="vaisselle", keywords=["vaisselle","tasse","mug"]
- USTENSILES/CASSEROLE → usage="cuisine", keywords=["ustensile","cuisine"]

JSON (une ligne):
{{"product_type":"...","usage":"...","material":"...","search_keywords":["...","...","..."]}}

Réponds UNIQUEMENT le JSON."""

        try:
            # Récupérer max_tokens depuis la configuration (par défaut 5000)
            max_tokens = 5000
            if self.db:
                max_tokens = self.db.get_config_int('max_tokens', default=5000)
            
            response = self.provider.generate(prompt, max_tokens=max_tokens)
            logger.info(f"📤 Product Agent - Réponse brute LLM (max_tokens={max_tokens}): {response[:200]}...")
            
            # Parser le JSON avec plusieurs méthodes
            # Nettoyer la réponse (enlever markdown)
            clean = response.strip()
            if clean.startswith('```json'):
                clean = clean[7:]
            if clean.startswith('```'):
                clean = clean[3:]
            if clean.endswith('```'):
                clean = clean[:-3]
            clean = clean.strip()
            
            # Méthode 1: Parser directement
            try:
                result = json.loads(clean)
                logger.info(f"✓ Produit défini: {result['product_type']} - Usage: {result['usage']}")
                return result
            except json.JSONDecodeError as e:
                logger.warning(f"Parsing JSON direct échoué: {e}, tentative de réparation...")
                
                # Méthode 2: Utiliser json-repair
                try:
                    from json_repair import repair_json
                    repaired = repair_json(clean)
                    result = json.loads(repaired)
                    logger.info(f"✓ Produit défini (JSON réparé): {result['product_type']} - Usage: {result['usage']}")
                    return result
                except Exception as e2:
                    logger.error(f"Réparation JSON échouée: {e2}")
                    raise
            
        except Exception as e:
            logger.error(f"Erreur totale parsing JSON: {e}")
            logger.error(f"Réponse brute: {response[:200]}")
            # Fallback: Analyse basique du titre
            title_lower = product_data.get('Title', '').lower()
            
            # Détecter le type de produit depuis le titre
            product_type = product_data.get('Type', '')
            usage = "unknown"
            keywords = []
            
            if 'plaid' in title_lower:
                product_type = 'plaid'
                usage = 'literie'
                keywords = ['couverture', 'lit', 'literie', 'plaid']
            elif 'nappe' in title_lower:
                product_type = 'nappe'
                usage = 'table'
                keywords = ['nappe', 'table', 'linge de table']
            elif 'rideau' in title_lower:
                product_type = 'rideau'
                usage = 'fenetre'
                keywords = ['rideau', 'fenêtre', 'decoration']
            elif 'serviette' in title_lower:
                if 'bain' in title_lower or 'toilette' in title_lower:
                    product_type = 'serviette de bain'
                    usage = 'salle_de_bain'
                    keywords = ['serviette', 'bain', 'toilette']
                else:
                    product_type = 'serviette de table'
                    usage = 'table'
                    keywords = ['serviette', 'table', 'linge de table']
            else:
                keywords = [w for w in title_lower.split() if len(w) > 3][:5]
            
            logger.info(f"⚠️ Fallback utilisé: {product_type} - Usage: {usage}")
            return {
                "product_type": product_type,
                "usage": usage,
                "material": "",
                "search_keywords": keywords if keywords else [product_data.get('Title', '')]
            }
