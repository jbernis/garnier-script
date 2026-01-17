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
        Construit le prompt complet avec le système et le prompt spécifique.
        
        Args:
            product_data: Données du produit
            
        Returns:
            Prompt complet
        """
        context = self._build_context(product_data)
        
        # Construire le contexte formaté
        context_str = ""
        if context.get('title'):
            context_str += f"Titre: {context['title']}\n"
        if context.get('vendor'):
            context_str += f"Marque: {context['vendor']}\n"
        if context.get('type'):
            context_str += f"Type: {context['type']}\n"
        if context.get('tags'):
            context_str += f"Tags: {context['tags']}\n"
        if context.get('body_html'):
            # Extraire un extrait du HTML (premiers 500 caractères)
            body_text = context['body_html'][:500].replace('<', ' ').replace('>', ' ')
            context_str += f"Description actuelle: {body_text}...\n"
        
        # Construire le prompt complet
        full_prompt = f"{self.system_prompt}\n\n"
        if context_str:
            full_prompt += f"Informations sur le produit:\n{context_str}\n\n"
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


class DescriptionAgent(BaseAIAgent):
    """Agent pour générer/modifier les descriptions (Body HTML)."""
    
    def generate(self, product_data: Dict[str, Any], **kwargs) -> str:
        """
        Génère une nouvelle description HTML pour le produit.
        
        Args:
            product_data: Données du produit
            
        Returns:
            Nouvelle description HTML
        """
        prompt = self._build_full_prompt(product_data)
        
        try:
            # Appeler l'IA avec le prompt
            response = self.ai_provider.generate(prompt, context=self._build_context(product_data))
            
            # Nettoyer la réponse (enlever les markdown si présent)
            response = response.strip()
            if response.startswith('```html'):
                response = response[7:]
            if response.startswith('```'):
                response = response[3:]
            if response.endswith('```'):
                response = response[:-3]
            response = response.strip()
            
            logger.debug(f"Description générée pour {product_data.get('Handle', 'unknown')}")
            return response
            
        except Exception as e:
            logger.error(f"Erreur lors de la génération de la description: {e}")
            raise


class GoogleShoppingAgent(BaseAIAgent):
    """Agent pour optimiser les champs Google Shopping (principalement Google Product Category)."""
    
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
            # Appeler l'IA avec le prompt
            response = self.ai_provider.generate(prompt, context=self._build_context(product_data))
            
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


class SEOAgent(BaseAIAgent):
    """Agent pour optimiser les champs SEO (SEO Title, SEO Description, Image Alt Text)."""
    
    def generate(self, product_data: Dict[str, Any], **kwargs) -> Dict[str, str]:
        """
        Génère les champs SEO pour le produit.
        
        Args:
            product_data: Données du produit
            
        Returns:
            Dictionnaire avec les clés: seo_title, seo_description, image_alt_text
        """
        prompt = self._build_full_prompt(product_data)
        
        try:
            # Appeler l'IA avec le prompt
            response = self.ai_provider.generate(prompt, context=self._build_context(product_data))
            
            # Parser la réponse (peut être JSON ou format texte)
            response = response.strip()
            
            # Essayer de parser comme JSON d'abord
            try:
                result = json.loads(response)
                if isinstance(result, dict):
                    return {
                        'seo_title': result.get('seo_title', ''),
                        'seo_description': result.get('seo_description', ''),
                        'image_alt_text': result.get('image_alt_text', '')
                    }
            except json.JSONDecodeError:
                pass
            
            # Si ce n'est pas du JSON, essayer de parser un format texte structuré
            # Format attendu: "SEO Title: ...\nSEO Description: ...\nImage Alt Text: ..."
            lines = response.split('\n')
            result = {
                'seo_title': '',
                'seo_description': '',
                'image_alt_text': ''
            }
            
            current_field = None
            current_value = []
            
            for line in lines:
                line = line.strip()
                if not line:
                    continue
                
                if line.startswith('SEO Title:'):
                    if current_field:
                        result[current_field] = ' '.join(current_value).strip()
                    current_field = 'seo_title'
                    current_value = [line.replace('SEO Title:', '').strip()]
                elif line.startswith('SEO Description:'):
                    if current_field:
                        result[current_field] = ' '.join(current_value).strip()
                    current_field = 'seo_description'
                    current_value = [line.replace('SEO Description:', '').strip()]
                elif line.startswith('Image Alt Text:'):
                    if current_field:
                        result[current_field] = ' '.join(current_value).strip()
                    current_field = 'image_alt_text'
                    current_value = [line.replace('Image Alt Text:', '').strip()]
                else:
                    if current_field:
                        current_value.append(line)
            
            # Ajouter le dernier champ
            if current_field:
                result[current_field] = ' '.join(current_value).strip()
            
            # Si aucun champ n'a été trouvé, utiliser la réponse complète comme titre SEO
            if not any(result.values()):
                result['seo_title'] = response[:60]  # Limiter à 60 caractères
                result['seo_description'] = response[:160]  # Limiter à 160 caractères
                result['image_alt_text'] = product_data.get('Title', '')
            
            logger.debug(f"SEO généré pour {product_data.get('Handle', 'unknown')}")
            return result
            
        except Exception as e:
            logger.error(f"Erreur lors de la génération SEO: {e}")
            raise
