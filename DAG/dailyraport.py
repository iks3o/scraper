import os
import smtplib
from email.message import EmailMessage
from datetime import datetime, timedelta
import psycopg2
from airflow import DAG
from airflow.operators.python import PythonOperator
from airflow.models import DagRun


def dbcheck():
    # conn - connect
    conn = psycopg2.connect(
        host=os.getenv("DB_HOST", "olx-db"),
        database=os.getenv("DB_NAME"),
        user=os.getenv("DB_USER"),
        password=os.getenv("DB_PASS"),
        port=os.getenv("DB_PORT", "5432"),
    )
    try:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT
                    COUNT(*),
                    COUNT(*) FILTER (WHERE scraped_at >= NOW() - INTERVAL '24 hours'),
                    MAX(scraped_at)
                FROM real_estate;
            """)
            everything, new_24h, last_entry = cur.fetchone()
    finally:
        conn.close()
    return everything, new_24h, last_entry


dags_to_check = ["dariusz", "mariusz"]


def dagcheck():
    lines = []
    if_error = False

    for dag_id in dags_to_check:
        runs = DagRun.find(dag_id=dag_id)

        if not runs:
            lines.append(f"- {dag_id}: Brak uruchomień.")
            if_error = True
            continue

        last = max(runs, key=lambda r: r.logical_date)
        status = str(last.state).upper()

        if status != "SUCCESS":
            if_error = True

        # czas trwania zadania
        if last.start_date and last.end_date:
            time = int((last.end_date - last.start_date).total_seconds())
            time_txt = f"{time}s"
        else:
            time_txt = "w trakcie / brak danych"

        start_txt = last.start_date.strftime("%Y-%m-%d %H:%M UTC") if last.start_date else "brak"
        lines.append(f"- {dag_id}: {status} (start: {start_txt}, czas: {time_txt})")

    return "\n".join(lines), if_error


###################
# WYSYLANIE RAPORTU
###################


def send_raport():
    dag_raport, if_error = dagcheck()

    try:
        everything, new_24h, last_entry = dbcheck()
        last_txt = last_entry.strftime("%Y-%m-%d %H:%M") if last_entry else "brak"
        if new_24h == 0:
            if_error = True
        db_raport = (
            f"- Wszystkich ogłoszeń: {everything}\n"
            f"- Nowych w ostatnich 24h: {new_24h}\n"
            f"- Ostatni zapis: {last_txt}"
        )
    except Exception as e:
        if_error = True
        db_raport = f"- Błąd połączenia z bazą: {e}"

    sender = os.getenv("EMAIL_SENDER")
    receiver = os.getenv("EMAIL_RECEIVER")
    password = os.getenv("EMAIL_APP_PASS")

    topic_status = "[Warning]" if if_error else "[OK]"
    today = datetime.now().strftime("%Y-%m-%d")

    msg = EmailMessage()
    msg["Subject"] = f"{topic_status} Raport serwera - {today}"
    msg["From"] = sender
    msg["To"] = receiver
    msg.set_content(
        f"Witaj królowo, uniżony sługa przedstawia poranny raport z Twojego serwera:\n\n"
        f"Status botów:\n{dag_raport}\n\n"
        f"Baza danych:\n{db_raport}\n"
    )

    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as smtp:
        smtp.login(sender, password)
        smtp.send_message(msg)


default_args = {
    "owner": "airflow",
    "retries": 1,
    "retry_delay": timedelta(minutes=5),
}

with DAG(
    dag_id="daily_raport",
    default_args=default_args,
    start_date=datetime(2026, 4, 10),
    schedule="0 8 * * *", 
    catchup=False,
) as dag:

    raport_task = PythonOperator(
        task_id="send_daily",
        python_callable=send_raport,
    )