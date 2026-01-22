cd /Users/jean-loup/shopify/garnier && python3 -c "
import sqlite3
from utils.app_config import get_cristel_db_path

db_path = get_cristel_db_path()
print(f'Connexion à la base de données: {db_path}')

conn = sqlite3.connect(db_path)
cursor = conn.cursor()

# Supprimer toutes les données des tables
print('Suppression des données des tables...')
cursor.execute('DELETE FROM product_images')
print(f'  - product_images: {cursor.rowcount} ligne(s) supprimée(s)')

cursor.execute('DELETE FROM product_variants')
print(f'  - product_variants: {cursor.rowcount} ligne(s) supprimée(s)')

cursor.execute('DELETE FROM products')
print(f'  - products: {cursor.rowcount} ligne(s) supprimée(s)')

# Réinitialiser sqlite_sequence
print('Réinitialisation de sqlite_sequence...')
cursor.execute('DELETE FROM sqlite_sequence')
print('  - sqlite_sequence vidée')

conn.commit()
conn.close()

print('✅ Base de données vidée avec succès!')
"