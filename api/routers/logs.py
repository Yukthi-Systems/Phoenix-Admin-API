"""
This module provides Domain related API endpoints
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
    status
)
from src.main import CurrentUser, validate_permissions, rmq_audit_logs, send_notification
from src.utils.models import AuditSearchForm, AddAuditLog, MailFlowSearchForm, LoginAttemptsSearchForm
from src.database import PostgresDep, get_mail_flow_logs, get_audit_logs, get_login_attempts, check_domain_organization_mapping


# Router
router = APIRouter()


# Search audit logs
@router.post("/audit/search", response_class=JSONResponse, tags=["Audit Logs"], summary="Search audit logs")
async def audit_logs_search(data: AuditSearchForm, current_page: int, page_size: int, user: CurrentUser, PgDB: PostgresDep) -> JSONResponse:
    """
    Search for audit logs based on the provided criteria
    """
    await validate_permissions(
        current_user_permissions=user.permissions,
        basic_permissions=["logs:audit:view"],
        organization_level_permissions=["organization:view"],
        current_user_organization_id=user.organization_id,
        accessed_organization_id=data.organization_id,
        user_id=data.user_id,
        db=PgDB
    )

    # Search for audit logs (CickHouse)
    data = get_audit_logs(
        organization_id=data.organization_id,
        start_time=data.date_range.from_date,
        end_time=data.date_range.to_date,
        user_id=data.user_id,
        search_text=data.search_text,
        action_type=data.action_type,
        current_page=current_page,
        page_size=page_size
    )

    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content=data
    )


# Mail flow Logs search
@router.post("/mail-flow/search", response_class=JSONResponse, tags=["Mail Flow Logs"], summary="Search mail flow logs")
async def mail_flow_logs_search(data: MailFlowSearchForm, current_page: int, page_size: int, user: CurrentUser, PgDB: PostgresDep) -> JSONResponse:
    """
    Search for mail flow logs based on the provided criteria
    """
    await validate_permissions(
        current_user_permissions=user.permissions,
        basic_permissions=["logs:mail_flow:view", "domain:view"],
        organization_level_permissions=["organization:view"],
        current_user_organization_id=user.organization_id,
        accessed_organization_id=data.organization_id,
        user_id=None,
        db=PgDB
    )

    await check_domain_organization_mapping(
        db_session=PgDB,
        domain_name=data.domain_name,
        organization_id=data.organization_id
    )

    # Search for mail flow logs (CickHouse)
    data: list[dict] = get_mail_flow_logs(
        current_page=current_page,
        page_size=page_size,
        from_date=data.date_range.from_date,
        to_date=data.date_range.to_date,
        euid=data.euid,
        subject=data.subject,
        log_type=data.log_type,
        log_status=data.log_status,
        from_email_id=data.from_email_id,
        to_email_ids=data.to_email_ids,
        user_domain=data.domain_name
    )

    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content=data
    )


# Add audit log
@router.post("/audit/add", response_class=JSONResponse, tags=["Audit Logs"], summary="Add audit log")
async def add_audit_log(notify: bool, data: AddAuditLog, user: CurrentUser) -> JSONResponse:
    """
    Add a new audit log
    """
    rmq_audit_logs(
        message=data.model_dump(),
        organization_id=data.organization_id,
        user_id=user.user_id
    )

    if notify:
        send_notification(
            notification_type="push",
            to=f"notifications:{user.organization_id}",
            template_name="push_audit_log",
            variables={
                # Notification will be sent to the user's organization not the organization of the audit log
                "organization_id": user.organization_id,
                "organization_name": user.organization_name,
                "user_id": user.user_id,
                "user_name": user.user_name,
                "details": data.model_dump()
            }
        )

    return JSONResponse(
        status_code=status.HTTP_201_CREATED,
        content={"message": "Audit log added successfully"}
    )


# Request audit logs (download)
@router.put("/audit/request", response_class=JSONResponse, tags=["Audit Logs"], summary="Request audit logs")
async def request_audit_logs(data: AuditSearchForm, user: CurrentUser, PgDB: PostgresDep) -> JSONResponse:
    """
    Request audit logs for download
    """
    await validate_permissions(
        current_user_permissions=user.permissions,
        basic_permissions=["logs:audit:view"],
        organization_level_permissions=["organization:view"],
        current_user_organization_id=user.organization_id,
        accessed_organization_id=data.organization_id,
        user_id=data.user_id,
        db=PgDB
    )

    return JSONResponse(    # TODO: Implement this endpoint
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        content={"message": "This feature is not implemented yet"}
    )


# Request mail flow logs (download)
@router.put("/mail-flow/request", response_class=JSONResponse, tags=["Mail Flow Logs"], summary="Request mail flow logs")
async def request_mail_flow_logs(data: MailFlowSearchForm, user: CurrentUser, PgDB: PostgresDep) -> JSONResponse:
    """
    Request mail flow logs for download
    """
    await validate_permissions(
        current_user_permissions=user.permissions,
        basic_permissions=["logs:mail_flow:view"],
        organization_level_permissions=["organization:view"],
        current_user_organization_id=user.organization_id,
        accessed_organization_id=data.organization_id,
        user_id=None,
        db=PgDB
    )

    return JSONResponse(    # TODO: Implement this endpoint
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        content={"message": "This feature is not implemented yet"}
    )


# Mail Login Attempts Logs
@router.post("/login-attempts/search", response_class=JSONResponse, tags=["Login Attempt Logs"], summary="Search login attempts")
async def login_attempts_search(data: LoginAttemptsSearchForm, current_page: int, page_size: int, user: CurrentUser, PgDB: PostgresDep) -> JSONResponse:
    """
    Search for login attempts based on the provided criteria
    """
    await validate_permissions(
        current_user_permissions=user.permissions,
        basic_permissions=["logs:login_attempts:view"],
        organization_level_permissions=["organization:view"],
        current_user_organization_id=user.organization_id,
        accessed_organization_id=data.organization_id,
        user_id=None,
        db=PgDB
    )

    await check_domain_organization_mapping(
        db_session=PgDB,
        domain_name=data.domain_name,
        organization_id=data.organization_id
    )

    # Fetch login attempts from the quest database
    data = get_login_attempts(
        from_date=data.date_range.from_date,
        to_date=data.date_range.to_date,
        current_page=current_page,
        page_size=page_size,
        email_id=data.email_id,
        domain_name=data.domain_name,
        origin_ip=data.origin_ip_address
    )

    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content=data
    )


# Request login attempts logs (download)
@router.put("/login-attempts/request", response_class=JSONResponse, tags=["Login Attempt Logs"], summary="Request login attempts logs")
async def request_login_attempts_logs(data: LoginAttemptsSearchForm, user: CurrentUser, PgDB: PostgresDep) -> JSONResponse:
    """
    Request login attempts logs for download
    """
    await validate_permissions(
        current_user_permissions=user.permissions,
        basic_permissions=["logs:login_attempts:view"],
        organization_level_permissions=["organization:view"],
        current_user_organization_id=user.organization_id,
        accessed_organization_id=data.organization_id,
        user_id=None,
        db=PgDB
    )

    return JSONResponse(    # TODO: Implement this endpoint
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        content={"message": "This feature is not implemented yet"}
    )
