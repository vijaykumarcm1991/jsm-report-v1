from datetime import datetime

def extract_value(field):
    if field is None:
        return None

    if isinstance(field, dict):
        return field.get("displayName") or field.get("name") or field.get("value")

    if isinstance(field, list):
        return ", ".join([str(extract_value(item)) for item in field])

    # ✅ Handle Jira datetime format
    if isinstance(field, str) and "T" in field and "+" in field:
        try:
            dt = datetime.strptime(field, "%Y-%m-%dT%H:%M:%S.%f%z")
            return dt.strftime("%Y-%m-%d %H:%M:%S")
        except:
            return field

    return field