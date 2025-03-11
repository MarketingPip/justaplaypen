import requests
from bs4 import BeautifulSoup
import csv
import time
import random
from fake_useragent import UserAgent
import cloudscraper  # To handle Cloudflare protection

# Initialize fake user agent for randomizing User-Agent header
ua = UserAgent()

# Cloudflare scraper that bypasses JS challenges
scraper = cloudscraper.create_scraper()

def get_memorial_links(base_url, max_pages=10):
    memorial_links = []
    for page in range(1, max_pages + 1):
        url = f"{base_url}&page={page}"
        print(f"Scraping page {page}: {url}")

        # Randomize headers to mimic different browser requests
        headers = {
            "User-Agent": ua.random,
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.5",
            "Connection": "keep-alive",
        }
        
        response = scraper.get(url, headers=headers)
        if response.status_code != 200:
            print("Failed to retrieve page.")
            break
        
        soup = BeautifulSoup(response.text, "html.parser")
        for link in soup.find_all("a", href=True):
            if "/memorial/" in link["href"]:
                full_url = "https://www.findagrave.com" + link["href"]
                if full_url not in memorial_links:
                    memorial_links.append(full_url)
        
        # Implement random sleep to mimic human behavior and avoid detection
        time.sleep(random.uniform(1, 3))  # Sleep between 1 to 3 seconds
    return memorial_links

def extract_lat_lon(memorial_url):
    # Randomize headers to avoid blocking
    headers = {
        "User-Agent": ua.random,
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.5",
        "Connection": "keep-alive",
    }

    response = scraper.get(memorial_url, headers=headers)
    
    # Check if we successfully retrieved the page
    if response.status_code != 200:
        print("Failed to retrieve the page.")
        return None, None
    
    soup = BeautifulSoup(response.text, "html.parser")
    
    # Look for the #gpsLocation element in the HTML
    gps_span = soup.select_one('#gpsLocation')
    if gps_span:
        print("Found #gpsLocation element:")
    else:
        print("No #gpsLocation element found.")
        return None, None

    # Look for the <a> tag within the gpsLocation span
    link = gps_span.find('a')
    if link:
        print("Found link in #gpsLocation:")
        href = link.get('href', '')
        if "google.com/maps" in href:
            print(f"Google Maps URL: {href}")
            parts = href.split("q=")
            if len(parts) > 1:
                coords = parts[1].split("&")[0].split(",")  # Extract latitude & longitude
                if len(coords) == 2:
                    print(f"Latitude: {coords[0]}, Longitude: {coords[1]}")
                    return coords[0], coords[1]
        else:
            print(f"URL does not contain 'google.com/maps': {href}")
    else:
        print("No <a> tag found within #gpsLocation.")
    
    return None, None

def main():
    base_url = "https://www.findagrave.com/memorial/search?firstname=&middlename=&lastname=&birthyear=&birthyearfilter=&deathyear=&deathyearfilter=&location=Crediton%2C+Huron+County%2C+Ontario%2C+Canada&locationId=city_252602&bio=&linkedToName=&plot=&memorialid=&mcid=&datefilter=&orderby=r"
    memorial_links = get_memorial_links(base_url, max_pages=5)  # Adjust max pages as needed
    
    with open("findagrave_data.csv", "w", newline="") as csvfile:
        fieldnames = ["memorial_url", "latitude", "longitude"]
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        writer.writeheader()
        
        for url in memorial_links:
            lat, lon = extract_lat_lon(url)
            writer.writerow({"memorial_url": url, "latitude": lat, "longitude": lon})
            print(f"Extracted: {url} -> {lat}, {lon}")
            time.sleep(random.uniform(1, 3))  # Sleep between 1 to 3 seconds to avoid detection

if __name__ == "__main__":
    main()
