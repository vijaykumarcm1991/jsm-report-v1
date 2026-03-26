from datetime import datetime, timedelta


def build_jql(filters: dict) -> str:
    clauses = []

    # 🔹 PROJECT
    if filters.get("project"):
        projects = ",".join([f'"{p}"' for p in filters["project"]])
        clauses.append(f"project IN ({projects})")

    # 🔹 STATUS
    if filters.get("status"):
        status = ",".join([f'"{s}"' for s in filters["status"]])
        clauses.append(f"status IN ({status})")

    # 🔹 ISSUE TYPE
    if filters.get("issuetype"):
        types_ = ",".join([f'"{t}"' for t in filters["issuetype"]])
        clauses.append(f"issuetype IN ({types_})")

    # 🔹 DATE FILTERS
    start_date = filters.get("start_date")
    end_date = filters.get("end_date")
    range_days = filters.get("range")

    # Case 1: Range (last N days)
    if range_days:
        clauses.append(f"created >= -{int(range_days)}d")

    # Case 2: Start & End Date
    else:
        if start_date:
            clauses.append(f'created >= "{start_date}"')

        if end_date:
            next_day = (
                datetime.strptime(end_date, "%Y-%m-%d") + timedelta(days=1)
            ).strftime("%Y-%m-%d")

            clauses.append(f'created < "{next_day}"')

    if not clauses:
        return ""

    return " AND ".join(clauses)