import argparse
import json
import os
import random
import re
import time
from typing import Optional, Tuple

import psycopg2
import requests
from bs4 import BeautifulSoup
from dotenv import load_dotenv

load_dotenv()

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/130.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "pl-PL,pl;q=0.9,en;q=0.5",
}


def clean_whitespace(text: str) -> str:
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def parse_olx(soup: BeautifulSoup) -> str:
    parts = []

    h1 = soup.find("h1")
    if h1:
        title = h1.get_text(" ", strip=True)
        if title:
            parts.append(f"TYTUŁ:\n{title}")

    # Parametry / tagi (Prywatne, Rodzaj, Powierzchnia, Media itd.)
    params_box = soup.find(attrs={"data-testid": "ad-parameters-container"})
    if params_box:
        params = [p.get_text(" ", strip=True) for p in params_box.find_all(["p", "li"])]
        params = [p for p in params if p]
        if params:
            parts.append("PARAMETRY:\n" + "\n".join(dict.fromkeys(params)))

    # Główny opis ogłoszenia (nowy układ Tailwind + starsze atrybuty jako zapas)
    desc_box = (
        soup.select_one("div.whitespace-pre-line.text-background-action-primary")
        or soup.find(attrs={"data-cy": "ad_description"})
        or soup.find(attrs={"data-testid": "ad-description"})
    )
    if desc_box:
        parts.append("OPIS:\n" + desc_box.get_text("\n", strip=True))

    if parts:
        return clean_whitespace("\n\n".join(parts))

    return fallback_text(soup)


def _clean_otodom_val(val: str) -> str:
    text = str(val).strip()
    # Usuwamy techniczny prefiks, np. "media_types::electricity" -> "electricity"
    if "::" in text:
        text = text.split("::", 1)[1]
    # Zamieniamy flagi jednoliterowe (np. fence: n -> nie), żeby AI nie zgadywało
    if text == "y":
        return "tak"
    if text == "n":
        return "nie"
    return text
#

def parse_otodom(soup: BeautifulSoup) -> str:
    next_data_tag = soup.find("script", id="__NEXT_DATA__")
    if next_data_tag and next_data_tag.string:
        try:
            payload = json.loads(next_data_tag.string)
            ad = payload.get("props", {}).get("pageProps", {}).get("ad", {})
            parts = []

            title = ad.get("title")
            if title:
                parts.append(f"TYTUŁ:\n{title}")

            # Parametry z topInformation i additionalInformation (media, dojazd, ogrodzenie, typ)
            param_lines = []
            for section in ("topInformation", "additionalInformation"):
                for item in ad.get(section, []):
                    label = item.get("label")
                    vals = item.get("values") or []
                    unit = item.get("unit") or ""
                    if label and vals:
                        cleaned = ", ".join(_clean_otodom_val(v) for v in vals)
                        line = f"{label}: {cleaned} {unit}".strip()
                        param_lines.append(line)

            if param_lines:
                parts.append("PARAMETRY:\n" + "\n".join(dict.fromkeys(param_lines)))

            desc_html = ad.get("description")
            if desc_html:
                desc_text = BeautifulSoup(desc_html, "html.parser").get_text("\n", strip=True)
                parts.append("OPIS:\n" + desc_text)

            if parts:
                return clean_whitespace("\n\n".join(parts))
        except Exception as exc:
            print(f"Nie udało się odczytać __NEXT_DATA__ na Otodom ({exc}), używam planu B.")

    desc_box = soup.find(attrs={"data-cy": "adPageAdDescription"})
    if desc_box:
        return clean_whitespace("OPIS:\n" + desc_box.get_text("\n", strip=True))

    return fallback_text(soup)


def fallback_text(soup: BeautifulSoup) -> str:
    for tag in soup(["script", "style", "noscript", "header", "footer", "nav"]):
        tag.decompose()
    container = soup.find("main") or soup.body or soup
    return clean_whitespace(container.get_text("\n", strip=True))


def fetch_offer_details(session: requests.Session, url: str) -> Tuple[Optional[str], str]:
    try:
        resp = session.get(url, headers=HEADERS, timeout=25, allow_redirects=True)
    except requests.RequestException as exc:
        print(f"Błąd sieci dla {url}: {exc}")
        return None, "network_error"

    if resp.status_code in (404, 410):
        return None, "404"
    if resp.status_code in (403, 429):
        return None, f"blocked_{resp.status_code}"
    if resp.status_code != 200:
        return None, f"http_{resp.status_code}"

    soup = BeautifulSoup(resp.text, "html.parser")
    final_url = resp.url.lower()

    if "otodom.pl" in final_url:
        text = parse_otodom(soup)
    else:
        text = parse_olx(soup)

    if not text or len(text) < 40:
        return None, "empty"

    return text[:6000], "ok"


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--limit", type=int, default=50, help="Ile ofert pobrać w jednej paczce")
    args = parser.parse_args()

    conn = psycopg2.connect(
        host=os.getenv("DB_HOST"),
        port=os.getenv("DB_PORT"),
        dbname=os.getenv("DB_NAME"),
        user=os.getenv("DB_USER"),
        password=os.getenv("DB_PASS"),
    )
    cur = conn.cursor()

    # Bezpieczne dodanie kolumn, jeśli jeszcze nie istnieją
    cur.execute("""
        ALTER TABLE real_estate ADD COLUMN IF NOT EXISTS raw_details TEXT;
        ALTER TABLE real_estate ADD COLUMN IF NOT EXISTS details_status TEXT;
        ALTER TABLE real_estate ADD COLUMN IF NOT EXISTS details_scraped_at TIMESTAMP;
    """)
    conn.commit()

    # Pobieramy paczkę czystych linków z widoku, które nie były jeszcze odwiedzone
    cur.execute("""
        SELECT c.id, c.link
        FROM real_estate_clean c
        JOIN real_estate r ON c.id = r.id
        WHERE r.details_status IS NULL
          AND c.link IS NOT NULL
        ORDER BY r.scraped_at DESC
        LIMIT %s;
    """, (args.limit,))
    rows = cur.fetchall()

    print(f"Znaleziono {len(rows)} ofert do pobrania szczegółów (limit={args.limit}).")
    if not rows:
        cur.close()
        conn.close()
        return

    session = requests.Session()
    consecutive_blocks = 0
    stats = {}

    for idx, (offer_id, link) in enumerate(rows, start=1):
        print(f"[{idx}/{len(rows)}] ID={offer_id} -> {link}")
        details_text, status = fetch_offer_details(session, link)
        stats[status] = stats.get(status, 0) + 1

        # Zapis natychmiast po każdym ogłoszeniu
        cur.execute("""
            UPDATE real_estate
            SET raw_details = %s,
                details_status = %s,
                details_scraped_at = NOW()
            WHERE id = %s;
        """, (details_text, status, offer_id))
        conn.commit()

        # W razie bloka przerywamy
        if status.startswith("blocked_"):
            consecutive_blocks += 1
            if consecutive_blocks >= 5:
                print("Wykryto 5 blokad z rzędu (403/429) — przerywam paczkę na dziś.")
                break
        else:
            consecutive_blocks = 0

        
        if idx < len(rows):
            time.sleep(random.uniform(8.0, 15.0))

    print(f"Zakończono paczkę. Statystyki statusów: {stats}")
    cur.close()
    conn.close()


if __name__ == "__main__":
    main()