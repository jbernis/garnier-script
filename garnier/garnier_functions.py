#!/usr/bin/env python3
"""
Module de fonctions pour le scraper Garnier-Thiebaut.
Ce module contient uniquement les fonctions réutilisables par les autres scripts.
Il n'est plus exécutable directement - utilisez les scripts collect/process/generate-csv.
"""

import requests
from bs4 import BeautifulSoup
import os
import re
import time
import logging
from urllib.parse import urljoin, urlparse, quote
from typing import List, Dict, Optional
import unicodedata
from dotenv import load_dotenv
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.common.exceptions import TimeoutException, NoSuchElementException, InvalidSessionIdException


def clean_gamme_name(gamme_name_raw: str) -> str:
    """
    Nettoie le nom de la gamme Garnier.
    
    Format d'entrée: "51469 - LOT H.COUETTE +TAIES ANNABELLE MIMOSAnewPA..."
    Format de sortie: "ANNABELLE MIMOSA"
    
    Args:
        gamme_name_raw: Nom brut de la gamme
        
    Returns:
        Nom nettoyé de la gamme
    """
    if not gamme_name_raw:
        return ""
    
    cleaned = gamme_name_raw.strip()
    
    # Étape 1: Enlever tout avant le premier " - " (code numérique)
    if ' - ' in cleaned:
        cleaned = cleaned.split(' - ', 1)[1]
    
    # Étape 2: Enlever tout à partir de "newPA", "NRPA", ou "PA" (suffixes de prix)
    # Utiliser une regex pour capturer différentes variantes
    cleaned = re.sub(r'(NR|new)?PA.*$', '', cleaned, flags=re.IGNORECASE).strip()
    
    # Étape 3: Enlever les types de produits courants au début
    product_types = [
        r'LOT H\.COUETTE \+TAIES\s+',
        r'HOUSSE DE COUETTE\s+',
        r'LOT DE 2 TAIES\s+',
        r'TAIE D\'OREILLER\s+',
        r'DRAP HOUSSE B\d+\s+',
        r'TORCHON\s+',
        r'CHEMIN DE TABLE\s+',
        r'NAPPE\s+',
        r'SERVIETTE\s+',
        r'SET DE TABLE\s+',
    ]
    
    for ptype in product_types:
        cleaned = re.sub(ptype, '', cleaned, flags=re.IGNORECASE).strip()
    
    # Étape 4: Enlever les espaces multiples
    cleaned = re.sub(r'\s+', ' ', cleaned).strip()
    
    # Étape 5: Enlever les prix résiduels (chiffres suivis de €)
    cleaned = re.sub(r'\s*[\d,.\s]+€.*$', '', cleaned).strip()
    
    return cleaned

# Logging - sera configuré par le script principal qui importe ce module
logger = logging.getLogger(__name__)

# Charger les variables d'environnement depuis .env
load_dotenv()

# Configuration
BASE_URL = os.getenv("BASE_URL_GARNIER", "https://garnier-thiebaut.adsi.me")
USERNAME = os.getenv("USERNAME", "")
PASSWORD = os.getenv("PASSWORD", "")
# Répertoire de sortie automatique basé sur le nom du fournisseur
# Peut être surchargé avec la variable d'environnement GARNIER_OUTPUT_DIR
OUTPUT_DIR = os.getenv("GARNIER_OUTPUT_DIR", "outputs/garnier")
OUTPUT_CSV = os.getenv("OUTPUT_CSV_GARNIER", "shopify_import_garnier.csv")

# Vérifier que les credentials sont définis
if not USERNAME or not PASSWORD:
    logger.error("Les credentials USERNAME et PASSWORD doivent être définis dans le fichier .env")
    logger.error("Veuillez créer un fichier .env basé sur .env.example")
    raise ValueError("Credentials manquants dans .env")

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


