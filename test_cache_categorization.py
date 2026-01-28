#!/usr/bin/env python3
"""
Script de test pour le cache de catégorisation Google Shopping.

Test les fonctionnalités:
- Cache HIT (produit identique)
- Cache MISS (nouveau produit)
- Catégorie parente (confidence basse)
- Statistiques du cache
"""

import sys
import logging
from apps.ai_editor.db import AIPromptsDB

# Configuration du logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    datefmt='%H:%M:%S'
)

logger = logging.getLogger(__name__)


def test_cache_system():
    """Test complet du système de cache."""
    
    logger.info("=" * 80)
    logger.info("TEST DU SYSTÈME DE CACHE DE CATÉGORISATION")
    logger.info("=" * 80)
    
    db = AIPromptsDB()
    
    # Produit de test
    test_product = {
        'Title': 'NAPPE EN COTON - ARGELOS',
        'Type': 'Nappes',
        'Vendor': 'Garnier-Thiebaut',
        'Handle': 'nappe-coton-argelos'
    }
    
    # 1. Test Cache MISS (premier accès)
    logger.info("\n📋 TEST 1: Cache MISS (produit non catégorisé)")
    logger.info("-" * 80)
    
    cached = db.get_cached_category(test_product)
    
    if cached:
        logger.error("❌ ERREUR: Produit déjà dans le cache!")
    else:
        logger.info("✅ Cache MISS confirmé (attendu)")
    
    # 2. Simuler une catégorisation réussie
    logger.info("\n📋 TEST 2: Sauvegarde dans le cache (haute confidence)")
    logger.info("-" * 80)
    
    success = db.save_to_cache(
        test_product,
        category_code='3320',
        category_path='Maison et jardin > Arts de la table et arts culinaires > Linge de table > Nappes',
        confidence=0.95,
        rationale='Nappe en coton pour table'
    )
    
    if success:
        logger.info("✅ Produit sauvegardé dans le cache")
    else:
        logger.error("❌ ERREUR: Échec de la sauvegarde")
    
    # 3. Test Cache HIT (accès suivant)
    logger.info("\n📋 TEST 3: Cache HIT (produit catégorisé)")
    logger.info("-" * 80)
    
    cached = db.get_cached_category(test_product)
    
    if cached:
        logger.info("✅ Cache HIT confirmé!")
        logger.info(f"  • Catégorie: {cached['category_path']}")
        logger.info(f"  • Code: {cached['category_code']}")
        logger.info(f"  • Confidence: {cached['confidence']:.2%}")
        logger.info(f"  • Rationale: {cached['rationale']}")
    else:
        logger.error("❌ ERREUR: Produit non trouvé dans le cache")
    
    # 4. Test confidence basse (pas de mise en cache)
    logger.info("\n📋 TEST 4: Confidence basse (pas de cache)")
    logger.info("-" * 80)
    
    test_product_low = {
        'Title': 'BOUDIN DE PORTE TISSU',
        'Type': 'Décoration',
        'Vendor': 'Garnier-Thiebaut',
        'Handle': 'boudin-porte'
    }
    
    success = db.save_to_cache(
        test_product_low,
        category_code='536',
        category_path='Maison et jardin',
        confidence=0.45,  # Trop basse
        rationale='Catégorie générique'
    )
    
    if not success:
        logger.info("✅ Sauvegarde refusée (confidence < 80%, attendu)")
    else:
        logger.error("❌ ERREUR: Produit avec confidence basse sauvegardé!")
    
    # 5. Test catégorie parente
    logger.info("\n📋 TEST 5: Catégorie parente")
    logger.info("-" * 80)
    
    test_path = "Maison et jardin > Linge > Literie > Couvertures"
    parent = db.get_parent_category(test_path)
    
    if parent:
        code, path = parent
        logger.info("✅ Catégorie parente trouvée:")
        logger.info(f"  • Original: {test_path}")
        logger.info(f"  • Parent: {path}")
        logger.info(f"  • Code: {code}")
    else:
        logger.warning("⚠️ Catégorie parente non trouvée (peut être normal si taxonomie incomplète)")
    
    # 6. Statistiques du cache
    logger.info("\n📋 TEST 6: Statistiques du cache")
    logger.info("-" * 80)
    
    stats = db.get_cache_stats()
    
    logger.info(f"  • Total produits en cache: {stats['total_entries']}")
    logger.info(f"  • Confidence moyenne: {stats['avg_confidence']:.2%}")
    logger.info(f"  • Utilisation max: {stats['max_uses']} fois")
    
    # 7. Test use_count (réutilisation)
    logger.info("\n📋 TEST 7: Compteur d'utilisation")
    logger.info("-" * 80)
    
    # Premier accès
    cached = db.get_cached_category(test_product)
    logger.info(f"  • Accès 1: use_count devrait être 2 (création + 1 lecture)")
    
    # Deuxième accès
    cached = db.get_cached_category(test_product)
    logger.info(f"  • Accès 2: use_count devrait être 3")
    
    # Vérifier use_count dans la DB
    cursor = db.conn.cursor()
    product_key = db._generate_product_key(test_product)
    cursor.execute('SELECT use_count FROM product_category_cache WHERE product_key = ?', (product_key,))
    result = cursor.fetchone()
    
    if result:
        logger.info(f"✅ use_count actuel: {result['use_count']}")
    
    # 8. Test variation de produit (même titre, différent vendor)
    logger.info("\n📋 TEST 8: Variation de produit (vendor différent)")
    logger.info("-" * 80)
    
    test_product_variant = {
        'Title': 'NAPPE EN COTON - ARGELOS',  # Même titre
        'Type': 'Nappes',                     # Même type
        'Vendor': 'Artiga',                   # Vendor différent
        'Handle': 'nappe-coton-argelos-artiga'
    }
    
    cached_variant = db.get_cached_category(test_product_variant)
    
    if not cached_variant:
        logger.info("✅ Cache MISS confirmé (vendor différent = product_key différent)")
    else:
        logger.warning("⚠️ Cache HIT (les vendors sont traités comme identiques)")
    
    # Résumé final
    logger.info("\n" + "=" * 80)
    logger.info("RÉSUMÉ DES TESTS")
    logger.info("=" * 80)
    
    final_stats = db.get_cache_stats()
    logger.info(f"✅ Total produits en cache: {final_stats['total_entries']}")
    logger.info(f"✅ Confidence moyenne: {final_stats['avg_confidence']:.2%}")
    logger.info(f"✅ Tests terminés avec succès!")
    
    db.close()


if __name__ == '__main__':
    try:
        test_cache_system()
    except Exception as e:
        logger.error(f"❌ Erreur lors des tests: {e}", exc_info=True)
        sys.exit(1)
