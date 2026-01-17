#!/usr/bin/env python3
"""
Script de test pour vérifier la configuration CSV.
"""

from csv_config import get_csv_config, SHOPIFY_ALL_COLUMNS

def test_config():
    """Teste la configuration CSV."""
    print("="*60)
    print("  TEST DE LA CONFIGURATION CSV")
    print("="*60)
    
    config = get_csv_config()
    
    # Tester pour chaque fournisseur
    suppliers = ['garnier', 'artiga', 'cristel']
    
    for supplier in suppliers:
        print(f"\n📦 {supplier.upper()}")
        print("-" * 60)
        
        columns = config.get_columns(supplier)
        handle_source = config.get_handle_source(supplier)
        vendor = config.get_vendor(supplier)
        
        print(f"Vendor: {vendor}")
        print(f"Handle source: {handle_source}")
        print(f"Nombre de colonnes: {len(columns)}")
        print(f"\nColonnes configurées:")
        for i, col in enumerate(columns, 1):
            print(f"  {i:2d}. {col}")
        
        # Vérifier que toutes les colonnes Shopify sont présentes
        missing = [col for col in SHOPIFY_ALL_COLUMNS if col not in columns]
        if missing:
            print(f"\n⚠️  Colonnes manquantes ({len(missing)}):")
            for col in missing:
                print(f"  - {col}")
        else:
            print(f"\n✓ Toutes les colonnes Shopify sont présentes!")
        
        # Vérifier l'ordre
        if columns == SHOPIFY_ALL_COLUMNS:
            print("✓ L'ordre des colonnes correspond à l'ordre Shopify standard")
        else:
            print("⚠️  L'ordre des colonnes est personnalisé")
    
    print("\n" + "="*60)
    print("Test terminé!")
    print("="*60)

if __name__ == '__main__':
    test_config()

