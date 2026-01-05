#!/usr/bin/env python3
"""
Script de scraping pour extraire les produits du site B2B Garnier-Thiebaut
et générer un fichier CSV d'importation Shopify.
"""

import requests
from bs4 import BeautifulSoup
import pandas as pd
import os
import re
import time
import logging
import argparse
from urllib.parse import urljoin, urlparse
from typing import List, Dict, Optional
import unicodedata
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.common.exceptions import TimeoutException, NoSuchElementException, InvalidSessionIdException

# Configuration du logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Configuration
BASE_URL = "https://garnier-thiebaut.adsi.me"
USERNAME = "164049"
PASSWORD = "thierry"
IMAGES_DIR = "images"
OUTPUT_CSV = "shopify_import.csv"

# Headers pour simuler un navigateur
HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
    'Accept-Language': 'fr-FR,fr;q=0.9,en-US;q=0.8,en;q=0.7',
    'Accept-Encoding': 'gzip, deflate, br',
    'Connection': 'keep-alive',
    'Upgrade-Insecure-Requests': '1',
}


def slugify(text: str) -> str:
    """Convertit un texte en slug pour le Handle Shopify."""
    text = unicodedata.normalize('NFKD', text)
    text = text.encode('ascii', 'ignore').decode('ascii')
    text = re.sub(r'[^\w\s-]', '', text.lower())
    text = re.sub(r'[-\s]+', '-', text)
    return text.strip('-')


def get_selenium_driver(headless: bool = True):
    """
    Crée et retourne une instance de WebDriver Selenium.
    """
    chrome_options = Options()
    if headless:
        chrome_options.add_argument('--headless')  # Mode headless
    chrome_options.add_argument('--no-sandbox')
    chrome_options.add_argument('--disable-dev-shm-usage')
    chrome_options.add_argument('--disable-blink-features=AutomationControlled')
    chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
    chrome_options.add_experimental_option('useAutomationExtension', False)
    chrome_options.add_argument(f'user-agent={HEADERS["User-Agent"]}')
    chrome_options.add_argument('--window-size=1920,1080')  # Taille de fenêtre pour éviter les problèmes de rendu
    
    try:
        driver = webdriver.Chrome(options=chrome_options)
        return driver
    except Exception as e:
        logger.warning(f"Chrome WebDriver non disponible, utilisation de requests: {e}")
        return None


def check_and_recreate_driver(driver: Optional[webdriver.Chrome], session: requests.Session, headless: bool = True) -> tuple:
    """
    Vérifie si le driver Selenium est valide et le recrée si nécessaire.
    Retourne un tuple (driver, session) avec le driver valide.
    """
    if driver is None:
        # Pas de driver, essayer d'en créer un nouveau
        logger.info("Création d'un nouveau driver Selenium...")
        driver, session = authenticate(headless=headless)
        return driver, session
    
    try:
        # Tester si la session est valide en accédant à une propriété simple
        _ = driver.current_url
        return driver, session
    except (InvalidSessionIdException, Exception) as e:
        logger.warning(f"Session Selenium invalide détectée: {e}. Recréation du driver...")
        try:
            driver.quit()
        except:
            pass
        
        # Recréer le driver et ré-authentifier
        logger.info("Recréation du driver et ré-authentification...")
        driver, session = authenticate(headless=headless)
        return driver, session


def authenticate(headless: bool = True) -> tuple:
    """
    Authentifie l'utilisateur sur le site.
    Retourne un tuple (driver, session) où driver peut être None si Selenium n'est pas disponible.
    """
    logger.info("Authentification en cours...")
    
    # Essayer d'abord avec Selenium pour gérer le JavaScript
    driver = get_selenium_driver(headless=headless)
    
    if driver:
        try:
            driver.get(BASE_URL)
            time.sleep(3)  # Attendre le chargement de la page
            
            # Attendre que la page soit chargée
            WebDriverWait(driver, 15).until(
                EC.presence_of_element_located((By.TAG_NAME, "body"))
            )
            
            # Trouver et remplir le champ code client avec plusieurs stratégies
            code_input = None
            selectors = [
                "//input[contains(@placeholder, 'Code client')]",
                "//input[contains(@placeholder, 'email')]",
                "//input[@type='text']",
                "//input[@type='email']",
                "//input[@name='code_client']",
                "//input[@name='email']",
            ]
            
            for selector in selectors:
                try:
                    code_input = WebDriverWait(driver, 5).until(
                        EC.element_to_be_clickable((By.XPATH, selector))
                    )
                    break
                except TimeoutException:
                    continue
            
            if code_input:
                # Faire défiler jusqu'à l'élément pour s'assurer qu'il est visible
                driver.execute_script("arguments[0].scrollIntoView(true);", code_input)
                time.sleep(0.5)
                code_input.clear()
                code_input.send_keys(USERNAME)
                logger.debug("Champ code client rempli")
            else:
                raise Exception("Impossible de trouver le champ code client")
            
            # Trouver et remplir le champ mot de passe
            password_input = WebDriverWait(driver, 10).until(
                EC.element_to_be_clickable((By.XPATH, "//input[@type='password']"))
            )
            driver.execute_script("arguments[0].scrollIntoView(true);", password_input)
            time.sleep(0.5)
            password_input.clear()
            password_input.send_keys(PASSWORD)
            logger.debug("Champ mot de passe rempli")
            
            # Trouver et cliquer sur le bouton de connexion
            login_selectors = [
                "//button[contains(text(), 'Me Connecter')]",
                "//button[contains(text(), 'Connecter')]",
                "//button[@type='submit']",
                "//input[@type='submit']",
            ]
            
            login_button = None
            for selector in login_selectors:
                try:
                    login_button = WebDriverWait(driver, 5).until(
                        EC.element_to_be_clickable((By.XPATH, selector))
                    )
                    break
                except TimeoutException:
                    continue
            
            if login_button:
                driver.execute_script("arguments[0].scrollIntoView(true);", login_button)
                time.sleep(0.5)
                # Essayer de cliquer avec JavaScript si le clic normal échoue
                try:
                    login_button.click()
                except:
                    driver.execute_script("arguments[0].click();", login_button)
                logger.debug("Bouton de connexion cliqué")
            else:
                raise Exception("Impossible de trouver le bouton de connexion")
            
            # Attendre la redirection ou le chargement de la page suivante
            time.sleep(5)
            
            # Vérifier si la connexion a réussi
            current_url = driver.current_url
            page_source = driver.page_source.lower()
            
            # Vérifier plusieurs indicateurs de succès
            success_indicators = [
                'catalogue' in page_source,
                'produit' in page_source,
                'déconnexion' in page_source,
                'logout' in page_source,
                current_url != BASE_URL,
                '/products/' in current_url,
            ]
            
            if any(success_indicators):
                logger.info("Authentification réussie avec Selenium!")
                # Récupérer les cookies pour les utiliser avec requests
                cookies = driver.get_cookies()
                session = requests.Session()
                session.headers.update(HEADERS)
                for cookie in cookies:
                    session.cookies.set(cookie['name'], cookie['value'])
                return (driver, session)
            else:
                logger.warning("Authentification peut-être échouée avec Selenium")
                logger.debug(f"URL actuelle: {current_url}")
                logger.debug(f"Indicateurs de succès: {success_indicators}")
                
        except Exception as e:
            logger.warning(f"Erreur avec Selenium, basculement vers requests: {e}")
            if driver:
                driver.quit()
            driver = None
    
    # Fallback vers requests si Selenium n'est pas disponible ou a échoué
    session = requests.Session()
    session.headers.update(HEADERS)
    
    try:
        response = session.get(BASE_URL, timeout=30)
        response.raise_for_status()
        soup = BeautifulSoup(response.content, 'html.parser')
        
        # Préparer les données de connexion
        login_data = {
            'code_client': USERNAME,
            'password': PASSWORD,
        }
        
        # Chercher tous les champs cachés
        hidden_inputs = soup.find_all('input', type='hidden')
        for hidden in hidden_inputs:
            if hidden.get('name'):
                login_data[hidden['name']] = hidden.get('value', '')
        
        # Essayer de se connecter
        response = session.post(BASE_URL, data=login_data, timeout=30, allow_redirects=True)
        logger.info("Tentative d'authentification avec requests effectuée")
        
    except Exception as e:
        logger.error(f"Erreur lors de l'authentification: {e}")
    
    return (driver, session)


