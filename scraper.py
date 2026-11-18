import sys
import time
import random
import requests
import os
import psycopg2
from bs4 import BeautifulSoup
from pprint import pprint
from dotenv import load_dotenv

load_dotenv()

if len(sys.argv) < 2:
    print("Podaj link i liczbę stron!!!")
    sys.exit()


baza_url = sys.argv[1] 
pagenumber = int(sys.argv[2])

#tak jestem czlowiekiem! :)
headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/157.0.0.0 Safari/537.36'
}

def scraping(url):
    answer = requests.get(url, headers=headers)
    return BeautifulSoup(answer.content, 'lxml')

def getplot(zupka):
    return zupka.find_all('div', attrs={"data-cy": "l-card"})

def scrapingplot(div):
    title = div.find(attrs={"data-testid": "ad-card-title"}).text
    link = div.find(attrs={"data-testid": "card-title-link"})['href']
    price = div.find(attrs={"data-testid": "ad-price"}).text
    locationdate = div.find(attrs={"data-testid": "location-date"}).text
    
    #w razie jakby to nie bylo podane?
    try:
        location = div.find(attrs={"data-testid": "location-date"})
        box = location.find_next_sibling('div')
        sizeandppm = box.text.strip()
    except AttributeError:
        sizeandppm = "Brak danych"

    plot = {
        "title": title,
        "link": link,
        "price": price,
        "locationdate": locationdate,
        "sizeandppm": sizeandppm
    }
    return plot

###############
#    MAIN     # 
###############

allplots = []
  

for page in range(1, pagenumber + 1):
    print(f"Pobieram stronę numer: {page} z {pagenumber} dla adresu: {baza_url}")

    
    url = f"{baza_url}?page={page}&search%5Bdist%5D=30&search%5Bfilter_enum_type%5D%5B0%5D=dzialki-budowlane"

    zupka = scraping(url)
    divelements = getplot(zupka)

    for div in divelements:
        try:
            oneplot = scrapingplot(div)
            allplots.append(oneplot)
        except AttributeError:
            pass

  
    woo = random.uniform(10.0, 15.0)
    time.sleep(woo)

try:
    conn = psycopg2.connect(
        host=os.getenv("DB_HOST"),
        port=os.getenv("DB_PORT"),
        dbname=os.getenv("DB_NAME"),
        user=os.getenv("DB_USER"),
        password=os.getenv("DB_PASS")
    )
    cur = conn.cursor()


    cur.execute("""
        CREATE TABLE IF NOT EXISTS real_estate (
            id SERIAL PRIMARY KEY,
            link TEXT UNIQUE,
            title TEXT,
            price TEXT,
            location_date TEXT,
            size_and_ppm TEXT,
            scraped_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
    """)
    insert_query = """
        INSERT INTO real_estate (link, title, price, location_date, size_and_ppm)
        VALUES (%s, %s, %s, %s, %s)
        ON CONFLICT (link) DO NOTHING;
    """

    for item in allplots:
        cur.execute(insert_query, (
            item.get('link'),
            item.get('title'),
            item.get('price'),
            item.get('locationdate'),
            item.get('sizeandppm')
        ))

    conn.commit()
    cur.close()
    conn.close()
    print(f"Przesłano {len(allplots)} ogłoszeń do bazy")

except Exception as e:
    print(f"Błąd :( przy zapisie do bazy: {e}")