import requests
from bs4 import BeautifulSoup
import csv
import time

def get_memorial_links(base_url, max_pages=10):
    memorial_links = []
    for page in range(1, max_pages + 1):
        url = f"{base_url}&page={page}"
        print(f"Scraping page {page}: {url}")
        response = requests.get(url)
        if response.status_code != 200:
            print("Failed to retrieve page.")
            break
        
        soup = BeautifulSoup(response.text, "html.parser")
        for link in soup.find_all("a", href=True):
            if "/memorial/" in link["href"]:
                full_url = "https://www.findagrave.com" + link["href"]
                if full_url not in memorial_links:
                    memorial_links.append(full_url)
        time.sleep(1)  # Be respectful to the server
    return memorial_links

def extract_lat_lon(memorial_url):
    response = requests.get(memorial_url)
    if response.status_code != 200:
        return None, None
    
    soup = BeautifulSoup(response.text, "html.parser")
    maps_links = soup.find_all("a", href=True)
    for link in maps_links:
        if "google.com/maps" in link["href"]:
            parts = link["href"].split("@")
            if len(parts) > 1:
                coords = parts[1].split(",")[:2]  # Extract latitude & longitude
                return coords[0], coords[1]
    return None, None

def main():
    base_url = "https://www.findagrave.com/memorial/search?location=Arkansas%2C+United+States+of+America&locationId=state_4&orderby=r"
    memorial_links = get_memorial_links(base_url, max_pages=5)  # Adjust max pages as needed
    
    with open("findagrave_data.csv", "w", newline="") as csvfile:
        fieldnames = ["memorial_url", "latitude", "longitude"]
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        writer.writeheader()
        
        for url in memorial_links:
            lat, lon = extract_lat_lon(url)
            writer.writerow({"memorial_url": url, "latitude": lat, "longitude": lon})
            print(f"Extracted: {url} -> {lat}, {lon}")
            time.sleep(1)

if __name__ == "__main__":
    main()
