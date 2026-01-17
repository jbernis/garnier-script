#!/usr/bin/env python3
"""
Script de scraping pour extraire les produits du site Cristel (https://www.cristel.com/)
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

# Configuration Cristel
BASE_URL = os.getenv("CRISTEL_BASE_URL", "https://www.cristel.com")
# Répertoire de sortie automatique basé sur le nom du fournisseur
# Peut être surchargé avec la variable d'environnement CRISTEL_OUTPUT_DIR
OUTPUT_DIR = os.getenv("CRISTEL_OUTPUT_DIR", "outputs/cristel")
OUTPUT_CSV = os.getenv("CRISTEL_OUTPUT_CSV", "shopify_import_cristel.csv")

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
        chrome_options.add_argument('--headless')
    chrome_options.add_argument('--no-sandbox')
    chrome_options.add_argument('--disable-dev-shm-usage')
    chrome_options.add_argument('--disable-blink-features=AutomationControlled')
    chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
    chrome_options.add_experimental_option('useAutomationExtension', False)
    chrome_options.add_argument(f'user-agent={HEADERS["User-Agent"]}')
    chrome_options.add_argument('--window-size=1920,1080')
    
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
    Extrait les catégories principales depuis le menu de navigation du site Cristel.
    Les catégories principales sont dans le menu avec class="liste".
    """
    logger.info("Extraction des catégories principales depuis Cristel...")
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
        
        # Chercher l'élément <ul class="liste"> qui contient les catégories principales
        liste_ul = soup.find('ul', class_='liste')
        
        if not liste_ul:
            logger.warning("Élément <ul class='liste'> non trouvé sur la page principale")
        else:
            seen_categories = set()
            
            # Chercher uniquement les <li class="categorie"> dans <ul class="liste">
            # Ce sont les vraies catégories principales, pas les sous-catégories
            category_lis = liste_ul.find_all('li', class_='categorie')
            
            for li in category_lis:
                # Chercher le lien dans ce <li>
                link = li.find('a', href=True)
                if not link:
                    continue
                
                href = link.get('href', '')
                text = link.get_text(strip=True)
                
                # Nettoyer le texte (supprimer les espaces multiples, etc.)
                text = ' '.join(text.split())
                
                # Exclure la dernière catégorie "Idées et cartes cadeaux"
                text_lower = text.lower()
                if 'idées' in text_lower and ('cartes cadeaux' in text_lower or 'carte cadeau' in text_lower):
                    continue
                
                # Filtrer les éléments qui ne sont pas des catégories valides
                if not text or len(text) < 3:
                    continue
                
                # Exclure les textes qui contiennent "icon", "product", "Created with Sketch", etc.
                if any(marker in text_lower for marker in ['icon', 'product', 'created with', 'sketch', 'bestseller', 'notre sélection']):
                    continue
                
                # Vérifier si c'est une catégorie valide
                if href:
                    # Construire l'URL complète
                    if href.startswith('http'):
                        category_url = href
                    else:
                        category_url = urljoin(BASE_URL, href)
                    
                    # Filtrer les liens qui ne sont pas des catégories
                    href_lower = href.lower()
                    if any(exclude in href_lower for exclude in ['/cart', '/checkout', '/account', '/search', '/contact', '/about', '/blog', 'javascript:', 'mailto:', '#', '/home', '/accueil']):
                        continue
                    
                    # Filtrer les liens de langue/navigation
                    if any(nav_word in text_lower for nav_word in ['accueil', 'home', 'contact', 'about', 'mentions', 'cgv', 'livraison', 'retour', 'english', 'deutsch', 'espanol']):
                        continue
                    
                    # Ajouter la catégorie si elle n'a pas déjà été vue
                    if category_url not in seen_categories:
                        categories.append({
                            'name': text,
                            'url': category_url
                        })
                        seen_categories.add(category_url)
        
        # Si pas de catégories trouvées avec class="liste", chercher dans le menu de navigation général
        if not categories:
            logger.info("Aucune catégorie trouvée avec class='liste', recherche dans le menu général...")
            nav_elements = soup.find_all(['nav', 'ul', 'div'], class_=re.compile(r'nav|menu', re.I))
            nav_links = []
            for nav_elem in nav_elements:
                nav_links.extend(nav_elem.find_all('a', href=True))
            
            for link in nav_links:
                href = link.get('href', '')
                text = link.get_text(strip=True)
                
                if text and len(text) > 2 and href and len(text.split()) <= 3:
                    if href.startswith('http'):
                        category_url = href
                    else:
                        category_url = urljoin(BASE_URL, href)
                    
                    href_lower = href.lower()
                    if any(exclude in href_lower for exclude in ['/cart', '/checkout', '/account', '/search', '/contact', '/about', '/blog', 'javascript:', 'mailto:', '#']):
                        continue
                    
                    text_lower = text.lower()
                    if any(nav_word in text_lower for nav_word in ['accueil', 'home', 'contact', 'about', 'mentions', 'cgv', 'livraison', 'retour', 'english', 'deutsch', 'espanol']):
                        continue
                    
                    if category_url not in seen_categories:
                        categories.append({
                            'name': text,
                            'url': category_url
                        })
                        seen_categories.add(category_url)
        
        logger.info(f"{len(categories)} catégorie(s) principale(s) trouvée(s)")
        return categories
        
    except Exception as e:
        logger.error(f"Erreur lors de l'extraction des catégories: {e}")
        return []


