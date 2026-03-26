from app.services.jira_service import JiraService

def get_field_map():
    data = JiraService.get("/rest/api/2/field")

    return {
        field["id"]: field["name"]
        for field in data
    }