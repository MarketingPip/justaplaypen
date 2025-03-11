import time
import json
import requests
from urllib.parse import quote_plus
from bs4 import BeautifulSoup

# Import Selenium components
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
import chromedriver_autoinstaller
from pyvirtualdisplay import Display

display = Display(visible=0, size=(800, 800))  
display.start()

chromedriver_autoinstaller.install()

chrome_options = webdriver.ChromeOptions()
options = [
    "--window-size=1200,1200",
    "--ignore-certificate-errors"
##    "--headless"  # Run headless to avoid UI rendering issues
]

for option in options:
    chrome_options.add_argument(option)
    
driver = webdriver.Chrome(options=chrome_options)

def scroll_to_bottom(driver, pause_time=2):
    last_height = driver.execute_script("return document.body.scrollHeight")
    while True:
        driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        time.sleep(pause_time)
        new_height = driver.execute_script("return document.body.scrollHeight")
        if new_height == last_height:
            break
        last_height = new_height

def get_memorial_links(search_url):
    driver.get(search_url)
    scroll_to_bottom(driver)
    link_elements = driver.find_elements(By.CSS_SELECTOR, "a.d-flex.align-items-center")
    links = [element.get_attribute("href") for element in link_elements if element.get_attribute("href")]
    return links

def scrape_memorial_page(url):
    response = requests.get(url)
    if response.status_code != 200:
        return None
    soup = BeautifulSoup(response.content, "html.parser")
    
    name_tag = soup.find("h1", id="bio-name")
    name = name_tag.get_text(strip=True) if name_tag else None
    
    photo_tag = soup.find("img", id="profileImage")
    photo_url = photo_tag["src"] if photo_tag else None
    
    birth_tag = soup.find("time", id="birthDateLabel")
    birth_date = birth_tag.get_text(strip=True) if birth_tag else None
    
    death_tag = soup.find("span", id="deathDateLabel")
    death_date = death_tag.get_text(strip=True) if death_tag else None
    
    cemetery_tag = soup.find("span", id="cemeteryNameLabel")
    cemetery_name = cemetery_tag.get_text(strip=True) if cemetery_tag else None
    
    gps_tag = soup.find("a", id="gpsValue")
    gps_link = gps_tag["href"] if gps_tag else None
    
    data = {
        "url": url,
        "name": name,
        "photo_url": photo_url,
        "birth_date": birth_date,
        "death_date": death_date,
        "cemetery_name": cemetery_name,
        "gps_link": gps_link
    }
    return data

def main(cemetery_str):
    location = quote_plus(cemetery_str)
    search_url = f"https://www.findagrave.com/memorial/search?location={location}&orderby=r"
    print(f"Fetching memorial links from: {search_url}")
    
    memorial_links = get_memorial_links(search_url)
    print(f"Found {len(memorial_links)} memorial links.")
    
    all_memorials = []
    for link in memorial_links:
        try:
            print(f"Scraping {link}...")
            memorial_data = scrape_memorial_page(link)
            if memorial_data:
                all_memorials.append(memorial_data)
        except Exception as e:
            print(f"Error scraping {link}: {e}")
    
    with open("FindAGrave_Results.json", "w") as f:
        json.dump(all_memorials, f, indent=2)
    
    print("Scraping completed. Data saved to FindAGrave_Results.json")
    driver.quit()

if __name__ == "__main__":
    cemetery_input = "Crediton, Huron County, Ontario, Canada"
    main(cemetery_input)
