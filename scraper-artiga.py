#!/usr/bin/env python3
"""
Script de scraping pour extraire les produits du site Artiga (https://www.artiga.fr/)
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
import json
from urllib.parse import urljoin, urlparse
from typing import List, Dict, Optional
import unicodedata
from datetime import datetime
from dotenv import load_dotenv
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait, Select
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.common.exceptions import TimeoutException, NoSuchElementException, InvalidSessionIdException
from csv_config import get_csv_config

# Logging - sera configuré par le script principal qui importe ce module
logger = logging.getLogger(__name__)

# Charger les variables d'environnement depuis .env
load_dotenv()

# Configuration Artiga
BASE_URL = os.getenv("ARTIGA_BASE_URL", "https://www.artiga.fr")
# Répertoire de sortie automatique basé sur le nom du fournisseur
# Peut être surchargé avec la variable d'environnement ARTIGA_OUTPUT_DIR
OUTPUT_DIR = os.getenv("ARTIGA_OUTPUT_DIR", "outputs/artiga")
OUTPUT_CSV = os.getenv("ARTIGA_OUTPUT_CSV", "shopify_import_artiga.csv")

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
    Crée et retourne une instance de WebDriver Selenium avec logs de performance activés.
    """
    chrome_options = Options()
    if headless:
        chrome_options.add_argument('--headless')
    chrome_options.add_argument('--no-sandbox')
    chrome_options.add_argument('--disable-dev-shm-usage')
    chrome_options.add_argument('--disable-blink-features=AutomationControlled')
    chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
    chrome_options.add_experimental_option('useAutomationExtension', False)
    chrome_options.add_argument(f'user-agent={HEADERS["User-Agent"]}')
    chrome_options.add_argument('--window-size=1920,1080')
    
    # Activer les logs de performance pour capturer les requêtes AJAX
    chrome_options.set_capability('goog:loggingPrefs', {'performance': 'ALL'})
    
    try:
        # Essayer avec webdriver-manager si disponible
        try:
            from webdriver_manager.chrome import ChromeDriverManager
            service = Service(ChromeDriverManager().install())
            driver = webdriver.Chrome(service=service, options=chrome_options)
            return driver
        except ImportError:
            # Fallback sur Chrome standard si webdriver-manager n'est pas disponible
            driver = webdriver.Chrome(options=chrome_options)
            return driver
    except Exception as e:
        logger.warning(f"Chrome WebDriver non disponible: {e}")
        return None


def extract_price_from_ajax_response(response_text: str) -> Optional[str]:
    """
    Extrait le prix depuis la réponse AJAX.
    """
    try:
        # Essayer d'extraire depuis le JSON
        data = json.loads(response_text)
        
        # Option 1: Extraire depuis product_prices (HTML)
        if 'product_prices' in data:
            prices_html = data['product_prices']
            # Extraire le prix avec une expression régulière
            price_match = re.search(r'<span class="display-4 current-price-display price">\s*([^<]+)\s*<\/span>', prices_html)
            if price_match:
                return price_match.group(1).strip()
        
        # Option 2: Extraire depuis price_amount
        if 'price_amount' in data:
            return f"{data['price_amount']},00 €"
        
        # Option 3: Extraire depuis attribute_price
        if 'attribute_price' in data:
            return f"{data['attribute_price']},00 €"
        
    except json.JSONDecodeError:
        # Si ce n'est pas du JSON valide, essayer d'extraire directement
        price_match = re.search(r'<span class="display-4 current-price-display price">\s*([^<]+)\s*<\/span>', response_text)
        if price_match:
            return price_match.group(1).strip()
    
    return None


def get_ajax_price_updates(driver: webdriver.Chrome) -> Dict:
    """
    Récupère les mises à jour de prix depuis les logs de performance (requêtes AJAX).
    """
    price_updates = {}
    
    try:
        # Récupérer les logs de performance
        logs = driver.get_log('performance')
        
        for log in logs:
            try:
                # Analyser le log
                log_data = json.loads(log['message'])['message']
                
                # Vérifier si c'est une réponse de requête réseau
                if log_data['method'] == 'Network.responseReceived':
                    request_id = log_data['params']['requestId']
                    response_url = log_data['params']['response']['url']
                    
                    # Vérifier si l'URL contient des indices qu'il s'agit d'une requête de produit
                    if 'controller=product' in response_url or 'ajax' in response_url.lower() or 'product' in response_url.lower():
                        try:
                            # Récupérer le corps de la réponse
                            response = driver.execute_cdp_cmd('Network.getResponseBody', {'requestId': request_id})
                            
                            # Extraire le prix de la réponse
                            price = extract_price_from_ajax_response(response['body'])
                            if price:
                                # Utiliser l'URL ou un timestamp comme clé
                                timestamp = log_data['params']['timestamp']
                                price_updates[timestamp] = {
                                    'url': response_url,
                                    'price': price,
                                    'response': response['body']
                                }
                        except Exception as e:
                            # Ignorer les erreurs de récupération du corps de la réponse
                            logger.debug(f"Erreur lors de la récupération de la réponse AJAX: {e}")
                            continue
                            
            except Exception as e:
                # Ignorer les erreurs de parsing
                continue
                
    except Exception as e:
        logger.debug(f"Erreur lors de la récupération des logs: {e}")
    
    return price_updates


def check_and_recreate_driver(driver: Optional[webdriver.Chrome], session: requests.Session, headless: bool = True) -> tuple:
    """
    Vérifie si le driver Selenium est valide et le recrée si nécessaire.
    """
    if driver is None:
        logger.info("Création d'un nouveau driver Selenium...")
        driver = get_selenium_driver(headless=headless)
        session = requests.Session()
        session.headers.update(HEADERS)
        return driver, session
    
    try:
        _ = driver.current_url
        return driver, session
    except (InvalidSessionIdException, Exception) as e:
        logger.warning(f"Session Selenium invalide détectée: {e}. Recréation du driver...")
        try:
            driver.quit()
        except:
            pass
        
        driver = get_selenium_driver(headless=headless)
        session = requests.Session()
        session.headers.update(HEADERS)
        return driver, session


def get_categories(driver: Optional[webdriver.Chrome], session: requests.Session) -> List[Dict[str, str]]:
    """
    Extrait les catégories principales depuis le menu de navigation du site Artiga.
    Les catégories principales sont dans <ul id="menu"> avec <li class="li-niveau1 advtm_menu_X">
    et <a class="a-niveau1" data-type="category">.
    """
    logger.info("Extraction des catégories principales depuis Artiga...")
    categories = []
    
    try:
        if driver:
            driver.get(BASE_URL)
            time.sleep(5)  # Attendre le chargement JavaScript
            html = driver.page_source
            soup = BeautifulSoup(html, 'html.parser')
        else:
            response = session.get(BASE_URL, timeout=30)
            response.raise_for_status()
            soup = BeautifulSoup(response.content, 'html.parser')
        
        # Chercher l'élément <ul id="menu"> qui contient les catégories principales
        menu_ul = soup.find('ul', id='menu')
        
        if not menu_ul:
            logger.warning("Élément <ul id='menu'> non trouvé sur la page principale")
            return []
        
        seen_categories = set()
        
        # Chercher les catégories principales avec les classes spécifiques
        # Les catégories intéressantes ont: class="li-niveau1 advtm_menu_X" où X est 3, 4, 46, 6, 8, 11, 9, 10
        category_classes = [
            'li-niveau1 advtm_menu_3',
            'li-niveau1 advtm_menu_4',
            'li-niveau1 advtm_menu_46',
            'li-niveau1 advtm_menu_6',
            'li-niveau1 advtm_menu_8',
            'li-niveau1 advtm_menu_11',
            'li-niveau1 advtm_menu_9',
            'li-niveau1 advtm_menu_10'
        ]
        
        # Chercher tous les <li> avec class commençant par "li-niveau1 advtm_menu_"
        category_lis = menu_ul.find_all('li', class_=re.compile(r'li-niveau1 advtm_menu_\d+'))
        
        for li in category_lis:
            # Chercher le lien <a class="a-niveau1" data-type="category">
            link = li.find('a', class_='a-niveau1', attrs={'data-type': 'category'})
            
            if not link:
                # Fallback: chercher n'importe quel lien dans ce <li>
                link = li.find('a', href=True)
                if not link:
                    continue
            
            href = link.get('href', '')
            text = link.get_text(strip=True)
            
            # Nettoyer le texte
            text = ' '.join(text.split())
            
            # Filtrer les éléments qui ne sont pas des catégories valides
            if not text or len(text) < 2:
                continue
            
            if href:
                # Construire l'URL complète
                if href.startswith('http'):
                    category_url = href
                else:
                    category_url = urljoin(BASE_URL, href)
                
                # Filtrer les liens qui ne sont pas des catégories
                href_lower = href.lower()
                if any(exclude in href_lower for exclude in ['/cart', '/checkout', '/account', '/search', '/contact', '/about', '/blog', 'javascript:', 'mailto:', '#']):
                    continue
                
                # Ajouter la catégorie si elle n'a pas déjà été vue
                if category_url not in seen_categories:
                    categories.append({
                        'name': text,
                        'url': category_url
                    })
                    seen_categories.add(category_url)
        
        # Filtrer pour ne garder que les catégories produits valides (2 à 9)
        # TOILES AU MÈTRE, TABLE, CUISINE, DÉCO, BAGAGERIE, ACCESSOIRES, BAIN & PLAGE, EXTERIEUR & JARDIN
        valid_category_names = [
            'TOILES AU MÈTRE',
            'TABLE',
            'CUISINE',
            'DÉCO',
            'BAGAGERIE',
            'ACCESSOIRES',
            'BAIN & PLAGE',
            'EXTERIEUR & JARDIN'
        ]
        
        filtered_categories = []
        for cat in categories:
            # Vérifier si le nom correspond à une catégorie valide (insensible à la casse)
            cat_name_upper = cat['name'].upper()
            if any(valid_name.upper() in cat_name_upper or cat_name_upper in valid_name.upper() for valid_name in valid_category_names):
                filtered_categories.append(cat)
        
        logger.info(f"{len(filtered_categories)} catégorie(s) principale(s) trouvée(s) (filtrées sur {len(categories)} total)")
        return filtered_categories
        
    except Exception as e:
        logger.error(f"Erreur lors de l'extraction des catégories: {e}")
        return []


