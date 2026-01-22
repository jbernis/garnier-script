#!/usr/bin/env python3
"""
Script de test pour vérifier l'extraction des prix depuis le DOM de la page web
pour chaque variant des produits Artiga.
"""

import sys
import os
import time
import re
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from selenium.common.exceptions import TimeoutException, NoSuchElementException

# URLs à tester
TEST_URLS = [
    "https://www.artiga.fr/nappe-en-coton-argelos",
    "https://www.artiga.fr/nappe-en-coton-adour-bleu"
]

def get_selenium_driver(headless=False):
    """Crée un driver Selenium Chrome."""
    try:
        chrome_options = Options()
        if headless:
            chrome_options.add_argument('--headless')
        chrome_options.add_argument('--no-sandbox')
        chrome_options.add_argument('--disable-dev-shm-usage')
        chrome_options.add_argument('--disable-blink-features=AutomationControlled')
        chrome_options.add_experimental_option('excludeSwitches', ['enable-logging'])
        chrome_options.add_experimental_option('useAutomationExtension', False)
        
        # Activer les logs de performance pour capturer les requêtes AJAX
        chrome_options.set_capability('goog:loggingPrefs', {'performance': 'ALL'})
        
        driver = webdriver.Chrome(options=chrome_options)
        return driver
    except Exception as e:
        print(f"Erreur lors de la création du driver: {e}")
        return None

def extract_price_from_dom(driver):
    """
    Extrait le prix depuis le DOM de la page web.
    Priorité : prix régulier (regular-price) > prix courant (current-price-display)
    """
    variant_price = None
    source = None
    
    try:
        # PRIORITÉ 1: Chercher le prix régulier (pour les produits en promotion)
        try:
            regular_price_span = driver.find_element(By.CSS_SELECTOR, 'span.regular-price')
            price_text = regular_price_span.text.strip()
            price_text_clean = price_text.replace('\xa0', ' ').replace('€', '').replace('&nbsp;', ' ').strip()
            price_match = re.search(r'([\d,]+\.?\d*)', price_text_clean.replace(' ', '').replace(',', '.'))
            if price_match:
                price_value = float(price_match.group(1).replace(',', '.'))
                if 1 <= price_value <= 10000:
                    variant_price = price_match.group(1).replace(',', '.')
                    source = "regular-price"
        except NoSuchElementException:
            pass
        
        # PRIORITÉ 2: Si pas de prix régulier, chercher le prix courant
        if not variant_price:
            try:
                current_price_div = driver.find_element(By.CSS_SELECTOR, 'div.current-price')
                price_span = current_price_div.find_element(By.CSS_SELECTOR, 'span.current-price-display')
                price_text = price_span.text.strip()
                price_text_clean = price_text.replace('\xa0', ' ').replace('€', '').replace('&nbsp;', ' ').strip()
                price_match = re.search(r'([\d,]+\.?\d*)', price_text_clean.replace(' ', '').replace(',', '.'))
                if price_match:
                    price_value = float(price_match.group(1).replace(',', '.'))
                    if 1 <= price_value <= 10000:
                        variant_price = price_match.group(1).replace(',', '.')
                        source = "current-price-display"
            except NoSuchElementException:
                pass
                
    except Exception as e:
        print(f"    Erreur lors de l'extraction du prix depuis le DOM: {e}")
    
    return variant_price, source