def get_categories(driver: Optional[webdriver.Chrome], session: requests.Session) -> List[Dict[str, str]]:
    """
    Extrait les catégories du menu Catalogue.
    """
    logger.info("Extraction des catégories...")
    categories = []
    
    # Catégories connues avec leurs codes
    known_categories = {
        "Linge de table": "A1",
        "Linge de lit": "A2",
        "Linge de bain": "A3",
        "Accessoire": "A4",
        "Linge d'office": "A5",
        "Literie": "A6",
        "Linge enfant": "A7",
        "Décoration": "A8",
        "Homewear": "A9",
        "Non reconduit": "A10"
    }
    
    try:
        if driver:
            # Utiliser Selenium pour obtenir le HTML rendu par JavaScript
            driver.get(BASE_URL)
            time.sleep(3)  # Attendre un peu plus pour le chargement JavaScript
            html = driver.page_source
            soup = BeautifulSoup(html, 'html.parser')
        else:
            response = session.get(BASE_URL, timeout=30)
            response.raise_for_status()
            soup = BeautifulSoup(response.content, 'html.parser')
        
        # Chercher le menu Catalogue - les catégories sont dans une liste
        # Format observé: "Linge de table", "Linge de lit", etc. dans des liens
        catalogue_menu = soup.find('a', string=re.compile(r'Catalogue', re.I))
        
        found_in_html = {}
        
        if catalogue_menu:
            # Chercher le parent qui contient la liste des catégories
            parent = catalogue_menu.find_parent()
            max_depth = 10  # Limiter la profondeur de recherche
            depth = 0
            
            while parent and depth < max_depth:
                # Chercher toutes les listes (ul) dans le parent
                category_lists = parent.find_all('ul', recursive=False)
                for category_list in category_lists:
                    category_links = category_list.find_all('a', href=True)
                    for link in category_links:
                        text = link.get_text(strip=True)
                        href = link.get('href', '')
                        
                        # Ignorer le lien "Catalogue" et les liens vides
                        if text and text.lower() != 'catalogue' and href and len(text) > 2:
                            # Vérifier si c'est une catégorie connue
                            for cat_name in known_categories.keys():
                                if cat_name.lower() in text.lower() or text.lower() in cat_name.lower():
                                    category_url = urljoin(BASE_URL, href)
                                    found_in_html[cat_name] = category_url
                                    break
                
                # Chercher aussi dans les éléments li
                list_items = parent.find_all('li', recursive=False)
                for li in list_items:
                    link = li.find('a', href=True)
                    if link:
                        text = link.get_text(strip=True)
                        href = link.get('href', '')
                        if text and text.lower() != 'catalogue' and href:
                            for cat_name in known_categories.keys():
                                if cat_name.lower() in text.lower() or text.lower() in cat_name.lower():
                                    category_url = urljoin(BASE_URL, href)
                                    found_in_html[cat_name] = category_url
                                    break
                
                parent = parent.find_parent()
                depth += 1
        
        # Construire la liste finale : utiliser les URLs trouvées dans le HTML si disponibles,
        # sinon construire les URLs avec les codes connus
        for cat_name, cat_code in known_categories.items():
            if cat_name in found_in_html:
                # Utiliser l'URL trouvée dans le HTML
                categories.append({
                    'name': cat_name,
                    'url': found_in_html[cat_name]
                })
            else:
                # Construire l'URL basée sur le code connu
                category_url = f"{BASE_URL}/products/{cat_code},/"
                categories.append({
                    'name': cat_name,
                    'url': category_url
                })
        
        logger.info(f"{len(categories)} catégories trouvées")
        if found_in_html:
            logger.info(f"URLs trouvées dans le HTML pour {len(found_in_html)} catégorie(s)")
        
        return categories
        
    except Exception as e:
        logger.error(f"Erreur lors de l'extraction des catégories: {e}")
        # En cas d'erreur, retourner les catégories connues avec URLs construites
        logger.info("Utilisation des catégories connues par défaut...")
        categories = []
        for cat_name, cat_code in known_categories.items():
            category_url = f"{BASE_URL}/products/{cat_code},/"
            categories.append({
                'name': cat_name,
                'url': category_url
            })
        return categories


