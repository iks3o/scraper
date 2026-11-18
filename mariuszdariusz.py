from airflow import DAG
from airflow.operators.bash import BashOperator
from datetime import datetime, timedelta

default_args = {
    'owner': 'martynka',
    'start_date': datetime(2026, 4, 10),
    'retries': 2,
    'retry_delay': timedelta(minutes=5),
}

with DAG(
    'olx_dariusz',
    default_args=default_args,
    schedule_interval='0 1 * * *',
    catchup=False, 
) as dag_dariusz:
    
    task_citya = BashOperator(
        task_id='citya',
        bash_command= 'python3 /opt/airflow/scripts/scraper_olx.py "https://www.olx.pl/nieruchomosci/dzialki/citya/" 10'
    )
    task_cityb = BashOperator(
        task_id='getcityb',
        bash_command = 'python3 /opt/airflow/scripts/scraper_olx.py "https://www.olx.pl/nieruchomosci/dzialki/cityb/" 10'
    )
    task_cityc = BashOperator(
        task_id='getcityc',
        bash_command= 'python3 /opt/airflow/scripts/scraper_olx.py "https://www.olx.pl/nieruchomosci/dzialki/cityc/" 10'
    )
    task_citya >> task_cityb >> task_cityc

with DAG(
    'olx_mariusz',
    default_args=default_args,
    schedule_interval='0 6 * * *',
    catchup=False, 
) as dag_mariusz:

    task_citya = BashOperator(
        task_id='citya',
        bash_command= 'python3 /opt/airflow/scripts/scraper_olx.py "https://www.olx.pl/nieruchomosci/dzialki/citya/" 3'
    )
    task_cityb = BashOperator(
        task_id='getcityb',
        bash_command = 'python3 /opt/airflow/scripts/scraper_olx.py "https://www.olx.pl/nieruchomosci/dzialki/cityb/" 3'
    )
    task_cityc = BashOperator(
        task_id='getcityc',
        bash_command= 'python3 /opt/airflow/scripts/scraper_olx.py "https://www.olx.pl/nieruchomosci/dzialki/cityc/" 3'
    )
    task_citya >> task_cityb >> task_cityc