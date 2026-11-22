#kroki z power query z mojego pierwszego podejscia do tego projektu w excelu przekopiowane 
#i przetlumaczone przez AI :D

CREATE OR REPLACE VIEW real_estate_clean AS
WITH parsed AS (
    SELECT
        id,
        city,
        title,
        price,
        location_date,
        size_and_ppm,
        link,
        scraped_at,
        REGEXP_MATCH(
            LOWER(location_date),
            '([0-9]{1,2})\s+(stycznia|lutego|marca|kwietnia|maja|czerwca|lipca|sierpnia|września|października|listopada|grudnia)\s+([0-9]{4})'
        ) AS d_match
    FROM real_estate
)
SELECT
    id,
    city AS miasto_wyszukiwania,
    title AS tytul,
    REPLACE(
        SUBSTRING(
            REPLACE(REPLACE(price, ' ', ''), chr(160), '')
            FROM '[0-9]+(?:[,.][0-9]+)?'
        ),
        ',', '.'
    )::NUMERIC AS cena_pln,
    TRIM(SPLIT_PART(SPLIT_PART(location_date, ' - ', 1), ',', 1)) AS miejscowosc,
    CASE
        WHEN LOWER(location_date) LIKE '%dzisiaj%' THEN scraped_at::DATE
        WHEN LOWER(location_date) LIKE '%wczoraj%' THEN (scraped_at - INTERVAL '1 day')::DATE
        WHEN d_match IS NOT NULL THEN MAKE_DATE(
            d_match[3]::INT,
            CASE d_match[2]
                WHEN 'stycznia' THEN 1
                WHEN 'lutego' THEN 2
                WHEN 'marca' THEN 3
                WHEN 'kwietnia' THEN 4
                WHEN 'maja' THEN 5
                WHEN 'czerwca' THEN 6
                WHEN 'lipca' THEN 7
                WHEN 'sierpnia' THEN 8
                WHEN 'września' THEN 9
                WHEN 'października' THEN 10
                WHEN 'listopada' THEN 11
                WHEN 'grudnia' THEN 12
            END,
            d_match[1]::INT
        )
        ELSE NULL
    END AS data_ogloszenia,
    REPLACE(
        SUBSTRING(
            REPLACE(REPLACE(SPLIT_PART(size_and_ppm, 'm', 1), ' ', ''), chr(160), '')
            FROM '[0-9]+(?:[,.][0-9]+)?'
        ),
        ',', '.'
    )::NUMERIC AS wielkosc_dzialki_m2,
    REPLACE(
        SUBSTRING(
            REPLACE(REPLACE(SUBSTRING(size_and_ppm FROM 'm[²2](.*)'), ' ', ''), chr(160), '')
            FROM '[0-9]+(?:[,.][0-9]+)?'
        ),
        ',', '.'
    )::NUMERIC AS cena_za_m2,
    CASE
        WHEN link LIKE '/%' THEN 'https://www.olx.pl' || link
        ELSE link
    END AS link,
    scraped_at::DATE AS data_pobrania,
    scraped_at
FROM parsed;