def get_variants(driver):
    """Récupère la liste des variants disponibles sur la page."""
    from selenium.webdriver.support.ui import Select
    
    variants = []
    
    try:
        # Chercher d'abord les selects (comme dans le scraper)
        variant_selectors = [
            'select[name*="group"]',
            'select[id*="group"]',
            'select[name*="variant"]',
            'select[name*="attribute"]',
            'select[name*="size"]',
            'select[id*="size"]'
        ]
        
        for selector in variant_selectors:
            try:
                variant_selects = driver.find_elements(By.CSS_SELECTOR, selector)
                for select_elem in variant_selects:
                    try:
                        select = Select(select_elem)
                        options = select.options
                        for option in options:
                            value = option.get_attribute('value')
                            text = option.text.strip()
                            if value and text and value != '' and value != '0':
                                variants.append({
                                    'type': 'select',
                                    'element': select_elem,
                                    'value': value,
                                    'text': text
                                })
                    except Exception as e:
                        continue
            except:
                continue
        
        # Si pas de select trouvé, chercher des boutons/liens (comme sur Artiga)
        if not variants:
            try:
                # Chercher les boutons/liens de sélection de taille
                variant_buttons = driver.find_elements(By.CSS_SELECTOR, 
                    'a[href*="#"], button[data-value], .product-variants a, .product-variants button, a[data-id]')
                
                for button in variant_buttons:
                    try:
                        variant_text = button.text.strip()
                        variant_value = button.get_attribute('data-value') or button.get_attribute('value') or ''
                        variant_href = button.get_attribute('href') or ''
                        
                        # Filtrer les variants qui ne sont pas des tailles/couleurs
                        is_valid_variant = False
                        
                        # Vérifier si c'est un variant valide
                        if variant_href and '#' in variant_href:
                            if 'taille' in variant_href.lower() or re.search(r'#/\d+-', variant_href):
                                is_valid_variant = True
                        
                        # Vérifier aussi le texte
                        if variant_text:
                            # Le texte doit contenir des indications de taille (cm, couverts, taille, size)
                            if any(keyword in variant_text.lower() for keyword in ['cm', 'taille', 'size', 'couverts']) or re.search(r'\d+\s*cm', variant_text):
                                is_valid_variant = True
                            # Exclure les textes qui ne sont pas des variants
                            excluded_texts = ['mail', 'partager', 'partage', 'share', 'print', 'imprimer', 'tweet', 'pinterest']
                            if any(excluded in variant_text.lower() for excluded in excluded_texts):
                                is_valid_variant = False
                        
                        if is_valid_variant and (variant_value or variant_href or variant_text):
                            variants.append({
                                'type': 'button',
                                'element': button,
                                'value': variant_value,
                                'text': variant_text,
                                'href': variant_href
                            })
                    except Exception as e:
                        continue
            except Exception as e:
                print(f"    Erreur lors de la recherche des boutons: {e}")
        
        # Si toujours rien trouvé, chercher dans les éléments avec texte "cm" (tailles)
        if not variants:
            try:
                # Chercher les éléments contenant des tailles (160 cm, 200 cm, etc.)
                all_elements = driver.find_elements(By.XPATH, "//*[contains(text(), 'cm')]")
                seen_texts = set()
                for elem in all_elements:
                    text = elem.text.strip()
                    # Vérifier que c'est bien un pattern de taille
                    if re.match(r'^\d+\s*cm\s*$', text) and text not in seen_texts:
                        seen_texts.add(text)
                        variants.append({
                            'type': 'text',
                            'element': elem,
                            'value': text,
                            'text': text
                        })
            except Exception as e:
                print(f"    Erreur lors de la recherche par XPath: {e}")
                
    except Exception as e:
        print(f"Erreur lors de la récupération des variants: {e}")
    
    return variants

