"""
Module commun pour le scraper Garnier-Thiebaut.
Contient les fonctions réutilisables pour la collecte et le traitement.
"""

import sys
import os

# Importer les fonctions depuis garnier_functions.py
# On utilise une approche d'import dynamique pour éviter les problèmes de dépendances circulaires
_scraper_module = None

def _get_scraper_module():
    """Charge le module garnier_functions de manière lazy."""
    global _scraper_module
    if _scraper_module is None:
        # Ajouter le répertoire parent au path si nécessaire
        if os.path.dirname(os.path.abspath(__file__)) not in sys.path:
            sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
        
        import importlib.util
        spec = importlib.util.spec_from_file_location(
            "garnier.garnier_functions",
            os.path.join(os.path.dirname(__file__), "garnier_functions.py")
        )
        _scraper_module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(_scraper_module)
    
    return _scraper_module

# Exposer les fonctions principales
def authenticate(headless=True):
    """Authentifie l'utilisateur sur le site."""
    module = _get_scraper_module()
    return module.authenticate(headless=headless)

def get_categories(driver, session):
    """Récupère la liste des catégories."""
    module = _get_scraper_module()
    return module.get_categories(driver, session)

def get_gammes_from_category(driver, session, category_name):
    """Récupère les gammes d'une catégorie."""
    module = _get_scraper_module()
    return module.get_gammes_from_category(driver, session, category_name)

def get_products_from_gamme(driver, session, gamme_url, headless=True):
    """Récupère les produits d'une gamme."""
    module = _get_scraper_module()
    return module.get_products_from_gamme(driver, session, gamme_url, headless=headless)

def extract_variants_from_product_page(driver, session, product_url, product_code, headless=True):
    """
    Extrait tous les code_vl d'un produit depuis sa page.
    Retourne une liste de dictionnaires avec 'code' et 'size_text'.
    """
    module = _get_scraper_module()
    from bs4 import BeautifulSoup
    import re
    import time
    
    try:
        # Visiter la page produit
        if driver:
            driver.get(product_url)
            time.sleep(3)
            html = driver.page_source
            soup = BeautifulSoup(html, 'html.parser')
        else:
            response = session.get(product_url, timeout=30)
            response.raise_for_status()
            soup = BeautifulSoup(response.content, 'html.parser')
        
        # Chercher le dropdown avec tous les variants
        code_vl_select = soup.find('select', id='code_vl_select')
        all_code_vl = []
        
        if code_vl_select:
            options = code_vl_select.find_all('option')
            for option in options:
                value = option.get('value', '')
                text = option.get_text(strip=True)
                code_match = re.search(r'code_vl=(\d+)', value)
                if code_match:
                    variant_code = code_match.group(1)
                    all_code_vl.append({
                        'code': variant_code,
                        'size_text': text
                    })
        else:
            # Pas de dropdown = produit sans variant
            all_code_vl.append({
                'code': product_code,
                'size_text': ''
            })
        
        return all_code_vl
        
    except Exception as e:
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f"Erreur lors de l'extraction des variants de {product_url}: {e}")
        return []

