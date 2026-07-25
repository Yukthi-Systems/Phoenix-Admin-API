"""
This module provides endpoints for managing Attachment Policies associated with Domains
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


from src.utils.base.libraries import JSONResponse, APIRouter, status
from src.main import CurrentUser, validate_permissions
from src.utils.models import CreateAttachmentPolicy
from src.database import (
    export_attachment_policies_by_domain,
    get_attachment_policy_details_by_id,
    create_new_attachment_policy_entry,
    check_domain_organization_mapping,
    update_attachment_policy_details,
    get_attachment_policy_by_domain,
    delete_attachment_policy_by_id,
    PostgresDep
)

# Router
router = APIRouter()


# Create a new Attachment Policy List Entry
@router.post("/create/{organization_id}", response_class=JSONResponse, tags=["Attachment Policy Management"], description="Create a new Attachment Policy List entry at Domain level")
async def create_new_attachment_policy(data: CreateAttachmentPolicy, organization_id: str, user: CurrentUser, PgDB: PostgresDep) -> JSONResponse:
    """
    Create a new Attachment Policy List entry for a domain
    """
    await validate_permissions(
        current_user_permissions=user.permissions,
        basic_permissions=["policy:attachment:create"],
        organization_level_permissions=["organization:view"],
        current_user_organization_id=user.organization_id,
        accessed_organization_id=organization_id,
        user_id=None,
        db=PgDB
    )

    await check_domain_organization_mapping(
        db_session=PgDB,
        domain_name=data.domain_name,
        organization_id=organization_id
    )

    # Create a new entry in the database
    await create_new_attachment_policy_entry(
        db_session=PgDB,
        policy_name=data.policy_name,
        policy_description=data.policy_description,
        domain_name=data.domain_name,
        max_attachment_size_mb=data.max_attachment_size_mb,
        allowed_file_types=data.allowed_file_types,
        blocked_file_types=data.blocked_file_types,
        is_active=data.is_active
    )

    return JSONResponse(
        status_code=status.HTTP_201_CREATED,
        content={"message": "Attachment Policy List entry created successfully"}
    )


# Edit an existing Attachment Policy List Entry
@router.put("/edit/{organization_id}/{policy_id}", response_class=JSONResponse, tags=["Attachment Policy Management"], description="Edit an existing Attachment Policy List entry at Domain level")
async def edit_attachment_policy(
    policy_id: str,
    organization_id: str,
    data: CreateAttachmentPolicy,
    user: CurrentUser,
    PgDB: PostgresDep
) -> JSONResponse:
    """
    Edit an existing Attachment Policy List entry for a domain
    """
    await validate_permissions(
        current_user_permissions=user.permissions,
        basic_permissions=["policy:attachment:edit"],
        organization_level_permissions=["organization:view"],
        current_user_organization_id=user.organization_id,
        accessed_organization_id=organization_id,
        user_id=None,
        db=PgDB
    )

    await check_domain_organization_mapping(
        db_session=PgDB,
        domain_name=data.domain_name,
        organization_id=organization_id
    )

    # Edit the existing entry in the database
    await update_attachment_policy_details(
        db_session=PgDB,
        policy_id=policy_id,
        policy_name=data.policy_name,
        policy_description=data.policy_description,
        domain_name=data.domain_name,
        max_attachment_size_mb=data.max_attachment_size_mb,
        allowed_file_types=data.allowed_file_types,
        blocked_file_types=data.blocked_file_types,
        is_active=data.is_active
    )

    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content={"message": "Attachment Policy List entry updated successfully"}
    )


# Get all Attachment Policy List Entries
@router.get("/list/{organization_id}", response_class=JSONResponse, tags=["Attachment Policy Management"], description="Get all Attachment Policy List entries at Domain level")
async def get_attachment_policy_list(organization_id: str, domain_name: str, query: str, user: CurrentUser, PgDB: PostgresDep, page: int = 1, page_size: int = 10) -> JSONResponse:
    """
    Get all Attachment Policy List entries for a domain
    """
    await validate_permissions(
        current_user_permissions=user.permissions,
        basic_permissions=["policy:attachment:view"],
        organization_level_permissions=["organization:view"],
        current_user_organization_id=user.organization_id,
        accessed_organization_id=organization_id,
        user_id=None,
        db=PgDB
    )

    await check_domain_organization_mapping(
        db_session=PgDB,
        domain_name=domain_name,
        organization_id=organization_id
    )

    # Fetch all entries from the database
    policies = await get_attachment_policy_by_domain(db_session=PgDB, domain_name=domain_name, page=page, limit=page_size, search_query=query)

    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content=policies
    )


# Export all Attachment Policy List Entries
@router.get("/export/{organization_id}", response_class=JSONResponse, tags=["Attachment Policy Management"], description="Export all Attachment Policy List entries at Domain level")
async def export_attachment_policy_list(organization_id: str, domain_name: str, user: CurrentUser, PgDB: PostgresDep, page: int = 1, page_size: int = 10) -> JSONResponse:
    """
    Export all Attachment Policy List entries for a domain
    """
    await validate_permissions(
        current_user_permissions=user.permissions,
        basic_permissions=["policy:attachment:view"],
        organization_level_permissions=["organization:view"],
        current_user_organization_id=user.organization_id,
        accessed_organization_id=organization_id,
        user_id=None,
        db=PgDB
    )

    await check_domain_organization_mapping(
        db_session=PgDB,
        domain_name=domain_name,
        organization_id=organization_id
    )

    # Fetch all entries from the database
    policies = await export_attachment_policies_by_domain(
        db_session=PgDB,
        domain_name=domain_name,
        page=page,
        limit=page_size
    )

    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content=policies
    )


# Delete a General Policy List Entry
@router.delete("/delete/{organization_id}/{policy_id}", response_class=JSONResponse, tags=["Attachment Policy Management"], description="Delete an Attachment Policy List entry at Domain level")
async def delete_attachment_policy(policy_id: str, domain_name: str, organization_id: str, user: CurrentUser, PgDB: PostgresDep) -> JSONResponse:
    """
    Delete an Attachment Policy List entry for a domain
    """
    await validate_permissions(
        current_user_permissions=user.permissions,
        basic_permissions=["policy:attachment:delete"],
        organization_level_permissions=["organization:view"],
        current_user_organization_id=user.organization_id,
        accessed_organization_id=organization_id,
        user_id=None,
        db=PgDB
    )

    # Delete the entry from the database
    await delete_attachment_policy_by_id(db_session=PgDB, policy_id=policy_id, domain_name=domain_name)

    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content={"message": "Attachment Policy List entry deleted successfully"}
    )


# Get a Attachment Policy List Entry by ID
@router.get("/get/{organization_id}/{policy_id}", response_class=JSONResponse, tags=["Attachment Policy Management"], description="Get an Attachment Policy List entry by ID at Domain level")
async def get_attachment_policy_by_id(
    policy_id: str,
    organization_id: str,
    domain_name: str,
    user: CurrentUser,
    PgDB: PostgresDep
) -> JSONResponse:
    """
    Get an Attachment Policy List entry by its ID for a domain
    """
    await validate_permissions(
        current_user_permissions=user.permissions,
        basic_permissions=["policy:attachment:view"],
        organization_level_permissions=["organization:view"],
        current_user_organization_id=user.organization_id,
        accessed_organization_id=organization_id,
        user_id=None,
        db=PgDB
    )

    # Fetch the entry from the database
    entry = await get_attachment_policy_details_by_id(
        db_session=PgDB,
        domain_name=domain_name,
        policy_id=policy_id
    )

    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content=entry
    )
