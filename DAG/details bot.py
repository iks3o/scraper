from datetime import timedelta
import pendulum
from airflow import DAG
from airflow.operators.bash import BashOperator

warsaw_tz = pendulum.timezone("Europe/Warsaw")

with DAG(
    dag_id="ekstraktor_opisow",
    start_date=pendulum.datetime(2026, 11, 24, tz=warsaw_tz),
    schedule="0 3 * * *",
    catchup=False,
    max_active_runs=1,
    default_args={
        "owner": "airflow",
        "retries": 1,
        "retry_delay": timedelta(minutes=10),
    },
    tags=["olx", "otodom", "details"],
) as dag:

    fetch_details = BashOperator(
        task_id="fetch_offer_details",
               bash_command="python3 /opt/airflow/scripts/details_scraper.py --limit 50",
        execution_timeout=timedelta(minutes=45),
    )