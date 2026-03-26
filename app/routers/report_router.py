from fastapi import APIRouter, HTTPException
from psycopg2.extras import Json
from app.database import get_connection

router = APIRouter(prefix="/reports", tags=["Reports"])

@router.post("/")
def create_report(body: dict):
    conn = get_connection()
    cur = conn.cursor()

    cur.execute(
        """
        INSERT INTO reports (name, filters, fields)
        VALUES (%s, %s, %s)
        RETURNING id
        """,
        (body["name"], Json(body["filters"]), Json(body["fields"]))
    )

    report_id = cur.fetchone()[0]
    conn.commit()

    return {"id": report_id}

@router.get("/")
def get_reports():
    conn = get_connection()
    cur = conn.cursor()

    cur.execute("SELECT id, name FROM reports ORDER BY id DESC")
    rows = cur.fetchall()

    return [{"id": r[0], "name": r[1]} for r in rows]

@router.get("/{report_id}")
def get_report(report_id: int):
    conn = get_connection()
    cur = conn.cursor()

    cur.execute("SELECT * FROM reports WHERE id=%s", (report_id,))
    row = cur.fetchone()

    if not row:
        raise HTTPException(404, "Report not found")

    return {
        "id": row[0],
        "name": row[1],
        "filters": row[2],
        "fields": row[3]
    }

@router.put("/{report_id}")
def update_report(report_id: int, body: dict):
    conn = get_connection()
    cur = conn.cursor()

    cur.execute(
        """
        UPDATE reports
        SET name=%s, filters=%s, fields=%s
        WHERE id=%s
        """,
        (body["name"], str(body["filters"]), str(body["fields"]), report_id)
    )

    conn.commit()

    return {"message": "updated"}

@router.delete("/{report_id}")
def delete_report(report_id: int):
    conn = get_connection()
    cur = conn.cursor()

    cur.execute("DELETE FROM reports WHERE id=%s", (report_id,))
    conn.commit()

    return {"message": "deleted"}