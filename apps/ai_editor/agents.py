"""
Module des agents IA pour le traitement des produits.
"""

import json
import logging
from typing import Dict, Any, Optional, List, Callable
from abc import ABC, abstractmethod

logger = logging.getLogger(__name__)


class BaseAIAgent(ABC):
    """Classe de base pour les agents IA."""
    
    def __init__(self, ai_provider, system_prompt: str, specific_prompt: str):
        """
        Initialise l'agent IA.
        
        Args:
            ai_provider: Instance de AIProvider (OpenAIProvider, ClaudeProvider, GeminiProvider)
            system_prompt: Prompt système global
            specific_prompt: Prompt spécifique à cet agent
        """
        self.ai_provider = ai_provider
        self.system_prompt = system_prompt
        self.specific_prompt = specific_prompt
        self.tools: List[Callable] = []  # Liste de fonctions/tools disponibles
    
    def add_tool(self, tool_function: Callable):
        """
        Ajoute un tool/fonction à l'agent.
        
        Args:
            tool_function: Fonction à ajouter comme tool
        """
        self.tools.append(tool_function)
        logger.debug(f"Tool ajouté à {self.__class__.__name__}: {tool_function.__name__}")
    
    def _build_context(self, product_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Construit le contexte à partir des données du produit.
        
        Args:
            product_data: Dictionnaire contenant les données du produit
            
        Returns:
            Dictionnaire de contexte formaté
        """
        context = {}
        
        # Extraire les champs principaux
        if 'Title' in product_data:
            context['title'] = product_data['Title']
        if 'Vendor' in product_data:
            context['vendor'] = product_data['Vendor']
        if 'Type' in product_data:
            context['type'] = product_data['Type']
        if 'Tags' in product_data:
            context['tags'] = product_data['Tags']
        if 'Body (HTML)' in product_data:
            context['body_html'] = product_data['Body (HTML)']
        if 'Handle' in product_data:
            context['handle'] = product_data['Handle']
        
        # Ajouter d'autres champs pertinents
        if 'Variant SKU' in product_data:
            context['sku'] = product_data['Variant SKU']
        if 'Variant Price' in product_data:
            context['price'] = product_data['Variant Price']
        if 'Google Shopping / Google Product Category' in product_data:
            context['google_category'] = product_data['Google Shopping / Google Product Category']
        
        return context
    
    def _build_full_prompt(self, product_data: Dict[str, Any]) -> str:
        """
        Construit le prompt complet avec TOUTES les données CSV du produit.
        
        Args:
            product_data: Données du produit (tous les champs CSV)
            
        Returns:
            Prompt complet
        """
        # Envoyer TOUS les champs CSV disponibles
        context_str = "===== LIGNE CSV COMPLÈTE DU PRODUIT =====\n\n"
        
        # Champs principaux en premier
        important_fields = [
            'Handle', 'Title', 'Body (HTML)', 'Vendor', 'Type', 'Tags',
            'Variant SKU', 'Variant Price', 'Option1 Name', 'Option1 Value',
            'Option2 Name', 'Option2 Value', 'SEO Title', 'SEO Description',
            'Image Alt Text', 'Google Shopping / Google Product Category'
        ]
        
        # Afficher les champs importants d'abord
        for field in important_fields:
            if field in product_data:
                value = product_data[field]
                if value:  # Afficher seulement si non vide
                    # Tronquer le Body HTML s'il est trop long
                    if field == 'Body (HTML)' and len(str(value)) > 500:
                        context_str += f"{field}: {str(value)[:500]}... (tronqué)\n"
                    else:
                        context_str += f"{field}: {value}\n"
        
        # Afficher les autres champs (sauf ceux déjà affichés)
        context_str += "\n--- Autres champs disponibles ---\n"
        for field, value in product_data.items():
            if field not in important_fields and value:
                context_str += f"{field}: {value}\n"
        
        # Construire le prompt complet
        full_prompt = f"{self.system_prompt}\n\n"
        full_prompt += context_str + "\n"
        full_prompt += "IMPORTANT : Tu as accès à TOUTES les données ci-dessus. Utilise-les pour générer du contenu riche.\n"
        full_prompt += "Si les champs Body (HTML) ou Tags existent déjà, tu DOIS les réutiliser/améliorer, JAMAIS les ignorer !\n\n"
        full_prompt += self.specific_prompt
        
        return full_prompt
    
    @abstractmethod
    def generate(self, product_data: Dict[str, Any], **kwargs) -> Any:
        """
        Génère la réponse avec l'IA.
        
        Args:
            product_data: Données du produit
            **kwargs: Arguments supplémentaires
            
        Returns:
            Résultat généré par l'agent
        """
        pass
    
    def generate_batch(self, products_data: List[Dict[str, Any]], **kwargs) -> List[Dict[str, Any]]:
        """
        Génère les résultats pour un batch de produits en une seule requête API.
        
        Args:
            products_data: Liste de dictionnaires contenant les données des produits
            **kwargs: Arguments supplémentaires
            
        Returns:
            Liste de dictionnaires {handle: str, ...champs générés...}
            
        Raises:
            ValueError: Si la réponse JSON est invalide
            Exception: Si l'API échoue
        """
        if not products_data:
            return []
        
        # Construire le prompt pour le batch
        batch_prompt = self._build_batch_prompt(products_data, **kwargs)
        
        # Appeler l'IA avec plus de tokens pour les batch
        logger.info(f"Traitement batch de {len(products_data)} produits...")
        # Augmenter max_tokens pour les batch: 8000 pour avoir assez d'espace pour tous les produits
        response = self.ai_provider.generate(batch_prompt, max_tokens=8000)
        
        # Parser la réponse JSON avec json-repair pour réparer automatiquement
        response_clean = self._clean_json_response(response)
        
        result = None
        parse_error = None
        
        # Tentative 1: Parser directement avec json standard
        try:
            result = json.loads(response_clean)
            logger.info("✓ JSON valide (parsing standard)")
        except json.JSONDecodeError as e:
            parse_error = e
            logger.warning(f"JSON invalide, tentative de réparation: {e}")
            
            # Tentative 2: Utiliser json-repair pour réparer automatiquement
            try:
                from json_repair import repair_json
                
                # Réparer le JSON cassé
                repaired_json = repair_json(response_clean)
                result = json.loads(repaired_json)
                logger.info("✓ JSON réparé avec succès (json-repair)")
                
            except Exception as e2:
                logger.error(f"Échec de la réparation JSON: {e2}")
                logger.error(f"Réponse reçue (300 premiers chars): {response[:300]}...")
                
                # Sauvegarder la réponse complète pour déboguer
                try:
                    import tempfile
                    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False, prefix='ai_response_') as f:
                        f.write(f"=== RÉPONSE BRUTE ===\n{response}\n\n")
                        f.write(f"=== APRÈS NETTOYAGE ===\n{response_clean}\n")
                        logger.error(f"Réponse complète sauvegardée dans: {f.name}")
                except Exception:
                    pass
                
                raise ValueError(f"Réponse JSON invalide et impossible à réparer: {parse_error}")
        
        # Valider la structure
        if not isinstance(result, dict) or 'products' not in result:
            raise ValueError("Format JSON invalide: clé 'products' manquante")
        
        products = result['products']
        if not isinstance(products, list):
            raise ValueError("Format JSON invalide: 'products' n'est pas une liste")
        
        logger.info(f"Batch traité: {len(products)}/{len(products_data)} produits retournés")
        return products
    
    def _clean_json_response(self, response: str) -> str:
        """
        Nettoie une réponse pour extraire et corriger le JSON.
        
        Args:
            response: Réponse brute de l'IA
            
        Returns:
            JSON nettoyé prêt à être parsé
        """
        import re
        
        # Étape 1: Nettoyer les espaces
        response_clean = response.strip()
        
        # Étape 2: Extraire le JSON si entouré de ```json ou ```
        if response_clean.startswith('```'):
            # Trouver le contenu entre ``` et ```
            match = re.search(r'```(?:json)?\s*\n(.*?)(?:\n```|$)', response_clean, re.DOTALL)
            if match:
                response_clean = match.group(1).strip()
            else:
                # Cas où il n'y a pas de ``` de fermeture
                lines = response_clean.split('\n')
                if len(lines) > 1:
                    response_clean = '\n'.join(lines[1:])
        
        # Étape 3: Trouver le premier { et le dernier }
        first_brace = response_clean.find('{')
        last_brace = response_clean.rfind('}')
        
        if first_brace != -1 and last_brace != -1 and last_brace > first_brace:
            response_clean = response_clean[first_brace:last_brace + 1]
        
        # Étape 4: Corrections courantes pour les erreurs JSON
        # Échapper les retours à la ligne non échappés dans les chaînes
        # Cette approche n'est pas parfaite mais aide dans beaucoup de cas
        
        # Remplacer les retours à la ligne littéraux par \n dans les valeurs de chaînes
        # Pattern: entre guillemets doubles, remplacer \n par \\n
        def escape_newlines(match):
            content = match.group(1)
            # Échapper les retours à la ligne
            content = content.replace('\n', '\\n').replace('\r', '\\r')
            # Échapper les tabulations
            content = content.replace('\t', '\\t')
            return f'"{content}"'
        
        # Cette regex trouve les chaînes entre guillemets et échappe leur contenu
        # Attention: ceci est une simplification et peut ne pas gérer tous les cas
        try:
            # Trouver toutes les paires de guillemets et échapper le contenu
            # On utilise une approche plus simple: remplacer les \n non échappés
            response_clean = response_clean.replace('\\\n', '\\n')  # Garder les \n déjà échappés
        except Exception:
            pass
        
        return response_clean
    
    def _build_batch_prompt(self, products_data: List[Dict[str, Any]], **kwargs) -> str:
        """
        Construit le prompt pour un batch de produits.
        
        Args:
            products_data: Liste des données de produits
            **kwargs: Arguments supplémentaires
            
        Returns:
            Prompt complet pour le batch
        """
        # Header du prompt
        batch_count = len(products_data)
        prompt = f"{self.system_prompt}\n\n{self.specific_prompt}\n\n"
        prompt += f"""
⚠️ INSTRUCTION CRITIQUE ⚠️
Tu dois traiter EXACTEMENT {batch_count} produits ci-dessous.
Tu DOIS retourner les {batch_count} produits dans ta réponse JSON.
Si tu omets un seul produit, la réponse sera considérée comme INVALIDE.

Compte des produits à traiter: {batch_count}
Compte des produits que tu DOIS retourner: {batch_count}

"""
        
        # Ajouter chaque produit
        for idx, product_data in enumerate(products_data, 1):
            handle = product_data.get('Handle', f'produit-{idx}')
            prompt += f"{'='*60}\n"
            prompt += f"PRODUIT {idx}/{batch_count}\n"
            prompt += f"Handle: {handle}\n"
            prompt += f"{'='*60}\n\n"
            prompt += self._build_full_prompt(product_data)
            prompt += "\n\n"
        
        # Instructions de format de sortie (à surcharger dans les classes filles)
        prompt += self._get_batch_output_format(products_data)
        
        return prompt
    
    def _get_batch_output_format(self, products_data: List[Dict[str, Any]]) -> str:
        """
        Retourne les instructions de format de sortie pour le batch.
        À surcharger dans les classes filles.
        
        Args:
            products_data: Liste des données de produits
            
        Returns:
            Instructions de format JSON
        """
        handles = [p.get('Handle', '') for p in products_data]
        return f"""
IMPORTANT:
- Tu DOIS retourner les {len(products_data)} produits
- Utilise les handles EXACTS fournis: {', '.join(handles)}
- Si des données manquent, génère quand même du contenu
- Retourne un JSON valide avec ce format EXACT:

{{
  "products": [
    {{"handle": "{handles[0]}", ...champs...}},
    ...
  ]
}}
"""


class GoogleShoppingAgent(BaseAIAgent):
    """Agent pour optimiser les champs Google Shopping (principalement Google Product Category)."""
    
    def __init__(self, ai_provider, system_prompt: str, specific_prompt: str):
        """Initialise l'agent Google Shopping."""
        super().__init__(ai_provider, system_prompt, specific_prompt)
        self.db = None  # Référence à la base de données (pour taxonomie)
    
    def set_database(self, db):
        """
        Configure l'accès à la base de données pour accéder à la taxonomie Google Shopping.
        
        Args:
            db: Instance de AIPromptsDB
        """
        self.db = db
        logger.info("Agent Google Shopping configuré avec accès à la taxonomie")
    
    def _get_taxonomy_sample(self, product_data: Dict[str, Any]) -> str:
        """
        Récupère un échantillon pertinent de catégories de la taxonomie.
        IMPORTANT: Les catégories retournées sont les SEULES options valides.
        
        Args:
            product_data: Données du produit
            
        Returns:
            Chaîne avec des exemples de catégories pertinentes
        """
        if not self.db:
            return ""
        
        try:
            # Utiliser la nouvelle méthode pour obtenir les catégories candidates
            # Réduit à 15 pour optimiser la vitesse (au lieu de 25)
            candidates = self.db.get_candidate_categories(product_data, max_results=15)
            
            if candidates:
                taxonomy_text = "\n\n📚 CATÉGORIES VALIDES (CHOISIS UNIQUEMENT PARMI CETTE LISTE):\n"
                for i, (code, path) in enumerate(candidates, 1):
                    taxonomy_text += f"  {i}. {path}\n"
                
                taxonomy_text += "\n⚠️ IMPORTANT: Tu DOIS choisir UNE catégorie de cette liste. N'invente PAS de nouvelle catégorie!"
                return taxonomy_text
            
        except Exception as e:
            logger.warning(f"Erreur lors de la récupération de la taxonomie: {e}")
        
        return ""
    
    def _build_full_prompt(self, product_data: Dict[str, Any]) -> str:
        """
        Construit le prompt complet avec les catégories disponibles.
        
        Args:
            product_data: Données du produit
            
        Returns:
            Prompt enrichi avec la taxonomie
        """
        # Prompt de base
        base_prompt = super()._build_full_prompt(product_data)
        
        # Ajouter un échantillon de catégories pertinentes
        taxonomy_sample = self._get_taxonomy_sample(product_data)
        
        if taxonomy_sample:
            base_prompt += taxonomy_sample
            base_prompt += "\n\n⚠️ RÈGLE ABSOLUE: Tu DOIS choisir UNIQUEMENT une catégorie de la liste ci-dessus.\n"
            base_prompt += "N'invente JAMAIS de nouvelle catégorie. Si aucune ne correspond parfaitement, choisis la plus proche.\n"
        else:
            base_prompt += "\n\n⚠️ ATTENTION: Aucune catégorie candidate trouvée. Choisis une catégorie générale valide.\n"
        
        return base_prompt
    
    def generate(self, product_data: Dict[str, Any], **kwargs) -> str:
        """
        Génère la catégorie Google Shopping pour le produit.
        
        Args:
            product_data: Données du produit
            
        Returns:
            Catégorie Google Shopping (ex: "Apparel & Accessories > Clothing > Shirts & Tops")
        """
        prompt = self._build_full_prompt(product_data)
        
        try:
            # Appeler l'IA avec le prompt ET toutes les données CSV comme contexte
            # Note: enable_search est déjà à False pour cet agent (configuré dans processor.py)
            response = self.ai_provider.generate(prompt, context=product_data)
            
            # Nettoyer la réponse
            response = response.strip()
            
            # Enlever les guillemets si présents
            if response.startswith('"') and response.endswith('"'):
                response = response[1:-1]
            if response.startswith("'") and response.endswith("'"):
                response = response[1:-1]
            
            logger.debug(f"Catégorie Google Shopping générée pour {product_data.get('Handle', 'unknown')}: {response}")
            return response
            
        except Exception as e:
            logger.error(f"Erreur lors de la génération de la catégorie Google Shopping: {e}")
            raise
    
    def _get_batch_output_format(self, products_data: List[Dict[str, Any]]) -> str:
        """Format de sortie JSON pour le batch Google Shopping."""
        handles = [p.get('Handle', '') for p in products_data]
        return f"""
RETOURNE un JSON valide avec ce format EXACT:

{{
  "products": [
    {{
      "handle": "{handles[0] if handles else 'exemple'}",
      "google_category": "Chemin complet de la catégorie (ex: Home & Garden > Kitchen & Dining > Table Linens)"
    }},
    ... (pour TOUS les {len(products_data)} produits)
  ]
}}

RÈGLES JSON STRICTES:
- Utilise UNIQUEMENT des guillemets doubles " pour les clés et valeurs (JAMAIS de guillemets simples ')
- Toutes les clés doivent être entre guillemets doubles: "handle", "google_category"
- Pas de virgule après le dernier élément d'un objet ou tableau
- JAMAIS de vrais retours à la ligne dans les valeurs (utilise \\n si nécessaire)
- Retourne UNIQUEMENT le JSON, sans texte avant ou après

CONTENU:
- Tu DOIS retourner les {len(products_data)} produits
- Utilise les handles EXACTS: {', '.join(handles[:5])}{'...' if len(handles) > 5 else ''}
- Chaque produit doit avoir le champ google_category
- Retourne UNIQUEMENT le chemin textuel de la catégorie (ex: "Home & Garden > Linens > Table Linens")
- Si tu es incertain, choisis la catégorie la plus pertinente
"""


class SEOAgent(BaseAIAgent):
    """Agent pour optimiser tous les champs SEO Shopify."""
    
    def generate(self, product_data: Dict[str, Any], **kwargs) -> Dict[str, Any]:
        """
        Génère tous les champs SEO pour le produit.
        
        Args:
            product_data: Données du produit
            
        Returns:
            Dict avec 7 clés :
            - seo_title: SEO Title
            - seo_description: SEO Description
            - title: Title
            - body_html: Body (HTML)
            - tags: Tags
            - image_alt_text: Image Alt Text
            - type: Type de produit en MAJUSCULES, PLURIEL, SANS ACCENTS (ex: "NAPPES", "TORCHONS", "PLAIDS")
            
        Note: Le champ 'type' est utilisé à la fois pour le CSV Shopify ET pour la concordance interne (csv_type).
        """
        prompt = self._build_full_prompt(product_data)
        
        # LOG: Afficher le prompt COMPLET envoyé à l'agent
        logger.info(f"📤 PROMPT COMPLET envoyé à l'agent SEO pour {product_data.get('Handle', 'unknown')}:")
        logger.info(f"--- DÉBUT PROMPT ---")
        logger.info(prompt[:2000] + ("..." if len(prompt) > 2000 else ""))  # Limiter à 2000 chars
        logger.info(f"--- FIN PROMPT (longueur totale: {len(prompt)} caractères) ---")
        
        try:
            # Appeler l'IA avec le prompt ET toutes les données CSV comme contexte
            response = self.ai_provider.generate(prompt, context=product_data)
            
            # Parser la réponse (peut être JSON ou format texte)
            response = response.strip()
            
            # LOG: Afficher la réponse brute pour déboguer
            logger.info(f"📝 Réponse brute de l'agent SEO pour {product_data.get('Handle', 'unknown')}:")
            logger.info(f"--- DÉBUT RÉPONSE ---")
            logger.info(response[:1000] + ("..." if len(response) > 1000 else ""))
            logger.info(f"--- FIN RÉPONSE ---")
            
            # Nettoyer les backticks markdown si présents
            response_cleaned = response.strip()
            if response_cleaned.startswith('```json'):
                response_cleaned = response_cleaned[7:].strip()
            elif response_cleaned.startswith('```'):
                response_cleaned = response_cleaned[3:].strip()
            
            if response_cleaned.endswith('```'):
                response_cleaned = response_cleaned[:-3].strip()
            
            # Essayer de parser comme JSON d'abord
            try:
                result = json.loads(response_cleaned)
                if isinstance(result, dict):
                    # Nettoyer le body_html si présent (enlever les markdown)
                    if 'body_html' in result:
                        body_html = result['body_html'].strip()
                        if body_html.startswith('```html'):
                            body_html = body_html[7:]
                        if body_html.startswith('```'):
                            body_html = body_html[3:]
                        if body_html.endswith('```'):
                            body_html = body_html[:-3]
                        result['body_html'] = body_html.strip()
                    
                    return {
                        'seo_title': result.get('seo_title', ''),
                        'seo_description': result.get('seo_description', ''),
                        'title': result.get('title', ''),
                        'body_html': result.get('body_html', ''),
                        'tags': result.get('tags', ''),
                        'image_alt_text': result.get('image_alt_text', ''),
                        'type': result.get('type', '')
                    }
            except json.JSONDecodeError:
                pass
            
            # Si ce n'est pas du JSON, essayer de parser un format texte structuré
            lines = response.split('\n')
            result = {
                'seo_title': '',
                'seo_description': '',
                'title': '',
                'body_html': '',
                'tags': '',
                'image_alt_text': '',
                'type': ''
            }
            
            current_field = None
            current_value = []
            
            field_markers = {
                'SEO Title:': 'seo_title',
                'SEO Description:': 'seo_description',
                'Title:': 'title',
                'Body HTML:': 'body_html',
                'Body (HTML):': 'body_html',
                'Tags:': 'tags',
                'Image Alt Text:': 'image_alt_text',
                'Type:': 'type'
            }
            
            for line in lines:
                line = line.strip()
                if not line:
                    continue
                
                # Vérifier si c'est un marqueur de champ
                field_found = False
                for marker, field_key in field_markers.items():
                    if line.startswith(marker):
                        if current_field:
                            result[current_field] = ' '.join(current_value).strip()
                        current_field = field_key
                        current_value = [line.replace(marker, '').strip()]
                        field_found = True
                        break
                
                if not field_found and current_field:
                    current_value.append(line)
            
            # Ajouter le dernier champ
            if current_field:
                result[current_field] = ' '.join(current_value).strip()
            
            # Nettoyer le body_html (enlever les markdown si présent)
            if result['body_html']:
                body_html = result['body_html']
                if body_html.startswith('```html'):
                    body_html = body_html[7:]
                if body_html.startswith('```'):
                    body_html = body_html[3:]
                if body_html.endswith('```'):
                    body_html = body_html[:-3]
                result['body_html'] = body_html.strip()
            
            # Si aucun champ n'a été trouvé, utiliser des valeurs par défaut
            if not any(result.values()):
                result['seo_title'] = product_data.get('Title', '')[:60]
                result['seo_description'] = product_data.get('Title', '')[:160]
                result['title'] = product_data.get('Title', '')
                result['image_alt_text'] = product_data.get('Title', '')
            
            # LOG: Afficher les champs extraits incluant csv_type
            logger.info(f"✅ SEO généré pour {product_data.get('Handle', 'unknown')}:")
            logger.info(f"  • csv_type: {result.get('csv_type', 'N/A')}")
            logger.info(f"  • csv_type_confidence: {result.get('csv_type_confidence', 0.0):.2f}")
            logger.debug(f"  • seo_title: {result.get('seo_title', '')[:50]}...")
            
            return result
            
        except Exception as e:
            logger.error(f"Erreur lors de la génération SEO: {e}")
            raise
    
    def _get_batch_output_format(self, products_data: List[Dict[str, Any]]) -> str:
        """Format de sortie JSON pour le batch SEO."""
        handles = [p.get('Handle', '') for p in products_data]
        return f"""
RETOURNE un JSON valide avec ce format EXACT:

{{
  "products": [
    {{
      "handle": "{handles[0] if handles else 'exemple'}",
      "seo_title": "Titre SEO optimisé (50-60 caractères)",
      "seo_description": "Meta description SEO (150-160 caractères)",
      "title": "Titre Shopify du produit",
      "body_html": "<p>Description HTML complète et riche</p>",
      "tags": "tag1, tag2, tag3",
      "image_alt_text": "Description de l'image pour SEO",
      "type": "NAPPES"
    }},
    {{
      "handle": "exemple-torchon",
      "seo_title": "...",
      "seo_description": "...",
      "title": "Torchon Éponge Bio",
      "body_html": "...",
      "tags": "...",
      "image_alt_text": "...",
      "type": "TORCHONS"
    }},
    ... (pour TOUS les {len(products_data)} produits)
  ]
}}

RÈGLES JSON STRICTES:
- Utilise UNIQUEMENT des guillemets doubles " pour les clés et valeurs (JAMAIS de guillemets simples ')
- Toutes les clés doivent être entre guillemets doubles: "handle", "seo_title", etc.
- Pas de virgule après le dernier élément d'un objet ou tableau
- Échappe les caractères spéciaux: \" pour guillemets, \\n pour retour à la ligne, \\t pour tabulation
- JAMAIS de vrais retours à la ligne dans les valeurs de chaînes (utilise \\n à la place)
- Pour le HTML dans body_html, mets tout sur une seule ligne ou utilise des \\n
- Retourne UNIQUEMENT le JSON, sans texte avant ou après

INSTRUCTIONS CSV_TYPE (TRÈS IMPORTANT):
- Le csv_type doit être déterminé en analysant UNIQUEMENT le Title (nom du produit)
- IGNORE complètement le champ Type original qui peut être générique (ex: "Accessoire", "Linge de table")
- Analyse sémantiquement le Title pour identifier la vraie nature du produit
- Exemples de transformation:
  * Title: "Nappe en Coton Jacquard" → csv_type: "NAPPES"
  * Title: "Torchon Éponge Absorbant" → csv_type: "TORCHONS"
  * Title: "Plaid Laine Mérinos" → csv_type: "COUVERTURES"
  * Title: "Serviette de Table Lin" → csv_type: "SERVIETTES"
  * Title: "Chemin de Table Festif" → csv_type: "CHEMINS DE TABLE"
- Utilise toujours le PLURIEL et les MAJUSCULES
- Si incertain, mets une confiance plus faible (0.6-0.7) mais propose quand même un csv_type

CONTENU:
⚠️ OBLIGATOIRE: Tu DOIS retourner EXACTEMENT {len(products_data)} produits dans le tableau "products"
- Liste des handles à retourner: {', '.join(handles[:5])}{'...' if len(handles) > 5 else ''}
- Compte de produits attendus: {len(products_data)}
- Chaque produit DOIT avoir les 7 champs: seo_title, seo_description, title, body_html, tags, image_alt_text, type
- type: Type de produit au PLURIEL, en MAJUSCULES, SANS ACCENTS (ex: "NAPPES", "TORCHONS", "PLAIDS", "SERVIETTES DE TABLE", "CHEMINS DE TABLE")
- IMPORTANT: Analyser sémantiquement le Title (nom du produit) pour déterminer le type (ex: "Nappe Coton" → "NAPPES", "Torchon Éponge" → "TORCHONS")
- Si des données manquent, génère quand même du contenu de qualité basé sur ce qui est disponible
- NE SAUTE AUCUN PRODUIT, même si les données sont limitées

VÉRIFICATION FINALE:
Avant de retourner ta réponse, compte le nombre d'objets dans ton tableau "products".
Il DOIT être égal à {len(products_data)}. Si ce n'est pas le cas, AJOUTE les produits manquants.
"""


class QualityControlAgent(BaseAIAgent):
    """
    Agent de contrôle qualité qui vérifie que tous les champs requis sont correctement remplis.
    Peut identifier les champs manquants ou de mauvaise qualité.
    """
    
    def generate(self, product_data: Dict[str, Any], **kwargs) -> Any:
        """
        Méthode generate non utilisée pour le QualityControlAgent.
        Cet agent utilise validate_seo_result() et generate_retry_prompt().
        """
        raise NotImplementedError("QualityControlAgent n'utilise pas generate(), utilisez validate_seo_result()")
    
    def validate_seo_result(self, 
                           product_data: Dict[str, Any], 
                           seo_result: Dict[str, str], 
                           required_fields: List[str]) -> Dict[str, Any]:
        """
        Valide les résultats SEO et identifie les champs manquants ou problématiques.
        
        Args:
            product_data: Données originales du produit
            seo_result: Résultats générés par le SEOAgent
            required_fields: Liste des champs requis (ex: ['seo_title', 'body_html'])
            
        Returns:
            Dict avec:
            - is_valid: bool (True si tous les champs requis sont OK)
            - missing_fields: List[str] (liste des champs manquants)
            - empty_fields: List[str] (liste des champs vides)
            - issues: Dict[str, str] (détails des problèmes par champ)
        """
        validation_result = {
            'is_valid': True,
            'missing_fields': [],
            'empty_fields': [],
            'issues': {}
        }
        
        # Vérifier chaque champ requis
        for field in required_fields:
            if field not in seo_result:
                validation_result['missing_fields'].append(field)
                validation_result['is_valid'] = False
                validation_result['issues'][field] = "Champ absent de la réponse"
                logger.warning(f"Champ manquant: {field}")
            elif not seo_result[field] or len(str(seo_result[field]).strip()) == 0:
                validation_result['empty_fields'].append(field)
                validation_result['is_valid'] = False
                validation_result['issues'][field] = "Champ vide"
                logger.warning(f"Champ vide: {field}")
            else:
                # Vérifications de qualité supplémentaires
                value = str(seo_result[field]).strip()
                
                # Vérifier la longueur minimale pour body_html
                if field == 'body_html' and len(value) < 50:
                    validation_result['issues'][field] = "Body HTML trop court (< 50 caractères)"
                    validation_result['is_valid'] = False
                    logger.warning(f"Body HTML trop court: {len(value)} caractères")
                
                # Vérifier que le body_html contient du HTML valide
                elif field == 'body_html' and not ('<' in value and '>' in value):
                    validation_result['issues'][field] = "Body HTML ne contient pas de balises HTML"
                    validation_result['is_valid'] = False
                    logger.warning(f"Body HTML sans balises HTML détectées")
                
                # Vérifier la longueur du SEO Title
                elif field == 'seo_title' and len(value) > 70:
                    validation_result['issues'][field] = "SEO Title trop long (> 70 caractères)"
                    # Warning mais pas invalidant
                    logger.warning(f"SEO Title trop long: {len(value)} caractères")
                
                # Vérifier la longueur du SEO Description
                elif field == 'seo_description' and len(value) > 320:
                    validation_result['issues'][field] = "SEO Description trop longue (> 320 caractères)"
                    # Warning mais pas invalidant
                    logger.warning(f"SEO Description trop longue: {len(value)} caractères")
        
        return validation_result
    
    def generate_retry_prompt(self, 
                             product_data: Dict[str, Any], 
                             validation_result: Dict[str, Any],
                             original_prompt: str) -> str:
        """
        Génère un prompt de retry avec des instructions spécifiques pour corriger les problèmes.
        
        Args:
            product_data: Données du produit
            validation_result: Résultat de la validation
            original_prompt: Prompt original
            
        Returns:
            Nouveau prompt enrichi avec les instructions de correction
        """
        retry_instructions = "\n\n⚠️ CORRECTION REQUISE ⚠️\n\n"
        retry_instructions += "La génération précédente a échoué pour les raisons suivantes:\n\n"
        
        # Lister les problèmes
        for field, issue in validation_result['issues'].items():
            retry_instructions += f"- {field}: {issue}\n"
        
        retry_instructions += "\n🎯 INSTRUCTIONS STRICTES 🎯\n\n"
        
        # Instructions spécifiques par type de problème
        if 'body_html' in validation_result['issues']:
            retry_instructions += """
Pour le champ Body (HTML):
- OBLIGATOIRE: Générer un contenu HTML riche et détaillé (minimum 200 caractères)
- Utiliser des balises HTML valides: <p>, <ul>, <li>, <strong>, <br>, etc.
- Inclure une description complète du produit avec ses caractéristiques
- Si tu as accès à internet via Perplexity, UTILISE-LE pour enrichir le contenu
- NE JAMAIS laisser ce champ vide ou avec un contenu minimal

"""
        
        if 'seo_title' in validation_result['issues']:
            retry_instructions += """
Pour le champ SEO Title:
- OBLIGATOIRE: Générer un titre optimisé SEO de 50-70 caractères
- Inclure le nom du produit et des mots-clés pertinents
- NE JAMAIS laisser ce champ vide

"""
        
        if 'seo_description' in validation_result['issues']:
            retry_instructions += """
Pour le champ SEO Description:
- OBLIGATOIRE: Générer une description SEO de 150-320 caractères
- Rédiger un texte attractif qui donne envie de cliquer
- NE JAMAIS laisser ce champ vide

"""
        
        if 'tags' in validation_result['issues']:
            retry_instructions += """
Pour le champ Tags:
- OBLIGATOIRE: Générer au moins 5-10 tags pertinents séparés par des virgules
- Inclure la catégorie, la marque, les caractéristiques principales
- NE JAMAIS laisser ce champ vide

"""
        
        if 'type' in validation_result['issues']:
            retry_instructions += """
Pour le champ Type:
- OBLIGATOIRE: Générer un type de produit en MAJUSCULES, PLURIEL, SANS ACCENTS
- Minimum 3 caractères
- Exemples: NAPPES, TORCHONS, SERVIETTES, COUSSINS
- NE JAMAIS laisser ce champ vide
- Le type doit être déterminé à partir du Title du produit

"""
        
        retry_instructions += "\n⚠️ CETTE FOIS, TOUS LES CHAMPS DOIVENT ÊTRE REMPLIS CORRECTEMENT ⚠️\n"
        
        # Construire le nouveau prompt
        full_retry_prompt = original_prompt + retry_instructions
        
        return full_retry_prompt
