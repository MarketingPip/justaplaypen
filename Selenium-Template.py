from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
import chromedriver_autoinstaller
#from pyvirtualdisplay import Display  # Optional: modern headless Chrome may not require this
import time
import random
import csv
from datetime import datetime
from bs4 import BeautifulSoup
import cloudscraper
from fake_useragent import UserAgent
import concurrent.futures

# Optionally start virtual display if required (e.g. in Linux without X server)
# display = Display(visible=0, size=(800, 800))
# display.start()

# Install and configure ChromeDriver
chromedriver_autoinstaller.install()
chrome_options = Options()
chrome_args = [
    "--window-size=1200,1200",
    "--ignore-certificate-errors",
    "--headless",
    "--no-sandbox",
    "--disable-dev-shm-usage",
    "--remote-debugging-port=9222"
]
for arg in chrome_args:
    chrome_options.add_argument(arg)

driver = webdriver.Chrome(options=chrome_options)

# Global instances to avoid recreating per request
global_ua = UserAgent()
global_scraper = cloudscraper.create_scraper()

def get_memorial_links(base_url, max_pages=10):
    driver.get(base_url)
    last_height = driver.execute_script("return document.body.scrollHeight")
    page = 0
    
    # Scroll until no new content or until reaching max_pages iterations
    while page < max_pages:
        driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        time.sleep(random.uniform(1, 2))  # Reduced delay for faster scrolling
        new_height = driver.execute_script("return document.body.scrollHeight")
        if new_height == last_height:
            break
        last_height = new_height
        page += 1

    memorial_links = set()  # Use set to avoid duplicates
    elements = driver.find_elements("css selector", "a[href*='/memorial/']")
    for elem in elements:
        link = elem.get_attribute("href")
        if link:
            memorial_links.add(link)
    
    return list(memorial_links)

def parse_date(date_string):
    try:
        # Try to parse dates like "4 Jun 1871" or "4 Jun, 1871"
        return datetime.strptime(date_string, "%d %b %Y").strftime("%Y-%m-%d")
    except ValueError:
        return None  # Return None if the date format is not recognized

def extract_family_members(family_section):
    family_members = []
    if family_section:
        family_items = family_section.find_all("li", itemscope=True)
        for item in family_items:
            name_tag = item.select_one("h3[itemprop='name']")
            name = name_tag.text.strip() if name_tag else None
            birth_tag = item.select_one("span[itemprop='birthDate']")
            birth_date = birth_tag.text.strip() if birth_tag else None
            death_tag = item.select_one("span[itemprop='deathDate']")
            death_date = death_tag.text.strip() if death_tag else None
            url_tag = item.find("a", itemprop="url")
            profile_url = url_tag["href"] if url_tag else None
            family_members.append({
                "name": name,
                "birth_date": parse_date(birth_date) if birth_date else None,
                "death_date": parse_date(death_date) if death_date else None,
                "profile_url": profile_url
            })
    return family_members

def extract_memorial_data(memorial_url):
    headers = {"User-Agent": global_ua.random}
    try:
        response = global_scraper.get(memorial_url, headers=headers, timeout=10)
    except Exception as e:
        print(f"Error fetching {memorial_url}: {e}")
        return None

    if response.status_code != 200:
        print(f"Failed to retrieve {memorial_url}: {response.status_code}")
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
    parents_section = spouse_section = None
    if family_grid:
        parents_section = family_grid.select_one("ul[aria-labelledby='parentsLabel']")
        spouse_section = family_grid.select_one("ul[aria-labelledby='spouseLabel']")
    parents = extract_family_members(parents_section) if parents_section else []
    spouses = extract_family_members(spouse_section) if spouse_section else []

    def safe_text(selector):
        element = soup.select_one(selector)
        return element.text.strip() if element else None

    data = {
        "memorial_url": memorial_url,
        "name": safe_text("#bio-name"),
        "birth_date": birth_date,
        "death_date": safe_text("#deathDateLabel"),
        "cemetery": safe_text("#cemeteryNameLabel"),
        "location": safe_text("#cemeteryCityName"),
        "bio": None,
        "gps": None,
        "image_url": image_url,
        "parents": parents,
        "spouses": spouses
    }

    # Extract bio
    bio_section = soup.select_one("#inscriptionValue")
    if bio_section:
        data["bio"] = bio_section.decode_contents().replace('<br>', '\n').strip()

    # Extract GPS coordinates if available
    gps_span = soup.select_one("#gpsLocation")
    if gps_span:
        link = gps_span.find("a")
        if link and "google.com/maps" in link.get("href", ""):
            try:
                coords = link["href"].split("q=")[1].split("&")[0].split(",")
                if len(coords) == 2:
                    data["gps"] = {"latitude": coords[0], "longitude": coords[1]}
            except IndexError:
                pass  # Unexpected URL format

    return data

def main():
    base_url = ("https://www.findagrave.com/memorial/search?"
                "location=Crediton%2C+Huron+County%2C+Ontario%2C+Canada&"
                "locationId=city_252602")
    memorial_links = get_memorial_links(base_url, max_pages=5)
    driver.quit()  # Free up resources as Selenium is no longer needed

    # Open CSV file for writing
    with open("findagrave_data.csv", "w", newline="", encoding="utf-8") as csvfile:
        fieldnames = ["memorial_url", "name", "birth_date", "death_date",
                      "cemetery", "location", "bio", "gps", "image_url", "parents", "spouses"]
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        writer.writeheader()

        # Use ThreadPoolExecutor to fetch memorial data concurrently
        with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
            future_to_url = {executor.submit(extract_memorial_data, url): url for url in memorial_links}
            for future in concurrent.futures.as_completed(future_to_url):
                url = future_to_url[future]
                data = future.result()
                if data:
                    writer.writerow(data)
                    print(f"Extracted: {data['name']} from {url}")
                else:
                    print(f"Skipping {url} due to extraction error.")
                # A short sleep can still be used to mitigate server overload
                time.sleep(random.uniform(0.5, 1.5))

if __name__ == "__main__":
    main()
