import os
from airflow import DAG
from airflow.operators.bash import BashOperator
from datetime import datetime, timedelta
from dotenv import load_dotenv

load_dotenv()

citya = os.getenv("citya", "no-city")
cityb = os.getenv("cityb", "no-city")
cityc = os.getenv("cityc", "no-city")
sitename = os.getenv("sitename", "no-site")

default_args = {
    'owner': 'martynka',
    'start_date': datetime(2026, 4, 10),
    'retries': 2,
    'retry_delay': timedelta(minutes=5),
}



with DAG(
    'dariusz',
    default_args=default_args,
    schedule_interval='0 1 * * *',
    catchup=False, 
) as dag_dariusz:
   
    task_citya = BashOperator(
        task_id='citya',
        bash_command= f'python3 /opt/airflow/scripts/scraper.py "https://www.{sitename}.pl/nieruchomosci/dzialki/sprzedaz/{citya}/" 10'
    )
    task_cityb = BashOperator(
        task_id='getcityb',
        bash_command = f'python3 /opt/airflow/scripts/scraper.py "https://www.{sitename}.pl/nieruchomosci/dzialki/sprzedaz/{cityb}/" 10'
    )
    task_cityc = BashOperator(
        task_id='getcityc',
        bash_command= f'python3 /opt/airflow/scripts/scraper.py "https://www.{sitename}.pl/nieruchomosci/dzialki/sprzedaz/{cityc}/" 10'
    )
    task_citya >> task_cityb >> task_cityc



with DAG(
    'mariusz',
    default_args=default_args,
    schedule_interval='0 6 * * *',
    catchup=False, 
) as dag_mariusz:

    task_citya = BashOperator(
        task_id='citya',
        bash_command= f'python3 /opt/airflow/scripts/scraper.py "https://www.{sitename}.pl/nieruchomosci/dzialki/sprzedaz/{citya}/" 3'
    )
    task_cityb = BashOperator(
        task_id='getcityb',
        bash_command = f'python3 /opt/airflow/scripts/scraper.py "https://www.{sitename}.pl/nieruchomosci/dzialki/sprzedaz/{cityb}/" 3'
    )
    task_cityc = BashOperator(
        task_id='getcityc',
        bash_command= f'python3 /opt/airflow/scripts/scraper.py "https://www.{sitename}.pl/nieruchomosci/dzialki/sprzedaz/{cityc}/" 3'
    )
    task_citya >> task_cityb >> task_cityc