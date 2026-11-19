import os
import smtplib
import psycopg2
from airflow import DAG
from airflow.operators.bash import PythonOperator
from datetime import datetime, timedelta
from dotenv import load_dotenv
from email.message import EmailMessage
from airflow.models import DagRun