def get_gammes_from_category(driver: Optional[webdriver.Chrome], session: requests.Session, category_url: str) -> List[Dict[str, str]]:
    """
    Extrait les gammes (cartes) d'une catégorie.
    Retourne la liste des URLs des gammes.
    """
    logger.info(f"Extraction des gammes de la catégorie...")
    gammes = []
    
    try:
        if not driver:
            logger.error("Selenium driver requis pour naviguer entre les pages")
            return []
        
        driver.get(category_url)
        time.sleep(5)  # Attendre le chargement JavaScript
        
        # Faire défiler la page pour charger les cartes dynamiquement
        try:
            last_height = driver.execute_script("return document.body.scrollHeight")
            scroll_pause_time = 2
            
            while True:
                driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
                time.sleep(scroll_pause_time)
                new_height = driver.execute_script("return document.body.scrollHeight")
                if new_height == last_height:
                    break
                last_height = new_height
            
            driver.execute_script("window.scrollTo(0, 0);")
            time.sleep(2)
        except Exception as e:
            logger.debug(f"Erreur lors du défilement: {e}")
        
        html = driver.page_source
        soup = BeautifulSoup(html, 'html.parser')
        
        # Chercher les cartes de gammes (articles ou divs avec des liens)
        # Les gammes sont généralement dans des cartes cliquables
        gamme_cards = soup.find_all(['article', 'div'], class_=re.compile(r'card|gamme|product|item', re.I))
        logger.debug(f"Nombre de cartes trouvées: {len(gamme_cards)}")
        
        # Chercher les liens dans ces cartes
        seen_urls = set()
        for card in gamme_cards:
            links = card.find_all('a', href=True)
            for link in links:
                href = link.get('href', '')
                # Les gammes ne doivent PAS avoir code_vl dans l'URL
                if href and 'code_vl' not in href and href not in seen_urls:
                    gamme_url = urljoin(BASE_URL, href)
                    gamme_name = link.get_text(strip=True) or card.get_text(strip=True)[:50]
                    
                    # Vérifier que ce n'est pas un lien de navigation ou autre
                    if '/products/' in href or '/product/' in href:
                        gammes.append({
                            'name': gamme_name,
                            'url': gamme_url
                        })
                        seen_urls.add(href)
        
        logger.info(f"{len(gammes)} gamme(s) trouvée(s)")
        return gammes
        
    except Exception as e:
        logger.error(f"Erreur lors de l'extraction des gammes: {e}")
        return []


def get_products_from_gamme(driver: Optional[webdriver.Chrome], session: requests.Session, gamme_url: str, headless: bool = True) -> List[Dict[str, str]]:
    """
    Extrait les produits d'une gamme en cliquant sur la carte gamme.
    """
    products = []
    
    try:
        if not driver:
            return []
        
        # Vérifier et recréer le driver si nécessaire
        driver, session = check_and_recreate_driver(driver, session, headless=headless)
        
        logger.debug(f"Chargement de la gamme: {gamme_url}")
        try:
            driver.get(gamme_url)
        except InvalidSessionIdException:
            logger.warning("Session invalide lors du chargement de la gamme, recréation...")
            driver, session = check_and_recreate_driver(None, session, headless=headless)
            driver.get(gamme_url)
        time.sleep(5)  # Attendre le chargement
        
        # Faire défiler pour charger les produits
        try:
            last_height = driver.execute_script("return document.body.scrollHeight")
            scroll_pause_time = 2
            
            while True:
                driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
                time.sleep(scroll_pause_time)
                new_height = driver.execute_script("return document.body.scrollHeight")
                if new_height == last_height:
                    break
                last_height = new_height
            
            driver.execute_script("window.scrollTo(0, 0);")
            time.sleep(2)
        except Exception as e:
            logger.debug(f"Erreur lors du défilement: {e}")
        
        html = driver.page_source
        soup = BeautifulSoup(html, 'html.parser')
        
        # Chercher les liens vers les fiches produits avec code_vl
        all_links = soup.find_all('a', href=True)
        logger.debug(f"Nombre de liens trouvés dans la gamme: {len(all_links)}")
        
        # Utiliser un set pour dédupliquer les produits par code_vl
        seen_product_codes = set()
        
        for link in all_links:
            href = link.get('href', '')
            # Chercher les liens avec /product-page/ et code_vl
            if '/product-page/' in href and 'code_vl=' in href:
                code_vl_match = re.search(r'code_vl=(\d+)', href)
                if code_vl_match:
                    product_code = code_vl_match.group(1)
                    
                    # Ignorer si on a déjà vu ce code_vl
                    if product_code in seen_product_codes:
                        logger.debug(f"Produit {product_code} déjà traité, ignoré")
                        continue
                    
                    seen_product_codes.add(product_code)
                    product_url = urljoin(BASE_URL, href)
                    product_name = link.get_text(strip=True) or f"Produit {product_code}"
                    
                    # Chercher l'image
                    parent = link.find_parent()
                    image_url = None
                    search_parent = parent
                    for _ in range(5):
                        if not search_parent:
                            break
                        img = search_parent.find('img')
                        if img:
                            image_url = img.get('src') or img.get('data-src') or img.get('data-lazy-src')
                            if image_url:
                                image_url = urljoin(BASE_URL, image_url)
                                break
                        search_parent = search_parent.find_parent() if hasattr(search_parent, 'find_parent') else None
                    
                    products.append({
                        'name': product_name,
                        'url': product_url,
                        'image_url': image_url,
                        'code': product_code
                    })
        
        logger.debug(f"{len(products)} produit(s) unique(s) trouvé(s) dans cette gamme (après déduplication)")
        return products
        
    except Exception as e:
        logger.error(f"Erreur lors de l'extraction des produits de la gamme: {e}")
        return []