def get_subcategories(driver: Optional[webdriver.Chrome], session: requests.Session, category_url: str, category_name: str) -> List[Dict[str, str]]:
    """
    Extrait les sous-catégories d'une catégorie principale Artiga.
    Les sous-catégories se trouvent dans <table class="columnWrapTable"> avec <a data-type="category">.
    """
    logger.info(f"Extraction des sous-catégories pour: {category_name}")
    subcategories = []
    
    try:
        if not driver:
            logger.error("Selenium driver requis pour extraire les sous-catégories")
            return []
        
        driver, session = check_and_recreate_driver(driver, session, headless=True)
        
        # Aller sur la page principale pour voir le menu complet avec toutes les catégories et sous-catégories
        driver.get(BASE_URL)
        time.sleep(3)
        
        html = driver.page_source
        soup = BeautifulSoup(html, 'html.parser')
        
        # Chercher l'élément <ul id="menu"> qui contient toutes les catégories
        menu_ul = soup.find('ul', id='menu')
        
        if not menu_ul:
            logger.warning("Élément <ul id='menu'> non trouvé")
            return []
        
        # Chercher le <li class="li-niveau1 advtm_menu_X"> correspondant à cette catégorie
        category_lis = menu_ul.find_all('li', class_=re.compile(r'li-niveau1 advtm_menu_\d+'))
        
        target_category_li = None
        for li in category_lis:
            link = li.find('a', class_='a-niveau1', attrs={'data-type': 'category'})
            if not link:
                link = li.find('a', href=True)
            if link:
                link_text = link.get_text(strip=True)
                if link_text == category_name:
                    target_category_li = li
                    break
        
        if not target_category_li:
            logger.warning(f"Catégorie '{category_name}' non trouvée dans le menu")
            return []
        
        # Chercher les <table class="columnWrapTable"> sous ce <li>
        subcategory_tables = target_category_li.find_all('table', class_='columnWrapTable')
        
        seen_subcategories = set()
        
        for table in subcategory_tables:
            # Chercher les liens <a data-type="category"> dans cette table
            subcategory_links = table.find_all('a', attrs={'data-type': 'category'}, href=True)
            
            for link in subcategory_links:
                href = link.get('href', '')
                text = link.get_text(strip=True)
                
                # Nettoyer le texte
                text = ' '.join(text.split())
                
                # Filtrer les éléments qui ne sont pas des sous-catégories valides
                if not text or len(text) < 2:
                    continue
                
                if href:
                    # Construire l'URL complète
                    if href.startswith('http'):
                        subcategory_url = href
                    else:
                        subcategory_url = urljoin(BASE_URL, href)
                    
                    # Filtrer les liens qui ne sont pas des sous-catégories
                    href_lower = href.lower()
                    if any(exclude in href_lower for exclude in ['/cart', '/checkout', '/account', '/search', '/contact', '/about', '/blog', 'javascript:', 'mailto:', '#']):
                        continue
                    
                    # Ajouter la sous-catégorie si elle n'a pas déjà été vue
                    if subcategory_url not in seen_subcategories:
                        subcategories.append({
                            'name': text,
                            'url': subcategory_url,
                            'parent': category_name
                        })
                        seen_subcategories.add(subcategory_url)
        
        logger.info(f"{len(subcategories)} sous-catégorie(s) trouvée(s) pour {category_name}")
        return subcategories
        
    except Exception as e:
        logger.error(f"Erreur lors de l'extraction des sous-catégories pour {category_name}: {e}")
        return []


def get_products_from_category(driver: Optional[webdriver.Chrome], session: requests.Session, category_url: str, category_name: str, args=None) -> List[Dict[str, str]]:
    """
    Extrait la liste des produits d'une catégorie Artiga.
    Structure: Catégorie → Sous-catégories → Cartes produits → Page produit
    """
    logger.info(f"Extraction des produits de la catégorie: {category_name}")
    all_products = []
    
    try:
        if not driver:
            logger.error("Selenium driver requis pour naviguer entre les pages")
            return []
        
        # Vérifier et recréer le driver si nécessaire
        driver, session = check_and_recreate_driver(driver, session, headless=True)
        
        # Extraire les sous-catégories pour cette catégorie
        subcategories = get_subcategories(driver, session, category_url, category_name)
        
        # Si des sous-catégories sont trouvées, extraire les produits de chaque sous-catégorie
        if subcategories:
            # Filtrer les sous-catégories si spécifié dans args
            selected_subcategories = subcategories
            if args and hasattr(args, 'subcategories') and args.subcategories:
                selected_subcategories = []
                selected_names_lower = [name.lower().strip() for name in args.subcategories]
                for subcat in subcategories:
                    subcat_name_lower = subcat['name'].lower()
                    if any(selected in subcat_name_lower or subcat_name_lower in selected for selected in selected_names_lower):
                        selected_subcategories.append(subcat)
                
                logger.info(f"Filtrage: {len(selected_subcategories)} sous-catégorie(s) sélectionnée(s) sur {len(subcategories)} disponible(s)")
            
            # Traiter chaque sous-catégorie
            for subcategory in selected_subcategories:
                subcategory_name = subcategory['name']
                subcategory_url = subcategory['url']
                
                logger.info(f"Traitement de la sous-catégorie: {subcategory_name}")
                
                products = get_products_from_subcategory(driver, session, subcategory_url, subcategory_name)
                all_products.extend(products)
        else:
            # Pas de sous-catégories : ne pas extraire pour éviter les doublons
            logger.warning(f"Aucune sous-catégorie trouvée pour {category_name}. Les produits doivent être extraits uniquement depuis les sous-catégories pour éviter les doublons.")
            logger.info(f"Veuillez utiliser --subcategory pour spécifier les sous-catégories à extraire.")
        
        logger.info(f"{len(all_products)} produit(s) trouvé(s) dans la catégorie {category_name} ({len(subcategories) if subcategories else 0} sous-catégorie(s))")
        return all_products
        
    except Exception as e:
        logger.error(f"Erreur lors de l'extraction des produits de {category_name}: {e}")
        return []


