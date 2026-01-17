"""
Module de traitement CSV avec les agents IA.
"""

import logging
from typing import Dict, List, Optional, Set, Callable, Tuple
from pathlib import Path
from datetime import datetime

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from apps.ai_editor.db import AIPromptsDB
from apps.ai_editor.csv_storage import CSVStorage
from apps.ai_editor.agents import DescriptionAgent, GoogleShoppingAgent, SEOAgent
from utils.ai_providers import get_provider, AIProviderError

logger = logging.getLogger(__name__)


class CSVAIProcessor:
    """Processeur CSV pour traiter les fichiers avec les agents IA."""
    
    def __init__(self, db: AIPromptsDB):
        """
        Initialise le processeur CSV.
        
        Args:
            db: Instance de AIPromptsDB
        """
        self.db = db
        self.csv_storage = CSVStorage(db)
    
    def process_csv(
        self,
        csv_path: str,
        prompt_set_id: int,
        provider_name: str,
        model_name: str,
        selected_fields: Dict[str, bool],
        selected_handles: Optional[Set[str]] = None,
        progress_callback: Optional[Callable[[str, int, int], None]] = None,
        log_callback: Optional[Callable[[str], None]] = None,
        cancel_check: Optional[Callable[[], bool]] = None
    ) -> Tuple[bool, Optional[str], Dict, Optional[int]]:
        """
        Traite un fichier CSV avec les agents IA.
        
        Args:
            csv_path: Chemin vers le fichier CSV à traiter
            prompt_set_id: ID de l'ensemble de prompts à utiliser
            provider_name: Nom du fournisseur IA (openai, claude, gemini)
            model_name: Nom du modèle à utiliser
            selected_fields: Dict avec clés 'description', 'google_category', 'seo' (valeurs bool)
            selected_handles: Set de handles à traiter (None = tous)
            progress_callback: Callback pour la progression (message, current, total)
            log_callback: Callback pour les logs
            cancel_check: Callback pour vérifier l'annulation
            
        Returns:
            Tuple (success, output_path, changes_dict, processing_result_id)
            - success: True si succès
            - output_path: Chemin du CSV généré
            - changes_dict: {handle: {field: {'original': ..., 'new': ...}}}
            - processing_result_id: ID du résultat de traitement
        """
        try:
            if log_callback:
                log_callback("Import du CSV en base de données...")
            
            # Vérifier l'annulation
            if cancel_check and cancel_check():
                return (False, None, {}, None)
            
            # 1. Importer le CSV en base de données
            csv_import_id = self.csv_storage.import_csv(csv_path)
            
            if log_callback:
                log_callback(f"CSV importé (ID: {csv_import_id})")
            
            # 2. Récupérer l'ensemble de prompts
            prompt_set = self.db.get_prompt_set(prompt_set_id)
            if not prompt_set:
                raise ValueError(f"Ensemble de prompts {prompt_set_id} introuvable")
            
            # 3. Récupérer les credentials AI depuis la base de données
            api_key = self.db.get_ai_credentials(provider_name)
            if not api_key:
                raise ValueError(f"Credentials AI non trouvés pour {provider_name}. Configurez-les dans la fenêtre IA.")
            
            # 4. Créer le fournisseur IA
            try:
                ai_provider = get_provider(provider_name, api_key=api_key, model=model_name)
            except AIProviderError as e:
                raise ValueError(f"Erreur lors de l'initialisation du fournisseur IA: {e}")
            
            # 5. Créer les agents IA
            agents = {}
            if selected_fields.get('description', False):
                agents['description'] = DescriptionAgent(
                    ai_provider,
                    prompt_set['system_prompt'],
                    prompt_set['description_prompt']
                )
            
            if selected_fields.get('google_category', False):
                agents['google_category'] = GoogleShoppingAgent(
                    ai_provider,
                    prompt_set['system_prompt'],
                    prompt_set['google_category_prompt']
                )
            
            if selected_fields.get('seo', False):
                agents['seo'] = SEOAgent(
                    ai_provider,
                    prompt_set['system_prompt'],
                    prompt_set['seo_prompt']
                )
            
            if not agents:
                raise ValueError("Aucun champ sélectionné pour le traitement")
            
            # 6. Récupérer les lignes à traiter
            if log_callback:
                log_callback("Récupération des lignes à traiter...")
            
            rows = self.csv_storage.get_csv_rows(csv_import_id, handles=selected_handles)
            
            if not rows:
                raise ValueError("Aucune ligne à traiter")
            
            # Grouper les lignes par handle pour traiter un produit complet
            products_by_handle = {}
            for row in rows:
                handle = row['data'].get('Handle', '')
                if handle not in products_by_handle:
                    products_by_handle[handle] = []
                products_by_handle[handle].append(row)
            
            total_products = len(products_by_handle)
            if log_callback:
                log_callback(f"{total_products} produit(s) à traiter")
            
            # 7. Traiter chaque produit
            changes_dict = {}
            processed_count = 0
            
            for handle, product_rows in products_by_handle.items():
                # Vérifier l'annulation
                if cancel_check and cancel_check():
                    return (False, None, changes_dict, None)
                
                if log_callback:
                    log_callback(f"Traitement du produit: {handle}")
                
                if progress_callback:
                    progress_callback(f"Traitement de {handle}", processed_count, total_products)
                
                # Utiliser la première ligne comme référence pour les données du produit
                product_data = product_rows[0]['data']
                
                # Traiter chaque champ sélectionné
                product_changes = {}
                
                # Description
                if 'description' in agents:
                    try:
                        original_value = product_data.get('Body (HTML)', '')
                        new_value = agents['description'].generate(product_data)
                        
                        # Mettre à jour toutes les lignes du produit
                        for row in product_rows:
                            self.csv_storage.update_csv_row(row['id'], {'Body (HTML)': new_value})
                        
                        product_changes['Body (HTML)'] = {
                            'original': original_value,
                            'new': new_value
                        }
                        
                        if log_callback:
                            log_callback(f"  ✓ Description mise à jour")
                    except Exception as e:
                        logger.error(f"Erreur lors du traitement de la description pour {handle}: {e}")
                        if log_callback:
                            log_callback(f"  ✗ Erreur description: {e}")
                
                # Google Shopping Category
                if 'google_category' in agents:
                    try:
                        original_value = product_data.get('Google Shopping / Google Product Category', '')
                        new_value = agents['google_category'].generate(product_data)
                        
                        # Mettre à jour toutes les lignes du produit
                        for row in product_rows:
                            self.csv_storage.update_csv_row(
                                row['id'],
                                {'Google Shopping / Google Product Category': new_value}
                            )
                        
                        product_changes['Google Shopping / Google Product Category'] = {
                            'original': original_value,
                            'new': new_value
                        }
                        
                        if log_callback:
                            log_callback(f"  ✓ Catégorie Google Shopping mise à jour")
                    except Exception as e:
                        logger.error(f"Erreur lors du traitement de la catégorie Google Shopping pour {handle}: {e}")
                        if log_callback:
                            log_callback(f"  ✗ Erreur catégorie: {e}")
                
                # SEO
                if 'seo' in agents:
                    try:
                        original_seo_title = product_data.get('SEO Title', '')
                        original_seo_description = product_data.get('SEO Description', '')
                        original_image_alt = product_data.get('Image Alt Text', '')
                        
                        seo_result = agents['seo'].generate(product_data)
                        
                        # Mettre à jour toutes les lignes du produit
                        for row in product_rows:
                            updates = {}
                            if 'seo_title' in seo_result:
                                updates['SEO Title'] = seo_result['seo_title']
                            if 'seo_description' in seo_result:
                                updates['SEO Description'] = seo_result['seo_description']
                            if 'image_alt_text' in seo_result:
                                updates['Image Alt Text'] = seo_result['image_alt_text']
                            
                            if updates:
                                self.csv_storage.update_csv_row(row['id'], updates)
                        
                        if 'seo_title' in seo_result:
                            product_changes['SEO Title'] = {
                                'original': original_seo_title,
                                'new': seo_result['seo_title']
                            }
                        if 'seo_description' in seo_result:
                            product_changes['SEO Description'] = {
                                'original': original_seo_description,
                                'new': seo_result['seo_description']
                            }
                        if 'image_alt_text' in seo_result:
                            product_changes['Image Alt Text'] = {
                                'original': original_image_alt,
                                'new': seo_result['image_alt_text']
                            }
                        
                        if log_callback:
                            log_callback(f"  ✓ SEO mis à jour")
                    except Exception as e:
                        logger.error(f"Erreur lors du traitement SEO pour {handle}: {e}")
                        if log_callback:
                            log_callback(f"  ✗ Erreur SEO: {e}")
                
                if product_changes:
                    changes_dict[handle] = product_changes
                
                processed_count += 1
            
            # 8. Exporter le CSV final
            if log_callback:
                log_callback("Export du CSV final...")
            
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_dir = Path("outputs/ai_editor")
            output_dir.mkdir(parents=True, exist_ok=True)
            output_path = str(output_dir / f"shopify_ai_processed_{timestamp}.csv")
            
            self.csv_storage.export_csv(csv_import_id, output_path)
            
            # 9. Sauvegarder le résultat de traitement
            processed_handles = list(changes_dict.keys())
            fields_processed = [field for field, enabled in selected_fields.items() if enabled]
            
            processing_result_id = self.db.save_processing_result(
                csv_import_id,
                output_path,
                prompt_set_id,
                provider_name,
                model_name,
                processed_handles,
                fields_processed
            )
            
            # 10. Sauvegarder les changements dans product_field_changes
            for handle, field_changes in changes_dict.items():
                # Trouver les lignes du produit
                product_rows = [r for r in rows if r['data'].get('Handle') == handle]
                
                for field_name, change_data in field_changes.items():
                    # Sauvegarder pour chaque ligne (ou seulement la première?)
                    if product_rows:
                        self.db.save_field_changes(
                            processing_result_id,
                            product_rows[0]['id'],
                            handle,
                            field_name,
                            change_data['original'],
                            change_data['new']
                        )
            
            if log_callback:
                log_callback(f"Traitement terminé: {len(changes_dict)} produit(s) modifié(s)")
            
            return (True, output_path, changes_dict, processing_result_id)
            
        except Exception as e:
            logger.error(f"Erreur lors du traitement CSV: {e}", exc_info=True)
            if log_callback:
                log_callback(f"Erreur: {e}")
            return (False, None, {}, None)
