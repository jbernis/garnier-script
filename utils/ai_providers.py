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


class AIQuotaError(AIProviderError):
    """Exception spécifique pour les erreurs de quota/tokens insuffisants."""
    def __init__(self, provider: str, message: str, original_error: str = ""):
        self.provider = provider
        self.original_error = original_error
        super().__init__(message)


class AIProvider(ABC):
    """Classe abstraite pour les fournisseurs d'API IA."""
    
    def __init__(self, api_key: Optional[str] = None, model: Optional[str] = None):
        self.api_key = api_key
        # Charger la config AVANT d'appeler get_default_model() qui en a besoin
        self.config = self._load_config()
        self.model = model or self.get_default_model()
    
    def _is_quota_error(self, error_message: str) -> bool:
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
    
    def __init__(self, api_key: Optional[str] = None, model: Optional[str] = None, 
                 enable_search: bool = False, perplexity_api_key: Optional[str] = None,
                 perplexity_model: Optional[str] = None):
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
        
        # Support du tool de recherche Internet (Perplexity)
        self.enable_search = enable_search
        self.search_tool = None
        
        if enable_search:
            if not perplexity_api_key:
                perplexity_api_key = os.getenv("PERPLEXITY_API_KEY")
            
            if perplexity_api_key:
                try:
                    from utils.search_tools import PerplexitySearchTool
                    self.search_tool = PerplexitySearchTool(perplexity_api_key, model=perplexity_model)
                    logger.info(f"✅ Tool de recherche Internet activé (Perplexity - modèle: {self.search_tool.model})")
                except Exception as e:
                    logger.warning(f"⚠️ Impossible d'activer le tool de recherche: {e}")
                    self.enable_search = False
            else:
                logger.warning("⚠️ PERPLEXITY_API_KEY non définie, recherche Internet désactivée")
                self.enable_search = False
        
        super().__init__(api_key, model)
    
    def get_default_model(self) -> str:
        """Retourne le modèle par défaut pour OpenAI."""
        models = self.config.get("ai_providers", {}).get("models", {}).get("openai", {})
        return models.get("default", "gpt-4o-mini")
    
    def _is_new_model(self, model_name: str) -> bool:
        """
        Détermine si un modèle utilise la nouvelle API (max_completion_tokens).
        
        Les critères pour identifier un modèle récent :
        - Contient une date >= 2024 (ex: gpt-4o-2024-08-06)
        - Commence par "o1" ou "o3" (série O)
        - Contient "gpt-4o" ou version supérieure
        - Version GPT >= 5 (gpt-5, gpt-6, etc.)
        
        Args:
            model_name: Nom du modèle OpenAI
            
        Returns:
            True si le modèle nécessite max_completion_tokens
        """
        import re
        
        model_lower = model_name.lower()
        
        # Série O (o1, o3, etc.)
        if re.match(r'^o[1-9]', model_lower):
            return True
        
        # GPT-4o et variantes
        if 'gpt-4o' in model_lower:
            return True
        
        # GPT-5 et supérieur (gpt-5, gpt-6, gpt-7, ...)
        gpt_version_match = re.match(r'gpt-(\d+)', model_lower)
        if gpt_version_match:
            version = int(gpt_version_match.group(1))
            if version >= 5:
                return True
        
        # Modèles avec une date >= 2024
        date_match = re.search(r'(\d{4})-\d{2}-\d{2}', model_name)
        if date_match:
            year = int(date_match.group(1))
            if year >= 2024:
                return True
        
        # Par défaut, utiliser l'ancien paramètre pour les modèles non reconnus
        return False
    
    def _supports_custom_temperature(self, model_name: str) -> bool:
        """
        Détermine si un modèle supporte une température personnalisée.
        
        Certains modèles (comme GPT-5) ne supportent que temperature=1 (défaut).
        
        Args:
            model_name: Nom du modèle OpenAI
            
        Returns:
            True si le modèle supporte une température personnalisée (ex: 0.7)
        """
        import re
        
        model_lower = model_name.lower()
        
        # GPT-5 et supérieur ne supportent que temperature=1
        gpt_version_match = re.match(r'gpt-(\d+)', model_lower)
        if gpt_version_match:
            version = int(gpt_version_match.group(1))
            if version >= 5:
                return False  # Ne supporte pas de température personnalisée
        
        # Série O ne supporte généralement pas de température personnalisée
        if re.match(r'^o[1-9]', model_lower):
            return False
        
        # Par défaut, les autres modèles supportent la température personnalisée
        return True
    
    def list_models(self) -> list[str]:
        """Liste les modèles de chat disponibles pour OpenAI (détection automatique de la dernière version GPT)."""
        try:
            import re
            
            # Appeler l'API OpenAI pour lister les modèles
            models_response = self.client.models.list()
            
            # Mots-clés à exclure (étendus pour couvrir tous les cas)
            excluded_keywords = [
                'instruct',      # Modèles instruct (deprecated)
                'whisper',       # Audio transcription
                'tts',           # Text-to-speech
                'dall-e',        # Image generation
                'embedding',     # Embeddings
                'babbage',       # Anciens modèles
                'davinci',       # Anciens modèles
                'curie',         # Anciens modèles
                'ada',           # Anciens modèles
                'moderation',    # Modération
                'search',        # Search models
                'codex',         # Code-specific
                'audio',         # Audio models
                'realtime',      # Realtime models
                'transcribe',    # Transcription
                'image',         # Image models
            ]
            
            # Étape 1 : Extraire tous les modèles GPT et leur version principale
            gpt_models = []
            max_version = 0
            
            for model in models_response.data:
                model_id = model.id
                model_id_lower = model_id.lower()
                
                # Garder uniquement les modèles qui commencent par "gpt-"
                if not model_id.startswith('gpt-'):
                    continue
                
                # Exclure les modèles avec des mots-clés non désirés
                if any(keyword in model_id_lower for keyword in excluded_keywords):
                    continue
                
                # Extraire le numéro de version principal (ex: gpt-5, gpt-6, etc.)
                # Pattern : gpt-X ou gpt-X.Y où X est le numéro de version
                match = re.match(r'gpt-(\d+)', model_id)
                if match:
                    version = int(match.group(1))
                    max_version = max(max_version, version)
                    gpt_models.append((model_id, version))
            
            # Étape 2 : Filtrer pour ne garder que les modèles de la version la plus récente
            if max_version == 0:
                logger.warning("Aucun modèle GPT détecté avec un numéro de version")
                return ["gpt-5", "gpt-5-mini", "gpt-5-nano", "gpt-5-pro"]
            
            available_models = [
                model_id for model_id, version in gpt_models 
                if version == max_version
            ]
            
            logger.info(f"✅ Détection automatique : GPT-{max_version} est la dernière version ({len(available_models)} modèles)")
            
            # Trier (les plus récents en premier)
            return sorted(available_models, reverse=True)
            
        except Exception as e:
            logger.warning(f"Impossible de charger les modèles OpenAI depuis l'API: {e}")
            # Retourner les modèles par défaut (GPT-5 uniquement)
            return ["gpt-5", "gpt-5-mini", "gpt-5-nano", "gpt-5-pro"]
    
    def generate(self, prompt: str, context: Optional[Dict[str, Any]] = None, max_tokens: Optional[int] = None) -> str:
        """Génère du texte avec OpenAI, avec support optionnel de la recherche Internet."""
        full_prompt = self._build_prompt(prompt, context)
        
        processing_config = self.config.get("processing", {})
        max_retries = processing_config.get("max_retries", 3)
        retry_delay = processing_config.get("retry_delay", 2.0)
        
        # Déterminer le bon paramètre pour les tokens selon le modèle
        use_completion_tokens = self._is_new_model(self.model)
        logger.info(f"Modèle OpenAI: {self.model}, use_completion_tokens={use_completion_tokens}")
        
        for attempt in range(max_retries):
            try:
                # Préparer les messages de base
                messages = [
                    {"role": "system", "content": "Tu es un expert en e-commerce et SEO. Tu génères du contenu optimisé pour les produits en ligne."},
                    {"role": "user", "content": full_prompt}
                ]
                
                # Préparer les paramètres de base
                params = {
                    "model": self.model,
                    "messages": messages
                }
                
                # Ajouter la température si le modèle la supporte
                if self._supports_custom_temperature(self.model):
                    params["temperature"] = 0.7
                
                # Ajouter le paramètre de tokens selon le modèle
                if use_completion_tokens:
                    params["max_completion_tokens"] = max_tokens or 3000
                else:
                    params["max_tokens"] = max_tokens or 3000
                
                # Ajouter les tools si la recherche est activée
                if self.enable_search and self.search_tool:
                    params["tools"] = [self.search_tool.get_tool_definition()]
                    params["tool_choice"] = "auto"  # L'IA décide si elle utilise le tool
                    logger.info("🌐 Recherche Internet ACTIVÉE - Tool Perplexity disponible pour l'IA")
                else:
                    logger.info("🔒 Recherche Internet DÉSACTIVÉE - L'IA utilisera uniquement les données fournies")
                
                # Premier appel à l'IA
                response = self.client.chat.completions.create(**params)
                message = response.choices[0].message
                
                # Vérifier si l'IA veut utiliser un tool (faire une recherche)
                if message.tool_calls:
                    logger.info("🔍 L'IA a décidé de faire une recherche Internet")
                    
                    tool_call = message.tool_calls[0]
                    function_args = json.loads(tool_call.function.arguments)
                    query = function_args.get("query", "")
                    
                    logger.info(f"🔎 Requête de recherche: '{query}'")
                    
                    # Exécuter la recherche via Perplexity
                    logger.info("⏳ Interrogation de Perplexity en cours...")
                    search_results = self.search_tool.search(query)
                    logger.info(f"✅ Résultats de recherche reçus ({len(search_results)} caractères)")
                    logger.debug(f"Résultats Perplexity: {search_results[:500]}...")
                    
                    # Ajouter le message de l'IA et les résultats de recherche à la conversation
                    messages.append({
                        "role": "assistant",
                        "content": None,
                        "tool_calls": message.tool_calls
                    })
                    messages.append({
                        "role": "tool",
                        "tool_call_id": tool_call.id,
                        "content": search_results
                    })
                    
                    # Deuxième appel avec les résultats de recherche
                    params["messages"] = messages
                    # Ne pas renvoyer les tools pour le second appel
                    if "tools" in params:
                        del params["tools"]
                    if "tool_choice" in params:
                        del params["tool_choice"]
                    
                    final_response = self.client.chat.completions.create(**params)
                    logger.info("✅ Réponse finale générée avec les résultats de recherche")
                    return final_response.choices[0].message.content.strip()
                
                # Pas de recherche nécessaire, retourner directement la réponse
                else:
                    if self.enable_search and self.search_tool:
                        logger.info("ℹ️  L'IA n'a pas jugé nécessaire de faire une recherche (données suffisantes)")
                return message.content.strip()
            
            except AIQuotaError:
                # Erreur de quota Perplexity ou autre : propager directement
                raise
            
            except Exception as e:
                error_msg = str(e)
                
                # Détecter les erreurs de quota/tokens OpenAI
                if self._is_quota_error(error_msg):
                    raise AIQuotaError(
                        "OpenAI",
                        "❌ Quota OpenAI dépassé ou tokens insuffisants.\n\n"
                        "Solutions :\n"
                        "• Vérifiez votre compte OpenAI : https://platform.openai.com/account/usage\n"
                        "• Rechargez des crédits si nécessaire\n"
                        "• Vérifiez les limites de votre plan\n"
                        f"• Erreur : {error_msg}",
                        error_msg
                    )
                
                if attempt < max_retries - 1:
                    logger.warning(f"Tentative {attempt + 1} échouée pour OpenAI: {e}. Nouvelle tentative dans {retry_delay}s...")
                    time.sleep(retry_delay)
                else:
                    raise AIProviderError(f"Erreur OpenAI après {max_retries} tentatives: {e}")