def get_next_page_url_artiga(driver: webdriver.Chrome, current_url: str) -> Optional[str]:
    """
    Détecte et retourne l'URL de la page suivante pour Artiga.
    Structure spécifique: <ul class="page-list pagination"> avec liens ?page=X
    Retourne None s'il n'y a pas de page suivante.
    """
    try:
        html = driver.page_source
        soup = BeautifulSoup(html, 'html.parser')
        
        # PRIORITÉ 1: Chercher la pagination spécifique d'Artiga
        # <ul class="page-list pagination justify-content-center justify-content-lg-end mt-3 mt-lg-0 mb-0">
        pagination_ul = soup.find('ul', class_=re.compile(r'page-list.*pagination', re.I))
        
        if pagination_ul:
            # PRIORITÉ 1: Chercher le bouton "next" avec rel="next"
            next_link = pagination_ul.find('a', attrs={'rel': 'next'})
            if next_link:
                href = next_link.get('href', '')
                # Vérifier que le lien n'est pas désactivé
                parent_li = next_link.find_parent('li')
                if parent_li and 'disabled' not in parent_li.get('class', []):
                    if href and 'disabled' not in next_link.get('class', []):
                        # Extraire le numéro de page depuis l'URL du lien
                        page_match = re.search(r'[?&]page=(\d+)', href)
                        if page_match:
                            next_page_num = int(page_match.group(1))
                            # Construire l'URL avec l'URL actuelle comme base (pas celle du lien)
                            # Car les liens peuvent pointer vers la catégorie parente
                            base_url = current_url.split('?')[0]
                            next_url = f"{base_url}?page={next_page_num}"
                            logger.info(f"Page suivante trouvée (next): {next_url} (depuis href={href})")
                            return next_url
                        else:
                            # Si pas de paramètre page, utiliser le href tel quel
                            if href.startswith('http'):
                                logger.info(f"Page suivante trouvée (next): {href}")
                                return href
                            else:
                                full_url = urljoin(BASE_URL, href)
                                logger.info(f"Page suivante trouvée (next): {full_url}")
                                return full_url
            
            # Si pas de bouton next, chercher la page active et calculer la suivante
            active_li = pagination_ul.find('li', class_='active')
            if active_li:
                active_link = active_li.find('a', class_='page-link')
                if active_link:
                    # Extraire le numéro de page depuis l'URL ou le texte
                    active_href = active_link.get('href', '')
                    active_text = active_link.get_text(strip=True)
                    
                    # Essayer d'extraire depuis l'URL
                    current_page = 1
                    if active_href:
                        page_match = re.search(r'[?&]page=(\d+)', active_href)
                        if page_match:
                            current_page = int(page_match.group(1))
                        elif active_text.isdigit():
                            current_page = int(active_text)
                    elif active_text.isdigit():
                        current_page = int(active_text)
                    
                    # Trouver toutes les pages pour déterminer la dernière
                    # IMPORTANT: Les liens peuvent pointer vers la catégorie parente, donc on extrait juste les numéros
                    max_page = current_page
                    
                    # Chercher dans tous les <li> pour trouver les numéros de page
                    all_page_items = pagination_ul.find_all('li', class_='page-item')
                    for li_item in all_page_items:
                        page_link = li_item.find('a', class_='page-link')
                        if page_link:
                            href = page_link.get('href', '')
                            text = page_link.get_text(strip=True)
                            
                            # Extraire le numéro de page depuis l'URL (même si elle pointe vers une autre catégorie)
                            if href:
                                page_match = re.search(r'[?&]page=(\d+)', href)
                                if page_match:
                                    page_num = int(page_match.group(1))
                                    max_page = max(max_page, page_num)
                            
                            # Ou depuis le texte du lien (si c'est un chiffre, pas "Suivant" ou autres)
                            text_clean = text.strip()
                            # Ignorer les textes non numériques (comme "Suivant", icônes, etc.)
                            if text_clean.isdigit():
                                page_num = int(text_clean)
                                max_page = max(max_page, page_num)
                    
                    # Aussi chercher tous les liens page-link directement
                    all_page_links = pagination_ul.find_all('a', class_='page-link')
                    for page_link in all_page_links:
                        href = page_link.get('href', '')
                        text = page_link.get_text(strip=True).strip()
                        
                        # Extraire depuis l'URL
                        if href:
                            page_match = re.search(r'[?&]page=(\d+)', href)
                            if page_match:
                                page_num = int(page_match.group(1))
                                max_page = max(max_page, page_num)
                        
                        # Extraire depuis le texte (si numérique)
                        if text.isdigit():
                            page_num = int(text)
                            max_page = max(max_page, page_num)
                    
                    logger.info(f"Pagination détectée: page actuelle={current_page}, page max={max_page}")
                    
                    # Si on n'est pas sur la dernière page, construire l'URL de la page suivante
                    # IMPORTANT: Utiliser current_url comme base (pas l'URL des liens de pagination)
                    if current_page < max_page:
                        next_page = current_page + 1
                        # Construire l'URL avec l'URL actuelle comme base
                        base_url = current_url.split('?')[0]
                        if '?' in current_url:
                            # Préserver les autres paramètres s'il y en a (sauf page)
                            params = current_url.split('?', 1)[1]
                            # Remplacer ou ajouter le paramètre page
                            if 'page=' in params:
                                # Remplacer le paramètre page existant
                                params_clean = re.sub(r'[&]?page=\d+', '', params)
                                if params_clean:
                                    next_url = f"{base_url}?{params_clean}&page={next_page}"
                                else:
                                    next_url = f"{base_url}?page={next_page}"
                            else:
                                next_url = f"{current_url}&page={next_page}"
                        else:
                            next_url = f"{base_url}?page={next_page}"
                        
                        logger.info(f"Page suivante calculée: {next_url} (page {current_page} -> {next_page}, max={max_page})")
                        return next_url
        
        # FALLBACK: Chercher avec les méthodes génériques
        # Chercher le bouton "Suivant" ou "Next"
        next_selectors = [
            'a[rel="next"]',
            'a.next',
            '.pagination .next',
            'a[aria-label*="suivant" i]',
            'a[aria-label*="next" i]',
        ]
        
        for selector in next_selectors:
            try:
                next_links = driver.find_elements(By.CSS_SELECTOR, selector)
                for link in next_links:
                    if link.is_enabled() and link.is_displayed():
                        href = link.get_attribute('href')
                        if href and href != current_url:
                            if 'disabled' not in (link.get_attribute('class') or ''):
                                logger.debug(f"Page suivante trouvée (fallback): {href}")
                                return href
            except:
                continue
        
        # Dernier recours: chercher les liens avec ?page=
        page_links = soup.find_all('a', href=re.compile(r'[?&]page=\d+'))
        if page_links:
            current_page = 1
            max_page = 1
            
            for page_link in page_links:
                href = page_link.get('href', '')
                page_match = re.search(r'[?&]page=(\d+)', href)
                if page_match:
                    page_num = int(page_match.group(1))
                    max_page = max(max_page, page_num)
                    if current_url in href or driver.current_url in href:
                        current_page = page_num
            
            if current_page < max_page:
                base_url = current_url.split('?')[0]
                next_url = f"{base_url}?page={current_page + 1}"
                logger.debug(f"Page suivante calculée (fallback): {next_url}")
                return next_url
        
        logger.debug("Aucune page suivante trouvée")
        return None
        
    except Exception as e:
        logger.debug(f"Erreur lors de la détection de pagination Artiga: {e}")
        return None


def get_products_from_subcategory(driver: Optional[webdriver.Chrome], session: requests.Session, subcategory_url: str, subcategory_name: str) -> List[Dict[str, str]]:
    """
    Extrait la liste des produits d'une sous-catégorie Artiga.
    Les produits sont dans des cartes d'articles.
    Gère la pagination si présente.
    """
    all_products = []
    current_url = subcategory_url
    page_num = 1
    max_pages = 100  # Limite de sécurité
    seen_product_urls = set()
    
    try:
        while current_url and page_num <= max_pages:
            driver.get(current_url)
            time.sleep(5)
            
            # Faire défiler pour charger tous les produits
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
            
            page_products = []
            
            # Chercher les produits avec plusieurs stratégies
            product_articles = []
            
            # Stratégie 1: éléments <article> avec classes product-miniature
            product_articles = soup.find_all('article', class_=re.compile(r'product-miniature', re.I))
            logger.debug(f"Stratégie 1 (article.product-miniature): {len(product_articles)} produit(s) trouvé(s)")
            
            # Stratégie 2: chercher par attribut data-product-id
            if not product_articles:
                product_articles = soup.find_all(attrs={'data-product-id': True})
                logger.debug(f"Stratégie 2 (data-product-id): {len(product_articles)} produit(s) trouvé(s)")
            
            # Stratégie 3: chercher les cartes d'articles avec classes product
            if not product_articles:
                product_articles = soup.find_all(['div', 'article'], class_=re.compile(r'product', re.I))
                logger.debug(f"Stratégie 3 (div/article.product): {len(product_articles)} produit(s) trouvé(s)")
            
            # Stratégie 4: chercher tous les liens dans des conteneurs de produits
            if not product_articles:
                # Chercher les conteneurs de produits (grid, list, etc.)
                product_containers = soup.find_all(['div', 'section'], class_=re.compile(r'products|grid|list|items', re.I))
                logger.debug(f"Stratégie 4: {len(product_containers)} conteneur(s) de produits trouvé(s)")
                for container in product_containers:
                    # Chercher les liens vers des produits dans ces conteneurs
                    links = container.find_all('a', href=True)
                    for link in links:
                        href = link.get('href', '')
                        # Filtrer les liens qui ressemblent à des produits
                        if href and '/product' in href.lower() or '/article' in href.lower() or '/p/' in href.lower():
                            # Créer un élément factice pour traiter comme un article
                            parent = link.find_parent(['article', 'div'])
                            if parent and parent not in product_articles:
                                product_articles.append(parent)
            
            # Stratégie 5: chercher tous les liens qui ressemblent à des produits
            if not product_articles:
                all_links = soup.find_all('a', href=True)
                product_links = []
                for link in all_links:
                    href = link.get('href', '')
                    href_lower = href.lower()
                    # Chercher les liens vers des produits (éviter les liens de navigation)
                    if (('/product' in href_lower or '/article' in href_lower or '/p/' in href_lower) and
                        not any(exclude in href_lower for exclude in ['/cart', '/checkout', '/account', '/search', '/contact', '/about', '/blog', 'javascript:', 'mailto:', '#', '/category', '/c/'])):
                        product_links.append(link)
                        # Prendre le parent comme conteneur produit
                        parent = link.find_parent(['article', 'div', 'li'])
                        if parent and parent not in product_articles:
                            product_articles.append(parent)
                logger.debug(f"Stratégie 5 (liens produits): {len(product_links)} lien(s) produit trouvé(s)")
            
            logger.debug(f"Total: {len(product_articles)} élément(s) produit trouvé(s) sur la page {page_num}")
            
            for article in product_articles:
                # Chercher le lien du produit dans l'article
                link = article.find('a', href=True)
                if not link:
                    continue
                
                href = link.get('href', '')
                if not href:
                    continue
                
                # Nettoyer les fragments (#/65-taille-160_) pour obtenir l'URL de base du produit
                if '#' in href:
                    href = href.split('#')[0]
                
                # Construire l'URL complète
                if href.startswith('http'):
                    product_url = href
                else:
                    product_url = urljoin(BASE_URL, href)
                
                # Filtrer les liens qui ne sont pas des produits
                href_lower = href.lower()
                if any(exclude in href_lower for exclude in ['/cart', '/checkout', '/account', '/search', '/contact', '/about', '/blog', 'javascript:', 'mailto:', '/category', '/c/']):
                    continue
                
                # S'assurer que c'est bien un lien vers un produit (contient le nom du produit dans l'URL)
                if not any(indicator in href_lower for indicator in ['/product', '/article', '/p/', '/nappe', '/serviette', '/set', '/jete']):
                    # Si ce n'est pas un lien évident vers un produit, vérifier qu'il ne pointe pas vers une catégorie
                    if '/category' in href_lower or '/c/' in href_lower or href_lower.endswith('/table') or href_lower.endswith('/nappes'):
                        continue
                
                # Éviter les doublons (déjà dans seen_product_urls global)
                if product_url in seen_product_urls:
                    continue
                
                seen_product_urls.add(product_url)
                
                # Extraire le nom du produit
                title_elem = article.find(['h1', 'h2', 'h3', 'h4', 'h5', 'h6']) or article.find(class_=re.compile(r'title|name', re.I))
                if title_elem:
                    product_name = title_elem.get_text(strip=True)
                else:
                    product_name = link.get_text(strip=True) or href.split('/')[-1].replace('-', ' ').title()
                
                # Chercher l'image du produit dans l'article
                image_url = None
                img = article.find('img')
                if img:
                    image_url = img.get('src') or img.get('data-src') or img.get('data-lazy-src') or img.get('data-original')
                    if image_url:
                        image_url = urljoin(BASE_URL, image_url)
                
                page_products.append({
                    'name': product_name,
                    'url': product_url,
                    'image_url': image_url
                })
            
            # Ajouter les produits de cette page à la liste totale
            all_products.extend(page_products)
            logger.info(f"Page {page_num}: {len(page_products)} produit(s) trouvé(s) dans {subcategory_name}")
            
            # Vérifier s'il y a une page suivante
            next_url = get_next_page_url_artiga(driver, current_url)
            if next_url and next_url != current_url:
                logger.info(f"Navigation vers la page suivante: {next_url}")
                current_url = next_url
                page_num += 1
                time.sleep(2)  # Petite pause entre les pages
            else:
                # Pas de page suivante, on arrête
                logger.info(f"Pas de page suivante détectée (current_url={current_url})")
                break
        
        logger.info(f"Total: {len(all_products)} produit(s) trouvé(s) dans {subcategory_name} sur {page_num} page(s)")
        return all_products
        
    except Exception as e:
        logger.error(f"Erreur lors de l'extraction des produits de {subcategory_name}: {e}")
        return []


