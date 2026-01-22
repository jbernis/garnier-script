"""
Validateur de pertinence pour les catégories Google Shopping.

Valide qu'une catégorie générée par l'IA est cohérente avec le produit.
Approche hybrid: keywords + LLM en fallback.
"""

import json
import logging
from typing import Dict, Tuple, Optional, Any, List

logger = logging.getLogger(__name__)


class CategoryValidator:
    """Validateur de pertinence pour les catégories Google Shopping."""
    
    def __init__(self, db, ai_provider=None):
        """
        Initialise le validateur.
        
        Args:
            db: Instance de AIPromptsDB
            ai_provider: Provider IA optionnel pour validation LLM
        """
        self.db = db
        self.ai_provider = ai_provider
        self._init_validation_table()
        self._load_default_rules()
    
    def _init_validation_table(self):
        """Crée la table de règles de validation si elle n'existe pas."""
        cursor = self.db.conn.cursor()
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS category_validation_rules (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                product_type TEXT NOT NULL,
                product_vendor TEXT,
                allowed_keywords TEXT NOT NULL,
                forbidden_keywords TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_validation_type 
            ON category_validation_rules(product_type)
        ''')
        
        cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_validation_vendor 
            ON category_validation_rules(product_vendor)
        ''')
        
        self.db.conn.commit()
        logger.info("Table category_validation_rules initialisée")
    
    def _load_default_rules(self):
        """Charge les règles par défaut si la table est vide."""
        cursor = self.db.conn.cursor()
        cursor.execute('SELECT COUNT(*) FROM category_validation_rules')
        count = cursor.fetchone()[0]
        
        if count == 0:
            logger.info("Chargement des règles de validation par défaut...")
            default_rules = [
                {
                    'product_type': 'linge de maison',
                    'product_vendor': None,
                    'allowed_keywords': ['home', 'garden', 'linen', 'textile', 'bedding', 'table', 'nappe', 'kitchen', 'dining'],
                    'forbidden_keywords': ['electronics', 'electronique', 'computers', 'phone', 'software', 'automotive', 'tools', 'sports']
                },
                {
                    'product_type': 'nappe',
                    'product_vendor': None,
                    'allowed_keywords': ['table', 'linen', 'textile', 'dining', 'home', 'garden', 'kitchen'],
                    'forbidden_keywords': ['electronics', 'tools', 'automotive', 'clothing', 'sports']
                },
                {
                    'product_type': 'serviette',
                    'product_vendor': None,
                    'allowed_keywords': ['table', 'linen', 'textile', 'dining', 'home', 'napkin', 'kitchen'],
                    'forbidden_keywords': ['electronics', 'bath', 'towel', 'tools', 'automotive']
                },
                {
                    'product_type': 'vaisselle',
                    'product_vendor': None,
                    'allowed_keywords': ['home', 'kitchen', 'dining', 'tableware', 'cookware', 'dishes'],
                    'forbidden_keywords': ['electronics', 'clothing', 'vetement', 'tools', 'automotive']
                },
                {
                    'product_type': 'plat',
                    'product_vendor': None,
                    'allowed_keywords': ['kitchen', 'dining', 'tableware', 'cookware', 'dish', 'home'],
                    'forbidden_keywords': ['electronics', 'clothing', 'tools', 'automotive']
                }
            ]
            
            for rule in default_rules:
                cursor.execute('''
                    INSERT INTO category_validation_rules 
                    (product_type, product_vendor, allowed_keywords, forbidden_keywords)
                    VALUES (?, ?, ?, ?)
                ''', (
                    rule['product_type'],
                    rule['product_vendor'],
                    json.dumps(rule['allowed_keywords']),
                    json.dumps(rule['forbidden_keywords'])
                ))
            
            self.db.conn.commit()
            logger.info(f"{len(default_rules)} règles par défaut chargées")
    
    def validate(self, product_data: Dict[str, Any], category_path: str) -> Tuple[bool, str, str]:
        """
        Valide la pertinence d'une catégorie Google Shopping pour un produit.
        
        Args:
            product_data: Données du produit (Title, Type, Vendor, etc.)
            category_path: Chemin de la catégorie (ex: "Home & Garden > Kitchen > Table Linens")
            
        Returns:
            Tuple (is_valid, reason, severity)
            - is_valid: True si la catégorie est valide
            - reason: Explication de la validation/invalidation
            - severity: 'ok', 'warning', 'error'
        """
        try:
            # Étape 1: Validation par keywords
            is_valid_keywords, reason_keywords = self._validate_by_keywords(product_data, category_path)
            
            if is_valid_keywords:
                logger.debug(f"Validation keywords OK: {reason_keywords}")
                return (True, reason_keywords, 'ok')
            
            # Étape 2: Validation LLM en fallback (si provider disponible)
            if self.ai_provider:
                logger.info(f"Validation keywords échouée, tentative validation LLM...")
                is_valid_llm, reason_llm = self._validate_by_llm(product_data, category_path)
                
                if is_valid_llm:
                    logger.info(f"Validation LLM OK: {reason_llm}")
                    return (True, f"Validé par LLM: {reason_llm}", 'warning')
                else:
                    logger.warning(f"Validation LLM échouée: {reason_llm}")
                    return (False, f"Keywords: {reason_keywords} | LLM: {reason_llm}", 'error')
            else:
                # Pas de provider LLM, considérer comme erreur
                logger.warning(f"Validation keywords échouée, pas de LLM disponible")
                return (False, reason_keywords, 'error')
        
        except Exception as e:
            logger.error(f"Erreur lors de la validation de catégorie: {e}", exc_info=True)
            return (True, f"Validation impossible: {e}", 'warning')  # En cas d'erreur, accepter
    
    def _validate_by_keywords(self, product_data: Dict[str, Any], category_path: str) -> Tuple[bool, str]:
        """
        Validation par keywords (niveau 1).
        
        Args:
            product_data: Données du produit
            category_path: Chemin de catégorie
            
        Returns:
            Tuple (is_valid, reason)
        """
        product_type = product_data.get('Type', '').lower().strip()
        product_vendor = product_data.get('Vendor', '').lower().strip()
        product_title = product_data.get('Title', '').lower().strip()
        
        category_lower = category_path.lower()
        
        # Récupérer les règles applicables
        rules = self._get_applicable_rules(product_type, product_vendor)
        
        if not rules:
            # Pas de règles spécifiques, accepter par défaut
            logger.debug(f"Pas de règles trouvées pour type='{product_type}', vendor='{product_vendor}'")
            return (True, "Pas de règles spécifiques, catégorie acceptée par défaut")
        
        # Vérifier chaque règle
        for rule in rules:
            allowed = json.loads(rule['allowed_keywords'])
            forbidden = json.loads(rule['forbidden_keywords'])
            
            # Vérifier les mots interdits
            for keyword in forbidden:
                if keyword.lower() in category_lower:
                    return (False, f"Keyword interdit '{keyword}' trouvé dans la catégorie")
            
            # Vérifier qu'au moins un mot autorisé est présent
            allowed_found = [kw for kw in allowed if kw.lower() in category_lower]
            
            if allowed_found:
                return (True, f"Keywords autorisés trouvés: {', '.join(allowed_found)}")
            else:
                # Vérifier dans le titre du produit
                allowed_in_title = [kw for kw in allowed if kw.lower() in product_title]
                if allowed_in_title:
                    return (True, f"Keywords cohérents avec le produit: {', '.join(allowed_in_title)}")
        
        return (False, f"Aucun keyword autorisé trouvé dans la catégorie")
    
    def _validate_by_llm(self, product_data: Dict[str, Any], category_path: str) -> Tuple[bool, str]:
        """
        Validation par LLM (niveau 2, fallback).
        
        Args:
            product_data: Données du produit
            category_path: Chemin de catégorie
            
        Returns:
            Tuple (is_valid, reason)
        """
        if not self.ai_provider:
            return (False, "Provider LLM non disponible")
        
        try:
            prompt = f"""Évalue la PERTINENCE de cette catégorie Google Shopping pour ce produit.

PRODUIT:
- Titre: {product_data.get('Title', 'N/A')}
- Type: {product_data.get('Type', 'N/A')}
- Vendor: {product_data.get('Vendor', 'N/A')}

CATÉGORIE PROPOSÉE:
{category_path}

QUESTION: Cette catégorie est-elle PERTINENTE pour ce produit?

Réponds UNIQUEMENT par:
- "OUI" suivi d'une courte explication (1 phrase)
- "NON" suivi d'une courte explication (1 phrase)

Exemple: "OUI - La catégorie correspond au linge de table"
Exemple: "NON - Le produit est du linge de maison, pas de l'électronique"
"""
            
            response = self.ai_provider.generate(prompt, max_tokens=100)
            response_clean = response.strip().upper()
            
            if response_clean.startswith('OUI'):
                reason = response.strip()[3:].strip(' -:')
                return (True, reason if reason else "Validé par LLM")
            elif response_clean.startswith('NON'):
                reason = response.strip()[3:].strip(' -:')
                return (False, reason if reason else "Rejeté par LLM")
            else:
                logger.warning(f"Réponse LLM ambiguë: {response}")
                return (False, f"Réponse LLM non claire: {response[:100]}")
        
        except Exception as e:
            logger.error(f"Erreur validation LLM: {e}", exc_info=True)
            return (False, f"Erreur LLM: {str(e)[:100]}")
    
    def _get_applicable_rules(self, product_type: str, product_vendor: Optional[str]) -> List[Dict]:
        """
        Récupère les règles de validation applicables au produit.
        
        Args:
            product_type: Type du produit
            product_vendor: Vendor du produit (optionnel)
            
        Returns:
            Liste de dictionnaires de règles
        """
        cursor = self.db.conn.cursor()
        
        # Chercher d'abord une règle spécifique au type+vendor
        if product_vendor:
            cursor.execute('''
                SELECT * FROM category_validation_rules
                WHERE LOWER(product_type) = ? AND LOWER(product_vendor) = ?
            ''', (product_type.lower(), product_vendor.lower()))
            rules = cursor.fetchall()
            if rules:
                return [dict(r) for r in rules]
        
        # Sinon, chercher une règle pour le type seul
        cursor.execute('''
            SELECT * FROM category_validation_rules
            WHERE LOWER(product_type) = ? AND product_vendor IS NULL
        ''', (product_type.lower(),))
        rules = cursor.fetchall()
        
        return [dict(r) for r in rules]
    
    def add_rule(
        self,
        product_type: str,
        allowed_keywords: List[str],
        forbidden_keywords: List[str],
        product_vendor: Optional[str] = None
    ) -> int:
        """
        Ajoute une nouvelle règle de validation.
        
        Args:
            product_type: Type de produit
            allowed_keywords: Liste des mots-clés autorisés
            forbidden_keywords: Liste des mots-clés interdits
            product_vendor: Vendor spécifique (optionnel)
            
        Returns:
            ID de la règle créée
        """
        cursor = self.db.conn.cursor()
        
        cursor.execute('''
            INSERT INTO category_validation_rules 
            (product_type, product_vendor, allowed_keywords, forbidden_keywords)
            VALUES (?, ?, ?, ?)
        ''', (
            product_type,
            product_vendor,
            json.dumps(allowed_keywords),
            json.dumps(forbidden_keywords)
        ))
        
        self.db.conn.commit()
        rule_id = cursor.lastrowid
        
        logger.info(f"Règle de validation ajoutée: type='{product_type}', vendor='{product_vendor}', ID={rule_id}")
        return rule_id
    
    def delete_rule(self, rule_id: int):
        """Supprime une règle de validation."""
        cursor = self.db.conn.cursor()
        cursor.execute('DELETE FROM category_validation_rules WHERE id = ?', (rule_id,))
        self.db.conn.commit()
        logger.info(f"Règle de validation {rule_id} supprimée")
    
    def list_rules(self) -> List[Dict]:
        """Liste toutes les règles de validation."""
        cursor = self.db.conn.cursor()
        cursor.execute('SELECT * FROM category_validation_rules ORDER BY product_type')
        return [dict(r) for r in cursor.fetchall()]
