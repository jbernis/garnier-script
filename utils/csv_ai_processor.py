"""
Traitement des fichiers CSV Shopify avec l'IA pour modifier les descriptions.
"""

import pandas as pd
import logging
from typing import Optional, Dict, List, Callable, Set
from pathlib import Path
from datetime import datetime
from utils.ai_providers import AIProvider, AIProviderError

logger = logging.getLogger(__name__)


class CSVAIProcessor:
    """Processeur CSV pour modifier les descriptions avec l'IA."""
    
    def __init__(self, ai_provider: AIProvider):
        self.ai_provider = ai_provider
    
    def process_csv(
        self,
        csv_path: str,
        output_path: Optional[str] = None,
        prompt: str = "",
        selected_handles: Optional[Set[str]] = None,
        progress_callback: Optional[Callable[[str, int, int], None]] = None,
        log_callback: Optional[Callable[[str], None]] = None,
        cancel_check: Optional[Callable[[], bool]] = None
    ) -> tuple[bool, Optional[str], Optional[str]]:
        """
        Traite un fichier CSV pour modifier les descriptions avec l'IA.
        
        Args:
            csv_path: Chemin vers le fichier CSV à traiter
            output_path: Chemin de sortie (si None, génère automatiquement)
            prompt: Prompt pour modifier les descriptions
            selected_handles: Set de handles à traiter (si None, traite tous)
            progress_callback: Callback pour la progression (message, current, total)
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
            required_columns = ["Handle", "Body (HTML)"]
            missing_columns = [col for col in required_columns if col not in df.columns]
            if missing_columns:
                error_msg = f"Colonnes manquantes dans le CSV: {', '.join(missing_columns)}"
                logger.error(error_msg)
                if log_callback:
                    log_callback(f"❌ {error_msg}")
                return False, None, error_msg
            
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
            
            # Vérifier le prompt
            if not prompt or not prompt.strip():
                error_msg = "Le prompt ne peut pas être vide"
                logger.error(error_msg)
                if log_callback:
                    log_callback(f"❌ {error_msg}")
                return False, None, error_msg
            
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
                    "body_html": first_row.get("Body (HTML)", "")
                }
                
                # Appeler l'IA pour générer la nouvelle description
                try:
                    if log_callback:
                        log_callback(f"🤖 Génération de la description pour '{context.get('title', handle)}'...")
                    
                    new_description = self.ai_provider.generate(prompt, context)
                    
                    if not new_description:
                        error_msg = f"Description vide générée pour {handle}"
                        logger.warning(error_msg)
                        errors.append(error_msg)
                        if log_callback:
                            log_callback(f"⚠️ {error_msg}")
                        continue
                    
                    # Mettre à jour toutes les lignes de ce produit
                    df.loc[df["Handle"] == handle, "Body (HTML)"] = new_description
                    
                    processed_count += 1
                    
                    if log_callback:
                        log_callback(f"✅ Description mise à jour pour '{context.get('title', handle)}'")
                
                except AIProviderError as e:
                    error_msg = f"Erreur IA pour {handle}: {str(e)}"
                    logger.error(error_msg)
                    errors.append(error_msg)
                    if log_callback:
                        log_callback(f"❌ {error_msg}")
                    continue
                
                except Exception as e:
                    error_msg = f"Erreur inattendue pour {handle}: {str(e)}"
                    logger.error(error_msg, exc_info=True)
                    errors.append(error_msg)
                    if log_callback:
                        log_callback(f"❌ {error_msg}")
                    continue
            
            # Générer le chemin de sortie si non spécifié
            if not output_path:
                input_path = Path(csv_path)
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                output_path = str(input_path.parent / f"{input_path.stem}_ai_edited_{timestamp}{input_path.suffix}")
            
            # Sauvegarder le CSV modifié
            if log_callback:
                log_callback(f"💾 Sauvegarde du fichier modifié...")
            
            df.to_csv(output_path, index=False)
            
            if log_callback:
                log_callback(f"✅ Fichier sauvegardé: {output_path}")
                log_callback(f"📊 Résumé: {processed_count}/{total_products} produit(s) traité(s) avec succès")
                if errors:
                    log_callback(f"⚠️ {len(errors)} erreur(s) rencontrée(s)")
            
            return True, output_path, None if not errors else f"{len(errors)} erreur(s) rencontrée(s)"
        
        except Exception as e:
            error_msg = f"Erreur lors du traitement du CSV: {str(e)}"
            logger.error(error_msg, exc_info=True)
            if log_callback:
                log_callback(f"❌ {error_msg}")
            return False, None, error_msg

