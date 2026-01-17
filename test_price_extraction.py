#!/usr/bin/env python3
"""
Script de test pour déboguer l'extraction du prix des variants Artiga
"""

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait, Select
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException
from bs4 import BeautifulSoup
import time
import re

def extract_price(driver):
    """Extrait le prix depuis la structure HTML spécifique"""
    variant_price = ""
    
    try:
        # Méthode 1: Chercher avec Selenium dans la structure exacte
        # <div class="current-price">
        #   <span class="display-4 current-price-display price">129,00&nbsp;€</span>
        # </div>
        current_price_div = driver.find_element(By.CSS_SELECTOR, 'div.current-price')
        if current_price_div:
            # Chercher le span avec les classes display-4 current-price-display price
            price_span = None
            try:
                price_span = current_price_div.find_element(By.CSS_SELECTOR, 'span.display-4.current-price-display.price')
            except:
                try:
                    price_span = current_price_div.find_element(By.CSS_SELECTOR, 'span.current-price-display.price')
                except:
                    try:
                        price_span = current_price_div.find_element(By.CSS_SELECTOR, 'span.current-price-display')
                    except:
                        pass
            
            if price_span:
                price_text = price_span.text.strip()
                print(f"  Texte brut du prix: '{price_text}'")
                # Nettoyer le texte (enlever &nbsp; (\xa0) et autres caractères)
                price_text_clean = price_text.replace('\xa0', ' ').replace('€', '').replace('&nbsp;', ' ').strip()
                print(f"  Texte nettoyé: '{price_text_clean}'")
                # Extraire le prix (format: "129,00" ou "129.00")
                price_match = re.search(r'([\d,]+\.?\d*)', price_text_clean.replace(' ', '').replace(',', '.'))
                if price_match:
                    price_value = float(price_match.group(1).replace(',', '.'))
                    variant_price = price_match.group(1).replace(',', '.')
                    print(f"  Prix extrait: {variant_price} (valeur: {price_value})")
    except Exception as e:
        print(f"  Erreur extraction prix avec Selenium: {e}")
    
    # Méthode 2: Si pas trouvé avec Selenium, utiliser BeautifulSoup
    if not variant_price:
        try:
            html = driver.page_source
            soup = BeautifulSoup(html, 'html.parser')
            
            # Chercher le div avec class="current-price"
            current_price_div = soup.find('div', class_='current-price')
            if current_price_div:
                print(f"  Div current-price trouvé")
                # Chercher le span avec les classes display-4 current-price-display price
                price_span = current_price_div.find('span', class_=lambda x: x and 'current-price-display' in ' '.join(x) if isinstance(x, list) else 'current-price-display' in str(x))
                
                if price_span:
                    price_text = price_span.get_text(strip=True)
                    print(f"  Texte brut du prix (BeautifulSoup): '{price_text}'")
                    # Nettoyer le texte
                    price_text_clean = price_text.replace('\xa0', ' ').replace('€', '').replace('&nbsp;', ' ').strip()
                    print(f"  Texte nettoyé (BeautifulSoup): '{price_text_clean}'")
                    # Extraire le prix
                    price_match = re.search(r'([\d,]+\.?\d*)', price_text_clean.replace(' ', '').replace(',', '.'))
                    if price_match:
                        price_value = float(price_match.group(1).replace(',', '.'))
                        variant_price = price_match.group(1).replace(',', '.')
                        print(f"  Prix extrait (BeautifulSoup): {variant_price} (valeur: {price_value})")
        except Exception as e:
            print(f"  Erreur extraction prix avec BeautifulSoup: {e}")
    
    return variant_price

