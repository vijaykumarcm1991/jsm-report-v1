import pandas as pd
from datetime import datetime
import pytz
from app.services.field_service import get_field_map


def generate_excel(data: list):

    if not data:
        raise Exception("No data to export")

    df = pd.DataFrame(data)
    df = df[[col for col in data[0].keys()]]

    # ✅ DEBUG (ADD HERE)
    print("Rows:", len(data))
    print("Columns:", df.columns)

    # ✅ Map field names
    field_map = get_field_map()
    df.rename(columns=field_map, inplace=True)

    # ✅ IST timestamp
    tz = pytz.timezone("Asia/Kolkata")
    timestamp = datetime.now(tz).strftime("%Y%m%d_%H%M%S")

    file_name = f"jira_report_{timestamp}.xlsx"
    file_path = f"/app/reports/{file_name}"

    df.to_excel(file_path, index=False)

    # ✅ VERY IMPORTANT
    return file_path, file_name