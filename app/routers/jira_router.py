from fastapi import APIRouter
from app.services.jira_service import JiraService
from fastapi import Request
from app.utils.jql_builder import build_jql
from app.utils.data_extractor import extract_value
from app.models.search_model import SearchRequest
from fastapi.responses import FileResponse
from app.services.excel_service import generate_excel
from fastapi import HTTPException

# ✅ DEFINE ROUTER FIRST
router = APIRouter(prefix="/jira", tags=["Jira"])

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

@router.post("/download")
def download_excel(request: SearchRequest):

    filters = request.filters.dict()
    selected_fields = request.fields

    if "key" not in selected_fields:
        selected_fields.insert(0, "key")

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
        total = data.get("total", 0)  # ✅ ADD THIS
        if not issues:
            break

        for issue in issues:
            row = {}

            # ✅ Maintain order
            for field in selected_fields:
                if field == "key":
                    row["key"] = issue.get("key")
                else:
                    value = issue.get("fields", {}).get(field)
                    row[field] = extract_value(value)

            all_issues.append(row)

        start_at += max_results

        # ✅ PROGRESS FIRST
        if total > 0:
            progress = int((start_at / total) * 100)
            print(f"PROGRESS:{progress}")

        # ✅ THEN BREAK
        if start_at >= total:
            break

    # ✅ ADD THIS BLOCK
    if not all_issues:
        raise HTTPException(status_code=404, detail="No issues found")

    file_path, file_name = generate_excel(all_issues)

    return FileResponse(
        path=file_path,
        filename=file_name,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )