"""
Module de gestion de la base de données SQLite pour le scraper Garnier.
"""

import sqlite3
import logging
from typing import List, Dict, Optional
from datetime import datetime
import os

logger = logging.getLogger(__name__)


class GarnierDB:
    """Gestionnaire de base de données pour les produits Garnier."""
    
    def __init__(self, db_path: str = "garnier_products.db"):
        """Initialise la connexion à la base de données."""
        self.db_path = db_path
        self.conn = None
        self._init_db()
    
    def _init_db(self):
        """Initialise les tables de la base de données."""
        self.conn = sqlite3.connect(self.db_path)
        self.conn.row_factory = sqlite3.Row  # Permet d'accéder aux colonnes par nom
        
        # Activer les contraintes de clés étrangères pour que CASCADE fonctionne
        # Cela permet de supprimer automatiquement les entrées dans gamme_products
        # quand un produit est supprimé
        self.conn.execute('PRAGMA foreign_keys = ON')
        
        cursor = self.conn.cursor()
        
        # Table des produits (niveau parent)
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS products (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                product_code TEXT NOT NULL UNIQUE,
                handle TEXT NOT NULL,
                title TEXT,
                description TEXT,
                vendor TEXT,
                product_type TEXT,
                tags TEXT,
                category TEXT,
                gamme TEXT,
                base_url TEXT,
                status TEXT DEFAULT 'pending',
                error_message TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Migration : Ajouter les colonnes status et error_message si elles n'existent pas
        try:
            cursor.execute('ALTER TABLE products ADD COLUMN status TEXT DEFAULT "pending"')
        except sqlite3.OperationalError:
            pass  # La colonne existe déjà
        
        try:
            cursor.execute('ALTER TABLE products ADD COLUMN error_message TEXT')
        except sqlite3.OperationalError:
            pass  # La colonne existe déjà
        
        # Migration : Ajouter la colonne is_new si elle n'existe pas
        try:
            cursor.execute('ALTER TABLE products ADD COLUMN is_new INTEGER DEFAULT 0')
        except sqlite3.OperationalError:
            pass  # La colonne existe déjà
        
        # Migration : Ajouter la colonne retry_count si elle n'existe pas
        try:
            cursor.execute('ALTER TABLE products ADD COLUMN retry_count INTEGER DEFAULT 0')
        except sqlite3.OperationalError:
            pass  # La colonne existe déjà
        
        # Table des variants (code_vl individuels)
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS product_variants (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                product_id INTEGER NOT NULL,
                code_vl TEXT NOT NULL UNIQUE,
                url TEXT NOT NULL,
                size_text TEXT,
                status TEXT DEFAULT 'pending',
                error_message TEXT,
                -- Données extraites
                sku TEXT,
                gencode TEXT,
                price_pa TEXT,
                price_pvc TEXT,
                stock INTEGER,
                size TEXT,
                color TEXT,
                material TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (product_id) REFERENCES products(id) ON DELETE CASCADE
            )
        ''')
        
        # Table des images (une par produit)
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS product_images (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                product_id INTEGER NOT NULL,
                image_url TEXT NOT NULL,
                image_position INTEGER,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (product_id) REFERENCES products(id) ON DELETE CASCADE
            )
        ''')
        
        # Table des gammes
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS gammes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT,
                url TEXT NOT NULL UNIQUE,
                category TEXT NOT NULL,
                status TEXT DEFAULT 'pending',
                retry_count INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Table de liaison gamme-products
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS gamme_products (
                gamme_id INTEGER NOT NULL,
                product_id INTEGER NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY (gamme_id, product_id),
                FOREIGN KEY (gamme_id) REFERENCES gammes(id) ON DELETE CASCADE,
                FOREIGN KEY (product_id) REFERENCES products(id) ON DELETE CASCADE
            )
        ''')
        
        # Migration : Ajouter retry_count si la colonne n'existe pas
        try:
            cursor.execute('ALTER TABLE gammes ADD COLUMN retry_count INTEGER DEFAULT 0')
        except sqlite3.OperationalError:
            pass  # La colonne existe déjà
        
        # Index pour améliorer les performances
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_variant_status ON product_variants(status)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_variant_code_vl ON product_variants(code_vl)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_variant_product ON product_variants(product_id)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_product_code ON products(product_code)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_product_handle ON products(handle)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_gamme_url ON gammes(url)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_gamme_status ON gammes(status)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_gamme_category ON gammes(category)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_gamme_products_gamme ON gamme_products(gamme_id)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_gamme_products_product ON gamme_products(product_id)')
        
        self.conn.commit()
        logger.info(f"Base de données initialisée: {self.db_path}")
    
    def add_product(self, product_code: str, handle: str, title: str = None, 
                    description: str = None, vendor: str = None, product_type: str = None,
                    tags: str = None, category: str = None, gamme: str = None,
                    base_url: str = None, status: str = None, error_message: str = None,
                    is_new: bool = False) -> int:
        """
        Ajoute un nouveau produit ou met à jour un produit existant uniquement si son status est 'error'.
        
        Si title est None ou vide, status sera automatiquement mis à 'error' et error_message sera défini.
        
        Args:
            is_new: True si le produit a le label "new" (Published sera FALSE dans le CSV)
        
        Returns:
            product_id: ID du produit (nouveau ou existant)
        """
        cursor = self.conn.cursor()
        
        # Déterminer le status et error_message si le titre est manquant
        if not title or not title.strip():
            if status is None:
                status = 'error'
            if error_message is None:
                error_message = 'Titre non trouvé ou vide'
        else:
            # Si le titre existe, status par défaut est 'pending' (sauf si spécifié)
            if status is None:
                status = 'pending'
            # Effacer l'error_message si le titre existe maintenant
            error_message = None
        
        # Vérifier si le produit existe déjà
        cursor.execute('SELECT id, status FROM products WHERE product_code = ?', (product_code,))
        existing = cursor.fetchone()
        
        if existing:
            existing_id = existing['id']
            existing_status = existing['status']
            
            # Toujours mettre à jour la gamme et la catégorie si elles sont fournies (même si le produit existe)
            # Cela permet de corriger les gammes/catégories malformées lors d'un retraitement
            # et de mettre à jour les catégories si elles changent lors d'un retraitement
            updates_needed = []
            update_params = []
            
            if gamme:
                updates_needed.append('gamme = ?')
                update_params.append(gamme)
                logger.debug(f"Gamme à mettre à jour pour le produit {product_code}: '{gamme}'")
            
            if category:
                updates_needed.append('category = ?')
                update_params.append(category)
                logger.debug(f"Catégorie à mettre à jour pour le produit {product_code}: '{category}'")
            
            if updates_needed:
                update_params.append(existing_id)
                cursor.execute(f'''
                    UPDATE products 
                    SET {', '.join(updates_needed)}, updated_at = CURRENT_TIMESTAMP
                    WHERE id = ?
                ''', tuple(update_params))
                self.conn.commit()
                logger.debug(f"Gamme/catégorie mise(s) à jour pour le produit {product_code}")
            
            # Ne mettre à jour complètement que si le status existant est 'error'
            if existing_status == 'error':
                # Mettre à jour le produit en erreur avec les nouvelles données
                cursor.execute('''
                    UPDATE products 
                    SET handle = ?, title = ?, description = ?, vendor = ?, product_type = ?, 
                        tags = ?, category = ?, gamme = ?, base_url = ?, 
                        status = ?, error_message = ?, is_new = ?, updated_at = CURRENT_TIMESTAMP
                    WHERE id = ?
                ''', (handle, title, description, vendor, product_type, tags, category, gamme, 
                      base_url, status, error_message, 1 if is_new else 0, existing_id))
                self.conn.commit()
                logger.debug(f"Produit {product_code} mis à jour complètement (était en erreur, status={existing_status})")
                return existing_id
            else:
                # Le produit existe mais n'est pas en erreur
                # PROTECTION : Si le nouveau titre est vide, forcer le passage en erreur
                if not title or not title.strip():
                    cursor.execute('''
                        UPDATE products 
                        SET status = 'error',
                            error_message = 'Titre non trouvé ou vide',
                            title = NULL,
                            updated_at = CURRENT_TIMESTAMP
                        WHERE id = ?
                    ''', (existing_id,))
                    self.conn.commit()
                    logger.warning(f"Produit {product_code} passé en erreur (titre vide détecté lors de la mise à jour)")
                    return existing_id
                
                # Sinon, retourner l'ID existant (gamme déjà mise à jour si fournie)
                logger.debug(f"Produit {product_code} existe déjà avec status={existing_status}")
                return existing_id
        
        # Le produit n'existe pas, l'ajouter
        try:
            cursor.execute('''
                INSERT INTO products 
                (product_code, handle, title, description, vendor, product_type, tags, category, gamme, base_url, status, error_message, is_new)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (product_code, handle, title, description, vendor, product_type, tags, category, gamme, base_url, status, error_message, 1 if is_new else 0))
            self.conn.commit()
            product_id = cursor.lastrowid
            logger.debug(f"Nouveau produit {product_code} ajouté (product_id={product_id})")
            return product_id
        except sqlite3.IntegrityError as e:
            # Si erreur d'intégrité (doublon), récupérer l'ID existant
            cursor.execute('SELECT id, status FROM products WHERE product_code = ?', (product_code,))
            row = cursor.fetchone()
            if row:
                logger.warning(f"Produit {product_code} existe déjà (race condition), retour de l'ID existant")
                return row['id']
            raise
    
    def update_product_status(self, product_id: int, status: str = None, error_message: str = None):
        """
        Met à jour le status et error_message d'un produit.
        
        Args:
            product_id: ID du produit à mettre à jour
            status: Nouveau statut (optionnel)
            error_message: Nouveau message d'erreur (optionnel, None pour effacer)
        """
        cursor = self.conn.cursor()
        updates = []
        params = []
        
        if status is not None:
            updates.append('status = ?')
            params.append(status)
        if error_message is not None:
            updates.append('error_message = ?')
            params.append(error_message)
        elif error_message is None and status == 'pending':
            # Si on remet à pending, effacer l'erreur
            updates.append('error_message = NULL')
        
        updates.append('updated_at = CURRENT_TIMESTAMP')
        params.append(product_id)
        
        if updates:
            query = f'UPDATE products SET {", ".join(updates)} WHERE id = ?'
            cursor.execute(query, params)
            self.conn.commit()
    
    def update_product_status_if_all_variants_processed(self, product_id: int) -> bool:
        """
        Vérifie et met à jour le statut d'un produit spécifique si tous ses variants sont traités.
        Appelé après chaque variant traité pour mettre à jour le produit immédiatement.
        
        Args:
            product_id: ID du produit à vérifier
            
        Returns:
            True si le statut du produit a été mis à jour, False sinon
        """
        cursor = self.conn.cursor()
        
        # Récupérer les stats de variants de ce produit
        cursor.execute('''
            SELECT p.id, p.status, p.product_code,
                   COUNT(pv.id) as total_variants,
                   SUM(CASE WHEN pv.status = 'completed' THEN 1 ELSE 0 END) as completed_variants,
                   SUM(CASE WHEN pv.status = 'error' THEN 1 ELSE 0 END) as error_variants,
                   SUM(CASE WHEN pv.status = 'pending' THEN 1 ELSE 0 END) as pending_variants
            FROM products p
            LEFT JOIN product_variants pv ON p.id = pv.product_id
            WHERE p.id = ?
            GROUP BY p.id
        ''', (product_id,))
        
        product = cursor.fetchone()
        if not product:
            return False
        
        current_status = product['status'] or 'pending'
        total_variants = product['total_variants'] or 0
        completed_variants = product['completed_variants'] or 0
        error_variants = product['error_variants'] or 0
        product_code = product['product_code']
        
        # Si aucun variant, ne rien faire
        if total_variants == 0:
            return False
        
        new_status = None
        
        # Si tous les variants sont complétés, le produit est complété
        if completed_variants == total_variants:
            new_status = 'completed'
        # Si tous les variants sont en erreur, le produit est en erreur
        elif error_variants == total_variants:
            new_status = 'error'
        # Sinon, le produit reste en pending (certains variants pas encore traités)
        else:
            new_status = 'pending'
        
        # Mettre à jour seulement si le status a changé
        if new_status and new_status != current_status:
            cursor.execute('''
                UPDATE products 
                SET status = ?, updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
            ''', (new_status, product_id))
            self.conn.commit()
            logger.info(f"✓ Produit {product_code} (ID {product_id}) passé à '{new_status}' ({completed_variants}/{total_variants} variants completed)")
            return True
        
        return False
    
    def update_products_status_after_processing(self):
        """
        Met à jour le status de TOUS les produits après traitement des variants.
        Utilisé à la fin du traitement pour s'assurer que tous les produits sont à jour.
        
        Note: Pendant le traitement, utilisez update_product_status_if_all_variants_processed()
        pour mettre à jour chaque produit dès que ses variants sont traités.
        """
        cursor = self.conn.cursor()
        
        # Récupérer tous les produits avec leurs variants
        cursor.execute('''
            SELECT p.id, p.status,
                   COUNT(pv.id) as total_variants,
                   SUM(CASE WHEN pv.status = 'completed' THEN 1 ELSE 0 END) as completed_variants,
                   SUM(CASE WHEN pv.status = 'error' THEN 1 ELSE 0 END) as error_variants,
                   SUM(CASE WHEN pv.status = 'pending' THEN 1 ELSE 0 END) as pending_variants
            FROM products p
            LEFT JOIN product_variants pv ON p.id = pv.product_id
            WHERE p.status != 'error' OR p.status IS NULL
            GROUP BY p.id
        ''')
        
        products = cursor.fetchall()
        updated_count = 0
        
        for product in products:
            product_id = product['id']
            current_status = product['status'] or 'pending'
            total_variants = product['total_variants'] or 0
            completed_variants = product['completed_variants'] or 0
            error_variants = product['error_variants'] or 0
            pending_variants = product['pending_variants'] or 0
            
            # Si aucun variant, ne pas changer le status
            if total_variants == 0:
                continue
            
            new_status = None
            
            # Si tous les variants sont complétés, le produit est complété
            if completed_variants == total_variants:
                new_status = 'completed'
            # Si tous les variants sont en erreur, le produit est en erreur
            elif error_variants == total_variants:
                new_status = 'error'
            # Sinon, le produit reste en pending (certains variants pas encore traités)
            else:
                new_status = 'pending'
            
            # Mettre à jour seulement si le status a changé
            if new_status and new_status != current_status:
                cursor.execute('''
                    UPDATE products 
                    SET status = ?, updated_at = CURRENT_TIMESTAMP
                    WHERE id = ?
                ''', (new_status, product_id))
                updated_count += 1
        
        self.conn.commit()
        logger.info(f"Mise à jour du status de {updated_count} produit(s) après traitement")
    
    def add_variant(self, product_id: int, code_vl: str, url: str, 
                   size_text: str = None, raise_on_duplicate: bool = True) -> tuple[int, bool]:
        """
        Ajoute un nouveau variant à un produit.
        Ne peut QUE ajouter, pas mettre à jour. Utilisez update_variant_collect() pour mettre à jour.
        
        Args:
            product_id: ID du produit parent
            code_vl: Code variant unique
            url: URL du variant
            size_text: Texte de la taille (optionnel)
            raise_on_duplicate: Si True, lève une exception si le variant existe déjà. Si False, retourne l'ID existant sans modifier.
        
        Returns:
            Tuple (variant_id, is_new) où:
            - variant_id: ID du variant (nouveau ou existant si raise_on_duplicate=False)
            - is_new: True si le variant a été créé, False s'il existait déjà
        
        Raises:
            sqlite3.IntegrityError: Si le code_vl existe déjà (et raise_on_duplicate=True)
        """
        cursor = self.conn.cursor()
        
        # Vérifier d'abord si le variant existe déjà
        cursor.execute('SELECT id, product_id FROM product_variants WHERE code_vl = ?', (code_vl,))
        existing = cursor.fetchone()
        
        if existing:
            existing_id = existing['id']
            existing_product_id = existing['product_id']
            
            # Si le variant existe avec un product_id différent
            if existing_product_id != product_id:
                # Si raise_on_duplicate=True, lever une exception
                if raise_on_duplicate:
                    cursor.execute('SELECT product_code, handle FROM products WHERE id = ?', (existing_product_id,))
                    existing_product = cursor.fetchone()
                    existing_product_code = existing_product['product_code'] if existing_product else 'inconnu'
                    
                    cursor.execute('SELECT product_code, handle FROM products WHERE id = ?', (product_id,))
                    new_product = cursor.fetchone()
                    new_product_code = new_product['product_code'] if new_product else 'inconnu'
                    
                    error_msg = (
                        f"DOUBLON DÉTECTÉ: Le code_vl '{code_vl}' existe déjà avec un produit différent ! "
                        f"Existant: produit_id={existing_product_id} ({existing_product_code}), "
                        f"Nouveau: product_id={product_id} ({new_product_code})"
                    )
                    logger.error(error_msg)
                    raise sqlite3.IntegrityError(error_msg)
                else:
                    # Si raise_on_duplicate=False, retourner l'ID existant sans modifier
                    logger.warning(f"Variant {code_vl} existe déjà avec product_id={existing_product_id}, "
                                 f"tentative d'ajout avec product_id={product_id}. "
                                 f"Retour de l'ID existant sans modification.")
                    return (existing_id, False)
            
            # Le variant existe déjà avec le même product_id
            if raise_on_duplicate:
                error_msg = f"Le variant '{code_vl}' existe déjà (product_id={existing_product_id})"
                logger.error(error_msg)
                raise sqlite3.IntegrityError(error_msg)
            else:
                # Retourner l'ID existant sans modifier
                logger.debug(f"Variant {code_vl} existe déjà (product_id={existing_product_id}), retour de l'ID existant")
                return (existing_id, False)
        
        # Le variant n'existe pas, on l'ajoute
        try:
            cursor.execute('''
                INSERT INTO product_variants 
                (product_id, code_vl, url, size_text, status)
                VALUES (?, ?, ?, ?, 'pending')
            ''', (product_id, code_vl, url, size_text))
            self.conn.commit()
            variant_id = cursor.lastrowid
            logger.debug(f"Nouveau variant {code_vl} ajouté (product_id={product_id})")
            return (variant_id, True)
        except sqlite3.IntegrityError as e:
            # Double vérification (race condition possible)
            cursor.execute('SELECT id FROM product_variants WHERE code_vl = ?', (code_vl,))
            row = cursor.fetchone()
            if row:
                # Le variant existe déjà, retourner l'ID existant
                logger.debug(f"Variant {code_vl} existe déjà (race condition), retour de l'ID existant")
                return (row['id'], False)
            else:
                raise
    
    def update_variant_collect(self, variant_id: int, url: str = None, 
                              size_text: str = None):
        """
        Met à jour les champs de base d'un variant lors de la collecte.
        Peut mettre à jour : url, size_text, error_message (NULL), status ('pending'), updated_at
        
        Args:
            variant_id: ID du variant à mettre à jour
            url: Nouvelle URL (optionnel)
            size_text: Nouveau texte de taille (optionnel)
        """
        cursor = self.conn.cursor()
        updates = []
        params = []
        
        if url is not None:
            updates.append('url = ?')
            params.append(url)
        if size_text is not None:
            updates.append('size_text = ?')
            params.append(size_text)
        
        # Toujours effacer les erreurs et remettre à pending lors d'une nouvelle collecte
        updates.append('error_message = NULL')
        updates.append('status = ?')
        params.append('pending')
        updates.append('updated_at = CURRENT_TIMESTAMP')
        params.append(variant_id)
        
        if updates:
            query = f'UPDATE product_variants SET {", ".join(updates)} WHERE id = ?'
            cursor.execute(query, params)
            self.conn.commit()
    
    def update_variant_data(self, variant_id: int,
                           price_pa: str = None, price_pvc: str = None, stock: int = None,
                           sku: str = None, gencode: str = None,
                           size: str = None, color: str = None, material: str = None,
                           status: str = 'pending', error_message: str = None):
        """
        Met à jour les données d'un variant après traitement.
        Peut mettre à jour :
        - price_pa, price_pvc, stock, sku, gencode, size, color, material, error_message, status, updated_at
        
        Les champs suivants ne doivent PAS être modifiés :
        - id, product_id, url, size_text, code_vl
        """
        cursor = self.conn.cursor()
        updates = []
        params = []
        
        if price_pa is not None:
            updates.append('price_pa = ?')
            params.append(price_pa)
        if price_pvc is not None:
            updates.append('price_pvc = ?')
            params.append(price_pvc)
        if stock is not None:
            updates.append('stock = ?')
            params.append(stock)
        if sku is not None:
            updates.append('sku = ?')
            params.append(sku)
        if gencode is not None:
            updates.append('gencode = ?')
            params.append(gencode)
        if size is not None:
            updates.append('size = ?')
            params.append(size)
        if color is not None:
            updates.append('color = ?')
            params.append(color)
        if material is not None:
            updates.append('material = ?')
            params.append(material)
        if status:
            updates.append('status = ?')
            params.append(status)
        if error_message is not None:
            updates.append('error_message = ?')
            params.append(error_message)
        
        updates.append('updated_at = CURRENT_TIMESTAMP')
        params.append(variant_id)
        
        if updates:
            query = f'UPDATE product_variants SET {", ".join(updates)} WHERE id = ?'
            cursor.execute(query, params)
            self.conn.commit()
    
    def mark_variant_processing(self, variant_id: int):
        """Marque un variant comme en cours de traitement."""
        cursor = self.conn.cursor()
        cursor.execute('''
            UPDATE product_variants 
            SET status = 'processing', updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
        ''', (variant_id,))
        self.conn.commit()
    
    def mark_variant_error(self, variant_id: int, error_message: str):
        """Marque un variant comme erreur."""
        cursor = self.conn.cursor()
        cursor.execute('''
            UPDATE product_variants 
            SET status = 'error', error_message = ?, updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
        ''', (error_message[:500], variant_id))  # Limiter la taille du message
        self.conn.commit()
    
    def get_pending_variants(self, limit: Optional[int] = None, category: Optional[str] = None, categories: Optional[List[str]] = None, gamme: Optional[str] = None) -> List[Dict]:
        """Récupère les variants en attente de traitement, optionnellement filtrés par catégorie ou gamme."""
        cursor = self.conn.cursor()
        query = '''
            SELECT pv.id, pv.code_vl, pv.url, pv.size_text, p.product_code, p.handle
            FROM product_variants pv
            JOIN products p ON pv.product_id = p.id
            WHERE pv.status = 'pending'
        '''
        params = []
        
        # Gérer plusieurs catégories (priorité sur category)
        if categories and len(categories) > 0:
            placeholders = ','.join(['?'] * len(categories))
            query += f' AND p.category IN ({placeholders})'
            params.extend(categories)
        elif category:
            query += ' AND p.category = ?'
            params.append(category)
        
        if gamme:
            query += ' AND (p.gamme = ? OR p.gamme LIKE ?)'
            params.append(gamme)
            params.append(f'{gamme}%')
        
        query += ' ORDER BY pv.id'
        
        if limit:
            query += f' LIMIT {limit}'
        
        cursor.execute(query, params)
        return [dict(row) for row in cursor.fetchall()]
    
    def get_variant_by_code_vl(self, code_vl: str) -> Optional[Dict]:
        """Récupère un variant par son code_vl."""
        cursor = self.conn.cursor()
        cursor.execute('''
            SELECT pv.*, p.product_code, p.handle, p.title, p.category, p.gamme
            FROM product_variants pv
            JOIN products p ON pv.product_id = p.id
            WHERE pv.code_vl = ?
        ''', (code_vl,))
        row = cursor.fetchone()
        return dict(row) if row else None
    
    def get_error_variants(self, limit: Optional[int] = None, category: Optional[str] = None, categories: Optional[List[str]] = None, gamme: Optional[str] = None) -> List[Dict]:
        """Récupère les variants en erreur, optionnellement filtrés par catégorie ou gamme."""
        cursor = self.conn.cursor()
        query = '''
            SELECT pv.id, pv.code_vl, pv.url, pv.error_message, p.product_code
            FROM product_variants pv
            JOIN products p ON pv.product_id = p.id
            WHERE pv.status = 'error'
        '''
        params = []
        
        # Gérer plusieurs catégories (priorité sur category)
        if categories and len(categories) > 0:
            placeholders = ','.join(['?'] * len(categories))
            query += f' AND p.category IN ({placeholders})'
            params.extend(categories)
        elif category:
            query += ' AND p.category = ?'
            params.append(category)
        
        if gamme:
            query += ' AND (p.gamme = ? OR p.gamme LIKE ?)'
            params.append(gamme)
            params.append(f'{gamme}%')
        
        query += ' ORDER BY pv.updated_at DESC'
        
        if limit:
            query += f' LIMIT {limit}'
        
        cursor.execute(query, params)
        return [dict(row) for row in cursor.fetchall()]
    
    def get_category_stats(self, category: str) -> Dict:
        """
        Récupère les statistiques détaillées d'une catégorie.
        
        Returns:
            {
                'products': {
                    'completed': 45,
                    'pending': 3,
                    'error': 2,
                    'total': 50
                },
                'variants': {
                    'completed': 180,
                    'pending': 15,
                    'error': 5,
                    'total': 200
                }
            }
        """
        cursor = self.conn.cursor()
        
        # Stats des produits
        cursor.execute('''
            SELECT 
                status,
                COUNT(*) as count
            FROM products
            WHERE category = ?
            GROUP BY status
        ''', (category,))
        
        products_stats = {'completed': 0, 'pending': 0, 'error': 0, 'total': 0}
        for row in cursor.fetchall():
            products_stats[row['status']] = row['count']
            products_stats['total'] += row['count']
        
        # Stats des variants
        cursor.execute('''
            SELECT 
                pv.status,
                COUNT(*) as count
            FROM product_variants pv
            JOIN products p ON pv.product_id = p.id
            WHERE p.category = ?
            GROUP BY pv.status
        ''', (category,))
        
        variants_stats = {'completed': 0, 'pending': 0, 'error': 0, 'total': 0}
        for row in cursor.fetchall():
            variants_stats[row['status']] = row['count']
            variants_stats['total'] += row['count']
        
        return {
            'products': products_stats,
            'variants': variants_stats
        }
    
    def get_available_categories(self) -> List[str]:
        """Récupère la liste des catégories disponibles dans la DB."""
        cursor = self.conn.cursor()
        cursor.execute('''
            SELECT DISTINCT category
            FROM products
            WHERE category IS NOT NULL
            ORDER BY category
        ''')
        return [row['category'] for row in cursor.fetchall()]
    
    def get_available_gammes(self, category: str = None) -> List[str]:
        """
        Récupère la liste des gammes disponibles dans la DB.
        Si une catégorie est spécifiée, retourne toutes les gammes de cette catégorie depuis la table gammes.
        Sinon, filtre uniquement les gammes qui ont au moins 1 produit avec au moins 1 variant en status 'completed'.
        
        Args:
            category: Filtrer par catégorie (optionnel)
        
        Returns:
            Liste des gammes disponibles
        """
        cursor = self.conn.cursor()
        
        if category:
            # Si une catégorie est spécifiée, utiliser la table gammes comme source principale
            # (c'est la source de vérité pour les gammes par catégorie)
            # Retourner toutes les gammes de cette catégorie, même si name est NULL
            query = '''
                SELECT DISTINCT COALESCE(g.name, '') as gamme
                FROM gammes g
                WHERE g.category = ?
                ORDER BY gamme
            '''
            params = [category]
            
            cursor.execute(query, params)
            gammes_from_table = [row['gamme'] for row in cursor.fetchall() if row['gamme']]
            
            # Aussi vérifier s'il y a des gammes dans products qui ne sont pas dans gammes
            query_products = '''
                SELECT DISTINCT p.gamme
                FROM products p
                WHERE p.category = ?
                AND p.gamme IS NOT NULL 
                AND p.gamme != ''
                AND NOT EXISTS (SELECT 1 FROM gammes g WHERE g.name = p.gamme AND g.category = p.category)
                ORDER BY p.gamme
            '''
            cursor.execute(query_products, [category])
            gammes_from_products = [row['gamme'] for row in cursor.fetchall()]
            
            # Combiner les deux listes et dédupliquer
            all_gammes = list(set(gammes_from_table + gammes_from_products))
            return sorted(all_gammes)
        else:
            # Sinon, filtrer uniquement les gammes avec variants complétés (comportement original)
            query = '''
                SELECT DISTINCT p.gamme
                FROM products p
                INNER JOIN product_variants v ON p.id = v.product_id
                WHERE p.gamme IS NOT NULL 
                AND p.gamme != ''
                AND v.status = 'completed'
                ORDER BY p.gamme
            '''
            params = []
            cursor.execute(query, params)
            return [row['gamme'] for row in cursor.fetchall()]
    
    def add_image(self, product_id: int, image_url: str, position: int = None):
        """Ajoute une image à un produit."""
        cursor = self.conn.cursor()
        cursor.execute('''
            INSERT OR IGNORE INTO product_images 
            (product_id, image_url, image_position)
            VALUES (?, ?, ?)
        ''', (product_id, image_url, position))
        self.conn.commit()
    
    def get_product_variants(self, product_id: int) -> List[Dict]:
        """Récupère tous les variants d'un produit."""
        cursor = self.conn.cursor()
        cursor.execute('''
            SELECT * FROM product_variants 
            WHERE product_id = ? 
            ORDER BY code_vl
        ''', (product_id,))
        return [dict(row) for row in cursor.fetchall()]
    
    def get_product_images(self, product_id: int) -> List[Dict]:
        """Récupère toutes les images d'un produit."""
        cursor = self.conn.cursor()
        cursor.execute('''
            SELECT * FROM product_images 
            WHERE product_id = ? 
            ORDER BY image_position, id
        ''', (product_id,))
        return [dict(row) for row in cursor.fetchall()]
    
    def get_completed_products(self, categories: List[str] = None, gamme: str = None, gammes: List[str] = None, exclude_errors: bool = False) -> List[Dict]:
        """
        Récupère tous les produits avec au moins un variant complété.
        
        Si des gammes sont spécifiées, utilise la table gamme_products pour récupérer
        tous les produits liés à ces gammes, même si leurs catégories diffèrent.
        Cela permet d'exporter tous les produits d'une gamme même si elle appartient
        à plusieurs catégories.
        
        Args:
            categories: Liste de catégories à filtrer (None = toutes les catégories)
            gamme: Nom de la gamme à filtrer (None = toutes les gammes, pour compatibilité)
            gammes: Liste de gammes à filtrer (priorité sur gamme si fourni)
            exclude_errors: Si True, exclut les produits avec status='error'
        
        Returns:
            Liste de dictionnaires contenant les produits
        """
        cursor = self.conn.cursor()
        
        # Gérer plusieurs gammes (priorité sur gamme)
        gamme_ids = None
        if gammes and len(gammes) > 0:
            # Trouver les IDs de gammes correspondant aux noms fournis
            # Utiliser LIKE pour matcher même si la gamme dans la DB est malformée
            gamme_id_conditions = []
            gamme_id_params = []
            for g in gammes:
                gamme_id_conditions.append("g.name LIKE ?")
                gamme_id_params.append(f"%{g}%")
            
            gamme_id_query = f'''
                SELECT DISTINCT g.id
                FROM gammes g
                WHERE {' OR '.join(gamme_id_conditions)}
            '''
            cursor.execute(gamme_id_query, gamme_id_params)
            gamme_ids = [row['id'] for row in cursor.fetchall()]
            logger.debug(f"Gammes trouvées: {len(gamme_ids)} IDs pour les noms {gammes}")
        elif gamme:
            # Trouver l'ID de la gamme correspondant au nom fourni
            cursor.execute('SELECT id FROM gammes WHERE name LIKE ?', (f"%{gamme}%",))
            gamme_ids = [row['id'] for row in cursor.fetchall()]
            logger.debug(f"Gamme trouvée: {len(gamme_ids)} ID(s) pour le nom '{gamme}'")
        
        # Si des gammes sont spécifiées, utiliser la table gamme_products
        if gamme_ids and len(gamme_ids) > 0:
            # Utiliser gamme_products pour récupérer tous les produits liés à ces gammes
            # Ne pas filtrer strictement par p.category dans ce cas
            conditions = ["pv.status = 'completed'"]
            params = []
            
            placeholders = ','.join(['?'] * len(gamme_ids))
            conditions.append(f"gp.gamme_id IN ({placeholders})")
            params.extend(gamme_ids)
            
            if exclude_errors:
                conditions.append("p.status != 'error'")
            
            where_clause = " AND ".join(conditions)
            
            query = f'''
                SELECT DISTINCT p.*
                FROM products p
                JOIN product_variants pv ON p.id = pv.product_id
                JOIN gamme_products gp ON p.id = gp.product_id
                WHERE {where_clause}
                ORDER BY p.product_code
            '''
            cursor.execute(query, params)
            return [dict(row) for row in cursor.fetchall()]
        
        # Sinon, utiliser l'ancienne logique (filtrage par p.gamme LIKE)
        conditions = ["pv.status = 'completed'"]
        params = []
        
        if categories and len(categories) > 0:
            placeholders = ','.join(['?'] * len(categories))
            conditions.append(f"p.category IN ({placeholders})")
            params.extend(categories)
        
        # Si gamme/gammes sont fournis mais aucun ID trouvé, utiliser LIKE sur p.gamme
        if gammes and len(gammes) > 0:
            # Utiliser OR pour combiner plusieurs gammes avec LIKE
            gamme_conditions = []
            for g in gammes:
                gamme_conditions.append("p.gamme LIKE ?")
                params.append(f"%{g}%")
            conditions.append(f"({' OR '.join(gamme_conditions)})")
        elif gamme:
            # Utiliser LIKE pour matcher même si la gamme dans la DB est malformée
            # Ex: DB = "37412 - TAIE ZIG ZAG CURRYNRPA 18,75 €", paramètre = "ZIG ZAG CURRY"
            conditions.append("p.gamme LIKE ?")
            params.append(f"%{gamme}%")
        
        if exclude_errors:
            conditions.append("p.status != 'error'")
        
        where_clause = " AND ".join(conditions)
        
        query = f'''
            SELECT DISTINCT p.*
            FROM products p
            JOIN product_variants pv ON p.id = pv.product_id
            WHERE {where_clause}
            ORDER BY p.product_code
        '''
        cursor.execute(query, params)
        
        return [dict(row) for row in cursor.fetchall()]
    
    def get_available_categories(self) -> List[str]:
        """Récupère la liste des catégories disponibles dans la base de données."""
        cursor = self.conn.cursor()
        cursor.execute('''
            SELECT DISTINCT category
            FROM products
            WHERE category IS NOT NULL AND category != ''
            ORDER BY category
        ''')
        return [row['category'] for row in cursor.fetchall()]
    
    def get_stats(self) -> Dict:
        """Récupère les statistiques de la base de données."""
        cursor = self.conn.cursor()
        
        stats = {}
        
        # Nombre de produits
        cursor.execute('SELECT COUNT(*) FROM products')
        stats['total_products'] = cursor.fetchone()[0]
        
        # Nombre de variants par statut
        cursor.execute('''
            SELECT status, COUNT(*) 
            FROM product_variants 
            GROUP BY status
        ''')
        stats['variants_by_status'] = dict(cursor.fetchall())
        
        # Total de variants
        cursor.execute('SELECT COUNT(*) FROM product_variants')
        stats['total_variants'] = cursor.fetchone()[0]
        
        return stats
    
    # ========== Méthodes pour les gammes ==========
    
    def add_gamme(self, url: str, category: str, name: str = None, status: str = None) -> int:
        """
        Ajoute ou met à jour une gamme.
        
        Logique automatique : Si name est NULL ou vide → status='error' automatiquement.
        Si name existe → status='pending' (ou celui fourni).
        
        Args:
            url: URL unique de la gamme
            category: Catégorie de la gamme
            name: Nom de la gamme (None si en erreur)
            status: Statut explicite (optionnel, sera déterminé automatiquement si None)
        
        Returns:
            gamme_id: ID de la gamme (nouveau ou existant)
        """
        cursor = self.conn.cursor()
        
        # Déterminer le status automatiquement si name est NULL ou vide
        if not name or not name.strip():
            final_status = 'error'
            final_name = None
        else:
            # Si name existe, utiliser le status fourni ou 'pending' par défaut
            final_status = status if status else 'pending'
            final_name = name.strip()
        
        # Vérifier si la gamme existe déjà
        cursor.execute('SELECT id, status, name, category FROM gammes WHERE url = ?', (url,))
        existing = cursor.fetchone()
        
        if existing:
            gamme_id = existing['id']
            existing_status = existing['status']
            existing_name = existing['name']
            existing_category = existing['category']
            
            # Si la gamme était en erreur et qu'on a maintenant un nom, la mettre à jour
            if existing_status == 'error' and final_name:
                cursor.execute('''
                    UPDATE gammes 
                    SET name = ?, status = ?, category = ?, updated_at = CURRENT_TIMESTAMP
                    WHERE id = ?
                ''', (final_name, 'pending', category, gamme_id))
                self.conn.commit()
                logger.debug(f"Gamme {url} mise à jour (était en erreur, maintenant avec nom)")
                return gamme_id
            
            # Si la gamme existe déjà, mettre à jour si nécessaire (nom, status, ou catégorie)
            if existing_name != final_name or existing_status != final_status or existing_category != category:
                cursor.execute('''
                    UPDATE gammes 
                    SET name = ?, status = ?, category = ?, updated_at = CURRENT_TIMESTAMP
                    WHERE id = ?
                ''', (final_name, final_status, category, gamme_id))
                self.conn.commit()
                logger.debug(f"Gamme {url} mise à jour (catégorie: {existing_category} -> {category})")
            
            return gamme_id
        
        # La gamme n'existe pas, l'ajouter
        try:
            cursor.execute('''
                INSERT INTO gammes (name, url, category, status)
                VALUES (?, ?, ?, ?)
            ''', (final_name, url, category, final_status))
            self.conn.commit()
            gamme_id = cursor.lastrowid
            logger.debug(f"Nouvelle gamme ajoutée: {url} (gamme_id={gamme_id}, status={final_status})")
            return gamme_id
        except sqlite3.IntegrityError as e:
            # Race condition : la gamme a été ajoutée entre temps
            cursor.execute('SELECT id FROM gammes WHERE url = ?', (url,))
            row = cursor.fetchone()
            if row:
                logger.debug(f"Gamme {url} existe déjà (race condition)")
                return row['id']
            raise
    
    def get_gamme_by_url(self, url: str) -> Optional[Dict]:
        """Récupère une gamme par son URL."""
        cursor = self.conn.cursor()
        cursor.execute('SELECT * FROM gammes WHERE url = ?', (url,))
        row = cursor.fetchone()
        return dict(row) if row else None
    
    def get_gamme_by_id(self, gamme_id: int) -> Optional[Dict]:
        """Récupère une gamme par son ID."""
        cursor = self.conn.cursor()
        cursor.execute('SELECT * FROM gammes WHERE id = ?', (gamme_id,))
        row = cursor.fetchone()
        return dict(row) if row else None
    
    def get_gammes_by_status(self, status: Optional[str] = None, category: Optional[str] = None) -> List[Dict]:
        """
        Récupère les gammes filtrées par statut.
        
        Args:
            status: 'pending', 'processing', 'completed', 'error', ou None pour toutes
            category: Filtrer par catégorie (optionnel)
        
        Returns:
            Liste des gammes correspondantes
        """
        cursor = self.conn.cursor()
        query = 'SELECT * FROM gammes WHERE 1=1'
        params = []
        
        if status:
            query += ' AND status = ?'
            params.append(status)
        
        if category:
            query += ' AND category = ?'
            params.append(category)
        
        query += ' ORDER BY updated_at DESC'
        
        cursor.execute(query, params)
        return [dict(row) for row in cursor.fetchall()]
    
    def get_error_gammes(self, category: Optional[str] = None) -> List[Dict]:
        """
        Récupère toutes les gammes en erreur.
        Une gamme est en erreur si status='error' OU name IS NULL.
        
        Args:
            category: Filtrer par catégorie (optionnel)
        
        Returns:
            Liste des gammes en erreur
        """
        cursor = self.conn.cursor()
        query = '''
            SELECT * FROM gammes 
            WHERE status = 'error' OR name IS NULL
        '''
        params = []
        
        if category:
            query += ' AND category = ?'
            params.append(category)
        
        query += ' ORDER BY updated_at DESC'
        
        cursor.execute(query, params)
        return [dict(row) for row in cursor.fetchall()]
    
    def link_gamme_to_product(self, gamme_id: int, product_id: int):
        """Lie un produit à une gamme dans la table gamme_products."""
        cursor = self.conn.cursor()
        try:
            cursor.execute('''
                INSERT OR IGNORE INTO gamme_products (gamme_id, product_id)
                VALUES (?, ?)
            ''', (gamme_id, product_id))
            self.conn.commit()
            logger.debug(f"Produit {product_id} lié à la gamme {gamme_id}")
        except sqlite3.IntegrityError:
            # Le lien existe déjà, c'est OK
            pass
    
    def get_gamme_products(self, gamme_id: int) -> List[int]:
        """Récupère tous les product_ids d'une gamme."""
        cursor = self.conn.cursor()
        cursor.execute('''
            SELECT product_id FROM gamme_products 
            WHERE gamme_id = ?
            ORDER BY created_at
        ''', (gamme_id,))
        return [row['product_id'] for row in cursor.fetchall()]
    
    def update_gamme_status(self, gamme_id: int, status: str):
        """Met à jour le statut d'une gamme."""
        cursor = self.conn.cursor()
        cursor.execute('''
            UPDATE gammes 
            SET status = ?, updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
        ''', (status, gamme_id))
        self.conn.commit()
    
    def update_all_gammes_status(self, category: Optional[str] = None) -> int:
        """
        Met à jour le statut de TOUTES les gammes après traitement.
        Utilise update_gamme_status_if_all_products_processed() pour chaque gamme.
        
        Args:
            category: Filtrer par catégorie (optionnel)
        
        Returns:
            Nombre de gammes mises à jour
        """
        cursor = self.conn.cursor()
        
        if category:
            cursor.execute('SELECT DISTINCT id FROM gammes WHERE category = ?', (category,))
        else:
            cursor.execute('SELECT DISTINCT id FROM gammes')
        
        gamme_ids = [row['id'] for row in cursor.fetchall()]
        
        updated_count = 0
        for gamme_id in gamme_ids:
            if self.update_gamme_status_if_all_products_processed(gamme_id):
                updated_count += 1
        
        return updated_count
    
    def update_gamme_status_if_all_products_processed(self, gamme_id: int) -> bool:
        """
        Vérifie et met à jour le statut d'une gamme si tous ses produits sont traités.
        
        Logique :
        - Nettoie d'abord les entrées orphelines dans gamme_products
        - Si tous les produits de la gamme ont au moins 1 variant completed → gamme 'completed'
        - Si tous les produits sont en erreur → gamme 'error'
        - Si aucune entrée valide et gamme en 'processing' → gamme 'error'
        - Sinon → gamme reste 'pending' ou 'processing'
        
        Args:
            gamme_id: ID de la gamme à vérifier
            
        Returns:
            True si le statut a été mis à jour, False sinon
        """
        cursor = self.conn.cursor()
        
        # Étape 1 : Nettoyer les entrées orphelines dans gamme_products
        # (produits qui ont été supprimés mais dont les entrées gamme_products existent encore)
        cursor.execute('''
            DELETE FROM gamme_products
            WHERE gamme_id = ? 
            AND product_id NOT IN (SELECT id FROM products)
        ''', (gamme_id,))
        orphaned_count = cursor.rowcount
        if orphaned_count > 0:
            self.conn.commit()
            logger.debug(f"Gamme {gamme_id}: {orphaned_count} entrée(s) orpheline(s) nettoyée(s)")
        
        # Étape 2 : Récupérer la catégorie de la gamme
        cursor.execute('SELECT category FROM gammes WHERE id = ?', (gamme_id,))
        gamme_row = cursor.fetchone()
        gamme_category = gamme_row['category'] if gamme_row else None
        
        # Étape 3 : Récupérer tous les produits valides de cette gamme qui appartiennent à la même catégorie
        cursor.execute('''
            SELECT p.id, p.status, p.product_code
            FROM products p
            INNER JOIN gamme_products gp ON p.id = gp.product_id
            WHERE gp.gamme_id = ?
            AND p.category = ?
        ''', (gamme_id, gamme_category))
        
        products = cursor.fetchall()
        
        # Étape 4 : Déterminer le statut actuel de la gamme
        current_status = None
        cursor.execute('SELECT status FROM gammes WHERE id = ?', (gamme_id,))
        row = cursor.fetchone()
        if row:
            current_status = row['status']
        
        # Étape 5 : Si aucun produit valide après nettoyage (pour cette catégorie)
        if not products:
            # Si la gamme était en processing, la marquer comme error
            if current_status == 'processing':
                cursor.execute('''
                    UPDATE gammes 
                    SET status = 'error', updated_at = CURRENT_TIMESTAMP
                    WHERE id = ?
                ''', (gamme_id,))
                self.conn.commit()
                logger.info(f"✓ Gamme {gamme_id} passée à 'error' (aucun produit valide après nettoyage)")
                return True
            # Sinon, ne rien changer
            return False
        
        # Étape 6 : Analyser les produits existants
        total_products = len(products)
        completed_products = 0
        error_products = 0
        
        for product in products:
            product_id = product['id']
            product_status = product['status']
            
            # Vérifier si le produit a au moins un variant completed
            cursor.execute('''
                SELECT COUNT(*) as count
                FROM product_variants
                WHERE product_id = ? AND status = 'completed'
            ''', (product_id,))
            
            completed_variants = cursor.fetchone()['count']
            
            if completed_variants > 0:
                completed_products += 1
            elif product_status == 'error':
                error_products += 1
        
        # Étape 7 : Déterminer le nouveau statut
        new_status = None
        
        if completed_products == total_products:
            new_status = 'completed'
        elif error_products == total_products:
            new_status = 'error'
        # Sinon, garder pending ou processing (ne pas changer si déjà processing)
        else:
            return False
        
        # Étape 8 : Mettre à jour seulement si le statut a changé
        if new_status and new_status != current_status:
            cursor.execute('''
                UPDATE gammes 
                SET status = ?, updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
            ''', (new_status, gamme_id))
            self.conn.commit()
            logger.info(f"✓ Gamme {gamme_id} passée à '{new_status}' ({completed_products}/{total_products} produits avec variants completed)")
            return True
        
        return False
    
    def mark_gamme_error(self, gamme_id: int):
        """Marque une gamme en erreur (met status='error' et name=NULL si nécessaire)."""
        cursor = self.conn.cursor()
        cursor.execute('''
            UPDATE gammes 
            SET status = 'error', name = NULL, updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
        ''', (gamme_id,))
        self.conn.commit()
    
    def increment_gamme_retry(self, gamme_id: int):
        """Incrémente le compteur de retry d'une gamme."""
        cursor = self.conn.cursor()
        cursor.execute('''
            UPDATE gammes 
            SET retry_count = retry_count + 1, updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
        ''', (gamme_id,))
        self.conn.commit()
    
    def get_category_gamme_stats(self, category: str) -> Dict:
        """
        Récupère les statistiques des gammes pour une catégorie.
        
        Returns:
            {
                'completed': 45,
                'pending': 3,
                'error': 2,
                'total': 50
            }
        """
        cursor = self.conn.cursor()
        cursor.execute('''
            SELECT 
                status,
                COUNT(*) as count
            FROM gammes
            WHERE category = ?
            GROUP BY status
        ''', (category,))
        
        stats = {'completed': 0, 'processing': 0, 'pending': 0, 'error': 0, 'total': 0}
        for row in cursor.fetchall():
            status = row['status'] or 'pending'
            count = row['count']
            if status in stats:
                stats[status] = count
            stats['total'] += count
        
        # Compter aussi les gammes avec name IS NULL comme erreur
        cursor.execute('''
            SELECT COUNT(*) as count
            FROM gammes
            WHERE category = ? AND name IS NULL
        ''', (category,))
        null_count = cursor.fetchone()['count']
        if null_count > stats['error']:
            stats['error'] = null_count
        
        return stats
    
    def close(self):
        """Ferme la connexion à la base de données."""
        if self.conn:
            self.conn.close()
            self.conn = None
    
    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
    
    # ========== Méthodes de nettoyage ==========
    
    def delete_all(self) -> int:
        """
        Supprime tous les produits, variants, images et gammes de la base de données.
        
        Returns:
            Nombre de produits supprimés
        """
        cursor = self.conn.cursor()
        
        # Compter les produits avant suppression
        cursor.execute('SELECT COUNT(*) FROM products')
        count = cursor.fetchone()[0]
        
        # Supprimer toutes les tables (CASCADE va supprimer les dépendances)
        cursor.execute('DELETE FROM gammes')
        cursor.execute('DELETE FROM products')
        
        self.conn.commit()
        logger.info(f"Base de données vidée: {count} produits supprimés")
        
        return count
    
    def delete_by_category(self, category: str) -> int:
        """
        Supprime tous les produits d'une catégorie.
        
        Args:
            category: Nom de la catégorie
            
        Returns:
            Nombre de produits supprimés
        """
        cursor = self.conn.cursor()
        
        # Compter les produits avant suppression
        cursor.execute('SELECT COUNT(*) FROM products WHERE category = ?', (category,))
        count = cursor.fetchone()[0]
        
        # Supprimer (CASCADE va supprimer les variants et images)
        cursor.execute('DELETE FROM products WHERE category = ?', (category,))
        self.conn.commit()
        
        logger.info(f"Catégorie '{category}' supprimée: {count} produits")
        
        return count
    
    def delete_by_gamme(self, gamme: str) -> int:
        """
        Supprime tous les produits d'une gamme.
        
        Args:
            gamme: Nom de la gamme
            
        Returns:
            Nombre de produits supprimés
        """
        cursor = self.conn.cursor()
        
        # Compter les produits avant suppression
        # Utiliser LIKE pour matcher même si la gamme est malformée
        cursor.execute('SELECT COUNT(*) FROM products WHERE gamme LIKE ?', (f'%{gamme}%',))
        count = cursor.fetchone()[0]
        
        # Supprimer (CASCADE va supprimer les variants et images)
        cursor.execute('DELETE FROM products WHERE gamme LIKE ?', (f'%{gamme}%',))
        self.conn.commit()
        
        logger.info(f"Gamme '{gamme}' supprimée: {count} produits")
        
        return count
    
    def delete_by_title(self, title: str) -> int:
        """
        Supprime les produits dont le titre contient la chaîne spécifiée (insensible à la casse).
        
        Args:
            title: Chaîne à rechercher dans le titre
            
        Returns:
            Nombre de produits supprimés
        """
        cursor = self.conn.cursor()
        
        # Compter les produits avant suppression
        cursor.execute('SELECT COUNT(*) FROM products WHERE title LIKE ? COLLATE NOCASE', (f'%{title}%',))
        count = cursor.fetchone()[0]
        
        # Supprimer (CASCADE va supprimer les variants et images)
        cursor.execute('DELETE FROM products WHERE title LIKE ? COLLATE NOCASE', (f'%{title}%',))
        self.conn.commit()
        
        logger.info(f"Produits avec titre contenant '{title}' supprimés: {count} produits")
        
        return count
    
    def delete_by_sku(self, sku: str) -> int:
        """
        Supprime les variants avec le SKU spécifié et leurs produits si plus aucun variant.
        
        Args:
            sku: SKU exact à supprimer
            
        Returns:
            Nombre de variants supprimés
        """
        cursor = self.conn.cursor()
        
        # Trouver les variants avec ce SKU
        cursor.execute('SELECT id, product_id FROM product_variants WHERE sku = ?', (sku,))
        variants = cursor.fetchall()
        
        if not variants:
            logger.info(f"Aucun variant trouvé avec le SKU '{sku}'")
            return 0
        
        # Supprimer les variants
        cursor.execute('DELETE FROM product_variants WHERE sku = ?', (sku,))
        count = len(variants)
        
        # Pour chaque produit, vérifier s'il a encore des variants
        product_ids = set(v['product_id'] for v in variants)
        for product_id in product_ids:
            cursor.execute('SELECT COUNT(*) FROM product_variants WHERE product_id = ?', (product_id,))
            remaining = cursor.fetchone()[0]
            
            # Si plus de variants, supprimer le produit
            if remaining == 0:
                cursor.execute('DELETE FROM products WHERE id = ?', (product_id,))
        
        self.conn.commit()
        logger.info(f"Variants avec SKU '{sku}' supprimés: {count} variants")
        
        return count
    
    def count_products_by_category(self, category: str) -> int:
        """
        Compte les produits dans une catégorie.
        
        Args:
            category: Nom de la catégorie
            
        Returns:
            Nombre de produits
        """
        cursor = self.conn.cursor()
        cursor.execute('SELECT COUNT(*) FROM products WHERE category = ?', (category,))
        return cursor.fetchone()[0]
    
    def count_products_by_gamme(self, gamme: str) -> int:
        """
        Compte les produits dans une gamme.
        
        Args:
            gamme: Nom de la gamme
            
        Returns:
            Nombre de produits
        """
        cursor = self.conn.cursor()
        cursor.execute('SELECT COUNT(*) FROM products WHERE gamme LIKE ?', (f'%{gamme}%',))
        return cursor.fetchone()[0]
    
    def count_products_by_title(self, title: str) -> int:
        """
        Compte les produits dont le titre contient la chaîne spécifiée.
        
        Args:
            title: Chaîne à rechercher dans le titre
            
        Returns:
            Nombre de produits
        """
        cursor = self.conn.cursor()
        cursor.execute('SELECT COUNT(*) FROM products WHERE title LIKE ? COLLATE NOCASE', (f'%{title}%',))
        return cursor.fetchone()[0]
    
    def count_variants_by_sku(self, sku: str) -> int:
        """
        Compte les variants avec le SKU spécifié.
        
        Args:
            sku: SKU exact à rechercher
            
        Returns:
            Nombre de variants
        """
        cursor = self.conn.cursor()
        cursor.execute('SELECT COUNT(*) FROM product_variants WHERE sku = ?', (sku,))
        return cursor.fetchone()[0]
    
    def delete_by_product_ids(self, product_ids: list) -> int:
        """
        Supprime les produits spécifiés par leurs IDs.
        
        Args:
            product_ids: Liste des IDs de produits à supprimer
            
        Returns:
            Nombre de produits supprimés
        """
        if not product_ids:
            return 0
        
        cursor = self.conn.cursor()
        
        # Créer les placeholders pour la requête
        placeholders = ','.join(['?'] * len(product_ids))
        
        # Supprimer les produits (CASCADE va supprimer les variants et images)
        cursor.execute(f'DELETE FROM products WHERE id IN ({placeholders})', product_ids)
        count = cursor.rowcount
        
        self.conn.commit()
        logger.info(f"Produits sélectionnés supprimés: {count} produits")
        
        return count