def get_products_from_category(driver: Optional[webdriver.Chrome], session: requests.Session, category_url: str, category_name: str) -> List[Dict[str, str]]:
    """
    Extrait la liste des produits d'une catégorie en naviguant: catégorie → gammes → produits.
    """
    logger.info(f"Extraction des produits de la catégorie: {category_name}")
    all_products = []
    
    try:
        if not driver:
            logger.error("Selenium driver requis pour naviguer entre les pages")
            return []
        
        # Étape 1: Extraire les gammes de la catégorie
        gammes = get_gammes_from_category(driver, session, category_url)
        
        if not gammes:
            logger.warning(f"Aucune gamme trouvée dans la catégorie {category_name}")
            return []
        
        # Étape 2: Pour chaque gamme, extraire les produits
        for idx, gamme in enumerate(gammes, 1):
            logger.info(f"Traitement de la gamme {idx}/{len(gammes)}: {gamme['name']}")
            # Vérifier et recréer le driver si nécessaire avant chaque gamme
            driver, session = check_and_recreate_driver(driver, session, headless=True)
            products = get_products_from_gamme(driver, session, gamme['url'], headless=True)
            
            # Ajouter la catégorie à chaque produit
            for product in products:
                product['category'] = category_name
                all_products.append(product)
            
            # Petite pause entre les gammes
            time.sleep(1)
        
        logger.info(f"Total: {len(all_products)} produit(s) trouvé(s) dans {len(gammes)} gamme(s)")
        return all_products
        
    except Exception as e:
        logger.error(f"Erreur lors de l'extraction des produits de {category_name}: {e}")
        return []


