# -*- mode: python ; coding: utf-8 -*-
"""
Configuration PyInstaller pour créer un exécutable Mac Intel.
"""

import os
import sys

block_cipher = None

# Chemin du répertoire de travail (répertoire parent car build.spec est dans creation-build)
# SPECPATH est le chemin absolu du fichier .spec
script_dir = os.path.dirname(os.path.abspath(SPECPATH))
work_dir = os.path.dirname(script_dir)  # Répertoire parent (racine du projet)

# Vérification: s'assurer que run_gui.py existe dans work_dir
run_gui_path = os.path.join(work_dir, 'run_gui.py')
if not os.path.exists(run_gui_path):
    # Si pas trouvé, essayer le répertoire parent (au cas où)
    work_dir = script_dir
    run_gui_path = os.path.join(work_dir, 'run_gui.py')
    if not os.path.exists(run_gui_path):
        raise FileNotFoundError(f"run_gui.py non trouvé dans {work_dir} ni dans {os.path.dirname(script_dir)}")

# Chemin de l'icône (si disponible)
icon_path = None
# Chercher l'icône dans le répertoire racine ou dans creation-build
if os.path.exists(os.path.join(work_dir, 'app_icon.icns')):
    icon_path = os.path.join(work_dir, 'app_icon.icns')
elif os.path.exists(os.path.join(script_dir, 'app_icon.icns')):
    icon_path = os.path.join(script_dir, 'app_icon.icns')
elif os.path.exists(os.path.join(work_dir, 'icon.icns')):
    icon_path = os.path.join(work_dir, 'icon.icns')
elif os.path.exists(os.path.join(script_dir, 'icon.icns')):
    icon_path = os.path.join(script_dir, 'icon.icns')
elif os.path.exists(os.path.join(work_dir, 'docs', 'app_icon.icns')):
    icon_path = os.path.join(work_dir, 'docs', 'app_icon.icns')

# Collecter les fichiers de données à inclure
datas = []

# Fichiers de configuration JSON
config_files = [
    ('app_config.json', '.'),
    ('csv_config.json', '.'),
    ('ai_config.json', '.'),
]

for config_file, dest_dir in config_files:
    src_path = os.path.join(work_dir, config_file)
    if os.path.exists(src_path):
        datas.append((src_path, dest_dir))

# Fichier HTML du visualiseur
html_file = os.path.join(work_dir, 'apps', 'gui', 'viewer_window_simple.html')
if os.path.exists(html_file):
    datas.append((html_file, 'apps/gui'))

# Fichiers de scripts chargés par chemin (PyInstaller ne les détecte pas)
extra_data_files = [
    ('scraper-artiga.py', '.'),
    ('scraper-cristel.py', '.'),
    ('garnier/garnier_functions.py', 'garnier'),
    ('garnier/scraper_garnier_module.py', 'garnier'),
    ('garnier/scraper-collect.py', 'garnier'),
    ('garnier/scraper-process.py', 'garnier'),
    ('garnier/scraper-generate-csv.py', 'garnier'),
    ('garnier/scraper-gamme.py', 'garnier'),
    ('garnier/query_product.py', 'garnier'),
]

for rel_path, dest_dir in extra_data_files:
    src_path = os.path.join(work_dir, rel_path)
    if os.path.exists(src_path):
        datas.append((src_path, dest_dir))

# Créer le répertoire database dans le bundle (les fichiers .db seront créés à l'exécution)
# On inclut juste la structure de répertoire si nécessaire

a = Analysis(
    [run_gui_path],  # Point d'entrée principal (chemin absolu)
    pathex=[work_dir],
    binaries=[],
    datas=datas,
    hiddenimports=[
        'customtkinter',
        'customtkinter.windows',
        'customtkinter.windows.ctk_tk',
        'scrapers.garnier_scraper',
        'scrapers.artiga_scraper',
        'scrapers.cristel_scraper',
        'scrapers.base_scraper',
        'utils.env_manager',
        'utils.setup_checker',
        'utils.scraper_registry',
        'utils.garnier_db',
        'utils.artiga_db',
        'utils.cristel_db',
        'utils.csv_ai_processor',
        'utils.google_shopping_optimizer',
        'utils.ai_providers',
        'utils.app_config',
        'apps.gui.main_window',
        'apps.gui.import_window',
        'apps.gui.progress_window',
        'apps.gui.config_window',
        'apps.gui.setup_window',
        'apps.gui.viewer_window',
        'apps.gui.ai_editor_window',
        'apps.ai_editor.gui.window',
        'apps.ai_editor.gui.viewer',
        'apps.gui.csv_config_window',
        'apps.gui.reprocess_window',
        'apps.ai_editor.processor',
        'apps.ai_editor.csv_storage',
        'apps.ai_editor.db',
        'apps.csv_generator.generator',
        'garnier.garnier_functions',
        'garnier.scraper_garnier_module',
        'selenium',
        'selenium.webdriver',
        'selenium.webdriver.chrome',
        'selenium.webdriver.chrome.service',
        'selenium.webdriver.chrome.options',
        'selenium.webdriver.common.by',
        'selenium.webdriver.support',
        'selenium.webdriver.support.ui',
        'selenium.webdriver.support.wait',
        'selenium.common.exceptions',
        'webdriver_manager',
        'webdriver_manager.chrome',
        'pandas',
        'bs4',
        'lxml',
        'requests',
        'dotenv',
        'tkinterweb',
        'PIL',
        'PIL.Image',
        'PIL.ImageTk',
        'sqlite3',
        'json',
        'logging',
        'threading',
        'queue',
        'pathlib',
        'tempfile',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        'matplotlib',
        'numpy.distutils',
        'pydoc',
        'tkinter.test',
        'test',
        'tests',
        'unittest',
        'pdb',
        'doctest',
    ],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    name='ScrapersShopify',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    exclude_binaries=True,
    runtime_tmpdir=None,
    console=False,  # Pas de console pour une application GUI
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch='x86_64',  # Mac Intel
    codesign_identity=None,
    entitlements_file=None,
    icon=icon_path,  # Icône si disponible
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='ScrapersShopify',
)

app = BUNDLE(
    coll,
    name='ScrapersShopify.app',
    icon=icon_path,  # Icône si disponible
    bundle_identifier='com.shopify.scrapers',
    version='1.0.0',
    info_plist={
        'NSPrincipalClass': 'NSApplication',
        'NSHighResolutionCapable': 'True',
        'CFBundleShortVersionString': '1.0.0',
        'CFBundleVersion': '1.0.0',
        'LSMinimumSystemVersion': '10.13.0',  # macOS High Sierra minimum
        'NSHumanReadableCopyright': 'Copyright © 2024',
        'CFBundleName': 'Scrapers Shopify',
        'CFBundleDisplayName': 'Scrapers Shopify',
        'NSRequiresAquaSystemAppearance': False,
    },
)

