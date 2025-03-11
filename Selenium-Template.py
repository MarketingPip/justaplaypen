from selenium import webdriver
from selenium.webdriver.chrome.options import Options
import chromedriver_autoinstaller
import requests
from bs4 import BeautifulSoup
import csv
import time
import random
from fake_useragent import UserAgent
import cloudscraper
from datetime import datetime

# Install ChromeDriver
chromedriver_autoinstaller.install()

# Initialize fake user agent and scraper
ua = UserAgent()
scraper = cloudscraper.create_scraper()

def get_memorial_links(base_url, max_pages=10):
    """Fetch memorial links using Selenium and close the driver immediately after use."""
    chrome_options = Options()
    options = [
        "--window-size=1200,1200",
        "--ignore-certificate-errors",
        "--headless",
        "--no-sandbox",
        "--disable-dev-shm-usage",
        "--remote-debugging-port=9222"
    ]
    
    for option in options:
        chrome_options.add_argument(option)
    
    memorial_links = []
    
    with webdriver.Chrome(options=chrome_options) as driver:
        driver.get(base_url)
        last_height = driver.execute_script("return document.body.scrollHeight")
        
        while True:
            driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            time.sleep(random.uniform(2, 4))  # Allow content to load
            new_height = driver.execute_script("return document.body.scrollHeight")
            if new_height == last_height:
                break
            last_height = new_height
        
        elements = driver.find_elements("css selector", "a[href*='/memorial/']")
        for elem in elements:
            link = elem.get_attribute("href")
            if link and link not in memorial_links:
                memorial_links.append(link)
    
    return memorial_links

def parse_date(date_string):
    """Convert date format from '4 Jun 1871' to 'YYYY-MM-DD'."""
    try:
        return datetime.strptime(date_string, "%d %b %Y").strftime("%Y-%m-%d")
    except ValueError:
        return None

def extract_family_members(family_section):
    """Extract family member details."""
    family_members = []
    if family_section:
        family_items = family_section.find_all("li", itemscope=True)
        for item in family_items:
            name = item.select_one("h3[itemprop='name']").text.strip() if item.select_one("h3[itemprop='name']") else None
            birth_date = item.select_one("span[itemprop='birthDate']").text.strip() if item.select_one("span[itemprop='birthDate']") else None
            death_date = item.select_one("span[itemprop='deathDate']").text.strip() if item.select_one("span[itemprop='deathDate']") else None
            profile_url = item.find("a", itemprop="url")["href"] if item.find("a", itemprop="url") else None
            
            family_members.append({
                "name": name,
                "birth_date": parse_date(birth_date) if birth_date else None,
                "death_date": parse_date(death_date) if death_date else None,
                "profile_url": profile_url
            })
    return family_members

def extract_memorial_data(memorial_url):
    """Extract memorial details from the page."""
    headers = {"User-Agent": ua.random}
    response = scraper.get(memorial_url, headers=headers)
    
    if response.status_code != 200:
        print(f"Failed to retrieve {memorial_url}")
        return None
    
    soup = BeautifulSoup(response.text, "html.parser")
    
    birth_date_raw = soup.select_one("#birthDateLabel").text.strip() if soup.select_one("#birthDateLabel") else None
    birth_date = parse_date(birth_date_raw) if birth_date_raw else None
    
    image_url = soup.select_one("#profileImage")["src"] if soup.select_one("#profileImage") else None
    
    family_grid = soup.select_one("#family-grid")
    parents = extract_family_members(family_grid.select_one("ul[aria-labelledby='parentsLabel']")) if family_grid else []
    spouses = extract_family_members(family_grid.select_one("ul[aria-labelledby='spouseLabel']")) if family_grid else []
    
    gps = None
    gps_span = soup.select_one("#gpsLocation")
    if gps_span:
        link = gps_span.find("a")
        if link and "google.com/maps" in link["href"]:
            coords = link["href"].split("q=")[1].split("&")[0].split(",")
            if len(coords) == 2:
                gps = {"latitude": coords[0], "longitude": coords[1]}
    
    return {
        "memorial_url": memorial_url,
        "name": soup.select_one("#bio-name").text.strip() if soup.select_one("#bio-name") else None,
        "birth_date": birth_date,
        "death_date": soup.select_one("#deathDateLabel").text.strip() if soup.select_one("#deathDateLabel") else None,
        "cemetery": soup.select_one("#cemeteryNameLabel").text.strip() if soup.select_one("#cemeteryNameLabel") else None,
        "location": soup.select_one("#cemeteryCityName").text.strip() if soup.select_one("#cemeteryCityName") else None,
        "bio": soup.select_one("#inscriptionValue").decode_contents().replace('<br>', '\n').strip() if soup.select_one("#inscriptionValue") else None,
        "gps": gps,
        "image_url": image_url,
        "parents": parents,
        "spouses": spouses
    }

def main():
    base_url = "https://www.findagrave.com/memorial/search?location=Crediton%2C+Huron+County%2C+Ontario%2C+Canada&locationId=city_252602"
    memorial_links = get_memorial_links(base_url, max_pages=5)
    
    with open("findagrave_data.csv", "w", newline="") as csvfile:
        fieldnames = ["memorial_url", "name", "birth_date", "death_date", "cemetery", "location", "bio", "gps", "image_url", "parents", "spouses"]
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        writer.writeheader()
        
        for url in memorial_links:
            data = extract_memorial_data(url)
            if data:
                writer.writerow(data)
                print(f"Extracted: {data}")
                time.sleep(random.uniform(1, 3))

if __name__ == "__main__":
    main()