def test_product_url(driver, url):
    """Teste l'extraction des prix pour tous les variants d'un produit."""
    print(f"\n{'='*80}")
    print(f"Test de l'URL: {url}")
    print(f"{'='*80}\n")
    
    try:
        # Charger la page
        print(f"Chargement de la page...")
        driver.get(url)
        time.sleep(3)  # Attendre le chargement initial
        
        # Récupérer le nom du produit
        try:
            product_name = driver.find_element(By.CSS_SELECTOR, 'h1, .product-name, .product-title').text.strip()
            print(f"Produit: {product_name}\n")
        except:
            product_name = "Produit inconnu"
            print(f"Produit: {product_name}\n")
        
        # Récupérer les variants
        print("Recherche des variants...")
        variants = get_variants(driver)
        
        if not variants:
            print("⚠️  Aucun variant trouvé automatiquement. Tentative de sélection manuelle...")
            # Essayer de trouver les tailles dans le texte de la page
            try:
                page_text = driver.find_element(By.TAG_NAME, 'body').text
                # Chercher des patterns comme "160 cm", "200 cm", etc.
                size_pattern = re.findall(r'(\d+\s*cm)', page_text)
                if size_pattern:
                    unique_sizes = list(set(size_pattern))
                    print(f"Tailles trouvées dans le texte: {unique_sizes}")
                    # Essayer de cliquer sur chaque taille
                    for size in unique_sizes:
                        try:
                            size_elem = driver.find_element(By.XPATH, f"//*[contains(text(), '{size}')]")
                            variants.append({
                                'type': 'text',
                                'element': size_elem,
                                'value': size,
                                'text': size
                            })
                        except:
                            pass
            except Exception as e:
                print(f"Erreur: {e}")
        
        if not variants:
            print("❌ Aucun variant trouvé. Extraction du prix par défaut...")
            price, source = extract_price_from_dom(driver)
            if price:
                print(f"✅ Prix par défaut trouvé: {price} € (source: {source})")
            else:
                print(f"❌ Aucun prix trouvé")
            return
        
        print(f"✅ {len(variants)} variant(s) trouvé(s): {[v['text'] for v in variants]}\n")
        
        # Extraire le prix pour chaque variant
        results = []
        
        for idx, variant in enumerate(variants, 1):
            print(f"[{idx}/{len(variants)}] Test du variant: {variant['text']}")
            
            try:
                # Sélectionner le variant
                if variant['type'] == 'select':
                    from selenium.webdriver.support.ui import Select
                    select = Select(variant['element'])
                    select.select_by_value(variant['value'])
                    
                    # Forcer la mise à jour avec JavaScript (comme dans le scraper)
                    try:
                        driver.execute_script("""
                            var select = arguments[0];
                            var targetValue = arguments[1];
                            
                            select.value = targetValue;
                            
                            for (var i = 0; i < select.options.length; i++) {
                                if (select.options[i].value == targetValue) {
                                    select.options[i].setAttribute('selected', 'selected');
                                    select.options[i].selected = true;
                                } else {
                                    select.options[i].removeAttribute('selected');
                                    select.options[i].selected = false;
                                }
                            }
                            
                            var changeEvent = new Event('change', { bubbles: true });
                            select.dispatchEvent(changeEvent);
                            
                            var inputEvent = new Event('input', { bubbles: true });
                            select.dispatchEvent(inputEvent);
                        """, variant['element'], variant['value'])
                    except:
                        pass
                elif variant['type'] == 'button':
                    # Scroll et clic
                    driver.execute_script("arguments[0].scrollIntoView(true);", variant['element'])
                    time.sleep(0.5)
                    variant['element'].click()
                elif variant['type'] == 'text':
                    # Essayer de cliquer sur l'élément
                    try:
                        driver.execute_script("arguments[0].scrollIntoView(true);", variant['element'])
                        time.sleep(0.5)
                        driver.execute_script("arguments[0].click();", variant['element'])
                    except:
                        # Si ça ne marche pas, essayer de trouver un parent cliquable
                        try:
                            parent = variant['element'].find_element(By.XPATH, './..')
                            parent.click()
                        except:
                            pass
                
                # Attendre que le prix soit mis à jour
                print(f"    Attente de la mise à jour du prix...")
                time.sleep(3)
                
                # Attendre que l'élément de prix soit présent
                try:
                    WebDriverWait(driver, 10).until(
                        EC.any_of(
                            EC.presence_of_element_located((By.CSS_SELECTOR, 'span.regular-price')),
                            EC.presence_of_element_located((By.CSS_SELECTOR, 'div.current-price span.current-price-display'))
                        )
                    )
                    time.sleep(2)  # Attendre que JavaScript mette à jour le prix
                except TimeoutException:
                    print(f"    ⚠️  Timeout en attendant l'élément de prix")
                
                # Extraire le prix depuis le DOM
                price, source = extract_price_from_dom(driver)
                
                if price:
                    print(f"    ✅ Prix trouvé: {price} € (source: {source})")
                    results.append({
                        'variant': variant['text'],
                        'price': price,
                        'source': source,
                        'success': True
                    })
                else:
                    print(f"    ❌ Prix non trouvé")
                    results.append({
                        'variant': variant['text'],
                        'price': None,
                        'source': None,
                        'success': False
                    })
                    
            except Exception as e:
                print(f"    ❌ Erreur lors du test du variant: {e}")
                results.append({
                    'variant': variant['text'],
                    'price': None,
                    'source': None,
                    'success': False,
                    'error': str(e)
                })
            
            print()
        
        # Résumé
        print(f"\n{'='*80}")
        print(f"RÉSUMÉ pour {product_name}")
        print(f"{'='*80}")
        print(f"Total variants testés: {len(results)}")
        print(f"Prix trouvés: {sum(1 for r in results if r['success'])}")
        print(f"Prix non trouvés: {sum(1 for r in results if not r['success'])}")
        print(f"\nDétails:")
        for result in results:
            if result['success']:
                print(f"  ✅ {result['variant']}: {result['price']} € (source: {result['source']})")
            else:
                error_msg = f" - {result.get('error', '')}" if result.get('error') else ""
                print(f"  ❌ {result['variant']}: Prix non trouvé{error_msg}")
        print()
        
    except Exception as e:
        print(f"❌ Erreur lors du test de l'URL {url}: {e}")
        import traceback
        traceback.print_exc()

def main():
    """Fonction principale."""
    print("="*80)
    print("TEST D'EXTRACTION DES PRIX DEPUIS LE DOM")
    print("="*80)
    
    driver = get_selenium_driver(headless=False)  # headless=False pour voir le navigateur
    
    if not driver:
        print("❌ Impossible de créer le driver Selenium")
        return
    
    try:
        for url in TEST_URLS:
            test_product_url(driver, url)
            time.sleep(2)  # Pause entre les tests
        
        print("\n" + "="*80)
        print("TESTS TERMINÉS")
        print("="*80)
        
    finally:
        print("\nFermeture du navigateur dans 5 secondes...")
        time.sleep(5)
        driver.quit()

if __name__ == '__main__':
    main()