def get_gammes_from_category(driver: Optional[webdriver.Chrome], session: requests.Session, category_url: str, start_page: int = 1) -> List[Dict[str, str]]:
    """
    Extrait les gammes (cartes) d'une catégorie.
    Gère la pagination pour extraire toutes les gammes de toutes les pages.
    Retourne la liste des URLs des gammes.
    
    Args:
        driver: Le driver Selenium
        session: La session requests
        category_url: L'URL de la catégorie
        start_page: Numéro de page de départ (défaut: 1). Si > 1, la fonction ne recharge pas la page
                    et commence l'extraction à partir de la page actuelle.
    """
    logger.info(f"Extraction des gammes de la catégorie...")
    all_gammes = []
    page_num = start_page
    max_pages = 100  # Limite de sécurité
    seen_urls = set()
    
    try:
        if not driver:
            logger.error("Selenium driver requis pour naviguer entre les pages")
            return []
        
        # Charger la première page seulement si on commence à la page 1
        # Si start_page > 1, on suppose qu'on est déjà sur la bonne page
        if start_page == 1:
            driver.get(category_url)
            time.sleep(5)  # Attendre le chargement JavaScript
        else:
            logger.info(f"Démarrage de l'extraction à partir de la page {start_page} (page déjà chargée)")
            time.sleep(2)  # Attendre un peu pour s'assurer que la page est stable
        
        while page_num <= max_pages:
            logger.info(f"Extraction des gammes de la page {page_num}...")
            
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
            logger.debug(f"Nombre de cartes trouvées sur la page {page_num}: {len(gamme_cards)}")
            
            page_gammes = []
            # Chercher les liens dans ces cartes
            for card in gamme_cards:
                links = card.find_all('a', href=True)
                for link in links:
                    href = link.get('href', '')
                    # Les gammes ne doivent PAS avoir code_vl dans l'URL
                    if href and 'code_vl' not in href and href not in seen_urls:
                        gamme_url = urljoin(BASE_URL, href)
                        gamme_name_raw = link.get_text(strip=True) or card.get_text(strip=True)[:50]
                        
                        # Nettoyer le nom de la gamme
                        gamme_name = clean_gamme_name(gamme_name_raw)
                        
                        # Vérifier que ce n'est pas un lien de navigation ou autre
                        if '/products/' in href or '/product/' in href:
                            page_gammes.append({
                                'name': gamme_name,
                                'url': gamme_url
                            })
                            seen_urls.add(href)
            
            # Ajouter les gammes de cette page à la liste totale
            all_gammes.extend(page_gammes)
            logger.info(f"Page {page_num}: {len(page_gammes)} gamme(s) trouvée(s)")
            
            # Vérifier s'il y a une page suivante (pagination Garnier avec data-lp)
            next_page_num, next_element = get_next_page_info(driver)
            if next_element is not None:
                try:
                    # Cliquer sur le bouton de pagination pour aller à la page suivante
                    driver.execute_script("arguments[0].scrollIntoView(true);", next_element)
                    time.sleep(0.5)
                    next_element.click()
                    time.sleep(3)  # Attendre le chargement de la nouvelle page
                    page_num = next_page_num if next_page_num else page_num + 1
                    logger.info(f"Navigation vers la page {page_num}")
                except Exception as e:
                    logger.debug(f"Erreur lors du clic sur la pagination: {e}")
                    # Essayer avec JavaScript directement
                    try:
                        driver.execute_script("arguments[0].click();", next_element)
                        time.sleep(3)
                        page_num = next_page_num if next_page_num else page_num + 1
                    except Exception as e2:
                        logger.debug(f"Erreur lors du clic JavaScript: {e2}")
                        break
            else:
                # Pas de page suivante, on arrête
                break
        
        logger.info(f"Total: {len(all_gammes)} gamme(s) trouvée(s) sur {page_num} page(s)")
        return all_gammes
        
    except Exception as e:
        logger.error(f"Erreur lors de l'extraction des gammes: {e}")
        return []


