from fastapi import FastAPI
from apscheduler.schedulers.background import BackgroundScheduler
from app.database import get_connection
from app.routers.jira_router import generate_report
from app.models.search_model import SearchRequest
import uuid
import json
import logging
from datetime import datetime
import pytz
from app.config import TIMEZONE
from app.routers import jira_router
from fastapi.staticfiles import StaticFiles
from app.routers import report_router
from app.database import init_db

app = FastAPI()

scheduler = BackgroundScheduler()
scheduler.start()

# ✅ IMPORTANT: router first
app.include_router(jira_router.router)
app.include_router(report_router.router)

# ✅ THEN static mount
app.mount("/ui", StaticFiles(directory="app/static", html=True), name="static")

@app.on_event("startup")
def startup():
    init_db()
    load_schedules()

@app.get("/")
def home():
    return {"message": "JSM Report API Running"}

@app.get("/health")
def health():
    tz = pytz.timezone(TIMEZONE)
    return {
        "status": "ok",
        "time": datetime.now(tz).strftime("%Y-%m-%d %H:%M:%S"),
        "timezone": TIMEZONE
    }

def run_scheduled_job(schedule):

    job_id = str(uuid.uuid4())
    logging.info(f"[SCHEDULER] Running job: {schedule['name']}")

    try:
        request = SearchRequest(
            filters=schedule["filters"],
            fields=schedule["fields"]
        )

        file_path, file_name = generate_report(request, job_id)

        # save to history
        conn = get_connection()
        cur = conn.cursor()

        cur.execute(
            """
            INSERT INTO report_history (name, file_path, filters, fields)
            VALUES (%s, %s, %s, %s)
            """,
            (
                file_name,
                file_path,
                schedule["filters"],
                schedule["fields"]
            )
        )

        conn.commit()
        cur.close()
        conn.close()

        logging.info(f"[SCHEDULER] Report generated: {file_name}")

    except Exception as e:
        logging.error(f"[SCHEDULER] ERROR: {str(e)}")

def load_schedules():

    conn = get_connection()
    cur = conn.cursor()

    cur.execute("SELECT * FROM scheduled_reports")
    rows = cur.fetchall()

    for r in rows:
        schedule = {
            "id": r[0],
            "name": r[1],
            "filters": r[2],
            "fields": r[3],
            "type": r[4],
            "time": r[5],
            "day": r[6],
            "date": r[7]
        }

        register_job(schedule)

    cur.close()
    conn.close()

def register_job(schedule):

    hour, minute = map(int, schedule["time"].split(":"))

    if schedule["type"] == "one-time":
        scheduler.add_job(
            run_scheduled_job,
            "date",
            run_date=schedule["time"],
            args=[schedule]
        )

    elif schedule["type"] == "daily":
        scheduler.add_job(
            run_scheduled_job,
            "cron",
            hour=hour,
            minute=minute,
            args=[schedule]
        )

    elif schedule["type"] == "weekly":
        scheduler.add_job(
            run_scheduled_job,
            "cron",
            day_of_week=schedule["day"].lower(),
            hour=hour,
            minute=minute,
            args=[schedule]
        )

    elif schedule["type"] == "monthly":
        scheduler.add_job(
            run_scheduled_job,
            "cron",
            day=schedule["date"],
            hour=hour,
            minute=minute,
            args=[schedule]
        )