import requests
from app.config import JIRA_BASE_URL, JIRA_PAT

HEADERS = {
    "Authorization": f"Bearer {JIRA_PAT}",
    "Accept": "application/json"
}

class JiraService:

    @staticmethod
    def get(endpoint, params=None):
        url = f"{JIRA_BASE_URL}{endpoint}"

        try:
            response = requests.get(url, headers=HEADERS, params=params, timeout=30)

            # Handle non-JSON (very important for on-prem issues)
            if "application/json" not in response.headers.get("Content-Type", ""):
                raise Exception(f"Non-JSON response from Jira: {response.text}")

            if response.status_code != 200:
                raise Exception(f"Jira API Error {response.status_code}: {response.text}")

            return response.json()

        except requests.exceptions.RequestException as e:
            raise Exception(f"Jira connection failed: {str(e)}")