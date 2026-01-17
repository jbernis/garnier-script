#!/usr/bin/env python3
"""
Script interactif pour configurer les champs CSV Shopify pour chaque fournisseur.
Permet d'ajouter, retirer ou réinitialiser les champs.
"""

import sys
import argparse
from csv_config import (
    get_csv_config, 
    SHOPIFY_ALL_COLUMNS, 
    HANDLE_OPTIONS,
    DEFAULT_CONFIG
)


def print_menu():
    """Affiche le menu principal."""
    print("\n" + "="*60)
    print("  CONFIGURATION DES CHAMPS CSV SHOPIFY")
    print("="*60)
    print("\n1. Voir la configuration actuelle")
    print("2. Configurer les champs pour un fournisseur")
    print("3. Ajouter un champ pour un fournisseur")
    print("4. Retirer un champ pour un fournisseur")
    print("5. Configurer la source du Handle")
    print("6. Réinitialiser la configuration d'un fournisseur")
    print("7. Réinitialiser toute la configuration")
    print("0. Quitter")
    print("\n" + "-"*60)


def print_config_for_supplier(config, supplier):
    """Affiche la configuration pour un fournisseur spécifique."""
    import sys
    try:
        print("\n" + "="*60, flush=True)
        print(f"  CONFIGURATION - {supplier.upper()}", flush=True)
        print("="*60, flush=True)
        
        print(f"\n📦 {supplier.upper()}", flush=True)
        print(f"   Vendor: {config.get_vendor(supplier)}", flush=True)
        print(f"   Handle source: {config.get_handle_source(supplier)}", flush=True)
        columns = config.get_columns(supplier)
        print(f"   Nombre de champs: {len(columns)}", flush=True)
        
        # Afficher les premiers champs
        if columns:
            print(f"   Premiers champs: {', '.join(columns[:5])}", flush=True)
            if len(columns) > 5:
                print(f"   ... et {len(columns) - 5} autres champs", flush=True)
            
            # Afficher tous les champs
            print(f"\n   Liste complète des champs ({len(columns)}):", flush=True)
            for i, col in enumerate(columns, 1):
                print(f"      {i:2d}. {col}", flush=True)
        else:
            print("   ⚠️  Aucun champ configuré!", flush=True)
        
        print("\n" + "="*60, flush=True)
        print()  # Ligne vide pour la lisibilité
        sys.stdout.flush()
        
    except Exception as e:
        print(f"\n⚠️  Erreur lors de l'affichage de la configuration: {e}", flush=True)
        import traceback
        traceback.print_exc()


def print_config(config):
    """Affiche la configuration actuelle pour tous les fournisseurs."""
    import sys
    try:
        print("\n" + "="*60, flush=True)
        print("  CONFIGURATION ACTUELLE - TOUS LES FOURNISSEURS", flush=True)
        print("="*60, flush=True)
        
        suppliers = config.get_all_suppliers()
        if not suppliers:
            print("\n⚠️  Aucune configuration trouvée.", flush=True)
            print("   La configuration par défaut sera utilisée.", flush=True)
            return
        
        for supplier in suppliers:
            try:
                print(f"\n📦 {supplier.upper()}", flush=True)
                print(f"   Vendor: {config.get_vendor(supplier)}", flush=True)
                print(f"   Handle source: {config.get_handle_source(supplier)}", flush=True)
                columns = config.get_columns(supplier)
                print(f"   Nombre de champs: {len(columns)}", flush=True)
                
                # Afficher les premiers champs
                if columns:
                    print(f"   Premiers champs: {', '.join(columns[:5])}", flush=True)
                    if len(columns) > 5:
                        print(f"   ... et {len(columns) - 5} autres champs", flush=True)
                    
                    # Afficher tous les champs
                    print(f"\n   Liste complète des champs ({len(columns)}):", flush=True)
                    for i, col in enumerate(columns, 1):
                        print(f"      {i:2d}. {col}", flush=True)
                else:
                    print("   ⚠️  Aucun champ configuré!", flush=True)
                    
            except Exception as e:
                print(f"   ⚠️  Erreur lors de l'affichage de {supplier}: {e}", flush=True)
                import traceback
                traceback.print_exc()
        
        print("\n" + "="*60, flush=True)
        print()  # Ligne vide pour la lisibilité
        sys.stdout.flush()  # Forcer l'affichage
        
    except Exception as e:
        print(f"\n⚠️  Erreur lors de l'affichage de la configuration: {e}")
        import traceback
        traceback.print_exc()


