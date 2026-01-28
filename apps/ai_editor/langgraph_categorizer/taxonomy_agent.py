"""
Agent spécialiste pour la sélection dans la taxonomie Google Shopping française.
"""

import json
import logging
from typing import List, Tuple

logger = logging.getLogger(__name__)


class TaxonomySpecialistAgent:
    """Expert de la taxonomie Google Shopping française."""
    
    def __init__(self, gemini_provider, db=None):
        """
        Initialise l'agent spécialiste taxonomy.
        
        Args:
            gemini_provider: Instance de GeminiProvider
            db: Instance de AIPromptsDB (optionnel, pour configuration)
        """
        self.provider = gemini_provider
        self.db = db
    
    def select_category(
        self, 
        product_definition: dict, 
        candidates: List[Tuple[int, str]]
    ) -> Tuple[str, float, str]:
        # Sauvegarder product_definition pour le fallback
        self.product_definition = product_definition
        """
        Sélectionne la catégorie la plus appropriée.
        
        Args:
            product_definition: Définition du produit de l'agent produit
            candidates: Liste de (code, path) candidates
        
        Returns:
            (category_path, confidence, rationale)
        """
        # Formater les candidates
        candidates_text = "\n".join([
            f"{i+1}. {path}"
            for i, (code, path) in enumerate(candidates)
        ])
        
        prompt = f"""Taxonomie Google Shopping FR.

PRODUIT: {product_definition['product_type']} | USAGE: {product_definition['usage']}

CATÉGORIES (copie EXACTE):
{candidates_text}

RÈGLE: Choisis la PLUS SPÉCIFIQUE (min 3 niveaux: A>B>C), JAMAIS juste "Maison et jardin".

Réponds UN SEUL JSON compact:
{{"chosen_category":"chemin exact","confidence":0.95,"rationale":"raison 2-3 mots"}}"""

        try:
            # Récupérer max_tokens depuis la configuration (par défaut 5000)
            max_tokens = 5000
            if self.db:
                max_tokens = self.db.get_config_int('max_tokens', default=5000)
            
            response = self.provider.generate(prompt, max_tokens=max_tokens)
            logger.info(f"📤 Taxonomy Agent - Réponse brute LLM (max_tokens={max_tokens}): {response[:200]}...")
            
            # Parser JSON avec plusieurs méthodes
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
                logger.info(f"✓ Catégorie sélectionnée: {result['chosen_category']}")
                return (
                    result['chosen_category'],
                    float(result['confidence']),  # Convertir en float
                    result['rationale']
                )
            except json.JSONDecodeError as e:
                logger.warning(f"Parsing JSON direct échoué: {e}, tentative de réparation...")
                
                # Méthode 2: Utiliser json-repair
                try:
                    from json_repair import repair_json
                    repaired = repair_json(clean)
                    result = json.loads(repaired)
                    logger.info(f"✓ Catégorie sélectionnée (JSON réparé): {result['chosen_category']}")
                    
                    # Vérifier si on a au moins chosen_category (même si confidence/rationale manquent)
                    if 'chosen_category' in result and result['chosen_category']:
                        confidence = result.get('confidence')  # Peut être None, 0, "", etc.
                        
                        # Convertir confidence en float si nécessaire
                        if confidence is not None and confidence != '':
                            try:
                                confidence = float(confidence)
                                # Si 0 ou négatif, utiliser le défaut
                                if confidence <= 0:
                                    logger.warning(f"⚠️ Confidence invalide ({confidence}), utilisation de 0.6")
                                    confidence = 0.6
                            except (ValueError, TypeError):
                                logger.warning(f"⚠️ Confidence invalide '{confidence}', utilisation de 0.6")
                                confidence = 0.6
                        else:
                            # Confidence manquante ou vide
                            logger.warning(f"⚠️ Confidence manquante, utilisation de 0.6 par défaut")
                            confidence = 0.6
                        
                        rationale = result.get('rationale', 'JSON partiellement réparé, confidence/rationale manquants')
                        
                        if confidence != result.get('confidence') or rationale != result.get('rationale'):
                            logger.warning(f"⚠️ JSON partiel: chosen_category OK mais confidence/rationale par défaut")
                        
                        return (
                            result['chosen_category'],
                            confidence,
                            rationale
                        )
                    else:
                        raise ValueError("chosen_category manquante ou vide")
                    
                except Exception as e2:
                    logger.error(f"Réparation JSON échouée: {e2}")
                    raise
            
        except Exception as e:
            logger.error(f"Erreur totale parsing taxonomy JSON: {e}")
            logger.error(f"Réponse brute: {response[:200]}")
            
            # Fallback intelligent: chercher une catégorie pertinente basée sur les keywords
            if candidates and self.product_definition:
                product_type = self.product_definition.get('product_type', '').lower()
                usage = self.product_definition.get('usage', '').lower()
                
                # PRIORITÉ 1: Chercher dans "Maison et jardin" ou "Aliments, boissons et tabac" (90% des produits)
                priority_categories = []
                other_categories = []
                
                for code, path in candidates:
                    path_lower = path.lower()
                    if path_lower.startswith('maison et jardin') or path_lower.startswith('aliments, boissons et tabac'):
                        priority_categories.append((code, path, path_lower))
                    else:
                        other_categories.append((code, path, path_lower))
                
                # Chercher d'abord dans les catégories prioritaires
                search_categories = priority_categories + other_categories
                
                for code, path, path_lower in search_categories:
                    # TEXTILE/LINGE
                    if 'plaid' in product_type or 'couverture' in product_type:
                        if 'couverture' in path_lower or 'literie' in path_lower or 'linge de lit' in path_lower:
                            logger.info(f"⚠️ Fallback intelligent: {path}")
                            return (path, 0.65, f"Fallback: {product_type} → {path}")
                    
                    elif 'nappe' in product_type or 'serviette' in product_type:
                        if 'nappe' in path_lower or 'linge de table' in path_lower or 'serviette de table' in path_lower:
                            logger.info(f"⚠️ Fallback intelligent: {path}")
                            return (path, 0.65, f"Fallback: {product_type} → {path}")
                    
                    elif 'rideau' in product_type:
                        if 'rideau' in path_lower and 'embrasse' not in path_lower:
                            logger.info(f"⚠️ Fallback intelligent: {path}")
                            return (path, 0.65, f"Fallback: {product_type} → {path}")
                    
                    # ALIMENTS & BOISSONS
                    elif 'thé' in product_type or 'infusion' in product_type:
                        if 'thé' in path_lower or 'infusion' in path_lower:
                            logger.info(f"⚠️ Fallback intelligent: {path}")
                            return (path, 0.65, f"Fallback: {product_type} → {path}")
                    
                    elif 'café' in product_type:
                        if 'café' in path_lower:
                            logger.info(f"⚠️ Fallback intelligent: {path}")
                            return (path, 0.65, f"Fallback: {product_type} → {path}")
                    
                    elif 'épice' in product_type or 'condiment' in product_type:
                        if 'épice' in path_lower or 'assaisonnement' in path_lower:
                            logger.info(f"⚠️ Fallback intelligent: {path}")
                            return (path, 0.65, f"Fallback: {product_type} → {path}")
                    
                    # VAISSELLE & USTENSILES
                    elif 'vaisselle' in product_type or 'tasse' in product_type or 'mug' in product_type:
                        if 'vaisselle' in path_lower or 'tasse' in path_lower or 'mug' in path_lower:
                            logger.info(f"⚠️ Fallback intelligent: {path}")
                            return (path, 0.65, f"Fallback: {product_type} → {path}")
                    
                    elif 'ustensile' in product_type or 'casserole' in product_type:
                        if 'ustensile' in path_lower or 'batterie de cuisine' in path_lower or 'casserole' in path_lower:
                            logger.info(f"⚠️ Fallback intelligent: {path}")
                            return (path, 0.65, f"Fallback: {product_type} → {path}")
            
            # Dernier recours: première catégorie avec warning
            if candidates:
                logger.warning("❌ Fallback: Première catégorie par défaut (peut être incorrect)")
                return (candidates[0][1], 0.3, "Erreur parsing, première catégorie par défaut - NÉCESSITE RÉVISION")
            
            # Fallback absolu si vraiment aucune catégorie n'est disponible
            logger.error("❌ ERREUR: Aucune catégorie candidate disponible - Utilisation de 'Maison et jardin' par défaut")
            return ("Maison et jardin", 0.05, "Aucune catégorie pertinente trouvée - Catégorie générique par défaut")
