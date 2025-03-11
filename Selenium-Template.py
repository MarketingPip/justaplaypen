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

# Initialize virtual display for headless mode
display = Display(visible=0, size=(800, 800))  
display.start()

# Install and configure ChromeDriver
chromedriver_autoinstaller.install()
chrome_options = webdriver.ChromeOptions()
options = [
    "--window-size=1200,1200",
    "--ignore-certificate-errors"
]
for option in options:
    chrome_options.add_argument(option)

driver = webdriver.Chrome(options=chrome_options)

# Initialize fake user agent and scraper
ua = UserAgent()
scraper = cloudscraper.create_scraper()

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
    headers = {"User-Agent": ua.random}
    response = scraper.get(memorial_url, headers=headers)
    if response.status_code != 200:
        print(f"Failed to retrieve {memorial_url}")
        return None
    
    soup = BeautifulSoup(response.text, "html.parser")
    data = {
        "memorial_url": memorial_url,
        "name": soup.select_one(".memorial-name").text.strip() if soup.select_one(".memorial-name") else None,
        "birth_date": soup.select_one(".birth-date").text.strip() if soup.select_one(".birth-date") else None,
        "death_date": soup.select_one(".death-date").text.strip() if soup.select_one(".death-date") else None,
        "cemetery": soup.select_one(".cemetery-name").text.strip() if soup.select_one(".cemetery-name") else None,
        "location": soup.select_one(".cemetery-location").text.strip() if soup.select_one(".cemetery-location") else None,
        "bio": soup.select_one(".bio-text").text.strip() if soup.select_one(".bio-text") else None,
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

def main():
    base_url = "https://www.findagrave.com/memorial/search?location=Crediton%2C+Huron+County%2C+Ontario%2C+Canada&locationId=city_252602"
    memorial_links = get_memorial_links(base_url, max_pages=5)
    
    with open("findagrave_data.csv", "w", newline="") as csvfile:
        fieldnames = ["memorial_url", "name", "birth_date", "death_date", "cemetery", "location", "bio", "gps"]
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
    driver.quit()
