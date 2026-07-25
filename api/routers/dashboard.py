"""
This module provides Dashboard metrics for an organization
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


from src.utils.base.libraries import (
    JSONResponse,
    APIRouter,
    datetime,
    status
)
from src.main import (
    notifications_centrifugo_health_check,
    has_required_permissions,
    validate_permissions,
    rabbit_status_check,
    otel_health_check,
    CurrentUser
)
from src.database import (
    get_all_domains_under_organization,
    get_total_users_under_organization,
    total_top_logins_per_domain,
    top_ip_logins_per_domain,
    get_org_space_metrics,
    get_mailboxes_space,
    logins_per_domains,
    get_domains_stats,
    qdb_health_check,
    get_server_stats,
    ch_health_check,
    PostgresDep
)

# Router
router = APIRouter()


# Get Organization Space Metrics
@router.get("/organization_space/{organization_id}", response_class=JSONResponse, tags=["Dashboard"], summary="Get Organization Space Metrics")
async def get_organization_space_metrics(organization_id: str, current_user: CurrentUser, PgDB: PostgresDep) -> JSONResponse:
    """
    Get organization space metrics
    """
    await validate_permissions(
        current_user_permissions=current_user.permissions,
        basic_permissions=["dashboard:view"],
        organization_level_permissions=["organization:view"],
        current_user_organization_id=current_user.organization_id,
        accessed_organization_id=organization_id,
        user_id=None,
        db=PgDB
    )

    org_space = await get_org_space_metrics(organization_id=organization_id, db=PgDB)

    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content={
            "message": "Organization space metrics fetched successfully",
            "data": org_space
        }
    )

# Get Mailboxes Space Metrics
@router.get("/mailboxes_space/{organization_id}", response_class=JSONResponse, tags=["Dashboard"], summary="Get Mailboxes Space Metrics")
async def get_mailboxes_space_metrics(organization_id: str, current_user: CurrentUser, PgDB: PostgresDep) -> JSONResponse:
    """
    Get mailboxes space metrics
    """
    await validate_permissions(
        current_user_permissions=current_user.permissions,
        basic_permissions=["dashboard:view"],
        organization_level_permissions=["organization:view"],
        current_user_organization_id=current_user.organization_id,
        accessed_organization_id=organization_id,
        user_id=None,
        db=PgDB
    )

    domain_names = await get_all_domains_under_organization(organization_id=organization_id, db_session=PgDB)
    mailboxes_space = await get_mailboxes_space(domain_names=domain_names, db=PgDB)

    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content={
            "message": "Mailboxes space metrics fetched successfully",
            "data": {
                "mailboxes_space": mailboxes_space,
                "total_mailboxes": sum(domain["total_mailboxes"] for domain in mailboxes_space.values()),
                "total_active_mailboxes": sum(domain["total_active_mailboxes"] for domain in mailboxes_space.values()),
                "total_inactive_mailboxes": sum(domain["total_inactive_mailboxes"] for domain in mailboxes_space.values()),
                "total_quota_allocated": sum(domain["total_quota_allocated"] for domain in mailboxes_space.values()),
                "total_quota_utilized_bytes": sum(domain["total_quota_utilized_bytes"] for domain in mailboxes_space.values()),
                "total_emails_count": sum(domain["total_emails_count"] for domain in mailboxes_space.values()),
                "total_domains_with_mailboxes": len(mailboxes_space)
            }
        }
    )


# Get Total Users Under Organization
@router.get("/total_users/{organization_id}", response_class=JSONResponse, tags=["Dashboard"], summary="Get Total Users Under Organization")
async def get_total_users(organization_id: str, current_user: CurrentUser, PgDB: PostgresDep) -> JSONResponse:
    """
    Get total users under the organization
    """
    await validate_permissions(
        current_user_permissions=current_user.permissions,
        basic_permissions=["dashboard:view"],
        organization_level_permissions=["organization:view"],
        current_user_organization_id=current_user.organization_id,
        accessed_organization_id=organization_id,
        user_id=None,
        db=PgDB
    )

    total_users = await get_total_users_under_organization(organization_id=organization_id, db=PgDB)

    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content={
            "message": "Total users fetched successfully",
            "data": total_users
        }
    )


# Get Top Logins Per Domain
@router.get("/top_logins_per_domain/{organization_id}", response_class=JSONResponse, tags=["Dashboard"], summary="Get Top Logins Per Domain")
async def get_top_logins_per_domain(organization_id: str, current_user: CurrentUser, PgDB: PostgresDep) -> JSONResponse:
    """
    Get top logins per domain
    """
    await validate_permissions(
        current_user_permissions=current_user.permissions,
        basic_permissions=["dashboard:view"],
        organization_level_permissions=["organization:view"],
        current_user_organization_id=current_user.organization_id,
        accessed_organization_id=organization_id,
        user_id=None,
        db=PgDB
    )

    domain_names = await get_all_domains_under_organization(organization_id=organization_id, db_session=PgDB)
    top_logins = total_top_logins_per_domain(domains=domain_names, top_n=10)

    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content={
            "message": "Top logins per domain from past 7 days fetched successfully",
            "info": "This data is from the last 7 days",
            "data": top_logins
        }
    )


# Get Top IP Logins Per Domain
@router.get("/top_ip_logins_per_domain/{organization_id}", response_class=JSONResponse, tags=["Dashboard"], summary="Get Top IP Logins Per Domain")
async def get_top_ip_logins_per_domain(organization_id: str, current_user: CurrentUser, PgDB: PostgresDep) -> JSONResponse:
    """
    Get top IP logins per domain
    """
    await validate_permissions(
        current_user_permissions=current_user.permissions,
        basic_permissions=["dashboard:view"],
        organization_level_permissions=["organization:view"],
        current_user_organization_id=current_user.organization_id,
        accessed_organization_id=organization_id,
        user_id=None,
        db=PgDB
    )

    domain_names = await get_all_domains_under_organization(organization_id=organization_id, db_session=PgDB)
    top_ip_logins = top_ip_logins_per_domain(domains=domain_names, top_n=10)

    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content={
            "message": "Top IP logins per domain fetched successfully",
            "info": "This data is from the last 30 days",
            "data": top_ip_logins
        }
    )


# Get Logins Per Domain
@router.get("/logins_per_domain/{organization_id}", response_class=JSONResponse, tags=["Dashboard"], summary="Get Logins Per Domain")
async def get_logins_per_domain(organization_id: str, current_user: CurrentUser, PgDB: PostgresDep) -> JSONResponse:
    """
    Get logins per domain
    """
    await validate_permissions(
        current_user_permissions=current_user.permissions,
        basic_permissions=["dashboard:view"],
        organization_level_permissions=["organization:view"],
        current_user_organization_id=current_user.organization_id,
        accessed_organization_id=organization_id,
        user_id=None,
        db=PgDB
    )

    domain_names = await get_all_domains_under_organization(organization_id=organization_id, db_session=PgDB)
    logins_per_domain_data = logins_per_domains(domains=domain_names)

    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content={
            "message": "Logins per domain fetched successfully",
            "info": "This data is from the last 15 days",
            "data": logins_per_domain_data
        }
    )


# Status Endpoint
@router.get("/status", response_class=JSONResponse, tags=["Dashboard"], summary="Get System Status")
async def get_status(current_user: CurrentUser, PgDB: PostgresDep) -> JSONResponse:
    """
    Get system status
    """
    await validate_permissions(
        current_user_permissions=current_user.permissions,
        basic_permissions=["dashboard:view"],
        organization_level_permissions=["organization:view"],
        current_user_organization_id=current_user.organization_id,
        accessed_organization_id=current_user.organization_id,
        user_id=current_user.user_id,   # To check the DB connection status we are doing this
        db=PgDB
    )

    # Check RabbitMQ status
    queue_status = rabbit_status_check()

    # Check Notifications service status (Centrifugo)
    notifications_status = notifications_centrifugo_health_check()

    # Check Metrics service status (QDB)
    metrics_db_status = qdb_health_check()

    # Check Logging DB status (ClickHouse)
    logging_db_status = ch_health_check()

    # Check for O-Tel status
    otel_status = otel_health_check()

    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content={
            "message": "All Systems Operational" if queue_status and notifications_status and metrics_db_status and logging_db_status else "Degraded Performance",
            "data": {
                "main_db_status": "OK", # Assuming the main database is operational if we reach this point
                "queue_status": "OK" if queue_status else "DOWN",
                "cache_status": "OK",   # Since the current_user works then cache is working
                "api_status": "OK",     # Assuming the API is operational if we reach this point
                "notifications_status": "OK" if notifications_status else "DOWN",
                "metrics_db_status": "OK" if metrics_db_status else "DOWN",
                "logging_db_status": "OK" if logging_db_status else "DOWN",
                "telemetry_status": "OK" if otel_status else "DOWN"
            },
            "status": "OK" if queue_status and notifications_status and metrics_db_status and logging_db_status else "DEGRADED"
        }
    )


# Add metrics for Server Load, CPU, Memory, Disk, Network, etc (Input will be server_id)
@router.get("/server_metrics/{server_id}", response_class=JSONResponse, tags=["Dashboard"], summary="Get Server Metrics")
async def get_server_metrics(server_id: str, from_date_time: datetime, to_date_time: datetime, user: CurrentUser) -> JSONResponse:
    """
    Get server metrics
    """
    # Basic permission checks
    if not has_required_permissions(user_permissions=user.permissions, required_permissions=["server:view", "dashboard:view"]):
        return JSONResponse(
            status_code=status.HTTP_403_FORBIDDEN,
            content={"message": "You do not have permission to view server metrics."}
        )

    # Make sure datetimes are timezone-aware
    if from_date_time.tzinfo is None or to_date_time.tzinfo is None:
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content={"message": "from_date_time and to_date_time must be timezone-aware datetimes."}
        )

    server_stats_data = get_server_stats(server_id=server_id, from_date=from_date_time, to_date=to_date_time)
    if not server_stats_data:
        return JSONResponse(
            status_code=status.HTTP_404_NOT_FOUND,
            content={"message": "Server metrics not found."}
        )

    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content={
            "message": "Server metrics fetched successfully",
            "data": server_stats_data
        }
    )


# Get Domains Info
@router.get("/domains/{organization_id}", response_class=JSONResponse, tags=["Dashboard"], summary="Get Domains Info")
async def get_domains_info(organization_id: str, current_user: CurrentUser, PgDB: PostgresDep) -> JSONResponse:
    """
    Get domains info
    """
    await validate_permissions(
        current_user_permissions=current_user.permissions,
        basic_permissions=["dashboard:view"],
        organization_level_permissions=["organization:view"],
        current_user_organization_id=current_user.organization_id,
        accessed_organization_id=organization_id,
        user_id=None,
        db=PgDB
    )

    domains_stats = await get_domains_stats(db_session=PgDB, organization_id=organization_id)

    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content={
            "message": "Organization domains info fetched successfully",
            "data": domains_stats
        }
    )