def extract_variant_data_from_url(driver, session, variant_url, code_vl, headless=True):
    """
    Extrait les données d'un variant depuis son URL.
    Retourne un dictionnaire avec les données du variant.
    Gère automatiquement la ré-authentification en cas de perte de connexion.
    """
    module = _get_scraper_module()
    from bs4 import BeautifulSoup
    import re
    import time
    from selenium.webdriver.common.by import By
    from selenium.webdriver.support.ui import WebDriverWait
    from selenium.webdriver.support import expected_conditions as EC
    from selenium.common.exceptions import TimeoutException, InvalidSessionIdException, StaleElementReferenceException
    import logging
    
    logger = logging.getLogger(__name__)
    
    variant_data = {
        'sku': '',
        'gencode': '',
        'price_pa': '',
        'price_pvc': '',
        'stock': 0,
        'size': '',
        'color': '',
        'material': ''
    }
    
    try:
        if not driver:
            return variant_data
        
        # Vérifier et recréer le driver si nécessaire avant d'accéder à la page
        driver, session = module.check_and_recreate_driver(driver, session, headless=headless)
        
        # Visiter la page du variant avec gestion de la perte de connexion
        try:
            driver.get(variant_url)
            time.sleep(2)
        except InvalidSessionIdException:
            # Session invalide détectée, recréer le driver et réessayer
            logger.warning(f"Session invalide lors de l'accès à {variant_url}, recréation du driver...")
            driver, session = module.check_and_recreate_driver(None, session, headless=headless)
            driver.get(variant_url)
            time.sleep(2)
        
        # Chercher div.tabs.product-tabs avec Selenium
        tabs_div = None
        try:
            wait = WebDriverWait(driver, 10)
            try:
                tabs_div = wait.until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, 'div.tabs.product-tabs'))
                )
            except TimeoutException:
                try:
                    tabs_div = wait.until(
                        EC.presence_of_element_located((By.XPATH, "//div[contains(@class, 'tabs') and contains(@class, 'product-tabs')]"))
                    )
                except TimeoutException:
                    raise Exception(f"div.tabs.product-tabs non trouvé après 10 secondes")
        except InvalidSessionIdException:
            # Session invalide lors de la recherche, recréer et réessayer
            logger.warning(f"Session invalide lors de la recherche de div.tabs.product-tabs, recréation du driver...")
            driver, session = module.check_and_recreate_driver(None, session, headless=headless)
            driver.get(variant_url)
            time.sleep(2)
            # Réessayer la recherche
            wait = WebDriverWait(driver, 10)
            try:
                tabs_div = wait.until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, 'div.tabs.product-tabs'))
                )
            except TimeoutException:
                try:
                    tabs_div = wait.until(
                        EC.presence_of_element_located((By.XPATH, "//div[contains(@class, 'tabs') and contains(@class, 'product-tabs')]"))
                    )
                except TimeoutException:
                    raise Exception(f"div.tabs.product-tabs non trouvé après 10 secondes")
        except Exception as e:
            # Essayer avec BeautifulSoup comme fallback
            try:
                html = driver.page_source
            except InvalidSessionIdException:
                # Session invalide lors de l'accès au HTML, recréer et réessayer
                logger.warning(f"Session invalide lors de l'accès au HTML, recréation du driver...")
                driver, session = module.check_and_recreate_driver(None, session, headless=headless)
                driver.get(variant_url)
                time.sleep(2)
                html = driver.page_source
            
            soup = BeautifulSoup(html, 'html.parser')
            
            def has_both_classes(class_attr):
                if not class_attr:
                    return False
                if isinstance(class_attr, list):
                    classes = class_attr
                else:
                    classes = str(class_attr).split()
                return 'tabs' in classes and 'product-tabs' in classes
            
            tabs_div_bs = soup.find('div', class_=has_both_classes)
            if tabs_div_bs:
                table = tabs_div_bs.find('table')
                if table:
                    tbody = table.find('tbody')
                    if tbody:
                        variant_rows = tbody.find_all('tr')
                        for row in variant_rows:
                            cells = row.find_all('td')
                            if len(cells) >= 2:
                                attribut = cells[0].get_text(strip=True)
                                valeur = cells[1].get_text(strip=True)
                                
                                # Log pour déboguer
                                logger.debug(f"  Attribut trouvé (BS): '{attribut}' = '{valeur}'")
                                
                                if attribut == "Référence":
                                    variant_data['sku'] = valeur
                                    logger.info(f"  ✓ SKU extrait (BS): '{valeur}'")
                                elif attribut == "Code EAN13":
                                    variant_data['gencode'] = valeur
                                    logger.info(f"  ✓ Gencode extrait (BS): '{valeur}'")
                                elif attribut == "Tarif client conseillé":
                                    price_match = re.search(r'([\d,]+)', valeur)
                                    if price_match:
                                        variant_data['price_pvc'] = price_match.group(1).replace(',', '.')
                                elif attribut == "Tarif distributeur":
                                    price_match = re.search(r'([\d,]+)', valeur)
                                    if price_match:
                                        variant_data['price_pa'] = price_match.group(1).replace(',', '.')
                                elif attribut == "Stock dispo":
                                    stock_match = re.search(r'(\d+)', valeur)
                                    if stock_match:
                                        variant_data['stock'] = int(stock_match.group(1))
                                elif attribut in ["Dimensions", "Taille"]:
                                    variant_data['size'] = valeur
                                elif attribut == "Couleur":
                                    variant_data['color'] = valeur
                                elif attribut == "Matière":
                                    variant_data['material'] = valeur
                        return variant_data, driver, session
            
            raise Exception(f"div.tabs.product-tabs introuvable: {e}")
        
        # Extraire les données depuis le tableau avec Selenium
        if tabs_div:
            time.sleep(1)
            try:
                table = tabs_div.find_element(By.TAG_NAME, 'table')
                tbody = table.find_element(By.TAG_NAME, 'tbody')
                variant_rows = tbody.find_elements(By.TAG_NAME, 'tr')
            except InvalidSessionIdException:
                # Session invalide lors de l'accès au tableau, recréer et réessayer
                logger.warning(f"Session invalide lors de l'accès au tableau, recréation du driver...")
                driver, session = module.check_and_recreate_driver(None, session, headless=headless)
                driver.get(variant_url)
                time.sleep(2)
                # Réessayer la recherche du tableau
                wait = WebDriverWait(driver, 10)
                tabs_div = wait.until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, 'div.tabs.product-tabs'))
                )
                table = tabs_div.find_element(By.TAG_NAME, 'table')
                tbody = table.find_element(By.TAG_NAME, 'tbody')
                variant_rows = tbody.find_elements(By.TAG_NAME, 'tr')
            
            for row in variant_rows:
                try:
                    cells = row.find_elements(By.TAG_NAME, 'td')
                    if len(cells) >= 2:
                        attribut = cells[0].text.strip()
                        valeur = cells[1].text.strip()
                        
                        # Log pour déboguer
                        logger.debug(f"  Attribut trouvé: '{attribut}' = '{valeur}'")
                        
                        if attribut == "Référence":
                            variant_data['sku'] = valeur
                            logger.info(f"  ✓ SKU extrait: '{valeur}'")
                        elif attribut == "Code EAN13":
                            variant_data['gencode'] = valeur
                            logger.info(f"  ✓ Gencode extrait: '{valeur}'")
                        elif attribut == "Tarif client conseillé":
                            price_match = re.search(r'([\d,]+)', valeur)
                            if price_match:
                                variant_data['price_pvc'] = price_match.group(1).replace(',', '.')
                        elif attribut == "Tarif distributeur":
                            price_match = re.search(r'([\d,]+)', valeur)
                            if price_match:
                                variant_data['price_pa'] = price_match.group(1).replace(',', '.')
                        elif attribut == "Stock dispo":
                            stock_match = re.search(r'(\d+)', valeur)
                            if stock_match:
                                variant_data['stock'] = int(stock_match.group(1))
                        elif attribut in ["Dimensions", "Taille"]:
                            variant_data['size'] = valeur
                        elif attribut == "Couleur":
                            variant_data['color'] = valeur
                        elif attribut == "Matière":
                            variant_data['material'] = valeur
                except (InvalidSessionIdException, StaleElementReferenceException):
                    # Si session invalide ou élément obsolète, recréer le driver et réessayer
                    logger.warning(f"Session invalide ou élément obsolète lors de l'extraction, recréation du driver...")
                    driver, session = module.check_and_recreate_driver(None, session, headless=headless)
                    driver.get(variant_url)
                    time.sleep(2)
                    # Réessayer avec BeautifulSoup comme fallback
                    html = driver.page_source
                    soup = BeautifulSoup(html, 'html.parser')
                    
                    def has_both_classes(class_attr):
                        if not class_attr:
                            return False
                        if isinstance(class_attr, list):
                            classes = class_attr
                        else:
                            classes = str(class_attr).split()
                        return 'tabs' in classes and 'product-tabs' in classes
                    
                    tabs_div_bs = soup.find('div', class_=has_both_classes)
                    if tabs_div_bs:
                        table = tabs_div_bs.find('table')
                        if table:
                            tbody = table.find('tbody')
                            if tbody:
                                variant_rows_bs = tbody.find_all('tr')
                                for row_bs in variant_rows_bs:
                                    cells_bs = row_bs.find_all('td')
                                    if len(cells_bs) >= 2:
                                        attribut = cells_bs[0].get_text(strip=True)
                                        valeur = cells_bs[1].get_text(strip=True)
                                        
                                        # Log pour déboguer
                                        logger.debug(f"  Attribut trouvé (BS retry): '{attribut}' = '{valeur}'")
                                        
                                        if attribut == "Référence":
                                            variant_data['sku'] = valeur
                                            logger.info(f"  ✓ SKU extrait (BS retry): '{valeur}'")
                                        elif attribut == "Code EAN13":
                                            variant_data['gencode'] = valeur
                                            logger.info(f"  ✓ Gencode extrait (BS retry): '{valeur}'")
                                        elif attribut == "Tarif client conseillé":
                                            price_match = re.search(r'([\d,]+)', valeur)
                                            if price_match:
                                                variant_data['price_pvc'] = price_match.group(1).replace(',', '.')
                                        elif attribut == "Tarif distributeur":
                                            price_match = re.search(r'([\d,]+)', valeur)
                                            if price_match:
                                                variant_data['price_pa'] = price_match.group(1).replace(',', '.')
                                        elif attribut == "Stock dispo":
                                            stock_match = re.search(r'(\d+)', valeur)
                                            if stock_match:
                                                variant_data['stock'] = int(stock_match.group(1))
                                        elif attribut in ["Dimensions", "Taille"]:
                                            variant_data['size'] = valeur
                                        elif attribut == "Couleur":
                                            variant_data['color'] = valeur
                                        elif attribut == "Matière":
                                            variant_data['material'] = valeur
                    break  # Sortir de la boucle car on a utilisé BeautifulSoup
                except Exception:
                    continue
        
        # Log final des données extraites
        logger.info(f"  Données extraites pour variant {code_vl}: SKU='{variant_data.get('sku')}', Gencode='{variant_data.get('gencode')}', Price_PVC='{variant_data.get('price_pvc')}', Price_PA='{variant_data.get('price_pa')}', Stock={variant_data.get('stock')}")
        
        return variant_data, driver, session
        
    except Exception as e:
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f"Erreur lors de l'extraction des données du variant {code_vl}: {e}")
        # RE-LEVER l'exception pour que scraper-garnier-process.py puisse la détecter
        # et appliquer le mécanisme de retry avec wait_for_url_accessible
        raise