def get_product_details(driver: Optional[webdriver.Chrome], session: requests.Session, product_url: str, product_name: str, headless: bool = True) -> tuple:
    """
    Extrait les détails complets d'un produit depuis sa fiche.
    Retourne un tuple (details_dict, driver, session) où details_dict peut être None en cas d'erreur.
    """
    """
    Extrait les détails complets d'un produit depuis sa fiche.
    Structure attendue: URL avec ?code_vl=<numero>, h2 avec "Article <numero>", tableau avec attributs.
    """
    try:
        if driver:
            # Vérifier et recréer le driver si nécessaire avant d'accéder à la page
            driver, session = check_and_recreate_driver(driver, session, headless=headless)
            
            try:
                driver.get(product_url)
                time.sleep(3)  # Attendre le chargement JavaScript
                html = driver.page_source
                soup = BeautifulSoup(html, 'html.parser')
            except InvalidSessionIdException as e:
                logger.warning(f"Session invalide lors de l'accès à {product_url}, recréation...")
                driver, session = check_and_recreate_driver(None, session, headless=headless)
                driver.get(product_url)
                time.sleep(3)
                html = driver.page_source
                soup = BeautifulSoup(html, 'html.parser')
        else:
            response = session.get(product_url, timeout=30)
            response.raise_for_status()
            soup = BeautifulSoup(response.content, 'html.parser')
        
        # Extraire le code article depuis l'URL (?code_vl=<numero>)
        code_vl_match = re.search(r'\?code_vl=(\d+)', product_url)
        product_code = code_vl_match.group(1) if code_vl_match else ""
        
        # Si pas trouvé dans l'URL, chercher dans le h2 "Article <numero>"
        if not product_code:
            h2_elem = soup.find('h2', string=re.compile(r'Article\s+(\d+)', re.I))
            if h2_elem:
                article_match = re.search(r'Article\s+(\d+)', h2_elem.get_text(), re.I)
                if article_match:
                    product_code = article_match.group(1)
        
        # Si toujours pas trouvé, essayer depuis le nom du produit
        if not product_code:
            code_match = re.search(r'^(\d+)', product_name)
            product_code = code_match.group(1) if code_match else ""
        
        # Extraire le nom du produit depuis le h4 "Détail de l'article <NOM>"
        product_name_from_page = ""
        h4_elem = soup.find('h4', string=re.compile(r'Détail de l\'article', re.I))
        if h4_elem:
            h4_text = h4_elem.get_text(strip=True)
            # Extraire le nom après "Détail de l'article "
            name_match = re.search(r'Détail de l\'article\s+(.+)', h4_text, re.I)
            if name_match:
                product_name_from_page = name_match.group(1).strip()
        
        # Utiliser le nom de la page ou celui fourni
        name_without_code = product_name_from_page if product_name_from_page else re.sub(r'^\d+\s*-\s*', '', product_name).strip()
        full_name = product_name_from_page if product_name_from_page else product_name
        
        # Chercher la description dans le paragraphe après le h4
        description = ""
        if h4_elem:
            # Chercher le paragraphe suivant
            next_p = h4_elem.find_next('p')
            if next_p:
                description = next_p.get_text(strip=True)
        
        # NOUVELLE APPROCHE : Extraire tous les code_vl du dropdown, puis traiter chaque variant
        variants = []
        
        # Étape 1 : Chercher le dropdown avec les variants
        code_vl_select = soup.find('select', id='code_vl_select')
        all_code_vl = []  # Array pour stocker tous les code_vl
        
        if code_vl_select:
            options = code_vl_select.find_all('option')
            logger.debug(f"Dropdown code_vl_select trouvé avec {len(options)} option(s)")
            
            for option in options:
                value = option.get('value', '')
                text = option.get_text(strip=True)
                
                # Extraire le code_vl depuis value="code_vl=51312"
                code_match = re.search(r'code_vl=(\d+)', value)
                if code_match:
                    variant_code = code_match.group(1)
                    all_code_vl.append({
                        'code': variant_code,
                        'size_text': text  # Le texte de l'option (ex: "115 X 115")
                    })
                    logger.debug(f"Code_vl trouvé: {variant_code} (taille: {text})")
        else:
            # Si pas de dropdown, utiliser le code_vl de la page actuelle
            logger.debug("Aucun dropdown trouvé, utilisation du code_vl de la page actuelle")
            all_code_vl.append({
                'code': product_code,
                'size_text': ''
            })
        
        logger.info(f"Total de {len(all_code_vl)} variant(s) à traiter pour le produit {product_code}")
        
        # Étape 2 : Pour chaque code_vl, aller sur sa page et capturer les infos
        base_url_without_params = product_url.split('?')[0]
        
        for idx, variant_info in enumerate(all_code_vl, 1):
            variant_code = variant_info['code']
            variant_size_text = variant_info['size_text']
            variant_url = f"{base_url_without_params}?code_vl={variant_code}"
            
            logger.debug(f"Traitement du variant {idx}/{len(all_code_vl)}: code_vl={variant_code}")
            
            # Aller sur la page du variant pour récupérer ses infos spécifiques
            if driver:
                try:
                    # Vérifier et recréer le driver si nécessaire
                    driver, session = check_and_recreate_driver(driver, session, headless=headless)
                    
                    try:
                        driver.get(variant_url)
                        time.sleep(2)  # Attendre le chargement
                        
                        variant_html = driver.page_source
                        variant_soup = BeautifulSoup(variant_html, 'html.parser')
                    except InvalidSessionIdException as e:
                        logger.warning(f"Session invalide lors de l'accès à la variante {variant_code}, recréation...")
                        driver, session = check_and_recreate_driver(None, session, headless=headless)
                        driver.get(variant_url)
                        time.sleep(2)
                        variant_html = driver.page_source
                        variant_soup = BeautifulSoup(variant_html, 'html.parser')
                    
                    # Extraire les informations de cette variante depuis le tableau
                    variant_sku = ""
                    variant_gencode = ""
                    variant_price_pa = ""
                    variant_price_pvc = ""
                    variant_stock = 0
                    variant_size = variant_size_text
                    variant_color = ""
                    variant_material = ""
                    
                    # Chercher le tableau d'attributs
                    variant_attribut_table = variant_soup.find('table', id='attribut_valeur_table')
                    if variant_attribut_table:
                        variant_rows = variant_attribut_table.find_all('tr')
                        for row in variant_rows:
                            cells = row.find_all('td')
                            if len(cells) >= 2:
                                attribut = cells[0].get_text(strip=True)
                                valeur = cells[1].get_text(strip=True)
                                
                                if attribut == "Référence":
                                    variant_sku = valeur
                                elif attribut == "Code EAN13":
                                    variant_gencode = valeur
                                elif attribut == "Tarif client conseillé":
                                    price_match = re.search(r'([\d,]+)', valeur)
                                    if price_match:
                                        variant_price_pvc = price_match.group(1).replace(',', '.')
                                elif attribut == "Tarif distributeur":
                                    price_match = re.search(r'([\d,]+)', valeur)
                                    if price_match:
                                        variant_price_pa = price_match.group(1).replace(',', '.')
                                elif attribut == "Stock dispo":
                                    stock_match = re.search(r'(\d+)', valeur)
                                    if stock_match:
                                        variant_stock = int(stock_match.group(1))
                                elif attribut in ["Dimensions", "Taille"]:
                                    variant_size = valeur
                                elif attribut == "Couleur":
                                    variant_color = valeur
                                elif attribut == "Matière":
                                    variant_material = valeur
                    
                    # Ajouter cette variante
                    variant_data = {
                        'code': variant_code,
                        'sku': variant_sku if variant_sku else variant_code,
                        'gencode': variant_gencode,
                        'size': variant_size if variant_size else variant_size_text,
                        'full_code': variant_sku if variant_sku else variant_code,
                        'pa': variant_price_pa if variant_price_pa else None,
                        'pvc': variant_price_pvc if variant_price_pvc else None,
                        'stock': variant_stock if variant_stock > 0 else None,
                        'color': variant_color,
                        'material': variant_material,
                        'url': variant_url,
                    }
                    variants.append(variant_data)
                    logger.debug(f"Variant {variant_code} ajouté avec succès")
                    
                except Exception as e:
                    logger.warning(f"Erreur lors de l'extraction de la variante {variant_code}: {e}")
                    # En cas d'erreur, créer quand même une variante avec les infos de base
                    variant_data = {
                        'code': variant_code,
                        'sku': variant_code,
                        'gencode': '',
                        'size': variant_size_text,
                        'full_code': variant_code,
                        'pa': None,
                        'pvc': None,
                        'stock': None,
                        'color': '',
                        'material': '',
                        'url': variant_url,
                    }
                    variants.append(variant_data)
            else:
                # Si pas de driver, créer une variante avec les infos de base
                logger.warning(f"Driver non disponible, création d'une variante basique pour {variant_code}")
                variant_data = {
                    'code': variant_code,
                    'sku': variant_code,
                    'gencode': '',
                    'size': variant_size_text,
                    'full_code': variant_code,
                    'pa': None,
                    'pvc': None,
                    'stock': None,
                    'color': '',
                    'material': '',
                    'url': variant_url,
                }
                variants.append(variant_data)
        
        logger.info(f"Total de {len(variants)} variant(s) extrait(s) pour le produit {product_code}")
        
        # Extraire UNIQUEMENT les images de la fiche produit (page d'article)
        # Exclure product-default.jpg et utiliser le nom de l'article pour nommer
        images = []
        
        # Image principale depuis <img name="imgzoom"> (sur la page d'article)
        imgzoom = soup.find('img', {'name': 'imgzoom'})
        if imgzoom:
            img_src = imgzoom.get('src')
            if img_src and 'product-default.jpg' not in img_src:
                image_url = urljoin(BASE_URL, img_src)
                images.append(image_url)
        
        # Chercher toutes les images dans la page produit uniquement
        # Filtrer pour ne garder que celles dans /media/GTB/IMG/ et exclure product-default.jpg
        img_tags = soup.find_all('img')
        for img in img_tags:
            src = img.get('src') or img.get('data-src') or img.get('data-lazy-src')
            if src:
                # Vérifier que c'est une image du produit (dans /media/GTB/IMG/)
                # ET que ce n'est pas product-default.jpg
                if '/media/GTB/IMG/' in src and 'product-default.jpg' not in src:
                    image_url = urljoin(BASE_URL, src)
                    # Vérifier que l'URL n'est pas déjà dans la liste
                    if image_url not in images:
                        images.append(image_url)
        
        # Chercher aussi dans les galeries d'images de la page produit
        gallery_images = soup.find_all(['div', 'ul'], class_=re.compile(r'gallery|thumb|image', re.I))
        for gallery in gallery_images:
            gallery_imgs = gallery.find_all('img')
            for img in gallery_imgs:
                src = img.get('src') or img.get('data-src') or img.get('data-lazy-src')
                if src and '/media/GTB/IMG/' in src and 'product-default.jpg' not in src:
                    image_url = urljoin(BASE_URL, src)
                    if image_url not in images:
                        images.append(image_url)
        
        logger.debug(f"{len(images)} image(s) trouvée(s) pour le produit {product_code} (nom: {full_name})")
        
        # Récupérer le SKU et gencode depuis le premier variant (ou valeurs par défaut)
        product_sku = product_code
        product_gencode = ""
        if variants:
            # Utiliser les valeurs du premier variant comme valeurs par défaut du produit
            product_sku = variants[0].get('sku', product_code)
            product_gencode = variants[0].get('gencode', '')
        
        details = {
            'code': product_code,
            'name': name_without_code,
            'full_name': full_name,
            'description': description,
            'variants': variants,
            'images': images,
            'url': product_url,
            'sku': product_sku,
            'gencode': product_gencode
        }
        
        return (details, driver, session)
        
    except Exception as e:
        logger.error(f"Erreur lors de l'extraction des détails du produit {product_name}: {e}", exc_info=True)
        return (None, driver, session)


