cd /Users/jean-loup/shopify/garnier && python3 -c "
import sqlite3
from utils.app_config import get_garnier_db_path

db_path = get_garnier_db_path()
print(f'Connexion à la base de données: {db_path}')

conn = sqlite3.connect(db_path)
# Activer les contraintes de clés étrangères pour que CASCADE fonctionne
conn.execute('PRAGMA foreign_keys = ON')
cursor = conn.cursor()

# Supprimer toutes les données des tables dans le bon ordre
# (en respectant les contraintes de clés étrangères)
print('Suppression des données des tables...')

# 1. Supprimer d'abord les tables dépendantes (sera fait automatiquement par CASCADE, mais on le fait explicitement pour être sûr)
cursor.execute('DELETE FROM product_images')
print(f'  - product_images: {cursor.rowcount} ligne(s) supprimée(s)')

cursor.execute('DELETE FROM product_variants')
print(f'  - product_variants: {cursor.rowcount} ligne(s) supprimée(s)')

cursor.execute('DELETE FROM gamme_products')
print(f'  - gamme_products: {cursor.rowcount} ligne(s) supprimée(s)')

# 2. Supprimer les tables principales
cursor.execute('DELETE FROM products')
print(f'  - products: {cursor.rowcount} ligne(s) supprimée(s)')

cursor.execute('DELETE FROM gammes')
print(f'  - gammes: {cursor.rowcount} ligne(s) supprimée(s)')

# Réinitialiser sqlite_sequence
print('Réinitialisation de sqlite_sequence...')
cursor.execute('DELETE FROM sqlite_sequence')
print('  - sqlite_sequence vidée')

conn.commit()
conn.close()

print('✅ Base de données vidée avec succès!')
"