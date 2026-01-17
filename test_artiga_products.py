#!/usr/bin/env python3
"""
Script de test pour inspecter la structure HTML des produits Artiga.
"""

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from bs4 import BeautifulSoup
import time
import re
from urllib.parse import urljoin

BASE_URL = "https://www.artiga.fr"

def test_artiga_subcategory():
    """Teste l'extraction des produits depuis une sous-catégorie Artiga."""
    chrome_options = Options()
    chrome_options.add_argument('--headless')
    chrome_options.add_argument('--no-sandbox')
    chrome_options.add_argument('--disable-dev-shm-usage')
    
    driver = webdriver.Chrome(options=chrome_options)
    
    try:
        # URL de la sous-catégorie Nappes dans Table
        # On doit d'abord trouver l'URL exacte
        driver.get("https://www.artiga.fr/table")
        time.sleep(5)
        
        html = driver.page_source
        soup = BeautifulSoup(html, 'html.parser')
        
        # Chercher les sous-catégories
        print("=== SOUS-CATÉGORIES TROUVÉES ===")
        subcategory_links = soup.find_all('a', href=re.compile(r'/table|/nappes', re.I))
        for link in subcategory_links[:10]:
            href = link.get('href', '')
            text = link.get_text(strip=True)
            if text and ('nappe' in text.lower() or '/nappes' in href.lower()):
                print(f"  {text}: {href}")
        
        # Aller sur la page nappes
        nappes_url = "https://www.artiga.fr/nappes"
        print(f"\n=== TEST SUR: {nappes_url} ===")
        driver.get(nappes_url)
        time.sleep(5)
        
        html = driver.page_source
        soup = BeautifulSoup(html, 'html.parser')
        
        # Chercher tous les liens
        print("\n=== TOUS LES LIENS (premiers 20) ===")
        all_links = soup.find_all('a', href=True)
        for i, link in enumerate(all_links[:20], 1):
            href = link.get('href', '')
            text = link.get_text(strip=True)[:50]
            if href and not href.startswith('#'):
                print(f"  {i}. {text[:30]:<30} -> {href[:60]}")
        
        # Chercher les articles
        print("\n=== ARTICLES TROUVÉS ===")
        articles = soup.find_all('article')
        print(f"  Total articles: {len(articles)}")
        for i, article in enumerate(articles[:5], 1):
            classes = article.get('class', [])
            data_id = article.get('data-product-id', '')
            print(f"  Article {i}: classes={classes}, data-product-id={data_id}")
            link = article.find('a', href=True)
            if link:
                print(f"    -> Lien: {link.get('href', '')[:60]}")
        
        # Chercher les divs avec classe product
        print("\n=== DIVS AVEC CLASSE PRODUCT ===")
        product_divs = soup.find_all('div', class_=re.compile(r'product', re.I))
        print(f"  Total divs product: {len(product_divs)}")
        for i, div in enumerate(product_divs[:5], 1):
            classes = div.get('class', [])
            print(f"  Div {i}: classes={classes}")
            link = div.find('a', href=True)
            if link:
                print(f"    -> Lien: {link.get('href', '')[:60]}")
        
        # Chercher data-product-id
        print("\n=== ÉLÉMENTS AVEC data-product-id ===")
        data_ids = soup.find_all(attrs={'data-product-id': True})
        print(f"  Total: {len(data_ids)}")
        for i, elem in enumerate(data_ids[:5], 1):
            data_id = elem.get('data-product-id', '')
            tag = elem.name
            classes = elem.get('class', [])
            print(f"  {i}. <{tag}> data-product-id={data_id}, classes={classes}")
        
    finally:
        driver.quit()

if __name__ == '__main__':
    test_artiga_subcategory()