def download_image(driver: Optional[webdriver.Chrome], session: requests.Session, image_url: str, product_name: str, image_index: int = 0) -> Optional[str]:
    """
    Télécharge une image et la sauvegarde localement.
    Le nom du fichier est basé sur le nom de l'article.
    Retourne le nom du fichier local.
    """
    if not image_url:
        return None
    
    try:
        # Créer le dossier images s'il n'existe pas
        os.makedirs(IMAGES_DIR, exist_ok=True)
        
        # Déterminer l'extension du fichier
        parsed_url = urlparse(image_url)
        path = parsed_url.path
        ext = os.path.splitext(path)[1] or '.jpg'
        
        # Créer le nom de fichier basé sur le nom de l'article
        # Nettoyer le nom pour qu'il soit valide comme nom de fichier
        safe_name = slugify(product_name)
        if image_index > 0:
            filename = f"{safe_name}_{image_index}{ext}"
        else:
            filename = f"{safe_name}{ext}"
        filepath = os.path.join(IMAGES_DIR, filename)
        
        # Télécharger l'image
        try:
            response = session.get(image_url, timeout=30, stream=True)
            response.raise_for_status()
            
            # Sauvegarder l'image
            with open(filepath, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)
        except Exception as e:
            logger.debug(f"Erreur lors du téléchargement de {image_url}: {e}")
            # Essayer avec le driver si disponible
            if driver:
                try:
                    driver.get(image_url)
                    # Sauvegarder le screenshot (fallback)
                    driver.save_screenshot(filepath)
                except:
                    return None
            else:
                return None
        
        logger.debug(f"Image téléchargée: {filename}")
        return filename
        
    except Exception as e:
        logger.warning(f"Erreur lors du téléchargement de l'image {image_url}: {e}")
        return None


def generate_shopify_csv(products_data: List[Dict]) -> pd.DataFrame:
    """
    Génère un DataFrame pandas au format CSV Shopify.
    """
    logger.info("Génération du CSV Shopify...")
    
    rows = []
    
    for product_data in products_data:
        product_details = product_data.get('details')
        if not product_details:
            continue
        
        product_code = product_details.get('code', '')
        product_name = product_details.get('name', '')
        full_name = product_details.get('full_name', product_name)
        description = product_details.get('description', '')
        category = product_data.get('category', '')
        variants = product_details.get('variants', [])
        images = product_details.get('images', [])
        
        # Créer le Handle
        handle = slugify(full_name)
        
        # Collecter les URLs des images (on garde aussi le téléchargement pour sauvegarde locale)
        image_urls = []
        driver = product_data.get('driver')
        session = product_data.get('session')
        
        # Télécharger les images localement (optionnel, pour sauvegarde)
        # Utiliser le nom de l'article pour nommer les images
        downloaded_images = []
        for idx, image_url in enumerate(images):
            # Télécharger pour sauvegarde locale avec le nom de l'article
            img_filename = download_image(
                driver,
                session,
                image_url,
                full_name,  # Utiliser le nom complet de l'article
                idx
            )
            if img_filename:
                downloaded_images.append(img_filename)
            # Garder l'URL pour le CSV
            if image_url:
                image_urls.append(image_url)
        
        # Si pas d'images trouvées depuis la fiche produit, utiliser l'image principale du produit
        if not image_urls and product_data.get('image_url'):
            # Vérifier que ce n'est pas product-default.jpg
            if 'product-default.jpg' not in product_data['image_url']:
                img_filename = download_image(
                    driver,
                    session,
                    product_data['image_url'],
                    full_name,
                    0
                )
                if img_filename:
                    downloaded_images.append(img_filename)
                image_urls.append(product_data['image_url'])
        
        # Utiliser SKU et gencode depuis les détails du produit
        product_sku = product_details.get('sku', product_code)
        product_gencode = product_details.get('gencode', '')
        
        # Créer une ligne par variante
        # Shopify format: première ligne avec toutes les infos produit et variante
        # Lignes suivantes pour les images supplémentaires (même Handle, autres champs vides sauf Image Src et Position)
        for variant_idx, variant in enumerate(variants):
            # Utiliser le SKU de la variante ou celui du produit
            variant_sku = variant.get('sku') or variant.get('full_code') or product_sku
            variant_gencode = variant.get('gencode') or product_gencode
            
            # Ligne principale avec les infos de la variante
            main_row = {
                'Handle': handle or '',
                'Title': full_name or '',
                'Body (HTML)': description or '',
                'Vendor': 'Garnier-Thiebaut',
                'Type': category,
                'Tags': category,
                'Published': 'TRUE',
                'Option1 Name': 'Taille' if variant.get('size') else '',
                'Option1 Value': variant.get('size') or '',
                'Variant SKU': variant_sku or '',
                'Variant Grams': '',
                'Variant Inventory Tracker': 'shopify',
                'Variant Inventory Qty': variant.get('stock') or 0,
                'Variant Inventory Policy': 'deny',
                'Variant Fulfillment Service': 'manual',
                'Variant Price': variant.get('pvc') or '',
                'Variant Compare At Price': variant.get('pa') or '',
                'Variant Requires Shipping': 'TRUE',
                'Variant Taxable': 'TRUE',
                'Variant Barcode': variant_gencode or '',
                'Image Src': image_urls[0] if image_urls else '',
                'Image Position': 1 if image_urls else '',
                'Image Alt Text': full_name if image_urls else '',
                'Gift Card': 'FALSE',
                'SEO Title': full_name or '',
                'SEO Description': (description[:160] if description else '') or '',
                'Google Shopping / Google Product Category': '',
                'Google Shopping / Gender': '',
                'Google Shopping / Age Group': '',
                'Google Shopping / MPN': variant.get('code') or '',
                'Google Shopping / AdWords Grouping': '',
                'Google Shopping / AdWords Labels': '',
                'Google Shopping / Condition': 'new',
                'Google Shopping / Custom Product': 'FALSE',
                'Google Shopping / Custom Label 0': '',
                'Google Shopping / Custom Label 1': '',
                'Google Shopping / Custom Label 2': '',
                'Google Shopping / Custom Label 3': '',
                'Google Shopping / Custom Label 4': '',
                'Variant Image': image_urls[0] if image_urls and variant_idx == 0 else '',
                'Variant Weight Unit': 'kg',
                'Variant Tax Code': '',
                'Cost per item': variant.get('pa') or '',
                'Status': 'active',
            }
            
            # Ajouter les images supplémentaires sur la même ligne (format Shopify compact)
            # Shopify supporte Image Src, Image Src 2, Image Src 3, etc. sur la même ligne
            for img_idx, image_url in enumerate(image_urls[1:], start=2):
                main_row[f'Image Src {img_idx}'] = image_url
                main_row[f'Image Position {img_idx}'] = img_idx
                main_row[f'Image Alt Text {img_idx}'] = full_name
            
            rows.append(main_row)
    
    # Créer le DataFrame
    df = pd.DataFrame(rows)
    
    # Remplacer tous les NaN et None par des chaînes vides pour le CSV Shopify
    df = df.fillna('')
    
    # S'assurer que toutes les valeurs None sont aussi remplacées
    df = df.replace([None, 'None', 'nan', 'NaN'], '')
    
    logger.info(f"CSV généré avec {len(df)} lignes")
    return df