def configure_columns_interactive(config, supplier):
    """Configuration interactive des colonnes."""
    print(f"\n📦 Configuration des champs pour: {supplier.upper()}")
    print("\nChamps Shopify disponibles:")
    
    current_columns = config.get_columns(supplier)
    
    # Afficher les champs disponibles avec leur statut
    print("\n" + "-"*60)
    print(f"{'N°':<5} {'Statut':<10} {'Nom du champ':<45}")
    print("-"*60)
    
    for idx, col in enumerate(SHOPIFY_ALL_COLUMNS, 1):
        status = "✓ Inclus" if col in current_columns else "✗ Exclu"
        print(f"{idx:<5} {status:<10} {col}")
    
    print("\nOptions:")
    print("  • Entrez les numéros des champs à INCLURE (séparés par des virgules)")
    print("  • Exemple: 1,2,3,5,10")
    print("  • Tapez 'all' pour inclure tous les champs")
    print("  • Tapez 'cancel' pour annuler")
    
    choice = input("\nVotre choix: ").strip().lower()
    
    if choice == 'cancel':
        print("Annulation.")
        return
    
    if choice == 'all':
        config.set_columns(supplier, SHOPIFY_ALL_COLUMNS.copy())
        print(f"✓ Tous les champs ont été inclus pour {supplier}.")
        return
    
    try:
        # Parser les numéros
        indices = [int(x.strip()) for x in choice.split(',')]
        selected_columns = [SHOPIFY_ALL_COLUMNS[i-1] for i in indices if 1 <= i <= len(SHOPIFY_ALL_COLUMNS)]
        
        if selected_columns:
            config.set_columns(supplier, selected_columns)
            print(f"✓ Configuration mise à jour pour {supplier}.")
            print(f"  {len(selected_columns)} champ(s) sélectionné(s).")
        else:
            print("✗ Aucun champ valide sélectionné.")
    except ValueError:
        print("✗ Format invalide. Utilisez des numéros séparés par des virgules.")


def add_column_interactive(config, supplier):
    """Ajoute un champ interactivement."""
    print(f"\n📦 Ajout d'un champ pour: {supplier.upper()}")
    
    current_columns = config.get_columns(supplier)
    available_columns = [col for col in SHOPIFY_ALL_COLUMNS if col not in current_columns]
    
    if not available_columns:
        print("✓ Tous les champs sont déjà inclus.", flush=True)
        print(f"   {len(current_columns)} champ(s) configuré(s) pour {supplier}.", flush=True)
        return
    
    print("\nChamps disponibles à ajouter:")
    for idx, col in enumerate(available_columns, 1):
        print(f"  {idx}. {col}")
    
    try:
        choice = input("\nNuméro du champ à ajouter (ou 'cancel'): ").strip().lower()
        if choice == 'cancel':
            return
        
        idx = int(choice) - 1
        if 0 <= idx < len(available_columns):
            column = available_columns[idx]
            config.add_column(supplier, column)
            print(f"✓ Champ '{column}' ajouté pour {supplier}.")
        else:
            print("✗ Numéro invalide.")
    except ValueError:
        print("✗ Format invalide.")


def remove_column_interactive(config, supplier):
    """Retire un champ interactivement."""
    print(f"\n📦 Retrait d'un champ pour: {supplier.upper()}")
    
    current_columns = config.get_columns(supplier)
    
    if not current_columns:
        print("✗ Aucun champ configuré.")
        return
    
    print("\nChamps actuellement inclus:")
    for idx, col in enumerate(current_columns, 1):
        print(f"  {idx}. {col}")
    
    try:
        choice = input("\nNuméro du champ à retirer (ou 'cancel'): ").strip().lower()
        if choice == 'cancel':
            return
        
        idx = int(choice) - 1
        if 0 <= idx < len(current_columns):
            column = current_columns[idx]
            config.remove_column(supplier, column)
            print(f"✓ Champ '{column}' retiré pour {supplier}.")
        else:
            print("✗ Numéro invalide.")
    except ValueError:
        print("✗ Format invalide.")


