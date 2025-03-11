from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
import chromedriver_autoinstaller
from pyvirtualdisplay import Display
import requests
from bs4 import BeautifulSoup
import csv
import time
import random
from fake_useragent import UserAgent
import cloudscraper
from concurrent.futures import ThreadPoolExecutor

# Initialize virtual display for headless mode
display = Display(visible=0, size=(800, 800))  
display.start()

# Install and configure ChromeDriver
chromedriver_autoinstaller.install()
chrome_options = webdriver.ChromeOptions()
options = [
  "--window-size=1200,1200",
  "--ignore-certificate-errors",
  "--headless",
  "--no-sandbox",
  "--disable-dev-shm-usage",
  '--remote-debugging-port=9222'
]
for option in options:
    chrome_options.add_argument(option)

driver = webdriver.Chrome(options=chrome_options)

# Initialize fake user agent and scraper
ua = UserAgent()
scraper = cloudscraper.create_scraper()  # This automatically bypasses Cloudflare

# Define headers to be used for bypassing detection
headers = {
    "User-Agent": ua.random,
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8",
    "Accept-Encoding": "gzip, deflate, br",
    "Accept-Language": "en-US,en;q=0.9",
    "Connection": "keep-alive",
    "Upgrade-Insecure-Requests": "1",
    "Cache-Control": "max-age=0"
}

def get_memorial_links(base_url, max_pages=10):
    driver.get(base_url)
    last_height = driver.execute_script("return document.body.scrollHeight")
    
    while True:
        driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        time.sleep(random.uniform(2, 4))  # Allow content to load
        new_height = driver.execute_script("return document.body.scrollHeight")
        if new_height == last_height:
            break
        last_height = new_height
    
    memorial_links = []
    elements = driver.find_elements("css selector", "a[href*='/memorial/']")
    for elem in elements:
        link = elem.get_attribute("href")
        if link and link not in memorial_links:
            memorial_links.append(link)
    
    return memorial_links

def extract_memorial_data(memorial_url):
    try:
        # Using cloudscraper to bypass Cloudflare's protection
        response = scraper.get(memorial_url, headers=headers)
        if response.status_code != 200:
            print(f"Failed to retrieve {memorial_url}")
            return None
        
        soup = BeautifulSoup(response.text, "html.parser")
        data = {
            "memorial_url": memorial_url,
            "name": soup.select_one("#bio-name").text.strip() if soup.select_one("#bio-name") else None,
            "birth_date": soup.select_one("#birthDateLabel").text.strip() if soup.select_one("#birthDateLabel") else None,
            "death_date": soup.select_one("#deathDateLabel").text.strip() if soup.select_one("#deathDateLabel") else None,
            "cemetery": soup.select_one("#cemeteryNameLabel").text.strip() if soup.select_one("#cemeteryNameLabel") else None,
            "location": soup.select_one("#cemeteryCityName").text.strip() if soup.select_one("#cemeteryCityName") else None,
            "bio": soup.select_one("#inscriptionValue").decode_contents().replace('<br>', '\n').strip() if soup.select_one("#inscriptionValue") else None,
            "gps": None
        }
        
        gps_span = soup.select_one("#gpsLocation")
        if gps_span:
            link = gps_span.find("a")
            if link and "google.com/maps" in link["href"]:
                coords = link["href"].split("q=")[1].split("&")[0].split(",")
                if len(coords) == 2:
                    data["gps"] = {"latitude": coords[0], "longitude": coords[1]}
        
        return data
    
    except Exception as e:
        print(f"Error extracting data from {memorial_url}: {e}")
        return None

def save_data_to_csv(data_list, filename="findagrave_data.csv"):
    with open(filename, "a", newline="") as csvfile:
        fieldnames = ["memorial_url", "name", "birth_date", "death_date", "cemetery", "location", "bio", "gps"]
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        for data in data_list:
            writer.writerow(data)

def main():
    base_url = "https://www.findagrave.com/memorial/search?location=Crediton%2C+Huron+County%2C+Ontario%2C+Canada&locationId=city_252602"
    memorial_links = get_memorial_links(base_url, max_pages=5)
    
    # Write header to CSV file
    with open("findagrave_data.csv", "w", newline="") as csvfile:
        fieldnames = ["memorial_url", "name", "birth_date", "death_date", "cemetery", "location", "bio", "gps"]
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        writer.writeheader()
    
    # Use ThreadPoolExecutor to extract data in parallel
    with ThreadPoolExecutor(max_workers=5) as executor:
        results = executor.map(extract_memorial_data, memorial_links)
        
        # Collect and save the results
        extracted_data = [data for data in results if data]
        save_data_to_csv(extracted_data)

    print(f"Data extraction completed for {len(extracted_data)} memorials.")

if __name__ == "__main__":
    main()
    driver.quit()
