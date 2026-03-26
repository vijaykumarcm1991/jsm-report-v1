from fastapi import FastAPI
from datetime import datetime
import pytz
from app.config import TIMEZONE
from app.routers import jira_router
from fastapi.staticfiles import StaticFiles
from app.routers import report_router
from app.database import init_db

app = FastAPI()

# ✅ IMPORTANT: router first
app.include_router(jira_router.router)
app.include_router(report_router.router)

# ✅ THEN static mount
app.mount("/ui", StaticFiles(directory="app/static", html=True), name="static")

@app.on_event("startup")
def startup():
    init_db()

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