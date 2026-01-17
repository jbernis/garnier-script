#!/usr/bin/env python3
"""
Script de build pour créer l'exécutable avec PyInstaller.
"""

import os
import sys
import subprocess
import shutil
from pathlib import Path


def clean():
    """Nettoie les fichiers de build."""
    print("Nettoyage des fichiers de build...")
    
    script_dir = Path(__file__).parent
    project_root = script_dir.parent
    
    dirs_to_remove = ['build', 'dist']
    
    for dir_name in dirs_to_remove:
        dir_path = project_root / dir_name
        if dir_path.exists():
            shutil.rmtree(dir_path)
            print(f"  ✓ Supprimé: {dir_path}/")
    
    # Nettoyer les fichiers .pyc dans le projet
    for root, dirs, files in os.walk(project_root):
        if '__pycache__' in root and 'venv' not in root and '.git' not in root:
            shutil.rmtree(root)
            print(f"  ✓ Supprimé: {root}/")
    
    print("Nettoyage terminé!")


def build():
    """Crée l'exécutable."""
    print("Construction de l'exécutable...")
    
    # Vérifier que PyInstaller est installé
    try:
        import PyInstaller
    except ImportError:
        print("Erreur: PyInstaller n'est pas installé.")
        print("Installez-le avec: pip install pyinstaller")
        sys.exit(1)
    
    # Vérifier que build.spec existe
    if not os.path.exists('build.spec'):
        print("Erreur: build.spec n'existe pas.")
        sys.exit(1)
    
    # Lancer PyInstaller depuis le répertoire parent (où se trouve run_gui.py)
    script_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(script_dir)
    spec_file = os.path.join(script_dir, 'build.spec')
    
    cmd = [sys.executable, '-m', 'PyInstaller', spec_file, '--clean']
    
    print(f"Exécution: {' '.join(cmd)}")
    print(f"Depuis le répertoire: {project_root}")
    result = subprocess.run(cmd, cwd=project_root)
    
    if result.returncode == 0:
        print("\n✓ Build réussi!")
        print(f"L'application se trouve dans: {os.path.join(project_root, 'dist', 'ScrapersShopify.app')}")
    else:
        print("\n✗ Erreur lors du build")
        sys.exit(1)


def dist():
    """Crée le package de distribution (DMG pour Mac)."""
    print("Création du package de distribution...")
    
    script_dir = Path(__file__).parent
    project_root = script_dir.parent
    
    # Créer le dossier dist si nécessaire
    dist_dir = project_root / 'dist'
    if not dist_dir.exists():
        dist_dir.mkdir()
    
    # Vérifier que l'application existe
    app_path = dist_dir / 'ScrapersShopify.app'
    if not app_path.exists():
        print("Erreur: L'application n'existe pas. Lancez 'python setup.py build' d'abord.")
        sys.exit(1)
    
    # Utiliser le script build_dmg.sh pour créer le DMG
    build_dmg_script = script_dir / 'build_dmg.sh'
    if build_dmg_script.exists():
        print("Utilisation du script build_dmg.sh pour créer le DMG...")
        import subprocess
        result = subprocess.run(['bash', str(build_dmg_script)], cwd=str(script_dir))
        if result.returncode == 0:
            print("\n✓ DMG créé avec succès!")
        else:
            print("\n✗ Erreur lors de la création du DMG")
            sys.exit(1)
    else:
        print("Script build_dmg.sh non trouvé. Création manuelle du DMG...")
        print("Pour créer un DMG sur Mac, utilisez:")
        print("  ./build_dmg.sh")
        print("Ou manuellement:")
        print("  hdiutil create -volname 'ScrapersShopify Installer' -srcfolder dist/ScrapersShopify.app -ov -format UDZO dist/ScrapersShopify_MacIntel.dmg")


def main():
    """Fonction principale."""
    if len(sys.argv) < 2:
        print("Usage: python setup.py [build|clean|dist]")
        print("\nCommandes:")
        print("  build  - Crée l'exécutable")
        print("  clean  - Nettoie les fichiers de build")
        print("  dist   - Crée le package de distribution")
        sys.exit(1)
    
    command = sys.argv[1].lower()
    
    if command == 'build':
        build()
    elif command == 'clean':
        clean()
    elif command == 'dist':
        dist()
    else:
        print(f"Commande inconnue: {command}")
        sys.exit(1)


if __name__ == '__main__':
    main()

