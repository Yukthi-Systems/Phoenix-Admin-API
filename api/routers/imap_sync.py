"""
This module provides MailBox Sync from external IMAP servers into the system
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


from src.main import CurrentUser, validate_permissions, start_imap_sync
from src.utils.base.libraries import JSONResponse, APIRouter, status
from src.utils.models import IMAPSyncCreateForm
from src.database import (
    get_all_paginated_imap_sync_jobs,
    create_new_imap_sync_job,
    get_domain_details,
    PostgresDep
)

# Router
router = APIRouter()


# Create a new MailBox IMAP Sync Job
@router.post("/create", response_class=JSONResponse, tags=["IMAP Sync"], description="Create a new IMAP Sync Job")
async def create_imap_sync_job(data: IMAPSyncCreateForm, user: CurrentUser, PgDB: PostgresDep) -> JSONResponse:
    """
    Create a new IMAP Sync Job
    """
    # Get Domain details
    domain_info = await get_domain_details(db_session=PgDB, domain_name=data.to_email_domain)

    # Domain should be active
    if not domain_info["is_active"]:
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content={"message": "Domain is not active"}
        )

    await validate_permissions(
        current_user_permissions=user.permissions,
        basic_permissions=["imap_sync:create", "mailbox:view", "domain:view"],
        organization_level_permissions=["organization:view"],
        current_user_organization_id=user.organization_id,
        accessed_organization_id=domain_info["managed_by"],
        user_id=None,
        db=PgDB
    )

    # Create a new IMAP Sync Job in the database
    job_id: str = await create_new_imap_sync_job(
        db_session=PgDB,
        from_email=data.imap_username,
        from_email_password=data.imap_password,
        from_imap_server=data.imap_server,
        from_imap_port=data.imap_port if data.imap_port else 993,
        to_email=f"{data.to_email_prefix}@{data.to_email_domain}",
        to_domain_name=data.to_email_domain
    )

    # Start the IMAP Sync process
    start_imap_sync(
        job_id=job_id,
        host1=data.imap_server,
        user1=data.imap_username,
        password1=data.imap_password,
        user2=f"{data.to_email_prefix}@{data.to_email_domain}",
        port1=data.imap_port,
        folder=data.sync_specific_folder,
        from_date=data.date_range_from,
        to_date=data.date_range_to
    )

    return JSONResponse(
        status_code=status.HTTP_201_CREATED,
        content={"message": "IMAP Sync Job created successfully", "to_email": f"{data.to_email_prefix}@{data.to_email_domain}", "job_id": job_id}
    )


# List all IMAP Sync Jobs
@router.get("/list/{domain_name}/{page}/{limit}", response_class=JSONResponse, tags=["IMAP Sync"], description="List all IMAP Sync Jobs")
async def list_imap_sync_jobs(user: CurrentUser, PgDB: PostgresDep, domain_name: str, page: int = 1, limit: int = 10) -> JSONResponse:
    """
    Create a new IMAP Sync Job
    """
    # Get Domain details
    domain_info = await get_domain_details(db_session=PgDB, domain_name=domain_name)

    # Domain should be active
    if not domain_info["is_active"]:
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content={"message": "Domain is not active"}
        )

    await validate_permissions(
        current_user_permissions=user.permissions,
        basic_permissions=["imap_sync:view", "mailbox:view", "domain:view"],
        organization_level_permissions=["organization:view"],
        current_user_organization_id=user.organization_id,
        accessed_organization_id=domain_info["managed_by"],
        user_id=None,
        db=PgDB
    )

    # Fetch the list of disclaimers for the organization
    data = await get_all_paginated_imap_sync_jobs(
        db_session=PgDB,
        domain_name=domain_name,
        page=page,
        limit=limit
    )

    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content={
            "message": "List of Domain Disclaimers retrieved successfully",
            "data": data
        }
    )