def main():
    # Configuration Chrome
    options = Options()
    options.add_argument('--headless')
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')
    options.add_argument('--disable-gpu')
    options.add_argument('--window-size=1920,1080')
    
    driver = webdriver.Chrome(options=options)
    
    try:
        # Tester avec le produit qui a des prix différents
        url = 'https://www.artiga.fr/nappe-en-coton-argelos'
        print(f"🌐 Navigation vers: {url}")
        print(f"📝 Ce produit devrait avoir des prix différents selon les variants")
        driver.get(url)
        time.sleep(5)
        
        # Attendre que la page soit chargée
        try:
            WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, 'div.current-price span.current-price-display'))
            )
            print("✅ Page chargée, élément de prix présent")
        except TimeoutException:
            print("⚠️  Timeout en attendant l'élément de prix")
        
        time.sleep(2)
        
        # Trouver le dropdown de sélection de taille
        print("\n🔍 Recherche du dropdown de taille...")
        try:
            # Chercher le select avec id="group_10"
            select_element = driver.find_element(By.CSS_SELECTOR, 'select#group_10')
            print(f"✅ Dropdown trouvé: {select_element.get_attribute('id')}")
            
            # Créer un objet Select
            select = Select(select_element)
            
            # Afficher les options disponibles
            print("\n📋 Options disponibles dans le dropdown:")
            for option in select.options:
                is_selected = option.is_selected()
                print(f"  - {option.text} (value={option.get_attribute('value')}, title={option.get_attribute('title')}) {'[SÉLECTIONNÉ]' if is_selected else ''}")
            
            # Reconstituer les URLs à partir du dropdown
            # Format: {value}-taille-{digits du title}_cm
            variants_to_test = []
            for option in select.options:
                option_value = option.get_attribute('value')
                option_title = option.get_attribute('title') or option.text.strip()
                option_text = option.text.strip()
                
                # Extraire uniquement les digits du title (ex: "160 cm" -> "160")
                digits_match = re.search(r'(\d+)', option_title)
                if digits_match:
                    digits = digits_match.group(1)
                    # Construire l'URL avec hash (format: #/65-taille-160_cm)
                    option_href = f"#/{option_value}-taille-{digits}_cm"
                    variants_to_test.append({
                        'value': option_value,
                        'text': option_text,
                        'title': option_title,
                        'digits': digits,
                        'href': option_href,
                        'url': f"{url}{option_href}"
                    })
            
            results = []
            
            print(f"\n📋 Variants à tester: {len(variants_to_test)}")
            for variant in variants_to_test:
                print(f"  - {variant['text']} (value={variant['value']}, digits={variant['digits']}, href={variant['href']})")
                print(f"    URL: {variant['url']}")
            
            # Naviguer vers chaque URL et extraire le prix
            print("\n" + "=" * 80)
            print("🔍 TEST: Navigation vers chaque URL avec hash et extraction du prix")
            print("=" * 80)
            
            for variant in variants_to_test:
                print("\n" + "=" * 80)
                print(f"🔄 TEST VARIANT: {variant['text']} (value={variant['value']}, digits={variant['digits']})")
                print("=" * 80)
                
                # Naviguer directement vers l'URL avec hash
                print(f"🌐 Navigation vers: {variant['url']}")
                driver.get(variant['url'])
                time.sleep(5)
                
                # Attendre que la page soit chargée
                try:
                    WebDriverWait(driver, 10).until(
                        EC.presence_of_element_located((By.CSS_SELECTOR, 'div.current-price span.current-price-display'))
                    )
                    print("✅ Page chargée avec variant")
                    time.sleep(3)  # Attendre que le JavaScript mette à jour le prix
                except TimeoutException:
                    print("⚠️  Timeout en attendant l'élément de prix")
                
                # Vérifier quelle option est sélectionnée
                try:
                    select_check = Select(driver.find_element(By.CSS_SELECTOR, 'select#group_10'))
                    selected_option = select_check.first_selected_option
                    selected_value = selected_option.get_attribute('value')
                    selected_text = selected_option.text
                    print(f"📋 Variant sélectionné dans le dropdown: {selected_text} (value={selected_value})")
                    
                    # Vérifier avec JavaScript aussi
                    selected_option_js = driver.execute_script("""
                        var select = document.querySelector('select#group_10');
                        var selectedOption = select.options[select.selectedIndex];
                        return {
                            value: selectedOption.value,
                            text: selectedOption.text,
                            title: selectedOption.title
                        };
                    """)
                    print(f"📋 Variant sélectionné (JavaScript): {selected_option_js['text']} (value={selected_option_js['value']})")
                except Exception as e:
                    print(f"⚠️  Impossible de vérifier le variant sélectionné: {e}")
                
                # Copier l'élément current-price
                print(f"\n📋 ÉLÉMENT CURRENT-PRICE:")
                try:
                    current_price_div = driver.find_element(By.CSS_SELECTOR, 'div.current-price')
                    current_price_html = driver.execute_script("""
                        var element = arguments[0];
                        return element.outerHTML;
                    """, current_price_div)
                    print("=" * 80)
                    print(current_price_html)
                    print("=" * 80)
                except Exception as e:
                    print(f"❌ Erreur lors de la copie de l'élément current-price: {e}")
                
                # Attendre que le prix soit mis à jour
                print(f"  ⏳ Attente de la mise à jour du prix...")
                time.sleep(5)
                
                # Attendre explicitement que l'élément de prix soit présent
                try:
                    WebDriverWait(driver, 10).until(
                        EC.presence_of_element_located((By.CSS_SELECTOR, 'div.current-price span.current-price-display'))
                    )
                    print(f"  ✅ Élément de prix présent")
                    
                    # Attendre que le prix soit réellement mis à jour (peut prendre du temps)
                    # Vérifier plusieurs fois si le prix change
                    previous_price = None
                    for check_attempt in range(5):
                        try:
                            current_price_div = driver.find_element(By.CSS_SELECTOR, 'div.current-price')
                            price_span = current_price_div.find_element(By.CSS_SELECTOR, 'span.current-price-display')
                            current_price_text = price_span.text.strip()
                            
                            if previous_price and current_price_text != previous_price:
                                print(f"  ✅ Prix changé détecté (tentative {check_attempt+1}): '{previous_price}' -> '{current_price_text}'")
                                break
                            elif check_attempt == 0:
                                previous_price = current_price_text
                                print(f"  📊 Prix initial détecté: '{current_price_text}'")
                            
                            time.sleep(2)
                        except:
                            pass
                    
                    time.sleep(2)  # Attendre encore un peu pour que le JavaScript mette à jour le prix
                except TimeoutException:
                    print("  ⚠️  Timeout en attendant l'élément de prix")
                
                # Vérifier quelle option est sélectionnée
                select_check = Select(driver.find_element(By.CSS_SELECTOR, 'select#group_10'))
                selected_option = select_check.first_selected_option
                selected_value = selected_option.get_attribute('value')
                selected_text = selected_option.text
                
                print(f"\n📋 VARIANT SÉLECTIONNÉ:")
                print(f"  Value: {selected_value}")
                print(f"  Text: {selected_text}")
                
                # Vérifier avec JavaScript aussi
                selected_option_js = driver.execute_script("""
                    var select = document.querySelector('select#group_10');
                    var selectedOption = select.options[select.selectedIndex];
                    return {
                        value: selectedOption.value,
                        text: selectedOption.text
                    };
                """)
                print(f"  JavaScript - Value: {selected_option_js['value']}, Text: {selected_option_js['text']}")
                
                # Récupérer le prix avec plusieurs méthodes pour déboguer
                print(f"\n📊 PRIX:")
                
                # Attendre et vérifier plusieurs fois que le prix est bien mis à jour
                prices_found = []
                for price_check in range(3):
                    try:
                        # Méthode 1: Avec Selenium directement
                        current_price_div = driver.find_element(By.CSS_SELECTOR, 'div.current-price')
                        price_span = current_price_div.find_element(By.CSS_SELECTOR, 'span.current-price-display')
                        price_text_selenium = price_span.text.strip()
                        
                        # Méthode 2: Avec JavaScript pour voir le contenu réel
                        price_js = driver.execute_script("""
                            var priceDiv = document.querySelector('div.current-price span.current-price-display');
                            if (priceDiv) {
                                return {
                                    textContent: priceDiv.textContent.trim(),
                                    innerHTML: priceDiv.innerHTML.trim(),
                                    innerText: priceDiv.innerText.trim()
                                };
                            }
                            return null;
                        """)
                        
                        if price_js:
                            price_text_clean = price_js['textContent'].replace('\xa0', ' ').replace('€', '').strip()
                            price_match = re.search(r'([\d,]+\.?\d*)', price_text_clean.replace(' ', '').replace(',', '.'))
                            if price_match:
                                price_value = price_match.group(1).replace(',', '.')
                                prices_found.append(price_value)
                                
                                if price_check == 0:
                                    print(f"  Tentative {price_check+1}: '{price_text_selenium}' -> {price_value} €")
                                    print(f"  JavaScript textContent: '{price_js['textContent']}'")
                                    print(f"  JavaScript innerHTML: '{price_js['innerHTML']}'")
                                elif price_value != prices_found[0]:
                                    print(f"  ⚠️  CHANGEMENT DÉTECTÉ! Tentative {price_check+1}: {price_value} € (était {prices_found[0]} €)")
                                    break
                    except Exception as e:
                        if price_check == 0:
                            print(f"  Erreur: {e}")
                    
                    if price_check < 2:
                        time.sleep(3)  # Attendre entre les vérifications
                
                # Utiliser le dernier prix trouvé ou extraire avec extract_price
                if prices_found:
                    price = prices_found[-1]
                else:
                    price = extract_price(driver)
                
                print(f"✅ Prix final pour {variant['text']}: {price} €")
                
                # Stocker le résultat
                results.append({
                    'variant': variant['text'],
                    'value': variant['value'],
                    'selected_value': selected_value,
                    'selected_text': selected_text,
                    'price': price
                })
                
                # Afficher le HTML du dropdown pour ce variant
                try:
                    form_group = driver.find_element(By.CSS_SELECTOR, 'div.form-group.product-variants-item')
                    dropdown_html = driver.execute_script("""
                        var element = arguments[0];
                        return element.outerHTML;
                    """, form_group)
                    print(f"\n📋 HTML DU DROPDOWN:")
                    print(dropdown_html[:200] + "..." if len(dropdown_html) > 200 else dropdown_html)
                except Exception as e:
                    print(f"⚠️  Erreur lors de la récupération du HTML: {e}")
            
            # Résumé final
            print("\n" + "=" * 80)
            print("📈 RÉSUMÉ DES RÉSULTATS")
            print("=" * 80)
            for result in results:
                print(f"  {result['variant']} (value={result['value']}): Prix = {result['price']} €")
            
            # Vérifier si les prix sont différents
            prices = [r['price'] for r in results if r['price']]
            unique_prices = set(prices)
            print(f"\n💰 Prix uniques trouvés: {sorted(unique_prices)}")
            if len(unique_prices) > 1:
                print("✅ Les prix sont DIFFÉRENTS selon les variants!")
            else:
                print("⚠️  Tous les variants ont le même prix")
            
        except NoSuchElementException as e:
            print(f"❌ Erreur: Dropdown non trouvé - {e}")
        except Exception as e:
            print(f"❌ Erreur: {e}")
        
    finally:
        print("\n🔚 Fermeture du navigateur...")
        driver.quit()
        print("✅ Script terminé")

if __name__ == '__main__':
    main()