def get_subcategories(driver: Optional[webdriver.Chrome], session: requests.Session, category_url: str, category_name: str) -> List[Dict[str, str]]:
    """
    Extrait les sous-catégories d'une catégorie principale.
    Les sous-catégories se trouvent dans <ul class="sous_categorie"> sous chaque <li class="categorie">.
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
        
        # Chercher l'élément <ul class="liste"> qui contient toutes les catégories
        liste_ul = soup.find('ul', class_='liste')
        
        if not liste_ul:
            logger.warning("Élément <ul class='liste'> non trouvé")
            return []
        
        # Chercher le <li class="categorie"> correspondant à cette catégorie
        category_lis = liste_ul.find_all('li', class_='categorie')
        
        target_category_li = None
        for li in category_lis:
            link = li.find('a', href=True)
            if link:
                link_text = link.get_text(strip=True)
                if link_text == category_name:
                    target_category_li = li
                    break
        
        if not target_category_li:
            logger.warning(f"Catégorie '{category_name}' non trouvée dans le menu")
            return []
        
        # Chercher les <ul class="sous_categorie"> sous ce <li class="categorie">
        subcategory_uls = target_category_li.find_all('ul', class_='sous_categorie')
        
        seen_subcategories = set()
        
        for subcategory_ul in subcategory_uls:
            # Chercher les liens de sous-catégories dans cet élément
            # Chercher d'abord les liens avec class="link_produit" (comme "Sets")
            link_produit_links = subcategory_ul.find_all('a', class_='link_produit', href=True)
            # Puis chercher tous les autres liens
            other_links = subcategory_ul.find_all('a', href=True)
            # Combiner les deux listes en évitant les doublons
            all_links = link_produit_links + [link for link in other_links if link not in link_produit_links]
            
            for link in all_links:
                href = link.get('href', '')
                
                # Essayer d'abord d'extraire le texte depuis <span class="libelle"> si présent
                libelle_span = link.find('span', class_='libelle')
                if libelle_span:
                    text = libelle_span.get_text(strip=True)
                else:
                    # Sinon utiliser le texte du lien directement
                    text = link.get_text(strip=True)
                
                # Nettoyer le texte (supprimer les espaces multiples, etc.)
                text = ' '.join(text.split())
                
                # Filtrer les éléments qui ne sont pas des sous-catégories valides
                if not text or len(text) < 2:
                    continue
                
                # Exclure les textes qui contiennent "icon", "product", "Created with Sketch", etc.
                # Mais garder "Sets" même s'il y a "set" dans le texte
                text_lower = text.lower()
                if any(marker in text_lower for marker in ['icon', 'product', 'created with', 'sketch', 'bestseller', 'notre sélection']) and text_lower != 'sets':
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
                    
                    # Filtrer les liens de langue/navigation
                    if any(nav_word in text_lower for nav_word in ['accueil', 'home', 'contact', 'about', 'mentions', 'cgv', 'livraison', 'retour', 'english', 'deutsch', 'espanol']):
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
    Extrait la liste des produits d'une catégorie Cristel.
    Structure: Catégorie → Sous-catégories (class="liste") → Cartes produits → Page produit
    """
    logger.info(f"Extraction des produits de la catégorie: {category_name}")
    all_products = []
    
    try:
        if not driver:
            logger.error("Selenium driver requis pour naviguer entre les pages")
            return []
        
        # Vérifier et recréer le driver si nécessaire
        driver, session = check_and_recreate_driver(driver, session, headless=True)
        
        # Étape 1: Extraire les sous-catégories de cette catégorie principale
        all_subcategories = get_subcategories(driver, session, category_url, category_name)
        
        # Filtrer les sous-catégories si spécifiées (via args.subcategories)
        if args and hasattr(args, 'subcategories') and args.subcategories:
            # Filtrer les sous-catégories selon la sélection
            selected_subcategories = []
            selected_lower = [name.lower().strip() for name in args.subcategories]
            
            for subcat in all_subcategories:
                subcat_name_lower = subcat['name'].lower()
                if any(selected in subcat_name_lower or subcat_name_lower in selected for selected in selected_lower):
                    selected_subcategories.append(subcat)
            
            if selected_subcategories:
                subcategories = selected_subcategories
                logger.info(f"Filtrage: {len(subcategories)} sous-catégorie(s) sélectionnée(s) sur {len(all_subcategories)} disponible(s)")
            else:
                logger.warning(f"Aucune sous-catégorie trouvée correspondant à: {', '.join(args.subcategories)}")
                logger.info(f"Sous-catégories disponibles pour {category_name}:")
                for subcat in all_subcategories:
                    logger.info(f"  - {subcat['name']}")
                subcategories = []
        else:
            subcategories = all_subcategories
        
        # Si pas de sous-catégories trouvées, essayer directement avec la catégorie principale
        if not subcategories:
            logger.info(f"Aucune sous-catégorie trouvée pour {category_name}, extraction directe depuis la catégorie...")
            subcategories = [{'name': category_name, 'url': category_url, 'parent': category_name}]
        
        # Étape 2: Pour chaque sous-catégorie, extraire les produits (cartes)
        # seen_product_urls pour éviter les doublons entre sous-catégories
        seen_product_urls = set()
        
        def get_next_page_url_cristel(driver: webdriver.Chrome, current_url: str) -> Optional[str]:
            """
            Détecte et retourne l'URL de la page suivante pour Cristel.
            Retourne None s'il n'y a pas de page suivante.
            """
            try:
                html = driver.page_source
                soup = BeautifulSoup(html, 'html.parser')
                
                # Chercher les éléments de pagination communs pour Cristel
                next_selectors = [
                    'a[aria-label*="suivant" i]',
                    'a[aria-label*="next" i]',
                    'a[title*="suivant" i]',
                    'a[title*="next" i]',
                    'a.pagination-next',
                    'a.pager-next',
                    'a.next',
                    'a[rel="next"]',
                    '.pagination .next',
                    '.pager .next'
                ]
                
                # Chercher avec Selenium d'abord
                for selector in next_selectors:
                    try:
                        if ':contains(' in selector:
                            xpath = "//a[contains(text(), 'Suivant') or contains(text(), 'Next')]"
                            next_links = driver.find_elements(By.XPATH, xpath)
                        else:
                            next_links = driver.find_elements(By.CSS_SELECTOR, selector)
                        
                        for link in next_links:
                            if link.is_enabled() and link.is_displayed():
                                href = link.get_attribute('href')
                                if href and href != current_url:
                                    if 'disabled' not in (link.get_attribute('class') or ''):
                                        return href
                    except:
                        continue
                
                # Chercher avec BeautifulSoup
                pagination = soup.find(['nav', 'div', 'ul'], class_=re.compile(r'pagination|pager', re.I))
                if pagination:
                    next_link = pagination.find('a', string=re.compile(r'suivant|next', re.I))
                    if not next_link:
                        next_link = pagination.find('a', attrs={'rel': 'next'})
                    if not next_link:
                        next_link = pagination.find('a', class_=re.compile(r'next', re.I))
                    
                    if next_link:
                        href = next_link.get('href', '')
                        if href and 'disabled' not in next_link.get('class', []):
                            if href.startswith('http'):
                                return href
                            else:
                                return urljoin(BASE_URL, href)
                
                # Chercher les numéros de page
                page_links = soup.find_all('a', href=re.compile(r'page=|p='))
                current_page = 1
                max_page = 1
                
                for page_link in page_links:
                    href = page_link.get('href', '')
                    page_match = re.search(r'[?&](?:page|p)=(\d+)', href)
                    if page_match:
                        page_num = int(page_match.group(1))
                        max_page = max(max_page, page_num)
                        if current_url in href or driver.current_url in href:
                            current_page = page_num
                
                if current_page < max_page:
                    if '?' in current_url:
                        next_url = f"{current_url.split('?')[0]}?page={current_page + 1}"
                    else:
                        next_url = f"{current_url}?page={current_page + 1}"
                    return next_url
                
                return None
                
            except Exception as e:
                logger.debug(f"Erreur lors de la détection de pagination Cristel: {e}")
                return None
        
        for subcategory in subcategories:
            subcategory_name = subcategory['name']
            subcategory_url = subcategory['url']
            
            logger.info(f"Traitement de la sous-catégorie: {subcategory_name}")
            
            # Gérer la pagination pour cette sous-catégorie
            current_url = subcategory_url
            page_num = 1
            max_pages = 100  # Limite de sécurité
            
            while current_url and page_num <= max_pages:
                try:
                    logger.debug(f"Chargement de la sous-catégorie (page {page_num}): {current_url}")
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
                    
                    # Attendre que les produits soient chargés (éléments avec images ou liens produits)
                    try:
                        WebDriverWait(driver, 10).until(
                            EC.presence_of_element_located((By.CSS_SELECTOR, 'a[href*="/product"], a[href*="/products"], img, [class*="product"], [class*="card"]'))
                        )
                    except TimeoutException:
                        logger.debug("Timeout en attendant le chargement des produits")
                    
                    html = driver.page_source
                    soup = BeautifulSoup(html, 'html.parser')
                    
                    # Vérifier si on est sur une page 404 ou erreur
                    page_title = soup.find('title')
                    if page_title and ('404' in page_title.get_text() or 'erreur' in page_title.get_text().lower()):
                        logger.warning(f"Page d'erreur détectée pour {subcategory_url}. Vérification de l'URL...")
                        continue
                    
                    # Chercher les produits dans le div id="liste_produits" avec data-redirect-urls
                    product_links = []
                    
                    try:
                        # Stratégie principale: Chercher le div id="liste_produits"
                        liste_produits = driver.find_element(By.ID, 'liste_produits')
                        
                        # Chercher tous les div avec data-redirect-urls dans ce conteneur
                        product_divs = liste_produits.find_elements(By.CSS_SELECTOR, 'div[data-redirect-url]')
                        
                        logger.debug(f"Trouvé {len(product_divs)} div(s) avec data-redirect-url dans liste_produits")
                        
                        for div_elem in product_divs:
                            redirect_url = div_elem.get_attribute('data-redirect-url')
                            if redirect_url:
                                # Construire l'URL complète
                                if redirect_url.startswith('http'):
                                    product_url = redirect_url
                                else:
                                    product_url = urljoin(BASE_URL, redirect_url)
                                
                                # Extraire le nom du produit depuis le div (titre, texte, etc.)
                                try:
                                    # Chercher un titre dans le div
                                    title_elem = div_elem.find_element(By.CSS_SELECTOR, 'h1, h2, h3, h4, h5, h6, [class*="title"], [class*="name"]')
                                    product_name = title_elem.text.strip()
                                except:
                                    # Si pas de titre, utiliser le texte du div
                                    product_name = div_elem.text.strip()[:100]
                                
                                # Chercher l'image du produit
                                image_url = None
                                try:
                                    img_elem = div_elem.find_element(By.CSS_SELECTOR, 'img')
                                    image_url = img_elem.get_attribute('src') or img_elem.get_attribute('data-src') or img_elem.get_attribute('data-lazy-src')
                                    if image_url and not image_url.startswith('http'):
                                        image_url = urljoin(BASE_URL, image_url)
                                except:
                                    pass
                                
                                product_links.append({
                                    'href': product_url,
                                    'text': product_name,
                                    'selenium_elem': div_elem,
                                    'image_url': image_url
                                })
                        
                        logger.info(f"Selenium (liste_produits): Trouvé {len(product_links)} produit(s) dans {subcategory_name}")
                        
                    except NoSuchElementException:
                        logger.debug("Div id='liste_produits' non trouvé, utilisation de méthodes alternatives...")
                        # Fallback: Chercher avec BeautifulSoup
                        liste_produits_soup = soup.find('div', id='liste_produits')
                        if liste_produits_soup:
                            # Chercher les div avec data-redirect-url
                            product_divs_soup = liste_produits_soup.find_all('div', attrs={'data-redirect-url': True})
                            logger.debug(f"BeautifulSoup: Trouvé {len(product_divs_soup)} div(s) avec data-redirect-url")
                            
                            for div_elem in product_divs_soup:
                                redirect_url = div_elem.get('data-redirect-url', '')
                                if redirect_url:
                                    if redirect_url.startswith('http'):
                                        product_url = redirect_url
                                    else:
                                        product_url = urljoin(BASE_URL, redirect_url)
                                    
                                    # Extraire le nom
                                    title_elem = div_elem.find(['h1', 'h2', 'h3', 'h4', 'h5', 'h6']) or div_elem.find(class_=re.compile(r'title|name', re.I))
                                    product_name = title_elem.get_text(strip=True) if title_elem else div_elem.get_text(strip=True)[:100]
                                    
                                    # Chercher l'image
                                    img = div_elem.find('img')
                                    image_url = None
                                    if img:
                                        image_url = img.get('src') or img.get('data-src') or img.get('data-lazy-src')
                                        if image_url and not image_url.startswith('http'):
                                            image_url = urljoin(BASE_URL, image_url)
                                    
                                    product_links.append({
                                        'href': product_url,
                                        'text': product_name,
                                        'selenium_elem': None,
                                        'image_url': image_url
                                    })
                            
                            logger.info(f"BeautifulSoup (liste_produits): Trouvé {len(product_links)} produit(s) dans {subcategory_name}")
                        else:
                            logger.warning("Div id='liste_produits' non trouvé, utilisation de méthodes de fallback...")
                            # Fallback: Chercher les liens /products/ ou /product/
                            try:
                                selenium_product_links = driver.find_elements(By.CSS_SELECTOR, 
                                    'a[href*="/product"], a[href*="/products"]')
                                
                                for elem in selenium_product_links:
                                    href = elem.get_attribute('href')
                                    if href and '/products/' in href.lower():
                                        product_links.append({
                                            'href': href,
                                            'text': elem.text.strip(),
                                            'selenium_elem': elem,
                                            'image_url': None
                                        })
                            except:
                                pass
                    
                    except Exception as e:
                        logger.error(f"Erreur lors de la recherche des produits: {e}")
                        # Fallback vers BeautifulSoup
                        try:
                            liste_produits_soup = soup.find('div', id='liste_produits')
                            if liste_produits_soup:
                                product_divs_soup = liste_produits_soup.find_all('div', attrs={'data-redirect-url': True})
                                for div_elem in product_divs_soup:
                                    redirect_url = div_elem.get('data-redirect-url', '')
                                    if redirect_url:
                                        if redirect_url.startswith('http'):
                                            product_url = redirect_url
                                        else:
                                            product_url = urljoin(BASE_URL, redirect_url)
                                        
                                        title_elem = div_elem.find(['h1', 'h2', 'h3', 'h4', 'h5', 'h6'])
                                        product_name = title_elem.get_text(strip=True) if title_elem else div_elem.get_text(strip=True)[:100]
                                        
                                        img = div_elem.find('img')
                                        image_url = None
                                        if img:
                                            image_url = img.get('src') or img.get('data-src')
                                            if image_url and not image_url.startswith('http'):
                                                image_url = urljoin(BASE_URL, image_url)
                                        
                                        product_links.append({
                                            'href': product_url,
                                            'text': product_name,
                                            'selenium_elem': None,
                                            'image_url': image_url
                                        })
                        except:
                            pass
                    
                    logger.info(f"Total de {len(product_links)} produit(s) trouvé(s) dans {subcategory_name}")
                    
                    # Traiter chaque produit trouvé depuis data-redirect-url
                    seen_product_urls_local = set()
                    
                    for product_data in product_links:
                        # Les données sont déjà dans un format dict avec href, text, image_url
                        product_url = product_data.get('href', '')
                        product_name = product_data.get('text', '')
                        image_url = product_data.get('image_url')
                        
                        if not product_url:
                            continue
                        
                        # Éviter les doublons
                        if product_url in seen_product_urls_local or product_url in seen_product_urls:
                            continue
                        
                        seen_product_urls_local.add(product_url)
                        
                        # Filtrer les liens qui ne sont pas des produits
                        href_lower = product_url.lower()
                        if any(exclude in href_lower for exclude in ['/cart', '/checkout', '/account', '/search', '/contact', '/about', '/blog', '/newsletter', 'javascript:', 'mailto:', '#']):
                            continue
                        
                        # Nettoyer le nom du produit
                        if not product_name or len(product_name) < 3:
                            # Extraire depuis l'URL
                            url_parts = product_url.split('/')
                            if len(url_parts) > 1:
                                product_name = url_parts[-1].replace('-', ' ').title()
                            else:
                                continue
                        
                        # Valider le nom du produit (ne doit pas être un lien de navigation/langue)
                        product_name_lower = product_name.lower()
                        invalid_names = [
                            'english', 'deutsch', 'espanol', 'français', 'french', 'german', 'spanish',
                            'j\'ai déjà', 'déjà un compte', 'se connecter', 'connexion', 'login',
                            'mon compte', 'my account', 'panier', 'cart', 'recherche', 'search',
                            'accueil', 'home', 'contact', 'about', 'mentions'
                        ]
                        if any(invalid in product_name_lower for invalid in invalid_names):
                            continue
                        
                        # Le nom ne doit pas être juste une combinaison de lettres de langue
                        if re.match(r'^(fr|en|de|es)+$', product_name_lower.replace(' ', '')):
                            continue
                        
                        # Construire l'URL complète de l'image si nécessaire
                        if image_url and not image_url.startswith('http'):
                            image_url = urljoin(BASE_URL, image_url)
                        
                        all_products.append({
                            'name': product_name,
                            'url': product_url,
                            'image_url': image_url
                        })
                        seen_product_urls.add(product_url)
                    
                    logger.info(f"Page {page_num}: {len(product_links)} produit(s) trouvé(s) dans {subcategory_name}")
                    
                    # Vérifier s'il y a une page suivante
                    next_url = get_next_page_url_cristel(driver, current_url)
                    if next_url and next_url != current_url:
                        current_url = next_url
                        page_num += 1
                        time.sleep(2)  # Petite pause entre les pages
                    else:
                        # Pas de page suivante, on arrête pour cette sous-catégorie
                        break
                        
                except Exception as e:
                    logger.error(f"Erreur lors de l'extraction des produits de la sous-catégorie {subcategory_name} (page {page_num}): {e}")
                # En cas d'erreur, essayer de passer à la page suivante si possible
                try:
                    next_url = get_next_page_url_cristel(driver, current_url)
                    if next_url and next_url != current_url:
                        current_url = next_url
                        page_num += 1
                        continue
                except:
                    pass
                # Si pas de page suivante ou erreur, passer à la sous-catégorie suivante
                break
        
        logger.info(f"{len(all_products)} produit(s) trouvé(s) dans la catégorie {category_name} ({len(subcategories)} sous-catégorie(s))")
        
        # Si aucun produit trouvé, essayer de trouver depuis la page d'accueil
        if not all_products:
            logger.warning(f"Aucun produit trouvé dans {category_url}, tentative depuis la page d'accueil...")
            try:
                driver.get(BASE_URL)
                time.sleep(5)
                
                # Faire défiler pour charger les produits
                try:
                    last_height = driver.execute_script("return document.body.scrollHeight")
                    scroll_pause_time = 2
                    for _ in range(3):  # Limiter à 3 scrolls
                        driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
                        time.sleep(scroll_pause_time)
                        new_height = driver.execute_script("return document.body.scrollHeight")
                        if new_height == last_height:
                            break
                        last_height = new_height
                except:
                    pass
                
                html_home = driver.page_source
                soup_home = BeautifulSoup(html_home, 'html.parser')
                
                # Chercher les produits sur la page d'accueil
                home_product_links = soup_home.find_all('a', href=re.compile(r'/products/', re.I))
                
                # Filtrer par catégorie si possible (chercher dans le texte ou autour)
                for link in home_product_links:
                    href = link.get('href', '')
                    if not href:
                        continue
                    
                    # Vérifier si le produit correspond à la catégorie recherchée
                    text = link.get_text(strip=True).lower()
                    category_lower = category_name.lower()
                    
                    # Si le nom de la catégorie est dans le texte du lien ou autour
                    parent = link.find_parent(['div', 'article', 'li', 'section'])
                    parent_text = parent.get_text(strip=True).lower() if parent else ''
                    
                    if category_lower in text or category_lower in parent_text:
                        if href.startswith('http'):
                            product_url = href
                        else:
                            product_url = urljoin(BASE_URL, href)
                        
                        if product_url not in seen_product_urls:
                            product_name = link.get_text(strip=True) or parent_text[:100] if parent else href.split('/')[-1].replace('-', ' ').title()
                            
                            # Chercher l'image
                            image_url = None
                            img = link.find('img') or (parent.find('img') if parent else None)
                            if img:
                                image_url = img.get('src') or img.get('data-src') or img.get('data-lazy-src')
                                if image_url:
                                    image_url = urljoin(BASE_URL, image_url)
                            
                            all_products.append({
                                'name': product_name,
                                'url': product_url,
                                'image_url': image_url
                            })
                            seen_product_urls.add(product_url)
                
                if all_products:
                    logger.info(f"Trouvé {len(all_products)} produit(s) depuis la page d'accueil pour la catégorie {category_name}")
            except Exception as e:
                logger.debug(f"Erreur lors de la recherche depuis la page d'accueil: {e}")
        
        return all_products
        
    except Exception as e:
        logger.error(f"Erreur lors de l'extraction des produits de {category_name}: {e}")
        return []