def configure_handle_source(config, supplier):
    """Configure la source du Handle."""
    print(f"\n📦 Configuration de la source du Handle pour: {supplier.upper()}")
    print(f"\nSource actuelle: {config.get_handle_source(supplier)}")
    
    print("\nOptions disponibles:")
    for key, description in HANDLE_OPTIONS.items():
        current = " (actuel)" if key == config.get_handle_source(supplier) else ""
        print(f"  {key}: {description}{current}")
    
    choice = input("\nVotre choix (ou 'cancel'): ").strip().lower()
    
    if choice == 'cancel':
        return
    
    if choice in HANDLE_OPTIONS:
        config.set_handle_source(supplier, choice)
        print(f"✓ Source du Handle mise à jour: {choice}")
    else:
        print("✗ Option invalide.")


def select_supplier(config):
    """Sélectionne un fournisseur."""
    suppliers = config.get_all_suppliers()
    
    if not suppliers:
        print("\nAucun fournisseur configuré.")
        return None
    
    print("\nFournisseurs disponibles:")
    for idx, supplier in enumerate(suppliers, 1):
        print(f"  {idx}. {supplier}")
    
    try:
        choice = input("\nNuméro du fournisseur (ou 'cancel'): ").strip().lower()
        if choice == 'cancel':
            return None
        
        idx = int(choice) - 1
        if 0 <= idx < len(suppliers):
            return suppliers[idx]
        else:
            print("✗ Numéro invalide.")
            return None
    except ValueError:
        print("✗ Format invalide.")
        return None


def main():
    """Fonction principale."""
    config = get_csv_config()
    
    print("\n" + "="*60)
    print("  CONFIGURATION DES CHAMPS CSV SHOPIFY")
    print("="*60)
    print("\nCe script vous permet de configurer les champs CSV générés")
    print("par les scrapers pour chaque fournisseur.")
    
    while True:
        print_menu()
        choice = input("\nVotre choix: ").strip()
        
        if choice == '0':
            print("\nAu revoir!")
            break
        elif choice == '1':
            # Demander si l'utilisateur veut voir tous les fournisseurs ou un spécifique
            print("\n" + "-"*60)
            print("Voir la configuration:")
            print("  1. Tous les fournisseurs")
            print("  2. Un fournisseur spécifique")
            print("  0. Retour au menu principal")
            sub_choice = input("\nVotre choix: ").strip()
            
            # Normaliser le choix (enlever les espaces, convertir en minuscule si nécessaire)
            sub_choice = sub_choice.strip()
            
            if sub_choice == '0':
                continue  # Retour au menu principal
            elif sub_choice == '1':
                # Afficher tous les fournisseurs
                print_config(config)
                input("\nAppuyez sur Entrée pour continuer...")  # Pause pour voir le résultat
            elif sub_choice == '2':
                supplier = select_supplier(config)
                if supplier:
                    print_config_for_supplier(config, supplier)
                    input("\nAppuyez sur Entrée pour continuer...")  # Pause pour voir le résultat
                else:
                    print("Aucun fournisseur sélectionné.", flush=True)
            else:
                print(f"✗ Choix invalide: '{sub_choice}'. Options valides: 0, 1, 2", flush=True)
                input("\nAppuyez sur Entrée pour continuer...")  # Pause pour voir le message d'erreur
            
            import sys
            sys.stdout.flush()
        elif choice == '2':
            supplier = select_supplier(config)
            if supplier:
                configure_columns_interactive(config, supplier)
                input("\nAppuyez sur Entrée pour continuer...")  # Pause pour voir le résultat
            else:
                print("Aucun fournisseur sélectionné.", flush=True)
        elif choice == '3':
            supplier = select_supplier(config)
            if supplier:
                add_column_interactive(config, supplier)
                input("\nAppuyez sur Entrée pour continuer...")  # Pause pour voir le résultat
            else:
                print("Aucun fournisseur sélectionné.", flush=True)
        elif choice == '4':
            supplier = select_supplier(config)
            if supplier:
                remove_column_interactive(config, supplier)
                input("\nAppuyez sur Entrée pour continuer...")  # Pause pour voir le résultat
            else:
                print("Aucun fournisseur sélectionné.", flush=True)
        elif choice == '5':
            supplier = select_supplier(config)
            if supplier:
                configure_handle_source(config, supplier)
                input("\nAppuyez sur Entrée pour continuer...")  # Pause pour voir le résultat
            else:
                print("Aucun fournisseur sélectionné.", flush=True)
        elif choice == '6':
            supplier = select_supplier(config)
            if supplier:
                confirm = input(f"\n⚠️  Réinitialiser la configuration pour {supplier}? (oui/non): ").strip().lower()
                if confirm == 'oui':
                    config.reset_to_default(supplier)
                    print(f"✓ Configuration réinitialisée pour {supplier}.")
        elif choice == '7':
            confirm = input("\n⚠️  Réinitialiser TOUTE la configuration? (oui/non): ").strip().lower()
            if confirm == 'oui':
                config.reset_to_default()
                print("✓ Toute la configuration a été réinitialisée.")
        else:
            print("✗ Choix invalide.")


