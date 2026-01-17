"""
Gestion des différents fournisseurs d'API IA (OpenAI, Claude, Gemini).
"""

import os
import json
import time
import logging
from abc import ABC, abstractmethod
from typing import Optional, Dict, Any
from pathlib import Path

logger = logging.getLogger(__name__)


class AIProviderError(Exception):
    """Exception pour les erreurs des fournisseurs IA."""
    pass


class AIProvider(ABC):
    """Classe abstraite pour les fournisseurs d'API IA."""
    
    def __init__(self, api_key: Optional[str] = None, model: Optional[str] = None):
        self.api_key = api_key
        # Charger la config AVANT d'appeler get_default_model() qui en a besoin
        self.config = self._load_config()
        self.model = model or self.get_default_model()
    
    def _load_config(self) -> Dict[str, Any]:
        """Charge la configuration depuis ai_config.json."""
        config_path = Path(__file__).parent.parent / "ai_config.json"
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            logger.warning(f"Impossible de charger ai_config.json: {e}")
            return {}
    
    @abstractmethod
    def get_default_model(self) -> str:
        """Retourne le modèle par défaut."""
        pass
    
    @abstractmethod
    def generate(self, prompt: str, context: Optional[Dict[str, Any]] = None, max_tokens: Optional[int] = None) -> str:
        """Génère du texte à partir d'un prompt."""
        pass
    
    @abstractmethod
    def list_models(self) -> list[str]:
        """Liste les modèles disponibles pour ce fournisseur."""
        pass
    
    def _build_prompt(self, user_prompt: str, context: Optional[Dict[str, Any]] = None) -> str:
        """Construit le prompt complet avec le contexte."""
        if not context:
            return user_prompt
        
        context_str = "Informations sur le produit:\n"
        if context.get("title"):
            context_str += f"- Titre: {context['title']}\n"
        if context.get("type"):
            context_str += f"- Type: {context['type']}\n"
        if context.get("tags"):
            context_str += f"- Tags: {context['tags']}\n"
        if context.get("vendor"):
            context_str += f"- Marque: {context['vendor']}\n"
        if context.get("body_html"):
            # Extraire un extrait du HTML (premiers 500 caractères)
            body_text = context['body_html'][:500].replace('<', ' ').replace('>', ' ')
            context_str += f"- Description: {body_text}...\n"
        
        return f"{context_str}\n\n{user_prompt}"


class OpenAIProvider(AIProvider):
    """Fournisseur OpenAI (GPT-4, GPT-3.5)."""
    
    def __init__(self, api_key: Optional[str] = None, model: Optional[str] = None):
        try:
            from openai import OpenAI
            self.OpenAI = OpenAI
        except ImportError:
            raise AIProviderError("La bibliothèque 'openai' n'est pas installée. Installez-la avec: pip install openai")
        
        if not api_key:
            api_key = os.getenv("OPENAI_API_KEY")
        
        if not api_key:
            raise AIProviderError("OPENAI_API_KEY n'est pas définie. Définissez-la dans le fichier .env ou passez-la en paramètre.")
        
        self.client = self.OpenAI(api_key=api_key)
        super().__init__(api_key, model)
    
    def get_default_model(self) -> str:
        """Retourne le modèle par défaut pour OpenAI."""
        models = self.config.get("ai_providers", {}).get("models", {}).get("openai", {})
        return models.get("default", "gpt-4o-mini")
    
    def list_models(self) -> list[str]:
        """Liste les modèles disponibles pour OpenAI."""
        try:
            # Appeler l'API OpenAI pour lister les modèles
            models_response = self.client.models.list()
            # Filtrer les modèles de chat (gpt-*)
            available_models = [
                model.id for model in models_response.data 
                if model.id.startswith('gpt-') and 'instruct' not in model.id.lower()
            ]
            # Trier et retourner
            return sorted(available_models, reverse=True)
        except Exception as e:
            logger.warning(f"Impossible de charger les modèles OpenAI depuis l'API: {e}")
            # Retourner les modèles par défaut depuis la config
            models = self.config.get("ai_providers", {}).get("models", {}).get("openai", {})
            return models.get("available", ["gpt-4o-mini", "gpt-4", "gpt-4-turbo", "gpt-3.5-turbo"])
    
    def generate(self, prompt: str, context: Optional[Dict[str, Any]] = None, max_tokens: Optional[int] = None) -> str:
        """Génère du texte avec OpenAI."""
        full_prompt = self._build_prompt(prompt, context)
        
        processing_config = self.config.get("processing", {})
        max_retries = processing_config.get("max_retries", 3)
        retry_delay = processing_config.get("retry_delay", 2.0)
        
        for attempt in range(max_retries):
            try:
                response = self.client.chat.completions.create(
                    model=self.model,
                    messages=[
                        {"role": "system", "content": "Tu es un expert en e-commerce et SEO. Tu génères du contenu optimisé pour les produits en ligne."},
                        {"role": "user", "content": full_prompt}
                    ],
                    max_tokens=max_tokens or 500,
                    temperature=0.7
                )
                
                return response.choices[0].message.content.strip()
            
            except Exception as e:
                if attempt < max_retries - 1:
                    logger.warning(f"Tentative {attempt + 1} échouée pour OpenAI: {e}. Nouvelle tentative dans {retry_delay}s...")
                    time.sleep(retry_delay)
                else:
                    raise AIProviderError(f"Erreur OpenAI après {max_retries} tentatives: {e}")


