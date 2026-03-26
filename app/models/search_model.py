from pydantic import BaseModel
from typing import List, Optional


class Filters(BaseModel):
    project: Optional[List[str]] = None
    status: Optional[List[str]] = None
    issuetype: Optional[List[str]] = None
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    range: Optional[int] = None


class SearchRequest(BaseModel):
    filters: Filters
    fields: List[str]