def extract_product_name_and_description(driver, session, product_url, fallback_name=None, headless=True):
    """
    Extrait le nom du produit et sa description depuis la page produit.
    Le titre est dans <h3> à l'intérieur de <div class="product-body">.
    
    Args:
        driver: WebDriver Selenium
        session: Session requests
        product_url: URL de la page produit
        fallback_name: Non utilisé (conservé pour compatibilité)
        headless: Mode headless
    
    Returns:
        Tuple (product_name, description) où:
        - product_name: Nom extrait du h3 dans product-body
        - description: Description extraite du <p> dans product-body
    
    Raises:
        Exception: Si le titre n'est pas trouvé
    """
    from bs4 import BeautifulSoup
    import time
    import logging
    
    logger = logging.getLogger(__name__)
    
    product_name = None
    description = ""
    
    try:
        if driver:
            driver.get(product_url)
            time.sleep(3)  # Attendre le chargement de la page
            html = driver.page_source
            soup = BeautifulSoup(html, 'html.parser')
        else:
            response = session.get(product_url, timeout=30)
            response.raise_for_status()
            soup = BeautifulSoup(response.content, 'html.parser')
        
        # Chercher le h3 dans product-body
        product_body = soup.find('div', class_='product-body')
        if product_body:
            h3_elem = product_body.find('h3')
            if h3_elem:
                product_name = h3_elem.get_text(strip=True)
                logger.info(f"    ✓ Titre extrait: {product_name}")
            
            # Chercher la description dans le paragraphe suivant
            next_p = product_body.find('p')
            if next_p:
                description = next_p.get_text(strip=True)
                if description:
                    logger.debug(f"    ✓ Description extraite ({len(description)} caractères)")
        
        # Si le titre n'est pas trouvé, lever une exception
        if not product_name or not product_name.strip():
            logger.error(f"    ✗ Titre non trouvé dans product-body pour {product_url}")
            raise Exception(f"Titre non trouvé dans product-body pour {product_url}")
        
        return product_name.strip(), description
        
    except Exception as e:
        logger.error(f"Erreur lors de l'extraction du nom/description de {product_url}: {e}")
        raise  # Re-lever l'exception pour que l'appelant puisse gérer l'erreur


