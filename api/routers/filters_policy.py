"""
This module provides API endpoints for managing Filters Policy List entries at Domain level
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
from src.main import CurrentUser, validate_permissions
from src.utils.models import CreateFiltersPolicyListEntryForm
from src.database import PostgresDep, create_filter_policy_entry, edit_filter_policy_entry, get_filter_policy_entries, delete_filter_policy_entry, get_filter_policy_entry_by_id, check_domain_organization_mapping, export_filter_policy_entries


# Router
router = APIRouter()


# Create a new Filters Policy List Entry
@router.post("/create/{organization_id}", response_class=JSONResponse, tags=["Filters Policy Management"], description="Create a new Filters Policy List entry at Domain level")
async def create_new_filters_policy_entry(data: CreateFiltersPolicyListEntryForm, organization_id: str, user: CurrentUser, PgDB: PostgresDep) -> JSONResponse:
    """
    Create a new Filters Policy List entry for a domain
    """
    await validate_permissions(
        current_user_permissions=user.permissions,
        basic_permissions=["policy:filters:create"],
        organization_level_permissions=["organization:view"],
        current_user_organization_id=user.organization_id,
        accessed_organization_id=organization_id,
        user_id=None,
        db=PgDB
    )

    await check_domain_organization_mapping(
        db_session=PgDB,
        domain_name=data.domain,
        organization_id=organization_id
    )

    # Create a new entry in the database
    await create_filter_policy_entry(
        db_session=PgDB,
        domain_name=data.domain,
        policy_name=data.policy_name,
        is_active=data.is_active,
        white_entries=data.white_entries,
        black_entries=data.black_entries
    )

    return JSONResponse(
        status_code=status.HTTP_201_CREATED,
        content={"message": "Filters Policy List entry created successfully"}
    )


# Edit an existing Filters Policy List Entry
@router.put("/edit/{organization_id}/{policy_id}", response_class=JSONResponse, tags=["Filters Policy Management"], description="Edit an existing Filters Policy List entry at Domain level")
async def edit_filter_policy(policy_id: str, organization_id: str, data: CreateFiltersPolicyListEntryForm, user: CurrentUser, PgDB: PostgresDep) -> JSONResponse:
    """
    Edit an existing Filters Policy List entry for a domain
    """
    await validate_permissions(
        current_user_permissions=user.permissions,
        basic_permissions=["policy:filters:edit"],
        organization_level_permissions=["organization:view"],
        current_user_organization_id=user.organization_id,
        accessed_organization_id=organization_id,
        user_id=None,
        db=PgDB
    )

    await check_domain_organization_mapping(
        db_session=PgDB,
        domain_name=data.domain,
        organization_id=organization_id
    )

    # Edit the existing entry in the database
    await edit_filter_policy_entry(
        db_session=PgDB,
        policy_id=policy_id,
        policy_name=data.policy_name,
        is_active=data.is_active,
        white_entries=data.white_entries,
        black_entries=data.black_entries
    )

    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content={"message": "Filters Policy List entry updated successfully"}
    )


# Delete a Filters Policy List Entry
@router.delete("/delete/{organization_id}/{policy_id}", response_class=JSONResponse, tags=["Filters Policy Management"], description="Delete a Filters Policy List entry at Domain level")
async def delete_filter_policy(policy_id: str, organization_id: str, user: CurrentUser, PgDB: PostgresDep) -> JSONResponse:
    """
    Delete a Filters Policy List entry for a domain
    """
    await validate_permissions(
        current_user_permissions=user.permissions,
        basic_permissions=["policy:filters:delete"],
        organization_level_permissions=["organization:view"],
        current_user_organization_id=user.organization_id,
        accessed_organization_id=organization_id,
        user_id=None,
        db=PgDB
    )

    # Delete the entry from the database
    await delete_filter_policy_entry(
        db_session=PgDB,
        policy_id=policy_id
    )

    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content={"message": "Filters Policy List entry deleted successfully"}
    )


# Get Filters Policy List Entries
@router.get("/list/{organization_id}/{domain_name}", response_class=JSONResponse, tags=["Filters Policy Management"], description="Get all Filters Policy List entries for a specific domain")
async def get_filter_policy(
    domain_name: str,
    organization_id: str,
    query: str,
    user: CurrentUser,
    PgDB: PostgresDep,
    page: int = 1,
    page_size: int = 10
) -> JSONResponse:
    """
    Get all Filters Policy List entries for a specific domain
    """
    await validate_permissions(
        current_user_permissions=user.permissions,
        basic_permissions=["policy:filters:view"],
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

    # Fetch the entries from the database
    entries = await get_filter_policy_entries(
        db_session=PgDB,
        domain_name=domain_name,
        search_query=query,
        page=page,
        page_size=page_size
    )

    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content=entries
    )


# Export Filters Policy List Entries
@router.get("/export/{organization_id}/{domain_name}", response_class=JSONResponse, tags=["Filters Policy Management"], description="Get all Filters Policy List entries for a specific domain")
async def export_filter_policy(
    organization_id: str,
    domain_name: str,
    user: CurrentUser,
    PgDB: PostgresDep,
    page: int = 1,
    page_size: int = 10
) -> JSONResponse:
    """
    Export all Filters Policy List entries for a specific domain
    """
    await validate_permissions(
        current_user_permissions=user.permissions,
        basic_permissions=["policy:filters:view"],
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

    # Fetch the entries from the database
    entries = await export_filter_policy_entries(
        db_session=PgDB,
        domain_name=domain_name,
        page=page,
        page_size=page_size
    )

    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content=entries
    )


# Get a specific Filters Policy List Entry by ID
@router.get("/entry/{organization_id}/{policy_id}", response_class=JSONResponse, tags=["Filters Policy Management"], description="Get a specific Filters Policy List entry by ID")
async def get_filter_policy_entry(
    policy_id: str,
    organization_id: str,
    user: CurrentUser,
    PgDB: PostgresDep
) -> JSONResponse:
    """
    Get a specific Filters Policy List entry by ID
    """
    await validate_permissions(
        current_user_permissions=user.permissions,
        basic_permissions=["policy:filters:view"],
        organization_level_permissions=["organization:view"],
        current_user_organization_id=user.organization_id,
        accessed_organization_id=organization_id,
        user_id=None,
        db=PgDB
    )

    # Fetch the entry from the database
    entry = await get_filter_policy_entry_by_id(
        db_session=PgDB,
        policy_id=policy_id
    )

    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content=entry
    )
