import requests
from bs4 import BeautifulSoup
import csv
import time
import random
from fake_useragent import UserAgent
import cloudscraper  # To handle Cloudflare protection
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.chrome.options import Options

# Initialize fake user agent for randomizing User-Agent header
ua = UserAgent()

# Cloudflare scraper that bypasses JS challenges
scraper = cloudscraper.create_scraper()

def get_memorial_links(base_url, max_pages=10):
    memorial_links = []
    options = Options()
    options.add_argument("--headless")
    options.add_argument("--disable-gpu")
    options.add_argument(f"user-agent={ua.random}")
    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)
    driver.get(base_url)
    time.sleep(3)  # Allow page to load

    # Scroll to bottom to load all results
    last_height = driver.execute_script("return document.body.scrollHeight")
    while True:
        driver.find_element(By.TAG_NAME, "body").send_keys(Keys.END)
        time.sleep(2)
        new_height = driver.execute_script("return document.body.scrollHeight")
        if new_height == last_height:
            break
        last_height = new_height
    
    # Extract memorial links
    soup = BeautifulSoup(driver.page_source, "html.parser")
    for link in soup.find_all("a", href=True, class_="memorial-search-result-link"):  # Adjust class as needed
        full_url = "https://www.findagrave.com" + link["href"]
        if full_url not in memorial_links:
            memorial_links.append(full_url)
    
    driver.quit()
    return memorial_links

def extract_memorial_data(memorial_url):
    headers = {
        "User-Agent": ua.random,
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.5",
        "Connection": "keep-alive",
    }
    response = scraper.get(memorial_url, headers=headers)
    if response.status_code != 200:
        print("Failed to retrieve page.")
        return None

    soup = BeautifulSoup(response.text, "html.parser")
    data = {
        "memorial_url": memorial_url,
        "name": soup.select_one(".memorial-name").text.strip() if soup.select_one(".memorial-name") else None,
        "image_url": soup.select_one(".memorial-image img")["src"] if soup.select_one(".memorial-image img") else None,
        "birth_date": soup.select_one(".birthDate").text.strip() if soup.select_one(".birthDate") else None,
        "death_date": soup.select_one(".deathDate").text.strip() if soup.select_one(".deathDate") else None,
        "cemetery": soup.select_one(".cemetery-name").text.strip() if soup.select_one(".cemetery-name") else None,
        "location": soup.select_one(".cemetery-location").text.strip() if soup.select_one(".cemetery-location") else None,
        "biography": soup.select_one(".bio-text").text.strip() if soup.select_one(".bio-text") else None,
        "family": [fam.text.strip() for fam in soup.select(".family-member")] if soup.select(".family-member") else [],
    }

    gps_span = soup.select_one("#gpsLocation")
    if gps_span:
        link = gps_span.find("a")
        if link and "google.com/maps" in link.get("href", ""):
            parts = link["href"].split("q=")
            if len(parts) > 1:
                coords = parts[1].split("&")[0].split(",")
                if len(coords) == 2:
                    data["latitude"], data["longitude"] = coords[0], coords[1]
    
    return data

def main():
    base_url = "https://www.findagrave.com/memorial/search?firstname=&middlename=&lastname=&birthyear=&birthyearfilter=&deathyear=&deathyearfilter=&location=Crediton%2C+Huron+County%2C+Ontario%2C+Canada&locationId=city_252602&bio=&linkedToName=&plot=&memorialid=&mcid=&datefilter=&orderby=r"
    memorial_links = get_memorial_links(base_url, max_pages=5)
    
    with open("findagrave_data.csv", "w", newline="") as csvfile:
        fieldnames = ["memorial_url", "name", "image_url", "birth_date", "death_date", "cemetery", "location", "biography", "family", "latitude", "longitude"]
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        writer.writeheader()
        
        for url in memorial_links:
            data = extract_memorial_data(url)
            if data:
                writer.writerow(data)
                print(f"Extracted: {data['name']} ({url})")
            time.sleep(random.uniform(1, 3))

if __name__ == "__main__":
    main()
