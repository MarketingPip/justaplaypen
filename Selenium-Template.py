from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
import chromedriver_autoinstaller
from pyvirtualdisplay import Display
import requests
from bs4 import BeautifulSoup
import csv
import time
import random
from fake_useragent import UserAgent
import cloudscraper
from datetime import datetime
import json
import re

# Initialize virtual display for headless mode
display = Display(visible=0, size=(800, 800))  
display.start()

# Install and configure ChromeDriver
chromedriver_autoinstaller.install()
chrome_options = webdriver.ChromeOptions()
options = [
  # Define window size here
   "--window-size=1200,1200",
    "--ignore-certificate-errors"
 
    "--headless",
    #"--disable-gpu",
    #"--window-size=1920,1200",
    #"--ignore-certificate-errors",
    #"--disable-extensions",
    "--no-sandbox",
    "--disable-dev-shm-usage",
    '--remote-debugging-port=9222'
]
for option in options:
    chrome_options.add_argument(option)

driver = webdriver.Chrome(options=chrome_options)

# Initialize fake user agent and scraper
ua = UserAgent()
scraper = cloudscraper.create_scraper()

def write_safe_row(writer, data):
    """ Converts nested lists to JSON strings before writing to CSV """
    data["parents"] = json.dumps(data["parents"]) if data["parents"] else "[]"
    data["spouses"] = json.dumps(data["spouses"]) if data["spouses"] else "[]"
    data["children"] = json.dumps(data["children"]) if data["children"] else "[]"
    data["siblings"] = json.dumps(data["siblings"]) if data["siblings"] else "[]"
    writer.writerow(data)

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




def parse_date(date_string):
    try:
        # Case 1: Full date with age, e.g., "26 May 1928 (aged 81)"
        date_string = re.sub(r"\(aged.*\)", "", date_string).strip()  # Remove age part
        return datetime.strptime(date_string, "%d %b %Y").strftime("%Y-%m-%d")
    except ValueError:
        try:
            # Case 2: Only year, e.g., "1928"
            return datetime.strptime(date_string, "%Y").strftime("%Y-00-00")
        except ValueError:
            try:
                # Case 3: Approximate year, e.g., "Abt. 1928"
                if date_string.lower().startswith("abt."):
                    return datetime.strptime(date_string[4:].strip(), "%Y").strftime("%Y-00-00")
                return None  # Return None if the date format is not recognized
            except ValueError:
                return None  # Return None if the date format is not recognized

def extract_family_members(family_section):
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





def get_memorial_images(base_url, exclude_image_url=None):
   #  display.start()
    driver = webdriver.Chrome(options=chrome_options)

    try:
        # Open the provided URL
        driver.get(base_url)

        # Wait until images appear (use the CSS selector for the image elements)
        time.sleep(random.uniform(2, 4))  # Allow content to load
        WebDriverWait(driver, 30).until(
            EC.presence_of_all_elements_located((By.CSS_SELECTOR, "#TabPhotos > div.section-photos.section-board > div > div > div:nth-child(n) > div > button > img"))
        )

        # Extract image URLs from the specified selector
        image_urls = []
        images = driver.find_elements(By.CSS_SELECTOR, "#TabPhotos > div.section-photos.section-board > div > div > div:nth-child(n) > div > button > img")
        
        for img in images:
            src = img.get_attribute("src")
            if src and (exclude_image_url is None or src != exclude_image_url) and src not in image_urls:
                image_urls.append(src)

        return image_urls
    
    finally:
        # Ensure the WebDriver quits properly after execution
        driver.quit()
      #  display.stop()

