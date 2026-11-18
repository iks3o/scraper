# Real Estate Scraper Pipeline (Airflow + Docker + PostgreSQL)

Zautomatyzowany pipeline do cyklicznego pobierania ogłoszeń nieruchomości i zapisywania ich w relacyjnej bazie danych PostgreSQL. Całość działa w kontenerach Docker na domowym serwerze Ubuntu.

## Architektura systemu

Infrastruktura zarządzana jest przez `docker-compose.yaml` i składa się z czterech usług:

* **`airflow-webserver`** – panel webowy Airflow (port `8080`).
* **`airflow-scheduler`** – harmonogram uruchamiający DAG-i (`dariusz` o `01:00 UTC`, `mariusz` o `06:00 UTC`).
* **`postgres`** – wewnętrzna baza danych na potrzeby metadanych Airflowa (niewystawiona na zewnątrz).
* **`db`** – dedykowana baza PostgreSQL przechowująca zebrane ogłoszenia (port `5432`, trwały wolumen `pgdata`).

> **Uwaga dotycząca czasu:** Airflow domyślnie pracuje w strefie czasowej **UTC** (zimą -1h, latem -2h względem czasu polskiego).

## Struktura plików

* `mariuszdariusz.py` – definicja DAG-ów Airflow (`dariusz`, `mariusz`) mapowana do `/opt/airflow/dags/`.
* `scraper.py` – główny skrypt scrapujący mapowany do `/opt/airflow/scripts/`.
* `docker-compose.yaml` – konfiguracja kontenerów, wolumenów i sieci Docker.
* `.env` – plik konfiguracyjny z hasłami i parametrami (wykluczony z Gita przez `.gitignore`).

## Konfiguracja (`.env`)

Plik `.env` nie jest przechowywany w repozytorium. Przed pierwszym uruchomieniem utwórz go ręcznie w katalogu głównym projektu na serwerze według poniższego wzoru:

```env
DB_HOST=db
DB_PORT=5432
DB_NAME=data
DB_USER=postgres
DB_PASS=<TWOJE_HASLO_DO_BAZY>
citya=<MIASTO_1>
cityb=<MIASTO_2>
cityc=<MIASTO_3>
sitename=<NAZWA_SERWISU>
```

> **Ważne:** `DB_HOST=db` to nazwa kontenera w wewnętrznej sieci Dockera — używana przez skrypt wewnątrz Airflowa. Łącząc się z laptopa (np. przez DBeaver), podajesz adres IP serwera Ubuntu.

## Pierwsze uruchomienie na serwerze

```bash
git clone <LINK_DO_REPOZYTORIUM>
cd <NAZWA_FOLDERU_PROJEKTU>
nano .env   # uzupełnij zmienne według wzoru powyżej
docker-compose up -d
```

## Aktualizacja kodu (Workflow: Windows → GitHub → Ubuntu)

1. Wprowadź zmiany lokalnie w VS Code, zrób `commit` i `push` na GitHuba.
2. Połącz się z serwerem Ubuntu przez SSH i wejdź do folderu projektu.
3. Pobierz najnowszy kod:
   ```bash
   git pull
   ```
4. Przeładuj kontenery Airflowa (bez ruszania baz danych):
   ```bash
   docker-compose up -d --force-recreate --no-deps airflow-webserver airflow-scheduler
   ```

## Dostęp i podgląd danych

### Panel Airflow
* **Adres:** `http://<IP_SERWERA>:8080`
* Po zmianie kodu lub przeładowaniu kontenerów odczekaj ok. 30 sekund przed odświeżeniem strony.

### Podgląd bazy w DBeaver (z laptopa)
| Pole | Wartość |
| :--- | :--- |
| **Host** | `<IP_SERWERA>` |
| **Port** | `5432` |
| **Database** | `data` |
| **Username** | `postgres` |
| **Password** | `<DB_PASS z pliku .env>` |

### Szybki podgląd bazy z terminala serwera
Wejście do konsoli PostgreSQL wewnątrz kontenera `db`:
```bash
docker-compose exec db psql -U postgres -d data
```

Przydatne komendy wewnątrz `psql`:
* `\dt` – lista tabel w bazie.
* `SELECT COUNT(*) FROM <nazwa_tabeli>;` – liczba zapisanych rekordów.
* `SELECT * FROM <nazwa_tabeli> LIMIT 10;` – podgląd 10 pierwszych wierszy.
* `\q` – wyjście z konsoli bazy.

## Przydatne komendy ratunkowe (Docker)

* **Sprawdzenie działających kontenerów:**
  ```bash
  docker ps
  ```
* **Sprawdzenie logów konkretnego kontenera (np. bazy lub schedulera):**
  ```bash
  docker-compose logs -f db
  docker-compose logs -f airflow-scheduler
  ```
* **Restart wszystkich kontenerów:**
  ```bash
  docker-compose restart
  ```
* **Zatrzymanie całego stosu (z zachowaniem danych w bazie):**
  ```bash
  docker-compose down
  ```
  > **Uwaga:** Nigdy nie dopisuj flagi `-v` (`docker-compose down -v`), ponieważ usunie ona trwały wolumen `pgdata` wraz ze wszystkimi zebranymi ogłoszeniami.