def get_next_page_info(driver: webdriver.Chrome):
    """
    Détecte la pagination Garnier et retourne (numéro_page_suivante, élément_next).
    Retourne (None, None) s'il n'y a pas de page suivante.
    Garnier utilise <div id="page-selection"> avec <ul class="pagination bootpag">
    et des <li data-lp="X"> pour les numéros de page.
    
    IMPORTANT: Parcourt les pages séquentiellement (1, 2, 3, 4...) et non en sautant.
    """
    try:
        # Chercher la pagination spécifique de Garnier
        try:
            page_selection = driver.find_element(By.ID, 'page-selection')
            pagination_ul = page_selection.find_element(By.CSS_SELECTOR, 'ul.pagination.bootpag')
            
            # PRIORITÉ 1: Chercher la page active et calculer la page suivante séquentielle
            try:
                active_li = pagination_ul.find_element(By.CSS_SELECTOR, 'li.active')
                current_page = int(active_li.get_attribute('data-lp'))
                
                # Calculer la page suivante séquentielle
                next_page_num = current_page + 1
                
                # Chercher toutes les pages pour trouver la dernière
                all_pages = pagination_ul.find_elements(By.CSS_SELECTOR, 'li[data-lp]')
                max_page = current_page
                for page_li in all_pages:
                    page_num_str = page_li.get_attribute('data-lp')
                    if page_num_str:
                        try:
                            page_num = int(page_num_str)
                            max_page = max(max_page, page_num)
                        except ValueError:
                            pass
                
                # Si on n'est pas sur la dernière page, chercher le bouton de la page suivante
                if next_page_num <= max_page:
                    # Chercher le <li> avec data-lp correspondant à la page suivante
                    try:
                        next_li = pagination_ul.find_element(By.CSS_SELECTOR, f'li[data-lp="{next_page_num}"]')
                        next_link = next_li.find_element(By.TAG_NAME, 'a')
                        logger.info(f"Page actuelle: {current_page}, Page suivante: {next_page_num}")
                        return (next_page_num, next_link)
                    except NoSuchElementException:
                        # Si la page suivante n'est pas visible dans la pagination,
                        # utiliser le bouton "next" pour avancer
                        try:
                            next_li = pagination_ul.find_element(By.CSS_SELECTOR, 'li.next:not(.disabled)')
                            next_link = next_li.find_element(By.TAG_NAME, 'a')
                            logger.info(f"Page actuelle: {current_page}, Utilisation du bouton 'next' pour aller à la page {next_page_num}")
                            return (next_page_num, next_link)
                        except NoSuchElementException:
                            pass
            except NoSuchElementException:
                pass
            
            # FALLBACK: Chercher le bouton "next" si on n'a pas trouvé la page active
            try:
                next_li = pagination_ul.find_element(By.CSS_SELECTOR, 'li.next')
                # Vérifier si le bouton est désactivé
                if 'disabled' not in next_li.get_attribute('class'):
                    # Récupérer le numéro de page suivant depuis data-lp
                    next_page_num = next_li.get_attribute('data-lp')
                    if next_page_num:
                        next_page_num = int(next_page_num)
                        # Trouver l'élément <a> dans ce <li>
                        next_link = next_li.find_element(By.TAG_NAME, 'a')
                        logger.warning(f"Utilisation du bouton 'next' avec data-lp={next_page_num} (peut sauter des pages)")
                        return (next_page_num, next_link)
            except NoSuchElementException:
                pass
                
        except NoSuchElementException:
            # Pagination Garnier non trouvée, essayer les méthodes génériques
            pass
        
        # Méthodes génériques de fallback
        html = driver.page_source
        soup = BeautifulSoup(html, 'html.parser')
        
        # Chercher avec BeautifulSoup
        pagination = soup.find(['nav', 'div', 'ul'], class_=re.compile(r'pagination|pager', re.I))
        if pagination:
            next_link_elem = pagination.find('a', class_=re.compile(r'next', re.I))
            if next_link_elem:
                parent_li = next_link_elem.find_parent('li')
                if parent_li and 'disabled' not in parent_li.get('class', []):
                    # Chercher avec Selenium pour pouvoir cliquer
                    try:
                        next_link_selenium = driver.find_element(By.CSS_SELECTOR, 'a.next:not(.disabled)')
                        if next_link_selenium.is_enabled() and next_link_selenium.is_displayed():
                            return (None, next_link_selenium)  # Numéro de page inconnu mais on peut cliquer
                    except:
                        pass
        
        return (None, None)
        
    except Exception as e:
        logger.debug(f"Erreur lors de la détection de pagination: {e}")
        return (None, None)