class ClaudeProvider(AIProvider):
    """Fournisseur Anthropic (Claude)."""
    
    def __init__(self, api_key: Optional[str] = None, model: Optional[str] = None,
                 enable_search: bool = False, perplexity_api_key: Optional[str] = None,
                 perplexity_model: Optional[str] = None):
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
        
        # Support du tool de recherche Internet (Perplexity)
        self.enable_search = enable_search
        self.search_tool = None
        
        if enable_search:
            if not perplexity_api_key:
                perplexity_api_key = os.getenv("PERPLEXITY_API_KEY")
            
            if perplexity_api_key:
                try:
                    from utils.search_tools import PerplexitySearchTool
                    self.search_tool = PerplexitySearchTool(perplexity_api_key, model=perplexity_model)
                    logger.info(f"✅ Tool de recherche Internet activé pour Claude (Perplexity - modèle: {self.search_tool.model})")
                except Exception as e:
                    logger.warning(f"⚠️ Impossible d'activer le tool de recherche pour Claude: {e}")
                    self.enable_search = False
            else:
                logger.warning("⚠️ PERPLEXITY_API_KEY non définie, recherche Internet désactivée pour Claude")
                self.enable_search = False
        
        super().__init__(api_key, model)
    
    def get_default_model(self) -> str:
        """Retourne le modèle par défaut pour Claude."""
        models = self.config.get("ai_providers", {}).get("models", {}).get("claude", {})
        return models.get("default", "claude-haiku-4-5-20251001")
    
    def list_models(self) -> list[str]:
        """Liste les modèles disponibles pour Claude depuis l'API."""
        try:
            # Créer un client temporaire pour lister les modèles
            client = self.client.Anthropic(api_key=self.api_key)
            
            # Appeler l'API pour lister les modèles
            models_response = client.models.list()
            
            # Extraire tous les modèles (pas de filtre - l'API retourne déjà les modèles pertinents)
            available_models = []
            
            for model in models_response.data:
                available_models.append({
                    'id': model.id,
                    'created_at': model.created_at,
                    'display_name': getattr(model, 'display_name', model.id)
                })
            
            # Si aucun modèle trouvé, retourner les modèles par défaut
            if not available_models:
                logger.warning("Aucun modèle trouvé via l'API Claude, utilisation de la liste par défaut")
                return [
                    "claude-opus-4-5-20251101",
                    "claude-haiku-4-5-20251001",
                    "claude-sonnet-4-5-20250929",
                    "claude-3-5-sonnet-20241022",
                    "claude-3-5-haiku-20241022",
                    "claude-3-opus-20240229"
                ]
            
            # Trier par date de création (les plus récents en premier)
            available_models.sort(key=lambda x: x['created_at'], reverse=True)
            
            # Retourner uniquement les IDs
            model_ids = [m['id'] for m in available_models]
            
            logger.info(f"✅ {len(model_ids)} modèles Claude disponibles via l'API")
            return model_ids
            
        except Exception as e:
            logger.warning(f"Impossible de charger les modèles Claude depuis l'API: {e}")
            # En cas d'erreur, retourner la liste par défaut
            return [
                "claude-opus-4-5-20251101",
                "claude-haiku-4-5-20251001",
                "claude-sonnet-4-5-20250929",
                "claude-3-5-sonnet-20241022",
                "claude-3-5-haiku-20241022",
                "claude-3-opus-20240229"
            ]
    
    def generate(self, prompt: str, context: Optional[Dict[str, Any]] = None, max_tokens: Optional[int] = None) -> str:
        """Génère du texte avec Claude."""
        full_prompt = self._build_prompt(prompt, context)
        
        processing_config = self.config.get("processing", {})
        max_retries = processing_config.get("max_retries", 3)
        retry_delay = processing_config.get("retry_delay", 2.0)
        
        for attempt in range(max_retries):
            try:
                client = self.client.Anthropic(api_key=self.api_key)
                
                # Construire les paramètres de base
                params = {
                    "model": self.model,
                    "max_tokens": max_tokens or 3000,
                    "temperature": 0.7,
                    "messages": [
                        {
                            "role": "user",
                            "content": f"Tu es un expert en e-commerce et SEO. Tu génères du contenu optimisé pour les produits en ligne.\n\n{full_prompt}"
                        }
                    ]
                }
                
                # Ajouter les tools si la recherche est activée
                if self.enable_search and self.search_tool:
                    params["tools"] = [self.search_tool.get_tool_definition_claude()]
                    logger.info("🌐 Recherche Internet ACTIVÉE - Tool Perplexity disponible pour Claude")
                else:
                    logger.info("🔒 Recherche Internet DÉSACTIVÉE - Claude utilisera uniquement les données fournies")
                
                # Premier appel à l'IA
                message = client.messages.create(**params)
                
                # Vérifier si Claude veut utiliser un tool (faire une recherche)
                if message.stop_reason == "tool_use":
                    logger.info("🔍 Claude a décidé de faire une recherche Internet")
                    
                    # Extraire le tool call
                    tool_use_block = next((block for block in message.content if block.type == "tool_use"), None)
                    if tool_use_block:
                        query = tool_use_block.input.get("query", "")
                        logger.info(f"🔎 Requête de recherche: '{query}'")
                        
                        # Exécuter la recherche via Perplexity
                        logger.info("⏳ Interrogation de Perplexity en cours...")
                        search_results = self.search_tool.search(query)
                        logger.info(f"✅ Résultats de recherche reçus ({len(search_results)} caractères)")
                        logger.debug(f"Résultats Perplexity: {search_results[:500]}...")
                        
                        # Ajouter le résultat du tool à la conversation
                        params["messages"].append({
                            "role": "assistant",
                            "content": message.content
                        })
                        params["messages"].append({
                            "role": "user",
                            "content": [
                                {
                                    "type": "tool_result",
                                    "tool_use_id": tool_use_block.id,
                                    "content": search_results
                                }
                            ]
                        })
                        
                        # Retirer les tools pour la réponse finale
                        if "tools" in params:
                            del params["tools"]
                        
                        final_response = client.messages.create(**params)
                        logger.info("✅ Réponse finale générée avec les résultats de recherche")
                        return final_response.content[0].text.strip()
                    
                # Pas de recherche nécessaire, retourner directement la réponse
                else:
                    if self.enable_search and self.search_tool:
                        logger.info("ℹ️  Claude n'a pas jugé nécessaire de faire une recherche (données suffisantes)")
                    return message.content[0].text.strip()
            
            except Exception as e:
                error_msg = str(e)
                
                # Détecter les erreurs de quota/tokens
                if self._is_quota_error(error_msg):
                    raise AIQuotaError(
                        "Claude",
                        "❌ Quota Claude (Anthropic) dépassé ou tokens insuffisants.\n\n"
                        "Solutions :\n"
                        "• Vérifiez votre compte Anthropic : https://console.anthropic.com/settings/usage\n"
                        "• Rechargez des crédits si nécessaire\n"
                        "• Vérifiez les limites de votre plan\n"
                        f"• Erreur : {error_msg}",
                        error_msg
                    )
                
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
        return models.get("default", "gemini-2.5-flash")
    
    @staticmethod
    def _is_relevant_text_generation_model(model_name: str) -> bool:
        """
        Filtre les modèles Gemini pour ne garder que ceux pertinents pour la génération de texte.
        
        Retourne True si le modèle est pertinent, False sinon.
        
        Critères de filtrage:
        - Garder: gemini-2.x, gemini-3.x (génération de texte)
        - Retirer: embedding, images (imagen), vidéos (veo), audio/TTS, Gemma, spécialisés
        """
        model_lower = model_name.lower()
        
        # 1. RETIRER les modèles non pertinents
        exclude_keywords = [
            'embed',           # Embedding (vectorisation)
            'imagen',          # Génération d'images
            'veo',             # Génération de vidéos
            'tts',             # Text-to-speech
            'audio',           # Audio
            'gemma',           # Modèles Gemma (différent de Gemini)
            'robotics',        # Robotique
            'computer-use',    # Usage ordinateur
            'deep-research',   # Recherche profonde
            'nano-banana',     # Modèle test bizarre
            'aqa',             # Q&A spécifique
        ]
        
        for keyword in exclude_keywords:
            if keyword in model_lower:
                return False
        
        # 2. GARDER uniquement les modèles Gemini de génération de texte
        if not model_lower.startswith('gemini-'):
            return False
        
        # 3. GARDER les versions récentes (2.0+, 2.5+, 3.0+)
        # Retirer les anciennes versions (1.0, 1.5)
        if any(version in model_lower for version in ['gemini-2.0', 'gemini-2.5', 'gemini-3.0', 'gemini-3.']):
            # Vérifier que c'est bien un modèle de génération (flash ou pro)
            if 'flash' in model_lower or 'pro' in model_lower or 'exp' in model_lower:
                # Retirer les variantes trop spécifiques
                if any(variant in model_lower for variant in ['-lite-preview', '-lite-001']):
                    return False
                return True
        
        return False
    
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
                    
                    # Utiliser le filtre intelligent pour ne garder que les modèles pertinents
                    if self._is_relevant_text_generation_model(model_name):
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
                        "max_output_tokens": max_tokens or 3000,
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
                error_msg = str(e)
                
                # Détecter les erreurs de quota/tokens
                if self._is_quota_error(error_msg):
                    raise AIQuotaError(
                        "Gemini",
                        "❌ Quota Gemini (Google) dépassé ou tokens insuffisants.\n\n"
                        "Solutions :\n"
                        "• Vérifiez votre compte Google Cloud : https://console.cloud.google.com/\n"
                        "• Rechargez des crédits si nécessaire\n"
                        "• Vérifiez les limites de votre plan\n"
                        f"• Erreur : {error_msg}",
                        error_msg
                    )
                
                if attempt < max_retries - 1:
                    logger.warning(f"Tentative {attempt + 1} échouée pour Gemini: {e}. Nouvelle tentative dans {retry_delay}s...")
                    time.sleep(retry_delay)
                else:
                    raise AIProviderError(f"Erreur Gemini après {max_retries} tentatives: {e}")