def extract_product_images(driver, session, product_url, headless=True):
    """
    Extrait toutes les URLs d'images d'un produit Garnier depuis sa page produit.
    Les images sont dans <div id="product-carousel"> avec name="imgzoom".
    Exclut les images product-default.jpg.
    """
    module = _get_scraper_module()
    return module.extract_product_images(driver, session, product_url, headless=headless)


def extract_product_is_new(driver, session, product_url, headless=True):
    """
    Extrait le statut "new" d'un produit depuis sa page produit.
    Cherche <div class="product-labels"> avec <span class="label label-info">new</span>
    """
    module = _get_scraper_module()
    return module.extract_product_is_new(driver, session, product_url, headless=headless)


def check_site_accessible(session, base_url, timeout=10):
    """
    Vérifie si le site est accessible en faisant une requête HTTP simple.
    Retourne True si on obtient un code 200.
    
    Args:
        session: Session requests (avec cookies d'authentification)
        base_url: URL de base du site
        timeout: Timeout en secondes pour la requête
    
    Returns:
        True si le site répond avec 200, False sinon
    """
    import logging
    from requests.exceptions import RequestException, Timeout, ConnectionError
    
    logger = logging.getLogger(__name__)
    
    try:
        # Simple requête GET (équivalent curl)
        response = session.get(base_url, timeout=timeout, allow_redirects=True)
        
        # Vérifier uniquement le code HTTP 200
        if response.status_code == 200:
            logger.debug(f"✓ Site accessible (code {response.status_code})")
            return True
        else:
            logger.debug(f"Site répond avec code {response.status_code}")
            return False
            
    except (Timeout, ConnectionError, RequestException) as e:
        logger.debug(f"Site non accessible: {e}")
        return False