def get_products_from_gamme(driver: Optional[webdriver.Chrome], session: requests.Session, gamme_url: str, headless: bool = True) -> List[Dict[str, str]]:
    """
    Extrait les produits d'une gamme en cliquant sur la carte gamme.
    Gère la pagination si présente.
    """
    all_products = []
    current_url = gamme_url
    page_num = 1
    max_pages = 100  # Limite de sécurité
    
    try:
        if not driver:
            return []
        
        # Vérifier et recréer le driver si nécessaire
        driver, session = check_and_recreate_driver(driver, session, headless=headless)
        
        # Utiliser un set pour dédupliquer les produits par code_vl (global pour toutes les pages)
        seen_product_codes = set()
        
        # Charger la première page
        logger.debug(f"Chargement de la gamme (page 1): {gamme_url}")
        try:
            driver.get(gamme_url)
        except InvalidSessionIdException:
            logger.warning("Session invalide lors du chargement de la gamme, recréation...")
            driver, session = check_and_recreate_driver(None, session, headless=headless)
            driver.get(gamme_url)
        time.sleep(5)  # Attendre le chargement
        
        while page_num <= max_pages:
            # #region agent log
            import json
            import time as time_module
            try:
                with open('/Users/jean-loup/shopify/garnier/.cursor/debug.log', 'a') as f:
                    f.write(json.dumps({
                        "sessionId": "debug-session",
                        "runId": "run1",
                        "hypothesisId": "C",
                        "location": "garnier_functions.py:get_products_from_gamme:PAGE_LOOP",
                        "message": "Processing page in pagination loop",
                        "data": {"page_num": page_num, "max_pages": max_pages},
                        "timestamp": int(time_module.time() * 1000)
                    }) + "\n")
            except:
                pass
            # #endregion
            
            # Vérifier et recréer le driver si nécessaire avant chaque page
            try:
                driver, session = check_and_recreate_driver(driver, session, headless=headless)
            except Exception as e:
                logger.warning(f"Erreur lors de la vérification du driver: {e}")
                driver, session = check_and_recreate_driver(None, session, headless=headless)
            
            # Faire défiler pour charger les produits
            try:
                last_height = driver.execute_script("return document.body.scrollHeight")
                scroll_pause_time = 2
                scroll_iterations = 0
                
                while True:
                    scroll_iterations += 1
                    # #region agent log
                    try:
                        with open('/Users/jean-loup/shopify/garnier/.cursor/debug.log', 'a') as f:
                            f.write(json.dumps({
                                "sessionId": "debug-session",
                                "runId": "run1",
                                "hypothesisId": "D",
                                "location": "garnier_functions.py:get_products_from_gamme:SCROLL_LOOP",
                                "message": "Scroll loop iteration",
                                "data": {"page_num": page_num, "scroll_iterations": scroll_iterations, "last_height": last_height},
                                "timestamp": int(time_module.time() * 1000)
                            }) + "\n")
                    except:
                        pass
                    # #endregion
                    
                    if scroll_iterations > 100:  # Limite de sécurité pour éviter boucle infinie
                        logger.warning(f"Limite de scroll atteinte (100 itérations) pour la page {page_num}")
                        break
                    driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
                    time.sleep(scroll_pause_time)
                    new_height = driver.execute_script("return document.body.scrollHeight")
                    if new_height == last_height:
                        # #region agent log
                        try:
                            with open('/Users/jean-loup/shopify/garnier/.cursor/debug.log', 'a') as f:
                                f.write(json.dumps({
                                    "sessionId": "debug-session",
                                    "runId": "run1",
                                    "hypothesisId": "D",
                                    "location": "garnier_functions.py:get_products_from_gamme:SCROLL_BREAK",
                                    "message": "Scroll loop break (height stable)",
                                    "data": {"page_num": page_num, "scroll_iterations": scroll_iterations, "height": new_height},
                                    "timestamp": int(time_module.time() * 1000)
                                }) + "\n")
                        except:
                            pass
                        # #endregion
                        break
                    last_height = new_height
                
                driver.execute_script("window.scrollTo(0, 0);")
                time.sleep(2)
            except InvalidSessionIdException as e:
                logger.warning(f"Session invalide lors du défilement (page {page_num}), recréation...")
                driver, session = check_and_recreate_driver(None, session, headless=headless)
                # Recharger la page actuelle
                try:
                    driver.get(gamme_url)
                    time.sleep(5)
                    # Si on était sur une page > 1, naviguer jusqu'à la page actuelle
                    if page_num > 1:
                        for p in range(2, page_num + 1):
                            next_page_num, next_element = get_next_page_info(driver)
                            if next_element:
                                driver.execute_script("arguments[0].scrollIntoView(true);", next_element)
                                time.sleep(0.5)
                                next_element.click()
                                time.sleep(3)
                    continue  # Recommencer la boucle avec la nouvelle session
                except Exception as e2:
                    logger.error(f"Impossible de recharger la page après reconnexion: {e2}")
                    break
            except Exception as e:
                logger.debug(f"Erreur lors du défilement: {e}")
            
            try:
                html = driver.page_source
                soup = BeautifulSoup(html, 'html.parser')
            except InvalidSessionIdException as e:
                logger.warning(f"Session invalide lors de l'extraction du HTML (page {page_num}), recréation...")
                driver, session = check_and_recreate_driver(None, session, headless=headless)
                # Recharger la page actuelle
                try:
                    driver.get(gamme_url)
                    time.sleep(5)
                    if page_num > 1:
                        for p in range(2, page_num + 1):
                            next_page_num, next_element = get_next_page_info(driver)
                            if next_element:
                                driver.execute_script("arguments[0].scrollIntoView(true);", next_element)
                                time.sleep(0.5)
                                next_element.click()
                                time.sleep(3)
                    continue  # Recommencer la boucle avec la nouvelle session
                except Exception as e2:
                    logger.error(f"Impossible de recharger la page après reconnexion: {e2}")
                    break
            
            # Chercher les liens vers les fiches produits avec code_vl
            all_links = soup.find_all('a', href=True)
            logger.debug(f"Nombre de liens trouvés dans la gamme (page {page_num}): {len(all_links)}")
            
            page_products = []
            
            for link in all_links:
                href = link.get('href', '')
                # Chercher les liens avec /product-page/ et code_vl
                if '/product-page/' in href and 'code_vl=' in href:
                    code_vl_match = re.search(r'code_vl=(\d+)', href)
                    if code_vl_match:
                        product_code = code_vl_match.group(1)
                        
                        # Ignorer si on a déjà vu ce code_vl (déjà dans all_products)
                        if product_code in seen_product_codes:
                            logger.debug(f"Produit {product_code} déjà traité, ignoré")
                            continue
                        
                        seen_product_codes.add(product_code)
                        product_url = urljoin(BASE_URL, href)
                        
                        # Chercher spécifiquement le <b> dans le lien pour le nom du produit
                        b_tag = link.find('b')
                        if b_tag:
                            full_text = b_tag.get_text(strip=True)
                            # Enlever le code produit au début si présent (format: "51297 - NAPPE AQUA MINERAL")
                            if full_text and ' - ' in full_text:
                                product_name = full_text.split(' - ', 1)[1]  # Prendre la partie après " - "
                            else:
                                product_name = full_text or f"Produit {product_code}"
                        else:
                            # Pas de <b>, utiliser le texte du lien ou fallback
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
                        
                        page_products.append({
                            'name': product_name,
                            'url': product_url,
                            'image_url': image_url,
                            'code': product_code
                        })
            
            # Ajouter les produits de cette page à la liste totale
            all_products.extend(page_products)
            logger.info(f"Page {page_num}: {len(page_products)} produit(s) trouvé(s)")
            
            # Vérifier s'il y a une page suivante (pagination Garnier avec data-lp)
            next_page_num, next_element = get_next_page_info(driver)
            if next_element is not None:
                try:
                    # Cliquer sur le bouton de pagination pour aller à la page suivante
                    driver.execute_script("arguments[0].scrollIntoView(true);", next_element)
                    time.sleep(0.5)
                    next_element.click()
                    time.sleep(3)  # Attendre le chargement de la nouvelle page
                    page_num = next_page_num if next_page_num else page_num + 1
                    logger.info(f"Navigation vers la page {page_num}")
                except Exception as e:
                    logger.debug(f"Erreur lors du clic sur la pagination: {e}")
                    # Essayer avec JavaScript directement
                    try:
                        driver.execute_script("arguments[0].click();", next_element)
                        time.sleep(3)
                        page_num = next_page_num if next_page_num else page_num + 1
                    except Exception as e2:
                        logger.debug(f"Erreur lors du clic JavaScript: {e2}")
                        break
            else:
                # Pas de page suivante, on arrête
                break
        
        logger.info(f"Total: {len(all_products)} produit(s) trouvé(s) sur {page_num} page(s)")
        return all_products
        
    except Exception as e:
        logger.error(f"Erreur lors de l'extraction des produits de la gamme: {e}")
        return []


