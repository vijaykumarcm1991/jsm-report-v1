from fastapi import APIRouter
from app.services.jira_service import JiraService
from fastapi import Request
from app.utils.jql_builder import build_jql
from app.utils.data_extractor import extract_value
from app.models.search_model import SearchRequest
from fastapi.responses import FileResponse
from app.services.excel_service import generate_excel
from fastapi import HTTPException
import uuid
from threading import Thread
import threading
import time
import logging
from app.database import get_connection
from psycopg2.extras import Json
from fastapi import WebSocket
import asyncio

# ✅ LOGGER CONFIG
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s"
)

logger = logging.getLogger(__name__)

# ✅ DEFINE ROUTER FIRST
router = APIRouter(prefix="/jira", tags=["Jira"])

# ✅ ADD THIS
progress_store = {}

jobs_store = {}  # job_id → file_path

@router.get("/projects")
def get_projects():
    data = JiraService.get("/rest/api/2/project")

    projects = [
        {
            "key": proj.get("key"),
            "name": proj.get("name")
        }
        for proj in data
    ]

    return projects

@router.get("/issuetypes")
def get_issue_types():
    data = JiraService.get("/rest/api/2/issuetype")

    return [
        {
            "name": item.get("name"),
            "id": item.get("id")
        }
        for item in data
    ]

@router.get("/status")
def get_status():
    data = JiraService.get("/rest/api/2/status")

    return [
        {
            "name": item.get("name"),
            "id": item.get("id")
        }
        for item in data
    ]

@router.get("/fields")
def get_fields():
    data = JiraService.get("/rest/api/2/field")

    return [
        {
            "id": field.get("id"),
            "name": field.get("name")
        }
        for field in data
    ]

@router.post("/search")
def search_issues(request: SearchRequest):

    filters = request.filters.dict()
    selected_fields = request.fields

    jql = build_jql(filters)

    all_issues = []
    start_at = 0
    max_results = 50

    while True:
        params = {
            "jql": jql,
            "startAt": start_at,
            "maxResults": max_results,
            "fields": ",".join(selected_fields)
        }

        data = JiraService.get("/rest/api/2/search", params=params)

        issues = data.get("issues", [])
        if not issues:
            break

        for issue in issues:
            row = {"key": issue.get("key")}

            for field in selected_fields:
                value = issue.get("fields", {}).get(field)
                row[field] = extract_value(value)

            all_issues.append(row)

        start_at += max_results

        if start_at >= data.get("total", 0):
            break

    return {
        "total": len(all_issues),
        "data": all_issues
    }

def generate_report(request: SearchRequest, job_id: str):
    filters = request.filters.dict()
    selected_fields = request.fields

    if "key" not in selected_fields:
        selected_fields.insert(0, "key")

    jql = build_jql(filters)
    logger.info(f"[{job_id}] JQL: {jql}")

    all_issues = []
    start_at = 0
    max_results = 50

    while True:
        params = {
            "jql": jql,
            "startAt": start_at,
            "maxResults": max_results,
            "fields": ",".join(selected_fields)
        }

        data = JiraService.get("/rest/api/2/search", params=params)

        issues = data.get("issues", [])
        total = data.get("total", 0)

        logger.info(f"[{job_id}] Fetched batch: {len(issues)} issues (Total: {total})")

        if not issues:
            break

        for issue in issues:
            row = {}
            for field in selected_fields:
                if field == "key":
                    row["key"] = issue.get("key")
                else:
                    value = issue.get("fields", {}).get(field)
                    row[field] = extract_value(value)

            all_issues.append(row)

        start_at += max_results

        if total > 0:
            progress = int((len(all_issues) / total) * 100) if total > 0 else 100
            progress = min(progress, 100)
            progress_store[job_id] = progress
            logger.info(f"[{job_id}] Progress: {progress}%")

        if start_at >= total:
            break

    if not all_issues:
        raise HTTPException(status_code=404, detail="No issues found")

    file_path, file_name = generate_excel(all_issues)

    logger.info(f"[{job_id}] File generated: {file_path}")

    return file_path, file_name

