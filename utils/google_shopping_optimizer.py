"""
Optimisation des champs Google Shopping avec l'IA.
"""

import pandas as pd
import json
import logging
from typing import Optional, Dict, List, Callable, Set
from pathlib import Path
from datetime import datetime
from utils.ai_providers import AIProvider, AIProviderError

logger = logging.getLogger(__name__)


class GoogleShoppingOptimizer:
    """Optimiseur pour les champs Google Shopping."""
    
    def __init__(self, ai_provider: AIProvider):
        self.ai_provider = ai_provider
        self.config = self._load_config()
    
    def _load_config(self) -> Dict:
        """Charge la configuration depuis ai_config.json."""
        config_path = Path(__file__).parent.parent / "ai_config.json"
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                config = json.load(f)
                return config.get("google_shopping_fields", {})
        except Exception as e:
            logger.warning(f"Impossible de charger ai_config.json: {e}")
            return {}
    
    def get_enabled_fields(self) -> List[str]:
        """Retourne la liste des champs activés."""
        if not self.config.get("enabled", True):
            return []
        
        fields = self.config.get("fields", {})
        return [field for field, enabled in fields.items() if enabled]
    
    def get_prompt_for_field(self, field_name: str) -> str:
        """Retourne le prompt par défaut pour un champ."""
        prompts = self.config.get("default_prompts", {})
        return prompts.get(field_name, f"Génère une valeur optimisée pour le champ '{field_name}'.")
    
    def optimize_csv(
        self,
        csv_path: str,
        output_path: Optional[str] = None,
        selected_handles: Optional[Set[str]] = None,
        progress_callback: Optional[Callable[[str, int, int], None]] = None,
        log_callback: Optional[Callable[[str], None]] = None,
        cancel_check: Optional[Callable[[], bool]] = None
    ) -> tuple[bool, Optional[str], Optional[str]]:
        """
        Optimise les champs Google Shopping d'un CSV.
        
        Args:
            csv_path: Chemin vers le fichier CSV à traiter
            output_path: Chemin de sortie (si None, génère automatiquement)
            selected_handles: Set de handles à traiter (si None, traite tous)
            progress_callback: Callback pour la progression
            log_callback: Callback pour les logs
            cancel_check: Callback pour vérifier l'annulation
        
        Returns:
            Tuple (success, output_path, error_message)
        """
        try:
            # Charger le CSV
            if log_callback:
                log_callback("Chargement du fichier CSV...")
            
            df = pd.read_csv(csv_path)
            
            # Vérifier que les colonnes nécessaires existent
            required_columns = ["Handle"]
            missing_columns = [col for col in required_columns if col not in df.columns]
            if missing_columns:
                error_msg = f"Colonnes manquantes dans le CSV: {', '.join(missing_columns)}"
                logger.error(error_msg)
                if log_callback:
                    log_callback(f"❌ {error_msg}")
                return False, None, error_msg
            
            # Récupérer les champs à optimiser
            enabled_fields = self.get_enabled_fields()
            
            if not enabled_fields:
                error_msg = "Aucun champ Google Shopping activé dans la configuration"
                logger.warning(error_msg)
                if log_callback:
                    log_callback(f"⚠️ {error_msg}")
                return False, None, error_msg
            
            # Vérifier que les colonnes existent dans le CSV
            missing_fields = [field for field in enabled_fields if field not in df.columns]
            if missing_fields:
                if log_callback:
                    log_callback(f"⚠️ Certains champs ne sont pas présents dans le CSV: {', '.join(missing_fields)}")
                # Créer les colonnes manquantes avec des valeurs vides
                for field in missing_fields:
                    df[field] = ""
            
            # Grouper par Handle pour traiter chaque produit une seule fois
            unique_handles = df["Handle"].unique()
            
            # Filtrer selon la sélection
            if selected_handles:
                unique_handles = [h for h in unique_handles if h in selected_handles]
            
            total_products = len(unique_handles)
            
            if total_products == 0:
                error_msg = "Aucun produit à traiter"
                logger.warning(error_msg)
                if log_callback:
                    log_callback(f"⚠️ {error_msg}")
                return False, None, error_msg
            
            if log_callback:
                log_callback(f"📊 {total_products} produit(s) à traiter")
                log_callback(f"🎯 Champs à optimiser: {', '.join(enabled_fields)}")
            
            # Traiter chaque produit
            processed_count = 0
            errors = []
            
            for idx, handle in enumerate(unique_handles):
                # Vérifier l'annulation
                if cancel_check and cancel_check():
                    if log_callback:
                        log_callback("⚠️ Traitement annulé par l'utilisateur")
                    return False, None, "Traitement annulé"
                
                if progress_callback:
                    progress_callback(f"Traitement du produit {idx + 1}/{total_products}", idx + 1, total_products)
                
                # Récupérer toutes les lignes de ce produit
                product_rows = df[df["Handle"] == handle]
                
                if product_rows.empty:
                    continue
                
                # Prendre la première ligne pour extraire les infos du produit
                first_row = product_rows.iloc[0]
                
                # Construire le contexte
                context = {
                    "title": first_row.get("Title", ""),
                    "type": first_row.get("Type", ""),
                    "tags": first_row.get("Tags", ""),
                    "vendor": first_row.get("Vendor", ""),
                    "body_html": first_row.get("Body (HTML)", ""),
                    "sku": first_row.get("Variant SKU", ""),
                    "barcode": first_row.get("Variant Barcode", "")
                }
                
                # Traiter chaque champ activé
                product_updated = False
                
                for field_name in enabled_fields:
                    try:
                        # Récupérer le prompt pour ce champ
                        prompt = self.get_prompt_for_field(field_name)
                        
                        # Construire un contexte spécifique pour ce champ
                        field_context = context.copy()
                        
                        # Ajouter des informations spécifiques selon le champ
                        if "MPN" in field_name:
                            field_context["hint"] = f"SKU: {context.get('sku', 'N/A')}, Code-barres: {context.get('barcode', 'N/A')}"
                        
                        if log_callback:
                            log_callback(f"🤖 Optimisation du champ '{field_name}' pour '{context.get('title', handle)}'...")
                        
                        # Générer la valeur optimisée
                        optimized_value = self.ai_provider.generate(prompt, field_context, max_tokens=200)
                        
                        if not optimized_value:
                            continue
                        
                        # Nettoyer la valeur (supprimer les guillemets si présents)
                        optimized_value = optimized_value.strip().strip('"').strip("'")
                        
                        # Validation spécifique selon le champ
                        if "SEO Title" in field_name and len(optimized_value) > 60:
                            optimized_value = optimized_value[:57] + "..."
                        
                        if "SEO Description" in field_name and len(optimized_value) > 160:
                            optimized_value = optimized_value[:157] + "..."
                        
                        # Mettre à jour toutes les lignes de ce produit
                        df.loc[df["Handle"] == handle, field_name] = optimized_value
                        product_updated = True
                        
                        if log_callback:
                            log_callback(f"✅ '{field_name}' optimisé: {optimized_value[:50]}...")
                    
                    except AIProviderError as e:
                        error_msg = f"Erreur IA pour {field_name} ({handle}): {str(e)}"
                        logger.error(error_msg)
                        errors.append(error_msg)
                        if log_callback:
                            log_callback(f"❌ {error_msg}")
                        continue
                    
                    except Exception as e:
                        error_msg = f"Erreur inattendue pour {field_name} ({handle}): {str(e)}"
                        logger.error(error_msg, exc_info=True)
                        errors.append(error_msg)
                        if log_callback:
                            log_callback(f"❌ {error_msg}")
                        continue
                
                if product_updated:
                    processed_count += 1
                    if log_callback:
                        log_callback(f"✅ Produit '{context.get('title', handle)}' optimisé")
            
            # Générer le chemin de sortie si non spécifié
            if not output_path:
                input_path = Path(csv_path)
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                output_path = str(input_path.parent / f"{input_path.stem}_google_optimized_{timestamp}{input_path.suffix}")
            
            # Sauvegarder le CSV modifié
            if log_callback:
                log_callback(f"💾 Sauvegarde du fichier modifié...")
            
            df.to_csv(output_path, index=False)
            
            if log_callback:
                log_callback(f"✅ Fichier sauvegardé: {output_path}")
                log_callback(f"📊 Résumé: {processed_count}/{total_products} produit(s) optimisé(s) avec succès")
                if errors:
                    log_callback(f"⚠️ {len(errors)} erreur(s) rencontrée(s)")
            
            return True, output_path, None if not errors else f"{len(errors)} erreur(s) rencontrée(s)"
        
        except Exception as e:
            error_msg = f"Erreur lors de l'optimisation du CSV: {str(e)}"
            logger.error(error_msg, exc_info=True)
            if log_callback:
                log_callback(f"❌ {error_msg}")
            return False, None, error_msg

