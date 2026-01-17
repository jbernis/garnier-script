"""
Module de gestion de la base de données SQLite pour le scraper Artiga.
"""

import sqlite3
import logging
from typing import List, Dict, Optional
from datetime import datetime
import os

logger = logging.getLogger(__name__)


class ArtigaDB:
    """Gestionnaire de base de données pour les produits Artiga."""
    
    def __init__(self, db_path: str = "artiga_products.db"):
        """Initialise la connexion à la base de données."""
        self.db_path = db_path
        self.conn = None
        self._init_db()
    
    def _init_db(self):
        """Initialise les tables de la base de données."""
        self.conn = sqlite3.connect(self.db_path)
        self.conn.row_factory = sqlite3.Row  # Permet d'accéder aux colonnes par nom
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
                subcategory TEXT,
                base_url TEXT,
                status TEXT DEFAULT 'pending',
                error_message TEXT,
                is_new INTEGER DEFAULT 0,
                retry_count INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
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
        
        # Table des images
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
        
        # Index pour améliorer les performances
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_variant_status ON product_variants(status)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_variant_code_vl ON product_variants(code_vl)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_variant_product ON product_variants(product_id)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_product_code ON products(product_code)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_product_handle ON products(handle)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_product_category ON products(category)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_product_subcategory ON products(subcategory)')
        
        self.conn.commit()
        logger.info(f"Base de données Artiga initialisée: {self.db_path}")
    
    def add_product(self, product_code: str, handle: str, title: str = None, 
                    description: str = None, vendor: str = None, product_type: str = None,
                    tags: str = None, category: str = None, subcategory: str = None,
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
            
            # Toujours mettre à jour la subcategory si elle est fournie
            if subcategory:
                cursor.execute('''
                    UPDATE products 
                    SET subcategory = ?, updated_at = CURRENT_TIMESTAMP
                    WHERE id = ?
                ''', (subcategory, existing_id))
                self.conn.commit()
                logger.debug(f"Sous-catégorie mise à jour pour le produit {product_code}: '{subcategory}'")
            
            # Ne mettre à jour complètement que si le status existant est 'error'
            if existing_status == 'error':
                cursor.execute('''
                    UPDATE products 
                    SET handle = ?, title = ?, description = ?, vendor = ?, product_type = ?, 
                        tags = ?, category = ?, subcategory = ?, base_url = ?, 
                        status = ?, error_message = ?, is_new = ?, updated_at = CURRENT_TIMESTAMP
                    WHERE id = ?
                ''', (handle, title, description, vendor, product_type, tags, category, subcategory, 
                      base_url, status, error_message, 1 if is_new else 0, existing_id))
                self.conn.commit()
                logger.debug(f"Produit {product_code} mis à jour complètement (était en erreur)")
                return existing_id
            else:
                # Le produit existe mais n'est pas en erreur
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
                    logger.warning(f"Produit {product_code} passé en erreur (titre vide)")
                    return existing_id
                
                logger.debug(f"Produit {product_code} existe déjà avec status={existing_status}")
                return existing_id
        
        # Le produit n'existe pas, l'ajouter
        try:
            cursor.execute('''
                INSERT INTO products 
                (product_code, handle, title, description, vendor, product_type, tags, category, subcategory, base_url, status, error_message, is_new)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (product_code, handle, title, description, vendor, product_type, tags, category, subcategory, base_url, status, error_message, 1 if is_new else 0))
            self.conn.commit()
            product_id = cursor.lastrowid
            logger.debug(f"Nouveau produit {product_code} ajouté (product_id={product_id})")
            return product_id
        except sqlite3.IntegrityError as e:
            cursor.execute('SELECT id, status FROM products WHERE product_code = ?', (product_code,))
            row = cursor.fetchone()
            if row:
                logger.warning(f"Produit {product_code} existe déjà (race condition)")
                return row['id']
            raise
    
    def update_product_status(self, product_id: int, status: str = None, error_message: str = None):
        """Met à jour le status et error_message d'un produit."""
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
            updates.append('error_message = NULL')
        
        updates.append('updated_at = CURRENT_TIMESTAMP')
        params.append(product_id)
        
        if updates:
            query = f'UPDATE products SET {", ".join(updates)} WHERE id = ?'
            cursor.execute(query, params)
            self.conn.commit()
    
    def update_product_status_if_all_variants_processed(self, product_id: int) -> bool:
        """Vérifie et met à jour le statut d'un produit si tous ses variants sont traités."""
        cursor = self.conn.cursor()
        
        cursor.execute('''
            SELECT p.id, p.status, p.product_code,
                   COUNT(pv.id) as total_variants,
                   SUM(CASE WHEN pv.status = 'completed' THEN 1 ELSE 0 END) as completed_variants,
                   SUM(CASE WHEN pv.status = 'error' THEN 1 ELSE 0 END) as error_variants
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
        
        if total_variants == 0:
            return False
        
        new_status = None
        
        if completed_variants == total_variants:
            new_status = 'completed'
        elif error_variants == total_variants:
            new_status = 'error'
        else:
            new_status = 'pending'
        
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
        """Met à jour le status de TOUS les produits après traitement des variants."""
        cursor = self.conn.cursor()
        
        cursor.execute('''
            SELECT p.id, p.status,
                   COUNT(pv.id) as total_variants,
                   SUM(CASE WHEN pv.status = 'completed' THEN 1 ELSE 0 END) as completed_variants,
                   SUM(CASE WHEN pv.status = 'error' THEN 1 ELSE 0 END) as error_variants
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
            
            if total_variants == 0:
                continue
            
            new_status = None
            
            if completed_variants == total_variants:
                new_status = 'completed'
            elif error_variants == total_variants:
                new_status = 'error'
            else:
                new_status = 'pending'
            
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
        
        Returns:
            Tuple (variant_id, is_new)
        """
        cursor = self.conn.cursor()
        
        cursor.execute('SELECT id, product_id FROM product_variants WHERE code_vl = ?', (code_vl,))
        existing = cursor.fetchone()
        
        if existing:
            existing_id = existing['id']
            existing_product_id = existing['product_id']
            
            if existing_product_id != product_id:
                if raise_on_duplicate:
                    error_msg = f"Le code_vl '{code_vl}' existe déjà avec un produit différent"
                    logger.error(error_msg)
                    raise sqlite3.IntegrityError(error_msg)
                else:
                    logger.warning(f"Variant {code_vl} existe déjà avec un autre produit")
                    return (existing_id, False)
            
            if raise_on_duplicate:
                error_msg = f"Le variant '{code_vl}' existe déjà"
                logger.error(error_msg)
                raise sqlite3.IntegrityError(error_msg)
            else:
                logger.debug(f"Variant {code_vl} existe déjà")
                return (existing_id, False)
        
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
            cursor.execute('SELECT id FROM product_variants WHERE code_vl = ?', (code_vl,))
            row = cursor.fetchone()
            if row:
                logger.debug(f"Variant {code_vl} existe déjà (race condition)")
                return (row['id'], False)
            else:
                raise
    
    def update_variant_collect(self, variant_id: int, url: str = None, size_text: str = None):
        """Met à jour les champs de base d'un variant lors de la collecte."""
        cursor = self.conn.cursor()
        updates = []
        params = []
        
        if url is not None:
            updates.append('url = ?')
            params.append(url)
        if size_text is not None:
            updates.append('size_text = ?')
            params.append(size_text)
        
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
        """Met à jour les données d'un variant après traitement."""
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
        ''', (error_message[:500], variant_id))
        self.conn.commit()
    
    def get_pending_variants(self, limit: Optional[int] = None, category: Optional[str] = None, subcategory: Optional[str] = None) -> List[Dict]:
        """Récupère les variants en attente de traitement."""
        cursor = self.conn.cursor()
        query = '''
            SELECT pv.id, pv.code_vl, pv.url, pv.size_text, p.product_code, p.handle
            FROM product_variants pv
            JOIN products p ON pv.product_id = p.id
            WHERE pv.status = 'pending'
        '''
        params = []
        
        if category:
            query += ' AND p.category = ?'
            params.append(category)
        
        if subcategory:
            query += ' AND p.subcategory = ?'
            params.append(subcategory)
        
        query += ' ORDER BY pv.id'
        
        if limit:
            query += f' LIMIT {limit}'
        
        cursor.execute(query, params)
        return [dict(row) for row in cursor.fetchall()]
    
    def get_variant_by_code_vl(self, code_vl: str) -> Optional[Dict]:
        """Récupère un variant par son code_vl."""
        cursor = self.conn.cursor()
        cursor.execute('''
            SELECT pv.*, p.product_code, p.handle, p.title, p.category, p.subcategory
            FROM product_variants pv
            JOIN products p ON pv.product_id = p.id
            WHERE pv.code_vl = ?
        ''', (code_vl,))
        row = cursor.fetchone()
        return dict(row) if row else None
    
    def get_error_variants(self, limit: Optional[int] = None, category: Optional[str] = None, subcategory: Optional[str] = None) -> List[Dict]:
        """Récupère les variants en erreur."""
        cursor = self.conn.cursor()
        query = '''
            SELECT pv.id, pv.code_vl, pv.url, pv.error_message, p.product_code
            FROM product_variants pv
            JOIN products p ON pv.product_id = p.id
            WHERE pv.status = 'error'
        '''
        params = []
        
        if category:
            query += ' AND p.category = ?'
            params.append(category)
        
        if subcategory:
            query += ' AND p.subcategory = ?'
            params.append(subcategory)
        
        query += ' ORDER BY pv.updated_at DESC'
        
        if limit:
            query += f' LIMIT {limit}'
        
        cursor.execute(query, params)
        return [dict(row) for row in cursor.fetchall()]
    
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
    
    def get_completed_products(self, categories: List[str] = None, subcategory: str = None) -> List[Dict]:
        """Récupère tous les produits avec au moins un variant complété."""
        cursor = self.conn.cursor()
        
        conditions = ["pv.status = 'completed'"]
        params = []
        
        if categories and len(categories) > 0:
            placeholders = ','.join(['?'] * len(categories))
            conditions.append(f"p.category IN ({placeholders})")
            params.extend(categories)
        
        if subcategory:
            conditions.append("p.subcategory = ?")
            params.append(subcategory)
        
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
        """Récupère la liste des catégories disponibles."""
        cursor = self.conn.cursor()
        cursor.execute('''
            SELECT DISTINCT category
            FROM products
            WHERE category IS NOT NULL AND category != ''
            ORDER BY category
        ''')
        return [row['category'] for row in cursor.fetchall()]
    
    def get_available_subcategories(self, category: str = None) -> List[str]:
        """Récupère la liste des sous-catégories disponibles."""
        cursor = self.conn.cursor()
        if category:
            cursor.execute('''
                SELECT DISTINCT subcategory
                FROM products
                WHERE subcategory IS NOT NULL AND subcategory != ''
                AND category = ?
                ORDER BY subcategory
            ''', (category,))
        else:
            cursor.execute('''
                SELECT DISTINCT subcategory
                FROM products
                WHERE subcategory IS NOT NULL AND subcategory != ''
                ORDER BY subcategory
            ''')
        return [row['subcategory'] for row in cursor.fetchall()]
    
    def get_category_stats(self, category: str) -> Dict:
        """
        Récupère les statistiques détaillées d'une sous-catégorie.
        Pour Artiga, 'category' correspond en réalité à une sous-catégorie.
        
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
        
        # Stats des produits (utiliser subcategory au lieu de category)
        cursor.execute('''
            SELECT 
                status,
                COUNT(*) as count
            FROM products
            WHERE subcategory = ?
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
            WHERE p.subcategory = ?
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
        
        # Produits en erreur avec retry_count < 3
        cursor.execute('''
            SELECT COUNT(*) FROM products 
            WHERE status = 'error' AND retry_count < 3
        ''')
        stats['retriable_errors'] = cursor.fetchone()[0]
        
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
