from fastapi import FastAPI
from datetime import datetime
import pytz
from app.config import TIMEZONE
from app.routers import jira_router
from fastapi.staticfiles import StaticFiles

app = FastAPI()

# ✅ IMPORTANT: router first
app.include_router(jira_router.router)

# ✅ THEN static mount
app.mount("/", StaticFiles(directory="app/static", html=True), name="static")

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