def wait_for_site_accessible(session, base_url, check_interval=30, timeout=10):
    """
    Attend que le site redevienne accessible (code 200).
    Vérifie toutes les check_interval secondes jusqu'à obtenir 200.
    
    Args:
        session: Session requests
        base_url: URL de base du site
        check_interval: Intervalle entre les vérifications (secondes)
        timeout: Timeout pour chaque vérification (secondes)
    
    Returns:
        True quand le site redevient accessible (code 200)
    """
    import time
    import logging
    logger = logging.getLogger(__name__)
    
    attempt = 0
    
    while True:
        attempt += 1
        logger.info(f"Vérification de l'accessibilité du site (tentative {attempt})...")
        
        if check_site_accessible(session, base_url, timeout=timeout):
            logger.info(f"✓ Site accessible après {attempt} tentative(s)")
            return True
        
        logger.warning(f"Site non accessible, nouvelle vérification dans {check_interval} secondes...")
        time.sleep(check_interval)


def wait_for_url_accessible(session, url, check_interval=30, timeout=10):
    """
    Attend qu'une URL spécifique redevienne accessible (code 200).
    Vérifie toutes les check_interval secondes jusqu'à obtenir 200.
    
    Args:
        session: Session requests (avec cookies d'authentification)
        url: URL spécifique à vérifier
        check_interval: Intervalle entre les vérifications (secondes)
        timeout: Timeout pour chaque vérification (secondes)
    
    Returns:
        True quand l'URL redevient accessible (code 200)
    """
    import time
    import logging
    import json
    from requests.exceptions import RequestException, Timeout, ConnectionError
    
    logger = logging.getLogger(__name__)
    
    attempt = 0
    start_time = time.time()
    max_wait_time = 300  # 5 minutes maximum (réduit de 30 minutes pour éviter les blocages)
    
    # #region agent log
    try:
        with open('/Users/jean-loup/shopify/garnier/.cursor/debug.log', 'a') as f:
            f.write(json.dumps({
                "sessionId": "debug-session",
                "runId": "run1",
                "hypothesisId": "A",
                "location": "scraper_garnier_module.py:wait_for_url_accessible:ENTRY",
                "message": "wait_for_url_accessible called",
                "data": {"url": url, "check_interval": check_interval, "timeout": timeout},
                "timestamp": int(time.time() * 1000)
            }) + "\n")
    except:
        pass
    # #endregion
    
    while True:
        attempt += 1
        elapsed_time = time.time() - start_time
        
        # #region agent log
        try:
            with open('/Users/jean-loup/shopify/garnier/.cursor/debug.log', 'a') as f:
                f.write(json.dumps({
                    "sessionId": "debug-session",
                    "runId": "run1",
                    "hypothesisId": "A",
                    "location": "scraper_garnier_module.py:wait_for_url_accessible:LOOP",
                    "message": "wait_for_url_accessible loop iteration",
                    "data": {"attempt": attempt, "elapsed_time": elapsed_time, "max_wait_time": max_wait_time, "url": url},
                    "timestamp": int(time.time() * 1000)
                }) + "\n")
        except:
            pass
        # #endregion
        
        # Vérifier si on a dépassé le temps maximum
        if elapsed_time >= max_wait_time:
            logger.warning(f"Temps maximum d'attente ({max_wait_time}s) dépassé pour {url}")
            # #region agent log
            try:
                with open('/Users/jean-loup/shopify/garnier/.cursor/debug.log', 'a') as f:
                    f.write(json.dumps({
                        "sessionId": "debug-session",
                        "runId": "run1",
                        "hypothesisId": "A",
                        "location": "scraper_garnier_module.py:wait_for_url_accessible:TIMEOUT",
                        "message": "wait_for_url_accessible timeout exceeded",
                        "data": {"attempt": attempt, "elapsed_time": elapsed_time, "url": url},
                        "timestamp": int(time.time() * 1000)
                    }) + "\n")
            except:
                pass
            # #endregion
            return False
        
        logger.info(f"Vérification de l'accessibilité de l'URL (tentative {attempt}, {int(elapsed_time)}s écoulés): {url}")
        
        try:
            response = session.get(url, timeout=timeout, allow_redirects=True)
            
            if response.status_code == 200:
                logger.info(f"✓ URL accessible après {attempt} tentative(s) (code {response.status_code})")
                return True
            else:
                logger.warning(f"URL répond avec code {response.status_code}, nouvelle vérification dans {check_interval} secondes...")
                
        except (Timeout, ConnectionError, RequestException) as e:
            logger.warning(f"URL non accessible: {e}, nouvelle vérification dans {check_interval} secondes...")
        
        time.sleep(check_interval)


def slugify(text: str) -> str:
    """Convertit un texte en slug pour le Handle Shopify."""
    import unicodedata
    import re
    
    text = unicodedata.normalize('NFKD', text)
    text = text.encode('ascii', 'ignore').decode('ascii')
    text = re.sub(r'[^\w\s-]', '', text.lower())
    text = re.sub(r'[-\s]+', '-', text)
    return text.strip('-')

