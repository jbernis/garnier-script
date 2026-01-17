"""
Gestion du fichier .env de manière sécurisée.
"""

import os
from typing import Dict, Optional, List, Tuple
from pathlib import Path
import logging

logger = logging.getLogger(__name__)


class EnvManager:
    """Gère la lecture et l'écriture du fichier .env."""
    
    def __init__(self, env_file: str = ".env"):
        self.env_file = Path(env_file)
        self.env_vars = {}
        self.load()
    
    def load(self) -> Dict[str, str]:
        """Charge les variables d'environnement depuis le fichier .env."""
        self.env_vars = {}
        
        if not self.env_file.exists():
            logger.warning(f"Fichier {self.env_file} n'existe pas")
            return self.env_vars
        
        try:
            with open(self.env_file, 'r', encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    # Ignorer les lignes vides et les commentaires
                    if not line or line.startswith('#'):
                        continue
                    
                    # Séparer la clé et la valeur
                    if '=' in line:
                        key, value = line.split('=', 1)
                        key = key.strip()
                        value = value.strip()
                        # Supprimer les guillemets si présents
                        if value.startswith('"') and value.endswith('"'):
                            value = value[1:-1]
                        elif value.startswith("'") and value.endswith("'"):
                            value = value[1:-1]
                        self.env_vars[key] = value
        
        except Exception as e:
            logger.error(f"Erreur lors du chargement du fichier .env: {e}")
        
        return self.env_vars
    
    def get(self, key: str, default: Optional[str] = None) -> Optional[str]:
        """Récupère une variable d'environnement."""
        return self.env_vars.get(key, default)
    
    def set(self, key: str, value: str) -> None:
        """Définit une variable d'environnement."""
        self.env_vars[key] = value
    
    def get_all(self) -> Dict[str, str]:
        """Récupère toutes les variables d'environnement."""
        return self.env_vars.copy()
    
    def get_by_provider(self, provider: str) -> Dict[str, str]:
        """Récupère les variables d'un fournisseur spécifique."""
        provider_vars = {}
        prefix = provider.upper().replace("-", "_")
        
        for key, value in self.env_vars.items():
            if key.startswith(prefix) or key in self._get_provider_keys(provider):
                provider_vars[key] = value
        
        return provider_vars
    
    def _get_provider_keys(self, provider: str) -> List[str]:
        """Retourne les clés spécifiques à un fournisseur."""
        provider_keys = {
            "garnier": ["BASE_URL_GARNIER", "USERNAME", "PASSWORD", "OUTPUT_CSV_GARNIER"],
            "artiga": ["ARTIGA_BASE_URL", "ARTIGA_OUTPUT_CSV"],
            "cristel": ["CRISTEL_BASE_URL", "CRISTEL_OUTPUT_CSV"],
        }
        return provider_keys.get(provider.lower(), [])
    
    def set_provider_vars(self, provider: str, vars_dict: Dict[str, str]) -> None:
        """Définit les variables d'un fournisseur."""
        for key, value in vars_dict.items():
            self.env_vars[key] = value
    
    def save(self) -> bool:
        """Sauvegarde les variables dans le fichier .env."""
        try:
            # Créer le fichier s'il n'existe pas
            self.env_file.parent.mkdir(parents=True, exist_ok=True)
            
            # Lire le contenu existant pour préserver les commentaires
            existing_lines = []
            if self.env_file.exists():
                with open(self.env_file, 'r', encoding='utf-8') as f:
                    existing_lines = f.readlines()
            
            # Créer un dictionnaire des variables existantes avec leurs commentaires
            comments = {}
            for line in existing_lines:
                if line.strip().startswith('#'):
                    # Garder les commentaires
                    continue
                if '=' in line:
                    key = line.split('=')[0].strip()
                    # Chercher un commentaire sur la ligne précédente
                    if existing_lines.index(line) > 0:
                        prev_line = existing_lines[existing_lines.index(line) - 1]
                        if prev_line.strip().startswith('#'):
                            comments[key] = prev_line.strip()
            
            # Écrire le fichier
            with open(self.env_file, 'w', encoding='utf-8') as f:
                # Écrire les variables par fournisseur
                providers = {
                    "Garnier": ["BASE_URL_GARNIER", "USERNAME", "PASSWORD", "OUTPUT_CSV_GARNIER"],
                    "Artiga": ["ARTIGA_BASE_URL", "ARTIGA_OUTPUT_CSV"],
                    "Cristel": ["CRISTEL_BASE_URL", "CRISTEL_OUTPUT_CSV"],
                }
                
                for provider_name, keys in providers.items():
                    f.write(f"\n# Configuration {provider_name}\n")
                    for key in keys:
                        if key in self.env_vars:
                            comment = comments.get(key, "")
                            if comment:
                                f.write(f"{comment}\n")
                            f.write(f"{key}={self.env_vars[key]}\n")
                
                # Écrire les clés API IA
                ai_keys = ["OPENAI_API_KEY", "ANTHROPIC_API_KEY", "GOOGLE_API_KEY"]
                has_ai_keys = any(key in self.env_vars for key in ai_keys)
                if has_ai_keys:
                    f.write("\n# Configuration Fournisseurs IA\n")
                    for key in ai_keys:
                        if key in self.env_vars:
                            comment = comments.get(key, "")
                            if comment:
                                f.write(f"{comment}\n")
                            f.write(f"{key}={self.env_vars[key]}\n")
                
                # Écrire les autres variables
                written_keys = set()
                for keys in providers.values():
                    written_keys.update(keys)
                written_keys.update(ai_keys)
                
                other_vars = {k: v for k, v in self.env_vars.items() if k not in written_keys}
                if other_vars:
                    f.write("\n# Autres variables\n")
                    for key, value in other_vars.items():
                        comment = comments.get(key, "")
                        if comment:
                            f.write(f"{comment}\n")
                        f.write(f"{key}={value}\n")
            
            logger.info(f"Fichier .env sauvegardé: {self.env_file}")
            return True
        
        except Exception as e:
            logger.error(f"Erreur lors de la sauvegarde du fichier .env: {e}")
            return False
    
    def validate_url(self, url: str) -> bool:
        """Valide qu'une URL est valide."""
        if not url:
            return False
        return url.startswith(('http://', 'https://'))
    
    def validate_credentials(self, provider: str) -> Tuple[bool, List[str]]:
        """Valide les credentials d'un fournisseur."""
        errors = []
        provider_vars = self.get_by_provider(provider)
        
        if provider.lower() == "garnier":
            if not provider_vars.get("BASE_URL_GARNIER"):
                errors.append("BASE_URL_GARNIER est requis")
            elif not self.validate_url(provider_vars["BASE_URL_GARNIER"]):
                errors.append("BASE_URL_GARNIER doit être une URL valide")
            
            if not provider_vars.get("USERNAME"):
                errors.append("USERNAME est requis")
            
            if not provider_vars.get("PASSWORD"):
                errors.append("PASSWORD est requis")
        
        elif provider.lower() == "artiga":
            if not provider_vars.get("ARTIGA_BASE_URL"):
                errors.append("ARTIGA_BASE_URL est requis")
            elif not self.validate_url(provider_vars["ARTIGA_BASE_URL"]):
                errors.append("ARTIGA_BASE_URL doit être une URL valide")
        
        elif provider.lower() == "cristel":
            if not provider_vars.get("CRISTEL_BASE_URL"):
                errors.append("CRISTEL_BASE_URL est requis")
            elif not self.validate_url(provider_vars["CRISTEL_BASE_URL"]):
                errors.append("CRISTEL_BASE_URL doit être une URL valide")
        
        return len(errors) == 0, errors

