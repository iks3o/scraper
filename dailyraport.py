import os
import smtplib
from email.message import EmailMessage
from datetime import datetime, timedelta
import psycop2
from airflow import DAG
from airflow.operators.python import PythonOperator
from airflow.models import DagRun

def dbcheck():
#conn - connect
    conn = psycop2.connect(
        host=os.getenv("DB_HOST"),
        database=os.getenv("DB_NAME"),
        user=os.getenv("DB_USER"),
        password=os.getenv("dbpass"),
        port=os.getenv("DB_PORT", "5432"),
)
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT COUNT(*), ...")
            everything, new_24h, last_entry = cur.fetchone()
    finally:
        conn.close()
    return everything, new_24h, last_entry

dags_to_check = ["dariusz", "mariusz"]

def dagcheck():
    lines = []
    if_error = False
    for dag_id in dagcheck:
        runs = DagRun.find(dag_id=dag_id)

        if not runs:
            lines.append(f"- {dag_id}: Brak uruchomień.")
        if_error = True
        continue

    last = max(runs, key=lambda r: r.logical_date)
    status = str(last.state).upper()

    if status != "SUCCESS":
        if_error = True

#czas trwania zadania
    if last.start_date and last.end_date:
        time = int((last.end_date - last.start_date).total_seconds())
        time_txt = f"{time}s"
    else:
        time_txt = "w trakcie/ brak danych"
    start_txt = last.start_date.striftime("%Y-%m-%d %H:%M CET") if last.start_date 	else "brak"
    lines.append(f"- {dag_id}: {status} (start: {start_txt}, czas: {time_text})")
    return "\n".join(lines), if_error

###################
#WYSYLANIE RAPORTU#
###################

def send_raport():
	dag_raport, if_error = dagcheck()

	try:
		everything, new_24h, last_entry = dbcheck()
		last_txt = last_entry.strftime("%Y-%m_%d %H:%M") if last_entry else "brak"
		if new_24h == 0:
			if_eror = True
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
	haslo = os.getenv("EMAIL_APP_PASS")

	topic_status = "[Warning]" if if_error else "[OK]"
	today = datetime.now().strftime("%Y-%m_%d")

	msg = EmailMessage()
	msg["Subject"] = f"{topic_status} Raport serwera - {today}"
	msg["From"] = sender
	msg["To"] = receiver
	msg.set_content(
	    f" aaaa"
)

with smtplib.SMTP_SSL("smtp.gmail.com", 465) as smtp:
	smtp.login(sender, password)
	smtp.send_message(msg)

default_args = {
    "owner": airflow,
    "retries": 1,
    "retry_delay": timedelta(minutes=5),
}

with DAG(
	dag_id="daily_raport",
	default_args=default_args,
	start_date=datetime(2026, 4, 10),
	schedule="0 9 * * *", 
	catchup=False,
) as dag:

	raport_task = PythonOperator(
		task_id="send_daily",
		python_callable=send_raport,
	)