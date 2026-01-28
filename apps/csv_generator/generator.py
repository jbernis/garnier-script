"""
Module de génération CSV avec gestion de csv_generator_config.json.
"""

import json
import shutil
import logging
from pathlib import Path
from typing import List, Optional
import os
import sys

logger = logging.getLogger(__name__)

# Ajouter le répertoire parent au path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from csv_config import CONFIG_FILE, SHOPIFY_ALL_COLUMNS
from apps.csv_generator.csv_generator_config import get_csv_generator_config


class CSVGenerator:
    """Générateur CSV avec configuration dédiée csv_generator_config.json."""
    
    def __init__(self):
        """Initialise le générateur CSV."""
        self.generator_config = get_csv_generator_config()
        # Fichier temporaire pour la génération (passé aux scripts de génération)
        self.temp_config_file = Path(CONFIG_FILE).parent / 'csv_config_temp.json'
    
    def generate_csv(
        self,
        supplier: str,
        categories: Optional[List[str]],
        subcategories: Optional[List[str]],
        selected_fields: List[str],
        handle_source: str,
        vendor: str,
        location: Optional[str] = None,
        gamme: Optional[str] = None,
        output_file: Optional[str] = None,
        max_images: Optional[int] = None,
        exclude_errors: bool = False
    ) -> str:
        """
        Génère un CSV Shopify avec les champs sélectionnés.
        
        Args:
            supplier: Nom du fournisseur (ex: 'garnier')
            categories: Liste de catégories à inclure (None = toutes)
            subcategories: Liste de sous-catégories à inclure (optionnel, pour Artiga/Cristel)
            selected_fields: Liste des champs CSV à inclure
            handle_source: Source du Handle ('barcode', 'sku', 'title', 'custom')
            vendor: Nom du vendor
            location: Emplacement (location) pour le stock
            gamme: Nom de la gamme à filtrer (optionnel, pour Garnier)
            output_file: Chemin du fichier CSV de sortie (None = auto)
            max_images: Nombre maximum d'images par produit (None = toutes)
            
        Returns:
            Chemin du CSV généré
            
        Raises:
            Exception: Si la génération échoue
        """
        try:
            # Créer un fichier de configuration temporaire pour la génération
            self._create_temp_config(supplier, selected_fields, handle_source, vendor, location)
            
            # Appeler la fonction de génération
            if supplier == 'garnier':
                # Importer le module de génération
                import importlib.util
                # Remonter jusqu'à la racine du projet (apps/csv_generator -> apps -> racine)
                project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
                generate_path = os.path.join(project_root, "garnier", "scraper-generate-csv.py")
                generate_spec = importlib.util.spec_from_file_location("scraper_garnier_generate_csv", generate_path)
                generate_module = importlib.util.module_from_spec(generate_spec)
                generate_spec.loader.exec_module(generate_module)
                generate_csv_from_db = generate_module.generate_csv_from_db
                
                from utils.app_config import get_garnier_db_path
                
                db_path = get_garnier_db_path()
                
                # Debug: afficher les paramètres avant l'appel
                logger.info(f"Paramètres pour generate_csv_from_db:")
                logger.info(f"  - categories: {categories}")
                logger.info(f"  - gamme: {gamme}")
                logger.info(f"  - max_images: {max_images}")
                
                # Ne PAS générer le nom du fichier ici, laisser generate_csv_from_db() le faire
                # avec sa détection automatique des catégories/gammes
                # output_file reste None pour activer la génération automatique du nom
                
                # Forcer le rechargement de la configuration avant la génération
                from csv_config import get_csv_config
                csv_config_manager = get_csv_config()
                csv_config_manager.reload_config()
                
                logger.info("Configuration rechargée, vérification des colonnes:")
                loaded_columns = csv_config_manager.get_columns(supplier)
                logger.info(f"  Colonnes chargées: {len(loaded_columns)}")
                logger.info(f"  Premières colonnes: {loaded_columns[:5]}")
                
                # Appeler la fonction de génération qui retourne le chemin du fichier
                # Si gamme est une liste, passer comme gammes, sinon comme gamme (pour compatibilité)
                if isinstance(gamme, list) and len(gamme) > 0:
                    output_file = generate_csv_from_db(
                        output_file=output_file,
                        output_db=db_path,
                        supplier=supplier,
                        categories=categories,
                        gammes=gamme,
                        max_images=max_images,
                        exclude_errors=exclude_errors
                    )
                else:
                    output_file = generate_csv_from_db(
                        output_file=output_file,
                        output_db=db_path,
                        supplier=supplier,
                        categories=categories,
                        gamme=gamme,
                        max_images=max_images,
                        exclude_errors=exclude_errors
                    )
                
                # Vérifier que le fichier existe
                if not output_file or not os.path.exists(output_file):
                    raise ValueError(f"Le fichier CSV généré n'existe pas: {output_file}")
                
                return output_file
            elif supplier == 'artiga':
                # Importer le module de génération
                import importlib.util
                # Remonter jusqu'à la racine du projet (apps/csv_generator -> apps -> racine)
                project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
                generate_path = os.path.join(project_root, "artiga", "scraper-generate-csv.py")
                generate_spec = importlib.util.spec_from_file_location("scraper_artiga_generate_csv", generate_path)
                generate_module = importlib.util.module_from_spec(generate_spec)
                generate_spec.loader.exec_module(generate_module)
                generate_csv_from_db = generate_module.generate_csv_from_db
                
                from utils.app_config import get_artiga_db_path
                
                db_path = get_artiga_db_path()
                
                # Debug: afficher les paramètres avant l'appel
                logger.info(f"[ARTIGA CSV] Paramètres avant appel generate_csv_from_db:")
                logger.info(f"  - categories: {categories}")
                logger.info(f"  - subcategories: {subcategories}")
                logger.info(f"  - max_images: {max_images}")
                logger.info(f"  - exclude_errors: {exclude_errors}")
                
                # Laisser scraper-generate-csv.py construire le nom du fichier
                # Il utilisera subcategory pour le nom si fourni
                print(f"[ARTIGA CSV] Appel avec subcategories: {subcategories}, categories: {categories}")
                
                # Forcer le rechargement de la configuration avant la génération
                from csv_config import get_csv_config
                csv_config_manager = get_csv_config()
                csv_config_manager.reload_config()
                
                logger.info("Configuration rechargée, vérification des colonnes:")
                loaded_columns = csv_config_manager.get_columns(supplier)
                logger.info(f"  Colonnes chargées: {len(loaded_columns)}")
                logger.info(f"  Premières colonnes: {loaded_columns[:5]}")
                
                # Appeler la fonction de génération avec subcategories
                # Pour Artiga, les sous-catégories sont stockées dans le champ "subcategory"
                # Passer toutes les sous-catégories sélectionnées
                # NE PAS passer output_file pour que le script génère le nom avec subcategories
                output_file = generate_csv_from_db(
                    output_file=None,  # Laisser le script générer le nom
                    output_db=db_path,
                    supplier=supplier,
                    categories=categories,
                    subcategory=subcategories[0] if subcategories and len(subcategories) == 1 else None,
                    subcategories=subcategories if subcategories and len(subcategories) > 1 else None,
                    max_images=max_images,
                    exclude_errors=exclude_errors
                )
                
                # Vérifier que le fichier existe
                if not output_file or not os.path.exists(output_file):
                    raise ValueError(f"Le fichier CSV généré n'existe pas: {output_file}")
                
                return output_file
            elif supplier == 'cristel':
                # Importer le module de génération
                import importlib.util
                # Remonter jusqu'à la racine du projet (apps/csv_generator -> apps -> racine)
                project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
                generate_path = os.path.join(project_root, "cristel", "scraper-generate-csv.py")
                generate_spec = importlib.util.spec_from_file_location("scraper_cristel_generate_csv", generate_path)
                generate_module = importlib.util.module_from_spec(generate_spec)
                generate_spec.loader.exec_module(generate_module)
                generate_csv_from_db = generate_module.generate_csv_from_db
                
                from utils.app_config import get_cristel_db_path
                
                db_path = get_cristel_db_path()
                
                # Laisser scraper-generate-csv.py construire le nom du fichier
                # Il utilisera subcategory pour le nom si fourni
                print(f"[CRISTEL CSV] Appel avec subcategories: {subcategories}, categories: {categories}")
                
                # Forcer le rechargement de la configuration avant la génération
                from csv_config import get_csv_config
                csv_config_manager = get_csv_config()
                csv_config_manager.reload_config()
                
                logger.info("Configuration rechargée, vérification des colonnes:")
                loaded_columns = csv_config_manager.get_columns(supplier)
                logger.info(f"  Colonnes chargées: {len(loaded_columns)}")
                logger.info(f"  Premières colonnes: {loaded_columns[:5]}")
                
                # Appeler la fonction de génération avec subcategories
                # Pour Cristel, les sous-catégories sont stockées dans le champ "subcategory"
                # Passer toutes les sous-catégories sélectionnées
                # NE PAS passer output_file pour que le script génère le nom avec subcategories
                output_file = generate_csv_from_db(
                    output_file=None,  # Laisser le script générer le nom
                    output_db=db_path,
                    supplier=supplier,
                    categories=categories,
                    subcategory=subcategories[0] if subcategories and len(subcategories) == 1 else None,
                    subcategories=subcategories if subcategories and len(subcategories) > 1 else None,
                    max_images=max_images
                )
                
                # Vérifier que le fichier existe
                if not output_file or not os.path.exists(output_file):
                    raise ValueError(f"Le fichier CSV généré n'existe pas: {output_file}")
                
                return output_file
            else:
                raise ValueError(f"Fournisseur '{supplier}' non supporté pour l'instant")
        
        finally:
            # Nettoyer le fichier de configuration temporaire
            self._cleanup_temp_config()
    
    def _create_temp_config(self, supplier: str, selected_fields: List[str], 
                           handle_source: str, vendor: str, location: Optional[str] = None):
        """Crée un fichier de configuration temporaire pour la génération."""
        try:
            # Charger la configuration de base depuis csv_config.json
            config_file = Path(CONFIG_FILE)
            if config_file.exists():
                with open(config_file, 'r', encoding='utf-8') as f:
                    config = json.load(f)
            else:
                config = {}
            
            # S'assurer que le fournisseur existe dans la config
            if supplier not in config:
                config[supplier] = {}
            
            # Mettre à jour les colonnes sélectionnées
            config[supplier]['columns'] = selected_fields.copy()
            
            # Mettre à jour handle_source, vendor et location
            config[supplier]['handle_source'] = handle_source
            config[supplier]['vendor'] = vendor
            config[supplier]['location'] = location if location is not None else f"Dropshipping {supplier.capitalize()}"
            
            # Sauvegarder la configuration temporaire
            with open(self.temp_config_file, 'w', encoding='utf-8') as f:
                json.dump(config, f, indent=2, ensure_ascii=False)
            
            # Remplacer temporairement csv_config.json par le fichier temporaire
            config_file_backup = Path(str(config_file) + ".backup_gen")
            if config_file.exists():
                shutil.copy2(config_file, config_file_backup)
            shutil.copy2(self.temp_config_file, config_file)
            
            logger.info(f"Configuration temporaire créée pour {supplier}:")
            logger.info(f"  - Champs sélectionnés: {len(selected_fields)}")
            logger.info(f"  - Handle source: {handle_source}")
            logger.info(f"  - Vendor: {vendor}")
            logger.info(f"  - Location: {location or f'Dropshipping {supplier.capitalize()}'}")
            
        except Exception as e:
            logger.error(f"Erreur lors de la création de la configuration temporaire: {e}")
            raise
    
    def _cleanup_temp_config(self):
        """Nettoie le fichier de configuration temporaire et restaure l'original."""
        try:
            config_file = Path(CONFIG_FILE)
            config_file_backup = Path(str(config_file) + ".backup_gen")
            
            # Restaurer l'original
            if config_file_backup.exists():
                shutil.copy2(config_file_backup, config_file)
                config_file_backup.unlink()
            
            # Supprimer le fichier temporaire
            if self.temp_config_file.exists():
                self.temp_config_file.unlink()
            
            logger.debug("Configuration temporaire nettoyée")
        except Exception as e:
            logger.error(f"Erreur lors du nettoyage de la configuration temporaire: {e}")
            # Ne pas lever d'exception pour ne pas masquer l'erreur originale
    
    def get_available_suppliers(self) -> List[str]:
        """
        Retourne la liste des fournisseurs disponibles (qui ont une base de données).
        
        Returns:
            Liste des noms de fournisseurs disponibles
        """
        suppliers = []
        
        # Vérifier Garnier
        try:
            from utils.app_config import get_garnier_db_path
            db_path = get_garnier_db_path()
            if Path(db_path).exists():
                suppliers.append('garnier')
        except Exception:
            pass
        
        # Vérifier Cristel
        try:
            from utils.app_config import get_cristel_db_path
            db_path = get_cristel_db_path()
            if Path(db_path).exists():
                suppliers.append('cristel')
        except Exception:
            pass
        
        # Vérifier Artiga
        try:
            from utils.app_config import get_artiga_db_path
            db_path = get_artiga_db_path()
            if Path(db_path).exists():
                suppliers.append('artiga')
        except Exception:
            pass
        
        return suppliers
    
    def get_categories(self, supplier: str) -> List[str]:
        """
        Récupère les catégories disponibles pour un fournisseur.
        
        Args:
            supplier: Nom du fournisseur
            
        Returns:
            Liste des catégories disponibles
        """
        if supplier == 'garnier':
            try:
                from utils.garnier_db import GarnierDB
                from utils.app_config import get_garnier_db_path
                
                db = GarnierDB(get_garnier_db_path())
                categories = db.get_available_categories()
                db.close()
                return categories
            except Exception as e:
                logger.error(f"Erreur lors de la récupération des catégories Garnier: {e}")
                return []
        elif supplier == 'artiga':
            try:
                from utils.artiga_db import ArtigaDB
                from utils.app_config import get_artiga_db_path
                
                db = ArtigaDB(get_artiga_db_path())
                categories = db.get_available_categories()
                db.close()
                return categories
            except Exception as e:
                logger.error(f"Erreur lors de la récupération des catégories Artiga: {e}")
                return []
        elif supplier == 'cristel':
            try:
                from utils.cristel_db import CristelDB
                from utils.app_config import get_cristel_db_path
                
                db = CristelDB(get_cristel_db_path())
                categories = db.get_available_categories()
                db.close()
                return categories
            except Exception as e:
                logger.error(f"Erreur lors de la récupération des catégories Cristel: {e}")
                return []
        else:
            return []
    
    def get_subcategories(self, supplier: str, category: Optional[str] = None) -> List[str]:
        """
        Récupère les sous-catégories disponibles pour un fournisseur.
        
        Args:
            supplier: Nom du fournisseur
            category: Catégorie pour laquelle récupérer les sous-catégories (optionnel)
            
        Returns:
            Liste des sous-catégories disponibles
        """
        if supplier == 'artiga':
            try:
                from utils.artiga_db import ArtigaDB
                from utils.app_config import get_artiga_db_path
                
                db = ArtigaDB(get_artiga_db_path())
                subcategories = db.get_available_subcategories(category)
                db.close()
                return subcategories
            except Exception as e:
                logger.error(f"Erreur lors de la récupération des sous-catégories Artiga: {e}")
                return []
        elif supplier == 'cristel':
            try:
                from utils.cristel_db import CristelDB
                from utils.app_config import get_cristel_db_path
                
                db = CristelDB(get_cristel_db_path())
                subcategories = db.get_available_subcategories(category)
                db.close()
                return subcategories
            except Exception as e:
                logger.error(f"Erreur lors de la récupération des sous-catégories Cristel: {e}")
                return []
        else:
            # Garnier n'a pas de sous-catégories
            return []
    
    def get_gammes(self, supplier: str, category: str = None) -> List[str]:
        """
        Récupère les gammes disponibles pour un fournisseur.
        
        Args:
            supplier: Nom du fournisseur
            category: Filtrer par catégorie (optionnel, pour Garnier uniquement)
            
        Returns:
            Liste des gammes disponibles
        """
        if supplier == 'garnier':
            try:
                from utils.garnier_db import GarnierDB
                from utils.app_config import get_garnier_db_path
                
                db = GarnierDB(get_garnier_db_path())
                gammes = db.get_available_gammes(category=category)
                db.close()
                return gammes
            except Exception as e:
                logger.error(f"Erreur lors de la récupération des gammes Garnier: {e}")
                return []
        else:
            # TODO: Ajouter d'autres fournisseurs
            return []
    
    def get_current_config(self, supplier: str) -> dict:
        """
        Récupère la configuration actuelle pour un fournisseur depuis csv_generator_config.
        
        Args:
            supplier: Nom du fournisseur
            
        Returns:
            Dictionnaire avec 'columns', 'handle_source', 'vendor', 'location', 'categories', 'subcategories'
        """
        try:
            # Utiliser la configuration du générateur
            columns = self.generator_config.get_columns(supplier)
            handle_source = self.generator_config.get_handle_source(supplier)
            vendor = self.generator_config.get_vendor(supplier)
            location = self.generator_config.get_location(supplier)
            categories = self.generator_config.get_categories(supplier)
            subcategories = self.generator_config.get_subcategories(supplier)
            
            return {
                'columns': columns,
                'handle_source': handle_source,
                'vendor': vendor,
                'location': location,
                'categories': categories,
                'subcategories': subcategories
            }
        except Exception as e:
            logger.error(f"Erreur lors de la récupération de la configuration: {e}")
            return {
                'columns': SHOPIFY_ALL_COLUMNS.copy(),
                'handle_source': 'barcode',
                'vendor': supplier.capitalize(),
                'location': f"Dropshipping {supplier.capitalize()}",
                'categories': None,
                'subcategories': None
            }