class ClaudeProvider(AIProvider):
    """Fournisseur Anthropic (Claude)."""
    
    def __init__(self, api_key: Optional[str] = None, model: Optional[str] = None):
        try:
            import anthropic
            self.client = anthropic
        except ImportError:
            raise AIProviderError("La bibliothèque 'anthropic' n'est pas installée. Installez-la avec: pip install anthropic")
        
        if not api_key:
            api_key = os.getenv("ANTHROPIC_API_KEY")
        
        if not api_key:
            raise AIProviderError("ANTHROPIC_API_KEY n'est pas définie. Définissez-la dans le fichier .env ou passez-la en paramètre.")
        
        self.client.api_key = api_key
        super().__init__(api_key, model)
    
    def get_default_model(self) -> str:
        """Retourne le modèle par défaut pour Claude."""
        models = self.config.get("ai_providers", {}).get("models", {}).get("claude", {})
        return models.get("default", "claude-haiku-4-5-20251001")
    
    def list_models(self) -> list[str]:
        """Liste les modèles disponibles pour Claude."""
        try:
            # Anthropic n'a pas d'API publique pour lister les modèles dynamiquement
            # On retourne la liste des modèles récents disponibles connus
            # Ces modèles sont maintenus à jour selon la documentation Anthropic
            return [
                "claude-haiku-4-5-20251001",  # Le plus récent (Haiku 4.5)
                "claude-3-5-sonnet-20241022",  # Sonnet 3.5 (octobre 2024)
                "claude-3-5-haiku-20241022",   # Haiku 3.5 (octobre 2024)
                "claude-3-opus-20240229",      # Opus 3 (février 2024)
                "claude-3-sonnet-20240229",    # Sonnet 3 (février 2024)
                "claude-3-haiku-20240307"      # Haiku 3 (mars 2024)
            ]
        except Exception as e:
            logger.error(f"Erreur lors du chargement des modèles Claude: {e}", exc_info=True)
            # En cas d'erreur, retourner uniquement le modèle par défaut
            return [self.get_default_model()]
    
    def generate(self, prompt: str, context: Optional[Dict[str, Any]] = None, max_tokens: Optional[int] = None) -> str:
        """Génère du texte avec Claude."""
        full_prompt = self._build_prompt(prompt, context)
        
        processing_config = self.config.get("processing", {})
        max_retries = processing_config.get("max_retries", 3)
        retry_delay = processing_config.get("retry_delay", 2.0)
        
        for attempt in range(max_retries):
            try:
                client = self.client.Anthropic(api_key=self.api_key)
                message = client.messages.create(
                    model=self.model,
                    max_tokens=max_tokens or 500,
                    temperature=0.7,
                    messages=[
                        {
                            "role": "user",
                            "content": f"Tu es un expert en e-commerce et SEO. Tu génères du contenu optimisé pour les produits en ligne.\n\n{full_prompt}"
                        }
                    ]
                )
                
                return message.content[0].text.strip()
            
            except Exception as e:
                if attempt < max_retries - 1:
                    logger.warning(f"Tentative {attempt + 1} échouée pour Claude: {e}. Nouvelle tentative dans {retry_delay}s...")
                    time.sleep(retry_delay)
                else:
                    raise AIProviderError(f"Erreur Claude après {max_retries} tentatives: {e}")


