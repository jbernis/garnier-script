#!/usr/bin/env python3
"""
Script de test pour vérifier que la refonte de la page de diagnostic fonctionne correctement.
"""

import sys
from pathlib import Path

def test_refonte():
    """Vérifie que toutes les modifications ont été appliquées."""
    
    print("=" * 80)
    print("TEST DE LA REFONTE DE LA PAGE DE DIAGNOSTIC")
    print("=" * 80)
    print()
    
    window_file = Path("apps/ai_editor/gui/window.py")
    db_file = Path("apps/ai_editor/db.py")
    
    # 1. Vérifier que les nouvelles méthodes existent dans window.py
    print("1. Vérification des nouvelles méthodes dans window.py...")
    window_content = window_file.read_text()
    
    methods_to_check = [
        "def select_all_errors(self)",
        "def deselect_all_errors(self)",
        "def update_error_selection_count(self)",
        "def reprocess_errors_sequential(self)"
    ]
    
    all_found = True
    for method in methods_to_check:
        if method in window_content:
            print(f"   ✅ {method}")
        else:
            print(f"   ❌ {method} - NON TROUVÉ")
            all_found = False
    
    # 2. Vérifier que les anciennes méthodes ont été supprimées
    print("\n2. Vérification de la suppression des anciennes méthodes...")
    old_methods = [
        "def reprocess_selected_errors(self)",
        "def reprocess_all_errors(self)"
    ]
    
    any_old_found = False
    for method in old_methods:
        if method in window_content:
            print(f"   ❌ {method} - ENCORE PRÉSENT (devrait être supprimé)")
            any_old_found = True
    
    if not any_old_found:
        print("   ✅ Anciennes méthodes correctement supprimées")
    
    # 3. Vérifier les éléments de l'interface
    print("\n3. Vérification de l'interface...")
    interface_elements = [
        '"✓ Tout sélectionner"',
        '"✗ Tout désélectionner"',
        'self.error_selection_label',
        '"🔄 Retraiter les produits sélectionnés (Mode séquentiel)"'
    ]
    
    for element in interface_elements:
        if element in window_content:
            print(f"   ✅ {element}")
        else:
            print(f"   ❌ {element} - NON TROUVÉ")
            all_found = False
    
    # 4. Vérifier les checkboxes par défaut cochées
    print("\n4. Vérification des checkboxes par défaut...")
    if 'ctk.BooleanVar(value=True)' in window_content:
        print("   ✅ Checkboxes cochées par défaut (value=True)")
    else:
        print("   ❌ Checkboxes NON cochées par défaut")
        all_found = False
    
    # 5. Vérifier le callback sur les checkboxes
    print("\n5. Vérification du callback sur les checkboxes...")
    if 'command=self.update_error_selection_count' in window_content:
        print("   ✅ Callback update_error_selection_count configuré")
    else:
        print("   ❌ Callback NON configuré")
        all_found = False
    
    # 6. Vérifier save_config dans db.py
    print("\n6. Vérification de save_config dans db.py...")
    db_content = db_file.read_text()
    if 'def save_config(self, key: str, value: Any):' in db_content:
        print("   ✅ Méthode save_config existe")
    else:
        print("   ❌ Méthode save_config NON TROUVÉE")
        all_found = False
    
    # 7. Vérifier l'utilisation de save_config
    print("\n7. Vérification de l'utilisation de save_config...")
    if "self.db.save_config('batch_size', 1)" in window_content:
        print("   ✅ save_config('batch_size', 1) appelé dans reprocess_errors_sequential")
    else:
        print("   ❌ save_config NON appelé")
        all_found = False
    
    # Résumé
    print("\n" + "=" * 80)
    if all_found and not any_old_found:
        print("✅ TOUS LES TESTS SONT PASSÉS - La refonte est complète !")
    else:
        print("⚠️  CERTAINS TESTS ONT ÉCHOUÉ - Vérifier les éléments ci-dessus")
    print("=" * 80)
    print()
    
    # Test de la configuration batch_size
    print("8. Test de la configuration batch_size...")
    try:
        from apps.ai_editor.db import AIPromptsDB
        
        db = AIPromptsDB()
        db.save_config('batch_size', 1)
        value = db.get_config_int('batch_size')
        
        if value == 1:
            print("   ✅ Configuration batch_size=1 fonctionne")
        else:
            print(f"   ❌ batch_size vaut {value} au lieu de 1")
        
        db.close()
    except Exception as e:
        print(f"   ⚠️  Impossible de tester la base de données: {e}")
    
    print()


if __name__ == "__main__":
    test_refonte()