def get_product_details(driver: Optional[webdriver.Chrome], session: requests.Session, product_url: str, product_name: str, headless: bool = True) -> tuple:
    """
    Extrait les détails complets d'un produit Artiga depuis sa page.
    Retourne un tuple (details_dict, driver, session).
    """
    try:
        if driver:
            driver, session = check_and_recreate_driver(driver, session, headless=headless)
            
            try:
                driver.get(product_url)
                time.sleep(3)
                html = driver.page_source
                soup = BeautifulSoup(html, 'html.parser')
            except InvalidSessionIdException:
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
        
        # Extraire les données depuis JSON-LD (priorité)
        json_ld_data = None
        json_ld_script = soup.find('script', type='application/ld+json')
        if json_ld_script:
            try:
                json_content = json_ld_script.string
                if json_content:
                    json_ld_data = json.loads(json_content)
                    # Si c'est une liste, chercher le premier élément de type Product
                    if isinstance(json_ld_data, list):
                        for item in json_ld_data:
                            if isinstance(item, dict) and item.get('@type') == 'Product':
                                json_ld_data = item
                                break
                    # Si c'est un dict mais pas de @type Product, chercher dans le contenu
                    elif isinstance(json_ld_data, dict) and json_ld_data.get('@type') != 'Product':
                        # Chercher dans @graph si présent
                        if '@graph' in json_ld_data:
                            for item in json_ld_data['@graph']:
                                if isinstance(item, dict) and item.get('@type') == 'Product':
                                    json_ld_data = item
                                    break
                    logger.debug("Données JSON-LD trouvées")
            except json.JSONDecodeError as e:
                logger.debug(f"Erreur lors du parsing JSON-LD: {e}")
        
        # Extraire le nom du produit depuis JSON-LD (priorité)
        full_name = ""
        if json_ld_data and 'name' in json_ld_data:
            full_name = json_ld_data['name']
            logger.debug(f"Titre extrait depuis JSON-LD: {full_name}")
        
        # Fallback: Extraire le nom du produit depuis le HTML
        if not full_name:
            # Chercher d'abord le h1
            h1_elem = soup.find('h1')
            h1_text = h1_elem.get_text(strip=True) if h1_elem else ''
            
            # Chercher le h2 (souvent la collection)
            h2_elem = soup.find('h2')
            h2_text = h2_elem.get_text(strip=True) if h2_elem else ''
            
            # Nettoyer h2 pour supprimer les textes indésirables
            if h2_text:
                # Supprimer les phrases indésirables
                unwanted_phrases = [
                    'Les clients qui ont acheté ce produit ont également acheté',
                    'Les clients qui ont acheté',
                    'ont également acheté',
                    'Produits similaires',
                    'Vous pourriez aussi aimer'
                ]
                for phrase in unwanted_phrases:
                    if phrase.lower() in h2_text.lower():
                        h2_text = ''
                        break
            
            # Construire le titre complet : h1 + h2 si h2 existe et est valide
            if h1_text:
                if h2_text and len(h2_text) > 2:
                    full_name = f"{h1_text} {h2_text}"
                else:
                    full_name = h1_text
            else:
                # Fallback sur title ou product_name
                title_elem = soup.find('title')
                full_name = title_elem.get_text(strip=True) if title_elem else product_name
        
        # Nettoyer le titre final pour supprimer les phrases indésirables
        unwanted_phrases = [
            'Les clients qui ont acheté ce produit ont également acheté',
            'Les clients qui ont acheté',
            'ont également acheté',
            'Produits similaires',
            'Vous pourriez aussi aimer'
        ]
        for phrase in unwanted_phrases:
            if phrase.lower() in full_name.lower():
                # Supprimer la phrase et tout ce qui suit
                idx = full_name.lower().find(phrase.lower())
                if idx > 0:
                    full_name = full_name[:idx].strip()
                break
        
        name_without_code = full_name
        
        # Extraire la description depuis JSON-LD (priorité)
        description = ""
        if json_ld_data and 'description' in json_ld_data:
            description = json_ld_data['description']
            # Convertir les entités HTML si nécessaire
            description = description.replace('&nbsp;', ' ').replace('\u00a0', ' ')
            # Convertir les retours à la ligne en <br> pour HTML
            description = description.replace('\n', '<br>')
            logger.info(f"Description extraite depuis JSON-LD ({len(description)} caractères)")
        
        # Fallback: Extraire la description HTML si pas trouvée dans JSON-LD
        if not description:
            description_html = ""
            if driver:
                try:
                    # Faire défiler jusqu'aux onglets
                    driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
                    time.sleep(1)
                    
                    # Chercher les onglets (tabs)
                    tabs = driver.find_elements(By.CSS_SELECTOR, 'a[data-toggle="tab"], button[data-toggle="tab"], .nav-tabs a, .tabs a')
                    if not tabs:
                        # Chercher par texte
                        tabs = driver.find_elements(By.XPATH, "//a[contains(text(), 'Description')] | //button[contains(text(), 'Description')] | //a[contains(text(), 'Détails')] | //button[contains(text(), 'Détails')]")
                    
                    # Collecter le contenu de tous les onglets
                    tab_contents = []
                    for tab in tabs:
                        try:
                            # Cliquer sur l'onglet
                            driver.execute_script("arguments[0].scrollIntoView(true);", tab)
                            time.sleep(0.5)
                            tab.click()
                            time.sleep(1)
                            
                            # Récupérer le contenu de l'onglet actif
                            active_pane = driver.find_elements(By.CSS_SELECTOR, '.tab-pane.active, .tab-content .active, [role="tabpanel"].active')
                            if not active_pane:
                                # Chercher le contenu après le clic
                                html_after_click = driver.page_source
                                soup_after = BeautifulSoup(html_after_click, 'html.parser')
                                active_content = soup_after.find('div', class_=re.compile(r'tab-pane|tab-content', re.I))
                                if active_content:
                                    tab_contents.append(str(active_content))
                            else:
                                for pane in active_pane:
                                    tab_contents.append(pane.get_attribute('innerHTML') or '')
                        except Exception as e:
                            logger.debug(f"Erreur lors du clic sur l'onglet: {e}")
                            continue
                    
                    # Si pas d'onglets trouvés, chercher directement le contenu des sections
                    if not tab_contents:
                        html_scrolled = driver.page_source
                        soup_scrolled = BeautifulSoup(html_scrolled, 'html.parser')
                        
                        # Chercher les sections de description
                        desc_sections = soup_scrolled.find_all(['div', 'section'], class_=re.compile(r'description|product-description|product-details|tab-content', re.I))
                        for section in desc_sections:
                            if section.get_text(strip=True):
                                tab_contents.append(str(section))
                    
                    # Combiner tout le contenu HTML
                    if tab_contents:
                        description_html = '\n'.join(tab_contents)
                    else:
                        # Fallback : chercher dans le HTML statique
                        desc_elem = soup.find('div', class_=re.compile(r'description|content|product-description', re.I))
                        if desc_elem:
                            description_html = str(desc_elem)
                        else:
                            paragraphs = soup.find_all('p')
                            description_html = ' '.join([str(p) for p in paragraphs[:5] if p.get_text(strip=True)])
                except Exception as e:
                    logger.debug(f"Erreur lors de l'extraction des onglets: {e}")
                    # Fallback vers extraction simple
                    desc_elem = soup.find('div', class_=re.compile(r'description|content|product-description', re.I))
                    if desc_elem:
                        description_html = str(desc_elem)
                    else:
                        paragraphs = soup.find_all('p')
                        description_html = ' '.join([str(p) for p in paragraphs[:5] if p.get_text(strip=True)])
            else:
                # Pas de driver, extraction simple
                desc_elem = soup.find('div', class_=re.compile(r'description|content|product-description', re.I))
                if desc_elem:
                    description_html = str(desc_elem)
                else:
                    paragraphs = soup.find_all('p')
                    description_html = ' '.join([str(p) for p in paragraphs[:5] if p.get_text(strip=True)])
            
            description = description_html
        
        # Extraire le prix
        price = ""
        price_elem = soup.find('span', class_=re.compile(r'price|prix', re.I))
        if price_elem:
            price_text = price_elem.get_text(strip=True)
            price_match = re.search(r'([\d,]+)', price_text.replace('€', '').replace(' ', ''))
            if price_match:
                price = price_match.group(1).replace(',', '.')
        
        # Extraire le SKU/Référence depuis JSON-LD (priorité)
        sku = ""
        if json_ld_data:
            # Chercher sku dans le JSON-LD
            if 'sku' in json_ld_data:
                sku = str(json_ld_data['sku']).strip()
                logger.debug(f"SKU trouvé via JSON-LD: {sku}")
            # Chercher aussi dans offers si présent
            elif 'offers' in json_ld_data:
                offers = json_ld_data['offers']
                if isinstance(offers, list) and len(offers) > 0:
                    sku = str(offers[0].get('sku', '')).strip()
                elif isinstance(offers, dict):
                    sku = str(offers.get('sku', '')).strip()
        
        # Fallback: Chercher le SKU dans différentes structures HTML
        if not sku:
            sku_selectors = [
                {'class': re.compile(r'reference|sku|product-reference', re.I)},
                {'itemprop': 'sku'},
                {'data-product-reference': True}
            ]
            
            for selector in sku_selectors:
                sku_elem = soup.find(['span', 'div', 'p'], selector)
                if sku_elem:
                    sku_text = sku_elem.get_text(strip=True)
                    # Extraire le code référence
                    sku_match = re.search(r'[:\s]*([A-Z0-9-]+)', sku_text, re.I)
                    if sku_match:
                        sku = sku_match.group(1).strip()
                        break
            
            # Si pas de SKU trouvé, utiliser l'ID produit depuis l'URL ou data-product-id
            if not sku:
                product_id_elem = soup.find(attrs={'data-product-id': True})
                if product_id_elem:
                    sku = product_id_elem.get('data-product-id', '')
        
        # Extraire les images
        images = []
        img_tags = soup.find_all('img')
        for img in img_tags:
            src = img.get('src') or img.get('data-src') or img.get('data-lazy-src')
            if src:
                # Filtrer les images de produits (exclure logos, icônes, etc.)
                if any(pattern in src.lower() for pattern in ['product', 'produit', 'artiga.fr']):
                    if 'logo' not in src.lower() and 'icon' not in src.lower():
                        image_url = urljoin(BASE_URL, src)
                        if image_url not in images:
                            images.append(image_url)
        
        # Si pas d'images trouvées, chercher dans les galeries
        if not images:
            gallery = soup.find('div', class_=re.compile(r'gallery|carousel|slider', re.I))
            if gallery:
                gallery_imgs = gallery.find_all('img')
                for img in gallery_imgs:
                    src = img.get('src') or img.get('data-src')
                    if src:
                        image_url = urljoin(BASE_URL, src)
                        if image_url not in images:
                            images.append(image_url)
        
        # Extraire les variants avec leurs prix spécifiques
        variants = []
        
        if driver:
            try:
                # Remonter en haut de la page pour les variants
                driver.execute_script("window.scrollTo(0, 0);")
                time.sleep(1)
                
                # Chercher les options de variantes (boutons, liens, selects)
                # IMPORTANT: Chercher uniquement dans la section du produit actuel, pas dans les produits suggérés
                
                # Chercher la section principale du produit
                product_section = None
                try:
                    # Chercher la section produit principale
                    product_sections = driver.find_elements(By.CSS_SELECTOR, 
                        '.product-details, .product-info, .product-main, [itemtype*="Product"], .product')
                    if product_sections:
                        product_section = product_sections[0]
                except:
                    pass
                
                # Chercher les boutons/liens de variants (tailles, couleurs)
                # Chercher par plusieurs sélecteurs CSS, mais uniquement dans la section produit
                variant_selectors = [
                    'a[href*="#/"]',  # Liens avec hash (comme #/68-taille-300_cm) - PRIORITAIRE
                    'a[data-value]',
                    'button[data-value]',
                    '.product-variants a',
                    '.variant a',
                    '[data-attribute-value]',
                    '.product-attributes a',
                    'a.product-variant',
                    '.product-variants li a',
                    'ul.product-variants a',
                ]
                
                variant_buttons = []
                seen_hrefs = set()
                
                # Extraire l'URL de base du produit pour filtrer les variants
                base_product_url = product_url.split('#')[0].split('?')[0]
                product_slug = base_product_url.split('/')[-1] if '/' in base_product_url else ''
                
                for selector in variant_selectors:
                    try:
                        # Si on a une section produit, chercher dedans
                        if product_section:
                            elements = product_section.find_elements(By.CSS_SELECTOR, selector)
                        else:
                            elements = driver.find_elements(By.CSS_SELECTOR, selector)
                        
                        for elem in elements:
                            # Récupérer le href
                            href = elem.get_attribute('href') or ''
                            text = elem.text.strip()
                            
                            # Filtrer: le href doit pointer vers le même produit (même slug)
                            if href:
                                # Vérifier que le href pointe vers le produit actuel
                                if product_slug and product_slug not in href:
                                    continue  # Ignorer les liens vers d'autres produits
                                
                                # Si c'est un lien avec hash et qu'il contient "taille" ou un ID numérique, c'est probablement un variant
                                if '#' in href and ('taille' in href.lower() or re.search(r'#/\d+', href)):
                                    if href not in seen_hrefs:
                                        variant_buttons.append(elem)
                                        seen_hrefs.add(href)
                            # Sinon, filtrer par texte (mais seulement si dans la section produit)
                            elif text and len(text) < 50 and ('taille' in text.lower() or 'size' in text.lower() or 'cm' in text or re.search(r'\d+\s*cm', text)):
                                if elem not in variant_buttons:
                                    variant_buttons.append(elem)
                    except:
                        continue
                
                # Chercher aussi les selects
                variant_selects = driver.find_elements(By.CSS_SELECTOR, 
                    'select[name*="group"], select[id*="group"], select[name*="variant"], select[name*="attribute"]')
                
                variant_options_list = []
                
                # Traiter les selects
                for select_elem in variant_selects:
                    try:
                        select = Select(select_elem)
                        options = select.options
                        for option in options:
                            option_value = option.get_attribute('value')
                            option_text = option.text.strip()
                            option_title = option.get_attribute('title') or option_text
                            
                            if option_value and option_text:
                                # Reconstruire l'URL avec hash au format: {value}-taille-{digits}_cm
                                # Extraire uniquement les digits du title (ex: "160 cm" -> "160")
                                digits_match = re.search(r'(\d+)', option_title)
                                variant_href = ""
                                if digits_match:
                                    digits = digits_match.group(1)
                                    variant_href = f"#/{option_value}-taille-{digits}_cm"
                                
                                variant_options_list.append({
                                    'type': 'select',
                                    'element': select_elem,
                                    'value': option_value,
                                    'text': option_text,
                                    'title': option_title,
                                    'option': option,
                                    'href': variant_href  # URL avec hash reconstruite
                                })
                    except Exception as e:
                        logger.debug(f"Erreur avec select: {e}")
                
                # Traiter les boutons/liens
                for button in variant_buttons:
                    try:
                        # Récupérer l'URL du variant (href avec hash)
                        variant_href = button.get_attribute('href') or ''
                        variant_value = button.get_attribute('data-value') or button.get_attribute('data-attribute-value') or ''
                        variant_text = button.text.strip()
                        
                        # Si le href contient un hash (#), l'utiliser
                        # Sinon, essayer de construire l'URL depuis data-value ou autres attributs
                        if not variant_href or '#' not in variant_href:
                            # Chercher dans les attributs data pour construire l'URL
                            data_id = button.get_attribute('data-id') or button.get_attribute('data-product-id') or ''
                            if data_id:
                                # Construire l'URL avec hash depuis l'ID
                                variant_href = f"#/{data_id}-taille-{slugify(variant_text).replace('-', '_')}"
                        
                        # Filtrer les variants qui ne sont pas des tailles/couleurs (ex: "mail", "partager", etc.)
                        # Un variant valide doit avoir soit un texte avec taille/cm, soit un href avec hash contenant "taille"
                        is_valid_variant = False
                        
                        # Vérifier si c'est un variant valide
                        if variant_href and '#' in variant_href:
                            # Si le href contient "taille" ou un pattern de variant (#/XX-taille-XXX), c'est valide
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
                        
                        # Si pas de texte et pas de href valide, ignorer
                        if not variant_text and not (variant_href and '#' in variant_href and 'taille' in variant_href.lower()):
                            is_valid_variant = False
                        
                        if is_valid_variant and (variant_value or variant_href or variant_text):
                            variant_options_list.append({
                                'type': 'button',
                                'element': button,
                                'value': variant_value,
                                'text': variant_text,
                                'href': variant_href  # URL complète avec hash si disponible
                            })
                    except Exception as e:
                        logger.debug(f"Erreur avec button: {e}")
                
                # Si on a trouvé des variants, cliquer sur chacun pour obtenir le prix
                if variant_options_list:
                    logger.info(f"Trouvé {len(variant_options_list)} option(s) de variant")
                    
                    # Obtenir le prix de base (avant de cliquer sur les variants)
                    base_price = price
                    
                    # Traiter chaque variant
                    for variant_option in variant_options_list:
                        try:
                            # Vider les logs de performance avant de changer de variant
                            try:
                                driver.get_log('performance')  # Lire les logs pour les vider
                            except:
                                pass
                            
                            # Cliquer sur le variant (même si on a une URL avec hash, utiliser le clic pour déclencher AJAX)
                            driver.execute_script("arguments[0].scrollIntoView(true);", variant_option['element'])
                            time.sleep(0.5)
                            
                            # Cliquer sur le variant
                            if variant_option['type'] == 'select':
                                select = Select(variant_option['element'])
                                select.select_by_value(variant_option['value'])
                                
                                # Forcer la mise à jour des attributs selected dans le HTML avec JavaScript
                                try:
                                    driver.execute_script("""
                                        var select = arguments[0];
                                        var targetValue = arguments[1];
                                        
                                        // Changer la valeur
                                        select.value = targetValue;
                                        
                                        // Mettre à jour les attributs selected dans le HTML
                                        for (var i = 0; i < select.options.length; i++) {
                                            if (select.options[i].value == targetValue) {
                                                select.options[i].setAttribute('selected', 'selected');
                                                select.options[i].selected = true;
                                            } else {
                                                select.options[i].removeAttribute('selected');
                                                select.options[i].selected = false;
                                            }
                                        }
                                        
                                        // Déclencher les événements pour mettre à jour le prix
                                        var changeEvent = new Event('change', { bubbles: true });
                                        select.dispatchEvent(changeEvent);
                                        
                                        var inputEvent = new Event('input', { bubbles: true });
                                        select.dispatchEvent(inputEvent);
                                    """, variant_option['element'], variant_option['value'])
                                    logger.debug(f"Attributs selected mis à jour avec JavaScript pour variant {variant_option.get('text', '')}")
                                except Exception as e:
                                    logger.debug(f"Erreur lors de la mise à jour des attributs selected: {e}")
                            else:
                                variant_option['element'].click()
                            
                            # Attendre que la requête AJAX soit envoyée
                            time.sleep(3)
                            
                            # Attendre que la page soit mise à jour et que le prix soit présent
                            try:
                                WebDriverWait(driver, 10).until(
                                    EC.presence_of_element_located((By.CSS_SELECTOR, 'div.current-price span.current-price-display'))
                                )
                                # Attendre encore un peu pour que le JavaScript mette à jour le prix
                                time.sleep(2)
                            except TimeoutException:
                                pass
                            
                            # Extraire le prix après navigation/clic sur le variant
                            variant_price = ""
                            
                            # Méthode 1: Essayer de récupérer le prix depuis les requêtes AJAX (plus fiable)
                            try:
                                # Récupérer les mises à jour de prix depuis les requêtes AJAX
                                price_updates = get_ajax_price_updates(driver)
                                
                                if price_updates:
                                    # Trier par timestamp pour obtenir le plus récent
                                    sorted_updates = sorted(price_updates.items(), key=lambda x: x[0], reverse=True)
                                    ajax_price_text = sorted_updates[0][1]['price']
                                    
                                    # Extraire le prix numérique
                                    price_match = re.search(r'([\d,]+\.?\d*)', ajax_price_text.replace('\xa0', ' ').replace('€', '').replace(' ', '').replace(',', '.'))
                                    if price_match:
                                        variant_price = price_match.group(1).replace(',', '.')
                                        logger.info(f"Prix variant {variant_option.get('text', '')}: {variant_price} (trouvé via AJAX)")
                                else:
                                    logger.debug(f"Aucune requête AJAX capturée pour variant {variant_option.get('text', '')}, utilisation du DOM")
                            except Exception as e:
                                logger.debug(f"Erreur lors de la récupération du prix via AJAX: {e}")
                            
                            # Méthode 2: Si pas trouvé via AJAX, utiliser le DOM
                            if not variant_price:
                                # Attendre que le prix soit mis à jour (JavaScript peut prendre du temps)
                                time.sleep(2)
                                
                                # Attendre explicitement que l'élément de prix soit présent
                                try:
                                    WebDriverWait(driver, 10).until(
                                        EC.presence_of_element_located((By.CSS_SELECTOR, 'div.current-price span.current-price-display'))
                                    )
                                    time.sleep(2)
                                except TimeoutException:
                                    logger.debug("Timeout en attendant l'élément de prix")
                                
                                # Chercher le prix dans le DOM avec Selenium
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
                                            logger.info(f"Prix variant {variant_option.get('text', '')}: {variant_price} (trouvé dans le DOM)")
                                except Exception as e:
                                    logger.debug(f"Erreur extraction prix depuis le DOM: {e}")
                                
                                # Si toujours pas trouvé, utiliser BeautifulSoup comme fallback
                                if not variant_price:
                                    html_after_variant = driver.page_source
                                    soup_variant_price = BeautifulSoup(html_after_variant, 'html.parser')
                                    current_price_div = soup_variant_price.find('div', class_='current-price')
                                    if current_price_div:
                                        price_span = current_price_div.find('span', class_=lambda x: x and 'current-price-display' in ' '.join(x) if isinstance(x, list) else 'current-price-display' in str(x))
                                        if price_span:
                                            price_text = price_span.get_text(strip=True)
                                            price_text_clean = price_text.replace('\xa0', ' ').replace('€', '').replace('&nbsp;', ' ').strip()
                                            price_match = re.search(r'([\d,]+\.?\d*)', price_text_clean.replace(' ', '').replace(',', '.'))
                                            if price_match:
                                                price_value = float(price_match.group(1).replace(',', '.'))
                                                if 1 <= price_value <= 10000:
                                                    variant_price = price_match.group(1).replace(',', '.')
                                                    logger.info(f"Prix variant {variant_option.get('text', '')}: {variant_price} (trouvé avec BeautifulSoup)")
                            
                            # Si toujours pas de prix trouvé, utiliser le prix de base
                            if not variant_price:
                                variant_price = base_price
                                logger.debug(f"Prix non trouvé pour variant {variant_option.get('text', '')}, utilisation du prix de base: {base_price}")
                            
                            logger.info(f"Variant {variant_option.get('text', '')}: Prix={variant_price}")
                            
                            # Récupérer le HTML mis à jour après le clic pour extraire SKU et autres infos
                            html_after_variant = driver.page_source
                            soup_variant = BeautifulSoup(html_after_variant, 'html.parser')
                            
                            # Récupérer le SKU/référence du variant depuis la page
                            variant_sku = sku
                            # Chercher dans différentes structures
                            ref_selectors = [
                                {'class': re.compile(r'product-reference|reference', re.I)},
                                {'id': re.compile(r'reference|ref', re.I)}
                            ]
                            
                            for selector in ref_selectors:
                                ref_elem = soup_variant.find(['div', 'span', 'p', 'td'], selector)
                                if ref_elem:
                                    # Chercher le span à l'intérieur qui contient la référence
                                    ref_span = ref_elem.find('span')
                                    if ref_span:
                                        ref_text = ref_span.get_text(strip=True)
                                    else:
                                        ref_text = ref_elem.get_text(strip=True)
                                    
                                    # Chercher un code référence (format: ARGEN160_1492_160CM ou similaire)
                                    # Exclure "Référence" du texte
                                    ref_text_clean = re.sub(r'^référence\s*:?\s*', '', ref_text, flags=re.I).strip()
                                    ref_match = re.search(r'([A-Z0-9][A-Z0-9_-]{5,})', ref_text_clean, re.I)
                                    if ref_match:
                                        variant_sku = ref_match.group(1).strip()
                                        break
                            
                            # Si toujours pas trouvé, chercher dans le texte brut
                            if variant_sku == sku:
                                ref_text_elem = soup_variant.find(text=re.compile(r'référence', re.I))
                                if ref_text_elem:
                                    parent = ref_text_elem.find_parent()
                                    if parent:
                                        ref_text = parent.get_text(strip=True)
                                        ref_text_clean = re.sub(r'^référence\s*:?\s*', '', ref_text, flags=re.I).strip()
                                        ref_match = re.search(r'([A-Z0-9][A-Z0-9_-]{5,})', ref_text_clean, re.I)
                                        if ref_match:
                                            variant_sku = ref_match.group(1).strip()
                            
                            # Récupérer l'EAN13 si disponible
                            variant_gencode = ""
                            # Chercher dans les sections de détails avec Selenium aussi
                            try:
                                # Chercher directement avec Selenium dans le HTML après le clic
                                ean_elements = driver.find_elements(By.XPATH, "//dt[contains(text(), 'ean13') or contains(text(), 'ean')]/following-sibling::dd")
                                if not ean_elements:
                                    # Chercher par texte
                                    ean_elements = driver.find_elements(By.XPATH, "//*[contains(text(), 'ean13') or contains(text(), 'ean 13')]")
                                
                                for ean_elem in ean_elements:
                                    ean_text = ean_elem.text.strip()
                                    ean_match = re.search(r'(\d{13})', ean_text)
                                    if ean_match:
                                        variant_gencode = ean_match.group(1)
                                        break
                            except Exception as e:
                                logger.debug(f"Erreur extraction EAN13 avec Selenium: {e}")
                            
                            # Si pas trouvé avec Selenium, chercher dans le HTML parsé
                            if not variant_gencode:
                                # Chercher dans les sections de détails
                                ean_sections = soup_variant.find_all('section', class_=re.compile(r'product-features', re.I))
                                for ean_section in ean_sections:
                                    # Chercher "ean13" dans les dt
                                    ean_dts = ean_section.find_all('dt')
                                    for ean_dt in ean_dts:
                                        if ean_dt.get_text() and re.search(r'ean13|ean', ean_dt.get_text(), re.I):
                                            ean_dd = ean_dt.find_next_sibling('dd')
                                            if ean_dd:
                                                ean_text = ean_dd.get_text(strip=True)
                                                ean_match = re.search(r'(\d{13})', ean_text)
                                                if ean_match:
                                                    variant_gencode = ean_match.group(1)
                                                    break
                                    if variant_gencode:
                                        break
                            
                            # Si toujours pas trouvé, chercher dans tout le HTML
                            if not variant_gencode:
                                # Utiliser find avec string au lieu de text (déprécié)
                                ean_text_elem = soup_variant.find(string=re.compile(r'ean13|ean\s*13', re.I))
                                if ean_text_elem:
                                    # Si c'est une NavigableString, trouver le parent
                                    if hasattr(ean_text_elem, 'find_parent'):
                                        parent = ean_text_elem.find_parent()
                                    else:
                                        # Sinon, chercher dans les éléments parents
                                        for elem in soup_variant.find_all(['dd', 'td', 'span', 'div']):
                                            if 'ean13' in elem.get_text().lower() or 'ean 13' in elem.get_text().lower():
                                                ean_text = elem.get_text(strip=True)
                                                ean_match = re.search(r'(\d{13})', ean_text)
                                                if ean_match:
                                                    variant_gencode = ean_match.group(1)
                                                    break
                                        if variant_gencode:
                                            break
                                    
                                    if not variant_gencode and hasattr(ean_text_elem, 'find_parent'):
                                        parent = ean_text_elem.find_parent()
                                        if parent:
                                            ean_text = parent.get_text(strip=True)
                                            ean_match = re.search(r'(\d{13})', ean_text)
                                            if ean_match:
                                                variant_gencode = ean_match.group(1)
                            
                            # Déterminer le type de variant (taille, couleur, etc.)
                            variant_text = variant_option.get('text', '').strip()
                            variant_value_raw = variant_option.get('value', variant_text)
                            
                            # Déterminer si c'est une taille (contient "cm", "taille", "size", ou des chiffres)
                            is_size = any(keyword in variant_text.lower() for keyword in ['cm', 'taille', 'size', 'couverts']) or bool(re.search(r'\d+', variant_text))
                            variant_type = "Taille" if is_size else "Couleur"
                            
                            # Nettoyer la valeur de la taille (extraire juste la taille si c'est "300 cm" par exemple)
                            variant_value = variant_text
                            if is_size:
                                # Extraire la taille (ex: "300 cm" -> "300 cm" ou "160x160 cm" -> "160x160 cm")
                                size_match = re.search(r'(\d+x?\d*\s*cm|\d+\s*couverts)', variant_text, re.I)
                                if size_match:
                                    variant_value = size_match.group(1)
                            
                            variant_data = {
                                'code': f"{variant_sku}_{variant_value}" if variant_sku else f"{slugify(full_name)}_{variant_value}",
                                'sku': variant_sku or sku or '',
                                'gencode': variant_gencode or '',
                                'size': variant_value if variant_type == "Taille" else '',
                                'full_code': variant_sku or sku or '',
                                'pa': None,
                                'pvc': variant_price or base_price or '',
                                'stock': None,
                                'color': variant_value if variant_type == "Couleur" else '',
                                'material': '',
                                'url': product_url,
                            }
                            variants.append(variant_data)
                            
                        except Exception as e:
                            logger.debug(f"Erreur lors du traitement du variant {variant_option.get('text', '')}: {e}")
                            continue
                
                # Si aucun variant trouvé ou traité, créer une variante par défaut
                if not variants:
                    variant_data = {
                        'code': sku if sku else slugify(full_name),
                        'sku': sku or '',
                        'gencode': '',
                        'size': '',
                        'full_code': sku or '',
                        'pa': None,
                        'pvc': price if price else '',
                        'stock': None,
                        'color': '',
                        'material': '',
                        'url': product_url,
                    }
                    variants.append(variant_data)
                    
            except Exception as e:
                logger.debug(f"Erreur lors de l'extraction des variants: {e}")
                # Fallback : créer une variante par défaut
                variant_data = {
                    'code': sku if sku else slugify(full_name),
                    'sku': sku or '',
                    'gencode': '',
                    'size': '',
                    'full_code': sku or '',
                    'pa': None,
                    'pvc': price if price else '',
                    'stock': None,
                    'color': '',
                    'material': '',
                    'url': product_url,
                }
                variants.append(variant_data)
        else:
            # Pas de driver, extraction simple depuis le HTML
            select_elements = soup.find_all('select')
            variant_options = {}
            
            for select in select_elements:
                select_name = select.get('name', '').lower()
                if 'color' in select_name or 'couleur' in select_name:
                    variant_options['color'] = []
                    for option in select.find_all('option'):
                        if option.get('value'):
                            variant_options['color'].append(option.get_text(strip=True))
                elif 'size' in select_name or 'taille' in select_name:
                    variant_options['size'] = []
                    for option in select.find_all('option'):
                        if option.get('value'):
                            variant_options['size'].append(option.get_text(strip=True))
            
            if variant_options:
                colors = variant_options.get('color', [''])
                sizes = variant_options.get('size', [''])
                
                for color in colors:
                    for size in sizes:
                        variant_data = {
                            'code': f"{sku}_{color}_{size}" if sku else f"{slugify(full_name)}_{color}_{size}",
                            'sku': sku or '',
                            'gencode': '',
                            'size': size,
                            'full_code': sku or '',
                            'pa': None,
                            'pvc': price if price else '',
                            'stock': None,
                            'color': color,
                            'material': '',
                            'url': product_url,
                        }
                        variants.append(variant_data)
            else:
                variant_data = {
                    'code': sku if sku else slugify(full_name),
                    'sku': sku or '',
                    'gencode': '',
                    'size': '',
                    'full_code': sku or '',
                    'pa': None,
                    'pvc': price if price else '',
                    'stock': None,
                    'color': '',
                    'material': '',
                    'url': product_url,
                }
                variants.append(variant_data)
        
        logger.info(f"Produit {full_name}: {len(variants)} variant(s), {len(images)} image(s)")
        
        # Récupérer le SKU et gencode depuis le premier variant
        product_sku = variants[0].get('sku', '') if variants else ''
        product_gencode = ''
        
        details = {
            'code': sku if sku else slugify(full_name),
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


def generate_shopify_csv(products_data: List[Dict]) -> pd.DataFrame:
    """
    Génère un DataFrame pandas au format CSV Shopify.
    Utilise la configuration centralisée pour les champs CSV.
    """
    logger.info("Génération du CSV Shopify...")
    
    # Obtenir la configuration CSV
    csv_config = get_csv_config()
    supplier = 'artiga'
    configured_columns = csv_config.get_columns(supplier)
    handle_source = csv_config.get_handle_source(supplier)
    vendor_name = csv_config.get_vendor(supplier)
    
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
        
        # Collecter les URLs des images
        image_urls = []
        for image_url in images:
            if image_url:
                image_urls.append(image_url)
        
        # Utiliser SKU et gencode depuis les détails du produit
        product_sku = product_details.get('sku', product_code)
        product_gencode = product_details.get('gencode', '')
        
        # Créer une ligne par variante
        for variant_idx, variant in enumerate(variants):
            variant_sku = variant.get('sku') or variant.get('full_code') or product_sku
            variant_gencode = variant.get('gencode') or product_gencode
            
            # Générer le Handle selon la source configurée
            if handle_source == 'barcode':
                handle = variant_gencode or product_gencode or ''
            elif handle_source == 'sku':
                handle = variant_sku or product_sku or ''
            elif handle_source == 'title':
                handle = slugify(full_name)
            else:
                handle = variant_gencode or product_gencode or slugify(full_name)
            
            # Créer un dictionnaire avec tous les champs Shopify par défaut
            base_row = {
                'Handle': handle or '',
                'Title': full_name or '',
                'Body (HTML)': description or '',
                'Vendor': vendor_name,
                'Product Category': '',
                'Type': category,
                'Tags': category,
                'Published': 'TRUE',
                'Option1 Name': 'Taille' if variant.get('size') else '',
                'Option1 Value': variant.get('size') or '',
                'Option2 Name': '',
                'Option2 Value': '',
                'Option3 Name': '',
                'Option3 Value': '',
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
                'Image Src': '',
                'Image Position': '',
                'Image Alt Text': '',
                'Gift Card': 'FALSE',
                'SEO Title': full_name or '',
                'SEO Description': (description[:160] if description else '') or '',
                'Google Shopping / Google Product Category': '',
                'Google Shopping / Gender': '',
                'Google Shopping / Age Group': '',
                'Google Shopping / MPN': variant.get('code') or '',
                'Google Shopping / Condition': 'new',
                'Google Shopping / Custom Product': 'FALSE',
                'Variant Image': image_urls[0] if image_urls and variant_idx == 0 else '',
                'Variant Weight Unit': 'kg',
                'Variant Tax Code': '',
                'Cost per item': variant.get('pa') or '',
                'Included / United States': '',
                'Price / United States': '',
                'Compare At Price / United States': '',
                'Included / International': '',
                'Price / International': '',
                'Compare At Price / International': '',
                'Status': 'active',
            }
            
            # Si pas d'images, créer une seule ligne sans images
            if not image_urls:
                rows.append(base_row.copy())
            else:
                # Créer une ligne par image
                for img_idx, image_url in enumerate(image_urls, start=1):
                    row = base_row.copy()
                    
                    # Pour la première image, garder toutes les infos
                    # Pour les images suivantes, vider les champs variant sauf Handle
                    if img_idx > 1:
                        row['Title'] = ''
                        row['Body (HTML)'] = ''
                        row['Vendor'] = ''
                        row['Product Category'] = ''
                        row['Type'] = ''
                        row['Tags'] = ''
                        row['Published'] = ''
                        row['Option1 Name'] = ''
                        row['Option1 Value'] = ''
                        row['Option2 Name'] = ''
                        row['Option2 Value'] = ''
                        row['Option3 Name'] = ''
                        row['Option3 Value'] = ''
                        row['Variant SKU'] = ''
                        row['Variant Grams'] = ''
                        row['Variant Inventory Tracker'] = ''
                        row['Variant Inventory Qty'] = ''
                        row['Variant Inventory Policy'] = ''
                        row['Variant Fulfillment Service'] = ''
                        row['Variant Price'] = ''
                        row['Variant Compare At Price'] = ''
                        row['Variant Requires Shipping'] = ''
                        row['Variant Taxable'] = ''
                        row['Variant Barcode'] = ''
                        row['Variant Image'] = ''
                        row['Variant Weight Unit'] = ''
                        row['Variant Tax Code'] = ''
                        row['Cost per item'] = ''
                        row['SEO Title'] = ''
                        row['SEO Description'] = ''
                        row['Google Shopping / Google Product Category'] = ''
                        row['Google Shopping / Gender'] = ''
                        row['Google Shopping / Age Group'] = ''
                        row['Google Shopping / MPN'] = ''
                        row['Google Shopping / Condition'] = ''
                        row['Google Shopping / Custom Product'] = ''
                        row['Included / United States'] = ''
                        row['Price / United States'] = ''
                        row['Compare At Price / United States'] = ''
                        row['Included / International'] = ''
                        row['Price / International'] = ''
                        row['Compare At Price / International'] = ''
                        row['Status'] = ''
                    
                    # Ajouter les informations de l'image
                    row['Image Src'] = image_url
                    row['Image Position'] = img_idx
                    row['Image Alt Text'] = full_name or ''
                    
                    rows.append(row)
    
    # Créer le DataFrame
    df = pd.DataFrame(rows)
    
    # S'assurer que toutes les colonnes configurées sont présentes
    for col in configured_columns:
        if col not in df.columns:
            df[col] = ''
    
    # Ne garder que les colonnes configurées (dans l'ordre)
    df = df[configured_columns]
    
    # Remplacer tous les NaN et None par des chaînes vides
    df = df.fillna('')
    df = df.replace([None, 'None', 'nan', 'NaN'], '')
    
    logger.info(f"CSV généré avec {len(df)} lignes et {len(df.columns)} colonnes")
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


def list_subcategories(driver: Optional[webdriver.Chrome], session: requests.Session, category_name: str):
    """
    Liste toutes les sous-catégories disponibles pour une catégorie donnée.
    """
    logger.info(f"Récupération de la liste des sous-catégories pour: {category_name}...")
    
    # Trouver la catégorie
    all_categories = get_categories(driver, session)
    target_category = None
    for cat in all_categories:
        if cat['name'].lower() == category_name.lower():
            target_category = cat
            break
    
    if not target_category:
        logger.error(f"Catégorie '{category_name}' non trouvée.")
        return []
    
    # Extraire les sous-catégories
    subcategories = get_subcategories(driver, session, target_category['url'], target_category['name'])
    
    if subcategories:
        print(f"\n=== Sous-catégories disponibles pour '{category_name}' ===")
        for idx, subcat in enumerate(subcategories, 1):
            print(f"{idx}. {subcat['name']}")
        print(f"\nTotal: {len(subcategories)} sous-catégories\n")
        return subcategories
    else:
        logger.warning(f"Aucune sous-catégorie trouvée pour '{category_name}'.")
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
        if any(selected in cat_name_lower or cat_name_lower in selected for selected in selected_lower):
            filtered.append(cat)
    
    return filtered


def main():
    """
    Fonction principale qui orchestre tout le processus.
    """
    global OUTPUT_CSV, OUTPUT_DIR
    
    parser = argparse.ArgumentParser(
        description='Extrait les produits du site Artiga (www.artiga.fr) et génère un fichier CSV pour Shopify.',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Exemples d'utilisation:
  # Lister les catégories disponibles
  python scraper-artiga.py --list-categories
  
  # Extraire une catégorie spécifique
  python scraper-artiga.py --category "Serviettes De Table"
  
  # Extraire plusieurs catégories
  python scraper-artiga.py --category "Serviettes De Table" --category "Nappes"
  
  # Limiter à 5 produits pour tester rapidement
  python scraper-artiga.py --category "Serviettes De Table" --limit 5 --preview
  
  # Voir le navigateur pendant l'extraction (débogage)
  python scraper-artiga.py --category "Serviettes De Table" --no-headless
        """
    )
    
    parser.add_argument(
        '--category', '-c',
        action='append',
        dest='categories',
        metavar='NOM',
        help='Catégorie à extraire (répétable pour plusieurs catégories)'
    )
    
    parser.add_argument(
        '--subcategory',
        action='append',
        dest='subcategories',
        metavar='NOM',
        help='Sous-catégorie à extraire (répétable pour plusieurs sous-catégories)'
    )
    
    parser.add_argument(
        '--list-categories', '-l',
        action='store_true',
        help='Affiche la liste des catégories disponibles et quitte'
    )
    
    parser.add_argument(
        '--list-subcategories',
        action='store_true',
        help='Affiche la liste des sous-catégories pour une catégorie donnée (nécessite --category)'
    )
    
    parser.add_argument(
        '--output', '-o',
        metavar='FICHIER',
        default=OUTPUT_CSV,
        help='Nom du fichier CSV de sortie (défaut: généré automatiquement)'
    )
    
    parser.add_argument(
        '--no-headless',
        action='store_true',
        help='Affiche le navigateur pendant l\'extraction (utile pour déboguer)'
    )
    
    parser.add_argument(
        '--preview',
        action='store_true',
        help='Affiche un aperçu des données avant de sauvegarder le CSV'
    )
    
    parser.add_argument(
        '--preview-rows',
        type=int,
        metavar='N',
        default=10,
        help='Nombre de lignes à afficher dans l\'aperçu (défaut: 10)'
    )
    
    parser.add_argument(
        '--limit',
        type=int,
        metavar='N',
        default=None,
        help='Limite le nombre de produits à extraire (utile pour tester rapidement)'
    )
    
    args = parser.parse_args()
    
    # Créer le répertoire de sortie s'il n'existe pas
    output_dir = OUTPUT_DIR
    if not os.path.exists(output_dir):
        os.makedirs(output_dir, exist_ok=True)
        logger.info(f"Répertoire de sortie créé: {output_dir}")
    
    # Générer le nom du fichier CSV automatiquement si non spécifié
    if args.output == OUTPUT_CSV:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        if args.categories and len(args.categories) > 0:
            if len(args.categories) == 1:
                category_slug = slugify(args.categories[0])
                OUTPUT_CSV = f"shopify_import_artiga_{category_slug}_{timestamp}.csv"
            else:
                category_slug = "_".join([slugify(cat)[:10] for cat in args.categories[:3]])
                OUTPUT_CSV = f"shopify_import_artiga_{category_slug}_{timestamp}.csv"
        else:
            base_name = OUTPUT_CSV.replace('.csv', '') if OUTPUT_CSV.endswith('.csv') else OUTPUT_CSV
            OUTPUT_CSV = f"{base_name}_{timestamp}.csv"
    else:
        OUTPUT_CSV = args.output
    
    # Construire le chemin complet du fichier CSV dans le répertoire de sortie
    # Si l'utilisateur a spécifié un chemin absolu ou un chemin avec répertoire, l'utiliser tel quel
    if os.path.isabs(OUTPUT_CSV) or '/' in OUTPUT_CSV or '\\' in OUTPUT_CSV:
        csv_path = OUTPUT_CSV
    else:
        csv_path = os.path.join(output_dir, OUTPUT_CSV)
    
    logger.info("Démarrage du scraper Artiga...")
    logger.info(f"Répertoire de sortie: {output_dir}")
    logger.info(f"Fichier CSV de sortie: {csv_path}")
    driver = None
    
    try:
        # Initialiser le driver et la session
        driver = get_selenium_driver(headless=not args.no_headless)
        session = requests.Session()
        session.headers.update(HEADERS)
        
        # Extraction des catégories
        all_categories = get_categories(driver, session)
        if not all_categories:
            logger.error("Aucune catégorie trouvée. Arrêt du script.")
            return
        
        # Si --list-categories, afficher et quitter
        if args.list_categories:
            list_categories(driver, session)
            return
        
        # Si --list-subcategories, afficher les sous-catégories et quitter
        if args.list_subcategories:
            if not args.categories or len(args.categories) == 0:
                logger.error("--list-subcategories nécessite --category")
                return
            for category_name in args.categories:
                list_subcategories(driver, session, category_name)
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
        
        # Extraction des produits
        all_products_data = []
        
        for category in categories:
            category_name = category['name']
            category_url = category['url']
            
            logger.info(f"Traitement de la catégorie: {category_name}")
            
            # Extraire les produits de la catégorie (passer args pour le filtrage des sous-catégories)
            products = get_products_from_category(driver, session, category_url, category_name, args)
            
            if not products:
                logger.warning(f"Aucun produit trouvé dans la catégorie {category_name}")
                continue
            
            # Appliquer la limite si spécifiée
            products_to_process = products
            if args.limit and args.limit > 0:
                products_to_process = products[:args.limit]
                logger.info(f"Limite activée: traitement de {len(products_to_process)} produit(s) sur {len(products)} trouvé(s)")
            
            for idx, product in enumerate(products_to_process, 1):
                logger.info(f"Traitement du produit {idx}/{len(products_to_process)}: {product['name']}")
                
                # Extraire les détails
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
        
        # Génération du CSV
        if all_products_data:
            df = generate_shopify_csv(all_products_data)
            
            # Afficher un aperçu si demandé
            if args.preview:
                pd.set_option('display.max_columns', None)
                pd.set_option('display.max_colwidth', 50)
                pd.set_option('display.width', None)
                pd.set_option('display.max_rows', args.preview_rows)
                
                print("\n" + "="*80)
                print("📊 APERÇU DU CSV SHOPIFY")
                print("="*80)
                
                preview_rows = args.preview_rows
                
                print(f"\n📈 Informations générales:")
                print(f"   • Total de lignes (variantes): {len(df)}")
                print(f"   • Total de colonnes: {len(df.columns)}")
                print(f"   • Produits uniques: {df['Handle'].nunique()}")
                
                important_cols = [
                    'Handle', 'Title', 'Variant SKU', 'Variant Price', 
                    'Variant Compare At Price', 'Variant Inventory Qty',
                    'Option1 Name', 'Option1 Value', 'Variant Barcode'
                ]
                
                available_cols = [col for col in important_cols if col in df.columns]
                
                # Filtrer pour ne montrer que les lignes avec des variantes (Variant SKU non vide)
                preview_df = df[df['Variant SKU'].notna() & (df['Variant SKU'] != '')]
                preview_df = preview_df[available_cols].head(preview_rows)
                
                print(f"\n📋 Premières {preview_rows} lignes avec données de variantes (colonnes principales):")
                print("-"*80)
                print(preview_df.to_string(index=False))
                
                if len(df) > preview_rows:
                    print(f"\n... ({len(df) - preview_rows} lignes supplémentaires)")
                
                print("\n" + "="*80)
            
            # Sauvegarder le CSV
            df.to_csv(csv_path, index=False, encoding='utf-8')
            logger.info(f"Fichier CSV généré: {csv_path}")
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