def extract_product_images(driver, session, product_url, headless=True):
    """
    Extrait toutes les URLs d'images d'un produit Garnier depuis sa page produit.
    Les images sont dans <div id="product-carousel"> avec name="imgzoom".
    Exclut les images product-default.jpg.
    
    Args:
        driver: WebDriver Selenium
        session: Session requests
        product_url: URL de la page produit (avec code_vl)
        headless: Mode headless
    
    Returns:
        Liste d'URLs d'images (liste vide si aucune image trouvée)
    """
    from bs4 import BeautifulSoup
    from urllib.parse import urljoin
    import time
    import logging
    
    logger = logging.getLogger(__name__)
    
    images = []
    
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
        
        # Chercher le div product-carousel
        product_carousel = soup.find('div', id='product-carousel')
        if product_carousel:
            # Chercher toutes les images avec name="imgzoom"
            img_tags = product_carousel.find_all('img', {'name': 'imgzoom'})
            
            for img in img_tags:
                src = img.get('src')
                if src:
                    # Exclure les images product-default.jpg
                    if 'product-default.jpg' not in src:
                        # Construire l'URL complète
                        if src.startswith('http'):
                            image_url = src
                        else:
                            image_url = urljoin(BASE_URL, src)
                        
                        if image_url not in images:
                            images.append(image_url)
            
            logger.debug(f"    {len(images)} image(s) trouvée(s) dans product-carousel")
        else:
            logger.debug(f"    div#product-carousel non trouvé pour {product_url}")
        
        return images
        
    except Exception as e:
        logger.warning(f"    Erreur lors de l'extraction des images: {e}")
        return []


def extract_product_is_new(driver, session, product_url, headless=True):
    """
    Extrait le statut "new" d'un produit depuis sa page produit.
    Cherche <div class="product-labels"> avec <span class="label label-info">new</span>
    
    Args:
        driver: WebDriver Selenium
        session: Session requests
        product_url: URL de la page produit
        headless: Mode headless
    
    Returns:
        True si le produit a le label "new", False sinon
    """
    from bs4 import BeautifulSoup
    import time
    import logging
    
    logger = logging.getLogger(__name__)
    
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
        
        # Chercher le div product-labels
        product_labels = soup.find('div', class_='product-labels')
        if product_labels:
            # Chercher tous les spans avec class="label"
            label_spans = product_labels.find_all('span', class_='label')
            for span in label_spans:
                label_text = span.get_text(strip=True).lower()
                if label_text == 'new':
                    logger.debug(f"    ✓ Label 'new' trouvé pour le produit")
                    return True
        
        return False
        
    except Exception as e:
        logger.warning(f"    Erreur lors de l'extraction du label 'new': {e}")
        return False