def extract_memorial_data(memorial_url):
    headers = {"User-Agent": ua.random}

    response = scraper.get(memorial_url, headers=headers)
    if response.status_code != 200:
        print(f"Failed to retrieve {memorial_url}")
        return None

    soup = BeautifulSoup(response.text, "html.parser")

    # Extract birth date
    birth_date_raw = soup.select_one("#birthDateLabel")
    birth_date = parse_date(birth_date_raw.text.strip()) if birth_date_raw else None

    # Extract profile image URL
    profile_image_tag = soup.select_one("#profileImage")
    image_url = profile_image_tag.get("src") if profile_image_tag else None

    # Extract family members (parents and spouses)
    family_grid = soup.select_one("#family-grid")
    
    parents_section = None
    spouse_section = None
    children_section = None
    sibling_section = None
    half_sibling_section = None

    if family_grid:
        parents_section = family_grid.select_one("ul[aria-labelledby='parentsLabel']")
        spouse_section = family_grid.select_one("ul[aria-labelledby='spouseLabel']")
        children_section = family_grid.select_one("ul[aria-labelledby='childrenLabel']")
        sibling_section = family_grid.select_one("ul[aria-labelledby='siblingLabel']")
        half_sibling_section = family_grid.select_one("ul[aria-labelledby='halfSibLabel']")


    parents = extract_family_members(parents_section) if parents_section else []
    spouses = extract_family_members(spouse_section) if spouse_section else []
    children = extract_family_members(children_section) if children_section else []
    siblings = extract_family_members(sibling_section) if sibling_section else []
    half_siblings = extract_family_members(half_sibling_section) if half_sibling_section else []

    # Extract other data safely
    def safe_text(selector):
        element = soup.select_one(selector)
        return element.text.strip() if element else None


    photos_count = soup.select_one(".photosCount")
    photos = []
    if photos_count:
      count = int(photos_count.text.strip())
      if count > 1:     
        photos = get_memorial_images(memorial_url + "/photo", image_url)
        print(memorial_url + "/photo")
        print(photos)
        print("Fetching extra photos")


    data = {
        "memorial_url": memorial_url,
        "name": safe_text("#bio-name > b") or safe_text("#bio-name"),
        "prefix": safe_text("#bio-name > span"),
        "title": safe_text("#bio-name > b > span.visually-hidden"),
        "birth_date": birth_date,
        "death_date": safe_text("#deathDateLabel"),
        "cemetery": safe_text("#cemeteryNameLabel"),
        "location": safe_text("#cemeteryCityName"),
        "plot_value": safe_text("#plotValueLabel"),
        "bio": None,
        "gps": None,
        "image_url": image_url,
        "parents": parents,
        "spouses": spouses,
        "children" : children,
        "siblings" : siblings,
        "half_siblings": half_siblings,
        "photos": photos
    }

    if data["death_date"]:
        data["death_date"] = parse_date(data["death_date"])
    # Extract bio safely
    bio_section = soup.select_one("#inscriptionValue") or soup.select_one("#fullBio")
    if bio_section:
        data["bio"] = bio_section.decode_contents().replace('<br>', '\n').strip()

    # Extract GPS coordinates
    gps_span = soup.select_one("#gpsLocation")
    if gps_span:
        link = gps_span.find("a")
        if link and "google.com/maps" in link["href"]:
            try:
                coords = link["href"].split("q=")[1].split("&")[0].split(",")
                if len(coords) == 2:
                    data["gps"] = {"latitude": coords[0], "longitude": coords[1]}
            except IndexError:
                pass  # Handle case where URL format is unexpected

    return data

def main():
    base_url = "https://www.findagrave.com/memorial/search?location=Crediton%2C+Huron+County%2C+Ontario%2C+Canada&locationId=city_252602"
    memorial_links = get_memorial_links(base_url, max_pages=5)
    driver.quit() # Close driver to free memory + we do not need it anymore.
   # display.stop()
    
    with open("findagrave_data.csv", "w", newline="") as csvfile:
        fieldnames = ["memorial_url", "name", "birth_date", "death_date", "cemetery", "location", "bio", "gps", "image_url", "parents", "spouses", "children", "siblings", "half_siblings", "plot_value", "title", "prefix", "photos"]
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames, quoting=csv.QUOTE_ALL)
        writer.writeheader()
        
        for url in memorial_links:
            data = extract_memorial_data(url)
            if data:
                write_safe_row(writer, data)
                print(f"Extracted: {data}")
                time.sleep(random.uniform(1, 3))

if __name__ == "__main__":
    main()
