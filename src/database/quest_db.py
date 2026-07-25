"""
All functions in this file are related to the quest database operations
"""

"""
Copyright (C) 2026 Yukthi Systems Private Limited

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License version 3
as published by the Free Software Foundation.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
version 3 along with this program. If not, see
<https://www.gnu.org/licenses/>.
"""


from src.utils.base.libraries import datetime, logging, requests, base64, timezone
from src.utils.base.constants import QUEST_DB_HOST, QUEST_DB_PORT, QUEST_DB_USER, QUEST_DB_PASSWORD


def _exec_query(query: str, from_entry: int = 0, to_entry: int = 10) -> tuple[int, list[dict]]:
    """
    Execute a query against the quest database and return the count and data
    """
    headers = {
        'Content-Type': 'application/json',
        'Authorization': f"Basic {base64.b64encode(f'{QUEST_DB_USER}:{QUEST_DB_PASSWORD}'.encode()).decode()}"
    }
    params = {
        'count': 'true',
        'src': 'con',
        'query': query,
        'timings': 'false',
        'version': '2',
        'limit': f'{from_entry},{to_entry}',
        'explain': 'false'
    }

    try:
        resp = requests.get(
            f"http://{QUEST_DB_HOST}:{QUEST_DB_PORT}/exec",
            params=params,
            headers=headers
        )
        data = resp.json()
        if 'error' in data:
            logging.error(f"Error executing query: {data['error']}")
            return 0, []

        columns = [col['name'] for col in data['columns']]
        return data['count'], [dict(zip(columns, row)) for row in data['dataset']]

    except Exception as e:
        logging.error(f"Error executing query via REST: {e}")
        return 0, []


def get_login_attempts(
    from_date: datetime,
    to_date: datetime,
    current_page: int = 1,
    page_size: int = 10,
    email_id: str = "",
    domain_name: str = "",
    origin_ip: str = ""
) -> dict:
    """
    Fetch login attempts from the quest database within a specified date range
    """
    query = f"""
    SELECT timestamp, origin_ip, email_id, domain_name
    FROM login_attempt
    WHERE timestamp >= '{from_date.isoformat()}' AND timestamp <= '{to_date.isoformat()}'
    """

    # Apply filters if provided
    if email_id:
        query += f" AND email_id = '{email_id}'"

    if domain_name:
        query += f" AND domain_name = '{domain_name}'"

    if origin_ip:
        query += f" AND origin_ip = '{origin_ip}'"

    query += f" ORDER BY timestamp DESC"

    # Calculate pagination
    offset = (current_page - 1) * page_size
    from_entry = offset + 1
    to_entry = page_size * current_page

    # Execute base query to get paginated results
    total_entries, data_ = _exec_query(query=query, from_entry=from_entry, to_entry=to_entry)

    return {
        "total_count": total_entries,
        "current_page": current_page,
        "page_size": page_size,
        "total_pages": (total_entries + page_size - 1) // page_size,
        "has_next_page": (current_page * page_size) < total_entries,
        "data": data_
    }


def logins_per_domains(domains: list[str]) -> dict:
    """
    Fetch login attempts per domain
    """
    if not domains:
        return {}

    query = f"""
    SELECT domain_name, count(*) AS total_logins
    FROM login_attempt
    WHERE domain_name IN ({', '.join(f"'{domain}'" for domain in domains)})
    AND timestamp >= dateadd('d', -15, now())
    GROUP BY domain_name
    """

    _, data = _exec_query(query=query, from_entry=0, to_entry=10)
    if not data:
        return {}

    return {row['domain_name']: row['total_logins'] for row in data}


def total_top_logins_per_domain(domains: list[str], top_n: int = 10) -> dict:
    """
    Fetch the top N login attempts per domain
    """
    if not domains:
        return {}

    query = f"""
    SELECT domain_name, email_id, count(*) AS total_logins
    FROM login_attempt
    WHERE domain_name IN ({', '.join(f"'{domain}'" for domain in domains)})
    AND timestamp >= dateadd('d', -7, now())
    GROUP BY domain_name, email_id
    ORDER BY total_logins DESC
    LIMIT {top_n}
    """

    _, data = _exec_query(query=query, from_entry=0, to_entry=top_n)
    if not data:
        return {}

    result = {}
    for row in data:
        domain = row['domain_name']
        if domain not in result:
            result[domain] = []
        result[domain].append({
            "email_id": row['email_id'],
            "total_logins": row['total_logins']
        })
    
    return result


def top_ip_logins_per_domain(domains: list[str], top_n: int = 10) -> dict:
    """
    Fetch the top N login attempts per domain by IP address
    """
    if not domains:
        return {}

    query = f"""
    SELECT domain_name, origin_ip, count(*) AS total_logins
    FROM login_attempt
    WHERE domain_name IN ({', '.join(f"'{domain}'" for domain in domains)})
    AND timestamp >= dateadd('d', -30, now())
    GROUP BY domain_name, origin_ip
    ORDER BY total_logins DESC
    LIMIT {top_n}
    """

    _, data = _exec_query(query=query, from_entry=0, to_entry=top_n)
    if not data:
        return {}

    result = {}
    for row in data:
        domain = row['domain_name']
        if domain not in result:
            result[domain] = []
        result[domain].append({
            "origin_ip": row['origin_ip'],
            "total_logins": row['total_logins']
        })
    
    return result


