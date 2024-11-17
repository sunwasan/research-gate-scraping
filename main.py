from seleniumbase import Driver
from bs4 import BeautifulSoup
from datetime import datetime
from tqdm import tqdm
import requests
import logging
import json 
import re
import os

file_dir = os.path.dirname(os.path.abspath(__file__))

destination_dir = os.path.join(file_dir, 'data')
log_dir = os.path.join(file_dir, 'logs')
os.makedirs(destination_dir, exist_ok=True)
os.makedirs(log_dir, exist_ok=True)
   
   
 
def get_research_urls(
    query:str,
    max_results:int=100
    ) -> list:
    """ 
    Get the ResearchGate URLs from Google search results
    """
    base_url = "https://www.google.com/search?q="
    all_research_urls = []
    full_query = f"site:researchgate.net {query}"
    query = base_url + full_query.replace(" ", "+")
    
    # Calculate how many pages you need to load (each page has 10 results)
    pages_to_load = (max_results // 10)
    
    logging.info(f"[get_research_urls] Loading {pages_to_load} pages of Google search results\nurl: {query}")
    
    for page in range(pages_to_load):
        start = page * 10  # Google search pagination (start=0, start=10, start=20, etc.)
        query_url = f"{query}&start={start}"
        

        soup = get_page_source(query_url)
        
        # Find all the links that might contain the researchgate URLs
        all_a = soup.find_all('a', href=True)
        hrefs = [a['href'] for a in all_a]
        
        # Use regex to find all the ResearchGate URLs
        research_urls = re.findall(r'(https?://www.researchgate.net\S+)', str(hrefs))
        all_research_urls.extend(research_urls)
        logging.info(f"[get_research_urls] Found {len(research_urls)} ResearchGate URLs on page {page + 1}")
        # Stop if we've gathered enough URLs (up to max_results)
        if len(all_research_urls) >= max_results or len(research_urls) == 0:
            logging.info(f"[get_research_urls] Found {len(all_research_urls)} ResearchGate URLs in total")
            break

    # Return the filtered URLs (trim to max_results if needed)
    return all_research_urls[:max_results]

def get_page_source(url:str) -> BeautifulSoup:
    """
    Get the page source of the ResearchGate page
    """
    driver = Driver(
        browser="chrome",
        uc=True,                   # Enables undetectable mode
        headless=False,            # Set to True if headless mode is needed
        incognito=True,            # Opens in incognito mode
        agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/112.0.5615.138 Safari/537.36",  # Custom user agent
        undetectable=True          # Additional undetectable options
    )
    driver.uc_open_with_reconnect(url, 4)
    driver.uc_gui_click_captcha()
    src_page = driver.page_source
    soup = BeautifulSoup(src_page, 'html.parser')
    driver.quit()
    return soup

def extract_abstract(soup: BeautifulSoup) -> dict:
    """
    Extract the abstract from the ResearchGate page
    """
    abstract = soup.find_all('div', attrs={'itemprop':'description'})[0].text
    head = soup.find_all('h1')[0].text
    return {head:abstract}

def save_json(data:dict, filename:str) -> None:
    """
    Save the data to a JSON file
    """
    if os.path.exists(filename):
        with open(filename, 'r') as f:
            old_data = json.load(f)
        old_data.update(data)
        with open(filename, 'w') as f:
            json.dump(old_data, f)
    else:
        with open(filename, 'w') as f:
            json.dump(data, f)

def get_n_save_abstract(url:str, kw:str, max_results:int) -> None:
    """ 
    Get the abstract from the ResearchGate page and save it to a JSON file
    """
    
    # now = datetime.now().strftime("%Y-%m-%d-%H-%M-%S")
    today = datetime.now().strftime("%Y-%m-%d")
    destination_path = os.path.join(destination_dir, f'{today}_{kw}_{max_results}_abstracts.json')
    
    try:
        soup = get_page_source(url)
        abstract = extract_abstract(soup)
        save_json(abstract, destination_path)
    except Exception as e:
        logging.error(f"[get_n_save_abstract(url = {url}, kw = {kw}, max_results = {max_results}) Error: {e}")
        pass            
        
def main(query:str, max_results:int):
    urls = get_research_urls(query, max_results)
    for url in tqdm(urls, desc="Downloading Abstracts" , unit="page", total=len(urls), position=0, leave=True):
        get_n_save_abstract(url, query, max_results)  
    n_abstracts = len(urls)
    logging.info(f"[main] Downloaded {n_abstracts} abstracts for the query: {query}")

if __name__ == "__main__":
    query = "banana waste"
    now = datetime.now().strftime("%Y-%m-%d-%H-%M-%S")
    logging.basicConfig(filename=os.path.join(log_dir, f"{query.replace(" ","_")}_{now}.log"), level=logging.INFO)
    max_results = 1000
    main(query, max_results)