def get_product_details(driver: Optional[webdriver.Chrome], session: requests.Session, product_url: str, product_name: str, headless: bool = True) -> tuple:
    """
    Extrait les détails complets d'un produit Cristel depuis sa page.
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
                    logger.debug("Données JSON-LD trouvées")
            except json.JSONDecodeError as e:
                logger.debug(f"Erreur lors du parsing JSON-LD: {e}")
        
        # Extraire le nom du produit depuis le HTML (comme avant)
        # Chercher d'abord le h1
        h1_elem = soup.find('h1')
        h1_text = h1_elem.get_text(strip=True) if h1_elem else ''
        
        # Chercher le h2 (souvent la collection)
        h2_elem = soup.find('h2')
        h2_text = h2_elem.get_text(strip=True) if h2_elem else ''
        
        # Construire le titre complet : h1 + h2 si h2 existe
        if h1_text:
            if h2_text:
                full_name = f"{h1_text} {h2_text}"
            else:
                full_name = h1_text
        else:
            # Fallback sur title ou product_name
            title_elem = soup.find('title')
            full_name = title_elem.get_text(strip=True) if title_elem else product_name
        
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
            desc_selectors = [
                {'class': re.compile(r'description|product-description|product-details', re.I)},
                {'id': re.compile(r'description|product-description', re.I)},
                {'itemprop': 'description'}
            ]
            
            for selector in desc_selectors:
                desc_elem = soup.find(['div', 'section', 'p'], selector)
                if desc_elem:
                    description_html = str(desc_elem)
                    break
            
            # Si pas trouvé, chercher dans les paragraphes
            if not description_html:
                paragraphs = soup.find_all('p', class_=re.compile(r'description|content', re.I))
                if paragraphs:
                    description_html = ' '.join([str(p) for p in paragraphs[:5] if p.get_text(strip=True)])
            
            description = description_html
        
        # Extraire le prix
        price = ""
        
        # Essayer d'abord avec Selenium si disponible (pour le JavaScript)
        if driver:
            try:
                # Attendre que le prix soit chargé
                time.sleep(2)
                
                # Chercher le prix avec plusieurs sélecteurs CSS
                price_selectors_css = [
                    '[class*="price"]',
                    '[itemprop="price"]',
                    '[data-price]',
                    '.product-price',
                    '.price',
                    '.current-price',
                    '.product__price',
                ]
                
                for css_selector in price_selectors_css:
                    try:
                        price_elem = driver.find_element(By.CSS_SELECTOR, css_selector)
                        if price_elem:
                            price_text = price_elem.text.strip()
                            # Nettoyer les retours à la ligne et autres caractères indésirables
                            price_text = price_text.replace('\n', ' ').replace('\r', ' ').replace('\t', ' ')
                            # Extraire le prix numérique
                            price_match = re.search(r'([\d\s,]+\.?\d*)', price_text.replace('€', '').replace('\xa0', ' '))
                            if price_match:
                                price_value = price_match.group(1).replace(' ', '').replace(',', '.').strip()
                                # Vérifier que c'est un prix raisonnable (entre 1 et 10000)
                                try:
                                    price_float = float(price_value)
                                    if 1 <= price_float <= 10000:
                                        price = price_value
                                        logger.debug(f"Prix trouvé via Selenium: {price}")
                                        break
                                except:
                                    pass
                    except:
                        continue
            except Exception as e:
                logger.debug(f"Erreur lors de l'extraction du prix avec Selenium: {e}")
        
        # Si pas trouvé avec Selenium, utiliser BeautifulSoup
        if not price:
            price_selectors = [
                {'class': re.compile(r'price|prix|current-price', re.I)},
                {'itemprop': 'price'},
                {'data-price': True}
            ]
            
            for selector in price_selectors:
                price_elem = soup.find(['span', 'div', 'p', 'meta'], selector)
                if price_elem:
                    if price_elem.name == 'meta':
                        price_text = price_elem.get('content', '')
                    else:
                        price_text = price_elem.get_text(strip=True)
                    # Nettoyer les retours à la ligne et autres caractères indésirables
                    price_text = price_text.replace('\n', ' ').replace('\r', ' ').replace('\t', ' ')
                    # Extraire le prix numérique
                    price_match = re.search(r'([\d\s,]+\.?\d*)', price_text.replace('€', '').replace('\xa0', ' ').replace(' ', ''))
                    if price_match:
                        price_value = price_match.group(1).replace(',', '.').strip()
                        try:
                            price_float = float(price_value)
                            if 1 <= price_float <= 10000:
                                price = price_value
                                logger.debug(f"Prix trouvé via BeautifulSoup: {price}")
                                break
                        except:
                            pass
        
        # Extraire le SKU/Référence
        sku = ""
        
        # Essayer d'abord avec Selenium si disponible
        if driver:
            try:
                sku_selectors_css = [
                    '[class*="sku"]',
                    '[class*="reference"]',
                    '[itemprop="sku"]',
                    '[data-product-id]',
                    '.product-sku',
                    '.sku',
                    '.product-reference',
                ]
                
                for css_selector in sku_selectors_css:
                    try:
                        sku_elem = driver.find_element(By.CSS_SELECTOR, css_selector)
                        if sku_elem:
                            sku_text = sku_elem.text.strip() or sku_elem.get_attribute('content') or sku_elem.get_attribute('data-product-id') or ''
                            if sku_text:
                                sku_match = re.search(r'[:\s]*([A-Z0-9-]+)', sku_text, re.I)
                                if sku_match:
                                    sku = sku_match.group(1).strip()
                                    logger.debug(f"SKU trouvé via Selenium: {sku}")
                                    break
                    except:
                        continue
            except Exception as e:
                logger.debug(f"Erreur lors de l'extraction du SKU avec Selenium: {e}")
        
        # Si pas trouvé avec Selenium, utiliser BeautifulSoup
        if not sku:
            sku_selectors = [
                {'class': re.compile(r'reference|sku|product-reference|product-id', re.I)},
                {'itemprop': 'sku'},
                {'data-product-id': True}
            ]
            
            for selector in sku_selectors:
                sku_elem = soup.find(['span', 'div', 'p', 'meta'], selector)
                if sku_elem:
                    sku_text = sku_elem.get_text(strip=True) if sku_elem.name != 'meta' else sku_elem.get('content', '')
                    if not sku_text:
                        sku_text = sku_elem.get('data-product-id', '')
                    sku_match = re.search(r'[:\s]*([A-Z0-9-]+)', sku_text, re.I)
                    if sku_match:
                        sku = sku_match.group(1).strip()
                        logger.debug(f"SKU trouvé via BeautifulSoup: {sku}")
                        break
        
        # Si pas de SKU trouvé, utiliser l'ID produit depuis l'URL ou data-product-id
        if not sku:
            product_id_elem = soup.find(attrs={'data-product-id': True})
            if product_id_elem:
                sku = product_id_elem.get('data-product-id', '')
            else:
                # Extraire depuis l'URL (dernière partie de l'URL)
                url_match = re.search(r'/products/([^/?]+)', product_url)
                if url_match:
                    sku_candidate = url_match.group(1)
                    # Utiliser seulement si ça ressemble à un SKU (pas juste un slug)
                    if re.match(r'^[A-Z0-9-]+$', sku_candidate, re.I) and len(sku_candidate) > 5:
                        sku = sku_candidate
                    else:
                        # Sinon utiliser le slug comme SKU de secours
                        sku = sku_candidate.replace('-', '_').upper()
        
        # Extraire les images depuis #images-slider uniquement
        images = []
        
        # Méthode 1: Avec Selenium en priorité (pour le contenu JavaScript dynamique)
        if driver:
            try:
                images_slider_elem = driver.find_element(By.ID, 'images-slider')
                if images_slider_elem:
                    img_elements = images_slider_elem.find_elements(By.TAG_NAME, 'img')
                    for img_elem in img_elements:
                        # Uniquement les images avec attribut src (pas data-src)
                        src = img_elem.get_attribute('src')
                        if src and src.strip():
                            image_url = urljoin(BASE_URL, src) if not src.startswith('http') else src
                            if image_url not in images:
                                images.append(image_url)
            except Exception as e:
                logger.debug(f"Erreur lors de l'extraction des images avec Selenium: {e}")
        
        # Méthode 2: Avec BeautifulSoup si Selenium n'a pas trouvé d'images
        if not images:
            images_slider = soup.find('div', id='images-slider')
            if images_slider:
                img_tags = images_slider.find_all('img')
                for img in img_tags:
                    # Uniquement les images avec attribut src
                    src = img.get('src')
                    if src and src.strip():
                        image_url = urljoin(BASE_URL, src)
                        if image_url not in images:
                            images.append(image_url)
        
        # Fallback: Si #images-slider n'existe pas, utiliser l'ancienne méthode mais filtrée
        if not images:
            logger.warning("Div #images-slider non trouvé, utilisation de la méthode de fallback...")
            img_tags = soup.find_all('img')
            for img in img_tags:
                src = img.get('src') or img.get('data-src') or img.get('data-lazy-src') or img.get('data-original')
                if src:
                    # Filtrer les images de produits (exclure logos, icônes, etc.)
                    src_lower = src.lower()
                    if any(pattern in src_lower for pattern in ['product', 'produit', 'cristel.com']):
                        if 'logo' not in src_lower and 'icon' not in src_lower and 'avatar' not in src_lower:
                            image_url = urljoin(BASE_URL, src)
                            if image_url not in images:
                                images.append(image_url)
        
        # Extraire les variants depuis JSON-LD (priorité)
        variants = []
        
        if json_ld_data and 'offers' in json_ld_data:
            # Extraire les variants depuis le JSON-LD
            offers = json_ld_data['offers']
            if isinstance(offers, list):
                # Plusieurs variants
                for offer in offers:
                    variant_sku = offer.get('sku', '')
                    variant_gtin = offer.get('GTIN', '')
                    variant_price = str(offer.get('price', ''))
                    variant_mpn = offer.get('mpn', '')
                    variant_availability = offer.get('availability', '')
                    
                    # Déterminer la taille depuis le SKU ou MPN si possible
                    size = ''
                    if variant_sku:
                        # Essayer d'extraire la taille depuis le SKU (ex: C14Q -> 14)
                        size_match = re.search(r'(\d+)', variant_sku)
                        if size_match:
                            size = size_match.group(1) + ' cm'
                    
                    variant_data = {
                        'code': variant_sku or variant_mpn or '',
                        'sku': variant_sku or '',
                        'gencode': variant_gtin or '',
                        'size': size,
                        'full_code': variant_sku or variant_mpn or '',
                        'pa': None,  # Prix de comparaison (non disponible dans JSON-LD)
                        'pvc': variant_price if variant_price else '',
                        'stock': None,  # Stock non disponible dans JSON-LD
                        'color': '',
                        'material': '',
                        'url': product_url,
                    }
                    variants.append(variant_data)
                    logger.debug(f"Variant extrait depuis JSON-LD: SKU={variant_sku}, GTIN={variant_gtin}, Prix={variant_price}")
            elif isinstance(offers, dict):
                # Un seul variant
                variant_sku = offers.get('sku', '')
                variant_gtin = offers.get('GTIN', '')
                variant_price = str(offers.get('price', ''))
                variant_mpn = offers.get('mpn', '')
                
                size = ''
                if variant_sku:
                    size_match = re.search(r'(\d+)', variant_sku)
                    if size_match:
                        size = size_match.group(1) + ' cm'
                
                variant_data = {
                    'code': variant_sku or variant_mpn or '',
                    'sku': variant_sku or '',
                    'gencode': variant_gtin or '',
                    'size': size,
                    'full_code': variant_sku or variant_mpn or '',
                    'pa': None,
                    'pvc': variant_price if variant_price else '',
                    'stock': None,
                    'color': '',
                    'material': '',
                    'url': product_url,
                }
                variants.append(variant_data)
                logger.debug(f"Variant unique extrait depuis JSON-LD: SKU={variant_sku}, GTIN={variant_gtin}, Prix={variant_price}")
        
        # Si pas de variants trouvés dans JSON-LD, utiliser l'ancienne méthode
        # Ne créer des variants que si on n'en a pas déjà depuis JSON-LD
        if not variants:
            if driver:
                try:
                    # Chercher les options de variantes (selects, boutons, etc.)
                    variant_selects = driver.find_elements(By.CSS_SELECTOR, 
                        'select[name*="option"], select[id*="option"], select[name*="variant"], select[name*="size"], select[name*="diameter"]')
                    
                    variant_options_list = []
                    
                    # Traiter les selects
                    for select_elem in variant_selects:
                        try:
                            select = Select(select_elem)
                            options = select.options
                            for option in options:
                                option_value = option.get_attribute('value')
                                option_text = option.text.strip()
                                
                                if option_value and option_text and option_value != '':
                                    variant_options_list.append({
                                        'type': 'select',
                                        'element': select_elem,
                                        'value': option_value,
                                        'text': option_text,
                                        'option': option
                                    })
                        except Exception as e:
                            logger.debug(f"Erreur avec select: {e}")
                    
                    # Chercher aussi les boutons/liens de variants
                    variant_buttons = driver.find_elements(By.CSS_SELECTOR,
                        'button[data-value], a[data-value], .product-variant, .variant-option')
                    
                    for button in variant_buttons:
                        try:
                            variant_value = button.get_attribute('data-value') or ''
                            variant_text = button.text.strip()
                            
                            if variant_value or variant_text:
                                variant_options_list.append({
                                    'type': 'button',
                                    'element': button,
                                    'value': variant_value,
                                    'text': variant_text
                                })
                        except Exception as e:
                            logger.debug(f"Erreur avec button: {e}")
                    
                    # Si on a trouvé des variants, traiter chacun
                    if variant_options_list:
                        logger.info(f"Trouvé {len(variant_options_list)} option(s) de variant")
                        
                        base_price = price
                        
                        for variant_option in variant_options_list:
                            try:
                                # Sélectionner le variant
                                if variant_option['type'] == 'select':
                                    select = Select(variant_option['element'])
                                    select.select_by_value(variant_option['value'])
                                    time.sleep(2)  # Attendre la mise à jour
                                else:
                                    variant_option['element'].click()
                                    time.sleep(2)
                                
                                # Extraire le prix après sélection
                                variant_price = base_price
                                
                                # Chercher le prix mis à jour
                                try:
                                    price_elem = driver.find_element(By.CSS_SELECTOR, 
                                        '[class*="price"], [itemprop="price"]')
                                    price_text = price_elem.text.strip()
                                    # Nettoyer les retours à la ligne et autres caractères indésirables
                                    price_text = price_text.replace('\n', ' ').replace('\r', ' ').replace('\t', ' ')
                                    price_match = re.search(r'([\d,]+\.?\d*)', price_text.replace('€', '').replace(' ', '').replace('\xa0', ''))
                                    if price_match:
                                        variant_price = price_match.group(1).replace(',', '.').strip()
                                except:
                                    pass
                                
                                # Récupérer le SKU du variant
                                variant_sku = sku
                                try:
                                    sku_elem = driver.find_element(By.CSS_SELECTOR,
                                        '[class*="sku"], [class*="reference"]')
                                    sku_text = sku_elem.text.strip()
                                    sku_match = re.search(r'[:\s]*([A-Z0-9-]+)', sku_text, re.I)
                                    if sku_match:
                                        variant_sku = sku_match.group(1).strip()
                                except:
                                    pass
                                
                                # Déterminer le type de variant
                                variant_text = variant_option.get('text', '').strip()
                                variant_value_raw = variant_option.get('value', variant_text)
                                
                                # Déterminer si c'est une taille (contient "cm", "diamètre", "Ø", etc.)
                                is_size = any(keyword in variant_text.lower() for keyword in ['cm', 'diamètre', 'diameter', 'ø', 'taille', 'size'])
                                variant_type = "Taille" if is_size else "Option"
                                
                                variant_data = {
                                    'code': f"{variant_sku}_{variant_value_raw}" if variant_sku else f"{slugify(full_name)}_{variant_value_raw}",
                                    'sku': variant_sku or sku or '',
                                    'gencode': '',
                                    'size': variant_text if variant_type == "Taille" else '',
                                    'full_code': variant_sku or sku or '',
                                    'pa': None,
                                    'pvc': variant_price or base_price or '',
                                    'stock': None,
                                    'color': '',
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
                    # Fallback : créer une variante par défaut seulement si on n'en a pas déjà
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
                
                # Si toujours pas de variants après toutes les tentatives avec driver, créer un variant par défaut
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
            # Pas de driver, extraction simple depuis le HTML
            # Ne créer des variants que si on n'en a pas déjà depuis JSON-LD
            if not variants:
                select_elements = soup.find_all('select')
                variant_options = {}
                
                for select in select_elements:
                    select_name = select.get('name', '').lower()
                    if 'size' in select_name or 'taille' in select_name or 'diameter' in select_name or 'diamètre' in select_name:
                        variant_options['size'] = []
                        for option in select.find_all('option'):
                            if option.get('value'):
                                variant_options['size'].append(option.get_text(strip=True))
                    elif 'color' in select_name or 'couleur' in select_name:
                        variant_options['color'] = []
                        for option in select.find_all('option'):
                            if option.get('value'):
                                variant_options['color'].append(option.get_text(strip=True))
                
                if variant_options:
                    sizes = variant_options.get('size', [''])
                    colors = variant_options.get('color', [''])
                    
                    for size in sizes:
                        for color in colors:
                            variant_data = {
                                'code': f"{sku}_{size}_{color}" if sku else f"{slugify(full_name)}_{size}_{color}",
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
        
        # Récupérer le SKU depuis le premier variant
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
    supplier = 'cristel'
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
        
        # Collecter les URLs des images (uniquement les images, pas les vidéos)
        image_urls = []
        for image_url in images:
            if image_url:
                image_urls.append(image_url)
        
        # Utiliser SKU depuis les détails du produit
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
                'Variant Price': str(variant.get('pvc') or '').replace('\n', '').replace('\r', '').strip(),
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
                # Créer une ligne par image/vidéo
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
    global OUTPUT_CSV
    
    parser = argparse.ArgumentParser(
        description='Extrait les produits du site Cristel (www.cristel.com) et génère un fichier CSV pour Shopify.',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Exemples d'utilisation:
  # Lister les catégories disponibles
  python scraper-cristel.py --list-categories
  
  # Lister les catégories principales
  python scraper-cristel.py --list-categories
  
  # Lister les sous-catégories d'une catégorie
  python scraper-cristel.py --category "Poêles" --list-subcategories
  
  # Extraire une catégorie spécifique (toutes les sous-catégories)
  python scraper-cristel.py --category "Poêles"
  
  # Extraire une sous-catégorie spécifique
  python scraper-cristel.py --category "Poêles" --subcategory "Poêles amovibles"
  
  # Extraire plusieurs sous-catégories
  python scraper-cristel.py --category "Poêles" --subcategory "Poêles amovibles" --subcategory "Poêles fixes"
  
  # Extraire plusieurs catégories
  python scraper-cristel.py --category "Poêles" --category "Casseroles"
  
  # Générer un fichier CSV par catégorie
  python scraper-cristel.py --category "Poêles" --category "Casseroles" --per-category
  
  # Limiter à 5 produits pour tester rapidement
  python scraper-cristel.py --category "Poêles" --subcategory "Poêles amovibles" --limit 5 --preview
  
  # Voir le navigateur pendant l'extraction (débogage)
  python scraper-cristel.py --category "Poêles" --no-headless
        """
    )
    
    parser.add_argument(
        '--category', '-c',
        action='append',
        dest='categories',
        metavar='NOM',
        help='Catégorie principale à extraire (répétable pour plusieurs catégories)'
    )
    
    parser.add_argument(
        '--subcategory', '-s',
        action='append',
        dest='subcategories',
        metavar='NOM',
        help='Sous-catégorie à extraire (doit être utilisée avec --category). Répétable pour plusieurs sous-catégories.'
    )
    
    parser.add_argument(
        '--list-categories', '-l',
        action='store_true',
        help='Affiche la liste des catégories principales disponibles et quitte'
    )
    
    parser.add_argument(
        '--list-subcategories',
        action='store_true',
        help='Affiche la liste des sous-catégories disponibles pour les catégories spécifiées avec --category'
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
    
    parser.add_argument(
        '--per-category',
        action='store_true',
        help='Génère un fichier CSV séparé pour chaque catégorie (au lieu d\'un seul fichier pour toutes les catégories)'
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
                OUTPUT_CSV = f"shopify_import_cristel_{category_slug}_{timestamp}.csv"
            else:
                category_slug = "_".join([slugify(cat)[:10] for cat in args.categories[:3]])
                OUTPUT_CSV = f"shopify_import_cristel_{category_slug}_{timestamp}.csv"
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
    
    logger.info("Démarrage du scraper Cristel...")
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
        
        # Récupérer le répertoire de sortie (défini plus haut)
        output_dir = OUTPUT_DIR
        if not os.path.exists(output_dir):
            os.makedirs(output_dir, exist_ok=True)
        
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
        
        # Si --list-subcategories, afficher les sous-catégories et quitter
        if args.list_subcategories:
            if not args.categories:
                logger.error("--list-subcategories nécessite --category pour spécifier la catégorie principale")
                return
            
            print("\n=== Sous-catégories disponibles ===")
            for category in categories:
                category_name = category['name']
                category_url = category['url']
                print(f"\n📁 Catégorie: {category_name}")
                subcategories = get_subcategories(driver, session, category_url, category_name)
                if subcategories:
                    for idx, subcat in enumerate(subcategories, 1):
                        print(f"  {idx}. {subcat['name']}")
                    print(f"  Total: {len(subcategories)} sous-catégorie(s)")
                else:
                    print("  Aucune sous-catégorie trouvée")
            print()
            return
        
        # Extraction des produits
        all_products_data = []
        
        # Si --per-category, traiter chaque catégorie séparément
        if args.per_category:
            logger.info("Mode --per-category activé: génération d'un fichier CSV par catégorie")
            
            for category in categories:
                category_name = category['name']
                category_url = category['url']
                
                logger.info(f"Traitement de la catégorie: {category_name}")
                
                # Extraire les produits de la catégorie
                products = get_products_from_category(driver, session, category_url, category_name, args)
                
                if not products:
                    logger.warning(f"Aucun produit trouvé dans la catégorie {category_name}")
                    continue
                
                # Appliquer la limite si spécifiée
                products_to_process = products
                if args.limit and args.limit > 0:
                    products_to_process = products[:args.limit]
                    logger.info(f"Limite activée: traitement de {len(products_to_process)} produit(s) sur {len(products)} trouvé(s)")
                
                # Extraire les détails de tous les produits de cette catégorie
                category_products_data = []
                
                for idx, product in enumerate(products_to_process, 1):
                    logger.info(f"Traitement du produit {idx}/{len(products_to_process)}: {product['name']}")
                    
                    # Extraire les détails
                    details, driver, session = get_product_details(driver, session, product['url'], product['name'], headless=not args.no_headless)
                    
                    if details:
                        category_products_data.append({
                            'category': category_name,
                            'image_url': product.get('image_url'),
                            'details': details,
                            'session': session,
                            'driver': driver
                        })
                    
                    # Petite pause pour ne pas surcharger le serveur
                    time.sleep(0.5)
                
                # Générer le CSV pour cette catégorie
                if category_products_data:
                    df = generate_shopify_csv(category_products_data)
                    
                    # Générer le nom du fichier pour cette catégorie
                    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                    category_slug = slugify(category_name)
                    category_output_csv = os.path.join(output_dir, f"shopify_import_cristel_{category_slug}_{timestamp}.csv")
                    
                    # Afficher un aperçu si demandé (seulement pour la première catégorie)
                    if args.preview and category == categories[0]:
                        pd.set_option('display.max_columns', None)
                        pd.set_option('display.max_colwidth', 50)
                        pd.set_option('display.width', None)
                        pd.set_option('display.max_rows', args.preview_rows)
                        
                        print("\n" + "="*80)
                        print(f"📊 APERÇU DU CSV SHOPIFY - {category_name}")
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
                        
                        print(f"\n📋 Premières {preview_rows} lignes avec données de variantes (colonnes principales):")
                        print("-"*80)
                        # Filtrer pour ne montrer que les lignes avec des données de variantes (SKU non vide)
                        variants_df = df[df['Variant SKU'].notna() & (df['Variant SKU'] != '')]
                        if len(variants_df) > 0:
                            preview_df = variants_df[available_cols].head(preview_rows)
                            print(preview_df.to_string(index=False))
                            if len(variants_df) > preview_rows:
                                print(f"\n... ({len(variants_df) - preview_rows} variantes supplémentaires)")
                        else:
                            # Si pas de variantes filtrées, afficher les premières lignes normales
                            preview_df = df[available_cols].head(preview_rows)
                            print(preview_df.to_string(index=False))
                            if len(df) > preview_rows:
                                print(f"\n... ({len(df) - preview_rows} lignes supplémentaires)")
                        
                        print("\n" + "="*80)
                    
                    # Sauvegarder le CSV pour cette catégorie
                    df.to_csv(category_output_csv, index=False, encoding='utf-8')
                    logger.info(f"Fichier CSV généré pour {category_name}: {category_output_csv}")
                    logger.info(f"Total: {len(df)} lignes (variantes de produits)")
                else:
                    logger.warning(f"Aucun produit trouvé dans la catégorie {category_name}. Aucun fichier CSV généré.")
        else:
            # Mode normal: un seul fichier CSV pour toutes les catégories
            for category in categories:
                category_name = category['name']
                category_url = category['url']
                
                logger.info(f"Traitement de la catégorie: {category_name}")
                
                # Extraire les produits de la catégorie
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
            
            # Génération du CSV pour toutes les catégories
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
                    
                    print(f"\n📋 Premières {preview_rows} lignes avec données de variantes (colonnes principales):")
                    print("-"*80)
                    # Filtrer pour ne montrer que les lignes avec des données de variantes (SKU non vide)
                    variants_df = df[df['Variant SKU'].notna() & (df['Variant SKU'] != '')]
                    if len(variants_df) > 0:
                        preview_df = variants_df[available_cols].head(preview_rows)
                        print(preview_df.to_string(index=False))
                        if len(variants_df) > preview_rows:
                            print(f"\n... ({len(variants_df) - preview_rows} variantes supplémentaires)")
                    else:
                        # Si pas de variantes filtrées, afficher les premières lignes normales
                        preview_df = df[available_cols].head(preview_rows)
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