def get_server_stats(server_id: str, from_date: datetime, to_date: datetime) -> dict:
    """
    Fetch server metrics for a specific server within a date range.
    The metrics include CPU, memory, disk, and network statistics.
    The date range must be timezone-aware and in UTC.
    """
    # Convert to UTC
    from_date_utc = from_date.astimezone(timezone.utc)
    to_date_utc = to_date.astimezone(timezone.utc)

    query = f"""
    SELECT
        CAST(
            (CAST(timestamp AS LONG) / (5 * 60 * 1000000)) * (5 * 60 * 1000000)
            AS TIMESTAMP
        ) AS interval_start,

        AVG(cpu_percent) AS avg_cpu_percent,
        AVG(load_avg_1) AS avg_load_avg_1,
        AVG(load_avg_5) AS avg_load_avg_5,
        AVG(load_avg_15) AS avg_load_avg_15,

        AVG(mem_total_mb) AS avg_mem_total_mb,
        AVG(mem_used_mb) AS avg_mem_used_mb,
        AVG(mem_available_mb) AS avg_mem_available_mb,
        AVG(mem_percent) AS avg_mem_percent,

        AVG(disk_total_gb) AS avg_disk_total_gb,
        AVG(disk_used_gb) AS avg_disk_used_gb,
        AVG(disk_free_gb) AS avg_disk_free_gb,
        AVG(disk_percent) AS avg_disk_percent,

        AVG(disk_read_MBps) AS avg_disk_read_MBps,
        AVG(disk_write_MBps) AS avg_disk_write_MBps,

        AVG(net_sent_MBps) AS avg_net_sent_MBps,
        AVG(net_recv_MBps) AS avg_net_recv_MBps

    FROM server_metrics
    WHERE
        server_id = '{server_id}'
        AND timestamp >= TIMESTAMP '{from_date_utc.strftime('%Y-%m-%d %H:%M:%S')}'
        AND timestamp < TIMESTAMP '{to_date_utc.strftime('%Y-%m-%d %H:%M:%S')}'
    GROUP BY
    """

    # Execute the query
    total_days = (to_date_utc - from_date_utc).days
    total_hours = (to_date_utc - from_date_utc).seconds // 3600
    total_minutes = (to_date_utc - from_date_utc).seconds // 60

    if total_days > 7 or total_days < 0:
        return {
            "server_id": server_id,
            "from_date": from_date_utc.isoformat(),
            "to_date": to_date_utc.isoformat(),
            "range": str(to_date_utc - from_date_utc),
            "interval": "5 minutes" if total_days <= 3 else "20 minutes",
            "total_records": 0,
            "metrics": [],
            "error": "Date range exceeds 7 days, please narrow down the range." if total_days > 7 else "Invalid date range."
        }
    
    interval_str = "5 minutes"
    cast_query = f"""
        CAST(
            (CAST(timestamp AS LONG) / (5 * 60 * 1000000)) * (5 * 60 * 1000000)
            AS TIMESTAMP
        )
    ORDER BY
        interval_start;
    """

    # 288 intervals in 24 hours with 5 min intervals - Fetching all intervals for the given range
    max_possible_size = (total_days * 288) + (total_hours * 12) + (total_minutes // 5) + 1
    if max_possible_size > 1000:
        # Switch to 20 minutes interval
        max_possible_size = (total_days * 72) + (total_hours * 3) + (total_minutes // 20) + 1
        interval_str = "20 minutes"
        cast_query = f"""
            CAST(
                (CAST(timestamp AS LONG) / (20 * 60 * 1000000)) * (20 * 60 * 1000000)
                AS TIMESTAMP
            )
        ORDER BY
            interval_start;
        """

    # Append the cast query to the main query
    query += cast_query

    _, data = _exec_query(query=query, from_entry=0, to_entry=max_possible_size)
    if data:
        return {
            "server_id": server_id,
            "from_date": from_date_utc.isoformat(),
            "to_date": to_date_utc.isoformat(),
            "range": str(to_date_utc - from_date_utc),
            "interval": interval_str,
            "total_records": len(data),
            "metrics": data
        }

    return {
        "server_id": server_id,
        "from_date": from_date_utc.isoformat(),
        "to_date": to_date_utc.isoformat(),
        "range": str(to_date_utc - from_date_utc),
        "interval": interval_str,
        "total_records": 0,
        "metrics": [],
        "error": "No data found for the given date range."
    }


def qdb_health_check() -> bool:
    """
    Check if the QuestDB is healthy by sending a ping request.
    """
    try:
        response = requests.get(f"http://{QUEST_DB_HOST}:{QUEST_DB_PORT}/ping")
        return response.status_code == 204

    except Exception as e:
        logging.error(f"QuestDB health check failed: {e}", exc_info=True)
        return False