@router.post("/download/start")
def start_download(request: SearchRequest):

    job_id = str(uuid.uuid4())
    progress_store[job_id] = 0

    logger.info(f"[{job_id}] Job started")

    def run_job():
        try:
            file_path, file_name = generate_report(request, job_id)
            jobs_store[job_id] = (file_path, file_name)
            time.sleep(1)
            progress_store[job_id] = 100

            # ✅ SAVE TO DB
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
                    Json(request.filters.dict()),
                    Json(request.fields)
                )
            )

            conn.commit()
            cur.close()
            conn.close()

            logger.info(f"[{job_id}] Saved to report_history")

        except Exception as e:
            progress_store[job_id] = -1  # error state
            logger.error(f"[{job_id}] ERROR: {str(e)}")

    Thread(target=run_job).start()

    return {"job_id": job_id}

@router.get("/download/file")
def download_file(job_id: str):

    if job_id not in jobs_store:
        raise HTTPException(status_code=404, detail="Job not found")

    file_path, file_name = jobs_store[job_id]

    logger.info(f"[{job_id}] Download requested: {file_path}")

    response = FileResponse(
        path=file_path,
        filename=file_name,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )

    # ✅ DELAY CLEANUP (IMPORTANT)
    def cleanup():
        time.sleep(20)  # wait for download
        jobs_store.pop(job_id, None)
        progress_store.pop(job_id, None)

    threading.Thread(target=cleanup).start()

    return response

@router.get("/progress/{job_id}")
def get_progress(job_id: str):
    return {"progress": progress_store.get(job_id, 0)}

@router.get("/history")
def get_history():

    from app.database import get_connection
    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
        SELECT id, name, file_path, created_at
        FROM report_history
        ORDER BY created_at DESC
    """)

    rows = cur.fetchall()

    result = []
    for r in rows:
        result.append({
            "id": r[0],
            "name": r[1],
            "file_path": r[2],
            "created_at": str(r[3])
        })

    return result

@router.get("/history/download/{id}")
def download_history(id: int):

    from app.database import get_connection
    conn = get_connection()
    cur = conn.cursor()

    cur.execute(
        "SELECT file_path, name FROM report_history WHERE id=%s",
        (id,)
    )

    row = cur.fetchone()

    if not row:
        raise HTTPException(status_code=404, detail="Report not found")

    file_path, name = row

    return FileResponse(
        path=file_path,
        filename=name,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )

@router.delete("/history/{id}")
def delete_history(id: int):

    from app.database import get_connection
    conn = get_connection()
    cur = conn.cursor()

    # get file path
    cur.execute("SELECT file_path FROM report_history WHERE id=%s", (id,))
    row = cur.fetchone()

    if not row:
        raise HTTPException(status_code=404, detail="Not found")

    file_path = row[0]

    # delete DB
    cur.execute("DELETE FROM report_history WHERE id=%s", (id,))
    conn.commit()

    # delete file
    import os
    if os.path.exists(file_path):
        os.remove(file_path)

    return {"message": "Deleted"}

@router.post("/schedule")
def create_schedule(request: dict):

    conn = get_connection()
    cur = conn.cursor()

    cur.execute(
        """
        INSERT INTO scheduled_reports
        (name, filters, fields, schedule_type, schedule_time, schedule_day, schedule_date)
        VALUES (%s, %s, %s, %s, %s, %s, %s)
        RETURNING id
        """,
        (
            request["name"],
            Json(request["filters"]),
            Json(request["fields"]),
            request["type"],
            request.get("time"),
            request.get("day"),
            request.get("date")
        )
    )

    schedule_id = cur.fetchone()[0]
    conn.commit()
    cur.close()
    conn.close()

    # register immediately
    from app.main import register_job
    register_job({
        "id": schedule_id,
        "name": request["name"],
        "filters": request["filters"],
        "fields": request["fields"],
        "type": request["type"],
        "time": request.get("time"),
        "day": request.get("day"),
        "date": request.get("date")
    })

    return {"message": "Scheduled successfully"}

@router.get("/schedule")
def get_schedules():

    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
        SELECT id, name, schedule_type, schedule_time, schedule_day, schedule_date
        FROM scheduled_reports
        ORDER BY created_at DESC
    """)

    rows = cur.fetchall()

    result = []
    for r in rows:
        result.append({
            "id": r[0],
            "name": r[1],
            "type": r[2],
            "time": r[3],
            "day": r[4],
            "date": r[5]
        })

    return result

@router.websocket("/ws/{job_id}")
async def websocket_progress(websocket: WebSocket, job_id: str):
    await websocket.accept()

    while True:
        progress = progress_store.get(job_id, 0)
        await websocket.send_json({"progress": progress})

        if progress >= 100 or progress == -1:
            break

        await asyncio.sleep(1)