class GeminiProvider(AIProvider):
    """Fournisseur Google Gemini."""
    
    def __init__(self, api_key: Optional[str] = None, model: Optional[str] = None):
        try:
            import google.genai as genai
            self.genai = genai
        except ImportError:
            raise AIProviderError(
                "La bibliothèque 'google-genai' n'est pas installée. "
                "L'ancien package 'google-generativeai' est déprécié et n'est plus supporté. "
                "Installez le nouveau package avec: pip install google-genai"
            )
        
        if not api_key:
            api_key = os.getenv("GOOGLE_API_KEY")
        
        if not api_key:
            raise AIProviderError("GOOGLE_API_KEY n'est pas définie. Définissez-la dans le fichier .env ou passez-la en paramètre.")
        
        self.api_key = api_key
        
        # Créer le client avec la nouvelle API
        try:
            self.client = self.genai.Client(api_key=api_key)
        except Exception as e:
            raise AIProviderError(f"Impossible d'initialiser le client Google Gemini: {e}")
        
        super().__init__(api_key, model)
    
    def get_default_model(self) -> str:
        """Retourne le modèle par défaut pour Gemini."""
        models = self.config.get("ai_providers", {}).get("models", {}).get("gemini", {})
        return models.get("default", "gemini-1.5-flash")
    
    def list_models(self) -> list[str]:
        """Liste les modèles disponibles pour Gemini depuis l'API."""
        try:
            # Utiliser l'API google-genai pour lister les modèles disponibles
            models_response = self.client.models.list()
            
            # Extraire les noms des modèles
            available_models = []
            
            # La structure de réponse peut varier selon la version de l'API
            # Essayer différentes structures possibles
            models_list = None
            
            if hasattr(models_response, 'models'):
                # Si c'est un objet avec une propriété models
                models_list = models_response.models
            elif hasattr(models_response, 'data'):
                # Si c'est un objet avec une propriété data
                models_list = models_response.data
            elif isinstance(models_response, list):
                # Si c'est directement une liste
                models_list = models_response
            elif hasattr(models_response, '__iter__') and not isinstance(models_response, str):
                # Si c'est itérable (mais pas une string)
                models_list = list(models_response)
            
            if models_list is None:
                logger.error(f"Format de réponse inattendu pour list_models: {type(models_response)}")
                # Retourner uniquement le modèle par défaut
                return [self.get_default_model()]
            
            # Extraire les noms des modèles
            for model in models_list:
                model_name = None
                
                # Essayer différentes façons d'extraire le nom
                if hasattr(model, 'name'):
                    model_name = model.name
                elif hasattr(model, 'display_name'):
                    model_name = model.display_name
                elif hasattr(model, 'id'):
                    model_name = model.id
                elif isinstance(model, str):
                    model_name = model
                elif isinstance(model, dict):
                    model_name = model.get('name') or model.get('display_name') or model.get('id')
                
                if model_name:
                    # Nettoyer le nom du modèle : retirer le préfixe "models/" s'il est présent
                    if model_name.startswith('models/'):
                        model_name = model_name[7:]  # Retirer "models/"
                    
                    # Filtrer les modèles dépréciés (gemini-1.5 et plus anciens)
                    # Garder seulement les modèles récents (gemini-2.0+, gemini-3+)
                    model_lower = model_name.lower()
                    if not any(deprecated in model_lower for deprecated in ['gemini-1.5', 'gemini-1.0', 'gemini-pro-vision', 'gemini-pro']):
                        available_models.append(model_name)
                    elif 'gemini-2.0' in model_lower or 'gemini-3' in model_lower:
                        # Inclure les modèles 2.0+ et 3+
                        available_models.append(model_name)
            
            # Si aucun modèle trouvé après filtrage, inclure le modèle par défaut
            if not available_models:
                logger.warning("Aucun modèle récent trouvé via l'API après filtrage, utilisation du modèle par défaut")
                return [self.get_default_model()]
            
            # Trier les modèles (les plus récents en premier)
            # Trier par numéro de version si possible
            def sort_key(name):
                # Extraire le numéro de version pour le tri
                import re
                match = re.search(r'gemini-(\d+)\.(\d+)', name.lower())
                if match:
                    major, minor = int(match.group(1)), int(match.group(2))
                    return (major, minor)
                return (0, 0)
            
            available_models.sort(key=sort_key, reverse=True)
            
            return available_models
            
        except Exception as e:
            logger.error(f"Erreur lors du chargement des modèles Gemini depuis l'API: {e}", exc_info=True)
            # En cas d'erreur, retourner uniquement le modèle par défaut
            return [self.get_default_model()]
    
    def generate(self, prompt: str, context: Optional[Dict[str, Any]] = None, max_tokens: Optional[int] = None) -> str:
        """Génère du texte avec Gemini."""
        full_prompt = self._build_prompt(prompt, context)
        
        processing_config = self.config.get("processing", {})
        max_retries = processing_config.get("max_retries", 3)
        retry_delay = processing_config.get("retry_delay", 2.0)
        
        for attempt in range(max_retries):
            try:
                system_instruction = "Tu es un expert en e-commerce et SEO. Tu génères du contenu optimisé pour les produits en ligne."
                full_content = f"{system_instruction}\n\n{full_prompt}"
                
                # Nouvelle API google-genai
                # Ajouter le préfixe "models/" si nécessaire (l'API l'attend)
                model_name = self.model
                if not model_name.startswith('models/'):
                    model_name = f"models/{model_name}"
                
                response = self.client.models.generate_content(
                    model=model_name,
                    contents=full_content,
                    config={
                        "max_output_tokens": max_tokens or 500,
                        "temperature": 0.7
                    }
                )
                
                # Extraire le texte de la réponse
                if hasattr(response, 'text'):
                    return response.text.strip()
                elif hasattr(response, 'candidates') and response.candidates:
                    # Structure avec candidates
                    candidate = response.candidates[0]
                    if hasattr(candidate, 'content'):
                        if hasattr(candidate.content, 'parts'):
                            return candidate.content.parts[0].text.strip()
                        elif hasattr(candidate.content, 'text'):
                            return candidate.content.text.strip()
                elif hasattr(response, 'content'):
                    # Structure directe avec content
                    if hasattr(response.content, 'parts'):
                        return response.content.parts[0].text.strip()
                    elif hasattr(response.content, 'text'):
                        return response.content.text.strip()
                
                # Si aucune structure connue, convertir en string
                return str(response).strip()
            
            except Exception as e:
                if attempt < max_retries - 1:
                    logger.warning(f"Tentative {attempt + 1} échouée pour Gemini: {e}. Nouvelle tentative dans {retry_delay}s...")
                    time.sleep(retry_delay)
                else:
                    raise AIProviderError(f"Erreur Gemini après {max_retries} tentatives: {e}")


def get_provider(provider_name: str, api_key: Optional[str] = None, model: Optional[str] = None) -> AIProvider:
    """Factory pour créer un fournisseur IA."""
    providers = {
        "openai": OpenAIProvider,
        "claude": ClaudeProvider,
        "gemini": GeminiProvider
    }
    
    provider_class = providers.get(provider_name.lower())
    if not provider_class:
        raise AIProviderError(f"Fournisseur '{provider_name}' non supporté. Fournisseurs disponibles: {', '.join(providers.keys())}")
    
    return provider_class(api_key=api_key, model=model)

