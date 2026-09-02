"""
Handler for ClickHouse database operations, specifically for audit logs and mail flow logs
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


from src.utils.base.libraries import datetime, clickhouse_connect, date, timedelta, timezone, logging
from src.utils.base.constants import (
    CLICK_HOUSE_MAIL_FLOW_LOGS_TABLE,
    CLICK_HOUSE_AUDIT_LOGS_TABLE,
    CLICK_HOUSE_USERNAME,
    CLICK_HOUSE_PASSWORD,
    CLICK_HOUSE_HOST,
    CLICK_HOUSE_PORT
)


def _process_row(result_rows, column_names) -> list[dict]:
    """
    Process the result rows from ClickHouse query and convert them to a list of dictionaries.
    Handles bytes and datetime formatting, recursively for lists & dicts.
    """
    def process_value(value):
        if isinstance(value, bytes):
            return value.decode('utf-8')
        elif isinstance(value, datetime) or isinstance(value, date):
            return value.isoformat()
        elif isinstance(value, list):
            return [process_value(item) for item in value]
        elif isinstance(value, dict):
            return {k: process_value(v) for k, v in value.items()}
        else:
            return value

    if not result_rows:
        return []

    data = []
    for row in result_rows:
        row_dict = {}
        for i, column_name in enumerate(column_names):
            value = row[i]
            row_dict[column_name] = process_value(value)
        data.append(row_dict)

    return data


def _convert_to_ist(dt: datetime) -> str:
    """
    Convert a timezone-aware datetime to IST timezone
    For ClickHouse querying
    """
    ist_timezone = timezone(timedelta(hours=5, minutes=30))
    dt_ist = dt.astimezone(ist_timezone)
    return dt_ist.strftime('%Y-%m-%d %H:%M:%S')


def _create_query_for_mail_flow_logs(
    current_page: int,
    page_size: int,
    from_date: datetime,
    to_date: datetime,
    euid: str,
    subject: str,
    log_type: str,
    log_status: str,
    from_email_id: str,
    to_email_ids: list[str],
    user_domain: str
) -> tuple[str, str, dict]:
    """
    Create parameterized queries for mail flow logs.
    """
    query = f"""
        SELECT *
        FROM {CLICK_HOUSE_MAIL_FLOW_LOGS_TABLE}
        WHERE
    """

    count_query = f"""
        SELECT COUNT(*)
        FROM {CLICK_HOUSE_MAIL_FLOW_LOGS_TABLE}
        WHERE
    """

    where_clauses = [
        "log_timestamp BETWEEN "
        "toDateTime({from_date:String}, 'Asia/Kolkata') "
        "AND toDateTime({to_date:String}, 'Asia/Kolkata')",
        "AND has(email_domains, {user_domain:String})"
    ]

    parameters = {
        "from_date": _convert_to_ist(from_date),
        "to_date": _convert_to_ist(to_date),
        "user_domain": user_domain,
    }

    if euid:
        where_clauses.append("AND euid = {euid:String}")
        parameters["euid"] = euid

    if subject:
        where_clauses.append("AND subject LIKE {subject:String}")
        parameters["subject"] = f"%{subject}%"

    if log_type:
        where_clauses.append("AND type = {log_type:String}")
        parameters["log_type"] = log_type

    if log_status:
        where_clauses.append("AND status = {log_status:String}")
        parameters["log_status"] = log_status

    if from_email_id:
        where_clauses.append("AND from_email_id = {from_email_id:String}")
        parameters["from_email_id"] = from_email_id

    if to_email_ids:
        where_clauses.append(
            "AND hasAny(to_email_ids, {to_email_ids:Array(String)})"
        )
        parameters["to_email_ids"] = to_email_ids

    # Combine all where clauses
    where_statement = " ".join(where_clauses)

    query += where_statement
    count_query += where_statement

    # Add pagination for main query
    offset = (current_page - 1) * page_size

    query += """
        ORDER BY log_timestamp DESC
        LIMIT {page_size:UInt64}
        OFFSET {offset:UInt64}
    """

    parameters["page_size"] = page_size
    parameters["offset"] = offset

    return query, count_query, parameters


def get_mail_flow_logs(
    current_page: int,
    page_size: int,
    from_date: datetime,
    to_date: datetime,
    euid: str,
    subject: str,
    log_type: str,
    log_status: str,
    from_email_id: str,
    to_email_ids: list[str],
    user_domain: str
) -> dict:
    """
    Get the admin logs from the ClickHouse DB
    """
    conn = clickhouse_connect.get_client(
        host=CLICK_HOUSE_HOST,
        port=CLICK_HOUSE_PORT,
        username=CLICK_HOUSE_USERNAME,
        password=CLICK_HOUSE_PASSWORD
    )

    # Create the query
    query, count_query, parameters = _create_query_for_mail_flow_logs(
        current_page=current_page,
        page_size=page_size,
        from_date=from_date,
        to_date=to_date,
        euid=euid,
        subject=subject,
        log_type=log_type,
        log_status=log_status,
        from_email_id=from_email_id,
        to_email_ids=to_email_ids,
        user_domain=user_domain
    )

    # Get the total count of records
    total_count_result = conn.query(count_query, parameters=parameters)
    total_count = total_count_result.result_rows[0][0] if total_count_result.result_rows else 0
    if total_count == 0:
        return {
            "data": [],
            "current_page": current_page,
            "page_size": page_size,
            "total_count": 0,
            "total_pages": 0
        }

    # Execute the query and fetch the results
    result = conn.query(query, parameters=parameters)
    if not result.result_rows:
        return {
            "data": [],
            "current_page": current_page,
            "page_size": page_size,
            "total_count": 0,
            "total_pages": 0
        }

    # Log the response
    logging.info(f"Summary of the Count Query: {total_count_result.summary}")
    logging.info(f"Summary of the Result Query: {result.summary}")

    # Convert the result to a list of dictionaries
    data = _process_row(result_rows=result.result_rows, column_names=result.column_names)

    return {
        "data": data,
        "current_page": current_page,
        "page_size": page_size,
        "total_count": total_count,
        "total_pages": (total_count + page_size - 1) // page_size
    }


def _create_query_for_audit_logs(
    organization_id: str,
    start_time: datetime,
    end_time: datetime,
    current_page: int,
    page_size: int,
    user_id: str = None,
    message: str = None,
    action_type: str = None
) -> tuple[str, str, dict]:
    """
    Create parameterized queries to fetch audit logs from ClickHouse.
    """
    query = f"""
        SELECT *
        FROM {CLICK_HOUSE_AUDIT_LOGS_TABLE}
        WHERE
    """

    count_query = f"""
        SELECT COUNT(*)
        FROM {CLICK_HOUSE_AUDIT_LOGS_TABLE}
        WHERE
    """

    where_clauses = [
        "organization_id = {organization_id:String}",
        "AND action_timestamp BETWEEN "
        "toDateTime({start_time:String}, 'Asia/Kolkata') "
        "AND toDateTime({end_time:String}, 'Asia/Kolkata')"
    ]

    parameters = {
        "organization_id": organization_id,
        "start_time": _convert_to_ist(start_time),
        "end_time": _convert_to_ist(end_time),
    }

    if user_id:
        where_clauses.append("AND user_id = {user_id:String}")
        parameters["user_id"] = user_id

    if message:
        where_clauses.append("AND message LIKE {message:String}")
        parameters["message"] = f"%{message}%"

    if action_type:
        where_clauses.append("AND action_type = {action_type:String}")
        parameters["action_type"] = action_type

    # Combine all where clauses
    where_statement = " ".join(where_clauses)

    query += where_statement
    count_query += where_statement

    # Add pagination for main query
    offset = (current_page - 1) * page_size

    query += """
        ORDER BY action_timestamp DESC
        LIMIT {page_size:UInt64}
        OFFSET {offset:UInt64}
    """

    parameters["page_size"] = page_size
    parameters["offset"] = offset

    return query, count_query, parameters


def get_audit_logs(
    organization_id: str,
    start_time: datetime,
    end_time: datetime,
    user_id: str = None,
    search_text: str = None,
    action_type: str = None,
    current_page: int = 1,
    page_size: int = 20
) -> dict:
    """
    Get the audit logs from the ClickHouse DB
    """
    conn = clickhouse_connect.get_client(
        host=CLICK_HOUSE_HOST,
        port=CLICK_HOUSE_PORT,
        username=CLICK_HOUSE_USERNAME,
        password=CLICK_HOUSE_PASSWORD
    )

    # Create the query
    query, count_query, parameters = _create_query_for_audit_logs(
        organization_id=organization_id,
        start_time=start_time,
        end_time=end_time,
        current_page=current_page,
        page_size=page_size,
        user_id=user_id,
        message=search_text,
        action_type=action_type
    )

    # Get the total count of records
    total_count_result = conn.query(count_query, parameters=parameters)
    total_count = total_count_result.result_rows[0][0] if total_count_result.result_rows else 0
    if total_count == 0:
        return {
            "data": [],
            "current_page": current_page,
            "page_size": page_size,
            "total_count": 0,
            "total_pages": 0
        }

    # Execute the query and fetch the results
    result = conn.query(query, parameters=parameters)
    if not result.result_rows:
        return {
            "data": [],
            "current_page": current_page,
            "page_size": page_size,
            "total_count": 0,
            "total_pages": 0
        }

    # Log the response
    logging.info(f"Summary of the Count Query: {total_count_result.summary}")
    logging.info(f"Summary of the Result Query: {result.summary}")

    # Convert the result to a list of dictionaries
    data = _process_row(result_rows=result.result_rows, column_names=result.column_names)

    return {
        "data": data,
        "current_page": current_page,
        "page_size": page_size,
        "total_count": total_count,
        "total_pages": (total_count + page_size - 1) // page_size
    }


def ch_health_check() -> bool:
    """
    Check the health of the ClickHouse database connection
    """
    try:
        conn = clickhouse_connect.get_client(
            host=CLICK_HOUSE_HOST,
            port=CLICK_HOUSE_PORT,
            username=CLICK_HOUSE_USERNAME,
            password=CLICK_HOUSE_PASSWORD
        )
        # Execute a simple query to check the connection
        conn.query("SELECT 1")
        return True

    except Exception as e:
        logging.error(f"ClickHouse health check failed: {e}", exc_info=True)
        return False
