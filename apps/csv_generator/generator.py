"""
Module de génération CSV avec gestion de csv_config.json.
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


class CSVGenerator:
    """Générateur CSV avec gestion temporaire de csv_config.json."""
    
    def __init__(self):
        """Initialise le générateur CSV."""
        self.config_file = Path(CONFIG_FILE)
        self.backup_file = Path(str(CONFIG_FILE) + ".backup")
    
    def generate_csv(
        self,
        supplier: str,
        categories: Optional[List[str]],
        selected_fields: List[str],
        handle_source: str,
        vendor: str,
        gamme: Optional[str] = None,
        output_file: Optional[str] = None
    ) -> str:
        """
        Génère un CSV Shopify avec les champs sélectionnés.
        
        Args:
            supplier: Nom du fournisseur (ex: 'garnier')
            categories: Liste de catégories à inclure (None = toutes)
            selected_fields: Liste des champs CSV à inclure
            handle_source: Source du Handle ('barcode', 'sku', 'title', 'custom')
            vendor: Nom du vendor
            gamme: Nom de la gamme à filtrer (optionnel, pour Garnier)
            output_file: Chemin du fichier CSV de sortie (None = auto)
            
        Returns:
            Chemin du CSV généré
            
        Raises:
            Exception: Si la génération échoue
        """
        # Sauvegarder la configuration actuelle
        self._backup_config()
        
        try:
            # Modifier csv_config.json temporairement
            self._modify_config(supplier, selected_fields, handle_source, vendor)
            
            # Appeler la fonction de génération
            if supplier == 'garnier':
                # Importer le module de génération
                import importlib.util
                generate_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "scraper-garnier-generate-csv.py")
                generate_spec = importlib.util.spec_from_file_location("scraper_garnier_generate_csv", generate_path)
                generate_module = importlib.util.module_from_spec(generate_spec)
                generate_spec.loader.exec_module(generate_module)
                generate_csv_from_db = generate_module.generate_csv_from_db
                
                from utils.app_config import get_garnier_db_path
                
                db_path = get_garnier_db_path()
                
                # Si output_file n'est pas fourni, générer un nom de fichier
                if not output_file:
                    from datetime import datetime
                    from garnier.scraper_garnier_module import slugify
                    # Importer la fonction de nettoyage pour les gammes
                    from garnier.garnier_functions import clean_gamme_name
                    
                    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                    output_dir = os.getenv("GARNIER_OUTPUT_DIR", "outputs/garnier")
                    
                    # Construire le nom du fichier
                    name_parts = []
                    if gamme:
                        # Nettoyer le nom de la gamme avant de créer le slug
                        cleaned_gamme = clean_gamme_name(gamme)
                        if cleaned_gamme:
                            name_parts.append(slugify(cleaned_gamme))
                    if categories:
                        category_slugs = [slugify(cat) for cat in categories]
                        name_parts.extend(category_slugs)
                    
                    if name_parts:
                        name_str = '_'.join(name_parts)
                        output_file = os.path.join(output_dir, f"shopify_import_garnier_{name_str}_{timestamp}.csv")
                    else:
                        output_file = os.path.join(output_dir, f"shopify_import_garnier_{timestamp}.csv")
                
                # Forcer le rechargement de la configuration avant la génération
                from csv_config import get_csv_config
                csv_config_manager = get_csv_config()
                csv_config_manager.reload_config()
                
                logger.info("Configuration rechargée, vérification des colonnes:")
                loaded_columns = csv_config_manager.get_columns(supplier)
                logger.info(f"  Colonnes chargées: {len(loaded_columns)}")
                logger.info(f"  Premières colonnes: {loaded_columns[:5]}")
                
                # Appeler la fonction de génération
                generate_csv_from_db(
                    output_file=output_file,
                    output_db=db_path,
                    supplier=supplier,
                    categories=categories,
                    gamme=gamme
                )
                
                # Vérifier que le fichier existe
                if not os.path.exists(output_file):
                    raise ValueError(f"Le fichier CSV généré n'existe pas: {output_file}")
                
                return output_file
            else:
                raise ValueError(f"Fournisseur '{supplier}' non supporté pour l'instant")
        
        finally:
            # Toujours restaurer la configuration
            self._restore_config()
    
    def _backup_config(self):
        """Sauvegarde csv_config.json dans un fichier backup."""
        if self.config_file.exists():
            try:
                shutil.copy2(self.config_file, self.backup_file)
                logger.debug(f"Configuration sauvegardée: {self.backup_file}")
            except Exception as e:
                logger.error(f"Erreur lors de la sauvegarde de la configuration: {e}")
                raise
    
    def _restore_config(self):
        """Restaure csv_config.json depuis le backup."""
        if self.backup_file.exists():
            try:
                shutil.copy2(self.backup_file, self.config_file)
                self.backup_file.unlink()  # Supprimer le backup
                logger.debug("Configuration restaurée")
            except Exception as e:
                logger.error(f"Erreur lors de la restauration de la configuration: {e}")
                # Ne pas lever d'exception pour ne pas masquer l'erreur originale
    
    def _modify_config(self, supplier: str, selected_fields: List[str], 
                      handle_source: str, vendor: str):
        """Modifie csv_config.json avec les paramètres sélectionnés."""
        try:
            # Charger la configuration actuelle
            if self.config_file.exists():
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    config = json.load(f)
            else:
                config = {}
            
            # S'assurer que le fournisseur existe dans la config
            if supplier not in config:
                config[supplier] = {}
            
            # Mettre à jour les colonnes sélectionnées
            config[supplier]['columns'] = selected_fields.copy()
            
            # Mettre à jour handle_source et vendor
            config[supplier]['handle_source'] = handle_source
            config[supplier]['vendor'] = vendor
            
            # Sauvegarder la configuration modifiée
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(config, f, indent=2, ensure_ascii=False)
            
            logger.info(f"Configuration modifiée pour {supplier}:")
            logger.info(f"  - Champs sélectionnés: {len(selected_fields)}")
            logger.info(f"  - Handle source: {handle_source}")
            logger.info(f"  - Vendor: {vendor}")
            logger.info(f"  - Colonnes: {selected_fields[:5]}{'...' if len(selected_fields) > 5 else ''}")
            
        except Exception as e:
            logger.error(f"Erreur lors de la modification de la configuration: {e}")
            raise
    
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
        
        # TODO: Ajouter d'autres fournisseurs quand leurs bases de données seront disponibles
        # Vérifier Cristel
        # try:
        #     from utils.app_config import get_cristel_db_path
        #     db_path = get_cristel_db_path()
        #     if Path(db_path).exists():
        #         suppliers.append('cristel')
        # except Exception:
        #     pass
        
        # Vérifier Artiga
        # try:
        #     from utils.app_config import get_artiga_db_path
        #     db_path = get_artiga_db_path()
        #     if Path(db_path).exists():
        #         suppliers.append('artiga')
        # except Exception:
        #     pass
        
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
        else:
            # TODO: Ajouter d'autres fournisseurs
            return []
    
    def get_gammes(self, supplier: str) -> List[str]:
        """
        Récupère les gammes disponibles pour un fournisseur.
        
        Args:
            supplier: Nom du fournisseur
            
        Returns:
            Liste des gammes disponibles
        """
        if supplier == 'garnier':
            try:
                from utils.garnier_db import GarnierDB
                from utils.app_config import get_garnier_db_path
                
                db = GarnierDB(get_garnier_db_path())
                gammes = db.get_available_gammes()
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
        Récupère la configuration actuelle pour un fournisseur.
        
        Args:
            supplier: Nom du fournisseur
            
        Returns:
            Dictionnaire avec 'columns', 'handle_source', 'vendor'
        """
        try:
            from csv_config import get_csv_config
            
            csv_config_manager = get_csv_config()
            columns = csv_config_manager.get_columns(supplier)
            handle_source = csv_config_manager.get_handle_source(supplier)
            vendor = csv_config_manager.get_vendor(supplier)
            
            return {
                'columns': columns,
                'handle_source': handle_source,
                'vendor': vendor
            }
        except Exception as e:
            logger.error(f"Erreur lors de la récupération de la configuration: {e}")
            return {
                'columns': SHOPIFY_ALL_COLUMNS.copy(),
                'handle_source': 'barcode',
                'vendor': supplier.capitalize()
            }