def list_categories(driver: Optional[webdriver.Chrome], session: requests.Session):
    """
    Liste toutes les catégories disponibles.
    """
    logger.info("Récupération de la liste des catégories...")
    categories = get_categories(driver, session)
    
    if categories:
        print("\n=== Catégories disponibles ===")
        for idx, cat in enumerate(categories, 1):
            print(f"{idx}. {cat['name']}")
        print(f"\nTotal: {len(categories)} catégories\n")
        return categories
    else:
        logger.error("Aucune catégorie trouvée.")
        return []


def filter_categories(all_categories: List[Dict], selected_names: List[str]) -> List[Dict]:
    """
    Filtre les catégories selon les noms sélectionnés.
    """
    if not selected_names:
        return all_categories
    
    filtered = []
    selected_lower = [name.lower().strip() for name in selected_names]
    
    for cat in all_categories:
        cat_name_lower = cat['name'].lower()
        # Correspondance exacte ou partielle
        if any(selected in cat_name_lower or cat_name_lower in selected for selected in selected_lower):
            filtered.append(cat)
    
    return filtered


def main():
    """
    Fonction principale qui orchestre tout le processus.
    """
    global OUTPUT_CSV
    
    parser = argparse.ArgumentParser(
        description='Scraper pour extraire les produits du site B2B Garnier-Thiebaut et générer un CSV Shopify',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Exemples d'utilisation:
  # Extraire toutes les catégories
  python scraper.py
  
  # Extraire une catégorie spécifique
  python scraper.py --category "Linge de table"
  
  # Extraire plusieurs catégories
  python scraper.py --category "Linge de table" --category "Linge de lit"
  
  # Lister toutes les catégories disponibles
  python scraper.py --list-categories
        """
    )
    
    parser.add_argument(
        '--category', '-c',
        action='append',
        dest='categories',
        help='Nom de la catégorie à extraire (peut être utilisé plusieurs fois)'
    )
    
    parser.add_argument(
        '--list-categories', '-l',
        action='store_true',
        help='Lister toutes les catégories disponibles et quitter'
    )
    
    parser.add_argument(
        '--output', '-o',
        default=OUTPUT_CSV,
        help=f'Nom du fichier CSV de sortie (défaut: {OUTPUT_CSV})'
    )
    
    parser.add_argument(
        '--no-headless',
        action='store_true',
        help='Désactiver le mode headless de Selenium (afficher le navigateur)'
    )
    
    parser.add_argument(
        '--preview',
        action='store_true',
        help='Afficher un aperçu du DataFrame avant de sauvegarder le CSV'
    )
    
    parser.add_argument(
        '--preview-rows',
        type=int,
        default=10,
        help='Nombre de lignes à afficher dans l\'aperçu (défaut: 10)'
    )
    
    parser.add_argument(
        '--limit',
        type=int,
        default=None,
        help='Limiter le nombre de produits à extraire (utile pour les tests)'
    )
    
    args = parser.parse_args()
    
    # Modifier le nom du fichier de sortie si spécifié
    if args.output != OUTPUT_CSV:
        OUTPUT_CSV = args.output
    
    logger.info("Démarrage du scraper...")
    driver = None
    
    try:
        # 1. Authentification
        driver, session = authenticate(headless=not args.no_headless)
        
        # 2. Extraction des catégories
        all_categories = get_categories(driver, session)
        if not all_categories:
            logger.error("Aucune catégorie trouvée. Arrêt du script.")
            return
        
        # Si --list-categories, afficher et quitter
        if args.list_categories:
            list_categories(driver, session)
            return
        
        # Filtrer les catégories selon la sélection
        if args.categories:
            categories = filter_categories(all_categories, args.categories)
            if not categories:
                logger.error(f"Aucune catégorie trouvée correspondant à: {', '.join(args.categories)}")
                logger.info("Catégories disponibles:")
                for cat in all_categories:
                    logger.info(f"  - {cat['name']}")
                return
            logger.info(f"Extraction de {len(categories)} catégorie(s) sélectionnée(s)")
        else:
            categories = all_categories
            logger.info(f"Extraction de toutes les catégories ({len(categories)})")
        
        # 3. Extraction des produits
        all_products_data = []
        
        for category in categories:
            category_name = category['name']
            category_url = category['url']
            
            logger.info(f"Traitement de la catégorie: {category_name}")
            
            # Extraire les produits de la catégorie
            products = get_products_from_category(driver, session, category_url, category_name)
            
            if not products:
                logger.warning(f"Aucun produit trouvé dans la catégorie {category_name}")
                continue
            
            # Pour chaque produit, extraire les détails
            # Appliquer la limite si spécifiée
            products_to_process = products
            if args.limit and args.limit > 0:
                products_to_process = products[:args.limit]
                logger.info(f"Limite activée: traitement de {len(products_to_process)} produit(s) sur {len(products)} trouvé(s)")
            
            for idx, product in enumerate(products_to_process, 1):
                logger.info(f"Traitement du produit {idx}/{len(products_to_process)}: {product['name']}")
                
                # Extraire les détails (retourne un tuple: details, driver, session)
                details, driver, session = get_product_details(driver, session, product['url'], product['name'], headless=not args.no_headless)
                
                if details:
                    all_products_data.append({
                        'category': category_name,
                        'image_url': product.get('image_url'),
                        'details': details,
                        'session': session,
                        'driver': driver
                    })
                
                # Petite pause pour ne pas surcharger le serveur
                time.sleep(0.5)
        
        # 4. Générer le CSV
        if all_products_data:
            df = generate_shopify_csv(all_products_data)
            
            # Afficher un aperçu si demandé
            if args.preview:
                # Configuration pandas pour un meilleur affichage
                pd.set_option('display.max_columns', None)
                pd.set_option('display.max_colwidth', 50)
                pd.set_option('display.width', None)
                pd.set_option('display.max_rows', args.preview_rows)
                
                print("\n" + "="*80)
                print("📊 APERÇU DU CSV SHOPIFY")
                print("="*80)
                
                preview_rows = args.preview_rows
                
                # Informations générales
                print(f"\n📈 Informations générales:")
                print(f"   • Total de lignes (variantes): {len(df)}")
                print(f"   • Total de colonnes: {len(df.columns)}")
                print(f"   • Produits uniques: {df['Handle'].nunique()}")
                
                # Colonnes importantes à afficher en priorité
                important_cols = [
                    'Handle', 'Title', 'Variant SKU', 'Variant Price', 
                    'Variant Compare At Price', 'Variant Inventory Qty',
                    'Option1 Name', 'Option1 Value', 'Variant Barcode'
                ]
                
                # Filtrer les colonnes qui existent
                available_cols = [col for col in important_cols if col in df.columns]
                other_cols = [col for col in df.columns if col not in important_cols]
                
                # Afficher les premières lignes avec colonnes importantes
                print(f"\n📋 Premières {preview_rows} lignes (colonnes principales):")
                print("-"*80)
                preview_df = df[available_cols].head(preview_rows)
                print(preview_df.to_string(index=False))
                
                if len(df) > preview_rows:
                    print(f"\n... ({len(df) - preview_rows} lignes supplémentaires)")
                
                # Statistiques sur les colonnes numériques importantes
                print("\n" + "-"*80)
                print("📊 Statistiques (colonnes numériques):")
                print("-"*80)
                numeric_cols = df.select_dtypes(include=['int64', 'float64']).columns
                if len(numeric_cols) > 0:
                    print(df[numeric_cols].describe().to_string())
                else:
                    print("Aucune colonne numérique trouvée")
                
                # Statistiques sur les colonnes textuelles importantes
                print("\n" + "-"*80)
                print("📝 Statistiques (colonnes textuelles):")
                print("-"*80)
                text_cols = ['Handle', 'Title', 'Variant SKU', 'Option1 Value']
                available_text_cols = [col for col in text_cols if col in df.columns]
                if available_text_cols:
                    for col in available_text_cols:
                        unique_count = df[col].nunique()
                        non_empty = df[col].notna().sum()
                        print(f"   • {col}:")
                        print(f"     - Valeurs uniques: {unique_count}")
                        print(f"     - Valeurs non vides: {non_empty}/{len(df)}")
                        if unique_count > 0 and unique_count <= 10:
                            unique_vals = [str(v) for v in df[col].dropna().unique()[:10] if v]
                            if unique_vals:
                                print(f"     - Valeurs: {', '.join(unique_vals)}")
                
                # Vérification des valeurs manquantes
                print("\n" + "-"*80)
                print("⚠️  Valeurs manquantes (NaN/vides):")
                print("-"*80)
                missing = df.isnull().sum()
                missing = missing[missing > 0]
                if len(missing) > 0:
                    for col, count in missing.items():
                        percentage = (count / len(df)) * 100
                        print(f"   • {col}: {count} ({percentage:.1f}%)")
                else:
                    print("   ✓ Aucune valeur manquante détectée")
                
                # Liste de toutes les colonnes
                print("\n" + "-"*80)
                print(f"📑 Toutes les colonnes ({len(df.columns)}):")
                print("-"*80)
                cols_per_line = 3
                for i in range(0, len(df.columns), cols_per_line):
                    cols_slice = df.columns[i:i+cols_per_line]
                    print("   " + " | ".join(f"{col:30}" for col in cols_slice))
                
                print("\n" + "="*80)
                
                # Demander confirmation avant de sauvegarder
                if args.output == OUTPUT_CSV:
                    response = input(f"\nSauvegarder le CSV dans '{OUTPUT_CSV}'? (o/n): ")
                    if response.lower() not in ['o', 'oui', 'y', 'yes']:
                        logger.info("Sauvegarde annulée par l'utilisateur.")
                        return
            
            # Sauvegarder le CSV
            df.to_csv(OUTPUT_CSV, index=False, encoding='utf-8')
            logger.info(f"Fichier CSV généré: {OUTPUT_CSV}")
            logger.info(f"Total: {len(df)} lignes (variantes de produits)")
        else:
            logger.warning("Aucun produit trouvé. Aucun fichier CSV généré.")
        
        logger.info("Scraping terminé avec succès!")
        
    except Exception as e:
        logger.error(f"Erreur fatale: {e}", exc_info=True)
        raise
    finally:
        # Fermer le driver Selenium si ouvert
        if driver:
            try:
                driver.quit()
            except:
                pass


if __name__ == "__main__":
    main()

