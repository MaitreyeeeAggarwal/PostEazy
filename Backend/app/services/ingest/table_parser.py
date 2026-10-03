import re
from typing import List, Optional
from pydantic import BaseModel

class TableData(BaseModel):
    title: str = "Data Overview"
    headers: List[str]
    rows: List[List[str]]
    chart_type: str = "bar"  # "bar", "line", "pie"

def detect_chart_type(headers: List[str], rows: List[List[str]]) -> str:
    """Auto-detects ideal chart type (bar, line, pie) based on headers and row values."""
    full_headers_str = " ".join(headers).lower()
    
    # 1. Line chart for time series (Year, Quarter, Month, Date, Time, Trend)
    if any(k in full_headers_str for k in ["year", "quarter", "month", "date", "q1", "q2", "q3", "q4", "202", "201", "time"]):
        return "line"
    
    # 2. Pie / Donut chart if single numeric column sums to ~100% or represents distribution/share
    if any(k in full_headers_str for k in ["share", "distribution", "breakdown", "percentage", "portion", "market share"]):
        return "pie"
    
    # Default to high-impact Bar Chart
    return "bar"

def parse_markdown_table(lines: List[str]) -> Optional[TableData]:
    """Parses markdown table lines (| col1 | col2 |) into structured TableData."""
    clean_lines = [l.strip() for l in lines if l.strip().startswith("|") and l.strip().endswith("|")]
    if len(clean_lines) < 2:
        return None
    
    # Filter out divider line (| --- | --- |)
    table_rows = []
    for l in clean_lines:
        if re.match(r"^\|[\s\-:|]+\|$", l):
            continue
        cells = [c.strip() for c in l.strip("|").split("|")]
        table_rows.append(cells)
    
    if len(table_rows) < 2:
        return None
    
    headers = table_rows[0]
    rows = table_rows[1:]
    chart_type = detect_chart_type(headers, rows)
    
    return TableData(
        title=f"Table: {headers[0]} breakdown",
        headers=headers,
        rows=rows,
        chart_type=chart_type
    )