if __name__ == '__main__':
    parser = argparse.ArgumentParser(
        description='Configure les champs CSV Shopify pour chaque fournisseur (Garnier, Artiga, Cristel).',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
DESCRIPTION:
  Ce script permet de configurer les champs CSV générés par les scrapers Shopify.
  La configuration est sauvegardée dans csv_config.json et s'applique automatiquement
  à tous les CSV générés par les scrapers.

FONCTIONNALITÉS:
  • Configurer les champs CSV pour chaque fournisseur (ajouter/retirer)
  • Choisir la source du Handle (barcode/sku/title)
  • Voir la configuration actuelle
  • Réinitialiser la configuration

EXEMPLES D'UTILISATION:

  1. Lancer le script interactif:
     python configure_csv_fields.py

  2. Voir la configuration actuelle:
     python configure_csv_fields.py
     # Choisir l'option 1 dans le menu

  3. Changer Handle = SKU au lieu de barcode pour Garnier:
     python configure_csv_fields.py
     # Option 5 → sélectionner "garnier" → choisir "sku"

  4. Retirer des champs Google Shopping pour Artiga:
     python configure_csv_fields.py
     # Option 4 → sélectionner "artiga" → choisir les champs à retirer

  5. Réinitialiser la configuration d'un fournisseur:
     python configure_csv_fields.py
     # Option 6 → sélectionner le fournisseur → confirmer

CONFIGURATION DU HANDLE:
  Par défaut, le Handle utilise le Variant Barcode. Options disponibles:
  
  • barcode (défaut): Utilise le Variant Barcode comme Handle
  • sku: Utilise le Variant SKU comme Handle
  • title: Utilise le Title slugifié comme Handle
  • custom: Utilise une fonction personnalisée (à implémenter)

CHAMPS SHOPIFY DISPONIBLES:
  Le script gère 48 champs Shopify standard:
  
  • Handle, Title, Body (HTML), Vendor, Product Category, Type, Tags
  • Option1/2/3 Name/Value (pour les variantes)
  • Variant SKU, Variant Price, Variant Compare At Price
  • Variant Barcode, Variant Inventory Qty
  • Image Src, Image Position, Image Alt Text
  • SEO Title, SEO Description
  • Google Shopping / ... (catégorie, genre, âge, MPN, condition, etc.)
  • Variant Image, Variant Weight Unit, Variant Tax Code
  • Cost per item, Status
  • Et bien d'autres...

FICHIER DE CONFIGURATION:
  La configuration est sauvegardée dans csv_config.json à la racine du projet.
  Ce fichier peut être modifié manuellement si nécessaire, mais il est recommandé
  d'utiliser ce script pour éviter les erreurs de syntaxe.

NOTES:
  • La configuration s'applique immédiatement aux prochains CSV générés
  • Chaque fournisseur peut avoir sa propre configuration
  • L'ordre des colonnes dans le CSV respecte l'ordre configuré
  • Les champs non configurés ne seront pas présents dans le CSV généré
        """
    )
    
    # Parser les arguments (--help est géré automatiquement par argparse)
    args = parser.parse_args()
    
    try:
        main()
    except KeyboardInterrupt:
        print("\n\nInterruption par l'utilisateur.")
        sys.exit(0)

