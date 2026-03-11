"""
Module de traitement CSV avec les agents IA.
"""

import json
import logging
from typing import Dict, List, Optional, Set, Callable, Tuple, Any
from pathlib import Path
from datetime import datetime

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from apps.ai_editor.db import AIPromptsDB
from apps.ai_editor.csv_storage import CSVStorage
from apps.ai_editor.agents import GoogleShoppingAgent, SEOAgent, QualityControlAgent
from apps.ai_editor.category_validator import CategoryValidator
from apps.ai_editor.langgraph_categorizer.graph import GoogleShoppingCategorizationGraph
from utils.ai_providers import get_provider, AIProviderError
from utils.text_utils import normalize_type

logger = logging.getLogger(__name__)

# Mapping des clés JSON vers les champs CSV Shopify
SEO_FIELD_MAPPING = {
    'seo_title': 'SEO Title',
    'seo_description': 'SEO Description',
    'title': 'Title',
    'body_html': 'Body (HTML)',
    'tags': 'Tags',
    'image_alt_text': 'Image Alt Text',
    'type': 'Type'
}

def add_lagustotheque_tag(tags: str) -> str:
    """
    Ajoute automatiquement le tag 'Lagustothèque' aux tags existants (en dernière position).
    
    Args:
        tags: String de tags séparés par des virgules
        
    Returns:
        String de tags avec 'Lagustothèque' ajouté à la fin
    """
    if not tags or tags.strip() == '':
        return 'Lagustothèque'
    
    # Séparer les tags existants
    tag_list = [t.strip() for t in tags.split(',') if t.strip()]
    
    # Vérifier si Lagustothèque est déjà présent (insensible à la casse)
    lagustotheque_present = any(t.lower() == 'lagustothèque' for t in tag_list)
    
    # Ajouter Lagustothèque à la fin si pas déjà présent
    if not lagustotheque_present:
        tag_list.append('Lagustothèque')
    
    # Retourner les tags séparés par des virgules
    return ', '.join(tag_list)


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
    
    def _update_concordance_table(
        self,
        product_type: str,
        csv_type: str,
        category_code: str,
        category_path: str,
        confidence: float,
        force_update: bool = False
    ) -> bool:
        """
        Crée ou met à jour une règle dans type_category_mapping.
        Protège les règles à confiance >= seuil configurable contre les modifications automatiques.
        
        Args:
            product_type: Type original du CSV (ex: "Accessoire")
            csv_type: Type suggéré par SEO (ex: "TORCHONS")
            category_code: Code de catégorie Google
            category_path: Chemin de catégorie Google
            confidence: Confiance du LLM Google Shopping (0.0 - 1.0)
            force_update: Si True, permet la modification même des règles protégées
            
        Returns:
            True si créé/mis à jour, False si protégé ou erreur
        """
        if not product_type or not csv_type or not category_code or not category_path:
            return False
        
        # Récupérer le seuil depuis la configuration (par défaut 90%)
        confidence_threshold_percent = self.db.get_config_int('confidence_threshold', default=90)
        HIGH_CONFIDENCE_THRESHOLD = confidence_threshold_percent / 100.0  # Convertir en 0.0-1.0
        
        cursor = self.db.conn.cursor()
        
        # Vérifier si une règle existe déjà (uniquement par csv_type)
        cursor.execute('''
            SELECT id, confidence, category_code, category_path FROM type_category_mapping
            WHERE csv_type = ?
        ''', (csv_type.strip(),))
        
        existing = cursor.fetchone()
        
        # Protection: Si règle existe avec confiance >= 0.9, ne pas modifier automatiquement
        if existing and existing['confidence'] >= HIGH_CONFIDENCE_THRESHOLD and not force_update:
            logger.info(f"🔒 Règle protégée (confiance {existing['confidence']:.2f}): {csv_type} → {existing['category_path']}")
            return False
        
        # Créer ou mettre à jour la règle
        try:
            cursor.execute('''
                INSERT OR REPLACE INTO type_category_mapping
                (product_type, csv_type, category_code, category_path, confidence, created_by, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
            ''', (
                product_type.strip(),
                csv_type.strip(),
                category_code,
                category_path,
                confidence,
                'auto'
            ))
            self.db.conn.commit()
            
            action = "mise à jour" if existing else "créée"
            logger.info(f"📝 Règle {action}: {csv_type} → {category_path} (conf: {confidence:.2f})")
            return True
        except Exception as e:
            logger.error(f"Erreur lors de la création/mise à jour de la règle: {e}")
            return False
    
    def process_batch(
        self,
        csv_import_id: int,
        batch_handles: List[str],
        agents: Dict[str, Any],
        selected_fields: Dict[str, bool],
        log_callback: Optional[Callable[[str], None]] = None
    ) -> Dict[str, Dict]:
        """
        Traite un batch de produits en une seule requête API par agent.
        
        Args:
            csv_import_id: ID de l'import CSV
            batch_handles: Liste des handles à traiter dans ce batch
            agents: Dict des agents IA (seo, google_category)
            selected_fields: Champs sélectionnés pour le traitement
            log_callback: Callback pour les logs
            
        Returns:
            Dict {handle: {changements}}
        """
        all_changes = {}
        
        try:
            if log_callback:
                log_callback(f"🔄 Traitement batch de {len(batch_handles)} produits...")
            
            # Récupérer les données de tous les produits du batch
            products_data = {}
            for handle in batch_handles:
                rows = self.csv_storage.get_csv_rows(csv_import_id, [handle])
                if rows:
                    products_data[handle] = rows[0]['data']
            
            if not products_data:
                logger.warning(f"Aucune donnée trouvée pour le batch")
                return all_changes
            
            # Liste des produits pour le batch
            batch_products = list(products_data.values())
            
            # ===== TRAITEMENT SEO EN BATCH =====
            if 'seo' in agents:
                try:
                    if log_callback:
                        log_callback(f"  📝 Génération SEO batch ({len(batch_products)} produits)...")
                    
                    # Appeler generate_batch()
                    seo_results = agents['seo'].generate_batch(batch_products)
                    
                    # Traiter chaque résultat
                    for result in seo_results:
                        handle = result.get('handle')
                        if not handle or handle not in products_data:
                            logger.warning(f"Handle invalide ou non trouvé dans le batch: {handle}")
                            continue
                        
                        # Récupérer les lignes CSV pour ce produit
                        rows = self.csv_storage.get_csv_rows(csv_import_id, [handle])
                        if not rows:
                            continue
                        
                        # Préparer les changements
                        product_changes = {}
                        field_updates = {}
                        
                        # Déterminer quels champs sont sélectionnés
                        seo_selected_fields = None
                        if isinstance(selected_fields.get('seo'), dict):
                            # Nouveau format: {'seo': {'enabled': bool, 'fields': [liste]}}
                            seo_selected_fields = set(selected_fields['seo'].get('fields', []))
                        elif selected_fields.get('seo'):
                            # Ancien format: {'seo': True} - tous les champs sont sélectionnés
                            seo_selected_fields = set(SEO_FIELD_MAPPING.keys())
                        
                        # Mapper les champs SEO
                        for json_key, csv_field in SEO_FIELD_MAPPING.items():
                            if json_key in result and result[json_key]:
                                new_value = result[json_key]
                                
                                # NORMALISATION SPÉCIALE POUR LE CHAMP TYPE
                                # Le LLM génère 'type', on le normalise et on l'utilise pour type ET csv_type
                                if json_key == 'type':
                                    # Normaliser : MAJUSCULES, PLURIEL, SANS ACCENTS
                                    original_type = new_value
                                    new_value = normalize_type(new_value)
                                    logger.info(f"📝 {handle}: Type normalisé: '{original_type}' → '{new_value}'")
                                    
                                    # IMPORTANT : Cette valeur sera utilisée pour :
                                    # 1. Le champ CSV 'Type' (ci-dessous)
                                    # 2. Le champ cache 'csv_type' (lignes 342-368)
                                    # Garantie : type = csv_type = new_value
                                
                                original_value = rows[0]['data'].get(csv_field, '')
                                
                                # Ne mettre à jour que si le champ est sélectionné
                                if seo_selected_fields is None or json_key in seo_selected_fields:
                                    if new_value != original_value:
                                        field_updates[csv_field] = new_value
                                        product_changes[csv_field] = {
                                            'original': original_value,
                                            'new': new_value
                                        }
                        
                        # Ajouter le tag Lagustothèque
                        if 'Tags' in field_updates:
                            field_updates['Tags'] = add_lagustotheque_tag(field_updates['Tags'])
                        
                        # Contrôle qualité: vérifier que TOUS les champs requis ont une VALEUR (pas juste modifiés)
                        expected_fields = set(SEO_FIELD_MAPPING.values())
                        
                        # Règles de validation selon le prompt système SEO
                        VALIDATION_RULES = {
                            'SEO Title': {'min_length': 20, 'field_type': 'text'},
                            'SEO Description': {'min_length': 50, 'field_type': 'text'},
                            'Title': {'min_length': 10, 'field_type': 'text'},
                            'Body (HTML)': {'min_length': 350, 'field_type': 'html'},
                            'Tags': {'min_tags': 3, 'field_type': 'tags'},
                            'Image Alt Text': {'min_length': 10, 'field_type': 'text'},
                            'Type': {'min_length': 3, 'field_type': 'text'}
                        }
                        
                        # Vérifier les valeurs FINALES (après modification ou originales)
                        final_values = {}
                        quality_issues = []  # Liste des problèmes de qualité
                        
                        for csv_field in expected_fields:
                            # Utiliser la nouvelle valeur si modifiée, sinon l'originale
                            final_value = field_updates.get(csv_field, rows[0]['data'].get(csv_field, ''))
                            
                            if final_value and final_value.strip():
                                final_values[csv_field] = final_value
                                
                                # Appliquer les règles de validation
                                if csv_field in VALIDATION_RULES:
                                    rules = VALIDATION_RULES[csv_field]
                                    value_stripped = final_value.strip()
                                    
                                    # Validation de longueur
                                    if 'min_length' in rules:
                                        if len(value_stripped) < rules['min_length']:
                                            quality_issues.append(
                                                f'{csv_field} trop court ({len(value_stripped)} car., min {rules["min_length"]})'
                                            )
                                    
                                    # Validation tags (minimum 3 tags)
                                    if 'min_tags' in rules:
                                        tags = [t.strip() for t in value_stripped.split(',') if t.strip()]
                                        if len(tags) < rules['min_tags']:
                                            quality_issues.append(
                                                f'{csv_field}: {len(tags)} tag(s), minimum {rules["min_tags"]} requis'
                                            )
                                    
                                    # Validation HTML (vérifier présence de balises)
                                    if rules['field_type'] == 'html':
                                        if '<' not in value_stripped or '>' not in value_stripped:
                                            quality_issues.append(f'{csv_field} sans balises HTML')
                        
                        missing_fields = expected_fields - set(final_values.keys())
                        
                        # Mettre à jour toutes les lignes du produit
                        if field_updates:
                            for row in rows:
                                self.csv_storage.update_csv_row(row['id'], field_updates)
                            
                            # Déterminer le status selon la complétude ET la qualité
                            if missing_fields or quality_issues:
                                # Champs manquants OU problèmes de qualité - mettre à jour TOUTES les lignes du produit
                                all_issues = []
                                if missing_fields:
                                    all_issues.append(f'Champs manquants: {", ".join(missing_fields)}')
                                if quality_issues:
                                    all_issues.extend(quality_issues)
                                
                                for row in rows:
                                    self.csv_storage.update_csv_row_status(
                                        row['id'],
                                        'error',
                                        error_message=' | '.join(all_issues),
                                        ai_explanation=f'Problèmes détectés: {" / ".join(all_issues)}'
                                    )
                                if log_callback:
                                    if missing_fields:
                                        log_callback(f"  ⚠ {handle}: SEO partiel ({len(final_values)}/{len(expected_fields)} champs)")
                                    if quality_issues:
                                        log_callback(f"  ⚠ {handle}: {', '.join(quality_issues)}")
                            else:
                                # Tous les champs présents ET qualité OK - mettre à jour TOUTES les lignes du produit
                                for row in rows:
                                    self.csv_storage.update_csv_row_status(row['id'], 'completed')
                                if log_callback:
                                    log_callback(f"  ✓ {handle}: SEO complet")
                            
                            # Extraire le type depuis les résultats SEO
                            # Le LLM SEO génère UNIQUEMENT 'type', on l'utilise pour remplir csv_type
                            # Garantie : type = csv_type (même valeur, format identique)
                            type_value = field_updates.get('Type', '').strip()
                            
                            # Fallback : Si Type n'a pas été mis à jour, essayer de récupérer depuis result
                            if not type_value:
                                type_value = result.get('type', '').strip()
                                if type_value:
                                    type_value = normalize_type(type_value)
                            
                            # LOG: Afficher le type (qui sera copié dans csv_type)
                            logger.info(f"📋 {handle}: Type SEO (sera copié dans csv_type): '{type_value}'")
                            
                            if type_value:
                                # COPIE AUTOMATIQUE : type → csv_type
                                # Le type généré par SEO (déjà normalisé) est copié dans csv_type
                                # Garantie : CSV.Type = cache.csv_type = type_value
                                product_key = self.db._generate_product_key(rows[0]['data'])
                                
                                try:
                                    cursor = self.db.conn.cursor()
                                    cursor.execute('''
                                        UPDATE product_category_cache
                                        SET csv_type = ?, last_used_at = CURRENT_TIMESTAMP
                                        WHERE product_key = ?
                                    ''', (type_value, product_key))
                                    
                                    # Si pas de cache existant, créer une entrée minimale
                                    if cursor.rowcount == 0:
                                        self.db.save_to_cache(
                                            rows[0]['data'],
                                            '',  # category_code vide pour l'instant
                                            '',  # category_path vide pour l'instant
                                            0.0,  # confidence vide pour l'instant
                                            f'Type SEO copié dans csv_type: {type_value}',
                                            source='seo',
                                            csv_type=type_value
                                        )
                                    
                                    self.db.conn.commit()
                                    logger.info(f"💾 {handle}: Type copié → CSV.Type = cache.csv_type = '{type_value}'")
                                    
                                    # Note: La concordance sera créée APRÈS la phase Google Shopping
                                    # (quand on aura la catégorie complète)
                                except Exception as e:
                                    logger.error(f"Erreur lors de la sauvegarde de csv_type pour {handle}: {e}")
                            
                            all_changes[handle] = product_changes
                        else:
                            # Aucun champ généré - mettre à jour TOUTES les lignes
                            for row in rows:
                                self.csv_storage.update_csv_row_status(
                                    row['id'],
                                    'error',
                                    error_message='Aucun champ SEO généré',
                                    ai_explanation='L\'IA n\'a généré aucun champ SEO pour ce produit'
                                )
                            if log_callback:
                                log_callback(f"  ✗ {handle}: Aucun champ SEO généré")
                    
                    # Vérifier les produits manquants
                    returned_handles = {r.get('handle') for r in seo_results if r.get('handle')}
                    missing_handles = set(batch_handles) - returned_handles
                    
                    for handle in missing_handles:
                        rows = self.csv_storage.get_csv_rows(csv_import_id, [handle])
                        if rows:
                            # Mettre à jour TOUTES les lignes du produit manquant
                            for row in rows:
                                self.csv_storage.update_csv_row_status(
                                    row['id'],
                                    'error',
                                    error_message='Produit non retourné par l\'IA',
                                    ai_explanation='Le produit était inclus dans le batch mais absent de la réponse JSON'
                                )
                            if log_callback:
                                log_callback(f"  ✗ {handle}: Non retourné par l'IA")
                
                except Exception as e:
                    logger.error(f"Erreur batch SEO: {e}", exc_info=True)
                    # Marquer tout le batch en erreur - TOUTES les lignes
                    for handle in batch_handles:
                        rows = self.csv_storage.get_csv_rows(csv_import_id, [handle])
                        if rows:
                            for row in rows:
                                self.csv_storage.update_csv_row_status(
                                    row['id'],
                                    'error',
                                    error_message=str(e),
                                    ai_explanation=f'Erreur lors du traitement batch SEO: {e}'
                                )
                    if log_callback:
                        log_callback(f"  ✗ Erreur batch SEO: {str(e)[:100]}")
            
            # ===== TRAITEMENT GOOGLE SHOPPING EN BATCH (LANGGRAPH) =====
            logger.info(f"Vérification 'google_category' in agents: {'google_category' in agents}")
            if 'google_category' in agents:
                logger.info("Début traitement Google Shopping (règles + LangGraph si nécessaire)")
                try:
                    if log_callback:
                        log_callback(f"  🛍️ Catégorisation Google Shopping ({len(batch_products)} produits)...")
                    
                    # Créer le graph LangGraph seulement si nécessaire (lazy loading)
                    langgraph = None
                    llm_used_count = 0
                    rules_used_count = 0
                    
                    # Traiter chaque produit avec règles ou LangGraph
                    for product_data in batch_products:
                        handle = product_data.get('Handle')
                        if not handle:
                            continue
                        
                        logger.info(f"📦 {handle}: Début catégorisation")
                        
                        # ÉTAPE 0: Vérifier les règles Type → Catégorie (prioritaire!)
                        # Récupérer product_type (original) et csv_type (suggéré) depuis le cache
                        product_key = self.db._generate_product_key(product_data)
                        cursor = self.db.conn.cursor()
                        cursor.execute('''
                            SELECT product_type, csv_type FROM product_category_cache
                            WHERE product_key = ?
                        ''', (product_key,))
                        cached = cursor.fetchone()
                        
                        # product_type = toujours le type original du CSV
                        product_type = product_data.get('Type', '').strip()
                        
                        # csv_type = type suggéré par SEO si disponible, sinon product_type
                        csv_type = None
                        if cached and cached['csv_type'] and cached['csv_type'].strip():
                            csv_type = cached['csv_type'].strip()
                        
                        # Chercher dans la table de concordance avec product_type + csv_type
                        type_mapping = None
                        if product_type:
                            type_mapping = self.db.get_type_mapping(product_type, csv_type)
                        
                        if type_mapping:
                            # ✅ RÈGLE TYPE trouvée - Utilisation directe (0 appel LLM!)
                            category_code = type_mapping['category_code']
                            category_path = type_mapping['category_path']
                            confidence = type_mapping['confidence']
                            rationale = f"Règle: {csv_type} (utilisée {type_mapping['use_count']} fois)"
                            needs_review = False
                            rules_used_count += 1
                            
                            logger.info(f"📋 {handle}: RÈGLE trouvée: {csv_type} → {category_path}")
                            
                            # Sauvegarder dans le cache pour historique
                            self.db.save_to_cache(
                                product_data,
                                category_code,
                                category_path,
                                confidence,
                                rationale,
                                original_category_code=category_code,
                                original_category_path=category_path,
                                force_save=True,
                                source='type_mapping'
                            )
                        else:
                            # Pas de règle trouvée → Appeler le LLM Google Shopping
                            # Créer le LangGraph seulement si nécessaire (lazy loading)
                            if langgraph is None:
                                logger.info("🤖 Initialisation du LangGraph (au moins 1 produit sans règle)")
                                langgraph = GoogleShoppingCategorizationGraph(
                                    self.db,
                                    agents['google_category'].ai_provider
                                )
                            
                            logger.info(f"🤖 {handle}: Appel LangGraph (pas de règle)")
                            llm_used_count += 1
                            result = langgraph.categorize(product_data)
                            
                            category_code = result['category_code']
                            category_path = result['category_path']
                            confidence = result['confidence']
                            needs_review = result['needs_review']
                            rationale = result['rationale']
                            
                            # Sauvegarder l'original du LLM (avant fallback parent)
                            original_category_code = category_code
                            original_category_path = category_path
                            
                            logger.info(f"📦 {handle}: Catégorie LangGraph: {category_path} (code: {category_code})")
                            logger.info(f"  Confidence: {confidence:.2f} | Needs review: {needs_review}")
                            
                            # Si confidence < 50%, remonter à la catégorie parente
                            CONFIDENCE_THRESHOLD = 0.5
                            if confidence < CONFIDENCE_THRESHOLD and category_code:
                                parent = self.db.get_parent_category(category_path)
                                if parent:
                                    category_code, category_path = parent
                                    logger.warning(f"⬆️ {handle}: Confidence basse ({confidence:.0%}) → Catégorie parente")
                                    logger.warning(f"  Avant: {original_category_path}")
                                    logger.warning(f"  Après: {category_path}")
                                    rationale = f"Catégorie parente utilisée (confidence origine: {confidence:.0%}). " + rationale
                                    needs_review = True
                            
                            # Sauvegarder dans le cache pour export CSV
                            if category_code:
                                self.db.save_to_cache(
                                    product_data,
                                    category_code,
                                    category_path,
                                    confidence,
                                    rationale,
                                    original_category_code=original_category_code,
                                    original_category_path=original_category_path,
                                    force_save=True,
                                    source='langgraph'
                                )
                                
                                # Créer/mettre à jour la règle type_category_mapping
                                # Récupérer product_type et csv_type depuis le cache
                                product_key = self.db._generate_product_key(product_data)
                                cursor = self.db.conn.cursor()
                                cursor.execute('''
                                    SELECT product_type, csv_type FROM product_category_cache
                                    WHERE product_key = ?
                                ''', (product_key,))
                                cache_entry = cursor.fetchone()
                                
                                if cache_entry:
                                    product_type = cache_entry['product_type'] or product_data.get('Type', '').strip()
                                    csv_type = cache_entry['csv_type']
                                    
                                    # Créer/mettre à jour la règle si csv_type valide
                                    if not csv_type or not csv_type.strip():
                                        logger.warning(f"⚠️ {handle}: csv_type manquant. Le LLM SEO n'a pas généré de csv_type valide.")
                                    elif product_type and csv_type:
                                        self._update_concordance_table(
                                            product_type=product_type,
                                            csv_type=csv_type,
                                            category_code=category_code,
                                            category_path=category_path,
                                            confidence=confidence  # Confidence du LLM Google Shopping
                                        )
                        
                        logger.info(f"✅ {handle}: Catégorie finale: {category_path} (code: {category_code})")
                        logger.info(f"  Confidence: {confidence:.2f} | Needs review: {needs_review}")
                        logger.info(f"  Rationale: {rationale}")
                        
                        if category_code:
                            # Validation : vérifier que category_code est bien un ID, pas un chemin
                            if isinstance(category_code, str) and ' > ' in category_code:
                                logger.warning(f"⚠️ {handle}: category_code contient un chemin au lieu d'un ID: '{category_code}'")
                                logger.warning(f"  Ce chemin devrait être un ID numérique. Vérifier search_google_category().")
                            
                            # Sauvegarder dans la base
                            rows = self.csv_storage.get_csv_rows(csv_import_id, [handle])
                            if rows:
                                for row in rows:
                                    self.csv_storage.update_csv_row(
                                        row['id'],
                                        {
                                            'Google Shopping / Google Product Category': category_code,
                                            '_google_category_confidence': confidence,
                                            '_google_category_needs_review': needs_review,
                                            '_google_category_rationale': rationale
                                        }
                                    )
                                
                                # Statut selon needs_review
                                status = 'completed' if not needs_review else 'warning'
                                for row in rows:
                                    self.csv_storage.update_csv_row_status(
                                        row['id'],
                                        status,
                                        error_message=f"Confidence: {confidence:.0%}" if needs_review else None
                                    )
                                
                                if handle not in all_changes:
                                    all_changes[handle] = {}
                                all_changes[handle]['Google Shopping / Google Product Category'] = {
                                    'original': rows[0]['data'].get('Google Shopping / Google Product Category', ''),
                                    'new': category_code
                                }
                                
                                if log_callback:
                                    status_icon = "✓" if not needs_review else "⚠"
                                    log_callback(f"  {status_icon} {handle}: {category_path} (conf: {confidence:.0%})")
                        else:
                            # Échec complet
                            rows = self.csv_storage.get_csv_rows(csv_import_id, [handle])
                            if rows:
                                for row in rows:
                                    self.csv_storage.update_csv_row_status(
                                        row['id'],
                                        'error',
                                        error_message='Catégorisation échouée',
                                        ai_explanation=f'LangGraph: {rationale}'
                                    )
                            if log_callback:
                                log_callback(f"  ❌ {handle}: Échec catégorisation")
                    
                    # Message récapitulatif
                    if log_callback:
                        if rules_used_count > 0 and llm_used_count == 0:
                            log_callback(f"✓ Batch de {len(batch_products)} produits traité (100% règles, 0 appel LLM)")
                        elif rules_used_count > 0 and llm_used_count > 0:
                            log_callback(f"✓ Batch de {len(batch_products)} produits traité ({rules_used_count} règles, {llm_used_count} appels LLM)")
                        elif llm_used_count > 0:
                            log_callback(f"✓ Batch de {len(batch_products)} produits traité ({llm_used_count} appels LLM)")
                        else:
                            log_callback(f"✓ Batch de {len(batch_products)} produits traité")
                
                except Exception as e:
                    logger.error(f"Erreur LangGraph Google Shopping: {e}", exc_info=True)
                    # Marquer tout le batch en erreur
                    for handle in batch_handles:
                        rows = self.csv_storage.get_csv_rows(csv_import_id, [handle])
                        if rows:
                            for row in rows:
                                self.csv_storage.update_csv_row_status(
                                    row['id'],
                                    'error',
                                    error_message=str(e),
                                    ai_explanation=f'Erreur LangGraph: {e}'
                                )
                    if log_callback:
                        log_callback(f"  ✗ Erreur LangGraph: {str(e)[:100]}")
            
            if log_callback:
                log_callback(f"✓ Batch de {len(batch_handles)} produits traité")
            
            return all_changes
            
        except Exception as e:
            logger.error(f"Erreur lors du traitement du batch: {e}", exc_info=True)
            if log_callback:
                log_callback(f"✗ Erreur batch: {str(e)[:100]}")
            return all_changes
    
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
        cancel_check: Optional[Callable[[], bool]] = None,
        enable_search: bool = False,
        csv_import_id: Optional[int] = None
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
            # Vérifier l'annulation
            if cancel_check and cancel_check():
                return (False, None, {}, None)
            
            # 1. Importer le CSV en base de données (seulement si pas déjà importé)
            if csv_import_id is None:
                if log_callback:
                    log_callback("Import du CSV en base de données...")
                csv_import_id = self.csv_storage.import_csv(csv_path)
                if log_callback:
                    log_callback(f"CSV importé (ID: {csv_import_id})")
            else:
                if log_callback:
                    log_callback(f"Utilisation de l'import existant (ID: {csv_import_id})")
            
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
                # Récupérer les credentials Perplexity si enable_search est activé
                perplexity_api_key = None
                perplexity_model = None
                if enable_search and provider_name in ['openai', 'claude']:
                    perplexity_api_key = self.db.get_ai_credentials('perplexity')
                    if perplexity_api_key:
                        perplexity_model = self.db.get_ai_model('perplexity') or 'llama-3.1-sonar-large-128k-online'
                
                ai_provider = get_provider(
                    provider_name, 
                    api_key=api_key, 
                    model=model_name,
                    enable_search=enable_search,
                    perplexity_api_key=perplexity_api_key,
                    perplexity_model=perplexity_model
                )
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
                # Google Shopping utilise TOUJOURS Gemini (plus performant pour la catégorisation)
                gemini_api_key = self.db.get_ai_credentials('gemini')
                if not gemini_api_key:
                    raise ValueError("Credentials Gemini non trouvés. Google Shopping nécessite Gemini.")
                
                # Récupérer le modèle Gemini sauvegardé en base (ou None pour utiliser le défaut du provider)
                gemini_model = self.db.get_ai_model('gemini')
                
                gemini_provider = get_provider(
                    'gemini',
                    api_key=gemini_api_key,
                    model=gemini_model  # Si None, le provider utilisera son modèle par défaut
                )
                
                agents['google_category'] = GoogleShoppingAgent(
                    gemini_provider,
                    prompt_set['system_prompt'],
                    prompt_set['google_category_prompt']
                )
                # Donner accès à la taxonomie pour les catégories candidates
                agents['google_category'].set_database(self.db)
                
                if log_callback:
                    log_callback(f"🤖 Google Shopping: Gemini ({gemini_model})")
            
            if selected_fields.get('seo', False):
                agents['seo'] = SEOAgent(
                    ai_provider,
                    prompt_set['system_prompt'],
                    prompt_set['seo_prompt']
                )
                
                if log_callback:
                    log_callback(f"🤖 SEO: {provider_name.capitalize()} ({model_name})")
            
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
            
            # 7. Récupérer la taille du batch depuis la configuration
            batch_size = self.db.get_config_int('batch_size', default=20)
            logger.info(f"Taille du batch configurée: {batch_size}")
            if log_callback:
                log_callback(f"Configuration: batch_size={batch_size}")
            
            # 8. Traiter les produits
            changes_dict = {}
            processed_count = 0
            handles_list = list(products_by_handle.keys())
            
            # Diviser en batches
            if batch_size > 1:
                # Mode BATCH
                batches = [handles_list[i:i+batch_size] for i in range(0, len(handles_list), batch_size)]
                logger.info(f"Mode BATCH: {len(batches)} batch(s) de max {batch_size} produits")
                if log_callback:
                    log_callback(f"Mode BATCH: {len(batches)} batch(s) à traiter")
                
                for batch_idx, batch_handles in enumerate(batches, 1):
                    # Vérifier l'annulation
                    if cancel_check and cancel_check():
                        return (False, None, changes_dict, None)
                    
                    if log_callback:
                        log_callback(f"Batch {batch_idx}/{len(batches)}: {len(batch_handles)} produits")
                    
                    if progress_callback:
                        progress_callback(f"Batch {batch_idx}/{len(batches)}", processed_count, total_products)
                    
                    # Traiter le batch
                    batch_changes = self.process_batch(
                        csv_import_id,
                        batch_handles,
                        agents,
                        selected_fields,
                        log_callback
                    )
                    
                    # Fusionner les changements
                    changes_dict.update(batch_changes)
                    processed_count += len(batch_handles)
                    
                    if log_callback:
                        log_callback(f"Batch {batch_idx}/{len(batches)}: {len(batch_changes)} produit(s) traité(s)")
            else:
                # Mode SÉQUENTIEL (batch_size == 1)
                logger.info(f"Mode SÉQUENTIEL: traitement produit par produit")
                if log_callback:
                    log_callback(f"Mode SÉQUENTIEL: {len(handles_list)} produit(s) à traiter")
                
                for handle in handles_list:
                    # Vérifier l'annulation
                    if cancel_check and cancel_check():
                        return (False, None, changes_dict, None)
                    
                    if log_callback:
                        log_callback(f"Traitement du produit: {handle}")
                    
                    if progress_callback:
                        progress_callback(f"Traitement de {handle}", processed_count, total_products)
                    
                    # Traiter un seul produit comme un batch de 1
                    batch_changes = self.process_batch(
                        csv_import_id,
                        [handle],
                        agents,
                        selected_fields,
                        log_callback
                    )
                    
                    changes_dict.update(batch_changes)
                    processed_count += 1
            
            # 8. Sauvegarder le résultat de traitement
            # Note: Le CSV sera généré à la demande via le bouton "Générer CSV"
            processed_handles = list(changes_dict.keys())
            fields_processed = [field for field, enabled in selected_fields.items() if enabled]
            
            processing_result_id = self.db.save_processing_result(
                csv_import_id,
                None,  # Pas de fichier généré automatiquement
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
                log_callback(f"✅ Traitement terminé: {len(changes_dict)} produit(s) modifié(s)")
                log_callback(f"💡 Utilisez le bouton 'Générer CSV' pour exporter le fichier")
            
            return (True, None, changes_dict, processing_result_id)
            
        except Exception as e:
            logger.error(f"Erreur lors du traitement CSV: {e}", exc_info=True)
            if log_callback:
                log_callback(f"Erreur: {e}")
            return (False, None, {}, None)
    
    def process_single_product(
        self,
        csv_import_id: int,
        handle: str,
        prompt_set_id: int,
        provider_name: str,
        model_name: str,
        selected_fields: Dict,
        log_callback: Optional[Callable] = None,
        enable_search: bool = False
    ) -> Tuple[bool, Dict]:
        """
        Traite un seul produit pour les tests.
        
        Args:
            csv_import_id: ID de l'import CSV
            handle: Handle du produit à traiter
            prompt_set_id: ID de l'ensemble de prompts
            provider_name: Nom du fournisseur IA
            model_name: Nom du modèle
            selected_fields: Champs à traiter
            log_callback: Callback pour les logs
            enable_search: Activer la recherche Internet
            
        Returns:
            Tuple (success, changes_dict)
        """
        try:
            # Récupérer les credentials AI
            api_key = self.db.get_ai_credentials(provider_name)
            if not api_key:
                raise ValueError(f"Credentials AI non trouvés pour {provider_name}")
            
            # Créer le fournisseur IA
            perplexity_api_key = None
            perplexity_model = None
            if enable_search and provider_name in ['openai', 'claude']:
                perplexity_api_key = self.db.get_ai_credentials('perplexity')
                if perplexity_api_key:
                    perplexity_model = self.db.get_ai_model('perplexity') or 'llama-3.1-sonar-large-128k-online'
            
            from utils.ai_providers import get_provider
            ai_provider = get_provider(
                provider_name,
                api_key=api_key,
                model=model_name,
                enable_search=enable_search,
                perplexity_api_key=perplexity_api_key,
                perplexity_model=perplexity_model
            )
            
            # Récupérer l'ensemble de prompts
            prompt_set = self.db.get_prompt_set(prompt_set_id)
            if not prompt_set:
                raise ValueError(f"Ensemble de prompts {prompt_set_id} introuvable")
            
            # Créer les agents
            from apps.ai_editor.agents import SEOAgent, GoogleShoppingAgent
            
            # Google Shopping utilise TOUJOURS Gemini
            gemini_api_key = self.db.get_ai_credentials('gemini')
            if not gemini_api_key:
                raise ValueError("Credentials Gemini non trouvés. Google Shopping nécessite Gemini.")
            
            # Récupérer le modèle Gemini sauvegardé en base (ou None pour utiliser le défaut du provider)
            gemini_model = self.db.get_ai_model('gemini')
            
            gemini_provider = get_provider(
                'gemini',
                api_key=gemini_api_key,
                model=gemini_model  # Si None, le provider utilisera son modèle par défaut
            )
            
            agents = {
                'seo': SEOAgent(
                    ai_provider,
                    prompt_set['seo_system_prompt'],
                    prompt_set['seo_prompt']
                ),
                'google_category': GoogleShoppingAgent(
                    gemini_provider,
                    prompt_set['google_shopping_system_prompt'],
                    prompt_set['google_category_prompt']
                )
            }
            
            # Donner accès à la taxonomie pour les catégories candidates
            agents['google_category'].set_database(self.db)
            
            if log_callback:
                log_callback(f"🤖 SEO: {provider_name.capitalize()} ({model_name})")
                log_callback(f"🤖 Google Shopping: Gemini ({gemini_model})")
            
            # Traiter le produit
            changes_dict = self.process_batch(
                csv_import_id,
                [handle],
                agents,
                selected_fields,
                log_callback
            )
            
            # Retourner les changements pour ce produit
            if handle in changes_dict:
                return (True, changes_dict[handle])
            else:
                return (False, {})
                
        except Exception as e:
            logger.error(f"Erreur lors du traitement du produit {handle}: {e}", exc_info=True)
            return (False, {})