def get_provider(provider_name: str, api_key: Optional[str] = None, model: Optional[str] = None, 
                 enable_search: bool = False, perplexity_api_key: Optional[str] = None,
                 perplexity_model: Optional[str] = None) -> AIProvider:
    """
    Factory pour créer un fournisseur IA.
    
    Args:
        provider_name: Nom du provider (openai, claude, gemini)
        api_key: Clé API du provider
        model: Modèle à utiliser
        enable_search: Active la recherche Internet via Perplexity (uniquement OpenAI pour l'instant)
        perplexity_api_key: Clé API Perplexity pour la recherche
        perplexity_model: Modèle Perplexity à utiliser (sonar par défaut)
        
    Returns:
        Instance du provider IA
    """
    providers = {
        "openai": OpenAIProvider,
        "claude": ClaudeProvider,
        "gemini": GeminiProvider
    }
    
    provider_class = providers.get(provider_name.lower())
    if not provider_class:
        raise AIProviderError(f"Fournisseur '{provider_name}' non supporté. Fournisseurs disponibles: {', '.join(providers.keys())}")
    
    # Passer les paramètres de recherche pour OpenAI et Claude
    if provider_name.lower() in ["openai", "claude"]:
        return provider_class(api_key=api_key, model=model, 
                             enable_search=enable_search, 
                             perplexity_api_key=perplexity_api_key,
                             perplexity_model=perplexity_model)
    else:
        # Gemini ne supporte pas encore la recherche Internet
        return provider_class(api_key=api_key, model=model)

